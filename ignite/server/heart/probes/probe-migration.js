'use strict';

// probe-migration — proves the heart store can carry a schema change onto a store that ALREADY
// EXISTS (G-135), and proves it on a COPY OF THE REAL LIVE STORE, not on a fresh fixture.
//
// ⚠ WHY THE FIXTURE CHOICE IS THE WHOLE PROBE. G-135 is that `schema.sql` is six
// `CREATE TABLE IF NOT EXISTS` re-run on every open, so a schema change lands in the file, passes
// every test, and never reaches a store that already has its tables. EVERY existing fixture in
// this repo builds a FRESH store — and fresh is the ONE path on which the bug is invisible. A
// migration proven green on fresh fixtures would be p-green-harness at the persistence layer,
// authored by the change that exists to fix p-green-harness at the persistence layer.
//
// So: when this box has a real store, it is COPIED (`VACUUM INTO`, read-only source, the original
// is never opened for write) and every legacy assertion runs against that copy — real schema, real
// rows. When there is none, a legacy-shaped store is synthesised and the probe SAYS SO in its
// output rather than implying live coverage it did not have.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const HEART = path.join(__dirname, '..');
const SCHEMA_SQL = fs.readFileSync(path.join(HEART, 'schema.sql'), 'utf8');
const { migrate, isFreshStore, LATEST, MIGRATIONS } = require(path.join(HEART, 'migrations.js'));

const outPath = path.join(__dirname, 'probe-migration.out');
fs.writeFileSync(outPath, '');
const out = (...l) => fs.appendFileSync(outPath, l.join('\n') + '\n');

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-migration-'));
const started = Date.now();

// ---- fixture: a copy of the REAL live store when this box has one -------------------------
function liveStorePath() {
  const root = process.env.RBTV_IGNITE_DATA_ROOT
    || path.join(os.homedir(), '.local', 'state', 'rbtv-ignite');
  const p = path.join(root, 'heart.db');
  return fs.existsSync(p) ? p : null;
}

// ⚠⚠ TWO FIXTURES, BECAUSE THIS PROBE ASKS TWO QUESTIONS AND ONE STORE CAN NO LONGER ANSWER BOTH.
//
// It used to have one — a copy of the live store — which satisfied both preconditions only because
// the live store happened to be unstamped. On 2026-07-28 the owner ratified MIGRATION_SESSION_SPLIT
// and the daemon restarted; the live store is now user_version 2. Its own guard fired
// ("else this probe tests nothing"), correctly, and two checks went red.
//
// ⚠ THE CONDITION IS ONE-WAY: A STORE THAT HAS BEEN ADOPTED IS NEVER PRE-VERSIONING AGAIN. So this
// is not a fixture that went stale and can be refreshed — the world stopped supplying that input,
// permanently. The repair is to ESTABLISH the precondition rather than sample it:
//
//   · existingStoreFixture() — a store that ALREADY EXISTS, real schema and real rows, at whatever
//     version it is at. This is G-135's subject: a schema change must reach a store schema.sql
//     cannot touch. LIVE COPY when this box has one, and it must stay a live copy — fresh is the
//     one shape on which G-135's bug is invisible.
//   · preVersioningFixture() — a store that has NEVER been stamped, at the PRE-SPLIT shape.
//     SYNTHESIZED, necessarily and permanently, and the output says so rather than implying live
//     coverage it did not have.
function existingStoreFixture(label) {
  const dest = path.join(tmp, label + '.db');
  const live = liveStorePath();
  if (live) {
    // Read-only source; VACUUM INTO writes a consistent copy including WAL content. The live
    // store is never opened for write and never touched.
    const src = new DatabaseSync(live, { readOnly: true });
    src.exec(`VACUUM INTO '${dest.replace(/'/g, "''")}'`);
    src.close();
    const chk = new DatabaseSync(dest, { readOnly: true });
    const v = Number(chk.prepare('PRAGMA user_version').get().user_version || 0);
    const rows = Number(chk.prepare('SELECT count(*) AS n FROM jobs_log').get().n || 0);
    chk.close();
    return { path: dest, source: 'LIVE COPY', version: v, rows };
  }
  // No live store on this box: synthesise one that already exists. It is a WEAKER fixture for
  // G-135 (no real rows, no real history) and the output must not imply otherwise.
  const db = new DatabaseSync(dest);
  db.exec(SCHEMA_SQL);
  db.close();
  const chk = new DatabaseSync(dest, { readOnly: true });
  const v = Number(chk.prepare('PRAGMA user_version').get().user_version || 0);
  chk.close();
  return { path: dest, source: 'SYNTHETIC (no live store on this box)', version: v, rows: 0 };
}

// A store as it was BEFORE any migration ran: tables present, never stamped, and without the
// artifacts migration 2 adds — because a store that predates a migration is, by definition, one
// that does not already carry its result. Built by removing those two declarations from schema.sql,
// exactly as § 3 below edits schema.sql to reproduce the pre-fix path.
//
// ⚠ THE STRIP IS ASSERTED, NOT ASSUMED (`shape` below, checked in § 1). If schema.sql is reworded
// so a pattern stops matching, the fixture silently becomes post-split, migration 2 becomes a no-op
// on it, and the adoption checks would keep passing while covering nothing — this probe's own
// history, in which two checks passed against a migration that never ran.
function preVersioningFixture(label) {
  const dest = path.join(tmp, label + '.db');
  const preSplit = SCHEMA_SQL
    .replace(/CREATE TABLE IF NOT EXISTS sessions \([\s\S]*?\n\);\n/, '')
    .replace(/CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions\(status\);\n/, '')
    .replace(/^\s*session_pk\s+INTEGER REFERENCES sessions\(session_pk\),\n/m, '');
  const db = new DatabaseSync(dest);
  db.exec(preSplit);
  // Real turn rows, spanning the statuses migration 2's backfill maps differently (`done` closes a
  // session, `failed` crashes one, `killed` is the lossy case, `running` stays alive) — so
  // "adoption did not touch the data" is a claim about rows that exist.
  const ins = db.prepare(
    'INSERT INTO jobs_log (job_id, action_type, args, enqueued_by, fired_tick, fired_at, status) '
    + "VALUES ('probe-legacy-job', 'launch-agent', '{}', 'probe-owner', 0, '2026-07-01T00:00:00Z', ?)"
  );
  for (const s of ['done', 'failed', 'killed', 'running']) ins.run(s);
  db.exec('PRAGMA user_version = 0');
  const shape = {
    sessionsTable: db.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND name='sessions'").get().n > 0,
    sessionPkColumn: db.prepare('PRAGMA table_info(jobs_log)').all().some((r) => r.name === 'session_pk'),
  };
  const rows = Number(db.prepare('SELECT count(*) AS n FROM jobs_log').get().n || 0);
  db.close();
  const chk = new DatabaseSync(dest, { readOnly: true });
  const v = Number(chk.prepare('PRAGMA user_version').get().user_version || 0);
  chk.close();
  return { path: dest, source: 'SYNTHETIC pre-versioning, pre-split (the live store is adopted and can never supply this again)', version: v, rows, shape };
}

// Opens a store the way HeartStore's constructor does, with an optional extra migration appended.
function open(dbPath, extraMigration) {
  const db = new DatabaseSync(dbPath);
  const fresh = isFreshStore(db);
  db.exec('PRAGMA journal_mode = WAL;');
  db.exec(SCHEMA_SQL);
  let res;
  try {
    res = migrate(db, extraMigration
      ? { fresh, migrations: MIGRATIONS.concat([extraMigration]) }
      : { fresh });
  } catch (e) {
    db.close();
    throw e;
  }
  return { db, res, fresh };
}

// ⚠ try/finally, not a bare cleanup call after the last check: every fixture/check below can
// throw (VACUUM INTO on a locked/full disk, a real migration bug propagating past `open()`), and
// a throw here used to skip the rmSync entirely — the mkdtemp dir, holding a full VACUUM copy of
// the live store, was leaked on every non-happy-path exit. The finally arm runs on both paths.
let exitCode = 1;
try {

const fx = existingStoreFixture('existing');
const lg = preVersioningFixture('preversioning');
// ⚠ A PRISTINE, UNMIGRATED COPY, taken before anything opens `fx.path`. The first version of this
// probe copied its later fixtures FROM fx.path after the add-column test had already walked it to
// version 2 — so the doomed migration was numbered at-or-below the store's own version, was
// skipped, and three checks reported on a migration that never ran. Two of them PASSED while
// proving nothing. The fixture, not the code, was the thing that had stopped discriminating.
const pristine = path.join(tmp, 'pristine.db');
fs.copyFileSync(fx.path, pristine);
out(`COMMAND: node ${path.relative(process.cwd(), __filename)}`);
out(`FIXTURE (G-135, §2-§5): ${fx.source} — user_version ${fx.version}, jobs_log rows ${fx.rows}`);
out(`FIXTURE (adoption, §1): ${lg.source} — user_version ${lg.version}, jobs_log rows ${lg.rows}`);
out('');

// ---- 1 · the pre-versioning store is adopted, not rebuilt ---------------------------------
// Runs on the PRE-VERSIONING fixture, never on the live copy: adoption is a claim about a store
// that was never stamped, and the live store has been stamped since the owner's ratification.
check('the fixture really is a pre-versioning store (user_version 0) — else this probe tests nothing',
  lg.version === 0, `user_version=${lg.version}`);
check('and it really predates the split — no sessions table, no session_pk column, else migration 2 is a no-op on it and this section covers nothing',
  lg.shape.sessionsTable === false && lg.shape.sessionPkColumn === false,
  `sessionsTable=${lg.shape.sessionsTable} session_pk=${lg.shape.sessionPkColumn}`);
check('the fixture is NOT fresh — it already has tables, which is the case schema.sql cannot reach',
  (() => { const d = new DatabaseSync(lg.path); const f = isFreshStore(d); d.close(); return !f; })());

let a = open(lg.path);
check('opening an existing store walks it forward and STAMPS it', a.res.to === LATEST,
  `from=${a.res.from} to=${a.res.to} applied=[${a.res.applied}]`);
check('adoption ran the baseline migration rather than assuming the store was current',
  a.res.applied.includes(1), `applied=[${a.res.applied}]`);
const rowsAfter = Number(a.db.prepare('SELECT count(*) AS n FROM jobs_log').get().n || 0);
check('adoption did not touch the data', rowsAfter === lg.rows, `rows ${lg.rows} -> ${rowsAfter}`);
check('adoption REALLY RAN THE SPLIT on it: every pre-split turn now carries a session',
  Number(a.db.prepare('SELECT count(*) AS n FROM jobs_log WHERE session_pk IS NULL').get().n || 0) === 0,
  `unlinked turns=${a.db.prepare('SELECT count(*) AS n FROM jobs_log WHERE session_pk IS NULL').get().n}`);
a.db.close();

const b = open(lg.path);
check('re-opening is a no-op — migrations are not re-applied on every start',
  b.res.applied.length === 0 && b.res.from === LATEST, `applied=[${b.res.applied}]`);
b.db.close();

// The G-135 fixture's own precondition — it must be a store that ALREADY EXISTS, or § 2 below is
// asserting nothing. (Its VERSION is deliberately unconstrained: a real store advances, and
// pinning it here is what put this probe in the ruling that produced this repair.)
check('the G-135 fixture is a store that ALREADY EXISTS (not fresh) — fresh is the one shape on which the defect is invisible',
  (() => { const d = new DatabaseSync(fx.path); const f = isFreshStore(d); d.close(); return !f; })(),
  `source=${fx.source}`);

// ---- 2 · A REAL SCHEMA CHANGE REACHES AN EXISTING STORE — the defect itself ---------------
// This is the check G-135 exists for. It must run against the legacy copy, never a fresh store.
const addCol = {
  version: LATEST + 1,
  name: 'probe-add-column',
  up(db) { db.exec('ALTER TABLE jobs_log ADD COLUMN probe_migration_marker TEXT'); },
};

function hasColumn(dbPath, table, col) {
  const d = new DatabaseSync(dbPath, { readOnly: true });
  const has = d.prepare(`PRAGMA table_info(${table})`).all().some((r) => r.name === col);
  d.close();
  return has;
}

check('CONTROL: the column does not exist before the migration', !hasColumn(fx.path, 'jobs_log', 'probe_migration_marker'));
const c = open(fx.path, addCol);
check('A REAL SCHEMA CHANGE REACHES AN ALREADY-EXISTING STORE — the entire point of G-135',
  hasColumn(fx.path, 'jobs_log', 'probe_migration_marker') && c.res.applied.includes(addCol.version),
  `applied=[${c.res.applied}] to=${c.res.to}`);
const rowsAfterCol = Number(c.db.prepare('SELECT count(*) AS n FROM jobs_log').get().n || 0);
check('the schema change preserved every row', rowsAfterCol === fx.rows, `rows ${fx.rows} -> ${rowsAfterCol}`);
c.db.close();

// ---- 3 · THE PRE-FIX BEHAVIOUR, so the bar discriminates ----------------------------------
// Without a migration runner, a schema change is expressed by editing schema.sql — and against an
// existing store CREATE TABLE IF NOT EXISTS does nothing at all. Reproduced here rather than
// asserted: this is what "silent no-op" means, and it must fail on the old path.
const pre = path.join(tmp, 'prefix.db');
fs.copyFileSync(pristine, pre);
{
  const db = new DatabaseSync(pre);
  const altered = SCHEMA_SQL.replace(
    /CREATE TABLE IF NOT EXISTS jobs_log \(/,
    'CREATE TABLE IF NOT EXISTS jobs_log (\n  never_arrives TEXT,'
  );
  check('CONTROL: the edited schema.sql really does declare the new column',
    /never_arrives/.test(altered));
  db.exec(altered);           // exactly what the pre-fix constructor did
  db.close();
}
check('PRE-FIX REPRODUCTION: editing schema.sql lands NOTHING on an existing store — silent, exit 0, no error',
  !hasColumn(pre, 'jobs_log', 'never_arrives'));

// ---- 4 · failure mode: named, and never half-applied --------------------------------------
const boom = {
  version: LATEST + 1,
  name: 'probe-doomed',
  up(db) {
    db.exec('ALTER TABLE jobs_log ADD COLUMN half_applied_marker TEXT');
    throw new Error('deliberate failure after a real DDL statement');
  },
};
const failFixture = path.join(tmp, 'fail.db');
fs.copyFileSync(pristine, failFixture);
{
  const before = userVersionOf(failFixture);
  let err = null;
  try { open(failFixture, boom); } catch (e) { err = e; }
  check('a failing migration THROWS rather than opening a store it could not migrate', Boolean(err));
  check('the failure is a NAMED typed code, not a bare SQLite message',
    err && err.code === 'E_MIGRATION_FAILED', err ? `code=${err.code}` : 'no error');
  check('the failure names the migration a reader must go and fix',
    err && /probe-doomed/.test(err.message) && /rolled back/i.test(err.message));
  check('⚠ NOT HALF-APPLIED: the DDL that DID run was rolled back with it',
    !hasColumn(failFixture, 'jobs_log', 'half_applied_marker'));
  // ⚠ ATOMICITY IS PER MIGRATION, NOT PER BATCH — and the distinction is the design, not a
  // concession. Migration 1 succeeded and committed before 2 threw, so the store correctly sits
  // at 1: it really did complete 1, and re-running it on the next start would be the actual bug.
  // What must never happen is the store claiming a version whose migration did NOT complete.
  // My first version of this check asserted the version was unchanged from 0, which would have
  // demanded that a successful migration be rolled back because a LATER one failed.
  check('the store reports the last migration that actually COMPLETED, never the one that failed',
    userVersionOf(failFixture) === boom.version - 1,
    `${before} -> ${userVersionOf(failFixture)}, failed migration was ${boom.version}`);
  check('and it never claims the failed version', userVersionOf(failFixture) !== boom.version);
}

// ---- 5 · a store from a newer build is refused, not migrated backwards ---------------------
{
  const future = path.join(tmp, 'future.db');
  fs.copyFileSync(pristine, future);
  const d = new DatabaseSync(future);
  d.exec(`PRAGMA user_version = ${LATEST + 99}`);
  d.close();
  let err = null;
  try { open(future); } catch (e) { err = e; }
  check('a store written by a NEWER build is refused with a named code, never silently accepted',
    err && err.code === 'E_STORE_NEWER_THAN_CODE', err ? `code=${err.code}` : 'no error — it was accepted');
}

// ---- 6 · a fresh store is stamped, not migrated --------------------------------------------
{
  const freshPath = path.join(tmp, 'fresh.db');
  const f = open(freshPath);
  check('a FRESH store is stamped straight to latest and runs no migration',
    f.fresh === true && f.res.to === LATEST && f.res.applied.length === 0,
    `fresh=${f.fresh} to=${f.res.to} applied=[${f.res.applied}]`);
  f.db.close();
}

function userVersionOf(p) {
  const d = new DatabaseSync(p, { readOnly: true });
  const v = Number(d.prepare('PRAGMA user_version').get().user_version || 0);
  d.close();
  return v;
}

const passed = checks.filter((c) => c.pass).length;
out('');
out(`CHECKS: ${passed}/${checks.length} passed`);
// Both fixtures, because a reader diagnosing a red needs to know WHICH store the failing section
// ran against — naming only one is how the last red read as a defect in the other.
out(`FIXTURE WAS: G-135 §2-§5 = ${fx.source} (user_version ${fx.version}, ${fx.rows} rows) | adoption §1 = ${lg.source}`);
out(`EXIT: ${passed === checks.length ? 0 : 1}`);
out(`WALL_MS: ${Date.now() - started}`);
exitCode = passed === checks.length ? 0 : 1;

} catch (e) {
  // ⚠ OUT OF ROOM IS ENVIRONMENTAL, NOT AN ASSERTION FAILURE - and it used to be
  // indistinguishable from one. This probe holds FIVE concurrent copies of the store under
  // os.tmpdir() (fx + pristine + prefix + fail + future); against the VPS live store that is
  // ~514 MiB, on a quota-mounted tmpfs /tmp. When the room ran out the throw landed at a
  // copyfile site with EVERY emitted check still reading PASS, so the red named an errno
  // (-122) instead of a cause (task 7.705). Say which wall was hit, and what to do about it.
  const shortage = !e ? null
    : e.code === 'EDQUOT' ? 'quota'
    : e.code === 'ENOSPC' ? 'space'
    // The FIRST copy is a VACUUM INTO, so it meets the same wall as SQLITE_FULL rather than as
    // an fs errno. Same cause, same refusal - classifying only the fs half would leave the
    // earlier site still reporting the mystery this catch exists to end.
    : /database or disk is full/i.test(e.message || '') ? 'space'
    : null;
  if (!shortage) throw e;
  out('', `REFUSED (environmental, not a defect): out of ${shortage} writing a fixture under `
    + `${os.tmpdir()} (${e.code || e.message}). This probe needs room for 5 concurrent copies `
    + `of the store there. Free ${shortage}, or point TMPDIR at a roomier filesystem.`);
  out('EXIT: 1');   // exitCode is already 1
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}
process.exit(exitCode);
