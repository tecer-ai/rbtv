'use strict';

const assert = require('node:assert/strict');
const { Store } = require('./store.js');
const { deliverPending } = require('./outbox.js');

const failures = [];
const pending = [];

function test(name, fn) {
  pending.push([name, fn]);
}

test('pending rows follow the new thread even when the old conversation remains', async (store) => {
  const key = 'T1:C1:board';
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: 'board' });
  store.upsertSchedule({ id: 'check', conversationKey: key, cadence: 'every:1h', timezone: 'UTC' });
  for (const id of ['r1', 'r2']) {
    store.enqueueOutbox({ id, conversationKey: key, payload: { text: id } });
  }
  const posts = [];
  const results = await deliverPending(store, { slack: {
    async postMessage(args) {
      posts.push(args);
      return { channel: args.channel, ts: `9.${posts.length}` };
    },
  } });
  assert.deepEqual(results.map((row) => row.delivered), [true, true]);
  assert.deepEqual(posts.map((post) => post.threadTs), [undefined, results[0].ts]);
  assert.equal(store.getConversation(key).root_ts, 'board');
  assert.equal(store.getSchedule('check').conversation_key, key);
});

test('a conversation lost after loading the row is recovered before delivery', async (store) => {
  const key = 'schedule:wake';
  const bound = 'T1:C1:9.1';
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1' });
  store.enqueueOutbox({ id: 'reply', conversationKey: key, payload: { text: 'follow-up' } });
  const getConversation = store.getConversation.bind(store);
  store.getConversation = (requested) => {
    if (requested !== key) return getConversation(requested);
    // Another delivery binds the thread between reading the row and its conversation.
    store.getConversation = getConversation;
    store._rekey(key, bound);
    store.upsertConversation({ key: bound, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '9.1' });
    return null;
  };
  const posts = [];
  const [result] = await deliverPending(store, { slack: {
    async postMessage(args) {
      posts.push(args);
      return { channel: args.channel, ts: '9.2' };
    },
  } });
  assert.equal(result.delivered, true);
  assert.equal(result.conversationKey, bound);
  assert.equal(posts.length, 1);
  assert.equal(posts[0].threadTs, '9.1');
  const saved = store.db.prepare('SELECT * FROM outbox WHERE id=?').get('reply');
  assert.equal(saved.state, 'delivered');
  assert.equal(saved.last_error, null);
});

test('a conversation still missing after reload stops delivery', async (store) => {
  const key = 'schedule:wake';
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1' });
  store.enqueueOutbox({ id: 'reply', conversationKey: key, payload: { text: 'follow-up' } });
  store.getConversation = () => null;
  const [result] = await deliverPending(store, { slack: {
    async postMessage() { assert.fail('unknown conversation must not post'); },
  } });
  assert.deepEqual(result, { id: 'reply', delivered: false, stopped: true, error: 'unknown conversation' });
  assert.equal(store.db.prepare('SELECT state FROM outbox WHERE id=?').get('reply').state, 'failed');
});

async function runAll() {
  for (const [name, fn] of pending) {
    const store = new Store(':memory:');
    try {
      await fn(store);
      console.log(`PASS ${name}`);
    } catch (error) {
      failures.push(name);
      console.log(`FAIL ${name}: ${error.stack || error.message}`);
    } finally {
      store.close();
    }
  }
  if (failures.length) {
    console.log(`FAIL ${failures.length}`);
    process.exit(1);
  }
  console.log('PASS outbox');
}

runAll();
