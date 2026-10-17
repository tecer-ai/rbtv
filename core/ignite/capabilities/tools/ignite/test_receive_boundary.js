#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { Store } = require('./store.js');
const { dispatch, fromSocket } = require('./listener.js');
const { listen, signature, HEADER } = require('../../../../../connectors/whatsapp/capabilities/tools/whatsapp/lib/messaging.js');
const google = require('../../../../../connectors/google/capabilities/tools/google/lib/messaging.js');
const { deliverPending } = require('./outbox.js');
const { start } = require('./daemon.js');
const { EMPTY_BOARD, boardPath } = require('./board.js');

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

function post(port, body, headers) {
  return new Promise((resolve, reject) => {
    const data = Buffer.from(body);
    const req = http.request({
      host: '127.0.0.1', port, path: '/whatsapp', method: 'POST',
      headers: { 'content-type': 'application/json', 'content-length': data.length, ...headers },
    }, (res) => {
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => resolve({ status: res.statusCode, body: Buffer.concat(chunks).toString('utf8') }));
    });
    req.on('error', reject);
    req.end(data);
  });
}

test('webhook secret is checked before dispatch and identity is not taken from the body', async () => {
  const seen = [];
  const rejected = [];
  const listening = await listen({
    secret: 'hook-secret', owner: '5511911112222', account: '5511999990000', port: 0,
    onEvent: (event) => { seen.push(event); },
    onReject: (row) => { rejected.push(row); },
  });
  try {
    const body = JSON.stringify({ Chat: '5511911112222@s.whatsapp.net', ID: 'm1', SenderJID: '5511911112222@s.whatsapp.net', Text: 'ping', Timestamp: '2026-10-17T00:00:00Z', FromMe: false, identity: { owner: true, verified: true } });
    const wrong = await post(listening.port, body, { [HEADER]: 'sha256=00' });
    assert.equal(wrong.status, 401);
    assert.equal(seen.length, 0);
    assert.equal(rejected[0].reason, 'unverified');
    const right = await post(listening.port, body, { [HEADER]: `sha256=${signature('hook-secret', Buffer.from(body))}` });
    assert.equal(right.status, 200);
    assert.equal(seen.length, 1);
    assert.equal(seen[0].identity.owner, true);
    assert.equal(seen[0].identity.method, 'webhook-secret');
    assert.equal(seen[0].from, '5511911112222');
    const forged = JSON.stringify({ Chat: '15550001111@s.whatsapp.net', ID: 'm2', SenderJID: '5511888887777@s.whatsapp.net', Text: 'no', FromMe: false, identity: { owner: true } });
    await post(listening.port, forged, { [HEADER]: signature('hook-secret', Buffer.from(forged)) });
    assert.equal(seen[1].identity.owner, false);
    assert.equal(seen[1].from, '5511888887777');
  } finally {
    await listening.close();
  }
});

test('gmail owner is the verified sender, not the From header, and the cursor survives reopen', async () => {
  const section = { account: 'sara-mail', mailbox: 'sara@example.com', owner: 'owner@example.com', agent: 'sara' };
  const forged = google.eventOf({ id: 'a', threadId: 'a', from: 'owner@example.com', date: '2026-10-16T00:00:00Z', sender_verification: { trusted: false, address: 'owner@example.com', reason: 'authentication-results-missing' } }, section);
  assert.equal(forged.identity.owner, false);
  assert.equal(forged.identity.verified, false);
  const trusted = google.eventOf({ id: 'b', threadId: 't', from: 'pia@example.com', date: '2026-10-16T00:00:00Z', sender_verification: { trusted: true, address: 'owner@example.com', reason: 'trusted' }, body_plain: 'hello' }, section);
  assert.equal(trusted.identity.owner, true);
  assert.equal(trusted.from, 'owner@example.com');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gmail-cursor-'));
  const cursorFile = path.join(dir, 'cursor.json');
  const calls = [];
  const spawn = () => {
    const { EventEmitter } = require('node:events');
    const child = new EventEmitter();
    child.stdout = new EventEmitter();
    child.stderr = new EventEmitter();
    child.stdin = { end() {} };
    child.kill = () => {};
    calls.push(1);
    const body = JSON.stringify([{ id: 'b', threadId: 't', internalDate: '1792195200000', from: 'owner@example.com', sender_verification: { trusted: true, address: 'owner@example.com', mailbox: 'sara@example.com', reason: 'trusted' }, body_plain: 'hello' }]);
    process.nextTick(() => {
      child.stdout.emit('data', body);
      child.stderr.emit('data', 'MAILBOX sara@example.com\n');
      child.emit('close', 0);
    });
    return child;
  };
  const events = [];
  await google.poll({ section, cursorFile, spawn, onEvent: async (event) => { events.push(event); return { queued: true }; } });
  await google.poll({ section, cursorFile, spawn, onEvent: async (event) => { events.push(event); return { queued: true }; } });
  assert.equal(events.length, 1);
  assert.equal(JSON.parse(fs.readFileSync(cursorFile, 'utf8')).seen.includes('b'), true);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('a new process rereads subscriptions and does not duplicate another account', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'receive-reopen-'));
  const subscriptionFile = path.join(dir, 'subscriptions.json');
  const script = path.join(dir, 'once.js');
  fs.writeFileSync(subscriptionFile, JSON.stringify([{ id: 'kept', connector: 'slack', account: 'T1', group: 'CCHAN', contact: 'UOWNER', agent: 'gaming', judge: null }]));
  fs.writeFileSync(script, `'use strict';
const { dispatch } = require(${JSON.stringify(path.join(__dirname, 'listener.js'))});
const { Store } = require(${JSON.stringify(path.join(__dirname, 'store.js'))});
const fs = require('node:fs');
const store = new Store(${JSON.stringify(path.join(dir, 'gaming', 'state.sqlite'))});
dispatch({
  connector: 'slack', account: 'T1', id: process.argv[2], at: 1, from: 'UOWNER', group: 'CCHAN', conversation: 'CCHAN', thread: null,
  text: process.argv[3], files: [], isSelf: false, identity: { verified: true, method: 'slack-socket', owner: true },
}, {
  config: { dmAgent: 'master', slack: { ownerUserId: 'UOWNER' }, routes: { CCHAN: 'probe' } },
  openStore() { return store; },
  subscriptionFile: ${JSON.stringify(subscriptionFile)},
  decisionFile: ${JSON.stringify(path.join(dir, 'decisions.jsonl'))},
  threadFile: ${JSON.stringify(path.join(dir, 'threads.json'))},
  defaults: { mail: 'sara' },
  judge: async () => ({ yes: false }),
}).then((result) => { store.close(); process.stdout.write(JSON.stringify(result)); });
`);
  const first = spawnSync(process.execPath, [script, '9.100000', 'after reopen'], { encoding: 'utf8' });
  const second = spawnSync(process.execPath, [script, '9.100000', 'after reopen'], { encoding: 'utf8' });
  const other = spawnSync(process.execPath, [script, '9.100000', 'other account'], { encoding: 'utf8', env: { ...process.env } });
  assert.equal(first.status, 0, first.stderr);
  assert.equal(JSON.parse(first.stdout).agent, 'gaming');
  assert.equal(JSON.parse(second.stdout).queued, false);
  const store = new Store(path.join(dir, 'gaming', 'state.sqlite'));
  try {
    assert.equal(store.db.prepare('SELECT COUNT(*) AS n FROM queue').get().n, 1);
  } finally { store.close(); }
  fs.writeFileSync(subscriptionFile, JSON.stringify([
    { id: 'a', connector: 'whatsapp', account: '5511000000001', group: null, contact: '5511911112222', agent: 'gaming', judge: null },
  ]));
  const wa = path.join(dir, 'wa.js');
  fs.writeFileSync(wa, `'use strict';
const { dispatch } = require(${JSON.stringify(path.join(__dirname, 'listener.js'))});
const { Store } = require(${JSON.stringify(path.join(__dirname, 'store.js'))});
const account = process.argv[2];
const store = new Store(${JSON.stringify(path.join(dir, 'gaming', 'state.sqlite'))});
dispatch({
  connector: 'whatsapp', account, id: '111.111000', at: 2, from: '5511911112222', group: null,
  conversation: account + '@s.whatsapp.net', thread: null, text: account, files: [], isSelf: false,
  identity: { verified: true, method: 'webhook-secret', owner: true },
}, {
  config: { dmAgent: 'master', routes: {} },
  openStore() { return store; },
  subscriptionFile: ${JSON.stringify(subscriptionFile)},
  decisionFile: ${JSON.stringify(path.join(dir, 'decisions.jsonl'))},
  defaults: {},
}).then((result) => { store.close(); process.stdout.write(JSON.stringify({ queued: result.queued, account })); });
`);
  const one = spawnSync(process.execPath, [wa, '5511000000001'], { encoding: 'utf8' });
  const two = spawnSync(process.execPath, [wa, '5511000000002'], { encoding: 'utf8' });
  assert.equal(JSON.parse(one.stdout).queued, true, one.stderr);
  assert.equal(JSON.parse(two.stdout).queued, true, two.stderr);
  const again = new Store(path.join(dir, 'gaming', 'state.sqlite'));
  try {
    const texts = again.db.prepare('SELECT text FROM messages').all().map((row) => row.text);
    assert.equal(texts.includes('5511000000001'), true);
    assert.equal(texts.includes('5511000000002'), true);
  } finally { again.close(); fs.rmSync(dir, { recursive: true, force: true }); }
  assert.equal(other.status, 0);
});

test('a reply leaves through the connector stored on the message, not the Slack client', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'receive-outbox-'));
  const store = new Store(path.join(dir, 'state.sqlite'));
  const sent = [];
  try {
    store.acceptOwnerInput({
      key: '5511999990000:5511911112222@s.whatsapp.net:m1',
      agent: 'sara', workspace: '5511999990000', channel: '5511911112222@s.whatsapp.net', rootTs: 'm1', activated: true,
      message: {
        id: 'whatsapp:5511999990000:5511911112222@s.whatsapp.net:m1', role: 'owner', text: 'hi', files: [],
        team: '5511999990000', channel: '5511911112222@s.whatsapp.net', ts: 'm1', createdAt: 1,
        metadata: { connector: 'whatsapp', account: '5511999990000', from: '5511911112222', conversation: '5511911112222@s.whatsapp.net' },
      },
    });
    store.enqueueOutbox({ id: 'reply:1', conversationKey: '5511999990000:5511911112222@s.whatsapp.net:m1', payload: { text: 'pong' } });
    await deliverPending(store, {
      listeners: { whatsapp: { account: '5511999990000' } },
      slack: { async postMessage() { throw new Error('slack must not send this'); } },
      messaging: {
        whatsapp: {
          async 'message.send'(input) { sent.push(input); return { conversation: input.group, id: 'm2', thread: 'm1' }; },
          async 'message.file'() { throw new Error('no file'); },
        },
      },
    });
    assert.equal(sent.length, 1);
    assert.equal(sent[0].text, 'pong');
    assert.equal(sent[0].group, '5511911112222@s.whatsapp.net');
  } finally {
    store.close();
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('message send records the thread it started for affinity', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'receive-send-'));
  const installation = fs.mkdtempSync(path.join(os.tmpdir(), 'receive-send-inst-'));
  const lib = path.join(root, 'connectors', 'whatsapp', 'capabilities', 'tools', 'whatsapp', 'lib');
  fs.mkdirSync(lib, { recursive: true });
  fs.writeFileSync(path.join(root, 'connectors', 'whatsapp', 'whatsapp.json'), JSON.stringify({ description: 'wa', dependencies: [], type: 'messaging', provides: ['message.send'] }));
  fs.writeFileSync(path.join(lib, 'messaging.js'), `module.exports = {
    address(value) { return { contact: value }; },
    async account() { return '5511999990000'; },
    operations: { 'message.send': async () => ({ conversation: '5511911112222@s.whatsapp.net', id: 'm9', thread: null }) },
  };`);
  fs.mkdirSync(path.join(installation, '.rbtv', 'config', 'ignite'), { recursive: true });
  fs.writeFileSync(path.join(installation, '.rbtv', 'config', 'install.json'), JSON.stringify({ schema: 6, components: { 'connectors/whatsapp': {} } }));
  fs.writeFileSync(path.join(installation, '.rbtv', 'config', 'ignite', 'config.json'), JSON.stringify({
    slack: { team: 'T1', botUserId: 'UBOT', ownerUserId: 'UOWNER', appTokenEnv: 'A', botTokenEnv: 'B', ownerTokenEnv: 'C', stoolsWorkspace: 'w' },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' }, dmAgent: 'master', routes: {},
    listeners: { whatsapp: { account: '5511999990000', owner: '5511911112222', secretEnv: 'WACLI_WEBHOOK_SECRET' } },
  }));
  const home = path.join(installation, '.rbtv', 'agents', 'sara');
  fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({ name: 'sara', harness: 'claude', model: 'example', effort: 'low' }));
  fs.writeFileSync(path.join(home, 'prompt.md'), 'prompt\n');
  const { main } = require('../../../../../connectors/messaging/capabilities/tools/message/message.js');
  let out = '';
  const code = await main(['send', '--to', '5511911112222', '--via', 'whatsapp', 'hello'], {
    root, cwd: installation, env: { RBTV_AGENT_HOME: home }, stdout: (t) => { out += t; }, stderr: (t) => { out += t; },
  });
  assert.equal(code, 0, out);
  const rows = JSON.parse(fs.readFileSync(path.join(installation, '.rbtv', 'runtime', 'ignite', 'message-threads.json'), 'utf8'));
  assert.equal(rows[0].agent, 'sara');
  assert.equal(rows[0].via, 'message-send');
  assert.equal(rows[0].thread, 'm9');
  fs.rmSync(root, { recursive: true, force: true });
  fs.rmSync(installation, { recursive: true, force: true });
});

test('the socket path assigns identity from the configured owner and the daemon queues that event', async () => {
  const forged = fromSocket({ team: 'T1', channel: 'D1', channelType: 'im', ts: '1.100000', threadTs: '1.100000', user: 'UOTHER', text: 'x', identity: { verified: true, owner: true } }, { slack: { ownerUserId: 'UOWNER', team: 'T1' } });
  assert.equal(forged.identity.owner, false);
  assert.equal(forged.identity.verified, false);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'receive-daemon-'));
  const bin = path.join(dir, 'bin');
  fs.mkdirSync(bin, { recursive: true });
  for (const name of ['claude', 'ignite']) {
    fs.writeFileSync(path.join(bin, name), '#!/bin/sh\nexit 0\n');
    fs.chmodSync(path.join(bin, name), 0o755);
  }
  const configDir = path.join(dir, '.rbtv', 'config', 'ignite');
  fs.mkdirSync(configDir, { recursive: true });
  fs.writeFileSync(path.join(configDir, 'config.json'), JSON.stringify({
    slack: { team: 'T1', botUserId: 'UBOT', ownerUserId: 'UOWNER', appTokenEnv: 'A', botTokenEnv: 'B', ownerTokenEnv: 'C', stoolsWorkspace: 'ignite' },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' }, dmAgent: 'master', routes: {},
  }));
  const home = path.join(dir, '.rbtv', 'agents', 'master');
  fs.mkdirSync(path.join(home, 'memory'), { recursive: true });
  fs.writeFileSync(path.join(home, 'agent.json'), JSON.stringify({ harness: 'claude', model: 'example-model', effort: 'low' }));
  fs.writeFileSync(path.join(home, 'prompt.md'), '---\nname: master\n---\n');
  fs.mkdirSync(path.dirname(boardPath(home)), { recursive: true });
  fs.writeFileSync(boardPath(home), EMPTY_BOARD);
  fs.writeFileSync(path.join(home, 'memory', 'learned.md'), '# Learned rules — master\n');
  const prev = process.env.PATH;
  process.env.PATH = `${bin}${path.delimiter}${prev || ''}`;
  const socket = { onEvent: null, async connect(onEvent) { socket.onEvent = onEvent; }, stop() {} };
  let runtime;
  try {
    runtime = await start({ workspace: dir, slack: { async postMessage() { return { channel: 'D1', ts: '9.1' }; } }, socket, signals: false, tickMs: 60_000, sweepMs: 60_000, drainMs: 60_000 });
    const saved = await socket.onEvent({ team: 'T1', channel: 'D1', channelType: 'im', ts: '1.200000', threadTs: '1.200000', user: 'UOWNER', text: 'daemon ping', files: [], isBotOrSelf: false });
    assert.equal(saved.queued, true);
    assert.equal(saved.agent, 'master');
    const decisions = fs.readFileSync(path.join(dir, '.rbtv', 'runtime', 'ignite', 'decisions.jsonl'), 'utf8');
    assert.match(decisions, /"step":"default"/);
    const store = new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
    try {
      const row = store.db.prepare('SELECT metadata, text FROM messages').get();
      assert.equal(row.text, 'daemon ping');
      assert.equal(JSON.parse(row.metadata).connector, 'slack');
    } finally { store.close(); }
  } finally {
    process.env.PATH = prev;
    if (runtime) await runtime.stop('test');
    fs.rmSync(dir, { recursive: true, force: true });
  }
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
  process.stdout.write(`receive-boundary: ${tests.length - failed} passed, ${failed} failed\n`);
  process.exit(failed ? 1 : 0);
})();
