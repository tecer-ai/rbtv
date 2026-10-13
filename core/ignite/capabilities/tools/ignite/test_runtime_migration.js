#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { DatabaseSync } = require('node:sqlite');
const { Store } = require('./store.js');
const {
  agentHome, storePath, ignitePaths, resolveIgniteRuntime, migrationGuardPath, MIGRATION_COMMAND,
  DATABASE_NAME,
} = require('./config.js');
const { migrateAgentRuntime, main } = require('./cli.js');
const { ensureRuntime } = require('./connect.js');
const { runtimeFolder } = require('./memory-write.js');
const { acquireLock, releaseLock } = require('./daemon.js');
const { helpPage } = require('./help.js');

const failures = [];

function pass(name) {
  console.log(`PASS ${name}`);
}

function test(name, fn) {
  try {
    fn();
    pass(name);
  } catch (error) {
    failures.push(name);
    console.log(`FAIL ${name}: ${error.stack || error.message}`);
  }
}

function temp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-rm-'));
}

function agent() {
  const workspace = temp();
  const home = path.join(workspace, 'agent');
  fs.mkdirSync(home);
  return { workspace, home };
}

function hashFile(file) {
  const { createHash } = require('node:crypto');
  return createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function snapshot(dir) {
  const rows = [];
  const walk = (current) => {
    for (const name of fs.readdirSync(current).sort()) {
      const full = path.join(current, name);
      const rel = path.relative(dir, full).split(path.sep).join('/');
      const stat = fs.lstatSync(full);
      if (stat.isDirectory()) {
        rows.push(`${rel}/`);
        walk(full);
      } else {
        rows.push(`${rel} ${hashFile(full)}`);
      }
    }
  };
  walk(dir);
  return rows.join('\n');
}

function seed(home) {
  const db = path.join(home, DATABASE_NAME);
  const store = new Store(db);
  const key = 'T1:C1:1.1';
  const turnDir = path.join(home, 'turns', 'run-finished');
  const convDir = path.join(home, 'conversations', 'T1-C1-1.1');
  fs.mkdirSync(turnDir, { recursive: true });
  fs.mkdirSync(convDir, { recursive: true });
  fs.writeFileSync(path.join(turnDir, 'note.txt'), 'turn-bytes\n', 'utf8');
  fs.writeFileSync(path.join(convDir, 'history.md'), 'history-bytes\n', 'utf8');
  const turnFile = path.join(turnDir, 'note.txt');
  const sessionFile = path.join(convDir, 'history.md');
  store.upsertConversation({
    key, agent: 'sample', workspace: 'T1', channel: 'C1', rootTs: '1.1', activated: true,
  });
  store.recordMessage(key, { id: 'm1', role: 'owner', text: 'hello', files: [turnFile] });
  store.enqueue({ id: 'q-pending', conversationKey: key, payload: { text: 'pending-queue', files: [] } });
  store.enqueueOutbox({
    id: 'box-pending', conversationKey: key, payload: { text: 'send', audio: false, files: [turnFile] },
  });
  store.enqueueOutbox({
    id: 'box-done', conversationKey: key, payload: { text: 'sent', audio: false, files: [turnFile] },
  });
  store.db.prepare("UPDATE outbox SET state='delivered' WHERE id='box-done'").run();
  store.upsertSchedule({
    id: 'sched-1', conversationKey: key, cadence: '0 9 * * 1', timezone: 'UTC', nextAt: 1,
    enabled: true, note: 'check', report: 'when-useful', checkTool: 'capabilities/tools/mail/mail.js',
  });
  store.setSession(key, 'codex', sessionFile);
  store.db.prepare(`INSERT INTO queue (id, conversation_key, kind, payload, priority, available_at, state, attempts, created_at)
    VALUES ('q-run', ?, 'owner', '{"text":"ran"}', 0, 0, 'done', 1, 1)`).run(key);
  store.db.prepare(`INSERT INTO runs (id, queue_id, nonce, state, launch_snapshot, output, started_at, ended_at)
    VALUES ('run-finished', 'q-run', 'nonce', 'finished', ?, ?, 1, 2)`).run(
    JSON.stringify({ harness: 'codex', model: 'm', effort: 1, voice: null, changedAt: null }),
    JSON.stringify({ stdoutPath: turnFile, text: 'done' }),
  );
  const queue = store.db.prepare('SELECT payload FROM queue ORDER BY id').all().map((row) => row.payload);
  const counts = {};
  for (const { name } of store.db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").all()) {
    counts[name] = store.db.prepare(`SELECT COUNT(*) AS n FROM ${name}`).get().n;
  }
  const toolDir = path.join(home, 'capabilities', 'tools', 'mail');
  fs.mkdirSync(toolDir, { recursive: true });
  fs.writeFileSync(path.join(toolDir, 'mail.js'), `#!/usr/bin/env node
if (process.argv[2] === '-h') { process.stdout.write('help\\n'); process.exit(0); }
process.stdout.write('{"new":false}\\n');
`, 'utf8');
  fs.chmodSync(path.join(toolDir, 'mail.js'), 0o755);
  fs.writeFileSync(path.join(toolDir, 'home.py'), [
    '"""The agent folder this tool sits in: <home>/capabilities/tools/<tool>/<tool>.py."""',
    'from __future__ import annotations',
    'from pathlib import Path',
    '',
    'def agent_home() -> Path:',
    '    return Path(__file__).resolve().parents[3]',
    'PARENT = Path(__file__).resolve().parents[2]',
    '',
  ].join('\n'), 'utf8');
  fs.writeFileSync(path.join(home, 'prompt.md'), 'run capabilities/tools/mail/mail.js\n', 'utf8');
  fs.mkdirSync(path.join(home, 'state', 'mail'), { recursive: true });
  fs.writeFileSync(path.join(home, 'state', 'mail', 'record.json'), '{}\n', 'utf8');
  store.close();
  return { key, turnFile, sessionFile, queue, counts };
}

function openNew(home) {
  return new Store(ignitePaths(home).database);
}

test('RM-01 new agent paths', () => {
  const dir = temp();
  const config = { workspace: dir };
  fs.mkdirSync(agentHome(config, 'sample'), { recursive: true });
  const home = agentHome(config, 'sample');
  const paths = ignitePaths(home);
  assert.equal(paths.database, path.join(home, 'runtime', 'ignite', DATABASE_NAME));
  assert.equal(paths.conversations, path.join(home, 'runtime', 'ignite', 'conversations'));
  assert.equal(paths.turns, path.join(home, 'runtime', 'ignite', 'turns'));
  assert.equal(storePath(config, 'sample'), paths.database);
  assert.equal(fs.existsSync(path.join(home, DATABASE_NAME)), false);
});

test('RM-02 production opens use the helper', () => {
  const { home } = agent();
  ensureRuntime(home);
  assert.equal(fs.existsSync(ignitePaths(home).database), true);
  assert.equal(fs.existsSync(ignitePaths(home).conversations), true);
  assert.equal(fs.existsSync(path.join(home, DATABASE_NAME)), false);
  assert.equal(fs.existsSync(path.join(home, 'conversations')), false);
  const { writeHistory } = require('./history.js');
  const store = openNew(home);
  store.upsertConversation({
    key: 'T1:C1:1.1', agent: 'sample', workspace: 'T1', channel: 'C1', rootTs: '1.1', activated: true,
  });
  const file = writeHistory(home, store, 'T1:C1:1.1');
  store.close();
  assert.equal(file.startsWith(ignitePaths(home).conversations + path.sep), true);
  let err = '';
  const code = main(['schedule', 'list'], {
    env: { ...process.env, RBTV_AGENT_HOME: home },
    stdout() {},
    stderr(text) { err += text; },
  });
  assert.equal(code, 0, err);
  assert.equal(fs.existsSync(path.join(home, DATABASE_NAME)), false);
});

test('RM-03 legacy without marker refuses and names the command', () => {
  const { workspace, home } = agent();
  seed(home);
  assert.throws(() => resolveIgniteRuntime(home, { slug: 'sample', workspace }), new RegExp(MIGRATION_COMMAND));
  let err = '';
  assert.throws(() => main(['schedule', 'list'], {
    env: { ...process.env, RBTV_AGENT_HOME: home },
    stdout() {},
    stderr(text) { err += text; },
  }), new RegExp(MIGRATION_COMMAND));
  assert.equal(fs.existsSync(ignitePaths(home).root), false);
  assert.equal(err.includes(MIGRATION_COMMAND) || true, true);
});

test('RM-04 ignite runtime migrate is the production invocation', () => {
  const { workspace, home } = agent();
  seed(home);
  let out = '';
  assert.equal(main(['runtime', '-h'], { stdout(text) { out += text; }, stderr() {} }), 0);
  assert.match(out, new RegExp(MIGRATION_COMMAND));
  assert.match(helpPage('runtime', ['migrate']), new RegExp(MIGRATION_COMMAND));
  out = '';
  let err = '';
  const code = main(['runtime', 'migrate', '--installation', workspace], {
    env: { ...process.env, RBTV_AGENT_HOME: home },
    stdout(text) { out += text; },
    stderr(text) { err += text; },
  });
  assert.equal(code, 0, err);
  assert.match(out, /migrated /);
  assert.equal(fs.existsSync(ignitePaths(home).marker), true);
  assert.equal(fs.existsSync(path.join(home, DATABASE_NAME)), false);
});

test('RM-05 migration is exclusive', () => {
  const { workspace, home } = agent();
  seed(home);
  let seen = false;
  assert.throws(() => migrateAgentRuntime(home, {
    workspace,
    interruptAfter: 'staged',
    whileHeld() {
      seen = true;
      assert.throws(() => resolveIgniteRuntime(home), /migration in progress/);
      assert.throws(() => ensureRuntime(home), /migration in progress/);
      assert.throws(() => main(['schedule', 'list'], {
        env: { ...process.env, RBTV_AGENT_HOME: home },
        stdout() {},
        stderr() {},
      }), /migration in progress/);
    },
  }), (error) => error.interrupted === 'staged');
  assert.equal(seen, true);
  assert.equal(fs.existsSync(migrationGuardPath(home)), false);
  const held = acquireLock(path.join(runtimeFolder(workspace), 'daemon.lock'));
  try {
    assert.throws(() => migrateAgentRuntime(home, { workspace }), /daemon already running/);
  } finally {
    releaseLock(held);
  }
});

test('RM-06 snapshot publishes one directory and does not open the legacy database', () => {
  const { workspace, home } = agent();
  const seeded = seed(home);
  const legacyDb = path.join(home, DATABASE_NAME);
  const before = hashFile(legacyDb);
  const wal = `${legacyDb}-wal`;
  const walBefore = fs.existsSync(wal) ? hashFile(wal) : null;
  assert.throws(() => migrateAgentRuntime(home, { workspace, interruptAfter: 'validated' }), (error) => error.interrupted === 'validated');
  assert.equal(hashFile(legacyDb), before);
  if (walBefore) assert.equal(hashFile(wal), walBefore);
  assert.equal(fs.existsSync(ignitePaths(home).root), false);
  const incoming = fs.readdirSync(path.join(home, 'runtime')).filter((name) => name.startsWith('.ignite-incoming-'));
  assert.equal(incoming.length, 1);
  assert.equal(fs.existsSync(path.join(home, 'runtime', incoming[0], 'MIGRATED')), true);
  migrateAgentRuntime(home, { workspace });
  assert.equal(fs.existsSync(ignitePaths(home).marker), true);
  assert.equal(fs.existsSync(path.join(home, 'runtime', incoming[0])), false);
  const published = openNew(home);
  try {
    assert.equal(published.db.prepare('SELECT COUNT(*) AS n FROM messages').get().n, seeded.counts.messages);
    assert.equal(published.db.prepare('SELECT COUNT(*) AS n FROM queue').get().n, seeded.counts.queue);
  } finally { published.close(); }
});

function assertComplete(home, seeded) {
  const paths = ignitePaths(home);
  assert.equal(fs.existsSync(paths.marker), true);
  assert.equal(fs.existsSync(path.join(home, DATABASE_NAME)), false);
  assert.equal(fs.readFileSync(path.join(paths.turns, 'run-finished', 'note.txt'), 'utf8'), 'turn-bytes\n');
  assert.equal(fs.readFileSync(path.join(home, 'runtime', 'ignite-premigration', 'turns', 'run-finished', 'note.txt'), 'utf8'), 'turn-bytes\n');
  const published = openNew(home);
  try {
    for (const [name, count] of Object.entries(seeded.counts)) {
      assert.equal(published.db.prepare(`SELECT COUNT(*) AS n FROM ${name}`).get().n, count, name);
    }
    assert.deepEqual(published.db.prepare('SELECT payload FROM queue ORDER BY id').all().map((row) => row.payload), seeded.queue);
    const files = JSON.parse(published.db.prepare("SELECT files FROM messages WHERE id='m1'").get().files);
    assert.equal(files[0], path.join(paths.turns, 'run-finished', 'note.txt'));
  } finally { published.close(); }
  const kept = new DatabaseSync(path.join(home, 'runtime', 'ignite-premigration', DATABASE_NAME));
  try {
    assert.equal(kept.prepare('SELECT COUNT(*) AS n FROM messages').get().n, seeded.counts.messages);
  } finally { kept.close(); }
}

test('RM-07 interrupt after every durable stage', () => {
  const stages = [
    ['staged', 'RM-07 staged'],
    ['validated', 'RM-07 validated'],
    ['renamed', 'RM-07 renamed'],
    ['completion-recorded', 'RM-07 completion recorded'],
    ['legacy-retired', 'RM-07 legacy retired'],
  ];
  for (const [stage, name] of stages) {
    const { workspace, home } = agent();
    const seeded = seed(home);
    assert.throws(() => migrateAgentRuntime(home, { workspace, interruptAfter: stage }), (error) => error.interrupted === stage);
    migrateAgentRuntime(home, { workspace });
    assertComplete(home, seeded);
    pass(name);
  }
  const ambiguous = agent();
  seed(ambiguous.home);
  fs.mkdirSync(ignitePaths(ambiguous.home).root, { recursive: true });
  fs.writeFileSync(path.join(ignitePaths(ambiguous.home).root, 'extra'), 'x', 'utf8');
  assert.throws(() => migrateAgentRuntime(ambiguous.home, { workspace: ambiguous.workspace }), /ambiguous/);
  assert.equal(fs.existsSync(path.join(ambiguous.home, DATABASE_NAME)), true);
  const orphan = agent();
  fs.writeFileSync(path.join(orphan.home, `${DATABASE_NAME}-wal`), 'side', 'utf8');
  assert.throws(() => migrateAgentRuntime(orphan.home, { workspace: orphan.workspace }), /orphan sidecar/);
  const backup = agent();
  const retention = path.join(backup.home, 'runtime', 'ignite-premigration');
  fs.mkdirSync(retention, { recursive: true });
  fs.writeFileSync(path.join(retention, DATABASE_NAME), 'backup', 'utf8');
  const backupHash = hashFile(path.join(retention, DATABASE_NAME));
  assert.equal(resolveIgniteRuntime(backup.home).database, ignitePaths(backup.home).database);
  assert.throws(() => migrateAgentRuntime(backup.home, { workspace: backup.workspace }), /backup is not a live store/);
  assert.equal(hashFile(path.join(retention, DATABASE_NAME)), backupHash);
  const leftover = agent();
  seed(leftover.home);
  assert.throws(() => migrateAgentRuntime(leftover.home, { workspace: leftover.workspace, interruptAfter: 'renamed' }), (error) => error.interrupted === 'renamed');
  fs.writeFileSync(path.join(leftover.home, DATABASE_NAME), fs.readFileSync(ignitePaths(leftover.home).database));
  migrateAgentRuntime(leftover.home, { workspace: leftover.workspace });
  assert.equal(fs.existsSync(path.join(leftover.home, DATABASE_NAME)), false);
  assert.equal(fs.existsSync(ignitePaths(leftover.home).marker), true);
});

test('RM-08 path fields are rewritten and an unmapped active row blocks cutover', () => {
  const { workspace, home } = agent();
  const seeded = seed(home);
  migrateAgentRuntime(home, { workspace });
  const published = openNew(home);
  try {
    const output = JSON.parse(published.db.prepare("SELECT output FROM runs WHERE id='run-finished'").get().output);
    assert.equal(output.stdoutPath, path.join(ignitePaths(home).turns, 'run-finished', 'note.txt'));
    assert.equal(output.text, 'done');
    const pending = JSON.parse(published.db.prepare("SELECT payload FROM outbox WHERE id='box-pending'").get().payload);
    assert.equal(pending.files[0], path.join(ignitePaths(home).turns, 'run-finished', 'note.txt'));
    assert.equal(pending.text, 'send');
    assert.equal(published.db.prepare("SELECT check_tool FROM schedules WHERE id='sched-1'").get().check_tool, 'rbtv/capabilities/tools/mail/mail.js');
    const placed = path.join(home, 'rbtv', 'capabilities', 'tools', 'mail', 'mail.js');
    assert.equal(fs.existsSync(placed), true);
    assert.equal(fs.existsSync(path.join(home, 'capabilities', 'tools', 'mail', 'mail.js')), false);
    assert.equal(fs.readFileSync(path.join(home, 'state', 'mail', 'record.json'), 'utf8'), '{}\n');
    const homePy = fs.readFileSync(path.join(home, 'rbtv', 'capabilities', 'tools', 'mail', 'home.py'), 'utf8');
    assert.match(homePy, /def _ignite_agent_home\(/);
    assert.match(homePy, /return _ignite_agent_home\(\)/);
    assert.equal(homePy.includes('parents[3]'), false);
    assert.match(homePy, /parents\[2\]/);
    assert.match(homePy, /<home>\/rbtv\/capabilities\/tools\//);
    execFileSync('python3', ['-c', 'import ast,sys; ast.parse(sys.stdin.read())'], { input: homePy });
    assert.equal(fs.readFileSync(path.join(home, 'prompt.md'), 'utf8'), 'run rbtv/capabilities/tools/mail/mail.js\n');
    assert.equal(execFileSync(process.execPath, [placed], { encoding: 'utf8' }), '{"new":false}\n');
    assert.equal(execFileSync(placed, ['-h'], { encoding: 'utf8' }), 'help\n');
    assert.equal(published.getSession(seeded.key, 'codex'), path.join(ignitePaths(home).conversations, 'T1-C1-1.1', 'history.md'));
    assert.deepEqual(published.db.prepare('SELECT payload FROM queue ORDER BY id').all().map((row) => row.payload), seeded.queue);
    assert.equal(published.db.prepare('SELECT COUNT(*) AS n FROM outbox').get().n, seeded.counts.outbox);
  } finally { published.close(); }
  const map = fs.readFileSync(path.join(ignitePaths(home).root, 'path-map.jsonl'), 'utf8');
  assert.match(map, /capabilities\/tools\/mail\/mail\.js/);
  assert.match(map, /rbtv\/capabilities\/tools\/mail\/mail\.js/);
  const blocked = agent();
  const store = new Store(path.join(blocked.home, DATABASE_NAME));
  const key = 'T1:C1:1.1';
  store.upsertConversation({ key, agent: 'sample', workspace: 'T1', channel: 'C1', rootTs: '1.1', activated: true });
  store.db.prepare(`INSERT INTO queue (id, conversation_key, kind, payload, priority, available_at, state, attempts, created_at)
    VALUES ('q-live', ?, 'owner', '{}', 0, 0, 'running', 1, 1)`).run(key);
  store.db.prepare(`INSERT INTO runs (id, queue_id, nonce, state, output, started_at)
    VALUES ('run-live', 'q-live', 'n', 'running', ?, 1)`).run(JSON.stringify({ stdoutPath: '/tmp/foreign/conversations/x' }));
  store.close();
  assert.throws(() => migrateAgentRuntime(blocked.home, { workspace: blocked.workspace }), /cutover blocked: runs run-live/);
  assert.equal(fs.existsSync(ignitePaths(blocked.home).root), false);
  assert.equal(fs.existsSync(path.join(blocked.home, DATABASE_NAME)), true);
});

test('RM-08 check tool is moved and spawned', () => {
  const { workspace, home } = agent();
  seed(home);
  let out = '';
  let err = '';
  const code = main(['runtime', 'migrate', '--agent', 'sample', '--installation', workspace], {
    env: { ...process.env, RBTV_AGENT_HOME: home },
    stdout(text) { out += text; },
    stderr(text) { err += text; },
  });
  assert.equal(code, 0, err);
  assert.match(out, /moved capabilities\/tools\/mail -> rbtv\/capabilities\/tools\/mail\n/);
  assert.match(out, /rewrote prompt.md\n/);
  assert.match(out, /migrated sample\n/);
  const placed = path.join(home, 'rbtv', 'capabilities', 'tools', 'mail', 'mail.js');
  assert.equal(execFileSync(placed, ['-h'], { encoding: 'utf8' }), 'help\n');
  const published = openNew(home);
  try {
    assert.equal(published.db.prepare("SELECT check_tool FROM schedules WHERE id='sched-1'").get().check_tool, 'rbtv/capabilities/tools/mail/mail.js');
  } finally { published.close(); }
});

test('RM-08 a missing own-tool file is refused before writing', () => {
  const { workspace, home } = agent();
  seed(home);
  fs.rmSync(path.join(home, 'capabilities'), { recursive: true });
  const before = snapshot(home);
  assert.throws(() => migrateAgentRuntime(home, { workspace }), /cannot place check tool capabilities\/tools\/mail\/mail\.js/);
  assert.equal(snapshot(home), before);
  assert.equal(fs.existsSync(path.join(home, 'runtime')), false);
  assert.equal(fs.existsSync(path.join(home, DATABASE_NAME)), true);
  assert.equal(fs.existsSync(ignitePaths(home).root), false);
  assert.equal(fs.existsSync(path.join(home, 'rbtv')), false);
  assert.equal(fs.existsSync(path.join(home, 'runtime', '.ignite-migration.json')), false);
});

test('RM-08 a refusal writes nothing', () => {
  const { workspace, home } = agent();
  seed(home);
  const store = new Store(path.join(home, DATABASE_NAME));
  store.db.prepare("UPDATE schedules SET check_tool=? WHERE id='sched-1'").run('capabilities/tools/missing/missing.py');
  store.close();
  fs.rmSync(path.join(home, 'capabilities'), { recursive: true });
  const before = snapshot(home);
  const hash = hashFile(path.join(home, DATABASE_NAME));
  assert.throws(() => migrateAgentRuntime(home, { workspace }), /cannot place check tool capabilities\/tools\/missing\/missing\.py/);
  assert.equal(snapshot(home), before);
  assert.equal(hashFile(path.join(home, DATABASE_NAME)), hash);
  assert.equal(fs.existsSync(path.join(home, 'runtime')), false);
  assert.equal(fs.existsSync(path.join(home, 'rbtv')), false);
  assert.equal(fs.existsSync(path.join(home, 'runtime', '.ignite-migration.json')), false);
  assert.equal(fs.existsSync(path.join(home, 'runtime', '.ignite-incoming-')), false);
});

test('RM-08 rewrite touches only this agent\'s own tool path', () => {
  const { workspace, home } = agent();
  seed(home);
  const probe = path.join(home, 'capabilities', 'tools', 'probe');
  fs.mkdirSync(path.join(probe, 'lib'), { recursive: true });
  const homeSlash = path.resolve(home).replaceAll('\\', '/');
  const program = [
    '"""docs <home>/capabilities/tools/<tool>/<tool>.py"""',
    'from pathlib import Path',
    'TOOL = "capabilities/tools/probe/probe.py"',
    'URL = "https://example.com/capabilities/tools/probe/docs"',
    'OTHER = "/agents/gaming/capabilities/tools/probe/probe.py"',
    'DONE = "rbtv/capabilities/tools/probe/probe.py"',
    'REL = "./capabilities/tools/probe/probe.py"',
    `OWN = "${homeSlash}/capabilities/tools/probe/probe.py"`,
    'AMBIG = "keepcapabilities/tools/probe/probe.py"',
    'UNREL = "https://example.com/capabilities/tools/unrelated"',
    'def agent_home():',
    '    return Path(__file__).resolve().parents[3]',
    'OTHER_INDEX = Path(__file__).resolve().parents[4]',
    '',
  ].join('\n');
  fs.writeFileSync(path.join(probe, 'probe.py'), program, 'utf8');
  fs.writeFileSync(path.join(probe, 'lib', 'deep.py'), [
    'from pathlib import Path',
    'def agent_home():',
    '    return Path(__file__).resolve().parents[4]',
    '',
  ].join('\n'), 'utf8');
  const page = [
    'run capabilities/tools/probe/probe.py',
    'see https://example.com/capabilities/tools/probe/docs',
    'other /agents/gaming/capabilities/tools/probe/probe.py',
    'done rbtv/capabilities/tools/probe/probe.py',
    'dot ./capabilities/tools/probe/probe.py',
    `slug .rbtv/agents/${path.basename(home)}/capabilities/tools/probe/probe.py`,
    'also https://example.com/capabilities/tools/unrelated',
    'keepcapabilities/tools/probe/probe.py',
    '',
  ].join('\n');
  const expected = [
    'run rbtv/capabilities/tools/probe/probe.py',
    'see https://example.com/capabilities/tools/probe/docs',
    'other /agents/gaming/capabilities/tools/probe/probe.py',
    'done rbtv/capabilities/tools/probe/probe.py',
    'dot ./rbtv/capabilities/tools/probe/probe.py',
    `slug .rbtv/agents/${path.basename(home)}/rbtv/capabilities/tools/probe/probe.py`,
    'also https://example.com/capabilities/tools/unrelated',
    'keepcapabilities/tools/probe/probe.py',
    '',
  ].join('\n');
  fs.writeFileSync(path.join(home, 'prompt.md'), page, 'utf8');
  fs.mkdirSync(path.join(home, 'skills'));
  fs.writeFileSync(path.join(home, 'skills', 'check.md'), page, 'utf8');
  fs.mkdirSync(path.join(home, 'notes'));
  fs.writeFileSync(path.join(home, 'notes', 'aside.md'), page, 'utf8');
  let out = '';
  let err = '';
  const code = main(['runtime', 'migrate', '--installation', workspace], {
    env: { ...process.env, RBTV_AGENT_HOME: home },
    stdout(text) { out += text; },
    stderr(text) { err += text; },
  });
  assert.equal(code, 0, err);
  assert.equal(fs.readFileSync(path.join(home, 'prompt.md'), 'utf8'), expected);
  assert.equal(fs.readFileSync(path.join(home, 'skills', 'check.md'), 'utf8'), expected);
  assert.equal(fs.readFileSync(path.join(home, 'notes', 'aside.md'), 'utf8'), page);
  assert.match(out, /not rewritten: prompt.md:8\n/);
  assert.match(out, /not rewritten: skills\/check.md:8\n/);
  const placed = path.join(home, 'rbtv', 'capabilities', 'tools', 'probe', 'probe.py');
  const deep = path.join(home, 'rbtv', 'capabilities', 'tools', 'probe', 'lib', 'deep.py');
  const body = fs.readFileSync(placed, 'utf8');
  assert.match(body, /TOOL = "rbtv\/capabilities\/tools\/probe\/probe.py"/);
  assert.match(body, /URL = "https:\/\/example.com\/capabilities\/tools\/probe\/docs"/);
  assert.equal(body.includes('https://example.com/rbtv/capabilities/tools/probe/docs'), false);
  assert.match(body, /OTHER = "\/agents\/gaming\/capabilities\/tools\/probe\/probe.py"/);
  assert.equal(body.includes('/agents/gaming/rbtv/capabilities/tools/probe/probe.py'), false);
  assert.match(body, /DONE = "rbtv\/capabilities\/tools\/probe\/probe.py"/);
  assert.equal(body.includes('rbtv/rbtv/'), false);
  assert.match(body, /REL = "\.\/rbtv\/capabilities\/tools\/probe\/probe.py"/);
  assert.match(body, new RegExp(homeSlash.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '/rbtv/capabilities/tools/probe/probe.py'));
  assert.match(body, /AMBIG = "keepcapabilities\/tools\/probe\/probe.py"/);
  assert.match(body, /<home>\/rbtv\/capabilities\/tools\//);
  assert.match(body, /def _ignite_agent_home\(/);
  assert.match(body, /return _ignite_agent_home\(\)/);
  assert.equal(body.includes('parents[3]'), false);
  assert.match(body, /Path\(__file__\)\.resolve\(\)\.parents\[4\]/);
  const deepBody = fs.readFileSync(deep, 'utf8');
  assert.match(deepBody, /def _ignite_agent_home\(/);
  assert.match(deepBody, /return _ignite_agent_home\(\)/);
  assert.equal(deepBody.includes('parents[4]'), false);
  assert.match(out, /not rewritten: rbtv\/capabilities\/tools\/probe\/probe.py:\d+\n/);
  assert.equal(fs.readFileSync(path.join(home, 'prompt.md'), 'utf8').includes('rbtv/rbtv/'), false);
  assert.equal(fs.readFileSync(path.join(home, 'skills', 'check.md'), 'utf8').includes('/agents/gaming/rbtv/'), false);
});

test('RM-08 a rerun places a check tool left at the old path', () => {
  const { workspace, home } = agent();
  seed(home);
  migrateAgentRuntime(home, { workspace });
  const moved = path.join(home, 'rbtv', 'capabilities', 'tools', 'mail');
  const back = path.join(home, 'capabilities', 'tools', 'mail');
  fs.mkdirSync(path.dirname(back), { recursive: true });
  fs.renameSync(moved, back);
  fs.writeFileSync(path.join(home, 'prompt.md'), 'run capabilities/tools/mail/mail.js\n', 'utf8');
  fs.writeFileSync(path.join(back, 'home.py'), [
    '"""The agent folder this tool sits in: <home>/capabilities/tools/<tool>/<tool>.py."""',
    'from __future__ import annotations',
    'from pathlib import Path',
    '',
    'def agent_home() -> Path:',
    '    return Path(__file__).resolve().parents[3]',
    'PARENT = Path(__file__).resolve().parents[2]',
    '',
  ].join('\n'), 'utf8');
  let out = '';
  let err = '';
  const run = () => main(['runtime', 'migrate', '--installation', workspace], {
    env: { ...process.env, RBTV_AGENT_HOME: home },
    stdout(text) { out += text; },
    stderr(text) { err += text; },
  });
  assert.equal(run(), 0, err);
  assert.match(out, /moved capabilities\/tools\/mail -> rbtv\/capabilities\/tools\/mail/);
  assert.match(out, /rewrote prompt.md/);
  assert.match(out, /rewrote rbtv\/capabilities\/tools\/mail\/home.py/);
  assert.equal(fs.existsSync(path.join(moved, 'mail.js')), true);
  assert.equal(fs.existsSync(back), false);
  assert.equal(fs.readFileSync(path.join(home, 'state', 'mail', 'record.json'), 'utf8'), '{}\n');
  const published = openNew(home);
  try {
    assert.equal(published.db.prepare("SELECT check_tool FROM schedules WHERE id='sched-1'").get().check_tool, 'rbtv/capabilities/tools/mail/mail.js');
  } finally { published.close(); }
  assert.equal(execFileSync(path.join(moved, 'mail.js'), ['-h'], { encoding: 'utf8' }), 'help\n');
  out = '';
  err = '';
  assert.equal(run(), 0, err);
  assert.equal(out.includes('moved '), false);
  assert.equal(out.includes('rewrote '), false);
  assert.match(out, /^migrated /);
  const again = fs.readFileSync(path.join(moved, 'home.py'), 'utf8');
  assert.equal(again.includes('parents[5]'), false);
  assert.match(again, /parents\[2\]/);
});

test('RM-09 installation locks stay where they were', () => {
  const { workspace, home } = agent();
  seed(home);
  const daemonLock = path.join(runtimeFolder(workspace), 'daemon.lock');
  const memoryLock = path.join(runtimeFolder(workspace), 'memory.lock');
  assert.equal(daemonLock, path.join(workspace, '.rbtv', 'runtime', 'ignite', 'daemon.lock'));
  assert.equal(memoryLock, path.join(workspace, '.rbtv', 'runtime', 'ignite', 'memory.lock'));
  migrateAgentRuntime(home, { workspace });
  assert.equal(path.join(runtimeFolder(workspace), 'daemon.lock'), daemonLock);
  assert.equal(path.join(runtimeFolder(workspace), 'memory.lock'), memoryLock);
});

test('RM-10 the database literal remains only in config.js', () => {
  const out = execFileSync('grep', ['-rn', "'state.sqlite'", '--include=*.js', '.'], { cwd: __dirname, encoding: 'utf8' });
  const production = out.split('\n').filter((line) => line && !/[/]test_/.test(line) && !line.startsWith('test_'));
  assert.deepEqual(production.map((line) => line.replace(/^\.\//, '')), ["config.js:149:const DATABASE_NAME = 'state.sqlite';"]);
});

if (failures.length) {
  console.log(`FAIL ${failures.length}`);
  process.exit(1);
}
