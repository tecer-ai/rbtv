#!/usr/bin/env node
'use strict';

// Suite for lib/messaging.js, the Slack connector's messaging adapter: each operation against a local stub
// of slack.com/api (SLACK_API_URL) that records every call and answers recorded bodies; the token read
// literally from a temporary installation's .env and never printed; the address and account helpers. No network.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');

const tests = [];
function test(name, fn) { tests.push([name, fn]); }

// An Asaas-style sentinel: a value a sourcing shell would expand away. It must arrive byte for byte.
const SENTINEL = 'xoxb-$SENTINEL$notreal';
const calls = [];
const answers = {};

const server = http.createServer((req, res) => {
  let body = '';
  req.on('data', (c) => { body += c; });
  req.on('end', () => {
    const method = req.url.replace(/^\//, '').split('?')[0];
    const params = Object.fromEntries(new URLSearchParams(body));
    calls.push({ method, params, auth: req.headers.authorization, type: req.headers['content-type'] });
    if (method === 'upload') { res.writeHead(200); res.end('OK'); return; }
    const answer = answers[method] ? answers[method](params, calls) : { ok: false, error: 'undeclared' };
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify(answer));
  });
});

let adapter;
let installation;

async function setup() {
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  process.env.SLACK_API_URL = `http://127.0.0.1:${server.address().port}`;
  delete process.env.SLACK_BOT_TOKEN;
  installation = fs.mkdtempSync(path.join(os.tmpdir(), 'slack-adapter-'));
  fs.mkdirSync(path.join(installation, '.rbtv', 'config', 'env'), { recursive: true });
  fs.writeFileSync(path.join(installation, '.rbtv', 'config', 'install.json'), '{}');
  fs.writeFileSync(path.join(installation, '.rbtv', 'config', 'env', '.env'), `OTHER=1\nSLACK_BOT_TOKEN=${SENTINEL}\n`);
  process.env.RBTV_AGENT_HOME = path.join(installation, '.rbtv', 'agents', 'sara');
  fs.mkdirSync(process.env.RBTV_AGENT_HOME, { recursive: true });
  adapter = require('./lib/messaging.js');
  answers['auth.test'] = () => ({ ok: true, team_id: 'T0BJAM8PACU', user_id: 'U0BOTSARA1', bot_id: 'B0BOT' });
}

test('the adapter exports the contract\'s shape and the port command\'s helpers', () => {
  for (const op of ['message.send', 'message.file', 'message.history', 'message.react', 'group.manage', 'approval.secure', 'message.receive']) {
    assert.equal(typeof adapter.operations[op], 'function', op);
  }
  assert.equal(typeof adapter.address, 'function');
  assert.equal(typeof adapter.account, 'function');
  assert.equal(adapter.TOKEN_ENV, 'SLACK_BOT_TOKEN');
});

test('address: a user id is a contact, a channel id a group, anything else refused with code address', () => {
  assert.deepEqual(adapter.address('U0OWNER001'), { contact: 'U0OWNER001' });
  assert.deepEqual(adapter.address('W0OWNER001'), { contact: 'W0OWNER001' });
  assert.deepEqual(adapter.address('C0SARA0001'), { group: 'C0SARA0001' });
  assert.deepEqual(adapter.address('D0OWNERDM1'), { group: 'D0OWNERDM1' });
  for (const [value, why] of [['pia@example.com', "slack addresses are a user id (U...) or a channel id (C...); a mail address is google's"], ['5511912345678', 'slack addresses are a user id (U...) or a channel id (C...); 5511912345678 is neither']]) {
    assert.throws(() => adapter.address(value), (error) => error.code === 'address' && error.message === why);
  }
});

test('message.send to a contact opens the direct conversation and posts markdown_text with the thread, client id and sender; the token arrives literally and is never printed', async () => {
  calls.length = 0;
  answers['conversations.open'] = (p) => ({ ok: true, channel: { id: 'D0OWNERDM1' } });
  answers['chat.postMessage'] = (p) => ({ ok: true, channel: p.channel, ts: '1792160000.000100' });
  const result = await adapter.operations['message.send']({ contact: 'U0OWNER001', thread: null, text: 'Receipt saved', as: { name: 'Sara', avatar: ':owl:' }, clientId: 'message:abc' });
  assert.deepEqual(result, { conversation: 'D0OWNERDM1', id: '1792160000.000100' });
  assert.deepEqual(calls.map((c) => c.method), ['conversations.open', 'chat.postMessage']);
  assert.equal(calls[0].params.users, 'U0OWNER001');
  assert.deepEqual(calls[1].params, { channel: 'D0OWNERDM1', markdown_text: 'Receipt saved', client_msg_id: 'message:abc', username: 'Sara', icon_emoji: ':owl:' });
  for (const call of calls) assert.equal(call.auth, `Bearer ${SENTINEL}`);
  calls.length = 0;
  const reply = await adapter.operations['message.send']({ group: 'D0OWNERDM1', thread: '1792160000.000100', text: 'Done.', clientId: 'message:def' });
  assert.deepEqual(reply, { conversation: 'D0OWNERDM1', id: '1792160000.000100' });
  assert.deepEqual(calls.map((c) => c.method), ['chat.postMessage']);
  assert.equal(calls[0].params.thread_ts, '1792160000.000100');
  await assert.rejects(adapter.operations['message.send']({ group: 'C1', text: '   ' }), /no_text/);
});

test('a Slack error becomes "slack answered <code>", with code thread for a thread it does not find; the process environment wins over .env', async () => {
  calls.length = 0;
  answers['chat.postMessage'] = (p) => ({ ok: false, error: 'thread_not_found' });
  await assert.rejects(adapter.operations['message.send']({ group: 'D0OWNERDM1', thread: '1792000000.000001', text: 'x' }),
    (error) => error.code === 'thread' && error.message === 'slack answered thread_not_found for 1792000000.000001 in D0OWNERDM1');
  answers['chat.postMessage'] = (p) => ({ ok: false, error: 'channel_not_found' });
  await assert.rejects(adapter.operations['message.send']({ group: 'C9', text: 'x' }), (error) => !error.code && error.message === 'slack answered channel_not_found');
  process.env.SLACK_BOT_TOKEN = 'xoxb-from-env';
  answers['chat.postMessage'] = (p) => ({ ok: true, channel: p.channel, ts: '1.1' });
  calls.length = 0;
  await adapter.operations['message.send']({ group: 'C1', text: 'x' });
  assert.equal(calls[0].auth, 'Bearer xoxb-from-env');
  delete process.env.SLACK_BOT_TOKEN;
});

test('message.file: the upload url, the bytes, the completion in the thread, as the agent; the share ts is the id', async () => {
  calls.length = 0;
  const file = path.join(installation, 'P-0003.pdf');
  fs.writeFileSync(file, '%PDF-1.4 fake');
  answers['files.getUploadURLExternal'] = () => ({ ok: true, upload_url: `${process.env.SLACK_API_URL}/upload`, file_id: 'F1' });
  answers['files.completeUploadExternal'] = () => ({ ok: true, files: [{ id: 'F1', name: 'P-0003.pdf', shares: { public: { D0OWNERDM1: [{ ts: '1792160000.000101' }] } } }] });
  const result = await adapter.operations['message.file']({ send: { conversation: 'D0OWNERDM1', thread: '1792160000.000100', file, as: { name: 'Sara' } } });
  assert.deepEqual(result, { id: '1792160000.000101', conversation: 'D0OWNERDM1' });
  assert.deepEqual(calls.map((c) => c.method), ['files.getUploadURLExternal', 'upload', 'files.completeUploadExternal']);
  assert.deepEqual(calls[0].params, { filename: 'P-0003.pdf', length: '13' });
  assert.equal(calls[2].params.channel_id, 'D0OWNERDM1');
  assert.equal(calls[2].params.thread_ts, '1792160000.000100');
  assert.equal(calls[2].params.username, 'Sara');
  assert.equal(JSON.parse(calls[2].params.files)[0].title, 'P-0003.pdf');
  calls.length = 0;
  answers['conversations.open'] = () => ({ ok: true, channel: { id: 'D0OWNERDM1' } });
  const direct = await adapter.operations['message.file']({ send: { contact: 'U0OWNER001', file } });
  assert.equal(direct.conversation, 'D0OWNERDM1');
  assert.equal(calls[0].method, 'conversations.open');
  await assert.rejects(adapter.operations['message.file']({ send: { conversation: 'C1', file: path.join(installation, 'missing.pdf') } }));
});

test('message.history: replies oldest first in the inbound event shape, paginated, a reply\'s id read as its thread; account from auth.test', async () => {
  calls.length = 0;
  const messages = [
    { ts: '1792160000.000100', user: 'U0BOTSARA1', text: 'Receipt saved: P-0003.pdf', channel_type: 'im' },
    { ts: '1792160030.000200', thread_ts: '1792160000.000100', user: 'U0OWNER001', text: 'Thanks.', files: [{ id: 'F2', name: 'a.png', mimetype: 'image/png', extra: 1 }] },
    { ts: '1792160060.000300', thread_ts: '1792160000.000100', user: 'U0BOTSARA1', text: 'Done.' },
  ];
  answers['conversations.replies'] = (p) => {
    if (p.ts === '1792160030.000200') return { ok: true, messages: [messages[1]] };
    if (!p.cursor) return { ok: true, messages: messages.slice(0, 2), response_metadata: { next_cursor: 'c2' } };
    return { ok: true, messages: messages.slice(2) };
  };
  const { events } = await adapter.operations['message.history']({ conversation: 'D0OWNERDM1', thread: '1792160000.000100' });
  assert.equal(events.length, 3);
  assert.deepEqual(events[1], {
    connector: 'slack', account: 'T0BJAM8PACU', id: '1792160030.000200', at: 1792160030000, from: 'U0OWNER001', group: null, conversation: 'D0OWNERDM1',
    thread: '1792160000.000100', text: 'Thanks.', files: [{ id: 'F2', name: 'a.png', mimetype: 'image/png' }], isSelf: false, raw: messages[1],
  });
  assert.deepEqual([events[0].thread, events[0].isSelf, events[2].isSelf], [null, true, true]);
  assert.deepEqual(calls.filter((c) => c.method === 'conversations.replies').map((c) => c.params.cursor || null), [null, 'c2']);
  calls.length = 0;
  const viaReply = await adapter.operations['message.history']({ conversation: 'D0OWNERDM1', thread: '1792160030.000200' });
  assert.equal(viaReply.events.length, 3, 'a reply\'s reference reads the whole thread');
  assert.deepEqual(calls.map((c) => c.params.ts), ['1792160030.000200', '1792160000.000100', '1792160000.000100']);
  answers['conversations.replies'] = () => ({ ok: false, error: 'thread_not_found' });
  await assert.rejects(adapter.operations['message.history']({ conversation: 'D0OWNERDM1', thread: '1.1' }), (error) => error.code === 'thread');
  assert.equal(await adapter.account(), 'T0BJAM8PACU');
  const group = await (async () => { answers['conversations.replies'] = () => ({ ok: true, messages: [{ ts: '2.2', user: 'U1', text: 'in a channel' }] }); return adapter.operations['message.history']({ conversation: 'C0SARA0001', thread: '2.2' }); })();
  assert.equal(group.events[0].group, 'C0SARA0001');
});

test('message.react, group.manage and approval.secure call the methods Ignite\'s client calls today; message.receive is refused until phase 4', async () => {
  calls.length = 0;
  for (const m of ['reactions.add', 'reactions.remove', 'conversations.join', 'conversations.invite', 'conversations.archive', 'chat.postEphemeral', 'views.open', 'views.push', 'views.update']) answers[m] = () => ({ ok: true });
  answers['conversations.create'] = () => ({ ok: true, channel: { id: 'C9' } });
  answers['chat.postMessage'] = (p) => ({ ok: true, channel: p.channel, ts: '3.3' });
  answers['chat.update'] = (p) => ({ ok: true, channel: p.channel, ts: p.ts });
  assert.deepEqual(await adapter.operations['message.react']({ conversation: 'C1', id: '1.1', name: 'eyes', add: true }), {});
  assert.deepEqual(await adapter.operations['message.react']({ conversation: 'C1', id: '1.1', name: 'eyes', add: false }), {});
  assert.deepEqual(await adapter.operations['group.manage']({ create: { name: 'agent-x' } }), { group: 'C9' });
  assert.deepEqual(await adapter.operations['group.manage']({ invite: { group: 'C9', contact: 'U1' } }), { group: 'C9' });
  assert.deepEqual(await adapter.operations['approval.secure']({ post: { conversation: 'C1', thread: '1.1', text: 't', blocks: [{ type: 'divider' }] } }), { conversation: 'C1', id: '3.3' });
  assert.deepEqual(await adapter.operations['approval.secure']({ update: { conversation: 'C1', id: '3.3', text: 't', blocks: [] } }), { conversation: 'C1', id: '3.3' });
  assert.deepEqual(await adapter.operations['approval.secure']({ open: { trigger: 'tr', view: { type: 'modal' } } }), {});
  assert.deepEqual(calls.map((c) => c.method), ['reactions.add', 'reactions.remove', 'conversations.create', 'conversations.invite', 'chat.postMessage', 'chat.update', 'views.open']);
  assert.deepEqual(calls[0].params, { channel: 'C1', timestamp: '1.1', name: 'eyes' });
  assert.equal(JSON.parse(calls[4].params.blocks)[0].type, 'divider');
  await assert.rejects(adapter.operations['message.receive']({ onEvent() {} }), /phase 4/);
});

(async () => {
  await setup();
  let failed = 0;
  for (const [name, fn] of tests) {
    try { await fn(); console.log(`PASS ${name}`); } catch (error) { failed += 1; console.log(`FAIL ${name}: ${error.message}`); }
  }
  server.close();
  process.exit(failed ? 1 : 0);
})();
