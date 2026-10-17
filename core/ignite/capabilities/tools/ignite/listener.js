'use strict';

// The messaging listener: dispatch(event, ctx) admits and routes one inbound event; start(ctx) opens
// the connector sessions the configuration names. Routing order: admission, thread affinity, the most
// specific subscription, a judged subscription, then the default agent. Every decision is one JSON line
// on ctx.decisionFile. A judgment error is held for retry and starts no turn.

const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { spawnable } = require('../../../../cast/capabilities/tools/cast/lib/win-exec');
const { conversationKey } = require('./store.js');
const live = require('./live-status.js');
const { listenersConfig, envValue } = require('./config.js');

const JUDGMENT_MS = 5_000;
const HOLD_BACKOFF_CAP_MS = 300_000;
const INGRESS_LIMIT = 20_000;

function logDecision(ctx, row) {
  const line = { at: typeof ctx.now === 'function' ? ctx.now() : Date.now(), ...row };
  const file = ctx.decisionFile;
  if (file) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.appendFileSync(file, `${JSON.stringify(line)}\n`);
  }
  return line;
}

function atomicWrite(file, text) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, text);
  fs.renameSync(tmp, file);
}

function withLock(file, fn) {
  const lock = `${file}.lock`;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  for (let attempt = 0; attempt < 30; attempt += 1) {
    let fd;
    try { fd = fs.openSync(lock, 'wx'); } catch (error) {
      if (error.code !== 'EEXIST') throw error;
      try {
        const age = Date.now() - fs.statSync(lock).mtimeMs;
        if (age > 10_000) fs.unlinkSync(lock);
      } catch { /* another writer owns it */ }
      continue;
    }
    try { return fn(); } finally {
      fs.closeSync(fd);
      try { fs.unlinkSync(lock); } catch { /* released */ }
    }
  }
  throw new Error(`${path.basename(file)} is busy`);
}

function readJson(file, fallback) {
  if (!file || !fs.existsSync(file)) return fallback;
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return fallback; }
}

function holdPath(ctx) {
  return ctx.holdFile || (ctx.decisionFile ? `${ctx.decisionFile}.hold` : null);
}

function readHold(ctx) {
  const file = holdPath(ctx);
  if (!file || !fs.existsSync(file)) return [];
  const text = fs.readFileSync(file, 'utf8').trim();
  if (!text) return [];
  if (text.startsWith('[')) {
    try {
      const parsed = JSON.parse(text);
      return Array.isArray(parsed) ? parsed : [];
    } catch { return []; }
  }
  return text.split(/\r?\n/).filter(Boolean).map((line) => {
    try { return JSON.parse(line); } catch { return null; }
  }).filter((row) => row?.event);
}

function writeHold(ctx, rows) {
  const file = holdPath(ctx);
  if (!file) return;
  atomicWrite(file, JSON.stringify(rows));
}

function eventKey(event) {
  return [event?.connector, event?.account, event?.conversation || event?.group, event?.id].join(':');
}

function hold(ctx, event, reason) {
  const file = holdPath(ctx);
  if (!file || !event) return;
  withLock(file, () => {
    const rows = readHold(ctx).filter((row) => eventKey(row.event) !== eventKey(event));
    const prior = readHold(ctx).find((row) => eventKey(row.event) === eventKey(event));
    const attempts = (prior?.attempts || 0) + 1;
    rows.push({
      id: eventKey(event),
      reason,
      attempts,
      nextAt: Date.now() + Math.min(HOLD_BACKOFF_CAP_MS, 1000 * (2 ** Math.min(attempts, 8))),
      event,
    });
    writeHold(ctx, rows);
  });
}

function releaseHold(ctx, event) {
  const file = holdPath(ctx);
  if (!file || !event || !fs.existsSync(file)) return;
  try {
    withLock(file, () => {
      writeHold(ctx, readHold(ctx).filter((row) => eventKey(row.event) !== eventKey(event)));
    });
  } catch { /* a failed release keeps the event; dedup stops a second queue */ }
}

function ingressPath(ctx) {
  return ctx.ingressFile || (ctx.decisionFile ? path.join(path.dirname(ctx.decisionFile), 'ingress.json') : null);
}

function acceptedIngress(ctx, event) {
  const body = readJson(ingressPath(ctx), null);
  return body?.accepted?.[eventKey(event)] || null;
}

function recordIngress(ctx, event, agent) {
  const file = ingressPath(ctx);
  if (!file) return;
  withLock(file, () => {
    const body = readJson(file, { accepted: {} }) || { accepted: {} };
    if (!body.accepted || typeof body.accepted !== 'object') body.accepted = {};
    body.accepted[eventKey(event)] = { agent, at: Date.now() };
    const keys = Object.keys(body.accepted);
    if (keys.length > INGRESS_LIMIT) {
      for (const key of keys.slice(0, keys.length - INGRESS_LIMIT)) delete body.accepted[key];
    }
    atomicWrite(file, JSON.stringify(body));
  });
}

function bindThread(ctx, row) {
  if (!ctx.threadFile || !row?.agent || !row.thread) return;
  withLock(ctx.threadFile, () => {
    const current = readJson(ctx.threadFile, []);
    const rows = Array.isArray(current) ? current : [];
    const exists = rows.some((item) => item.connector === row.connector && item.account === row.account
      && item.conversation === row.conversation && item.thread === row.thread);
    if (!exists) rows.push(row);
    atomicWrite(ctx.threadFile, JSON.stringify(rows));
  });
}

function ruleProblem(rule) {
  if (!rule || typeof rule !== 'object' || Array.isArray(rule)) return 'rule is not an object';
  for (const key of ['id', 'connector', 'account', 'group', 'contact', 'agent']) {
    if (rule[key] != null && typeof rule[key] !== 'string') return `${key} must be a string`;
  }
  if (!rule.agent) return 'agent required';
  if (rule.judge == null) return null;
  const question = typeof rule.judge === 'string' ? rule.judge : rule.judge.question;
  if (!question || typeof question !== 'string') return 'judge must be a question or null';
  return null;
}

function lastGoodPath(ctx) {
  return ctx.decisionFile ? path.join(path.dirname(ctx.decisionFile), 'subscriptions.last-good.json') : null;
}

function loadRules(ctx) {
  const file = ctx.subscriptionFile;
  if (!file || !fs.existsSync(file)) return { rules: [], error: null, held: false };
  let parsed;
  try { parsed = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (error) {
    return recoverRules(ctx, error.message);
  }
  if (!Array.isArray(parsed)) return recoverRules(ctx, 'subscriptions must be an array');
  for (const rule of parsed) {
    const problem = ruleProblem(rule);
    if (problem) return recoverRules(ctx, problem);
  }
  const good = lastGoodPath(ctx);
  if (good) {
    try { atomicWrite(good, JSON.stringify(parsed)); } catch { /* the source file is still valid */ }
  }
  return { rules: parsed, error: null, held: false };
}

function recoverRules(ctx, message) {
  const memory = ctx._rules;
  const saved = readJson(lastGoodPath(ctx), null);
  const rules = Array.isArray(memory) ? memory : (Array.isArray(saved) ? saved : null);
  return { rules: rules || [], error: message, held: !rules };
}

function constraints(rule) {
  const set = [];
  if (rule.connector) set.push(['connector', rule.connector]);
  if (rule.account) set.push(['account', rule.account]);
  if (rule.group) set.push(['group', rule.group]);
  if (rule.contact) set.push(['contact', rule.contact]);
  return set;
}

function sameConstraints(a, b) {
  const left = constraints(a);
  const right = new Map(constraints(b));
  return left.length === right.size && left.every(([key, value]) => right.get(key) === value);
}

function moreSpecific(a, b) {
  const extra = constraints(a);
  const base = constraints(b);
  if (extra.length <= base.length) return false;
  const have = new Map(extra);
  return base.every(([key, value]) => have.get(key) === value);
}

function matches(rule, event) {
  if (rule.connector && rule.connector !== event.connector) return false;
  if (rule.account && rule.account !== event.account) return false;
  if (rule.group && rule.group !== (event.group || null)) return false;
  if (rule.contact && rule.contact !== event.from) return false;
  return true;
}

function agentNames(ctx, rules) {
  const names = new Set();
  if (ctx.config?.dmAgent) names.add(ctx.config.dmAgent);
  for (const agent of Object.values(ctx.config?.routes || {})) names.add(agent);
  for (const agent of Object.values(ctx.defaults || {})) if (agent) names.add(agent);
  for (const rule of rules) if (rule.agent) names.add(rule.agent);
  const threads = readJson(ctx.threadFile, []);
  if (Array.isArray(threads)) for (const row of threads) if (row.agent) names.add(row.agent);
  if (typeof ctx.agentSlugs === 'function') {
    for (const slug of ctx.agentSlugs() || []) names.add(slug);
  }
  return [...names];
}

function affinityFromStore(store, event, conversation, thread) {
  if (!store?.db) return false;
  if (event.connector === 'slack') {
    return Boolean(store.db.prepare(`SELECT o.id FROM outbox o
      JOIN conversations c ON c.key = o.conversation_key
      WHERE o.state='delivered' AND c.workspace=? AND o.channel=? AND o.ts=?
        AND c.key NOT LIKE 'google:%' AND c.key NOT LIKE 'whatsapp:%'`).get(event.account, conversation, thread));
  }
  return Boolean(store.db.prepare(`SELECT o.id FROM outbox o
    JOIN conversations c ON c.key = o.conversation_key
    WHERE o.state='delivered' AND c.workspace=? AND o.channel=? AND o.ts=? AND c.key LIKE ?`)
    .get(event.account, conversation, thread, `${event.connector}:%`));
}

function affinity(event, ctx, rules) {
  const thread = event.thread;
  if (!thread || thread === event.id) return null;
  const conversation = event.conversation || event.group;
  const threads = readJson(ctx.threadFile, []);
  if (Array.isArray(threads)) {
    for (const row of threads) {
      if (row.connector === event.connector && row.account === event.account
        && row.conversation === conversation && row.thread === thread && row.agent) return row.agent;
    }
  }
  if (typeof ctx.openStore !== 'function') return null;
  for (const slug of agentNames(ctx, rules)) {
    let store;
    try { store = ctx.openStore(slug); } catch { continue; }
    if (affinityFromStore(store, event, conversation, thread)) return slug;
  }
  return null;
}

function defaultAgent(event, ctx) {
  if (event.connector === 'google') return ctx.defaults?.mail || null;
  if (event.connector === 'whatsapp') return ctx.defaults?.whatsapp || ctx.config?.dmAgent || null;
  if (event.group) return ctx.config?.routes?.[event.group] || null;
  return ctx.defaults?.slackDm || ctx.config?.dmAgent || null;
}

function pickSubscription(matched) {
  const tops = matched.filter((rule) => !matched.some((other) => other !== rule && moreSpecific(other, rule)));
  if (tops.length === 1) return { agent: tops[0].agent, reason: tops[0].id || 'match' };
  const equal = tops.every((rule) => sameConstraints(rule, tops[0]));
  const agents = new Set(tops.map((rule) => rule.agent));
  if (equal && agents.size === 1) return { agent: tops[0].agent, reason: tops[0].id || 'match' };
  return { tie: true };
}

function launch(command, args) {
  const win = spawnable(command, args);
  return spawn(win.cmd, win.args, { stdio: ['pipe', 'pipe', 'pipe'], ...win.opts });
}

function typesafeYesNo(question, text, ctx) {
  const command = ctx.typesafeCommand || 'typesafe';
  return new Promise((resolve, reject) => {
    const child = launch(command, ['yesno', question, '--json']);
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error('timeout'));
    }, ctx.judgeTimeoutMs || JUDGMENT_MS);
    let out = '';
    let err = '';
    child.stdout.on('data', (chunk) => { out += chunk; });
    child.stderr.on('data', (chunk) => { err += chunk; });
    child.on('error', (error) => { clearTimeout(timer); reject(error); });
    child.on('close', (code) => {
      clearTimeout(timer);
      if (code !== 0 && code !== 3) {
        reject(new Error((err || out || `typesafe exited ${code}`).trim()));
        return;
      }
      try {
        const body = JSON.parse(out);
        const answers = body.answers || body.results?.[0]?.answers || {};
        const answer = Object.values(answers)[0] || {};
        const probability = typeof answer.noul === 'number' ? answer.noul : null;
        resolve({ yes: probability != null ? probability >= 0.5 : Boolean(body.passed) });
      } catch (error) {
        reject(error);
      }
    });
    child.stdin.end(text || '');
  });
}

async function judgeOne(ctx, question, text) {
  if (typeof ctx.judge === 'function') return ctx.judge(question, text);
  return typesafeYesNo(question, text, ctx);
}

async function judgedRoute(event, rules, ctx) {
  const judged = rules.filter((rule) => rule.judge && matches(rule, event));
  if (!judged.length) return {};
  const yes = [];
  for (const rule of judged) {
    let answer;
    try {
      answer = await judgeOne(ctx, rule.judge.question || rule.judge, event.text || '');
    } catch (error) {
      return { error: error.message || 'judgment-error' };
    }
    if (answer?.yes) yes.push(rule);
  }
  if (yes.length > 1) return { tie: true };
  if (yes.length === 1) return { agent: yes[0].agent, reason: yes[0].id || 'judged' };
  return {};
}

function keyPart(value, label) {
  const text = String(value ?? '');
  if (!text || text.includes(':')) throw new Error(`${label} required`);
  return text;
}

function provenanceOf(event, account, channel) {
  return {
    connector: event.connector,
    account,
    conversation: channel,
    sender: event.from || null,
    claimed: event.claimedFrom || event.from || null,
    trusted: Boolean(event.identity?.verified && event.identity?.owner),
  };
}

async function accept(event, agent, ctx, step) {
  if (typeof ctx.openStore !== 'function') throw new Error('openStore required');
  const store = await ctx.openStore(agent);
  const account = keyPart(event.account, 'account');
  const channel = keyPart(event.conversation || event.group, 'conversation');
  const ts = keyPart(event.id, 'id');
  const rootTs = event.thread && event.thread !== event.id ? keyPart(event.thread, 'thread') : ts;
  const key = conversationKey(account, channel, rootTs, event.connector);
  const provenance = provenanceOf(event, account, channel);
  const message = {
    id: `${event.connector}:${account}:${channel}:${ts}`,
    role: 'owner',
    text: event.text || '',
    files: Array.isArray(event.files) ? event.files : [],
    team: account,
    channel,
    ts,
    createdAt: Number.isFinite(event.at) ? event.at : Date.now(),
    metadata: {
      connector: event.connector,
      account,
      from: event.from || null,
      claimed: provenance.claimed,
      trusted: provenance.trusted,
      conversation: channel,
      thread: event.thread || null,
      group: event.group || null,
    },
  };
  const input = {
    key,
    agent,
    workspace: account,
    channel,
    rootTs,
    activated: true,
    message,
    payload: {
      text: message.text,
      files: message.files,
      ts,
      threadTs: rootTs,
      connector: event.connector,
      provenance,
    },
  };
  let result;
  const threaded = Boolean(event.thread && event.thread !== event.id && event.group);
  if (threaded && event.connector === 'slack') {
    const existing = await store.conversationByThread({ workspace: account, channel, rootTs });
    if (!existing?.activated) {
      if (typeof ctx.slack?.threadHistory !== 'function') throw new Error('slack.threadHistory required');
      const history = await ctx.slack.threadHistory(channel, rootTs);
      result = store.transaction(() => {
        store.upsertConversation({ key, agent, workspace: account, channel, rootTs, activated: false });
        for (const raw of history || []) {
          if (!raw?.ts || raw.ts === ts) continue;
          store.recordMessage(key, {
            id: `${account}:${channel}:${raw.ts}`,
            role: raw.user === ctx.config?.slack?.ownerUserId ? 'owner' : 'user',
            text: raw.text || '',
            files: raw.files || [],
            team: account,
            channel,
            ts: raw.ts,
            createdAt: Math.round(Number(raw.ts) * 1000) || Date.now(),
            metadata: { connector: 'slack', account, from: raw.user || null, conversation: channel, trusted: raw.user === ctx.config?.slack?.ownerUserId },
          });
        }
        return store.acceptOwnerInput(input);
      });
    }
  }
  if (!result) result = await store.acceptOwnerInput(input);
  if (result?.duplicate) return { ignored: 'duplicate', agent, key, queued: false };
  bindThread(ctx, { connector: event.connector, account, conversation: channel, thread: rootTs, agent, via: 'inbound' });
  recordIngress(ctx, event, agent);
  if (event.connector === 'slack') {
    live.received(store, { conversationKey: key, channel, ts }, ctx.log);
  }
  return { queued: true, agent, key, workId: result.workId, step };
}

function decisionBase(event) {
  return {
    connector: event?.connector || null,
    from: event?.from || null,
    claimed: event?.claimedFrom || event?.from || null,
    account: event?.account || null,
    conversation: event?.conversation || event?.group || null,
    id: event?.id || null,
    trusted: Boolean(event?.identity?.verified && event?.identity?.owner),
  };
}

async function dispatch(event, ctx) {
  const base = decisionBase(event);
  if (!event?.connector || !event.id) {
    logDecision(ctx, { step: 'admission', agent: null, reason: 'malformed', ...base });
    return { queued: false, agent: null, ignored: 'malformed' };
  }
  if (event.isSelf) {
    logDecision(ctx, { step: 'self', agent: null, reason: 'self', ...base });
    releaseHold(ctx, event);
    return { queued: false, agent: null, ignored: 'self' };
  }
  const identity = event.identity || {};
  if (!identity.verified || !identity.owner) {
    const reason = identity.verified ? 'non-owner' : 'unverified';
    logDecision(ctx, { step: 'admission', agent: null, reason, ...base });
    releaseHold(ctx, event);
    return { queued: false, agent: null, ignored: reason === 'non-owner' ? 'non-owner' : 'unverified' };
  }
  const prior = acceptedIngress(ctx, event);
  if (prior) {
    if (typeof ctx.openStore === 'function') {
      try { await ctx.openStore(prior.agent); } catch { /* the ledger still names the agent */ }
    }
    logDecision(ctx, { step: 'admission', agent: prior.agent, reason: 'duplicate', ...base });
    releaseHold(ctx, event);
    return { queued: false, agent: prior.agent, ignored: 'duplicate' };
  }
  const loaded = loadRules(ctx);
  if (!loaded.error) ctx._rules = loaded.rules;
  if (loaded.error) {
    logDecision(ctx, { step: 'subscriptions', agent: null, reason: 'invalid', detail: loaded.error, ...base });
    if (loaded.held) {
      hold(ctx, event, 'subscriptions-invalid');
      return { queued: false, agent: null, ignored: 'subscriptions-invalid' };
    }
  }
  const rules = loaded.rules;
  const threadAgent = affinity(event, ctx, rules);
  if (threadAgent) {
    logDecision(ctx, { step: 'affinity', agent: threadAgent, reason: 'thread', ...base });
    const accepted = await accept(event, threadAgent, ctx, 'affinity');
    if (accepted.queued) releaseHold(ctx, event);
    return accepted;
  }
  const deterministic = rules.filter((rule) => !rule.judge && matches(rule, event));
  if (deterministic.length) {
    const picked = pickSubscription(deterministic);
    if (picked.tie) {
      logDecision(ctx, { step: 'subscription', agent: null, reason: 'tie', ...base });
      return { queued: false, agent: null, ignored: 'tie' };
    }
    logDecision(ctx, { step: 'subscription', agent: picked.agent, reason: picked.reason, ...base });
    const accepted = await accept(event, picked.agent, ctx, 'subscription');
    if (accepted.queued) releaseHold(ctx, event);
    return accepted;
  }
  const judged = await judgedRoute(event, rules, ctx);
  if (judged.error) {
    logDecision(ctx, { step: 'judged', agent: null, reason: 'judgment-error', detail: judged.error, ...base });
    hold(ctx, event, 'judgment-error');
    return { queued: false, agent: null, ignored: 'judgment-error' };
  }
  if (judged.tie) {
    logDecision(ctx, { step: 'subscription', agent: null, reason: 'tie', ...base });
    releaseHold(ctx, event);
    return { queued: false, agent: null, ignored: 'tie' };
  }
  if (judged.agent) {
    logDecision(ctx, { step: 'judged', agent: judged.agent, reason: judged.reason, ...base });
    const accepted = await accept(event, judged.agent, ctx, 'judged');
    if (accepted.queued) releaseHold(ctx, event);
    return accepted;
  }
  const agent = defaultAgent(event, ctx);
  if (!agent) {
    const ignored = event.group ? 'unconfigured' : 'no-default';
    logDecision(ctx, { step: 'default', agent: null, reason: ignored, ...base });
    releaseHold(ctx, event);
    return { queued: false, agent: null, ignored };
  }
  logDecision(ctx, { step: 'default', agent, reason: event.connector === 'google' ? 'mail' : (event.group ? 'route' : 'dm'), ...base });
  const accepted = await accept(event, agent, ctx, 'default');
  if (accepted.queued) releaseHold(ctx, event);
  return accepted;
}

async function replayHeld(ctx) {
  const now = typeof ctx.now === 'function' ? ctx.now() : Date.now();
  for (const row of readHold(ctx)) {
    if (row.nextAt && row.nextAt > now) continue;
    try { await dispatch(row.event, ctx); } catch (error) {
      logDecision(ctx, { step: 'replay', agent: null, reason: error.message, connector: row.event?.connector || null, id: row.event?.id || null });
    }
  }
}

function fromSocket(event, config) {
  const owner = config?.slack?.ownerUserId || '';
  const user = typeof event?.user === 'string' ? event.user : '';
  const self = Boolean(event?.isBotOrSelf);
  const ownerMatch = Boolean(owner) && user === owner && !self;
  const im = event?.channelType === 'im';
  const thread = event?.threadTs && event.threadTs !== event?.ts ? event.threadTs : null;
  return {
    connector: 'slack',
    account: event?.team || config?.slack?.team,
    id: event?.ts,
    at: Number(event?.ts) ? Math.round(Number(event.ts) * 1000) : Date.now(),
    from: user,
    claimedFrom: user,
    group: im ? null : (event?.channel || null),
    conversation: event?.channel || null,
    thread,
    text: event?.text || '',
    files: Array.isArray(event?.files) ? event.files : [],
    isSelf: self,
    mentionsAgent: Boolean(event?.mentionsBot),
    identity: { verified: ownerMatch, method: 'slack-socket', owner: ownerMatch, claimed: user },
  };
}

async function start(ctx) {
  const stops = [];
  const transports = ctx.transports || {};
  for (const [name, transport] of Object.entries(transports)) {
    if (typeof transport?.connect !== 'function') continue;
    try {
      await transport.connect();
    } catch (error) {
      logDecision(ctx, { step: 'connection', connector: name, agent: null, reason: error.message });
    }
  }
  if (ctx.transports) return { stop() { for (const fn of stops) fn(); } };
  const sections = listenersConfig(ctx.config);
  if (!sections) return { async stop() {} };
  const abort = new AbortController();
  let chain = Promise.resolve();
  if (sections.whatsapp) {
    try {
      const receiver = require('../../../../../connectors/whatsapp/capabilities/tools/whatsapp/lib/messaging.js');
      const secret = envValue(ctx.config.workspace, sections.whatsapp.secretEnv);
      if (!secret) {
        logDecision(ctx, { step: 'connection', connector: 'whatsapp', agent: null, reason: 'webhook secret is not configured' });
      } else {
        const status = await receiver.sessionStatus({
          installation: ctx.config.workspace,
          account: sections.whatsapp.account,
          spawn: ctx.spawn,
        });
        const phone = status.phone || String(status.linked_jid || '').split('@')[0];
        if (!status.authenticated || phone.replace(/\D/g, '') !== String(sections.whatsapp.account).replace(/\D/g, '')) {
          logDecision(ctx, { step: 'connection', connector: 'whatsapp', agent: null, reason: 'whatsapp session does not match the configured account' });
        } else {
          const listening = await receiver.listen({
            secret,
            owner: sections.whatsapp.owner,
            account: sections.whatsapp.account,
            port: sections.whatsapp.port,
            onEvent: (neutral) => dispatch(neutral, ctx),
            onReject: (row) => logDecision(ctx, { step: 'admission', agent: null, reason: 'unverified', connector: 'whatsapp', from: null, ...row }),
          });
          const sync = receiver.supervise({
            store: path.join(ctx.config.workspace, '.rbtv', 'runtime', 'whatsapp'),
            secret,
            port: listening.port,
            account: sections.whatsapp.account,
            spawn: ctx.spawn,
            onLog: (reason) => logDecision(ctx, { step: 'connection', connector: 'whatsapp', agent: null, reason }),
          });
          stops.push(async () => { await sync.stop(); await listening.close(); });
        }
      }
    } catch (error) {
      logDecision(ctx, { step: 'connection', connector: 'whatsapp', agent: null, reason: error.message });
    }
  } else if (ctx.config?.listeners?.whatsapp) {
    logDecision(ctx, { step: 'connection', connector: 'whatsapp', agent: null, reason: 'owner identity is not configured' });
  }
  if (sections.google?.pollMs) {
    const google = require('../../../../../connectors/google/capabilities/tools/google/lib/messaging.js');
    const safeAccount = String(sections.google.account).replace(/[^A-Za-z0-9._-]/g, '_');
    const cursorFile = path.join(path.dirname(ctx.decisionFile || path.join(ctx.config.workspace, '.rbtv', 'runtime', 'ignite', 'decisions.jsonl')), `google-cursor-${safeAccount}.json`);
    const poll = () => {
      chain = chain.then(() => replayHeld(ctx)).then(() => google.poll({
        section: sections.google,
        cursorFile,
        spawn: ctx.spawn,
        signal: abort.signal,
        onEvent: (neutral) => dispatch(neutral, ctx),
      })).catch((error) => logDecision(ctx, { step: 'connection', connector: 'google', agent: null, reason: error.message }));
      return chain;
    };
    const timer = setInterval(() => { if (!abort.signal.aborted) poll(); }, sections.google.pollMs);
    if (typeof timer.unref === 'function') timer.unref();
    stops.push(async () => {
      clearInterval(timer);
      abort.abort();
      google.abort();
      await chain;
    });
  } else if (ctx.config?.listeners?.google) {
    logDecision(ctx, { step: 'connection', connector: 'google', agent: null, reason: 'poll cadence is not configured' });
  }
  try { await replayHeld(ctx); } catch (error) {
    logDecision(ctx, { step: 'replay', agent: null, reason: error.message });
  }
  return {
    async stop() {
      for (const fn of stops) await fn();
    },
  };
}

module.exports = { dispatch, start, fromSocket, replayHeld, JUDGMENT_MS };
