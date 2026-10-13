#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Store, conversationKey } = require('./store.js');
const { runCheck } = require('./timer-check.js');
const { getState, saveState } = require('./dreamer.js');
const evidence = require('./albert-evidence.js');

const failures = [];
const queue = [];
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-albert-evidence-'));

function test(name, fn) {
  queue.push([name, fn]);
}

function linuxOnly(name, why, fn) {
  queue.push([name, process.platform === 'win32' ? null : fn, why]);
}

function workspace() {
  const dir = fs.mkdtempSync(path.join(root, 'w-'));
  fs.mkdirSync(path.join(dir, '.rbtv', 'config', 'ignite'), { recursive: true });
  fs.writeFileSync(path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'), `${JSON.stringify({
    slack: { team: 'T1', botUserId: 'UBOT', ownerUserId: 'UOWNER', appTokenEnv: 'A', botTokenEnv: 'B', ownerTokenEnv: 'C', stoolsWorkspace: 'ignite' },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' },
    routes: { CSRC: 'source' },
    dreamer: { enabled: false, model: { harness: 'codex', model: 'm', effort: 3 } },
  }, null, 2)}\n`);
  return dir;
}

function agent(dir, slug) {
  const home = path.join(dir, '.rbtv', 'agents', slug);
  fs.mkdirSync(path.join(home, 'runtime', 'ignite'), { recursive: true });
  fs.writeFileSync(path.join(home, 'prompt.md'), 'fixture\n');
  fs.writeFileSync(path.join(home, 'agent.json'), `${JSON.stringify({ name: slug, files: [], packs: [] })}\n`);
  return home;
}

function storeOf(home) {
  return new Store(path.join(home, 'runtime', 'ignite', 'state.sqlite'));
}

function owner(store, slug, text, rowid) {
  const key = conversationKey('T1', `C${slug}`, '1.1');
  store.upsertConversation({ key, agent: slug, workspace: 'T1', channel: `C${slug}`, rootTs: '1.1', activated: true });
  if (rowid == null) {
    store.recordMessage(key, { id: `m-${text}`, role: 'owner', text, metadata: { source: 'slack' } });
    return;
  }
  store.db.prepare(`INSERT INTO messages(rowid, id, conversation_key, role, text, files, metadata, created_at)
    VALUES (?, ?, ?, 'owner', ?, '[]', ?, 1)`).run(rowid, `m-${text}`, key, text, JSON.stringify({ source: 'slack' }));
}

function otherRole(store, slug, text) {
  const key = conversationKey('T1', `C${slug}`, '1.1');
  store.upsertConversation({ key, agent: slug, workspace: 'T1', channel: `C${slug}`, rootTs: '1.1', activated: true });
  store.recordMessage(key, { id: `a-${text}`, role: 'agent', text, metadata: { source: 'slack' } });
}

function fakeAlbert(home) {
  const file = path.join(home, 'fake-albert.js');
  fs.writeFileSync(file, `#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const home = process.env.RBTV_AGENT_HOME;
const op = process.argv[2];
const calls = path.join(home, 'albert-calls.json');
const seen = fs.existsSync(calls) ? JSON.parse(fs.readFileSync(calls, 'utf8')) : [];
seen.push(process.argv.slice(2));
fs.writeFileSync(calls, JSON.stringify(seen));
function arg(name) { const i = process.argv.indexOf(name); return i < 0 ? null : process.argv[i + 1]; }
if (op === 'check') {
  if (process.env.ALBERT_CHECK_FAIL) { process.stderr.write('check failed\\n'); process.exit(1); }
  const dir = path.join(home, 'runtime/albert/evidence');
  const batches = fs.existsSync(dir) ? fs.readdirSync(dir).filter((name) => name.endsWith('.json')) : [];
  fs.mkdirSync(path.join(home, 'runtime/albert'), { recursive: true });
  fs.writeFileSync(path.join(home, 'runtime/albert/liveness.json'), JSON.stringify({ lastSuccessAt: Date.now() }));
  process.stdout.write(JSON.stringify(batches.length ? { new: true, details: { reasons: ['evidence'] } } : { new: false }));
  process.exit(0);
}
if (op === 'watchdog') { process.stdout.write(process.env.ALBERT_WATCHDOG || '{"new":false}'); process.exit(0); }
if (op === 'liveness') {
  fs.mkdirSync(path.join(home, 'runtime/albert'), { recursive: true });
  fs.writeFileSync(path.join(home, 'runtime/albert/liveness.json'), JSON.stringify({ lastSuccessAt: Number(arg('--at')) }));
  process.stdout.write(JSON.stringify({ seeded: true, lastSuccessAt: Number(arg('--at')) }));
  process.exit(0);
}
if (op === 'report') {
  const occasion = arg('--occasion');
  const dir = path.join(home, 'runtime/albert/reports');
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, occasion + '.json');
  if (!fs.existsSync(file)) {
    const items = JSON.parse(fs.readFileSync(path.join(home, 'runtime/albert/report-items.json'), 'utf8'));
    const acked = fs.existsSync(path.join(home, 'runtime/albert/acked.json')) ? JSON.parse(fs.readFileSync(path.join(home, 'runtime/albert/acked.json'), 'utf8')) : [];
    const covered = items.filter((item) => !acked.includes(item));
    const text = ['Applied', ...covered, '', 'Pending global-rule approvals', 'approval-1', '', 'Unresolved conflicts', 'conflict-1', ''].join('\\n');
    fs.writeFileSync(file, JSON.stringify({ occasion, identity: occasion, items: covered, acked: false, text }));
  }
  const payload = JSON.parse(fs.readFileSync(file, 'utf8'));
  process.stdout.write(JSON.stringify({ occasion, identity: payload.identity, items: payload.items, acked: payload.acked, text: payload.text }));
  process.exit(0);
}
if (op === 'report-ack') {
  const occasion = arg('--occasion');
  const file = path.join(home, 'runtime/albert/reports', occasion + '.json');
  const payload = JSON.parse(fs.readFileSync(file, 'utf8'));
  payload.acked = true;
  fs.writeFileSync(file, JSON.stringify(payload));
  const ackedFile = path.join(home, 'runtime/albert/acked.json');
  const acked = fs.existsSync(ackedFile) ? JSON.parse(fs.readFileSync(ackedFile, 'utf8')) : [];
  fs.writeFileSync(ackedFile, JSON.stringify([...new Set([...acked, ...payload.items])]));
  process.stdout.write(JSON.stringify({ occasion, acked: true, items: payload.items, identity: payload.identity }));
  process.exit(0);
}
process.stderr.write('unknown\\n');
process.exit(2);
`);
  return file;
}

function bindFriday(home) {
  const store = storeOf(home);
  const key = conversationKey('T1', 'CALBERT', 'board');
  store.upsertConversation({ key, agent: 'albert', workspace: 'T1', channel: 'CALBERT', rootTs: 'board', activated: true });
  store.upsertSchedule({
    id: 'albert-friday', conversationKey: key, cadence: 'cron:45 8 * * 5', timezone: 'America/Sao_Paulo',
    nextAt: 1, enabled: true, note: 'Friday memory report', checkTool: evidence.CHECKS.friday,
  });
  store.upsertSchedule({
    id: 'albert-watchdog', conversationKey: key, cadence: 'every:1h', timezone: 'fixed',
    nextAt: 1, enabled: true, note: 'memory watchdog', checkTool: evidence.CHECKS.watchdog,
  });
  store.close();
}

function receipt(home, id, outcome, slug, ceiling, positions, commit = null) {
  const dir = path.join(home, 'runtime', 'albert', 'receipts');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `${id}.json`), `${JSON.stringify({
    id, createdAt: 1, outcome, runId: id, commit,
    sources: [{ source: slug, sourceKind: 'ignite', sourceAgent: slug, sourceCursor: '0', ceiling, positions }],
    items: [],
  })}\n`);
}

function configOf(dir) {
  return JSON.parse(fs.readFileSync(path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'), 'utf8'));
}

test('owner rows only', () => {
  const dir = workspace();
  const source = agent(dir, 'source');
  const albert = agent(dir, 'albert');
  const store = storeOf(source);
  owner(store, 'source', 'owner-line');
  otherRole(store, 'source', 'agent-line');
  store.close();
  process.env.ALBERT_TOOL = fakeAlbert(albert);
  const loaded = { ...require('./config.js').loadConfig(dir) };
  const refreshed = evidence.refreshEvidence(albert, loaded);
  const batch = JSON.parse(fs.readFileSync(refreshed.batches[0], 'utf8'));
  assert.deepEqual(batch.rows.map((row) => row.text), ['owner-line']);
  assert.equal(batch.rows.every((row) => row.author === 'owner'), true);
  delete process.env.ALBERT_TOOL;
});

test('cursor stays per source agent', () => {
  const dir = workspace();
  const raw = configOf(dir);
  raw.routes.C2 = 'other';
  fs.writeFileSync(path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'), `${JSON.stringify(raw)}\n`);
  const source = agent(dir, 'source');
  const other = agent(dir, 'other');
  const albert = agent(dir, 'albert');
  const left = storeOf(source);
  const right = storeOf(other);
  owner(left, 'source', 'left');
  owner(right, 'other', 'right');
  left.close();
  right.close();
  const loaded = require('./config.js').loadConfig(dir);
  evidence.refreshEvidence(albert, loaded);
  const ceiling = storeOf(source);
  const max = ceiling.db.prepare('SELECT MAX(rowid) AS n FROM messages').get().n;
  ceiling.close();
  receipt(albert, 'r1', 'published', 'source', max, [max], 'abc');
  evidence.reconcile(albert, loaded);
  const cursors = evidence.readCursors(albert);
  assert.equal(cursors.source.cursor, max);
  assert.equal(cursors.other, undefined);
});

test('late backfill below the ceiling waits', () => {
  const dir = workspace();
  const source = agent(dir, 'source');
  const albert = agent(dir, 'albert');
  const store = storeOf(source);
  owner(store, 'source', 'first', 1);
  owner(store, 'source', 'third', 3);
  store.close();
  const loaded = require('./config.js').loadConfig(dir);
  evidence.refreshEvidence(albert, loaded);
  const again = storeOf(source);
  owner(again, 'source', 'backfill', 2);
  again.close();
  receipt(albert, 'gap', 'published', 'source', 3, [1, 3], 'abc');
  evidence.reconcile(albert, loaded);
  assert.equal(evidence.readCursors(albert).source, undefined);
});

test('cursors advance only for exact positions in a durable committed-publication or validated-no-change receipt', () => {
  const dir = workspace();
  const source = agent(dir, 'source');
  const albert = agent(dir, 'albert');
  const store = storeOf(source);
  owner(store, 'source', 'one', 1);
  store.close();
  const loaded = require('./config.js').loadConfig(dir);
  receipt(albert, 'quiet', 'refused', 'source', 1, [1]);
  evidence.reconcile(albert, loaded);
  assert.equal(evidence.readCursors(albert).source, undefined);
  receipt(albert, 'pub', 'published', 'source', 1, [1], 'commit');
  evidence.reconcile(albert, loaded);
  assert.equal(evidence.readCursors(albert).source.cursor, 1);
});

test('validated no-change needs no memory commit and repeated reconciliation after crash is idempotent', () => {
  const dir = workspace();
  const source = agent(dir, 'source');
  const albert = agent(dir, 'albert');
  const store = storeOf(source);
  owner(store, 'source', 'one', 1);
  store.close();
  const loaded = require('./config.js').loadConfig(dir);
  receipt(albert, 'none', 'no-change', 'source', 1, [1], null);
  evidence.reconcile(albert, loaded);
  evidence.reconcile(albert, loaded);
  assert.equal(evidence.readCursors(albert).source.cursor, 1);
  assert.equal(fs.existsSync(path.join(dir, '.git')), false);
});

test('liveness and pending state migrate with the dry-run printing the plan and writing nothing', () => {
  const dir = workspace();
  const source = agent(dir, 'source');
  const albert = agent(dir, 'albert');
  process.env.ALBERT_TOOL = fakeAlbert(albert);
  process.env.RBTV_AGENT_HOME = albert;
  const store = storeOf(source);
  saveState(store, { cursor: 4, lastSuccessAt: 50, commit: null, reportedConflicts: ['Pending global rule: keep'] }, 50);
  store.close();
  const before = fs.readdirSync(path.join(albert, 'runtime'));
  const code = evidence.main(['migrate', '--dry-run']);
  assert.equal(code, 0);
  assert.equal(fs.existsSync(path.join(albert, 'runtime', 'albert', 'ignite-cursors.json')), false);
  assert.equal(fs.existsSync(path.join(albert, 'runtime', 'albert', 'liveness.json')), false);
  const applied = evidence.main(['migrate']);
  assert.equal(applied, 0);
  assert.equal(evidence.readCursors(albert).source.cursor, 4);
  assert.equal(JSON.parse(fs.readFileSync(path.join(albert, 'runtime', 'albert', 'liveness.json'), 'utf8')).lastSuccessAt, 50);
  assert.equal(before.includes('ignite'), true);
  delete process.env.ALBERT_TOOL;
  delete process.env.RBTV_AGENT_HOME;
});

function fridayFixture() {
  const dir = workspace();
  const albert = agent(dir, 'albert');
  process.env.ALBERT_TOOL = fakeAlbert(albert);
  process.env.RBTV_AGENT_HOME = albert;
  fs.mkdirSync(path.join(albert, 'runtime', 'albert'), { recursive: true });
  fs.writeFileSync(path.join(albert, 'runtime', 'albert', 'report-items.json'), JSON.stringify(['A']));
  bindFriday(albert);
  return { dir, albert };
}

test('Friday report keyed by its stable identity: a crash injected after the queue write and before report-ack, and one after report-ack, each retried, neither omit nor repeat items and queue exactly one outbox row', () => {
  const { albert } = fridayFixture();
  process.env.ALBERT_OCCASION = 'week-a';
  process.env.ALBERT_EVIDENCE_FAULT = 'after-queue';
  assert.throws(() => evidence.queueReport(albert, { occasion: 'week-a' }), /fault after-queue/);
  delete process.env.ALBERT_EVIDENCE_FAULT;
  evidence.queueReport(albert, { occasion: 'week-a' });
  process.env.ALBERT_EVIDENCE_FAULT = 'after-ack';
  assert.throws(() => evidence.queueReport(albert, { occasion: 'week-a' }), /fault after-ack/);
  delete process.env.ALBERT_EVIDENCE_FAULT;
  evidence.queueReport(albert, { occasion: 'week-a' });
  const store = storeOf(albert);
  const rows = store.db.prepare('SELECT client_msg_id, payload FROM outbox').all();
  assert.equal(rows.length, 1);
  assert.equal(rows[0].client_msg_id, 'week-a');
  const payload = JSON.parse(rows[0].payload);
  assert.match(payload.text, /Applied\nA\n/);
  store.close();
  delete process.env.ALBERT_OCCASION;
  delete process.env.RBTV_AGENT_HOME;
  delete process.env.ALBERT_TOOL;
});

test('report-ack is idempotent', () => {
  const { albert } = fridayFixture();
  evidence.queueReport(albert, { occasion: 'week-ack' });
  evidence.queueReport(albert, { occasion: 'week-ack' });
  const store = storeOf(albert);
  assert.equal(store.db.prepare('SELECT COUNT(*) AS n FROM outbox').get().n, 1);
  store.close();
  delete process.env.RBTV_AGENT_HOME;
  delete process.env.ALBERT_TOOL;
});

test('pending approvals listed apart', () => {
  const { albert } = fridayFixture();
  const body = evidence.queueReport(albert, { occasion: 'week-split' });
  assert.match(body.text, /Pending global-rule approvals\napproval-1/);
  assert.match(body.text, /Unresolved conflicts\nconflict-1/);
  assert.equal(body.text.includes('approval-1') && body.text.indexOf('approval-1') > body.text.indexOf('Applied'), true);
  assert.equal(body.text.indexOf('Applied') < body.text.indexOf('Pending global-rule approvals'), true);
  delete process.env.RBTV_AGENT_HOME;
  delete process.env.ALBERT_TOOL;
});

test('new owner source row plus no precreated batch wakes', () => {
  const dir = workspace();
  const source = agent(dir, 'source');
  const albert = agent(dir, 'albert');
  const store = storeOf(source);
  owner(store, 'source', 'fresh');
  store.close();
  process.env.ALBERT_TOOL = fakeAlbert(albert);
  process.env.RBTV_AGENT_HOME = albert;
  const cast = path.join(dir, 'cast');
  fs.writeFileSync(cast, '#!/bin/sh\necho cast-ran >> "$HOME/cast-ran"\n');
  fs.chmodSync(cast, 0o755);
  const previous = process.env.PATH;
  process.env.PATH = `${dir}${path.delimiter}${previous}`;
  const body = evidence.runCheck(albert, { installation: dir });
  assert.equal(body.new, true);
  assert.equal(fs.existsSync(path.join(dir, 'cast-ran')), false);
  const homeStore = storeOf(albert);
  const key = conversationKey('T1', 'CALBERT', 'board');
  homeStore.upsertConversation({ key, agent: 'albert', workspace: 'T1', channel: 'CALBERT', rootTs: 'board', activated: true });
  homeStore.upsertSchedule({
    id: 'albert-nightly', conversationKey: key, cadence: 'cron:0 3 * * *', timezone: 'America/Sao_Paulo',
    nextAt: 1, enabled: true, note: 'nightly memory check', checkTool: 'runtime/ignite/checks/albert-evidence.js',
  });
  evidence.installChecks(albert);
  homeStore.close();
  delete process.env.ALBERT_TOOL;
  delete process.env.RBTV_AGENT_HOME;
  process.env.PATH = previous;
});

test('no unread rows invokes no model', () => {
  const dir = workspace();
  const source = agent(dir, 'source');
  storeOf(source).close();
  const albert = agent(dir, 'albert');
  process.env.ALBERT_TOOL = fakeAlbert(albert);
  const cast = path.join(dir, 'cast-bin');
  fs.mkdirSync(cast, { recursive: true });
  fs.writeFileSync(path.join(cast, 'cast'), '#!/bin/sh\ntouch /tmp/ignite-cast-ran\n');
  fs.chmodSync(path.join(cast, 'cast'), 0o755);
  const previous = process.env.PATH;
  process.env.PATH = `${cast}${path.delimiter}${previous}`;
  const body = evidence.runCheck(albert, { installation: dir });
  assert.equal(body.new, false);
  assert.equal(fs.existsSync('/tmp/ignite-cast-ran'), false);
  process.env.PATH = previous;
  delete process.env.ALBERT_TOOL;
});

test('source-read error is visible and never false quiet success', () => {
  const dir = workspace();
  const albert = agent(dir, 'albert');
  process.env.ALBERT_TOOL = fakeAlbert(albert);
  assert.throws(() => evidence.runCheck(albert, { installation: dir }), /source store missing/);
  assert.equal(fs.existsSync(path.join(albert, 'runtime', 'albert', 'liveness.json')), false);
  delete process.env.ALBERT_TOOL;
});

test('validated-no-change tool result produces a durable receipt and advances the right external cursors exactly once without a memory commit', () => {
  const dir = workspace();
  const source = agent(dir, 'source');
  const albert = agent(dir, 'albert');
  const store = storeOf(source);
  owner(store, 'source', 'kept', 1);
  store.close();
  receipt(albert, 'tool-none', 'no-change', 'source', 1, [1], null);
  const loaded = require('./config.js').loadConfig(dir);
  evidence.reconcile(albert, loaded);
  evidence.reconcile(albert, loaded);
  assert.equal(evidence.readCursors(albert).source.cursor, 1);
  assert.equal(fs.existsSync(path.join(dir, '.git')), false);
});

test('quiet and refused results advance none', () => {
  const dir = workspace();
  const source = agent(dir, 'source');
  const albert = agent(dir, 'albert');
  const store = storeOf(source);
  owner(store, 'source', 'kept', 1);
  store.close();
  process.env.ALBERT_TOOL = fakeAlbert(albert);
  const loaded = require('./config.js').loadConfig(dir);
  evidence.refreshEvidence(albert, loaded);
  const quiet = evidence.runCheck(albert, { installation: dir, config: loaded });
  assert.equal(quiet.new, true);
  assert.equal(evidence.readCursors(albert).source, undefined);
  receipt(albert, 'bad', 'refused', 'source', 1, [1]);
  evidence.reconcile(albert, loaded);
  assert.equal(evidence.readCursors(albert).source, undefined);
  delete process.env.ALBERT_TOOL;
});

test('frozen report A, crash after queue before ack, intervening change B, retry and a later occasion cover B once', () => {
  const { albert } = fridayFixture();
  fs.writeFileSync(path.join(albert, 'runtime', 'albert', 'report-items.json'), JSON.stringify(['A']));
  process.env.ALBERT_EVIDENCE_FAULT = 'after-queue';
  assert.throws(() => evidence.queueReport(albert, { occasion: 'week-a' }), /after-queue/);
  delete process.env.ALBERT_EVIDENCE_FAULT;
  fs.writeFileSync(path.join(albert, 'runtime', 'albert', 'report-items.json'), JSON.stringify(['A', 'B']));
  evidence.queueReport(albert, { occasion: 'week-a' });
  evidence.queueReport(albert, { occasion: 'week-a' });
  const later = evidence.queueReport(albert, { occasion: 'week-b' });
  assert.deepEqual(later.items, ['B']);
  const store = storeOf(albert);
  const rows = store.db.prepare('SELECT client_msg_id FROM outbox ORDER BY client_msg_id').all();
  assert.deepEqual(rows.map((row) => row.client_msg_id), ['week-a', 'week-b']);
  store.close();
  delete process.env.RBTV_AGENT_HOME;
  delete process.env.ALBERT_TOOL;
});

linuxOnly('timer check parser wakes on the adapter only when the tool reports new work', 'the check tool is started as a program', async () => {
  const dir = workspace();
  const source = agent(dir, 'source');
  storeOf(source).close();
  const albert = agent(dir, 'albert');
  process.env.ALBERT_TOOL = fakeAlbert(albert);
  evidence.installChecks(albert);
  const store = storeOf(albert);
  const key = conversationKey('T1', 'CALBERT', 'board');
  store.upsertConversation({ key, agent: 'albert', workspace: 'T1', channel: 'CALBERT', rootTs: 'board', activated: true });
  store.upsertSchedule({
    id: 'night', conversationKey: key, cadence: 'every:1h', timezone: 'fixed', nextAt: 1, enabled: true,
    note: 'nightly memory check', checkTool: evidence.CHECKS.nightly,
  });
  store.close();
  process.env.RBTV_AGENT_HOME = albert;
  const quiet = await runCheck({ home: albert, tool: evidence.CHECKS.nightly, env: { ...process.env, ALBERT_TOOL: process.env.ALBERT_TOOL, RBTV_AGENT_HOME: albert } });
  assert.equal(quiet.answer, 'nothing', JSON.stringify(quiet));
  const sourceStore = storeOf(source);
  owner(sourceStore, 'source', 'wake-me');
  sourceStore.close();
  const woken = await runCheck({ home: albert, tool: evidence.CHECKS.nightly, env: { ...process.env, ALBERT_TOOL: process.env.ALBERT_TOOL, RBTV_AGENT_HOME: albert } });
  assert.equal(woken.answer, 'new', JSON.stringify(woken));
  delete process.env.ALBERT_TOOL;
  delete process.env.RBTV_AGENT_HOME;
});

test('fence then drain then migrate then recover selects one publisher', () => {
  const dir = workspace();
  const source = agent(dir, 'source');
  const albert = agent(dir, 'albert');
  process.env.ALBERT_TOOL = fakeAlbert(albert);
  process.env.RBTV_AGENT_HOME = albert;
  const store = storeOf(source);
  saveState(store, { cursor: 2, lastSuccessAt: 9, commit: null, reportedConflicts: [] }, 9);
  store.close();
  assert.throws(() => evidence.main(['drain']), /fence/);
  assert.equal(evidence.main(['fence']), 0);
  assert.equal(evidence.legacyFenced(dir), true);
  assert.equal(evidence.main(['drain']), 0);
  assert.equal(evidence.main(['migrate', '--dry-run']), 0);
  assert.equal(fs.existsSync(path.join(albert, 'runtime', 'albert', 'ignite-cursors.json')), false);
  assert.equal(evidence.main(['migrate']), 0);
  assert.equal(evidence.readCursors(albert).source.cursor, 2);
  bindFriday(albert);
  assert.equal(evidence.main(['recover']), 0);
  assert.equal(evidence.legacyFenced(dir), false);
  const after = storeOf(albert);
  assert.equal(after.getSchedule('albert-friday').enabled, false);
  assert.equal(after.getSchedule('albert-watchdog').enabled, false);
  after.close();
  assert.equal(getState(storeOf(source)).cursor, 2);
  delete process.env.ALBERT_TOOL;
  delete process.env.RBTV_AGENT_HOME;
});

(async () => {
  for (const [name, fn, why] of queue) {
    if (!fn) { console.log(`skip: ${name} is Linux-only: ${why}`); continue; }
    try {
      await fn();
      console.log(`PASS ${name}`);
    } catch (error) {
      failures.push(name);
      console.log(`FAIL ${name}: ${error.stack || error.message}`);
    }
  }
  if (failures.length) {
    console.log(`FAILED ${failures.length}`);
    process.exit(1);
  }
  console.log('ok');
})();
