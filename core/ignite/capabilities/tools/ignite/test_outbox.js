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

test('every post and upload is sent as the agent named in agent.json', async (store) => {
  const fs = require('node:fs');
  const os = require('node:os');
  const path = require('node:path');
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-as-'));
  fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({
    name: 'sara', harness: 'claude', model: 'opus-5-5', effort: 'medium', avatar: ':owl:',
  }));
  fs.writeFileSync(path.join(home, 'prompt.md'), 'prompt');
  const file = path.join(home, 'out.txt');
  fs.writeFileSync(file, 'x');
  const key = 'T1:C1:1.1';
  store.upsertConversation({ key, agent: 'sara', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.enqueueOutbox({ id: 'r1', conversationKey: key, payload: { text: 'hello', files: [file] } });
  const calls = [];
  const [result] = await deliverPending(store, { home, slack: {
    async postMessage(args) { calls.push(args); return { channel: args.channel, ts: '9.1' }; },
    async uploadFile(args) { calls.push(args); return { ts: '9.2' }; },
  } });
  assert.equal(result.delivered, true);
  assert.equal(calls.length, 2);
  for (const call of calls) assert.deepEqual(call.as, { name: 'Sara', avatar: ':owl:' });
});

test('an external_name is shown instead of the internal name', async (store) => {
  const fs = require('node:fs');
  const os = require('node:os');
  const path = require('node:path');
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-as-'));
  fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({
    name: 'master', external_name: 'Brigid', harness: 'claude', model: 'opus-5-5', effort: 'medium', avatar: ':owl:',
  }));
  fs.writeFileSync(path.join(home, 'prompt.md'), 'prompt');
  const key = 'T1:C1:1.1';
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.enqueueOutbox({ id: 'r1', conversationKey: key, payload: { text: 'hello' } });
  const calls = [];
  await deliverPending(store, { home, slack: {
    async postMessage(args) { calls.push(args); return { channel: args.channel, ts: '9.1' }; },
  } });
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].as, { name: 'Brigid', avatar: ':owl:' });
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

function markSlack() {
  const slack = {
    reactions: [], error: null,
    async postMessage(args) { return { channel: args.channel, ts: '9.1' }; },
    async addReaction(channel, ts, name) {
      if (slack.error) throw new Error(slack.error);
      slack.reactions.push(`add ${name}`);
    },
    async removeReaction(channel, ts, name) {
      if (slack.error) throw new Error(slack.error);
      slack.reactions.push(`remove ${name}`);
    },
  };
  return slack;
}

function markedRows(store, ids) {
  const key = 'T1:C1:1.1';
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  for (const id of ids) {
    store.enqueueOutbox({ id, conversationKey: key, payload: { text: id, mark: { channel: 'C1', ts: '1.1' } } });
  }
}

test('delivering every marked reply marks the owner message heavy_check_mark once', async (store) => {
  markedRows(store, ['r1', 'r2']);
  const slack = markSlack();
  await deliverPending(store, { slack });
  assert.deepEqual(slack.reactions, [
    'add heavy_check_mark', 'remove hourglass_flowing_sand', 'remove eyes',
  ]);
});

test('a marked reply that gives up marks heavy_multiplication_x and the other reply never marks replied', async (store) => {
  markedRows(store, ['r1', 'r2']);
  const slack = markSlack();
  const post = slack.postMessage;
  slack.postMessage = async (args) => {
    if (args.text === 'r1') throw new Error('Slack chat.postMessage: channel_not_found');
    return post(args);
  };
  await deliverPending(store, { slack });
  assert.deepEqual(slack.reactions, [
    'add heavy_multiplication_x', 'remove hourglass_flowing_sand', 'remove eyes',
  ]);
});

test('a retryable delivery failure marks nothing', async (store) => {
  markedRows(store, ['r1']);
  const slack = markSlack();
  slack.postMessage = async () => { throw new Error('slack down'); };
  await deliverPending(store, { slack });
  assert.deepEqual(slack.reactions, []);
});

test('rows without a mark, and hold notices, never react', async (store) => {
  const key = 'T1:C1:1.1';
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.enqueueOutbox({ id: 'plain', conversationKey: key, payload: { text: 'plain' } });
  store.enqueueOutbox({ id: 'hold:x', conversationKey: key, payload: { text: 'hold' } });
  const slack = markSlack();
  const results = await deliverPending(store, { slack });
  assert.deepEqual(results.map((r) => r.delivered), [true, true]);
  assert.deepEqual(slack.reactions, []);
});

test('a reaction API error never fails a delivery', async (store) => {
  markedRows(store, ['r1']);
  const slack = markSlack();
  slack.error = 'Slack reactions.add: ratelimited';
  const logs = [];
  const [result] = await deliverPending(store, { slack, log: (f) => logs.push(f) });
  assert.equal(result.delivered, true);
  assert.equal(store.db.prepare('SELECT state FROM outbox WHERE id=?').get('r1').state, 'delivered');
  assert.equal(logs[0].event, 'mark-failed');
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
