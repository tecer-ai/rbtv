'use strict';

// The messaging listener: dispatch(event, ctx) admits and routes one inbound event; start(ctx) opens
// the connector sessions the configuration names. Routing order: admission, thread affinity, the most
// specific subscription, a judged subscription, then the default agent. Every decision is one JSON line
// on ctx.decisionFile. A judgment error is held for retry and starts no turn.

const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { conversationKey } = require('./store.js');
const live = require('./live-status.js');
const { listenersConfig, envValue } = require('./config.js');

const JUDGMENT_MS = 5_000;

function logDecision(ctx, row) {
  const line = { at: typeof ctx.now === 'function' ? ctx.now() : Date.now(), ...row };
  const file = ctx.decisionFile;
  if (file) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.appendFileSync(file, `${JSON.stringify(line)}\n`);
  }
  return line;
}

function hold(ctx, event, reason) {
  const file = ctx.holdFile || (ctx.decisionFile ? `${ctx.decisionFile}.hold` : null);
  if (!file) return;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, `${JSON.stringify({ at: Date.now(), reason, event })}\n`);
}

function readList(file) {
  if (!file || !fs.existsSync(file)) return [];
  try {
    const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
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
  for (const row of readList(ctx.threadFile)) if (row.agent) names.add(row.agent);
  if (typeof ctx.agentSlugs === 'function') {
    for (const slug of ctx.agentSlugs() || []) names.add(slug);
  }
  return [...names];
}

function affinity(event, ctx, rules) {
  const thread = event.thread;
  if (!thread || thread === event.id) return null;
  const conversation = event.conversation || event.group;
  for (const row of readList(ctx.threadFile)) {
    if (row.connector === event.connector && row.account === event.account
      && row.conversation === conversation && row.thread === thread && row.agent) return row.agent;
  }
  if (typeof ctx.openStore !== 'function') return null;
  for (const slug of agentNames(ctx, rules)) {
    let store;
    try { store = ctx.openStore(slug); } catch { continue; }
    if (!store?.db) continue;
    const hit = store.db.prepare("SELECT id FROM outbox WHERE state='delivered' AND channel=? AND ts=?").get(conversation, thread);
    if (hit) return slug;
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

function typesafeYesNo(question, text, ctx) {
  const command = ctx.typesafeCommand || 'typesafe';
  return new Promise((resolve, reject) => {
    const child = spawn(command, ['--json', 'yesno', question], { stdio: ['pipe', 'pipe', 'pipe'] });
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

async function accept(event, agent, ctx, step) {
  if (typeof ctx.openStore !== 'function') throw new Error('openStore required');
  const store = await ctx.openStore(agent);
  const account = keyPart(event.account, 'account');
  const channel = keyPart(event.conversation || event.group, 'conversation');
  const ts = keyPart(event.id, 'id');
  const rootTs = event.thread && event.thread !== event.id ? keyPart(event.thread, 'thread') : ts;
  const key = conversationKey(account, channel, rootTs);
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
    payload: { text: message.text, files: message.files, ts, threadTs: rootTs, connector: event.connector },
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
            metadata: { connector: 'slack', account, from: raw.user || null, conversation: channel },
          });
        }
        return store.acceptOwnerInput(input);
      });
    }
  }
  if (!result) result = await store.acceptOwnerInput(input);
  if (result?.duplicate) return { ignored: 'duplicate', agent, key, queued: false };
  if (event.connector === 'slack') {
    live.received(store, { conversationKey: key, channel, ts }, ctx.log);
  }
  return { queued: true, agent, key, workId: result.workId, step };
}

async function dispatch(event, ctx) {
  const base = { connector: event?.connector || null, from: event?.from || null, id: event?.id || null };
  if (!event?.connector || !event.id) {
    logDecision(ctx, { step: 'admission', agent: null, reason: 'malformed', ...base });
    return { queued: false, agent: null, ignored: 'malformed' };
  }
  if (event.isSelf) {
    logDecision(ctx, { step: 'self', agent: null, reason: 'self', ...base });
    return { queued: false, agent: null, ignored: 'self' };
  }
  const identity = event.identity || {};
  if (!identity.verified || !identity.owner) {
    const reason = identity.verified ? 'non-owner' : 'unverified';
    logDecision(ctx, { step: 'admission', agent: null, reason, ...base });
    return { queued: false, agent: null, ignored: reason === 'non-owner' ? 'non-owner' : 'unverified' };
  }
  const rules = readList(ctx.subscriptionFile);
  const threadAgent = affinity(event, ctx, rules);
  if (threadAgent) {
    logDecision(ctx, { step: 'affinity', agent: threadAgent, reason: 'thread', ...base });
    return accept(event, threadAgent, ctx, 'affinity');
  }
  const deterministic = rules.filter((rule) => !rule.judge && matches(rule, event));
  if (deterministic.length) {
    const picked = pickSubscription(deterministic);
    if (picked.tie) {
      logDecision(ctx, { step: 'subscription', agent: null, reason: 'tie', ...base });
      return { queued: false, agent: null, ignored: 'tie' };
    }
    logDecision(ctx, { step: 'subscription', agent: picked.agent, reason: picked.reason, ...base });
    return accept(event, picked.agent, ctx, 'subscription');
  }
  const judged = await judgedRoute(event, rules, ctx);
  if (judged.error) {
    logDecision(ctx, { step: 'judged', agent: null, reason: 'judgment-error', detail: judged.error, ...base });
    hold(ctx, event, 'judgment-error');
    return { queued: false, agent: null, ignored: 'judgment-error' };
  }
  if (judged.tie) {
    logDecision(ctx, { step: 'subscription', agent: null, reason: 'tie', ...base });
    return { queued: false, agent: null, ignored: 'tie' };
  }
  if (judged.agent) {
    logDecision(ctx, { step: 'judged', agent: judged.agent, reason: judged.reason, ...base });
    return accept(event, judged.agent, ctx, 'judged');
  }
  const agent = defaultAgent(event, ctx);
  if (!agent) {
    const ignored = event.group ? 'unconfigured' : 'no-default';
    logDecision(ctx, { step: 'default', agent: null, reason: ignored, ...base });
    return { queued: false, agent: null, ignored };
  }
  logDecision(ctx, { step: 'default', agent, reason: event.connector === 'google' ? 'mail' : (event.group ? 'route' : 'dm'), ...base });
  return accept(event, agent, ctx, 'default');
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
    group: im ? null : (event?.channel || null),
    conversation: event?.channel || null,
    thread,
    text: event?.text || '',
    files: Array.isArray(event?.files) ? event.files : [],
    isSelf: self,
    mentionsAgent: Boolean(event?.mentionsBot),
    identity: { verified: ownerMatch, method: 'slack-socket', owner: ownerMatch },
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
  if (!sections) return { stop() {} };
  if (sections.whatsapp) {
    try {
      const receiver = require('../../../../../connectors/whatsapp/capabilities/tools/whatsapp/lib/messaging.js');
      const secret = envValue(ctx.config.workspace, sections.whatsapp.secretEnv);
      if (!secret) {
        logDecision(ctx, { step: 'connection', connector: 'whatsapp', agent: null, reason: 'webhook secret is not configured' });
      } else {
        const listening = await receiver.listen({
          secret,
          owner: sections.whatsapp.owner,
          account: sections.whatsapp.account,
          port: sections.whatsapp.port,
          onEvent: (neutral) => dispatch(neutral, ctx),
          onReject: () => logDecision(ctx, { step: 'admission', agent: null, reason: 'unverified', connector: 'whatsapp', from: null }),
        });
        stops.push(() => listening.close());
      }
    } catch (error) {
      logDecision(ctx, { step: 'connection', connector: 'whatsapp', agent: null, reason: error.message });
    }
  } else if (ctx.config?.listeners?.whatsapp) {
    logDecision(ctx, { step: 'connection', connector: 'whatsapp', agent: null, reason: 'owner identity is not configured' });
  }
  if (sections.google?.pollMs) {
    const google = require('../../../../../connectors/google/capabilities/tools/google/lib/messaging.js');
    const cursorFile = path.join(path.dirname(ctx.decisionFile || path.join(ctx.config.workspace, '.rbtv', 'runtime', 'ignite', 'decisions.jsonl')), 'google-cursor.json');
    const poll = () => google.poll({
      section: sections.google,
      cursorFile,
      spawn: ctx.spawn,
      onEvent: (neutral) => dispatch(neutral, ctx),
    }).catch((error) => logDecision(ctx, { step: 'connection', connector: 'google', agent: null, reason: error.message }));
    const timer = setInterval(poll, sections.google.pollMs);
    if (typeof timer.unref === 'function') timer.unref();
    stops.push(() => clearInterval(timer));
  } else if (ctx.config?.listeners?.google) {
    logDecision(ctx, { step: 'connection', connector: 'google', agent: null, reason: 'poll cadence is not configured' });
  }
  return { stop() { for (const fn of stops) fn(); } };
}

module.exports = { dispatch, start, fromSocket, JUDGMENT_MS };
