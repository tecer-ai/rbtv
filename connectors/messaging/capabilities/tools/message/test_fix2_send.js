#!/usr/bin/env node
'use strict';

// fix2-send lane suite: WhatsApp lifecycle/history and outgoing authorization/account binding, after
// the failed re-review of phase 3a (F2, F6, N1, N2 and the port half of F3).
//
// Everything runs the REAL production code: the `message` port command and Ignite's outbox in
// process, the WhatsApp adapter behind the real whatsapp.py wrapper and the real wacli binary
// (a synthetic local store; sends reach only this suite's Unix-delegate socket fixture), the Gmail
// port path behind the real google.py → gtools → gmail_* parsers redirected to a loopback-only
// HTTP service (sitecustomize patches discovery; the socket layer refuses non-loopback). Stand-ins
// replace service endpoints only, never the parser or adapter under test. No live service, no
// installed credential, no send outside this process's own fixtures.
//
// Run: node --test test_fix2_send.js   (from this folder; wacli 0.20.0 on PATH)

const assert = require('node:assert/strict');
const fs = require('node:fs');
const net = require('node:net');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');
const { spawn, spawnSync } = require('node:child_process');
const { DatabaseSync } = require('node:sqlite');

const REPO = path.resolve(__dirname, '..', '..', '..', '..', '..');
const WACLI = process.env.FIX2_WACLI_BIN || '/home/henri/.local/bin/wacli';
// The adapter starts `whatsapp` from PATH: put this checkout's wrapper first, so the test exercises
// the code under test and not the installed copy.
const WRAPPER_BIN = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-wrapper-'));
fs.symlinkSync(path.join(REPO, 'connectors/whatsapp/capabilities/tools/whatsapp/whatsapp.py'), path.join(WRAPPER_BIN, 'whatsapp'));
process.on('exit', () => fs.rmSync(WRAPPER_BIN, { recursive: true, force: true }));
const WA_ACCOUNT = '15550000001';
const WA_OWNER = '15550000002';
const WA_CHAT = `${WA_OWNER}@s.whatsapp.net`;
const BASE_S = 1792195200; // 2026-10-17T00:00:00Z

const ENV_KEYS = ['PATH', 'HOME', 'PYTHONDONTWRITEBYTECODE', 'PYTHONPATH', 'FIX2_GOOGLE_ROOT', 'FIX2_API', 'GOOGLE_TOOLS_CONFIG', 'FIX2_WA_PIDS', 'FIX2_WA_PHONE_FILE'];
const CHILDREN = new Set();

function job(child) { CHILDREN.add(child); child.on('exit', () => CHILDREN.delete(child)); return child; }
function reap() { for (const child of CHILDREN) { try { child.kill('SIGKILL'); } catch { /* gone */ } } }
process.on('exit', reap);

async function withEnv(env, fn) {
  const saved = Object.fromEntries(ENV_KEYS.map((key) => [key, process.env[key]]));
  for (const [key, value] of Object.entries(env)) process.env[key] = value;
  try { return await fn(); } finally {
    for (const key of ENV_KEYS) {
      if (saved[key] === undefined) delete process.env[key]; else process.env[key] = saved[key];
    }
  }
}

const alive = (pid) => { try { process.kill(pid, 0); return true; } catch { return false; } };

async function whenFile(file, timeoutMs = 20_000) {
  const started = Date.now();
  for (;;) {
    try {
      const text = fs.readFileSync(file, 'utf8');
      if (text.trim()) return text;
    } catch { /* absent or not written yet */ }
    if (Date.now() - started > timeoutMs) throw new Error(`timeout waiting for ${file}`);
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
}

function installationAt(dir, ignite = null, components = null) {
  fs.mkdirSync(path.join(dir, '.rbtv/config/ignite'), { recursive: true });
  fs.writeFileSync(path.join(dir, '.rbtv/config/install.json'), JSON.stringify(components || { schema: 6, components: { 'connectors/slack': {}, 'connectors/whatsapp': {}, 'connectors/google': {} } }));
  fs.writeFileSync(path.join(dir, '.rbtv/config/ignite/config.json'), JSON.stringify(ignite || { slack: { team: 'T1', ownerUserId: 'U0OWNER' }, routes: {} }));
  return dir;
}

function waStore(dir, phone = WA_ACCOUNT) {
  const store = path.join(dir, '.rbtv/runtime/whatsapp');
  fs.mkdirSync(store, { recursive: true });
  const db = new DatabaseSync(path.join(store, 'session.db'));
  db.exec('CREATE TABLE IF NOT EXISTS whatsmeow_device (jid TEXT)');
  db.prepare('INSERT INTO whatsmeow_device VALUES (?)').run(`${phone}:1@s.whatsapp.net`);
  db.close();
  return store;
}

function waRows(store, rows) {
  const list = spawnSync(WACLI, ['--store', store, '--json', 'messages', 'list', '--chat', WA_CHAT, '--limit', '1'], { env: process.env, encoding: 'utf8' });
  assert.equal(list.status, 0, `wacli store init failed: ${list.stdout} ${list.stderr}`);
  const db = new DatabaseSync(path.join(store, 'wacli.db'));
  db.prepare('INSERT OR REPLACE INTO chats(jid,kind,name) VALUES (?,?,?)').run(WA_CHAT, 'dm', 'Fixture Owner');
  const insert = db.prepare('INSERT OR REPLACE INTO messages(chat_jid,msg_id,sender_jid,ts,from_me,text,quoted_msg_id) VALUES (?,?,?,?,?,?,?)');
  for (const row of rows) insert.run(WA_CHAT, row.id, WA_CHAT, row.ts, 0, row.text, row.quoted || null);
  db.close();
}

const CHAIN = [
  { id: 'root', ts: BASE_S + 200, text: 'root text' },
  { id: 'reply', ts: BASE_S + 210, text: 'reply text', quoted: 'root' },
  { id: 'reply-chain', ts: BASE_S + 220, text: 'chain text', quoted: 'reply' },
];
const CHAIN_AT = CHAIN.map((row) => row.ts * 1000);

async function delegateServer(sockPath, requests) {
  try { fs.unlinkSync(sockPath); } catch { /* absent */ }
  const server = net.createServer((conn) => {
    let buffer = '';
    conn.on('data', (chunk) => {
      buffer += chunk;
      const at = buffer.indexOf('\n');
      if (at < 0) return;
      const request = JSON.parse(buffer.slice(0, at));
      buffer = buffer.slice(at + 1);
      requests.push(request);
      conn.write(`${JSON.stringify({ ok: true, sent: true, to: request.to, id: `fx-${requests.length}` })}\n`);
      conn.end();
    });
  });
  await new Promise((resolve) => server.listen(sockPath, resolve));
  return server;
}

function lockHolder(lockPath) {
  return job(spawn('python3', ['-c', 'import fcntl,sys,time\nf=open(sys.argv[1],"w")\nfcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)\nprint("held",flush=True)\ntime.sleep(600)', lockPath], { stdio: 'ignore' }));
}

// A sleeping wacli stand-in for the lifecycle tests: it answers auth status from a file the test
// controls (session revalidation) and otherwise parks as the wrapper's child, recording its pid.
function wacliStandIn(bin, pidsFile, phoneFile) {
  fs.mkdirSync(bin, { recursive: true });
  fs.symlinkSync(path.join(REPO, 'connectors/whatsapp/capabilities/tools/whatsapp/whatsapp.py'), path.join(bin, 'whatsapp'));
  const script = path.join(bin, 'wacli');
  fs.writeFileSync(script, `#!/usr/bin/env python3
import json, os, sys, time
args = sys.argv[1:]
if 'auth' in args and 'status' in args:
    phone = open(os.environ['FIX2_WA_PHONE_FILE']).read().strip() or '${WA_ACCOUNT}'
    print(json.dumps({'success': True, 'data': {'authenticated': True, 'phone': phone, 'linked_jid': phone + '@s.whatsapp.net'}, 'error': None}))
    raise SystemExit(0)
with open(os.environ['FIX2_WA_PIDS'], 'a') as f:
    f.write(str(os.getpid()) + chr(10))
time.sleep(600)
`);
  fs.chmodSync(script, 0o755);
  fs.writeFileSync(pidsFile, '');
  fs.writeFileSync(phoneFile, WA_ACCOUNT);
  return { bin, pidsFile, phoneFile };
}

const waAdapter = () => require(path.join(REPO, 'connectors/whatsapp/capabilities/tools/whatsapp/lib/messaging.js'));

// ── WhatsApp history (F2): ancestry, order, real timestamps, beyond one page ───────────────

test('whatsapp history returns the connected reply chain oldest first with its real timestamps', { timeout: 90_000 }, async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-hist-'));
  const installation = installationAt(path.join(work, 'inst'));
  const store = waStore(installation);
  waRows(store, CHAIN);
  const previous = process.cwd();
  process.chdir(installation);
  try {
    await withEnv({ PATH: `${WRAPPER_BIN}:${path.dirname(WACLI)}:${process.env.PATH}`, PYTHONDONTWRITEBYTECODE: '1' }, async () => {
      const adapter = waAdapter();
      for (const ref of ['root', 'reply', 'reply-chain']) {
        const result = await adapter.operations['message.history']({ conversation: WA_CHAT, thread: ref }, { installation, store, account: WA_ACCOUNT, owner: WA_OWNER });
        assert.deepEqual(result.events.map((event) => event.id), ['root', 'reply', 'reply-chain'], `referencing ${ref} resolves the whole connected chain`);
        assert.deepEqual(result.events.map((event) => event.at), CHAIN_AT, `referencing ${ref} keeps the stored timestamps`);
        assert.deepEqual(result.events.map((event) => event.text), ['root text', 'reply text', 'chain text']);
        assert.deepEqual(result.events.map((event) => event.thread), [null, 'root', 'reply']);
      }
      const whole = await adapter.operations['message.history']({ conversation: WA_CHAT }, { installation, store, account: WA_ACCOUNT, owner: WA_OWNER });
      assert.deepEqual(whole.events.map((event) => event.id), ['root', 'reply', 'reply-chain'], 'a chat read is oldest first');
    });
  } finally { process.chdir(previous); fs.rmSync(work, { recursive: true, force: true }); }
});

test('whatsapp history reaches a reply chain older than the 200-message window', { timeout: 120_000 }, async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-paged-'));
  const installation = installationAt(path.join(work, 'inst'));
  const store = waStore(installation);
  const rows = [];
  for (let i = 0; i < 205; i += 1) rows.push({ id: `f${String(i).padStart(3, '0')}`, ts: BASE_S + 300 + i, text: `filler ${i}` });
  rows.push(...CHAIN);
  waRows(store, rows);
  const previous = process.cwd();
  process.chdir(installation);
  try {
    await withEnv({ PATH: `${WRAPPER_BIN}:${path.dirname(WACLI)}:${process.env.PATH}`, PYTHONDONTWRITEBYTECODE: '1' }, async () => {
      const result = await waAdapter().operations['message.history']({ conversation: WA_CHAT, thread: 'reply' }, { installation, store, account: WA_ACCOUNT, owner: WA_OWNER });
      assert.deepEqual(result.events.map((event) => event.id), ['root', 'reply', 'reply-chain']);
      assert.deepEqual(result.events.map((event) => event.at), CHAIN_AT);
    });
  } finally { process.chdir(previous); fs.rmSync(work, { recursive: true, force: true }); }
});

test('whatsapp history refuses a thread the chat does not hold', { timeout: 90_000 }, async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-none-'));
  const installation = installationAt(path.join(work, 'inst'));
  const store = waStore(installation);
  waRows(store, CHAIN);
  const previous = process.cwd();
  process.chdir(installation);
  try {
    await withEnv({ PATH: `${WRAPPER_BIN}:${path.dirname(WACLI)}:${process.env.PATH}`, PYTHONDONTWRITEBYTECODE: '1' }, async () => {
      await assert.rejects(
        waAdapter().operations['message.history']({ conversation: WA_CHAT, thread: 'absent' }, { installation, store, account: WA_ACCOUNT, owner: WA_OWNER }),
        (error) => error.code === 'thread' && /thread_not_found/.test(error.message),
      );
    });
  } finally { process.chdir(previous); fs.rmSync(work, { recursive: true, force: true }); }
});

// ── Port-level WhatsApp send/reply authorization through the real wrapper and IPC (N1) ────

test('message send/reply via whatsapp authorizes the owner only and delivers through the delegate protocol', { timeout: 120_000 }, async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-waport-'));
  const installation = installationAt(path.join(work, 'inst'), {
    slack: { team: 'T1', ownerUserId: 'U0OWNER' }, routes: {},
    listeners: { whatsapp: { account: WA_ACCOUNT, owner: WA_OWNER } },
  });
  const store = waStore(installation);
  const requests = [];
  const server = await delegateServer(path.join(store, '.send.sock'), requests);
  const holder = lockHolder(path.join(store, 'LOCK'));
  const previous = process.cwd();
  process.chdir(installation);
  const message = require(path.join(REPO, 'connectors/messaging/capabilities/tools/message/message.js'));
  const run = async (argv) => {
    let out = '';
    let err = '';
    const code = await message.main(argv, { root: REPO, cwd: installation, env: {}, stdout: (t) => { out += t; }, stderr: (t) => { err += t; } });
    return { code, out, err };
  };
  try {
    await withEnv({ PATH: `${WRAPPER_BIN}:${path.dirname(WACLI)}:${process.env.PATH}`, PYTHONDONTWRITEBYTECODE: '1' }, async () => {
      const owner = await run(['send', '--via', 'whatsapp', '--to', WA_OWNER, 'owner hello']);
      assert.equal(owner.code, 0, owner.err);
      assert.match(owner.out, new RegExp(`Ref      whatsapp:${WA_ACCOUNT}:.*:fx-1`));
      assert.equal(requests.length, 1);
      assert.equal(requests[0].to, WA_OWNER);
      assert.equal(requests[0].message, 'owner hello');

      const before = requests.length;
      const outsider = await run(['send', '--via', 'whatsapp', '--to', '15550000003', 'leak']);
      assert.equal(outsider.code, 1);
      assert.match(outsider.err, /^message: send refused: no permission to message 15550000003\n/);
      assert.equal(requests.length, before, 'a refused send reaches no connector process');

      const group = await run(['send', '--via', 'whatsapp', '--to', '1203630234@g.us', 'group leak']);
      assert.equal(group.code, 1);
      assert.match(group.err, /^message: send refused: no permission to message 1203630234@g\.us\n/);

      const reply = await run(['reply', '--thread', `whatsapp:${WA_ACCOUNT}:${WA_CHAT}:root-msg`, 'owner reply']);
      assert.equal(reply.code, 0, reply.err);
      assert.equal(requests.length, 2);
      assert.equal(requests[1].reply_to, 'root-msg');
      assert.equal(requests[1].to, WA_CHAT);

      const foreign = await run(['reply', '--thread', 'whatsapp:15550000001:15550000003@s.whatsapp.net:root-msg', 'foreign reply']);
      assert.equal(foreign.code, 1);
      assert.match(foreign.err, /^message: reply refused: no permission to message 15550000003@s\.whatsapp\.net\n/);
      assert.equal(requests.length, 2, 'a refused reply reaches no connector process');
    });
  } finally {
    process.chdir(previous);
    holder.kill();
    server.close();
    fs.rmSync(work, { recursive: true, force: true });
  }
});

// ── Outbox account binding (N2) ────────────────────────────────────────────────────────────

test('the outbox never sends an old-account conversation through the current whatsapp account', { timeout: 120_000 }, async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-outbox-'));
  const installation = installationAt(path.join(work, 'inst'));
  const store = waStore(installation);
  const requests = [];
  const server = await delegateServer(path.join(store, '.send.sock'), requests);
  const holder = lockHolder(path.join(store, 'LOCK'));
  const { Store } = require(path.join(REPO, 'core/ignite/capabilities/tools/ignite/store.js'));
  const { dispatch } = require(path.join(REPO, 'core/ignite/capabilities/tools/ignite/listener.js'));
  const { deliverPending } = require(path.join(REPO, 'core/ignite/capabilities/tools/ignite/outbox.js'));
  const stores = new Map();
  const ctx = {
    config: { workspace: installation, dmAgent: 'master', routes: {} },
    subscriptionFile: path.join(installation, 'rules.json'),
    threadFile: path.join(installation, 'threads.json'),
    decisionFile: path.join(installation, 'decisions.jsonl'),
    openStore(slug) { if (!stores.has(slug)) stores.set(slug, new Store(path.join(installation, slug, 'state.sqlite'))); return stores.get(slug); },
  };
  fs.writeFileSync(ctx.subscriptionFile, '[]');
  fs.writeFileSync(ctx.threadFile, '[]');
  const section = { account: WA_ACCOUNT, owner: WA_OWNER };
  try {
    await withEnv({ PATH: `${WRAPPER_BIN}:${path.dirname(WACLI)}:${process.env.PATH}`, PYTHONDONTWRITEBYTECODE: '1' }, async () => {
      const route = async (name, account) => {
        const routed = await dispatch({
          connector: 'whatsapp', account, conversation: WA_CHAT, thread: `${name}-root`, id: `${name}-msg`, from: WA_OWNER, text: `via ${account}`,
          identity: { verified: true, method: 'webhook-secret', owner: true },
        }, ctx);
        const agent = stores.get(routed.agent);
        agent.enqueueOutbox({ id: `${name}-answer`, conversationKey: routed.key, payload: { text: `answer meant for ${account}` } });
        const outbox = await deliverPending(agent, { workspace: installation, listeners: { whatsapp: section } });
        const row = agent.db.prepare('SELECT state, last_error FROM outbox WHERE id=?').get(`${name}-answer`);
        return { outbox, row, key: routed.key };
      };
      const oldAccount = await route('old', '15550000009');
      assert.equal(oldAccount.outbox[0].delivered, false);
      assert.equal(oldAccount.outbox[0].stopped, true);
      assert.match(oldAccount.outbox[0].error, /belongs to account 15550000009.*current whatsapp account is 15550000001/);
      assert.notEqual(oldAccount.row.state, 'delivered');
      assert.equal(requests.filter((request) => request.message === 'answer meant for 15550000009').length, 0, 'no old-account answer is sent');

      const current = await route('current', WA_ACCOUNT);
      assert.equal(current.outbox[0].delivered, true, 'the current account still delivers');
      assert.equal(current.row.state, 'delivered');
      assert.equal(requests.filter((request) => request.message === 'answer meant for 15550000001').length, 1);
    });
  } finally {
    holder.kill();
    server.close();
    for (const open of stores.values()) open.close();
    fs.rmSync(work, { recursive: true, force: true });
  }
});

// ── Wrapper + wacli process tree lifecycle (F6) ───────────────────────────────────────────

test('supervise stop resolves only after the wrapper and its wacli child are gone', { timeout: 90_000 }, async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-life-'));
  const installation = installationAt(path.join(work, 'inst'));
  const store = waStore(installation);
  const { bin, pidsFile, phoneFile } = wacliStandIn(path.join(work, 'bin'), path.join(work, 'pids.txt'), path.join(work, 'phone.txt'));
  const previous = process.cwd();
  process.chdir(installation);
  try {
    await withEnv({ PATH: `${bin}:${process.env.PATH}`, PYTHONDONTWRITEBYTECODE: '1', FIX2_WA_PIDS: pidsFile, FIX2_WA_PHONE_FILE: phoneFile }, async () => {
      const sync = waAdapter().supervise({ store, secret: 's', port: 8791, account: WA_ACCOUNT, spawn: undefined });
      await whenFile(pidsFile);
      const pid = Number(fs.readFileSync(pidsFile, 'utf8').trim().split('\n').pop());
      assert.equal(alive(pid), true, 'the wrapper started its wacli child');
      await sync.stop();
      assert.equal(alive(pid), false, 'the wacli child exited before stop resolved');
    });
  } finally { process.chdir(previous); fs.rmSync(work, { recursive: true, force: true }); }
});

test('supervise respawns after a crash and stops for good when the session account changes', { timeout: 120_000 }, async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-respawn-'));
  const installation = installationAt(path.join(work, 'inst'));
  const store = waStore(installation);
  const { bin, pidsFile, phoneFile } = wacliStandIn(path.join(work, 'bin'), path.join(work, 'pids.txt'), path.join(work, 'phone.txt'));
  const states = [];
  const previous = process.cwd();
  process.chdir(installation);
  try {
    await withEnv({ PATH: `${bin}:${process.env.PATH}`, PYTHONDONTWRITEBYTECODE: '1', FIX2_WA_PIDS: pidsFile, FIX2_WA_PHONE_FILE: phoneFile }, async () => {
      const sync = waAdapter().supervise({ store, secret: 's', port: 8791, account: WA_ACCOUNT, spawn: undefined, onState: (state) => states.push(state) });
      await whenFile(pidsFile);
      const first = Number(fs.readFileSync(pidsFile, 'utf8').trim().split('\n').pop());
      process.kill(first, 'SIGKILL'); // the child crashes; the wrapper exits with it
      const respawnStart = Date.now();
      for (;;) {
        const pids = fs.readFileSync(pidsFile, 'utf8').trim().split('\n').filter(Boolean).map(Number);
        if (pids.length >= 2) {
          assert.notEqual(pids[1], first);
          break;
        }
        if (Date.now() - respawnStart > 20_000) assert.fail('no respawn after the child crashed');
        await new Promise((resolve) => setTimeout(resolve, 50));
      }

      fs.writeFileSync(phoneFile, '15550000009'); // the store's session changed to another account
      const second = Number(fs.readFileSync(pidsFile, 'utf8').trim().split('\n').filter(Boolean).pop());
      process.kill(second, 'SIGKILL');
      await new Promise((resolve) => setTimeout(resolve, 6_000));
      const pids = fs.readFileSync(pidsFile, 'utf8').trim().split('\n').filter(Boolean);
      assert.equal(pids.length, 2, 'no respawn through another account');
      assert.equal(sync.state(), 'failed');
      assert.ok(states.includes('failed'), `states seen: ${states.join(',')}`);
      await sync.stop();
    });
  } finally { process.chdir(previous); fs.rmSync(work, { recursive: true, force: true }); }
});

test('supervise retries a wrapper that cannot start yet', { timeout: 120_000 }, async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-spawn-'));
  const installation = installationAt(path.join(work, 'inst'));
  const store = waStore(installation);
  const pidsFile = path.join(work, 'pids.txt');
  const phoneFile = path.join(work, 'phone.txt');
  const bin = path.join(work, 'bin');
  fs.mkdirSync(bin, { recursive: true });
  fs.writeFileSync(pidsFile, '');
  fs.writeFileSync(phoneFile, WA_ACCOUNT);
  const previous = process.cwd();
  process.chdir(installation);
  try {
    await withEnv({ PATH: `${bin}:${process.env.PATH}`, PYTHONDONTWRITEBYTECODE: '1', FIX2_WA_PIDS: pidsFile, FIX2_WA_PHONE_FILE: phoneFile }, async () => {
      const sync = waAdapter().supervise({ store, secret: 's', port: 8791, account: WA_ACCOUNT, spawn: undefined });
      await new Promise((resolve) => setTimeout(resolve, 1_000));
      assert.equal(fs.readFileSync(pidsFile, 'utf8').trim(), ''); // nothing could start
      wacliStandIn(bin, pidsFile, phoneFile); // the wrapper appears (an install finishing)
      await whenFile(pidsFile, 20_000);
      const pid = Number(fs.readFileSync(pidsFile, 'utf8').trim().split('\n').pop());
      assert.equal(alive(pid), true);
      await sync.stop();
      assert.equal(alive(pid), false);
    });
  } finally { process.chdir(previous); fs.rmSync(work, { recursive: true, force: true }); }
});

// ── Gmail port authorization and thread binding (N1, port half of F3) ─────────────────────

function gmailService(state) {
  const calls = [];
  const b64 = (text) => Buffer.from(text).toString('base64').replace(/\+/g, '-').replace(/\//g, '_');
  const full = (id, tid, sender) => ({
    id, threadId: tid, internalDate: String((BASE_S + 1) * 1000), snippet: 'TRUNCATED', labelIds: ['INBOX'],
    payload: {
      mimeType: 'text/plain',
      headers: [
        ['Delivered-To', 'agent@example.com'],
        ['Received', 'from sender.example by mx.google.com with ESMTP id fixture'],
        ['Authentication-Results', `mx.google.com; dmarc=pass header.from=${sender.split('@')[1]}; dkim=pass header.d=${sender.split('@')[1]}`],
        ['From', sender], ['To', 'agent@example.com'], ['Date', 'Sat, 17 Oct 2026 00:00:00 +0000'],
        ['Subject', 'Fixture'], ['Message-ID', `<${id}@example.com>`],
      ].map(([name, value]) => ({ name, value })),
      body: { data: b64('Full owner text body') },
    },
  });
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://fixture');
    let raw = '';
    req.on('data', (chunk) => { raw += chunk; });
    req.on('end', () => {
      const parsed = raw ? JSON.parse(raw) : null;
      calls.push({ method: req.method, path: url.pathname, body: parsed });
      const sender = state.sender || 'owner@example.com';
      let out = {};
      let status = 200;
      if (url.pathname.endsWith('/profile')) out = { emailAddress: 'agent@example.com' };
      else if (url.pathname.endsWith('/drafts/send')) { state.sent = (state.sent || 0) + 1; out = { id: `sent-${state.sent}`, threadId: 't1', labelIds: ['SENT'] }; }
      else if (/\/drafts$/.test(url.pathname)) {
        state.drafts = state.drafts || [];
        state.drafts.push(parsed.message);
        out = { id: `draft-${state.drafts.length}`, message: { id: 'draft-message-1', threadId: parsed.message?.threadId || 'draft-thread' } };
      } else if (/\/threads\/[^/]+$/.test(url.pathname)) {
        const tid = url.pathname.split('/').pop();
        if (tid === 't1') out = { id: 't1', messages: [full('m1', 't1', sender)] };
        else if (tid === 't2') out = { id: 't2', messages: [full('m2', 't2', sender)] };
        else { status = 404; out = { error: { code: 404, message: 'thread not found' } }; }
      } else if (/\/messages\/[^/]+$/.test(url.pathname)) {
        const mid = url.pathname.split('/').pop();
        if (mid === 'm1') out = full('m1', 't1', sender);
        else if (mid === 'm2') out = full('m2', 't2', sender);
        else { status = 404; out = { error: { code: 404, message: 'not found' } }; }
      } else if (/\/messages$/.test(url.pathname)) out = { messages: [] };
      else { status = 404; out = { error: { code: 404, message: url.pathname } }; }
      const data = JSON.stringify(out);
      res.writeHead(status, { 'content-type': 'application/json' });
      res.end(data);
    });
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve({ server, calls, port: server.address().port })));
}

function gmailScratch(work) {
  const scratch = path.join(work, 'gm');
  const patch = path.join(scratch, 'patch');
  fs.mkdirSync(patch, { recursive: true });
  fs.writeFileSync(path.join(patch, 'sitecustomize.py'), `import json,os,socket,sys
from pathlib import Path
root=Path(os.environ['FIX2_GOOGLE_ROOT'])
sys.path.insert(0,str(root/'scripts'))
for site in (root/'.venv/lib').glob('python*/site-packages'): sys.path.insert(0,str(site))
import auth
from googleapiclient import discovery,discovery_cache
from google_auth_httplib2 import AuthorizedHttp
from httplib2 import Http
original=socket.socket.connect
def local(sock,address):
    if isinstance(address,tuple) and address[0] not in ('127.0.0.1','::1'): raise RuntimeError('test forbids external network')
    return original(sock,address)
socket.socket.connect=local
def build(api,version,credentials):
    doc=json.loads(discovery_cache.get_static_doc(api,version));doc['rootUrl']=os.environ['FIX2_API'];doc['baseUrl']=doc['rootUrl']+doc.get('servicePath','')
    return discovery.build_from_document(doc,http=AuthorizedHttp(credentials,http=Http(proxy_info=None)))
auth.build=build
`);
  const bin = path.join(scratch, 'bin');
  fs.mkdirSync(bin, { recursive: true });
  fs.symlinkSync(path.join(REPO, 'connectors/google/capabilities/tools/google/google.py'), path.join(bin, 'google'));
  const cred = path.join(scratch, 'credentials');
  fs.mkdirSync(cred, { recursive: true });
  fs.writeFileSync(path.join(cred, 'token.json'), JSON.stringify({ token: 'fixture', refresh_token: 'fixture', token_uri: 'http://127.0.0.1/unused', client_id: 'fixture', client_secret: 'fixture', expiry: '2099-01-01T00:00:00Z' }));
  fs.writeFileSync(path.join(scratch, 'config.json'), JSON.stringify({ accounts: { review: { email: 'agent@example.com', display_name: 'Fixture', credentials_dir: cred } }, scopes: ['https://www.googleapis.com/auth/gmail.modify'] }));
  const installation = installationAt(path.join(scratch, 'inst'), {
    slack: { team: 'T1', ownerUserId: 'U0OWNER' }, routes: {},
    listeners: { google: { account: 'review', mailbox: 'agent@example.com', owner: 'owner@example.com', agent: 'sara' } },
  });
  return { patch, bin, config: path.join(scratch, 'config.json'), installation };
}

test('google send and reply authorize the exact owner address and refuse outsiders before any draft', { timeout: 180_000 }, async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-gport-'));
  const { patch, bin, config, installation } = gmailScratch(work);
  const state = {};
  const { server, calls, port } = await gmailService(state);
  const message = require(path.join(REPO, 'connectors/messaging/capabilities/tools/message/message.js'));
  const run = async (argv) => {
    let out = '';
    let err = '';
    const code = await message.main(argv, { root: REPO, cwd: installation, env: {}, stdout: (t) => { out += t; }, stderr: (t) => { err += t; } });
    return { code, out, err };
  };
  try {
    await withEnv({
      PATH: `${bin}:${process.env.PATH}`, PYTHONDONTWRITEBYTECODE: '1', PYTHONPATH: patch,
      FIX2_GOOGLE_ROOT: path.join(REPO, 'connectors/google/repository'),
      FIX2_API: `http://127.0.0.1:${port}/`, GOOGLE_TOOLS_CONFIG: config,
    }, async () => {
      state.sender = 'owner@example.com';
      const owner = await run(['send', '--via', 'google', '--to', 'owner@example.com', 'owner control']);
      assert.equal(owner.code, 0, owner.err);
      assert.match(owner.out, /^Sent     to owner@example.com \(direct\) via google/);
      assert.equal(state.drafts.length, 1);
      const rawOne = Buffer.from(state.drafts[0].raw, 'base64').toString('utf8');
      assert.match(rawOne, /^To: owner@example\.com$/mi);

      const before = calls.length;
      const outsider = await run(['send', '--via', 'google', '--to', 'outsider@elsewhere.example', 'leak']);
      assert.equal(outsider.code, 1);
      assert.match(outsider.err, /^message: send refused: no permission to message outsider@elsewhere\.example\n/);
      assert.equal(calls.length, before, 'a refused send starts no connector subprocess at all');

      const reply = await run(['reply', '--thread', 'google:agent@example.com:t1:m1', 'owner reply control']);
      assert.equal(reply.code, 0, reply.err);
      assert.match(reply.out, /^Sent     in thread google:agent@example\.com:t1:m1 via google/);
      const rawTwo = Buffer.from(state.drafts[1].raw, 'base64').toString('utf8');
      assert.match(rawTwo, /^To: owner@example\.com$/mi);
      assert.match(rawTwo, /^In-Reply-To: <m1@example\.com>$/mi);

      state.sender = 'outsider@elsewhere.example';
      const draftsBefore = state.drafts.length;
      const outsiderThread = await run(['reply', '--thread', 'google:agent@example.com:t1:m1', 'leak reply']);
      assert.equal(outsiderThread.code, 1);
      assert.match(outsiderThread.err, /^message: reply refused: no permission to message outsider@elsewhere\.example\n/);
      assert.equal(state.drafts.length, draftsBefore, 'a thread whose sender is an outsider drafts nothing');
    });
  } finally { server.close(); fs.rmSync(work, { recursive: true, force: true }); }
});

test('google reply and history refuse a spoofed or mismatched thread reference', { timeout: 180_000 }, async () => {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'fix2-gref-'));
  const { patch, bin, config, installation } = gmailScratch(work);
  const state = { sender: 'owner@example.com' };
  const { server, calls, port } = await gmailService(state);
  const message = require(path.join(REPO, 'connectors/messaging/capabilities/tools/message/message.js'));
  const run = async (argv) => {
    let out = '';
    let err = '';
    const code = await message.main(argv, { root: REPO, cwd: installation, env: {}, stdout: (t) => { out += t; }, stderr: (t) => { err += t; } });
    return { code, out, err };
  };
  try {
    await withEnv({
      PATH: `${bin}:${process.env.PATH}`, PYTHONDONTWRITEBYTECODE: '1', PYTHONPATH: patch,
      FIX2_GOOGLE_ROOT: path.join(REPO, 'connectors/google/repository'),
      FIX2_API: `http://127.0.0.1:${port}/`, GOOGLE_TOOLS_CONFIG: config,
    }, async () => {
      const draftsBefore = (state.drafts || []).length;
      const spoofed = await run(['reply', '--thread', 'google:agent@example.com:unrelated:m1', 'spoof']);
      assert.equal(spoofed.code, 1);
      assert.equal(spoofed.out, '');
      assert.equal((state.drafts || []).length, draftsBefore, 'an invented conversation drafts nothing');

      const mismatch = await run(['reply', '--thread', 'google:agent@example.com:t2:m1', 'wrong binding']);
      assert.equal(mismatch.code, 1);
      assert.match(mismatch.err, /^message: reply refused: reference conversation does not match\n/);
      assert.equal((state.drafts || []).length, draftsBefore, 'a message id from another thread drafts nothing');

      const history = await run(['history', '--thread', 'google:agent@example.com:t1:m1', '--json']);
      assert.equal(history.code, 0, history.err);
      const body = JSON.parse(history.out);
      assert.equal(body.ref, 'google:agent@example.com:t1:m1');
      assert.deepEqual(body.events.map((event) => event.id), ['m1']);
      assert.equal(body.events[0].text, 'Full owner text body');
      assert.equal(body.events[0].from, 'owner@example.com', 'a trusted owner sender is the canonical address');

      const badHistory = await run(['history', '--thread', 'google:agent@example.com:t2:m1', '--json']);
      assert.equal(badHistory.code, 1);
      assert.match(badHistory.err, /^message: history refused: reference conversation does not match\n/);
    });
  } finally { server.close(); fs.rmSync(work, { recursive: true, force: true }); }
});
