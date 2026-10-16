'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Store } = require('./store.js');
const { deliverPending } = require('./outbox.js');
const live = require('./live-status.js');
const { example } = require('../../../../cast/capabilities/tools/cast/example-models');
const AGENT_MODEL = example('a claude CLI model for the agent record', (m) => m.harness === 'claude' && m.mode === 'cli');

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
    name: 'sara', harness: 'claude', model: AGENT_MODEL.model, effort: AGENT_MODEL.rungs[0], avatar: ':owl:',
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
    name: 'master', external_name: 'Brigid', harness: 'claude', model: AGENT_MODEL.model, effort: AGENT_MODEL.rungs[0], avatar: ':owl:',
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

// Slack confirms each post and upload with the next ts, 9.1, 9.2, …; calls keeps each as post or upload
// with its text or file.
function markSlack() {
  const slack = {
    reactions: [],
    posted: 0,
    calls: [],
    async postMessage(args) {
      slack.posted += 1;
      slack.calls.push(`post ${args.text}`);
      return { channel: args.channel, ts: `9.${slack.posted}` };
    },
    async uploadFile(args) {
      slack.posted += 1;
      slack.calls.push(`upload ${args.file}`);
      return { ts: `9.${slack.posted}` };
    },
    async addReaction(channel, ts, name) { slack.reactions.push(`add ${name}`); },
    async removeReaction(channel, ts, name) { slack.reactions.push(`remove ${name}`); },
  };
  return slack;
}

// Reply rows of run R1 answering owner message C1/1.1, the thread's latest message, whose turn is over:
// it still shows its agent state. payload adds to each row's payload (files, audio, text).
function markedRows(store, ids, task = 'done', payload = {}) {
  const key = 'T1:C1:1.1';
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.setLiveStatus({ conversationKey: key, channel: 'C1', ts: '1.1', system: 'running', agent: 'working', runId: 'R1' });
  for (const id of ids) {
    store.enqueueOutbox({ id, conversationKey: key,
      payload: { text: id, mark: { channel: 'C1', ts: '1.1', runId: 'R1', ...(task && { task }) }, ...payload } });
  }
}

// Each message's live layers, by ts.
const shown = (store) => Object.fromEntries(store.liveStatuses()
  .map((row) => [row.ts, { system: row.system, agent: row.agent, task: row.task }]));
const none = { system: null, agent: null, task: null };

test('each delivered reply takes the live status; the last one of its turn keeps the task in place of the agent state', async (store) => {
  markedRows(store, ['r1', 'r2']);
  const slack = markSlack();
  const post = slack.postMessage;
  let seenAfterFirst = null;
  slack.postMessage = async (args) => {
    if (args.text === 'r2') seenAfterFirst = shown(store);
    return post(args);
  };
  await deliverPending(store, { slack });
  assert.deepEqual(seenAfterFirst, { 1.1: none, 9.1: { system: 'running', agent: 'working', task: null } });
  assert.deepEqual(shown(store), { 1.1: none, 9.1: none, 9.2: { system: 'running', agent: null, task: 'done' } });
  const last = store.getLiveStatus('C1', '9.2');
  assert.deepEqual([last.kept, last.kept_for, last.run_id], ['done', '1.1', 'R1']);
  assert.deepEqual(slack.reactions, []);
});

test('a reply with no task (continue, waiting_workers) takes the agent state as it is', async (store) => {
  markedRows(store, ['r1'], null);
  await deliverPending(store, { slack: markSlack() });
  assert.deepEqual(shown(store), { 1.1: none, 9.1: { system: 'running', agent: 'working', task: null } });
});

test('a reply that gives up moves nothing: the latest message shows failed, and the turn never shows its task', async (store) => {
  markedRows(store, ['r1', 'r2']);
  const slack = markSlack();
  const post = slack.postMessage;
  let seenAtSecond = null;
  slack.postMessage = async (args) => {
    if (args.text === 'r1') throw new Error('Slack chat.postMessage: channel_not_found');
    seenAtSecond = shown(store);
    return post(args);
  };
  await deliverPending(store, { slack });
  assert.deepEqual(seenAtSecond, { 1.1: { system: 'failed', agent: null, task: null } });
  // The other reply is still delivered: the failure moves with it, and no task shows.
  assert.deepEqual(shown(store), { 1.1: none, 9.1: { system: 'failed', agent: null, task: null } });
});

test('a retryable delivery failure changes no live status', async (store) => {
  markedRows(store, ['r1']);
  const slack = markSlack();
  slack.postMessage = async () => { throw new Error('slack down'); };
  await deliverPending(store, { slack });
  assert.deepEqual(shown(store), { 1.1: { system: 'running', agent: 'working', task: null } });
});

test('a thread that shows no live status gets none from its rows, hold notices included', async (store) => {
  const key = 'T1:C1:1.1';
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.enqueueOutbox({ id: 'plain', conversationKey: key, payload: { text: 'plain' } });
  store.enqueueOutbox({ id: 'hold:x', conversationKey: key, payload: { text: 'hold' } });
  const slack = markSlack();
  const results = await deliverPending(store, { slack });
  assert.deepEqual(results.map((r) => r.delivered), [true, true]);
  assert.deepEqual(store.liveStatuses(), []);
});

test('a post into a thread that shows a live status takes it, the conversation\'s task included, and keeps that task once the status leaves it, after a reopened store too', async () => {
  const database = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-outbox-')), 'state.sqlite');
  let db = new Store(database);
  const key = 'T1:C1:1.1';
  db.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  db.setLiveStatus({ conversationKey: key, channel: 'C1', ts: '1.1', system: 'running', task: 'done', kept: 'done', keptFor: '1.1' });
  db.enqueueOutbox({ id: 'post:p1', conversationKey: key, payload: { text: 'notice' } });
  await deliverPending(db, { slack: markSlack() });
  assert.deepEqual(shown(db), { 1.1: { system: null, agent: null, task: 'done' }, 9.1: { system: 'running', agent: null, task: 'done' } });
  const kept = (ts) => { const row = db.getLiveStatus('C1', ts); return [row.kept, row.kept_for]; };
  assert.deepEqual(kept('9.1'), ['done', '1.1']);
  db.close();
  db = new Store(database);
  assert.deepEqual(kept('9.1'), ['done', '1.1']);
  // The owner's next message: the post keeps its done and loses only its system state.
  live.received(db, { conversationKey: key, channel: 'C1', ts: '10.1' });
  assert.deepEqual(shown(db), {
    1.1: { system: null, agent: null, task: 'done' },
    9.1: { system: null, agent: null, task: 'done' },
    '10.1': { system: 'queued', agent: null, task: null },
  });
  assert.deepEqual(kept('10.1'), [null, null]);
  db.close();
});

// Every message Slack confirmed for a row, and its text receipt.
const sent = (store, id) => {
  const row = store._outbox(store.db.prepare('SELECT * FROM outbox WHERE id=?').get(id));
  return { state: row.state, ts: row.ts, posted: row.posted };
};
const replyOf = (store, ts) => { const row = store.getLiveStatus('C1', ts); return [row.kept, row.kept_for]; };

test('a reply with text and a file: both messages are known, and the live status and task go to the file, the newer', async (store) => {
  markedRows(store, ['r1'], 'done', { files: ['/out/report.pdf'] });
  const slack = markSlack();
  await deliverPending(store, { slack });
  assert.deepEqual(slack.calls, ['post r1', 'upload /out/report.pdf']);
  assert.deepEqual(sent(store, 'r1'), { state: 'delivered', ts: '9.1', posted: ['9.1', '9.2'] });
  assert.deepEqual(shown(store), { 1.1: none, 9.1: none, 9.2: { system: 'running', agent: null, task: 'done' } });
  assert.deepEqual([replyOf(store, '9.1'), replyOf(store, '9.2')], [[null, '1.1'], ['done', '1.1']]);
});

test('a reply of several files and no text: each upload is known, and the live status and task go to the last', async (store) => {
  markedRows(store, ['r1'], 'done', { text: '', files: ['/out/a.png', '/out/b.png', '/out/c.png'] });
  const slack = markSlack();
  await deliverPending(store, { slack });
  assert.deepEqual(slack.calls, ['upload /out/a.png', 'upload /out/b.png', 'upload /out/c.png']);
  assert.deepEqual(sent(store, 'r1'), { state: 'delivered', ts: '9.1', posted: ['9.1', '9.2', '9.3'] });
  assert.deepEqual(shown(store), { 1.1: none, 9.1: none, 9.2: none, 9.3: { system: 'running', agent: null, task: 'done' } });
});

test('an audio reply: its text and its voice file are known, and the live status and task go to the voice file', async (store) => {
  markedRows(store, ['r1'], 'done', { audio: true });
  const slack = markSlack();
  const audio = { async speak(text) { return `/voice/${text}.mp3`; } };
  await deliverPending(store, { slack, audio });
  assert.deepEqual(slack.calls, ['post r1', 'upload /voice/r1.mp3']);
  assert.deepEqual(sent(store, 'r1'), { state: 'delivered', ts: '9.1', posted: ['9.1', '9.2'] });
  assert.deepEqual(shown(store), { 1.1: none, 9.1: none, 9.2: { system: 'running', agent: null, task: 'done' } });
});

test('the messages of a reply survive a failed upload and a reopened store: the text is not posted again, and the status goes to the newest', async () => {
  const database = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-outbox-')), 'state.sqlite');
  let db = new Store(database);
  markedRows(db, ['r1'], 'done', { files: ['/out/a.png', '/out/b.png'] });
  const slack = markSlack();
  const upload = slack.uploadFile;
  slack.uploadFile = async (args) => {
    if (args.file === '/out/b.png' && slack.calls.length < 3) { slack.calls.push(`upload ${args.file}`); throw new Error('slack down'); }
    return upload(args);
  };
  const [first] = await deliverPending(db, { slack, now: () => 0 });
  assert.equal(first.delivered, false);
  assert.deepEqual(sent(db, 'r1'), { state: 'pending', ts: '9.1', posted: ['9.1', '9.2'] });
  assert.deepEqual(shown(db), { 1.1: { system: 'running', agent: 'working', task: null } });
  db.close();
  db = new Store(database);
  // The retry posts no text; it uploads every file of the reply again.
  await deliverPending(db, { slack, now: () => 60_000 });
  assert.deepEqual(slack.calls, ['post r1', 'upload /out/a.png', 'upload /out/b.png', 'upload /out/a.png', 'upload /out/b.png']);
  assert.deepEqual(sent(db, 'r1'), { state: 'delivered', ts: '9.1', posted: ['9.1', '9.2', '9.3', '9.4'] });
  assert.deepEqual(shown(db), { 1.1: none, 9.1: none, 9.2: none, 9.3: none, 9.4: { system: 'running', agent: null, task: 'done' } });
  db.close();
});

test('a live status write error never fails a delivery', async (store) => {
  markedRows(store, ['r1']);
  store.setLiveStatus = () => { throw new Error('disk full'); };
  const logs = [];
  const [result] = await deliverPending(store, { slack: markSlack(), log: (f) => logs.push(f) });
  assert.equal(result.delivered, true);
  assert.equal(store.db.prepare('SELECT state FROM outbox WHERE id=?').get('r1').state, 'delivered');
  assert.deepEqual(logs, [{ event: 'status-failed', message: 'disk full' }]);
});

// What reaches the database, in order: each top-level transaction, and the writes in it.
function recordEvents(store) {
  const events = [];
  const exec = store.db.exec.bind(store.db);
  store.db.exec = (sql) => {
    if (/^(BEGIN|COMMIT)/.test(sql)) events.push(sql.split(' ')[0]);
    return exec(sql);
  };
  for (const name of ['rememberPost', 'markDelivered', 'stopOutbox', 'setLiveStatus']) {
    const original = store[name].bind(store);
    store[name] = (...args) => { events.push(name); return original(...args); };
  }
  return events;
}

test('each move and the task are written in the transaction that records the delivery', async (store) => {
  markedRows(store, ['r1', 'r2']);
  const events = recordEvents(store);
  await deliverPending(store, { slack: markSlack() });
  // (a name is noted as its call starts: rememberPost opens its own transaction.) r1: the reply is
  // known, the owner message cleared, the reply takes the layers. r2: the same, then its task.
  assert.deepEqual(events, [
    'rememberPost', 'BEGIN', 'COMMIT', 'BEGIN', 'markDelivered', 'setLiveStatus', 'setLiveStatus', 'setLiveStatus', 'COMMIT',
    'rememberPost', 'BEGIN', 'COMMIT', 'BEGIN', 'markDelivered', 'setLiveStatus', 'setLiveStatus', 'setLiveStatus', 'setLiveStatus', 'COMMIT',
  ]);
  assert.deepEqual(shown(store)['9.2'], { system: 'running', agent: null, task: 'done' });
});

test('a give-up and its failed system state are written in one transaction', async (store) => {
  markedRows(store, ['r3']);
  const events = recordEvents(store);
  const slack = markSlack();
  slack.postMessage = async () => { throw new Error('Slack chat.postMessage: channel_not_found'); };
  await deliverPending(store, { slack });
  assert.deepEqual(events.slice(events.indexOf('stopOutbox') - 1, events.indexOf('stopOutbox') + 3),
    ['BEGIN', 'stopOutbox', 'setLiveStatus', 'COMMIT']);
  assert.deepEqual(shown(store), { 1.1: { system: 'failed', agent: null, task: null } });
});

test('a DM agent board post goes to the DM that conversations.open returns, never to the user id', async (store) => {
  const key = 'T1:UOWNER:board';
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'UOWNER', rootTs: 'board' });
  store.enqueueOutbox({ id: 'b1', conversationKey: key, payload: { text: 'check' } });
  const posts = [];
  const [result] = await deliverPending(store, { slack: {
    async openIm(user) { assert.equal(user, 'UOWNER'); return 'DOWNER'; },
    async postMessage(args) { posts.push(args); return { channel: args.channel, ts: '9.1' }; },
  } });
  assert.equal(result.delivered, true);
  // The literal is the guard: Slack may route a user-id post to the owner's Slackbot DM.
  assert.deepEqual(posts.map((post) => post.channel), ['DOWNER']);
});

// Phase 2 of the connector architecture: outbox.js and `message send` call one send function, the module
// connectors/messaging/capabilities/tools/message/lib/send.js. The test fails when either caller stops
// resolving to that module's export, or when a delivery no longer goes through it.
const SEND_MODULE = path.resolve(__dirname, '..', '..', '..', '..', '..', 'connectors', 'messaging', 'capabilities', 'tools', 'message', 'lib', 'send.js');
const MESSAGE_COMMAND = path.resolve(SEND_MODULE, '..', '..', 'message.js');

// The port command's caller: a synthetic installation whose one messaging connector is a stub adapter that
// records every operation in global.__divergenceCalls, and an agent folder whose name people see is Brigid.
const DIVERGENCE_STUB = `'use strict';
const calls = global.__divergenceCalls = global.__divergenceCalls || [];
module.exports = {
  address(value) { return /^[UW]/.test(value) ? { contact: value } : { group: value }; },
  async account() { return 'T1'; },
  operations: {
    async 'message.send'(input) { calls.push({ op: 'message.send', text: input.text, as: input.as, thread: input.thread }); return { conversation: 'D1', id: '8.' + calls.length }; },
    async 'message.file'({ send }) { calls.push({ op: 'message.file', file: send.file, as: send.as, thread: send.thread }); return { id: '8.' + calls.length, conversation: send.conversation || 'D1' }; },
  },
};
`;
function messageCaller() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-divergence-root-'));
  const installation = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-divergence-inst-'));
  fs.mkdirSync(path.join(root, 'connectors', 'slack', 'capabilities', 'tools', 'slack', 'lib'), { recursive: true });
  fs.writeFileSync(path.join(root, 'connectors', 'slack', 'slack.json'), JSON.stringify({ description: 'stub', dependencies: [], type: 'messaging', provides: ['message.send', 'message.file'] }));
  fs.writeFileSync(path.join(root, 'connectors', 'slack', 'capabilities', 'tools', 'slack', 'lib', 'messaging.js'), DIVERGENCE_STUB);
  fs.mkdirSync(path.join(installation, '.rbtv', 'config', 'ignite'), { recursive: true });
  fs.writeFileSync(path.join(installation, '.rbtv', 'config', 'install.json'), JSON.stringify({ schema: 6, components: { 'connectors/slack': {} } }));
  fs.writeFileSync(path.join(installation, '.rbtv', 'config', 'ignite', 'config.json'), JSON.stringify({ slack: { ownerUserId: 'UOWNER' }, routes: {} }));
  const home = path.join(installation, '.rbtv', 'agents', 'sara');
  fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({ name: 'sara', external_name: 'Brigid', harness: 'claude', model: AGENT_MODEL.model, effort: AGENT_MODEL.rungs[0], avatar: ':owl:' }));
  fs.writeFileSync(path.join(home, 'prompt.md'), 'prompt\n');
  const file = path.join(home, 'out.txt');
  fs.writeFileSync(file, 'x');
  global.__divergenceCalls = [];
  return { root, installation, home, file };
}

test('outbox.js and message send resolve to the one send function, and both deliver and name the sender through it', async (store) => {
  const sendModule = require(SEND_MODULE);
  const message = require(MESSAGE_COMMAND);
  assert.equal(typeof sendModule.send, 'function');
  assert.equal(require('./outbox.js').sendModule, sendModule, 'outbox.js shares the module');
  assert.equal(message.sendModule, sendModule, 'message.js shares the module');
  const fx = messageCaller();
  // Over an 11,000-character limit, under the contract's 12,000: the one function posts it as text. A caller
  // with its own implementation and its own limit would send a file, or never pass through here.
  const text = 'z'.repeat(11_500);
  const key = 'T1:C1:1.1';
  store.upsertConversation({ key, agent: 'sara', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.enqueueOutbox({ id: 'r1', conversationKey: key, payload: { text, files: [fx.file] } });
  const original = sendModule.send;
  const originalSender = sendModule.senderOf;
  const seen = [];
  const named = [];
  sendModule.send = async (operations, input) => {
    seen.push({ operations: Object.keys(operations).sort(), input });
    return original(operations, input);
  };
  sendModule.senderOf = (home) => { named.push(home); return originalSender(home); };
  let out = '';
  let err = '';
  let slack;
  let code;
  try {
    slack = markSlack();
    const [result] = await deliverPending(store, { slack, home: fx.home });
    assert.equal(result.delivered, true);
    code = await message.main(['--json', 'send', '--to', 'UOWNER', '--via', 'slack', text, '--file', fx.file], {
      root: fx.root, cwd: fx.installation, env: { RBTV_AGENT_HOME: fx.home },
      stdout: (t) => { out += t; }, stderr: (t) => { err += t; },
    });
  } finally {
    sendModule.send = original;
    sendModule.senderOf = originalSender;
  }
  assert.equal(code, 0, err);
  assert.equal(seen.length, 2, 'two callers, two calls of the one send function');
  assert.deepEqual(seen.map((s) => s.operations), [['message.file', 'message.send'], ['message.file', 'message.send']]);
  assert.deepEqual(seen.map((s) => [s.input.text.length, s.input.files.length]), [[11_500, 1], [11_500, 1]]);
  assert.deepEqual([seen[0].input.group, seen[0].input.thread, seen[0].input.clientId], ['C1', '1.1', 'r1']);
  assert.equal(seen[1].input.contact, 'UOWNER');
  // Each connector saw the text posted as text, then the file: the one function's policy, in both callers.
  assert.deepEqual(slack.calls.map((c) => c.split(' ')[0]), ['post', 'upload']);
  assert.deepEqual(global.__divergenceCalls.map((c) => c.op), ['message.send', 'message.file']);
  assert.equal(global.__divergenceCalls[0].text.length, 11_500);
  assert.equal(JSON.parse(out).id, '8.1');
  // The sender's name and avatar come from the one routine, for both callers.
  assert.deepEqual(named, [fx.home, fx.home], 'both callers name the sender through sendModule.senderOf');
  assert.deepEqual(seen.map((s) => s.input.as), [{ name: 'Brigid', avatar: ':owl:' }, { name: 'Brigid', avatar: ':owl:' }]);
  const row = store.db.prepare('SELECT * FROM outbox WHERE id=?').get('r1');
  assert.deepEqual([row.channel, row.ts, JSON.parse(row.posted)], ['C1', '9.1', ['9.1', '9.2']]);
});

test('a reply text over 12,000 characters is delivered as a file through the shared send function', async (store) => {
  const key = 'T1:C1:1.1';
  store.upsertConversation({ key, agent: 'master', workspace: 'T1', channel: 'C1', rootTs: '1.1' });
  store.enqueueOutbox({ id: 'long', conversationKey: key, payload: { text: 'y'.repeat(12001) } });
  const slack = markSlack();
  const [result] = await deliverPending(store, { slack });
  assert.equal(result.delivered, true);
  assert.equal(slack.calls.length, 1);
  assert.match(slack.calls[0], /^upload .*message\.md$/);
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
