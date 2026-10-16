#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Store } = require('./store.js');
const { handleEvent } = require('./ingress.js');

const TEAM = 'T1';
const OWNER = 'UOWNER';
const PHONE = '5511911112222';
const MAIL = 'owner@example.com';
const AGENT_MAIL = 'sara@example.com';
const tests = [];

function test(name, fn) { tests.push({ name, fn }); }

function slackId(id) {
  return typeof id === 'string' && /^\d+\.\d+$/.test(id) ? id : '9.424242';
}

function toSlackEvent(event, ctx) {
  const id = event.ts || slackId(event.id);
  const thread = event.threadTs || (event.thread && /^\d+\.\d+$/.test(event.thread) ? event.thread : id);
  const forged = event.identity?.verified && event.identity?.owner ? ctx.config.slack.ownerUserId : (event.from || '');
  return {
    team: event.account && !String(event.account).includes(':') ? event.account : (event.team || TEAM),
    channel: event.conversation || event.group || event.channel || 'D1',
    channelType: event.group ? 'channel' : (event.channelType || 'im'),
    ts: id,
    threadTs: thread,
    user: event.user || forged,
    text: event.text || '',
    files: event.files || [],
    isBotOrSelf: Boolean(event.isSelf || event.isBotOrSelf),
    mentionsBot: Boolean(event.mentionsAgent),
  };
}

function listener() {
  const file = path.join(__dirname, 'listener.js');
  if (!fs.existsSync(file)) return null;
  const mod = require(file);
  return mod && typeof mod.dispatch === 'function' ? mod : null;
}

async function dispatch(event, ctx) {
  const mod = listener();
  if (mod) return mod.dispatch(event, ctx);
  return handleEvent(toSlackEvent(event, ctx), ctx);
}

async function startListeners(ctx) {
  const mod = listener();
  if (mod && typeof mod.start === 'function') return mod.start(ctx);
  try {
    await ctx.transports.slack.connect();
  } catch (error) {
    ctx._seenConnectError = error.message;
  }
}

function harness() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-receive-'));
  const stores = new Map();
  const opened = [];
  function openStore(slug) {
    opened.push(slug);
    if (!stores.has(slug)) stores.set(slug, new Store(path.join(dir, slug, 'state.sqlite')));
    return stores.get(slug);
  }
  const decisionFile = path.join(dir, 'decisions.jsonl');
  const subscriptionFile = path.join(dir, 'subscriptions.json');
  const threadFile = path.join(dir, 'threads.json');
  fs.writeFileSync(subscriptionFile, '[]', 'utf8');
  fs.writeFileSync(threadFile, '[]', 'utf8');
  const judgeCalls = [];
  const sent = [];
  const ctx = {
    config: {
      dmAgent: 'master',
      slack: { team: TEAM, botUserId: 'UBOT', ownerUserId: OWNER },
      routes: { CCHAN: 'probe' },
    },
    openStore,
    slack: { async threadHistory() { return []; } },
    now: () => 1700000000000,
    decisionFile,
    subscriptionFile,
    threadFile,
    defaults: { slackDm: 'master', mail: 'sara', whatsapp: 'master' },
    owners: { slack: OWNER, whatsapp: PHONE, google: MAIL },
    judge: async (question, text) => {
      judgeCalls.push({ question, text });
      if (ctx._judge) return ctx._judge(question, text);
      return { yes: false };
    },
    transports: {
      slack: {
        async connect() { if (ctx._connectError) throw new Error(ctx._connectError); },
        async send(body) { sent.push({ connector: 'slack', body }); },
      },
      whatsapp: { async connect() {}, async send(body) { sent.push({ connector: 'whatsapp', body }); } },
      google: { async connect() {}, async send(body) { sent.push({ connector: 'google', body }); } },
    },
    log() {},
  };
  return {
    dir, stores, opened, ctx, judgeCalls, sent,
    close() {
      for (const store of stores.values()) store.close();
      fs.rmSync(dir, { recursive: true, force: true });
    },
  };
}

function writeJson(file, value) {
  fs.writeFileSync(file, JSON.stringify(value), 'utf8');
}

function decisions(ctx) {
  if (!fs.existsSync(ctx.decisionFile)) return [];
  return fs.readFileSync(ctx.decisionFile, 'utf8').split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function queues(h) {
  const rows = [];
  for (const [slug, store] of h.stores) {
    for (const row of store.db.prepare('SELECT id, kind, conversation_key FROM queue').all()) rows.push({ slug, ...row });
  }
  return rows;
}

function messages(h) {
  const rows = [];
  for (const [slug, store] of h.stores) {
    for (const row of store.db.prepare('SELECT text, role, team, channel, ts, metadata FROM messages').all()) {
      rows.push({ slug, text: row.text, role: row.role, team: row.team, channel: row.channel, ts: row.ts, metadata: JSON.parse(row.metadata) });
    }
  }
  return rows;
}

function gap(gaps, ok, message) {
  if (!ok) gaps.push(message);
}

function finish(gaps) {
  assert.equal(gaps.length, 0, gaps.join(' | '));
}

function ownerSlack(extra = {}) {
  return {
    connector: 'slack', account: TEAM, id: extra.id || '1.100000', at: 1700000000000,
    from: OWNER, group: extra.group ?? null, conversation: extra.conversation || 'D1',
    thread: extra.thread ?? null, text: extra.text || 'hello', files: [], isSelf: false,
    identity: { verified: true, method: 'slack-socket', owner: true },
    ...extra,
  };
}

test('slack-owner-dm-reaches-default-and-is-logged', async () => {
  const h = harness();
  try {
    const result = await dispatch(ownerSlack({ text: 'keep this' }), h.ctx);
    const rows = messages(h);
    const logged = decisions(h.ctx).some((row) => row.step === 'default' && row.agent === 'master' && row.reason);
    const gaps = [];
    gap(gaps, result.agent === 'master' && result.queued === true, `result ${JSON.stringify(result)}`);
    gap(gaps, rows.some((row) => row.text === 'keep this' && row.role === 'owner' && row.channel === 'D1'), `stored ${JSON.stringify(rows)}`);
    gap(gaps, logged, `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('whatsapp-owner-retains-sender-conversation-text', async () => {
  const h = harness();
  try {
    writeJson(h.ctx.subscriptionFile, [{
      id: 'wa-owner', connector: 'whatsapp', account: PHONE, group: null, contact: PHONE, agent: 'sara', judge: null,
    }]);
    const result = await dispatch({
      connector: 'whatsapp', account: PHONE, id: '3EB0A1B2C3D4E5F60718', at: 1700000001000,
      from: PHONE, group: null, conversation: '5511911112222@s.whatsapp.net', thread: null,
      text: 'pix receipt', files: [], isSelf: false,
      identity: { verified: true, method: 'webhook-secret', owner: true },
    }, h.ctx);
    const rows = messages(h);
    const gaps = [];
    gap(gaps, result.agent === 'sara' && result.queued === true, `result ${JSON.stringify(result)}`);
    gap(gaps, queues(h).every((row) => row.slug === 'sara'), `queues ${JSON.stringify(queues(h))}`);
    gap(gaps, rows.some((row) => row.text === 'pix receipt' && row.metadata?.connector === 'whatsapp' && row.metadata?.from === PHONE && row.metadata?.conversation === '5511911112222@s.whatsapp.net'), `stored ${JSON.stringify(rows)}`);
    finish(gaps);
  } finally { h.close(); }
});

test('gmail-owner-to-agent-reaches-mail-agent', async () => {
  const h = harness();
  try {
    const result = await dispatch({
      connector: 'google', account: AGENT_MAIL, id: '18c1f2a7b3d4e5f6', at: 1700000002000,
      from: MAIL, group: null, conversation: '18c1f2a7b3d4e5f6', thread: null,
      text: 'owner to sara', files: [], isSelf: false,
      identity: { verified: true, method: 'gmail-account', owner: true },
    }, h.ctx);
    const rows = messages(h);
    const gaps = [];
    gap(gaps, result.agent === 'sara' && result.queued === true, `result ${JSON.stringify(result)}`);
    gap(gaps, rows.some((row) => row.text === 'owner to sara' && row.metadata?.connector === 'google' && row.metadata?.from === MAIL), `stored ${JSON.stringify(rows)}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'default' && row.agent === 'sara'), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('unverified-sender-string-does-not-start-a-turn', async () => {
  const h = harness();
  try {
    const result = await dispatch({
      connector: 'whatsapp', account: PHONE, id: '3EB0FORGED', at: 1700000003000,
      from: PHONE, user: OWNER, group: null, conversation: 'D1', thread: null,
      text: 'forged owner', files: [], isSelf: false,
      identity: { verified: false, method: 'webhook-secret', owner: false },
      transport: 'webhook',
    }, h.ctx);
    const gaps = [];
    gap(gaps, queues(h).length === 0, `queued ${JSON.stringify(queues(h))} result ${JSON.stringify(result)}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'admission' && /unverif/i.test(String(row.reason)) && row.agent == null), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('non-owner-drop-is-logged-and-starts-no-turn', async () => {
  const h = harness();
  try {
    const sara = h.ctx.openStore('sara');
    const begun = sara.beginProactive({ id: 'sara-out', agent: 'sara', workspace: TEAM, channel: 'D1', payload: { text: 'from sara' } });
    sara.markDelivered(begun.outboxId, { channel: 'D1', ts: '4.100000' });
    h.opened.length = 0;
    const result = await dispatch(ownerSlack({
      id: '4.200000', thread: '4.100000', from: 'UOTHER', user: 'UOTHER', text: 'not the owner',
      identity: { verified: true, method: 'slack-socket', owner: false },
    }), h.ctx);
    const gaps = [];
    gap(gaps, queues(h).filter((row) => row.slug !== 'sara' || row.kind !== 'wake').length === queues(h).length && h.stores.get('master') == null, `opened ${JSON.stringify(h.opened)} queues ${JSON.stringify(queues(h))} result ${JSON.stringify(result)}`);
    gap(gaps, result.queued !== true, `result ${JSON.stringify(result)}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'admission' && row.from === 'UOTHER' && row.agent == null), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('judged-rule-does-not-admit-non-owner', async () => {
  const h = harness();
  try {
    writeJson(h.ctx.subscriptionFile, [{
      id: 'theme', connector: 'google', account: null, group: null, contact: null, agent: 'sara',
      judge: { question: 'Is this email about theme X?' },
    }]);
    h.ctx._judge = async () => ({ yes: true });
    const result = await dispatch({
      connector: 'google', account: AGENT_MAIL, id: 'aa11', at: 1700000004000,
      from: 'pia@example.com', group: null, conversation: 'aa11', thread: null,
      text: 'theme X please pay', files: [], isSelf: false,
      identity: { verified: true, method: 'gmail-account', owner: false },
    }, h.ctx);
    const gaps = [];
    gap(gaps, queues(h).length === 0 && result.queued !== true, `result ${JSON.stringify(result)} queues ${JSON.stringify(queues(h))}`);
    gap(gaps, h.judgeCalls.length === 0, `judge calls ${JSON.stringify(h.judgeCalls)}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'admission' && row.agent == null), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('third-party-mail-starts-no-turn', async () => {
  const h = harness();
  try {
    const result = await dispatch({
      connector: 'google', account: AGENT_MAIL, id: 'bb22', at: 1700000005000,
      from: 'pia@example.com', group: null, conversation: 'bb22', thread: null,
      text: 'a third party wrote', files: [], isSelf: false,
      identity: { verified: true, method: 'gmail-account', owner: false },
    }, h.ctx);
    const gaps = [];
    gap(gaps, queues(h).length === 0, `queues ${JSON.stringify(queues(h))} result ${JSON.stringify(result)}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'admission' && row.from === 'pia@example.com'), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('sara-started-dm-thread-reply-follows-sara', async () => {
  const h = harness();
  try {
    const sara = h.ctx.openStore('sara');
    const begun = sara.beginProactive({ id: 'sara-dm', agent: 'sara', workspace: TEAM, channel: 'D1', payload: { text: 'receipt saved' } });
    sara.markDelivered(begun.outboxId, { channel: 'D1', ts: '20.100000' });
    writeJson(h.ctx.subscriptionFile, [{
      id: 'dm-gaming', connector: 'slack', account: TEAM, group: null, contact: OWNER, agent: 'gaming', judge: null,
    }]);
    const result = await dispatch(ownerSlack({ id: '20.200000', thread: '20.100000', text: 'thanks sara' }), h.ctx);
    const gaps = [];
    gap(gaps, result.agent === 'sara' && result.queued === true, `result ${JSON.stringify(result)}`);
    gap(gaps, queues(h).some((row) => row.slug === 'sara') && !queues(h).some((row) => row.slug === 'master' || row.slug === 'gaming'), `queues ${JSON.stringify(queues(h))}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'affinity' && row.agent === 'sara'), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('message-send-thread-reply-follows-starter', async () => {
  const h = harness();
  try {
    writeJson(h.ctx.threadFile, [{
      connector: 'slack', account: TEAM, conversation: 'D1', thread: '30.100000', agent: 'sara', via: 'message-send',
    }]);
    const result = await dispatch(ownerSlack({ id: '30.200000', thread: '30.100000', text: 'reply to send' }), h.ctx);
    const gaps = [];
    gap(gaps, result.agent === 'sara' && result.queued === true, `result ${JSON.stringify(result)}`);
    gap(gaps, !queues(h).some((row) => row.slug === 'master'), `queues ${JSON.stringify(queues(h))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('most-specific-subscription-wins', async () => {
  const h = harness();
  try {
    writeJson(h.ctx.subscriptionFile, [
      { id: 'group', connector: 'slack', account: TEAM, group: 'CCHAN', contact: null, agent: 'probe', judge: null },
      { id: 'contact-group', connector: 'slack', account: TEAM, group: 'CCHAN', contact: OWNER, agent: 'gaming', judge: null },
    ]);
    const result = await dispatch(ownerSlack({
      id: '6.100000', group: 'CCHAN', conversation: 'CCHAN', channelType: 'channel', text: 'in channel',
    }), h.ctx);
    const gaps = [];
    gap(gaps, result.agent === 'gaming' && result.queued === true, `result ${JSON.stringify(result)}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'subscription' && row.agent === 'gaming' && row.reason), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('equal-specificity-tie-starts-no-turn', async () => {
  const h = harness();
  try {
    writeJson(h.ctx.subscriptionFile, [
      { id: 'a', connector: 'slack', account: TEAM, group: 'CCHAN', contact: null, agent: 'sara', judge: null },
      { id: 'b', connector: 'slack', account: TEAM, group: 'CCHAN', contact: null, agent: 'gaming', judge: null },
    ]);
    h.ctx._judge = async () => ({ yes: true });
    const result = await dispatch(ownerSlack({
      id: '7.100000', group: 'CCHAN', conversation: 'CCHAN', text: 'tied',
    }), h.ctx);
    const gaps = [];
    gap(gaps, queues(h).length === 0 && result.queued !== true, `result ${JSON.stringify(result)} queues ${JSON.stringify(queues(h))}`);
    gap(gaps, h.judgeCalls.length === 0, `judge calls ${JSON.stringify(h.judgeCalls)}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'subscription' && row.reason === 'tie' && row.agent == null), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('judged-subscription-routes-when-no-deterministic-match', async () => {
  const h = harness();
  try {
    writeJson(h.ctx.subscriptionFile, [{
      id: 'theme', connector: 'google', account: AGENT_MAIL, group: null, contact: null, agent: 'gaming',
      judge: { question: 'Is this email about theme X?' },
    }]);
    h.ctx._judge = async () => ({ yes: true });
    const result = await dispatch({
      connector: 'google', account: AGENT_MAIL, id: 'cc33', at: 1700000006000,
      from: MAIL, group: null, conversation: 'cc33', thread: null, text: 'theme X notes', files: [], isSelf: false,
      identity: { verified: true, method: 'gmail-account', owner: true },
    }, h.ctx);
    const gaps = [];
    gap(gaps, result.agent === 'gaming' && result.queued === true, `result ${JSON.stringify(result)}`);
    gap(gaps, h.judgeCalls.length === 1 && h.judgeCalls[0].text === 'theme X notes', `judge ${JSON.stringify(h.judgeCalls)}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'judged' && row.agent === 'gaming'), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('judgment-error-starts-no-turn', async () => {
  const h = harness();
  try {
    writeJson(h.ctx.subscriptionFile, [{
      id: 'theme', connector: 'google', account: AGENT_MAIL, group: null, contact: null, agent: 'gaming',
      judge: { question: 'Is this email about theme X?' },
    }]);
    h.ctx._judge = async () => { throw new Error('timeout'); };
    const result = await dispatch({
      connector: 'google', account: AGENT_MAIL, id: 'dd44', at: 1700000007000,
      from: MAIL, group: null, conversation: 'dd44', thread: null, text: 'maybe theme', files: [], isSelf: false,
      identity: { verified: true, method: 'gmail-account', owner: true },
    }, h.ctx);
    const gaps = [];
    gap(gaps, queues(h).length === 0 && result.queued !== true, `result ${JSON.stringify(result)} queues ${JSON.stringify(queues(h))}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'judged' && row.reason === 'judgment-error' && row.agent == null), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('judge-no-falls-through-to-default', async () => {
  const h = harness();
  try {
    writeJson(h.ctx.subscriptionFile, [{
      id: 'theme', connector: 'google', account: AGENT_MAIL, group: null, contact: null, agent: 'gaming',
      judge: { question: 'Is this email about theme X?' },
    }]);
    h.ctx._judge = async () => ({ yes: false });
    const result = await dispatch({
      connector: 'google', account: AGENT_MAIL, id: 'ee55', at: 1700000008000,
      from: MAIL, group: null, conversation: 'ee55', thread: null, text: 'unrelated', files: [], isSelf: false,
      identity: { verified: true, method: 'gmail-account', owner: true },
    }, h.ctx);
    const gaps = [];
    gap(gaps, result.agent === 'sara' && result.queued === true, `result ${JSON.stringify(result)}`);
    gap(gaps, h.judgeCalls.length === 1, `judge ${JSON.stringify(h.judgeCalls)}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'default' && row.agent === 'sara'), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('slack-redelivery-one-queue', async () => {
  const h = harness();
  try {
    const event = ownerSlack({ id: '8.100000', text: 'once' });
    const first = await dispatch(event, h.ctx);
    const second = await dispatch(event, h.ctx);
    const gaps = [];
    gap(gaps, first.queued === true && second.queued !== true, `first ${JSON.stringify(first)} second ${JSON.stringify(second)}`);
    gap(gaps, queues(h).length === 1, `queues ${JSON.stringify(queues(h))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('reopen-redelivery-one-queue', async () => {
  const h = harness();
  try {
    const event = ownerSlack({ id: '8.200000', text: 'restart' });
    const first = await dispatch(event, h.ctx);
    for (const store of h.stores.values()) store.close();
    h.stores.clear();
    const second = await dispatch(event, h.ctx);
    const gaps = [];
    gap(gaps, first.queued === true && second.queued !== true, `first ${JSON.stringify(first)} second ${JSON.stringify(second)}`);
    gap(gaps, queues(h).length === 1, `queues ${JSON.stringify(queues(h))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('colliding-native-ids-stay-distinct', async () => {
  const h = harness();
  try {
    const slack = await dispatch(ownerSlack({ id: '111.111000', text: 'slack-collide' }), h.ctx);
    const whatsapp = await dispatch({
      connector: 'whatsapp', account: '5511999990000', id: '111.111000', at: 1700000009000,
      from: PHONE, group: null, conversation: '5511999990000@s.whatsapp.net', thread: null,
      text: 'wa-collide', files: [], isSelf: false,
      identity: { verified: true, method: 'webhook-secret', owner: true },
    }, h.ctx);
    const rows = messages(h);
    const gaps = [];
    gap(gaps, slack.queued === true && whatsapp.queued === true, `slack ${JSON.stringify(slack)} wa ${JSON.stringify(whatsapp)}`);
    gap(gaps, rows.filter((row) => row.text === 'slack-collide').length === 1 && rows.filter((row) => row.text === 'wa-collide').length === 1, `stored ${JSON.stringify(rows)}`);
    gap(gaps, rows.some((row) => row.text === 'wa-collide' && row.metadata?.connector === 'whatsapp') && rows.some((row) => row.text === 'slack-collide' && row.metadata?.connector === 'slack'), `identity ${JSON.stringify(rows)}`);
    finish(gaps);
  } finally { h.close(); }
});

test('subscription-file-survives-reopen-and-routes', async () => {
  const h = harness();
  try {
    writeJson(h.ctx.subscriptionFile, [{
      id: 'kept', connector: 'slack', account: TEAM, group: 'CCHAN', contact: OWNER, agent: 'gaming', judge: null,
    }]);
    const raw = fs.readFileSync(h.ctx.subscriptionFile, 'utf8');
    const again = fs.readFileSync(h.ctx.subscriptionFile, 'utf8');
    const result = await dispatch(ownerSlack({
      id: '9.100000', group: 'CCHAN', conversation: 'CCHAN', text: 'after reopen',
    }), h.ctx);
    const gaps = [];
    gap(gaps, raw === again && JSON.parse(again)[0].agent === 'gaming', `file ${again}`);
    gap(gaps, result.agent === 'gaming', `result ${JSON.stringify(result)} file ${again}`);
    finish(gaps);
  } finally { h.close(); }
});

test('connection-failure-is-logged', async () => {
  const h = harness();
  try {
    h.ctx._connectError = 'socket refused';
    await startListeners(h.ctx);
    const gaps = [];
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'connection' && row.connector === 'slack' && /refused|socket/i.test(String(row.reason))), `seen ${h.ctx._seenConnectError || 'none'}; decisions ${JSON.stringify(decisions(h.ctx))}`);
    gap(gaps, queues(h).length === 0, `queues ${JSON.stringify(queues(h))}`);
    finish(gaps);
  } finally { h.close(); }
});

test('self-message-is-not-sent-again', async () => {
  const h = harness();
  try {
    const result = await dispatch(ownerSlack({ id: '10.100000', text: 'echo', isSelf: true, identity: { verified: true, method: 'slack-socket', owner: true } }), h.ctx);
    const gaps = [];
    gap(gaps, queues(h).length === 0 && result.queued !== true, `result ${JSON.stringify(result)} queues ${JSON.stringify(queues(h))}`);
    gap(gaps, h.sent.length === 0, `sent ${JSON.stringify(h.sent)}`);
    gap(gaps, decisions(h.ctx).some((row) => row.step === 'self' && row.agent == null), `decisions ${JSON.stringify(decisions(h.ctx))}`);
    finish(gaps);
  } finally { h.close(); }
});

(async () => {
  let failed = 0;
  for (const { name, fn } of tests) {
    try {
      await fn();
      process.stdout.write(`PASS ${name}\n`);
    } catch (error) {
      failed += 1;
      process.stdout.write(`FAIL ${name}: ${error.stack || error.message}\n`);
    }
  }
  process.stdout.write(`message-receive: ${tests.length - failed} passed, ${failed} failed\n`);
  process.exit(failed ? 1 : 0);
})();
