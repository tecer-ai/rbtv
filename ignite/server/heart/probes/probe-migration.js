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

function legacyFixture(label) {
  const dest = path.join(tmp, label + '.db');
  const live = liveStorePath();
  if (live) {
    // Read-only source; VACUUM INTO writes a consistent copy including WAL content. The live
    // store is never opened for write and never touched.
    const src = new DatabaseSync(live, { readOnly: true });
    src.exec(`VACUUM INTO '${dest.replace(/'/g, "''")}'`);
    src.close();
    // A real store predates versioning, so it carries user_version 0 already. Assert rather than
    // assume — if a future live store is already stamped, this fixture stops being "legacy" and
    // the probe must say so instead of quietly testing nothing.
    const chk = new DatabaseSync(dest, { readOnly: true });
    const v = Number(chk.prepare('PRAGMA user_version').get().user_version || 0);
    const rows = Number(chk.prepare('SELECT count(*) AS n FROM jobs_log').get().n || 0);
    chk.close();
    return { path: dest, source: 'LIVE COPY', version: v, rows };
  }
  // No live store on this machine: synthesise one shaped like a pre-versioning store.
  const db = new DatabaseSync(dest);
  db.exec(SCHEMA_SQL);
  db.exec('PRAGMA user_version = 0');
  db.close();
  return { path: dest, source: 'SYNTHETIC (no live store on this box)', version: 0, rows: 0 };
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

const fx = legacyFixture('legacy');
// ⚠ A PRISTINE, UNMIGRATED COPY, taken before anything opens `fx.path`. The first version of this
// probe copied its later fixtures FROM fx.path after the add-column test had already walked it to
// version 2 — so the doomed migration was numbered at-or-below the store's own version, was
// skipped, and three checks reported on a migration that never ran. Two of them PASSED while
// proving nothing. The fixture, not the code, was the thing that had stopped discriminating.
const pristine = path.join(tmp, 'pristine.db');
fs.copyFileSync(fx.path, pristine);
out(`COMMAND: node ${path.relative(process.cwd(), __filename)}`);
out(`FIXTURE: ${fx.source} — user_version ${fx.version}, jobs_log rows ${fx.rows}`);
out('');

// ---- 1 · the legacy store is adopted, not rebuilt ----------------------------------------
check('the fixture really is a pre-versioning store (user_version 0) — else this probe tests nothing',
  fx.version === 0, `user_version=${fx.version}`);
check('the fixture is NOT fresh — it already has tables, which is the case schema.sql cannot reach',
  (() => { const d = new DatabaseSync(fx.path); const f = isFreshStore(d); d.close(); return !f; })());

let a = open(fx.path);
check('opening an existing store walks it forward and STAMPS it', a.res.to === LATEST,
  `from=${a.res.from} to=${a.res.to} applied=[${a.res.applied}]`);
check('adoption ran the baseline migration rather than assuming the store was current',
  a.res.applied.includes(1), `applied=[${a.res.applied}]`);
const rowsAfter = Number(a.db.prepare('SELECT count(*) AS n FROM jobs_log').get().n || 0);
check('adoption did not touch the data', rowsAfter === fx.rows, `rows ${fx.rows} -> ${rowsAfter}`);
a.db.close();

const b = open(fx.path);
check('re-opening is a no-op — migrations are not re-applied on every start',
  b.res.applied.length === 0 && b.res.from === LATEST, `applied=[${b.res.applied}]`);
b.db.close();

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
out(`FIXTURE WAS: ${fx.source}`);
out(`EXIT: ${passed === checks.length ? 0 : 1}`);
out(`WALL_MS: ${Date.now() - started}`);
fs.rmSync(tmp, { recursive: true, force: true });
process.exit(passed === checks.length ? 0 : 1);
