#!/usr/bin/env node
'use strict';

// Phase 3a fix2, Gmail lane. Drives the PRODUCTION adapter (lib/messaging.js) through the REAL
// google wrapper (google.py -> gtools.py -> gmail_read.py / gmail_draft.py / gmail_send.py, the
// actual parsers) against a loopback-only Gmail HTTP fixture. The stand-in replaces the service
// endpoint only; wrapper, parsers and adapter are production. Reproduces rereview findings F3
// (message/thread binding), F5 (lossless paging, isolated held retries, awaited child-tree stop)
// and N3 (reply draft MIME From), with positive and negative controls for owner verification.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');

const GOOGLE_TOOL = __dirname;
const REPOSITORY = path.resolve(__dirname, '..', '..', '..', 'repository');
const PYTHON = path.join(REPOSITORY, '.venv', 'bin', 'python');
const adapter = require(path.join(GOOGLE_TOOL, 'lib', 'messaging.js'));

const BASE_MS = 1792195200000;
const MAILBOX = 'agent@example.com';
const OWNER = 'owner@example.com';
const BODY = 'Full owner text ' + 'x'.repeat(1100);
const SECTION = { account: 'review', mailbox: MAILBOX, owner: OWNER };

const SHARED = fs.mkdtempSync(path.join(os.tmpdir(), 'gmail-fix2-'));
const PATCH = path.join(SHARED, 'patch');
fs.mkdirSync(PATCH, { recursive: true });
fs.writeFileSync(path.join(PATCH, 'sitecustomize.py'), [
  'import json, os, socket, sys',
  'from pathlib import Path',
  "root = Path(os.environ['FIX2_GMAIL_ROOT'])",
  'leaf = os.path.basename(sys.argv[0] or "") not in ("google.py", "gtools.py")',
  'if leaf:',
  "    sys.path.insert(0, str(root / 'scripts'))",
  "    for site in (root / '.venv' / 'lib').glob('python*/site-packages'): sys.path.insert(0, str(site))",
  '    import auth',
  '    from googleapiclient import discovery, discovery_cache',
  '    from google_auth_httplib2 import AuthorizedHttp',
  '    from httplib2 import Http',
  '    _original = socket.socket.connect',
  '    def _local(sock, address):',
  "        if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1'):",
  "            raise RuntimeError('gmail-fix2 forbids external network')",
  '        return _original(sock, address)',
  '    socket.socket.connect = _local',
  '    def _build(api, version, credentials):',
  '        doc = json.loads(discovery_cache.get_static_doc(api, version))',
  "        doc['rootUrl'] = os.environ['FIX2_GMAIL_API']",
  "        doc['baseUrl'] = doc['rootUrl'] + doc.get('servicePath', '')",
  '        return discovery.build_from_document(doc, http=AuthorizedHttp(credentials, http=Http(proxy_info=None)))',
  '    auth.build = _build',
  '',
].join('\n'));

function harness(scenario) {
  const dir = fs.mkdtempSync(path.join(SHARED, 'case-'));
  const home = path.join(dir, 'home');
  const credentials = path.join(dir, 'credentials');
  fs.mkdirSync(home, { recursive: true });
  fs.mkdirSync(credentials, { recursive: true });
  fs.writeFileSync(path.join(credentials, 'token.json'), JSON.stringify({
    token: 'fixture', refresh_token: 'fixture', token_uri: 'http://127.0.0.1/unused',
    client_id: 'fixture', client_secret: 'fixture', expiry: '2099-01-01T00:00:00Z',
  }));
  const config = path.join(dir, 'config.json');
  fs.writeFileSync(config, JSON.stringify({
    accounts: { review: { email: MAILBOX, display_name: 'Fixture Agent', credentials_dir: credentials } },
    scopes: ['https://www.googleapis.com/auth/gmail.modify'],
  }));
  const state = { scenario, calls: [], commands: [], drafts: [], sends: [], hang: null };
  const server = http.createServer((req, res) => { serve(req, res, state); });
  const ready = new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const env = () => {
    const clean = {};
    for (const [key, value] of Object.entries(process.env)) {
      if (/^(SLACK_|IGNITE_|RBTV_|GOOGLE_|WACLI_|TYPESAFE_|FIX2_)/.test(key)) continue;
      clean[key] = value;
    }
    return {
      ...clean,
      HOME: home, USERPROFILE: home, PATH: '/usr/bin:/bin',
      PYTHONDONTWRITEBYTECODE: '1', PYTHONPATH: PATCH,
      GOOGLE_TOOLS_CONFIG: config, FIX2_GMAIL_ROOT: REPOSITORY,
      FIX2_GMAIL_API: `http://127.0.0.1:${server.address().port}/`,
    };
  };
  const spawnReal = (command, args, opts = {}) => {
    assert.equal(command, 'google', 'the adapter must launch the google command');
    const record = { args, out: '', err: '' };
    state.commands.push(record);
    const child = spawn(PYTHON, [path.join(GOOGLE_TOOL, 'google.py'), ...args], { ...opts, env: env() });
    child.stdout?.on('data', (chunk) => { record.out += chunk; });
    child.stderr?.on('data', (chunk) => { record.err += chunk; });
    child.on('close', (code) => { record.exit = code; });
    return child;
  };
  return {
    state, dir, ready, spawnReal,
    cursorFile: (name) => path.join(dir, `${name}-cursor.json`),
    async close() {
      server.close();
      if (typeof server.closeAllConnections === 'function') server.closeAllConnections();
    },
  };
}

function rowsOf(state) {
  const scenario = state.scenario;
  const n = scenario.n ?? 1;
  const base = scenario.baseMs ?? BASE_MS;
  return Array.from({ length: n }, (_, k) => {
    const i = k + 1;
    return {
      id: `m${i}`,
      threadId: scenario.threads?.[i - 1] ?? `t${i}`,
      ms: scenario.equal ? base : base + i * 1000,
    };
  });
}

function fullMessage(state, row) {
  const scenario = state.scenario;
  const sender = scenario.sender ?? OWNER;
  const proof = 'mx.google.com; dmarc=pass header.from=example.com; dkim=pass header.d=example.com';
  let headers = [
    ['Delivered-To', MAILBOX],
    ['Received', 'from sender.example by mx.google.com with ESMTP id fixture'],
    ['Authentication-Results', proof],
    ['From', sender],
    ['To', MAILBOX],
    ['Subject', 'Fixture'],
    ['Message-ID', `<${row.id}@example.com>`],
  ];
  if (scenario.missing) headers = headers.filter(([name]) => name !== 'Authentication-Results');
  if (scenario.forged) headers.splice(2, 0, ['Authentication-Results', 'evil.example; dmarc=pass header.from=example.com']);
  return {
    id: row.id,
    threadId: row.threadId,
    internalDate: String(row.ms),
    snippet: 'Full owner text xxx',
    labelIds: scenario.self ? ['SENT'] : ['INBOX'],
    payload: {
      mimeType: 'text/plain',
      headers: headers.map(([name, value]) => ({ name, value })),
      body: { data: Buffer.from(BODY).toString('base64url') },
    },
  };
}

function sendJson(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, { 'content-type': 'application/json', 'content-length': data.length });
  res.end(data);
}

function serve(req, res, state) {
  const chunks = [];
  req.on('data', (chunk) => chunks.push(chunk));
  req.on('end', () => {
    const url = new URL(req.url, 'http://127.0.0.1');
    const body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
    state.calls.push({ method: req.method, path: url.pathname, query: url.searchParams, body });
    const rows = rowsOf(state);
    if (url.pathname.endsWith('/profile')) {
      sendJson(res, 200, { emailAddress: state.scenario.mailbox ?? MAILBOX });
    } else if (url.pathname.endsWith('/messages') && req.method === 'GET') {
      const q = url.searchParams.get('q') || '';
      let items = rows;
      const after = /after:(\d+)/.exec(q);
      const before = /before:(\d+)/.exec(q);
      const gone = state.scenario.gone || [];
      if (gone.length) items = items.filter((row) => !gone.includes(row.id));
      if (after) items = items.filter((row) => row.ms >= Number(after[1]) * 1000);
      if (before) items = items.filter((row) => row.ms < Number(before[1]) * 1000);
      items = [...items].sort((a, b) => (b.ms - a.ms) || (b.id < a.id ? -1 : 1));
      const size = Number(url.searchParams.get('maxResults') || '10');
      const offset = Number(url.searchParams.get('pageToken') || '0');
      const out = { messages: items.slice(offset, offset + size).map((row) => ({ id: row.id, threadId: row.threadId })) };
      if (offset + size < items.length) out.nextPageToken = String(offset + size);
      sendJson(res, 200, out);
    } else if (/\/messages\/[^/]+$/.test(url.pathname)) {
      const id = url.pathname.split('/').pop();
      if (id.startsWith('sent-')) {
        sendJson(res, 200, { id, threadId: `thread-${id}`, payload: { headers: [] } });
        return;
      }
      const row = rows.find((item) => item.id === id);
      if (!row || (state.scenario.gone || []).includes(id)) {
        sendJson(res, 404, { error: { code: 404, message: 'message not found' } });
        return;
      }
      if (state.scenario.hang === id && url.searchParams.get('format') === 'full') {
        state.hang = { closed: false };
        res.on('close', () => { if (state.hang) state.hang.closed = true; });
        return;
      }
      const message = fullMessage(state, row);
      if (url.searchParams.get('format') !== 'full') delete message.payload.body;
      sendJson(res, 200, message);
    } else if (/\/threads\/[^/]+$/.test(url.pathname)) {
      const tid = url.pathname.split('/').pop();
      const items = rows.filter((row) => row.threadId === tid);
      if (!items.length) {
        sendJson(res, 404, { error: { code: 404, message: 'thread not found' } });
        return;
      }
      sendJson(res, 200, { id: tid, messages: items.map((row) => fullMessage(state, row)) });
    } else if (url.pathname.endsWith('/drafts') && req.method === 'POST') {
      const raw = Buffer.from(body.message.raw, 'base64url').toString('utf8');
      const headerBlock = raw.split(/\r?\n\r?\n/)[0];
      const headers = {};
      for (const line of headerBlock.split(/\r?\n/)) {
        const at = line.indexOf(':');
        if (at > 0) headers[line.slice(0, at).toLowerCase()] = line.slice(at + 1).trim();
      }
      const record = {
        to: headers.to || '', from: headers.from || '', subject: headers.subject || '',
        inReplyTo: headers['in-reply-to'] || '', raw,
        threadId: body.message.threadId || null,
      };
      state.drafts.push(record);
      const id = `draft-${state.drafts.length}`;
      sendJson(res, 200, { id, message: { id: `draft-message-${state.drafts.length}`, threadId: record.threadId || `draft-thread-${state.drafts.length}` } });
    } else if (url.pathname.endsWith('/drafts/send') && req.method === 'POST') {
      const draft = state.drafts[Number(String(body.id).split('-')[1]) - 1];
      state.sends.push(body.id);
      sendJson(res, 200, { id: `sent-${state.sends.length}`, threadId: draft?.threadId || `sent-thread-${state.sends.length}`, labelIds: ['SENT'] });
    } else {
      sendJson(res, 404, { error: { code: 404, message: `unexpected endpoint ${url.pathname}` } });
    }
  });
 }

test('owner mail arrives whole with sender, conversation and trusted identity (positive control)', async () => {
  const h = harness({ n: 2 });
  await h.ready;
  try {
    const seen = [];
    const result = await adapter.poll({
      section: SECTION, cursorFile: h.cursorFile('owner'), spawn: h.spawnReal,
      onEvent: async (event) => { seen.push(event); return { queued: true }; },
    });
    assert.deepEqual(seen.map((event) => event.id), ['m1', 'm2']);
    assert.equal(seen[0].from, OWNER);
    assert.equal(seen[0].conversation, 't1');
    assert.equal(seen[0].text, BODY);
    assert.equal(seen[0].identity.verified, true);
    assert.equal(seen[0].identity.owner, true);
    assert.equal(seen[0].at, BASE_MS + 1000);
    assert.deepEqual(result.held, []);
    const cursor = JSON.parse(fs.readFileSync(h.cursorFile('owner'), 'utf8'));
    assert.equal(cursor.account, 'review');
    assert.equal(cursor.mailbox, MAILBOX);
    assert.ok(cursor.afterMs >= BASE_MS + 2000, 'high-water advanced past both messages');
  } finally { await h.close(); }
});

test('authenticated non-owner mail stays fail-closed (negative control)', async () => {
  const h = harness({ n: 1, sender: 'outsider@elsewhere.example' });
  await h.ready;
  try {
    const seen = [];
    await adapter.poll({
      section: SECTION, cursorFile: h.cursorFile('outsider'), spawn: h.spawnReal,
      onEvent: async (event) => { seen.push(event); return { queued: true }; },
    });
    assert.equal(seen.length, 1);
    assert.equal(seen[0].from, 'outsider@elsewhere.example');
    assert.equal(seen[0].identity.verified, false);
    assert.equal(seen[0].identity.owner, false);
  } finally { await h.close(); }
});

test('history resolves a message reference to its thread and refuses a mismatched conversation (F3)', async () => {
  const h = harness({ n: 2, threads: ['t1', 't1'] });
  await h.ready;
  try {
    const direct = await adapter.operations['message.history']({ conversation: 't1', thread: 't1' }, { section: SECTION, spawn: h.spawnReal });
    assert.deepEqual(direct.events.map((event) => event.id), ['m1', 'm2']);
    const viaMessage = await adapter.operations['message.history']({ conversation: 't1', thread: 'm1' }, { section: SECTION, spawn: h.spawnReal });
    assert.deepEqual(viaMessage.events.map((event) => event.id), ['m1', 'm2'], 'a message reference resolves to its own thread');
    await assert.rejects(
      adapter.operations['message.history']({ conversation: 'unrelated', thread: 'm1' }, { section: SECTION, spawn: h.spawnReal }),
      (error) => error.code === 'thread' && /m1/.test(error.message) && /unrelated/.test(error.message),
      'a reference whose conversation is not the message\'s thread is refused',
    );
  } finally { await h.close(); }
});

test('reply validates the conversation binding before any draft and reports the canonical recipient (F3/N1)', async () => {
  const h = harness({ n: 2, threads: ['t1', 't1'] });
  await h.ready;
  try {
    await assert.rejects(
      adapter.operations['message.send']({ group: 'unrelated', thread: 'm1', text: 'wrong binding' }, { section: SECTION, spawn: h.spawnReal }),
      (error) => error.code === 'thread',
      'a mismatched conversation/message binding is refused before any draft',
    );
    assert.equal(h.state.drafts.length, 0, 'no draft may exist for the refused reply');
    assert.equal(h.state.sends.length, 0, 'nothing may be sent for the refused reply');
    const sent = await adapter.operations['message.send']({ group: 't1', thread: 'm1', text: 'answer' }, { section: SECTION, spawn: h.spawnReal });
    assert.equal(sent.conversation, 't1');
    assert.equal(sent.to, OWNER, 'the adapter reports the resolved canonical recipient');
    assert.equal(sent.recipientVerified, true, 'the recipient is the service-verified owner address');
    const draft = h.state.drafts[0];
    assert.equal(draft.threadId, 't1');
    const draftArgv = h.state.commands.find((row) => row.args.includes('draft'));
    const threadAt = draftArgv.args.indexOf('--thread-id');
    const replyAt = draftArgv.args.indexOf('--reply-to-message-id');
    assert.ok(threadAt > 0 && draftArgv.args[threadAt + 1] === 't1', 'the draft targets the verified thread');
    assert.ok(replyAt > 0 && ['m1', 'm2'].includes(draftArgv.args[replyAt + 1]), 'the draft replies to a message of the verified thread');
  } finally { await h.close(); }
});

test('an unverified thread party is reported as the recipient without being called verified (N1 adapter half)', async () => {
  const h = harness({ n: 1, sender: 'outsider@elsewhere.example' });
  await h.ready;
  try {
    const resolved = await adapter.resolveReply({ conversation: 't1', id: 'm1' }, { section: SECTION, spawn: h.spawnReal });
    assert.equal(resolved.to, 'outsider@elsewhere.example');
    assert.equal(resolved.verified, false);
    assert.equal(resolved.threadId, 't1');
    assert.equal(resolved.messageId, 'm1');
  } finally { await h.close(); }
});

test('paging is lossless across 101 identical internalDate messages and sustained arrivals (F5)', { timeout: 420_000 }, async () => {
  const h = harness({ n: 101, equal: true, threads: Array.from({ length: 101 }, () => 'shared') });
  await h.ready;
  const ids = [];
  const input = () => ({
    section: SECTION, cursorFile: h.cursorFile('equal'), spawn: h.spawnReal,
    onEvent: async (event) => { ids.push(event.id); return { queued: true }; },
  });
  try {
    await adapter.poll(input());
    await adapter.poll(input());
    assert.equal(new Set(ids).size, ids.length, 'no message is delivered twice');
    assert.equal(ids.length, 101, 'every equal-second message is delivered');
    assert.ok(ids.includes('m1'), 'the oldest same-second message is not lost');
    assert.ok(h.state.commands.some((row) => row.args.includes('--page-token')), 'pagination follows the service page token');
    h.state.scenario.n = 111;
    await adapter.poll(input());
    h.state.scenario.n = 121;
    await adapter.poll(input());
    assert.equal(new Set(ids).size, 121, 'sustained arrivals after restart-from-cursor are all delivered');
    assert.ok(ids.includes('m1'), 'the recovered message survives continued traffic');
    const every = Array.from({ length: 121 }, (_, i) => `m${i + 1}`);
    assert.deepEqual([...new Set(ids)].sort((a, b) => Number(a.slice(1)) - Number(b.slice(1))), every);
  } finally { await h.close(); }
});

test('a held unreadable item is retried in isolation, accounted, and never blocks newer mail (F5)', async () => {
  const h = harness({ n: 2 });
  await h.ready;
  const delivered = [];
  try {
    await adapter.poll({
      section: SECTION, cursorFile: h.cursorFile('held'), spawn: h.spawnReal,
      onEvent: async (event) => {
        if (event.id === 'm1') return { ignored: 'judgment-error' };
        delivered.push(event.id);
        return { queued: true };
      },
    });
    assert.deepEqual(delivered, ['m2']);
    h.state.scenario.gone = ['m1'];
    h.state.scenario.n = 3;
    const second = await adapter.poll({
      section: SECTION, cursorFile: h.cursorFile('held'), spawn: h.spawnReal,
      onEvent: async (event) => { delivered.push(event.id); return { queued: true }; },
    });
    assert.ok(delivered.includes('m3'), 'newer mail is consumed while the held item is unreadable');
    assert.ok(second.failures?.some((row) => row.id === 'm1' && row.attempts === 1 && /404|not found|google answered/i.test(row.lastError)),
      'the exact held failure is reported distinctly from successful consumes');
    assert.ok(!second.failures?.some((row) => row.id === 'm3'), 'a successful consume is not a failure');
    await adapter.poll({
      section: SECTION, cursorFile: h.cursorFile('held'), spawn: h.spawnReal,
      onEvent: async (event) => { delivered.push(event.id); return { queued: true }; },
    });
    const third = await adapter.poll({
      section: SECTION, cursorFile: h.cursorFile('held'), spawn: h.spawnReal,
      onEvent: async (event) => { delivered.push(event.id); return { queued: true }; },
    });
    assert.ok(third.dropped?.some((row) => row.id === 'm1'), 'a permanently unreadable held item is dropped with accounting');
    const cursor = JSON.parse(fs.readFileSync(h.cursorFile('held'), 'utf8'));
    assert.ok(!cursor.held.some((row) => row.id === 'm1'), 'the dropped item stops retrying');
    assert.equal(delivered.filter((id) => id === 'm3').length, 1, 'newer mail consumed exactly once');
  } finally { await h.close(); }
});

test('an aborted poll drains the actual child tree before its promise settles (F5)', { timeout: 60_000 }, async () => {
  const h = harness({ n: 1, hang: 'm1' });
  await h.ready;
  try {
    const controller = new AbortController();
    const pending = adapter.poll({
      section: SECTION, cursorFile: h.cursorFile('hang'), spawn: h.spawnReal, signal: controller.signal,
      onEvent: async () => ({ queued: true }),
    });
    const deadline = Date.now() + 20_000;
    while (!h.state.hang && Date.now() < deadline) await new Promise((resolve) => setTimeout(resolve, 50));
    assert.ok(h.state.hang, 'the real read reached the service');
    controller.abort();
    await assert.rejects(pending, /aborted/);
    const grace = Date.now() + 5_000;
    while (!h.state.hang.closed && Date.now() < grace) await new Promise((resolve) => setTimeout(resolve, 50));
    assert.ok(h.state.hang.closed, 'the hung service connection closed: the wrapper\'s child tree is drained');
  } finally { await h.close(); }
});

test('a reply draft carries the sending mailbox as MIME From, quoting the original author separately (N3)', async () => {
  const h = harness({ n: 1 });
  await h.ready;
  try {
    const sent = await adapter.operations['message.send']({ group: 't1', thread: 'm1', text: 'answer' }, { section: SECTION, spawn: h.spawnReal });
    assert.ok(sent.id, 'the send is confirmed');
    const draft = h.state.drafts[0];
    assert.ok(draft.from.includes(MAILBOX), `From must be the authenticated sending mailbox, got ${draft.from}`);
    assert.ok(!draft.from.includes(OWNER), 'From must not be the original author');
    assert.equal(draft.to, OWNER);
    assert.equal(draft.inReplyTo, '<m1@example.com>');
    const bodyText = Buffer.from(draft.raw.split(/\r?\n/).filter((line) => /^[A-Za-z0-9+/=]{40,}$/.test(line)).join(''), 'base64').toString('utf8');
    assert.ok(bodyText.includes(`${OWNER} wrote:`), 'the original author is quoted in the attribution, not the From');
  } finally { await h.close(); }
});

test('account confirmation refuses a wrong mailbox and an unknown alias (controls)', async () => {
  const h = harness({ n: 1 });
  await h.ready;
  try {
    await assert.rejects(
      adapter.account({ section: { ...SECTION, mailbox: 'wrong@example.com' }, spawn: h.spawnReal }),
      /did not confirm its account identity/,
    );
    await assert.rejects(
      adapter.account({ section: { ...SECTION, account: 'absent' }, spawn: h.spawnReal }),
      (error) => /absent|account/i.test(error.message),
    );
  } finally { await h.close(); }
});
