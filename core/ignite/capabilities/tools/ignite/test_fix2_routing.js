#!/usr/bin/env node
'use strict';

// Phase 3a fix2, routing/recovery/provenance lane. Every test drives the production
// listener.dispatch/listener.start with real per-agent Store databases, the real WhatsApp
// receiver for the signed wire where a quote arrives, and the production history/prompt
// renderers. Service endpoints are loopback or direct neutral events; no parser or adapter
// under test is replaced.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { Store } = require('./store.js');
const { dispatch, start, fromSocket } = require('./listener.js');
const { handleEvent } = require('./ingress.js');
const { composeTurn } = require('./prompt.js');
const { writeHistory } = require('./history.js');
const wa = require('../../../../../connectors/whatsapp/capabilities/tools/whatsapp/lib/messaging.js');

const INGRESS_LIMIT = 20_000;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function harness({ listeners = undefined } = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-routing-'));
  const stores = new Map();
  const config = {
    workspace: dir,
    dmAgent: 'master',
    slack: { team: 'T1', ownerUserId: 'UOWNER' },
    routes: {},
    ...(listeners === undefined ? {} : { listeners }),
  };
  const ctx = {
    config,
    defaults: { slackDm: 'master', mail: 'sara', whatsapp: 'master' },
    subscriptionFile: path.join(dir, 'subscriptions.json'),
    threadFile: path.join(dir, 'threads.json'),
    decisionFile: path.join(dir, 'decisions.jsonl'),
    openStore(slug) {
      if (!stores.has(slug)) stores.set(slug, new Store(path.join(dir, slug, 'state.sqlite')));
      return stores.get(slug);
    },
    agentSlugs: () => ['master', 'sara', 'gaming'],
    slack: { threadHistory: async () => [] },
    judge: async () => ({ yes: false }),
  };
  fs.writeFileSync(ctx.subscriptionFile, '[]');
  return {
    dir, ctx, stores,
    rules(rows) { fs.writeFileSync(ctx.subscriptionFile, JSON.stringify(rows)); },
    ingress() {
      const file = path.join(dir, 'ingress.json');
      return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : { accepted: {} };
    },
    hold() {
      const file = `${ctx.decisionFile}.hold`;
      return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : [];
    },
    queues() {
      const out = {};
      for (const [slug, store] of stores) out[slug] = store.db.prepare('SELECT COUNT(*) AS n FROM queue').get().n;
      return out;
    },
    // The evidence scan opens every candidate agent's store, so empty stores exist; compare the
    // queues that hold work.
    nonzero() {
      return Object.fromEntries(Object.entries(this.queues()).filter(([, n]) => n > 0));
    },
    close() {
      for (const store of stores.values()) store.close();
      fs.rmSync(dir, { recursive: true, force: true });
    },
  };
}

function slackOwner(extra = {}) {
  return {
    connector: 'slack', account: 'T1', id: '1.1', at: 1792195200000, from: 'UOWNER', group: null,
    conversation: 'D1', thread: null, text: 'hello', files: [], isSelf: false,
    identity: { verified: true, method: 'slack-socket', owner: true }, ...extra,
  };
}

function waEvent(id, thread, extra = {}) {
  return {
    connector: 'whatsapp', account: '15550000001', conversation: '15550000002@s.whatsapp.net',
    id, thread: thread ?? null, from: '15550000002', text: id, files: [], isSelf: false,
    identity: { verified: true, method: 'webhook-secret', owner: true }, ...extra,
  };
}

function decisions(ctx) {
  if (!fs.existsSync(ctx.decisionFile)) return [];
  return fs.readFileSync(ctx.decisionFile, 'utf8').split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

// F1 — a due held event retries through the production scheduler when the config names no
// listener at all (the live config today), without any Gmail poll, without a manual replay
// or an edited deadline.
test('scheduler retries a due held event with no listeners section', { timeout: 20_000 }, async () => {
  const h = harness();
  try {
    h.rules([{ id: 'judge', connector: 'slack', account: 'T1', agent: 'gaming', judge: { question: 'urgent?' } }]);
    h.ctx.judge = async () => { throw new Error('typesafe down'); };
    const held = await dispatch(slackOwner(), h.ctx);
    assert.equal(held.ignored, 'judgment-error');
    h.ctx.judge = async () => ({ yes: true });
    const session = await start(h.ctx);
    try {
      let queued = 0;
      for (let i = 0; i < 60 && queued === 0; i += 1) {
        await sleep(100);
        queued = h.queues().gaming || 0;
      }
      assert.equal(queued, 1, `gaming queue after scheduler: ${JSON.stringify(h.queues())}`);
      assert.equal(h.queues().master || 0, 0);
      assert.equal(h.hold().length, 0, 'a replayed event leaves the hold file');
    } finally {
      await session.stop();
    }
    // The stopped scheduler retries nothing further.
    h.ctx.judge = async () => { throw new Error('down again'); };
    await dispatch(slackOwner({ id: '2.2', text: 'second' }), h.ctx);
    await sleep(2600);
    assert.equal(h.queues().gaming, 1, `no retry after stop: ${JSON.stringify(h.queues())}`);
  } finally { h.close(); }
});

// F1 — same guarantee when a listeners section exists but no Google poll is configured.
test('scheduler retries a due held event with listeners but no google poll', { timeout: 20_000 }, async () => {
  const h = harness({ listeners: {} });
  try {
    h.rules([{ id: 'judge', connector: 'slack', account: 'T1', agent: 'gaming', judge: { question: 'urgent?' } }]);
    h.ctx.judge = async () => { throw new Error('typesafe down'); };
    await dispatch(slackOwner({ id: '5.5', text: 'hold' }), h.ctx);
    h.ctx.judge = async () => ({ yes: true });
    const session = await start(h.ctx);
    try {
      let queued = 0;
      for (let i = 0; i < 60 && queued === 0; i += 1) {
        await sleep(100);
        queued = h.queues().gaming || 0;
      }
      assert.equal(queued, 1, `gaming queue after scheduler: ${JSON.stringify(h.queues())}`);
    } finally {
      await session.stop();
    }
  } finally { h.close(); }
});

// F1 — an orderly stop drains the replay in flight: the turn the scheduler was queueing is
// committed before stop() resolves.
test('stop drains an in-flight replay before resolving', { timeout: 20_000 }, async () => {
  const h = harness({ listeners: {} });
  try {
    h.rules([{ id: 'judge', connector: 'slack', account: 'T1', agent: 'gaming', judge: { question: 'urgent?' } }]);
    h.ctx.judge = async () => { throw new Error('down'); };
    const session = await start(h.ctx);
    try {
      await dispatch(slackOwner({ id: '7.7', text: 'hold' }), h.ctx);
      let judgeStarted;
      const started = new Promise((resolve) => { judgeStarted = resolve; });
      h.ctx.judge = async () => { judgeStarted(); await sleep(300); return { yes: true }; };
      await Promise.race([started, sleep(6000)]);
      await session.stop();
      assert.equal(h.queues().gaming || 0, 1, `in-flight replay committed before stop resolved: ${JSON.stringify(h.queues())}`);
    } finally {
      await session.stop();
    }
  } finally { h.close(); }
});

// F4 — a binding write failure after the queue commit leaves a reservation; the retry keeps
// the first agent even after a rule change, instead of queueing a second agent.
test('binding write failure after queue commit keeps one agent on retry', async () => {
  const h = harness();
  try {
    fs.writeFileSync(`${h.ctx.threadFile}.lock`, 'held');
    let error;
    try { await dispatch(slackOwner(), h.ctx); } catch (e) { error = e.message; }
    assert.match(String(error), /busy/);
    assert.deepEqual(h.nonzero(), { master: 1 }, 'the queue commit survived the binding failure');
    fs.unlinkSync(`${h.ctx.threadFile}.lock`);
    h.rules([{ id: 'gaming', connector: 'slack', account: 'T1', agent: 'gaming', judge: null }]);
    const retry = await dispatch(slackOwner(), h.ctx);
    assert.equal(retry.queued, false);
    assert.equal(retry.ignored, 'duplicate');
    assert.equal(retry.agent, 'master');
    assert.deepEqual(h.nonzero(), { master: 1 });
    const fresh = await dispatch(slackOwner({ id: '3.3', text: 'new' }), h.ctx);
    assert.equal(fresh.agent, 'gaming', 'later events still follow the changed rules');
    assert.deepEqual(h.nonzero(), { master: 1, gaming: 1 });
  } finally { h.close(); }
});

// F4 — the real crash gap: a process interrupted right after the queue commit, before the
// ledger and affinity writes. The same event retried under new rules must not start a second
// agent's turn.
test('process crash after queue commit recovers to the same agent', async () => {
  const h = harness();
  const script = path.join(h.dir, 'crash.js');
  fs.writeFileSync(script, `'use strict';
const { dispatch } = require(${JSON.stringify(path.join(__dirname, 'listener.js'))});
const { Store } = require(${JSON.stringify(path.join(__dirname, 'store.js'))});
const store = new Store(${JSON.stringify(path.join(h.dir, 'master', 'state.sqlite'))});
const real = store.acceptOwnerInput.bind(store);
store.acceptOwnerInput = async (input) => {
  const result = await real(input);
  if (!result.duplicate) process.exit(9); // interrupted right after the queue commit
  return result;
};
dispatch(${JSON.stringify(slackOwner())}, {
  config: ${JSON.stringify(h.ctx.config)},
  defaults: ${JSON.stringify(h.ctx.defaults)},
  subscriptionFile: ${JSON.stringify(h.ctx.subscriptionFile)},
  threadFile: ${JSON.stringify(h.ctx.threadFile)},
  decisionFile: ${JSON.stringify(h.ctx.decisionFile)},
  openStore: () => store,
}).catch(() => {});
`);
  try {
    const crashed = spawnSync(process.execPath, [script], { encoding: 'utf8' });
    assert.equal(crashed.status, 9, `child was interrupted after commit: ${crashed.stderr}`);
    h.ctx.openStore('master'); // the crashed child held the store; the queue commit is on disk
    assert.deepEqual(h.nonzero(), { master: 1 });
    h.rules([{ id: 'gaming', connector: 'slack', account: 'T1', agent: 'gaming', judge: null }]);
    const retry = await dispatch(slackOwner(), h.ctx);
    assert.equal(retry.queued, false);
    assert.equal(retry.agent, 'master', `retry after crash keeps master: ${JSON.stringify(retry)}`);
    assert.deepEqual(h.nonzero(), { master: 1 });
    const reply = await dispatch(slackOwner({ id: '2.1', thread: '1.1', text: 'reply' }), h.ctx);
    assert.equal(reply.agent, 'master');
    assert.deepEqual(h.nonzero(), { master: 2 });
  } finally { h.close(); }
});

// F4 — legacy Slack input stored by the pre-migration ingress path: deduped on its original
// agent, with durable affinity and identity backfilled, so a rule change cannot duplicate it.
test('legacy slack events dedup and backfill affinity and identity', async () => {
  const h = harness();
  try {
    const raw = { team: 'T1', channel: 'D1', channelType: 'im', ts: '1.1', user: 'UOWNER', text: 'legacy' };
    const first = await handleEvent(raw, h.ctx);
    assert.equal(first.queued, true);
    assert.equal(first.agent, 'master');
    const same = await dispatch(slackOwner(), h.ctx);
    assert.equal(same.queued, false);
    assert.equal(same.agent, 'master');
    const threads = JSON.parse(fs.readFileSync(h.ctx.threadFile, 'utf8'));
    assert.equal(threads.some((row) => row.connector === 'slack' && row.account === 'T1'
      && row.conversation === 'D1' && row.thread === '1.1' && row.agent === 'master'), true, `backfilled affinity: ${JSON.stringify(threads)}`);
    assert.equal(h.ingress().accepted['slack:T1:D1:1.1']?.agent, 'master', 'backfilled identity ledger');
    h.rules([{ id: 'gaming', connector: 'slack', account: 'T1', agent: 'gaming', judge: null }]);
    const changed = await dispatch(slackOwner(), h.ctx);
    assert.equal(changed.queued, false);
    assert.equal(changed.agent, 'master');
    const reply = await dispatch(slackOwner({ id: '2.1', thread: '1.1', text: 'reply' }), h.ctx);
    assert.equal(reply.agent, 'master');
    assert.deepEqual(h.nonzero(), { master: 2 }, `the legacy root once, the new reply once, no duplicate turn: ${JSON.stringify(h.queues())}`);
  } finally { h.close(); }
});

// F4 — a redelivery that arrives while the first accept is still committing sees the durable
// reservation and recovers with the same agent; the rules changing mid-flight cannot queue a
// second agent.
test('a redelivery racing the first accept keeps one agent', async () => {
  const h = harness();
  try {
    const openStore = h.ctx.openStore.bind(h.ctx);
    let armSlow = true;
    h.ctx.openStore = (slug) => {
      const store = openStore(slug);
      if (slug === 'master' && armSlow) {
        armSlow = false;
        const real = store.acceptOwnerInput.bind(store);
        store.acceptOwnerInput = async (input) => { await sleep(120); return real(input); };
      }
      return store;
    };
    const first = dispatch(slackOwner({ id: '6.1', text: 'race' }), h.ctx);
    let reserved = null;
    for (let i = 0; i < 100 && !reserved; i += 1) {
      await sleep(20);
      reserved = h.ingress().accepted['slack:T1:D1:6.1'];
    }
    assert.equal(reserved?.state, 'reserved', 'the routing decision is durable before the queue commit');
    h.rules([{ id: 'gaming', connector: 'slack', account: 'T1', agent: 'gaming', judge: null }]);
    const second = await dispatch(slackOwner({ id: '6.1', text: 'race' }), h.ctx);
    const done = await first;
    assert.equal(second.queued, false, `the redelivery recovers the reserved agent: ${JSON.stringify(second)}`);
    assert.equal(second.agent, 'master');
    assert.equal(done.agent, 'master');
    assert.deepEqual(h.nonzero(), { master: 1 }, `one queue for one event: ${JSON.stringify(h.queues())}`);
  } finally { h.close(); }
});

// F4 — a process interrupted after the reservation but before the queue commit: the retry
// completes the accept with the reserved agent under new rules, not with a second agent.
test('a crash after the reservation recovers with the reserved agent', async () => {
  const h = harness();
  const script = path.join(h.dir, 'crash-before-commit.js');
  fs.writeFileSync(script, `'use strict';
const { dispatch } = require(${JSON.stringify(path.join(__dirname, 'listener.js'))});
const { Store } = require(${JSON.stringify(path.join(__dirname, 'store.js'))});
const store = new Store(${JSON.stringify(path.join(h.dir, 'master', 'state.sqlite'))});
store.acceptOwnerInput = async () => { process.exit(9); }; // interrupted before the commit
dispatch(${JSON.stringify(slackOwner({ id: '6.2', text: 'reserve then crash' }))}, {
  config: ${JSON.stringify(h.ctx.config)},
  defaults: ${JSON.stringify(h.ctx.defaults)},
  subscriptionFile: ${JSON.stringify(h.ctx.subscriptionFile)},
  threadFile: ${JSON.stringify(h.ctx.threadFile)},
  decisionFile: ${JSON.stringify(h.ctx.decisionFile)},
  openStore: () => store,
}).catch(() => {});
`);
  try {
    const crashed = spawnSync(process.execPath, [script], { encoding: 'utf8' });
    assert.equal(crashed.status, 9, `child was interrupted before commit: ${crashed.stderr}`);
    const reserved = h.ingress().accepted['slack:T1:D1:6.2'];
    assert.equal(reserved?.agent, 'master');
    assert.equal(reserved?.state, 'reserved');
    h.ctx.openStore('master');
    assert.deepEqual(h.nonzero(), {}, 'nothing was committed');
    h.rules([{ id: 'gaming', connector: 'slack', account: 'T1', agent: 'gaming', judge: null }]);
    const retry = await dispatch(slackOwner({ id: '6.2', text: 'reserve then crash' }), h.ctx);
    assert.equal(retry.queued, true, `the retry completes the reserved accept: ${JSON.stringify(retry)}`);
    assert.equal(retry.agent, 'master');
    assert.deepEqual(h.nonzero(), { master: 1 });
  } finally { h.close(); }
});

// F4 — quoting an intermediate reply follows the conversation's original agent and root, not
// just the root id. The quote arrives through the real signed wacli wire receiver.
test('quoting an intermediate reply follows the original agent', { timeout: 15_000 }, async () => {
  const h = harness();
  let listening;
  try {
    const seen = [];
    listening = await wa.listen({
      secret: 'fixture', account: '15550000001', owner: '15550000002', port: 0,
      onEvent: (event) => seen.push(dispatch(event, h.ctx)),
    });
    const post = (payload) => new Promise((resolve, reject) => {
      const body = Buffer.from(JSON.stringify(payload));
      const req = require('node:http').request({
        host: '127.0.0.1', port: listening.port, path: '/whatsapp', method: 'POST',
        headers: { [wa.HEADER]: wa.signature('fixture', body), 'content-length': body.length },
      }, (res) => { res.resume(); res.on('end', () => resolve(res.statusCode)); });
      req.on('error', reject);
      req.end(body);
    });
    const wire = (id, replyTo) => ({ Chat: '15550000002@s.whatsapp.net', ID: id, SenderJID: '15550000002@s.whatsapp.net', Text: id, Timestamp: '2026-10-17T00:00:00Z', ReplyToID: replyTo || '', FromMe: false });
    assert.equal(await post(wire('root')), 200);
    await Promise.all(seen.splice(0));
    assert.equal(await post(wire('reply', 'root')), 200);
    await Promise.all(seen.splice(0));
    h.rules([{ id: 'gaming', connector: 'whatsapp', account: '15550000001', agent: 'gaming', judge: null }]);
    assert.equal(await post(wire('reply2', 'reply')), 200);
    const [quoted] = await Promise.all(seen.splice(0));
    assert.equal(quoted.agent, 'master', `a quote of the reply follows the original agent: ${JSON.stringify(quoted)}`);
    assert.equal(quoted.key, 'whatsapp:15550000001:15550000002@s.whatsapp.net:root', `the quote stays on the root conversation: ${JSON.stringify(quoted)}`);
    const threads = JSON.parse(fs.readFileSync(h.ctx.threadFile, 'utf8'));
    assert.equal(threads.some((row) => row.connector === 'whatsapp' && row.account === '15550000001'
      && row.conversation === '15550000002@s.whatsapp.net' && row.thread === 'reply'
      && row.root === 'root' && row.agent === 'master'), true, `the intermediate reply id is bound to the root: ${JSON.stringify(threads)}`);
    assert.deepEqual(h.nonzero(), { master: 3 });
  } finally {
    if (listening) await listening.close();
    h.close();
  }
});

// F4 — with no thread binding file at all (a store from before the listener kept one), a quote
// resolves its agent and its conversation's root from the stored messages alone.
test('a quote resolves its conversation root from stored messages alone', async () => {
  const h = harness();
  try {
    const chat = '15550000002@s.whatsapp.net';
    const store = h.ctx.openStore('master');
    const key = 'whatsapp:15550000001:' + chat + ':root';
    store.upsertConversation({ key, agent: 'master', workspace: '15550000001', channel: chat, rootTs: 'root' });
    for (const [id, text] of [['root', 'root text'], ['reply', 'reply text']]) {
      store.recordMessage(key, {
        id: `whatsapp:15550000001:${chat}:${id}`, role: 'owner', text, team: '15550000001',
        channel: chat, ts: id, createdAt: 1792195200000,
        metadata: { connector: 'whatsapp', account: '15550000001', conversation: chat, thread: id === 'reply' ? 'root' : null },
      });
    }
    h.rules([{ id: 'gaming', connector: 'whatsapp', account: '15550000001', agent: 'gaming', judge: null }]);
    const quoted = await dispatch(waEvent('reply2', 'reply'), h.ctx);
    assert.equal(quoted.agent, 'master', `the stored reply's conversation owns the quote: ${JSON.stringify(quoted)}`);
    assert.equal(quoted.key, key, `the quote lands on the stored root conversation: ${JSON.stringify(quoted)}`);
    assert.deepEqual(h.nonzero(), { master: 1 });
  } finally { h.close(); }
});

// F4 — when the identity ledger evicts its oldest entries past the 20,000 bound, the stored
// message identity still dedups the event instead of reaccepting it under new rules.
test('evicted ingress identity is still deduped by store evidence', async () => {
  const h = harness();
  try {
    const first = await dispatch(slackOwner({ id: '9.9', text: 'old retry' }), h.ctx);
    assert.equal(first.agent, 'master');
    const file = path.join(h.dir, 'ingress.json');
    const body = h.ingress();
    const ours = 'slack:T1:D1:9.9';
    for (let i = 0; i < INGRESS_LIMIT; i += 1) body.accepted[`slack:T1:D1:dummy-${i}`] = { agent: 'master', at: 1792195200000 + i };
    fs.writeFileSync(file, JSON.stringify(body));
    // One more accept runs the eviction: the oldest identity (ours) is dropped from the ledger.
    await dispatch(slackOwner({ id: '8.8', text: 'newer' }), h.ctx);
    const after = JSON.parse(fs.readFileSync(file, 'utf8'));
    assert.equal(Object.keys(after.accepted).length, INGRESS_LIMIT, 'the ledger keeps its bound');
    assert.equal(after.accepted[ours] === undefined, true, 'our identity was the one evicted');
    h.rules([{ id: 'gaming', connector: 'slack', account: 'T1', agent: 'gaming', judge: null }]);
    const retry = await dispatch(slackOwner({ id: '9.9', text: 'old retry' }), h.ctx);
    assert.equal(retry.queued, false, `an evicted identity is not reaccepted: ${JSON.stringify(retry)}`);
    assert.equal(retry.agent, 'master');
    assert.equal(h.queues().master, 2);
    assert.equal(h.queues().gaming || 0, 0);
  } finally { h.close(); }
});

// F7 — a corrupt recovery cache holds and logs instead of throwing after the socket ACK.
test('invalid last-good cache holds the event instead of throwing', async () => {
  const h = harness();
  try {
    fs.writeFileSync(h.ctx.subscriptionFile, '{');
    fs.writeFileSync(path.join(h.dir, 'subscriptions.last-good.json'), '[null]');
    const result = await dispatch(slackOwner({ id: '4.4', text: 'not lost' }), h.ctx);
    assert.equal(result.queued, false);
    assert.equal(result.ignored, 'subscriptions-invalid');
    const held = h.hold();
    assert.equal(held.length, 1);
    assert.equal(held[0].event.id, '4.4');
    assert.equal(decisions(h.ctx).some((row) => row.step === 'subscriptions' && row.reason === 'invalid' && row.detail), true);
  } finally { h.close(); }
});

// F7 positive control — a valid cached rule set still routes while the primary is corrupt.
test('valid last-good cache still routes while the primary is corrupt', async () => {
  const h = harness();
  try {
    fs.writeFileSync(path.join(h.dir, 'subscriptions.last-good.json'), JSON.stringify([{ id: 'sara', connector: 'slack', account: 'T1', agent: 'sara', judge: null }]));
    fs.writeFileSync(h.ctx.subscriptionFile, '{');
    const result = await dispatch(slackOwner({ id: '6.6', text: 'cached rules' }), h.ctx);
    assert.equal(result.agent, 'sara');
    assert.equal(result.queued, true);
    assert.equal(h.hold().length, 0);
  } finally { h.close(); }
});

// F8 — the generated history renders sender, trust, service, account and conversation for
// owner messages of every connector, and keeps the old Slack wording only where no
// provenance was stored.
test('generated history renders sender trust service account and conversation', async () => {
  const h = harness();
  try {
    await dispatch({
      connector: 'google', account: 'agent@example.com', id: 'm1', from: 'owner@example.com',
      claimedFrom: 'Owner <owner@example.com>', conversation: 't1', text: 'mail body',
      files: [], isSelf: false, identity: { verified: true, method: 'gmail-account', owner: true },
    }, h.ctx);
    const sara = h.stores.get('sara');
    const mailKey = sara.db.prepare('SELECT key FROM conversations').get().key;
    const mailHistory = fs.readFileSync(writeHistory(path.join(h.dir, 'sara-home'), sara, mailKey), 'utf8');
    assert.match(mailHistory, /google id m1 account agent@example\.com conversation t1 sender trusted Owner <owner@example\.com>/);
    assert.doesNotMatch(mailHistory, /Slack timestamp/);

    const neutral = fromSocket({ team: 'T1', channel: 'D1', channelType: 'im', ts: '3.100000', threadTs: '3.100000', user: 'UOWNER', text: 'slack hello' }, h.ctx.config);
    await dispatch(neutral, h.ctx);
    const master = h.stores.get('master');
    const slackKey = master.db.prepare('SELECT key FROM conversations').get().key;
    const slackHistory = fs.readFileSync(writeHistory(path.join(h.dir, 'master-home'), master, slackKey), 'utf8');
    assert.match(slackHistory, /slack id 3\.100000 account T1 conversation D1 sender trusted UOWNER/);
  } finally { h.close(); }
});

// F8 — Slack prompt entries carry the same provenance line as other connectors when the
// provenance was stored; rows without provenance keep the legacy timestamp line.
test('prompt renders slack provenance like other connectors', async () => {
  const h = harness();
  try {
    const neutral = fromSocket({ team: 'T1', channel: 'D1', channelType: 'im', ts: '3.100000', threadTs: '3.100000', user: 'UOWNER', text: 'slack hello' }, h.ctx.config);
    const queued = await dispatch(neutral, h.ctx);
    const master = h.stores.get('master');
    const rows = master.listHistory(queued.key, 10);
    const prompt = composeTurn({
      board: 'B', work: {}, inputs: [], recent: rows, stored: [{ role: 'owner', text: 'old row', ts: '1.1' }],
      historyPath: 'h', resultPath: 'r', nonce: 'n', rehydrate: true,
    });
    assert.match(prompt, /Source: slack account T1 conversation D1 id 3\.100000 sender trusted UOWNER/);
    assert.match(prompt, /Slack timestamp of this message: 1\.1/);
  } finally { h.close(); }
});
