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
const BOT = 'UBOT';
const FILE = { id: 'F1', name: 'note.mp3', mimetype: 'audio/mpeg', filetype: 'mp3' };

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

function config() {
  return {
    dmAgent: 'master',
    slack: { team: TEAM, botUserId: BOT, ownerUserId: OWNER },
    routes: { CCHAN: 'probe' },
  };
}

function event(extra = {}) {
  const ts = extra.ts || '1.100000';
  return {
    team: TEAM,
    channel: 'D1',
    channelType: 'im',
    ts,
    threadTs: extra.threadTs || ts,
    user: OWNER,
    text: 'hello',
    files: [],
    isBotOrSelf: false,
    mentionsBot: false,
    ...extra,
  };
}

function queueCount(store) {
  return store.db.prepare('SELECT COUNT(*) AS n FROM queue').get().n;
}

function harness(history = []) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-ingress-'));
  const stores = new Map();
  const opened = [];
  const historyCalls = [];
  function openStore(slug) {
    opened.push(slug);
    if (!stores.has(slug)) {
      stores.set(slug, new Store(path.join(dir, slug, 'state.sqlite')));
    }
    return stores.get(slug);
  }
  const slack = {
    async threadHistory(channel, threadTs) {
      historyCalls.push({ channel, threadTs });
      return history;
    },
  };
  return {
    dir,
    stores,
    opened,
    historyCalls,
    ctx: { config: config(), openStore, slack },
    close() {
      for (const store of stores.values()) store.close();
      fs.rmSync(dir, { recursive: true, force: true });
    },
  };
}

test('dm-toplevel', async () => {
  const h = harness();
  try {
    const result = await handleEvent(event({ text: 'dm', files: [FILE] }), h.ctx);
    assert.equal(result.queued, true);
    assert.equal(result.agent, 'master');
    assert.equal(result.key, 'T1:D1:1.100000');
    const store = h.stores.get('master');
    assert.equal(store.getConversation(result.key).activated, true);
    const rows = store.listHistory(result.key);
    assert.equal(rows.length, 1);
    assert.equal(rows[0].role, 'owner');
    assert.equal(rows[0].team, TEAM);
    assert.equal(rows[0].channel, 'D1');
    assert.equal(rows[0].ts, '1.100000');
    assert.deepEqual(rows[0].files, [FILE]);
    assert.equal(queueCount(store), 1);
    assert.equal(h.historyCalls.length, 0);
    assert.deepEqual(h.opened, ['master']);
  } finally {
    h.close();
  }
});

test('dm-reply-known-thread', async () => {
  const h = harness();
  try {
    const root = await handleEvent(event({ ts: '2.100000', text: 'root' }), h.ctx);
    const reply = await handleEvent(event({
      ts: '2.200000', threadTs: '2.100000', text: 'reply',
    }), h.ctx);
    assert.equal(reply.queued, true);
    assert.equal(reply.key, root.key);
    assert.equal(reply.key, 'T1:D1:2.100000');
    const store = h.stores.get('master');
    assert.equal(store.listHistory(root.key).length, 2);
    assert.equal(queueCount(store), 2);
    assert.equal(store.getConversation('T1:D1:2.200000'), null);
  } finally {
    h.close();
  }
});

test('channel-toplevel-mention', async () => {
  const h = harness();
  try {
    const result = await handleEvent(event({
      channel: 'CCHAN', channelType: 'channel', ts: '3.100000', text: '<@UBOT> go', mentionsBot: true,
    }), h.ctx);
    assert.equal(result.queued, true);
    assert.equal(result.agent, 'probe');
    assert.equal(result.key, 'T1:CCHAN:3.100000');
    const store = h.stores.get('probe');
    assert.equal(store.getConversation(result.key).activated, true);
    assert.equal(store.listHistory(result.key).length, 1);
    assert.equal(queueCount(store), 1);
    assert.equal(h.historyCalls.length, 0);
    assert.deepEqual(h.opened, ['probe']);
  } finally {
    h.close();
  }
});

test('channel-thread-unknown', async () => {
  const earlier = event({
    channel: 'CCHAN', channelType: 'channel', ts: '4.100000', threadTs: '4.100000',
    text: 'before', user: OWNER,
  });
  const trigger = event({
    channel: 'CCHAN', channelType: 'channel', ts: '4.200000', threadTs: '4.100000',
    text: 'late', mentionsBot: false,
  });
  const h = harness([earlier, trigger]);
  try {
    const result = await handleEvent(trigger, h.ctx);
    assert.equal(result.queued, true);
    assert.equal(result.key, 'T1:CCHAN:4.100000');
    assert.deepEqual(h.historyCalls, [{ channel: 'CCHAN', threadTs: '4.100000' }]);
    const store = h.stores.get('probe');
    assert.equal(store.getConversation(result.key).activated, true);
    const rows = store.listHistory(result.key);
    assert.deepEqual(rows.map((row) => row.text), ['before', 'late']);
    assert.equal(rows[0].ts, '4.100000');
    assert.equal(rows[0].role, 'owner');
    assert.equal(queueCount(store), 1);
  } finally {
    h.close();
  }
});

test('channel-activated-thread-no-mention', async () => {
  const h = harness();
  try {
    const store = h.ctx.openStore('probe');
    h.opened.length = 0;
    const begun = store.beginProactive({
      id: 'post1', agent: 'probe', workspace: TEAM, channel: 'CCHAN', payload: { text: 'result' },
    });
    store.markDelivered(begun.outboxId, { channel: 'CCHAN', ts: '5.100000' });
    const result = await handleEvent(event({
      channel: 'CCHAN', channelType: 'channel', ts: '5.200000', threadTs: '5.100000',
      text: 'thanks', mentionsBot: false,
    }), h.ctx);
    assert.equal(result.queued, true);
    assert.equal(result.agent, 'probe');
    assert.equal(result.key, 'T1:CCHAN:5.100000');
    assert.equal(store.getConversation('pending:post1'), null);
    assert.equal(store.getConversation(result.key).activated, true);
    assert.equal(store.listHistory(result.key).length, 1);
    assert.equal(store.listHistory(result.key)[0].text, 'thanks');
    assert.equal(queueCount(store), 1);
    assert.equal(h.historyCalls.length, 0);
    assert.equal(store.getConversation('T1:CCHAN:5.200000'), null);
  } finally {
    h.close();
  }
});

test('channel-unmentioned-toplevel', async () => {
  const h = harness();
  try {
    const result = await handleEvent(event({
      channel: 'CCHAN', channelType: 'channel', ts: '6.100000', text: '', files: [FILE], mentionsBot: false,
    }), h.ctx);
    assert.equal(result.queued, true);
    assert.equal(result.agent, 'probe');
    assert.equal(result.key, 'T1:CCHAN:6.100000');
    const store = h.stores.get('probe');
    assert.equal(store.getConversation(result.key).activated, true);
    const rows = store.listHistory(result.key);
    assert.equal(rows.length, 1);
    assert.deepEqual(rows[0].files, [FILE]);
    assert.equal(queueCount(store), 1);
    assert.equal(h.historyCalls.length, 0);
  } finally {
    h.close();
  }
});

test('mention-changes-nothing', async () => {
  const h = harness();
  try {
    const plain = await handleEvent(event({
      channel: 'CCHAN', channelType: 'channel', ts: '11.100000', text: 'plain', mentionsBot: false,
    }), h.ctx);
    const mentioned = await handleEvent(event({
      channel: 'CCHAN', channelType: 'channel', ts: '11.200000', text: '<@UBOT> go', mentionsBot: true,
    }), h.ctx);
    assert.equal(plain.queued, true);
    assert.equal(mentioned.queued, true);
    assert.equal(plain.agent, 'probe');
    assert.equal(mentioned.agent, 'probe');
    assert.equal(plain.key, 'T1:CCHAN:11.100000');
    assert.equal(mentioned.key, 'T1:CCHAN:11.200000');
    assert.equal(h.historyCalls.length, 0);
    const store = h.stores.get('probe');
    store.upsertConversation({
      key: 'T1:CCHAN:11.300000', agent: 'probe', workspace: TEAM, channel: 'CCHAN',
      rootTs: '11.300000', activated: true,
    });
    const follow = await handleEvent(event({
      channel: 'CCHAN', channelType: 'channel', ts: '11.400000', threadTs: '11.300000',
      text: '<@UBOT> again', mentionsBot: true,
    }), h.ctx);
    assert.equal(follow.queued, true);
    assert.equal(follow.key, 'T1:CCHAN:11.300000');
    assert.equal(h.historyCalls.length, 0);
  } finally {
    h.close();
  }
});

test('bot-self-subtype-or-saved', async () => {
  const h = harness();
  try {
    h.ctx.openStore = () => { throw new Error('store opened'); };
    const bot = await handleEvent(event({ user: BOT, isBotOrSelf: true, text: 'echo' }), h.ctx);
    assert.deepEqual(bot, { ignored: 'bot' });
    const subtype = await handleEvent(event({
      user: OWNER, isBotOrSelf: true, text: 'edited', ts: '7.200000',
    }), h.ctx);
    assert.deepEqual(subtype, { ignored: 'bot' });
  } finally {
    h.close();
  }
  const saved = harness();
  try {
    const first = await handleEvent(event({ ts: '7.300000', text: 'once' }), saved.ctx);
    const again = await handleEvent(event({ ts: '7.300000', text: 'once' }), saved.ctx);
    assert.equal(first.queued, true);
    assert.equal(again.ignored, 'duplicate');
    const store = saved.stores.get('master');
    assert.equal(store.listHistory(first.key).length, 1);
    assert.equal(queueCount(store), 1);
  } finally {
    saved.close();
  }
});

test('non-owner', async () => {
  const h = harness();
  try {
    h.ctx.openStore = () => { throw new Error('store opened'); };
    const channel = await handleEvent(event({
      channel: 'CCHAN', channelType: 'channel', user: 'UOTHER', mentionsBot: true, text: '<@UBOT> hi',
    }), h.ctx);
    assert.deepEqual(channel, { ignored: 'non-owner' });
    const dm = await handleEvent(event({ user: 'UOTHER', text: 'dm' }), h.ctx);
    assert.deepEqual(dm, { ignored: 'non-owner' });
  } finally {
    h.close();
  }
});

test('unconfigured-channel', async () => {
  const h = harness();
  try {
    h.ctx.openStore = () => { throw new Error('store opened'); };
    const result = await handleEvent(event({
      channel: 'CNOPE', channelType: 'channel', mentionsBot: true, text: '<@UBOT> hi',
    }), h.ctx);
    assert.deepEqual(result, { ignored: 'unconfigured' });
  } finally {
    h.close();
  }
});

test('redelivery-one-message-one-queue', async () => {
  const h = harness();
  try {
    const incoming = event({ ts: '8.100000', text: 'again', files: [FILE] });
    const first = await handleEvent(incoming, h.ctx);
    const second = await handleEvent(incoming, h.ctx);
    assert.equal(first.queued, true);
    assert.equal(second.ignored, 'duplicate');
    const store = h.stores.get('master');
    assert.equal(store.listHistory(first.key).length, 1);
    assert.equal(queueCount(store), 1);
    assert.deepEqual(store.listHistory(first.key)[0].files, [FILE]);
  } finally {
    h.close();
  }
});

test('late-mention-three-earlier', async () => {
  const root = '9.100000';
  const earlier = [
    event({ channel: 'CCHAN', channelType: 'channel', ts: '9.100000', threadTs: root, text: 'one', user: OWNER }),
    event({
      channel: 'CCHAN', channelType: 'channel', ts: '9.200000', threadTs: root,
      text: 'bot said', user: BOT, isBotOrSelf: true,
    }),
    event({
      channel: 'CCHAN', channelType: 'channel', ts: '9.300000', threadTs: root,
      text: 'other', user: 'UOTHER',
    }),
  ];
  const trigger = event({
    channel: 'CCHAN', channelType: 'channel', ts: '9.400000', threadTs: root,
    text: '<@UBOT> now', mentionsBot: true, files: [FILE],
  });
  const h = harness([...earlier, trigger]);
  try {
    const result = await handleEvent(trigger, h.ctx);
    assert.equal(result.queued, true);
    assert.equal(result.key, 'T1:CCHAN:9.100000');
    const store = h.stores.get('probe');
    const rows = store.listHistory(result.key);
    assert.deepEqual(rows.map((row) => row.text), ['one', 'bot said', 'other', '<@UBOT> now']);
    assert.deepEqual(rows.map((row) => row.role), ['owner', 'assistant', 'user', 'owner']);
    assert.deepEqual(rows.map((row) => row.ts), ['9.100000', '9.200000', '9.300000', '9.400000']);
    assert.equal(rows[0].team, TEAM);
    assert.equal(rows[0].channel, 'CCHAN');
    assert.deepEqual(rows[3].files, [FILE]);
    assert.equal(queueCount(store), 1);
    const again = await handleEvent(trigger, h.ctx);
    assert.equal(again.ignored, 'duplicate');
    assert.equal(store.listHistory(result.key).length, 4);
    assert.equal(queueCount(store), 1);
  } finally {
    h.close();
  }
});

test('ack-after-store-write', async () => {
  let wrote = false;
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  const store = {
    async acceptOwnerInput() {
      await gate;
      wrote = true;
      return { duplicate: false, inserted: true, workId: 'w1' };
    },
  };
  const pending = handleEvent(event({ text: 'wait' }), {
    config: config(),
    openStore: async () => store,
    slack: { async threadHistory() { throw new Error('no history'); } },
  });
  let settled = false;
  pending.then(() => { settled = true; }, () => { settled = true; });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(settled, false);
  assert.equal(wrote, false);
  release();
  const result = await pending;
  assert.equal(wrote, true);
  assert.equal(settled, true);
  assert.equal(result.queued, true);
  assert.equal(result.workId, 'w1');
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
  process.stdout.write(`ingress: ${tests.length - failed} passed, ${failed} failed\n`);
  process.exit(failed ? 1 : 0);
})();
