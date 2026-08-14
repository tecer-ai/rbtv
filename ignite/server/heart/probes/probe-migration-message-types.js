'use strict';

// probe-migration-message-types — W4. Proves the seven-value message-type CHECK reaches a store
// that ALREADY EXISTS, and that the table REBUILD it needs does not break the one foreign key
// pointing INTO `messages`.
//
// ⚠ THE FIXTURE IS THE PROBE, for G-135's reason restated by schema.sql's own jobs_log note: a
// CHECK change is invisible on a fresh store (schema.sql already carries it) and is the whole
// question on a store that has rows. So every assertion below runs on a store built from the
// PRE-W4 schema, populated, and then migrated — never on a fresh fixture. The fresh arm is here
// only to prove the two shapes agree afterwards, which is the divergence schema.sql calls out.
//
// ⚠ THE FK IS THE HAZARD, not the CHECK. `jobs_log.completion_msg_id REFERENCES messages(msg_id)`
// means a naive rebuild (create-new, drop-old) runs an implicit delete against a referenced table
// with foreign_keys ON. Arm 4 measures that the reference survives and resolves.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const HEART = path.join(__dirname, '..');
const SCHEMA_SQL = fs.readFileSync(path.join(HEART, 'schema.sql'), 'utf8');
const { migrate, MIGRATION_MESSAGE_TYPES_SEVEN, MIGRATIONS, LATEST } =
  require(path.join(HEART, 'migrations.js'));

const outPath = path.join(__dirname, 'probe-migration-message-types.out');
fs.writeFileSync(outPath, '');
const out = (...l) => fs.appendFileSync(outPath, l.join('\n') + '\n');

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// The PRE-W4 shape, reconstructed from today's schema by putting the FIVE-value CHECK back. Derived
// rather than pasted so the rest of the table (columns, the two status CHECKs, the indexes) is
// literally what production had — only the one constraint under test differs.
const FIVE = "type IN ('completion','ask','answer','verdict','note')";
const SEVEN = "type IN ('completion','ask','answer','verdict','note','queue-request','escalation')";
const PRE_W4_SQL = SCHEMA_SQL.replace(SEVEN, FIVE);
if (PRE_W4_SQL === SCHEMA_SQL) {
  out('FAIL  fixture — schema.sql no longer carries the seven-value CHECK verbatim, so the pre-W4 '
    + 'fixture could not be derived and every arm below would test the same shape twice');
  out('EXIT: 1');
  process.exit(1);
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-msgtypes-'));
let exitCode = 0;

function openStore(file, sql) {
  const db = new DatabaseSync(file);
  db.exec('PRAGMA foreign_keys = ON;');   // production posture (heart-store.js)
  db.exec(sql);
  return db;
}

function refused(fn) {
  try { fn(); return null; } catch (e) { return e && e.message ? e.message : String(e); }
}

try {
  // ---- arm 1: the pre-W4 store refuses the two new types -------------------------------------
  const file = path.join(tmp, 'pre-w4.db');
  const db = openStore(file, PRE_W4_SQL);
  db.exec('PRAGMA user_version = 4;');    // an adopted store, one version behind W4

  const ins = db.prepare(
    'INSERT INTO messages (type, sender, thread, corpus, status, created_at) VALUES (?, ?, ?, ?, ?, ?)'
  );
  ins.run('note', 'seat-a', 'exec-1', 'a note', null, '2026-08-14T00:00:00Z');
  const completion = ins.run('completion', 'seat-a', 'exec-1', 'done here', 'done', '2026-08-14T00:01:00Z');
  const completionId = Number(completion.lastInsertRowid);
  ins.run('verdict', 'judge', 'exec-1', 'verdict: FAIL\nnot yet', null, '2026-08-14T00:02:00Z');

  // The row that makes the FK real. Column set kept minimal — everything else is nullable.
  db.prepare(
    'INSERT INTO jobs_log (job_id, action_type, args, enqueued_by, fired_tick, status, fired_at, completion_msg_id) '
    + 'VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
  ).run('job-w4', 'fire-tool', '{}', 'owner', 1, 'done', '2026-08-14T00:01:00Z', completionId);

  const beforeRows = db.prepare('SELECT count(*) AS n FROM messages').get().n;
  check('arm 1 · pre-W4 store REFUSES `escalation`',
    refused(() => ins.run('escalation', 'leader', 'exec-1', 'halted', null, 'x')) !== null,
    `${beforeRows} rows seeded under the five-value CHECK`);
  check('arm 1 · pre-W4 store REFUSES `queue-request`',
    refused(() => ins.run('queue-request', 'engine', 'exec-1', 'next wave', null, 'x')) !== null);

  // ---- arm 2: the migration runs on THAT store, in place --------------------------------------
  const res = migrate(db, { migrations: MIGRATIONS });
  check('arm 2 · migration applied to an EXISTING store',
    res.applied.includes(MIGRATION_MESSAGE_TYPES_SEVEN.version),
    `applied ${JSON.stringify(res.applied)}, now at user_version ${res.to} (LATEST ${LATEST})`);

  const sqlNow = db.prepare("SELECT sql FROM sqlite_master WHERE type='table' AND name='messages'").get().sql;
  check('arm 2 · the MIGRATED store carries the seven-value CHECK',
    sqlNow.includes("'escalation'") && sqlNow.includes("'queue-request'"));

  // ---- arm 3: the two new types are now writable, the old rows survived -----------------------
  const insNow = db.prepare(
    'INSERT INTO messages (type, sender, thread, corpus, status, created_at) VALUES (?, ?, ?, ?, ?, ?)'
  );
  check('arm 3 · `escalation` accepted after the migration',
    refused(() => insNow.run('escalation', 'leader', 'exec-1', 'halted', null, 'z')) === null);
  check('arm 3 · `queue-request` accepted after the migration',
    refused(() => insNow.run('queue-request', 'engine', 'exec-1', 'next wave', null, 'z')) === null);
  check('arm 3 · a bogus type is STILL refused (the CHECK was widened, not dropped)',
    refused(() => insNow.run('correction', 'someone', 'exec-1', 'x', null, 'z')) !== null);
  const kept = db.prepare('SELECT count(*) AS n FROM messages WHERE msg_id <= ?').get(completionId + 1).n;
  check('arm 3 · every pre-migration row survived the rebuild with its msg_id',
    kept === beforeRows, `${kept} of ${beforeRows} original rows still present`);

  // ---- arm 4: the incoming foreign key still resolves -----------------------------------------
  const fkViolations = db.prepare('PRAGMA foreign_key_check').all();
  check('arm 4 · PRAGMA foreign_key_check is clean after the rebuild',
    fkViolations.length === 0, `${fkViolations.length} violation(s)`);
  const joined = db.prepare(
    'SELECT m.corpus AS c FROM jobs_log j JOIN messages m ON m.msg_id = j.completion_msg_id WHERE j.job_id = ?'
  ).get('job-w4');
  check('arm 4 · jobs_log.completion_msg_id still joins to its message',
    joined && joined.c === 'done here', joined ? joined.c : 'no row');
  const jobsLogSql = db.prepare("SELECT sql FROM sqlite_master WHERE type='table' AND name='jobs_log'").get().sql;
  check('arm 4 · the sibling FK clause still names `messages`, not the rename shim',
    /REFERENCES\s+messages\s*\(/.test(jobsLogSql) && !jobsLogSql.includes('messages_pre_w4'));

  // ---- arm 5: idempotent — a second run changes nothing ----------------------------------------
  const before2 = db.prepare('SELECT count(*) AS n FROM messages').get().n;
  MIGRATION_MESSAGE_TYPES_SEVEN.up(db);
  const after2 = db.prepare('SELECT count(*) AS n FROM messages').get().n;
  check('arm 5 · re-running the migration is a NO-OP', before2 === after2,
    `${before2} -> ${after2} rows`);
  db.close();

  // ---- arm 6: fresh and migrated agree ---------------------------------------------------------
  const fresh = openStore(path.join(tmp, 'fresh.db'), SCHEMA_SQL);
  const freshSql = fresh.prepare("SELECT sql FROM sqlite_master WHERE type='table' AND name='messages'").get().sql;
  const norm = (s) => s.replace(/--[^\n]*\n/g, ' ').replace(/\s+/g, ' ').trim();
  check('arm 6 · fresh and migrated stores enforce the SAME messages CHECK',
    norm(freshSql).includes(SEVEN) && norm(sqlNow).includes(SEVEN));
  fresh.close();
} catch (e) {
  check('probe', false, `threw: ${e && e.stack ? e.stack : e}`);
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}

const failed = checks.filter((c) => !c.pass);
out('', `${checks.length - failed.length}/${checks.length} checks passed`);
out(`EXIT: ${failed.length ? 1 : 0}`);
exitCode = failed.length ? 1 : 0;
process.exit(exitCode);
