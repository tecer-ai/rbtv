#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { Store } = require('./store.js');
const { dispatch, start, replayHeld } = require('./listener.js');
const { composeTurn } = require('./prompt.js');
const { writeHistory } = require('./history.js');
const wa = require('../../../../../connectors/whatsapp/capabilities/tools/whatsapp/lib/messaging.js');
const google = require('../../../../../connectors/google/capabilities/tools/google/lib/messaging.js');

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }
function child() {
  const { EventEmitter } = require('node:events');
  const proc = new EventEmitter();
  proc.stdout = new EventEmitter();
  proc.stderr = new EventEmitter();
  proc.stdin = { end() {} };
  proc.kill = () => { proc.killed = true; proc.emit('close', 0); };
  return proc;
}
function harness() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'phase3a-contract-'));
  const stores = new Map();
  const ctx = {
    config: { dmAgent: 'master', slack: { team: 'T1', ownerUserId: 'UOWNER' }, routes: {} },
    openStore(slug) {
      if (!stores.has(slug)) stores.set(slug, new Store(path.join(dir, slug, 'state.sqlite')));
      return stores.get(slug);
    },
    decisionFile: path.join(dir, 'decisions.jsonl'),
    subscriptionFile: path.join(dir, 'subscriptions.json'),
    threadFile: path.join(dir, 'threads.json'),
    defaults: { slackDm: 'master', mail: 'sara', whatsapp: 'master' },
    judge: async () => ({ yes: false }),
  };
  fs.writeFileSync(ctx.subscriptionFile, '[]');
  fs.writeFileSync(ctx.threadFile, '[]');
  return { dir, ctx, stores, close() { for (const store of stores.values()) store.close(); fs.rmSync(dir, { recursive: true, force: true }); } };
}
function owner(extra) {
  return {
    connector: 'slack', account: 'T1', id: '1.100000', from: 'UOWNER', conversation: 'D1', group: null,
    text: 'hello', identity: { verified: true, method: 'slack-socket', owner: true }, ...extra,
  };
}

test('rule change does not queue a second copy', async () => {
  const h = harness();
  try {
    await dispatch(owner({ id: '4.100000', text: 'once' }), h.ctx);
    fs.writeFileSync(h.ctx.subscriptionFile, JSON.stringify([{ id: 'later', connector: 'slack', account: 'T1', group: null, contact: 'UOWNER', agent: 'gaming', judge: null }]));
    const again = await dispatch(owner({ id: '4.100000', text: 'once' }), h.ctx);
    const queues = [...h.stores.entries()].flatMap(([slug, store]) => store.db.prepare('SELECT id FROM queue').all().map((row) => slug + row.id));
    assert.equal(again.queued, false);
    assert.equal(queues.length, 1);
    assert.equal(queues[0].startsWith('master'), true);
  } finally { h.close(); }
});

test('ordinary inbound thread stays with its agent', async () => {
  const h = harness();
  try {
    await dispatch(owner({ id: '5.100000', text: 'root' }), h.ctx);
    fs.writeFileSync(h.ctx.subscriptionFile, JSON.stringify([{ id: 'later', connector: 'slack', account: 'T1', agent: 'gaming', judge: null }]));
    const reply = await dispatch(owner({ id: '5.200000', thread: '5.100000', text: 'reply' }), h.ctx);
    assert.equal(reply.agent, 'master');
    assert.equal([...h.stores.keys()].includes('gaming'), false);
  } finally { h.close(); }
});

test('affinity does not cross account or connector', async () => {
  const h = harness();
  try {
    fs.writeFileSync(h.ctx.threadFile, JSON.stringify([{ connector: 'whatsapp', account: '5511000000001', conversation: 'chat', thread: 'root', agent: 'sara' }]));
    const other = await dispatch({
      connector: 'whatsapp', account: '5511000000002', id: 'next', from: '5511911112222', conversation: 'chat', thread: 'root', text: 'other',
      identity: { verified: true, method: 'webhook-secret', owner: true },
    }, h.ctx);
    const slack = await dispatch(owner({ id: '6.200000', thread: 'root', conversation: 'chat', text: 'slack' }), h.ctx);
    assert.equal(other.agent, 'master');
    assert.notEqual(slack.agent, 'sara');
  } finally { h.close(); }
});

test('same native id on two connectors both queue', async () => {
  const h = harness();
  try {
    const slack = await dispatch(owner({ id: 'same', conversation: 'room', text: 'slack' }), h.ctx);
    const mail = await dispatch({
      connector: 'google', account: 'owner@example.com', id: 'same', from: 'owner@example.com', conversation: 'room', text: 'mail',
      identity: { verified: true, method: 'gmail-account', owner: true },
    }, h.ctx);
    assert.equal(slack.queued, true);
    assert.equal(mail.queued, true);
  } finally { h.close(); }
});

test('corrupt subscriptions are logged and held', async () => {
  const h = harness();
  try {
    fs.writeFileSync(h.ctx.subscriptionFile, '{');
    const result = await dispatch(owner({ id: '7.100000' }), h.ctx);
    const lines = fs.readFileSync(h.ctx.decisionFile, 'utf8');
    assert.equal(result.ignored, 'subscriptions-invalid');
    assert.equal(result.queued, false);
    assert.match(lines, /invalid/);
    const held = JSON.parse(fs.readFileSync(`${h.ctx.decisionFile}.hold`, 'utf8'));
    assert.equal(held.length, 1);
  } finally { h.close(); }
});

test('a held judgment is replayed and not sent to the default', async () => {
  const h = harness();
  try {
    fs.writeFileSync(h.ctx.subscriptionFile, JSON.stringify([{ id: 'theme', connector: 'slack', account: 'T1', agent: 'gaming', judge: { question: 'theme?' } }]));
    h.ctx.judge = async () => { throw new Error('timeout'); };
    const held = await dispatch(owner({ id: '8.100000', text: 'hold me' }), h.ctx);
    assert.equal(held.ignored, 'judgment-error');
    h.ctx.judge = async () => ({ yes: true });
    const file = `${h.ctx.decisionFile}.hold`;
    const rows = JSON.parse(fs.readFileSync(file, 'utf8'));
    rows[0].nextAt = 0;
    fs.writeFileSync(file, JSON.stringify(rows));
    await replayHeld(h.ctx);
    assert.equal(h.stores.has('gaming'), true);
    assert.equal(h.stores.has('master'), false);
  } finally { h.close(); }
});

test('prompt and history keep service provenance and do not call it a Slack timestamp', async () => {
  const h = harness();
  try {
    await dispatch({
      connector: 'google', account: 'owner@example.com', id: 'm1', from: 'owner@example.com', claimedFrom: 'owner@example.com',
      conversation: 'thread-1', text: 'mail body', identity: { verified: true, method: 'gmail-account', owner: true },
    }, h.ctx);
    const store = h.stores.get('sara');
    const home = path.join(h.dir, 'sara-home');
    fs.mkdirSync(home, { recursive: true });
    const key = store.db.prepare('SELECT key FROM conversations').get().key;
    const history = fs.readFileSync(writeHistory(home, store, key), 'utf8');
    assert.match(history, /google id m1/);
    assert.doesNotMatch(history, /Slack timestamp/);
    const prompt = composeTurn({
      board: 'board', work: {}, inputs: [{ role: 'owner', text: 'mail body', ts: 'm1', connector: 'google', provenance: { connector: 'google', account: 'owner@example.com', conversation: 'thread-1', claimed: 'owner@example.com', trusted: true } }],
      recent: [], stored: [], historyPath: 'h', resultPath: 'r', nonce: 'n',
    });
    assert.match(prompt, /Source: google account owner@example.com/);
    assert.match(prompt, /sender trusted/);
    assert.doesNotMatch(prompt, /Slack timestamp/);
  } finally { h.close(); }
});

test('signed wacli payload is accepted and a lowercase invention is not', async () => {
  const seen = [];
  const listening = await wa.listen({ secret: 's', owner: '5511911112222', account: '5511999990000', port: 0, onEvent: (event) => seen.push(event) });
  try {
    const payload = { Chat: '5511911112222@s.whatsapp.net', ID: 'MID', SenderJID: '5511911112222@s.whatsapp.net', Timestamp: '2026-10-17T00:00:00Z', FromMe: false, Text: 'hello', ReplyToID: 'ROOT' };
    const raw = Buffer.from(JSON.stringify(payload));
    const sig = crypto.createHmac('sha256', 's').update(raw).digest('hex');
    const status = await new Promise((resolve, reject) => {
      const req = http.request({ host: '127.0.0.1', port: listening.port, path: '/whatsapp', method: 'POST', headers: { 'x-wacli-signature': `sha256=${sig}`, 'content-length': raw.length } }, (res) => resolve(res.statusCode));
      req.on('error', reject);
      req.end(raw);
    });
    assert.equal(status, 200);
    assert.equal(seen[0].thread, 'ROOT');
    assert.equal(seen[0].text, 'hello');
    const lower = Buffer.from(JSON.stringify({ text: 'no identity' }));
    const lowerSig = crypto.createHmac('sha256', 's').update(lower).digest('hex');
    const rejected = await new Promise((resolve, reject) => {
      const req = http.request({ host: '127.0.0.1', port: listening.port, path: '/whatsapp', method: 'POST', headers: { 'x-wacli-signature': lowerSig, 'content-length': lower.length } }, (res) => resolve(res.statusCode));
      req.on('error', reject);
      req.end(lower);
    });
    assert.equal(rejected, 400, 'a payload without Chat and ID is not the wacli message');
  } finally { await listening.close(); }
});

test('whatsapp send and history use the real command grammar', async () => {
  const argv = [];
  const spawn = (command, args) => {
    argv.push([command, ...args]);
    const proc = child();
    const send = args.includes('send');
    const body = send
      ? JSON.stringify({ success: true, data: { sent: true, to: '5511911112222@s.whatsapp.net', id: 'OUT' }, error: null })
      : JSON.stringify({ success: true, data: { authenticated: true, phone: '5511999990000', linked_jid: '5511999990000@s.whatsapp.net' }, error: null });
    if (args.includes('list')) {
      process.nextTick(() => {
        proc.stdout.emit('data', JSON.stringify({ success: true, data: { messages: [{ MsgID: 'ROOT', ChatJID: '5511911112222@s.whatsapp.net', SenderJID: '5511911112222@s.whatsapp.net', Text: 'root', Timestamp: '2026-10-17T00:00:00Z', FromMe: false }, { MsgID: 'REPLY', quoted_msg_id: 'ROOT', ChatJID: '5511911112222@s.whatsapp.net', SenderJID: '5511911112222@s.whatsapp.net', Text: 'reply', Timestamp: '2026-10-17T00:01:00Z', FromMe: false }] }, error: null }));
        proc.emit('close', 0);
      });
      return proc;
    }
    process.nextTick(() => { proc.stdout.emit('data', body); proc.emit('close', 0); });
    return proc;
  };
  const ctx = { account: '5511999990000', owner: '5511911112222', installation: fs.mkdtempSync(path.join(os.tmpdir(), 'wa-store-')), spawn };
  const sent = await wa.operations['message.send']({ contact: '5511911112222', thread: 'ROOT', text: 'pong' }, ctx);
  assert.equal(sent.id, 'OUT');
  assert.equal(argv.some((row) => row.includes('--message-id')), false);
  assert.equal(argv.some((row) => row.includes('--reply-to') && row.includes('ROOT')), true);
  assert.equal(argv.some((row) => row.includes('--store')), true);
  const history = await wa.operations['message.history']({ conversation: '5511911112222@s.whatsapp.net', thread: 'ROOT' }, ctx);
  assert.equal(history.events.length, 2);
  assert.equal(argv.some((row) => row.includes('--query')), false);
  fs.rmSync(ctx.installation, { recursive: true, force: true });
});

test('gmail send parses the real id line and keeps the thread', async () => {
  const argv = [];
  const spawn = (command, args) => {
    argv.push(args);
    const proc = child();
    let out = 'MAILBOX sara@example.com\n';
    let stdout = '[]';
    if (args.includes('--thread-id') && args.includes('read')) stdout = JSON.stringify({ threadId: 'thread-1', messages: [{ id: 'm-src', threadId: 'thread-1', from: 'owner@example.com', to: 'sara@example.com', subject: 'Hello', sender_verification: { trusted: true, address: 'owner@example.com', mailbox: 'sara@example.com' } }] });
    if (args.includes('draft')) stdout = 'Draft created: id=draft-9\n';
    if (args.includes('send') && args.includes('--draft-id')) stdout = 'Sent! Message ID: sent-9\nThread ID: thread-9\n';
    process.nextTick(() => { proc.stderr.emit('data', out); proc.stdout.emit('data', stdout); proc.emit('close', 0); });
    return proc;
  };
  const section = { account: 'review', mailbox: 'sara@example.com', owner: 'owner@example.com' };
  const sent = await google.operations['message.send']({ thread: 'thread-1', text: 'reply body' }, { section, spawn });
  assert.equal(sent.id, 'sent-9');
  assert.equal(sent.thread, 'thread-9');
  assert.equal(argv.some((row) => row[0] === '--json'), false);
  assert.equal(argv.some((row) => row.includes('--reply-to-message-id') && row.includes('m-src')), true);
  assert.equal(argv.some((row) => row.includes('--to') && row.includes('owner@example.com')), true);
});

test('poll drains more than one page, keeps a held message, and an empty poll does not divide the watermark', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gmail-page-'));
  const cursorFile = path.join(dir, 'cursor.json');
  const section = { account: 'review', mailbox: 'sara@example.com', owner: 'owner@example.com' };
  let page = 0;
  const spawn = (command, args) => {
    const proc = child();
    const limit = args.includes('--message-id');
    let stdout = '[]';
    if (args.includes('--query') && args[args.indexOf('--query') + 1].includes('before:')) page = 1;
    if (!limit && args.includes('--query')) {
      const rows = page === 0
        ? Array.from({ length: 100 }, (_, i) => ({ id: `n${i}`, threadId: `t${i}`, internalDate: String(1_800_000_000_000 - i * 1000), snippet: 'short' }))
        : [{ id: 'old', threadId: 'told', internalDate: '1790000000000', snippet: 'short' }];
      stdout = JSON.stringify(rows);
    }
    if (limit) {
      const id = args[args.indexOf('--message-id') + 1];
      stdout = JSON.stringify({ id, threadId: `t-${id}`, internalDate: id === 'old' ? '1790000000000' : '1800000000000', body_plain: 'x'.repeat(1100), from: 'owner@example.com', sender_verification: { trusted: true, address: 'owner@example.com', mailbox: 'sara@example.com' } });
    }
    process.nextTick(() => { proc.stderr.emit('data', 'MAILBOX sara@example.com\n'); proc.stdout.emit('data', stdout); proc.emit('close', 0); });
    return proc;
  };
  const seen = [];
  await google.poll({
    section, cursorFile, spawn, onEvent: async (event) => {
      seen.push(event.id);
      if (event.id === 'n99') return { ignored: 'judgment-error' };
      return { queued: true };
    },
  });
  assert.equal(seen.includes('old'), true);
  assert.equal(seen.filter((id) => id === 'n0').length, 1);
  const cursor = JSON.parse(fs.readFileSync(cursorFile, 'utf8'));
  assert.equal(cursor.held.some((row) => row.id === 'n99'), true);
  assert.equal(cursor.afterMs < 1_800_000_000_000, true);
  const before = cursor.afterMs;
  await google.poll({ section, cursorFile, spawn: () => {
    const proc = child();
    process.nextTick(() => { proc.stderr.emit('data', 'MAILBOX sara@example.com\n'); proc.stdout.emit('data', '[]'); proc.emit('close', 0); });
    return proc;
  }, onEvent: async () => ({ queued: true }) });
  const after = JSON.parse(fs.readFileSync(cursorFile, 'utf8'));
  assert.equal(after.afterMs, before);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('polls do not overlap and stop waits for the child to exit', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gmail-stop-'));
  let started = 0;
  let killed = 0;
  const session = await start({
    config: {
      workspace: dir,
      listeners: { google: { account: 'review', mailbox: 'sara@example.com', owner: 'owner@example.com', agent: 'sara', pollMs: 10 } },
    },
    decisionFile: path.join(dir, 'decisions.jsonl'),
    subscriptionFile: path.join(dir, 'subscriptions.json'),
    threadFile: path.join(dir, 'threads.json'),
    defaults: { mail: 'sara' },
    openStore() { throw new Error('no store'); },
    spawn() {
      started += 1;
      const proc = child();
      const orig = proc.kill;
      proc.kill = () => { killed += 1; orig(); };
      return proc;
    },
  });
  await new Promise((resolve) => setTimeout(resolve, 40));
  assert.equal(started, 1);
  await session.stop();
  assert.equal(killed > 0, true);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('real typesafe yesno --json is the judge argv', async () => {
  const server = http.createServer((req, res) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', () => {
      const body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
      const noul = String(body.state || '').includes('no') ? 0.1 : 0.9;
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ model: 'fixture', answers: { answer: { type: 'noul', noul } } }));
    });
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const previous = { base: process.env.TYPESAFE_BASE_URL, key: process.env.TYPESAFE_API_KEY };
  process.env.TYPESAFE_BASE_URL = `http://127.0.0.1:${server.address().port}`;
  process.env.TYPESAFE_API_KEY = 'fixture';
  const h = harness();
  delete h.ctx.judge;
  try {
    fs.writeFileSync(h.ctx.subscriptionFile, JSON.stringify([{ id: 'theme', connector: 'slack', account: 'T1', agent: 'gaming', judge: { question: 'Is this urgent?' } }]));
    const yes = await dispatch(owner({ id: '9.100000', text: 'yes please' }), h.ctx);
    assert.equal(yes.agent, 'gaming');
  } finally {
    if (previous.base == null) delete process.env.TYPESAFE_BASE_URL; else process.env.TYPESAFE_BASE_URL = previous.base;
    if (previous.key == null) delete process.env.TYPESAFE_API_KEY; else process.env.TYPESAFE_API_KEY = previous.key;
    server.close();
    h.close();
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
  const repo = path.resolve(__dirname, '../../../../..');
  const py = spawnSync(path.join(repo, 'connectors/google/repository/.venv/bin/python'), [path.join(repo, 'connectors/google/capabilities/tools/google/test_gmail_loopback.py')], { encoding: 'utf8' });
  process.stdout.write(py.stdout || '');
  if (py.status !== 0) {
    failed += 1;
    process.stdout.write(`FAIL gmail-loopback: ${py.stderr}\n`);
  }
  process.stdout.write(`phase3a-contract: ${tests.length - failed} passed, ${failed} failed\n`);
  process.exit(failed ? 1 : 0);
})();
