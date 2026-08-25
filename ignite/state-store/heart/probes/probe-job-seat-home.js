'use strict';

// Task 7.12 — the job->seat pointer (owner ruling `r-job-seat-home`, 2026-07-27).
//
// Isolation: a THROWAWAY db under os.tmpdir(), per the convention every heart probe follows. This
// probe WRITES catalogue rows and RUNS A MIGRATION — it must NEVER be pointed at the live store.
//
// The capture is truncated at module load, BEFORE any work, so a probe that dies at start leaves an
// EMPTY capture rather than the previous run's stale `EXIT: 0` (the D51 evidence-husk hazard).
//
// ⚠ WHAT THIS PROBE EXISTS TO PROVE, and it is TWO claims that are easy to conflate:
//   (a) a FRESH store gets the columns from `schema.sql`, and
//   (b) an EXISTING store gets them from MIGRATION_JOB_SEAT_HOME.
// (b) is the one that matters and the one a fresh-fixture suite CANNOT see — G-135's whole lesson
// is that a schema change is invisible exactly where it is tested and broken where it matters. So
// the migration leg here builds a store at the OLD shape first and walks it forward, rather than
// asserting against a store that already had the columns.
//
// ⚠ POSITIVE CONTROL (bars 11's second half): a negative needs a positive control in the same run.
// Every refusal check below is paired with an ACCEPTANCE of the nearest-neighbour input, so a bug
// that refused everything would turn this suite RED rather than reading as a clean sweep.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-job-seat-home.out');
fs.writeFileSync(outPath, '');

const { openHeartStore, closeHeartStore, E_BAD_ARGS } = require('../heart-store');
const { migrate, MIGRATION_JOB_SEAT_HOME, MIGRATIONS } = require('../migrations');

const tmpDb = path.join(os.tmpdir(), `heart-probe-jobseat-${Date.now()}-${process.pid}.db`);
const tmpOld = path.join(os.tmpdir(), `heart-probe-jobseat-old-${Date.now()}-${process.pid}.db`);

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// Read back from DISK on a fresh raw connection — never the store's own in-memory view.
function readBack(jobId) {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT job_id, goal_name, seat_name FROM jobs WHERE job_id = ?').get(jobId) || null;
  } finally {
    raw.close();
  }
}

function refusal(fn) {
  try {
    fn();
    return null;
  } catch (err) {
    return err;
  }
}

const BASE = { actionType: 'launch-agent', function: 'spawn', argsSchema: '{"required":{"profile":"string"}}' };

try {
  // ── LEG 1 · a FRESH store carries the columns from schema.sql ─────────────────────────────────
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  const store = openHeartStore({ dbPath: tmpDb, profiles: { default: { headed: false } } });

  const cols = (() => {
    const raw = new DatabaseSync(tmpDb, { readOnly: true });
    try { return raw.prepare('PRAGMA table_info(jobs)').all().map((r) => r.name); } finally { raw.close(); }
  })();
  check('fresh store: jobs carries goal_name', cols.includes('goal_name'), `columns: ${cols.join(',')}`);
  check('fresh store: jobs carries seat_name', cols.includes('seat_name'));

  // ── LEG 2 · the pointer round-trips to DISK ───────────────────────────────────────────────────
  store.registerJob({ jobId: 'homed', ...BASE, goalName: 'build-core-daemon-mvp', seatName: 'engineer' });
  const homed = readBack('homed');
  check('a homed job stores both halves, read back from disk',
    homed && homed.goal_name === 'build-core-daemon-mvp' && homed.seat_name === 'engineer',
    homed ? `goal=${homed.goal_name} seat=${homed.seat_name}` : 'row missing');

  // POSITIVE CONTROL for the refusals below: the unhomed case must still be ACCEPTED. If the
  // both-or-neither guard were written as "reject unless both present", this check goes red.
  store.registerJob({ jobId: 'unhomed', ...BASE });
  const unhomed = readBack('unhomed');
  check('an UNHOMED job is still accepted, both halves NULL (the interim path stays reachable)',
    unhomed && unhomed.goal_name === null && unhomed.seat_name === null,
    unhomed ? `goal=${unhomed.goal_name} seat=${unhomed.seat_name}` : 'row missing');

  // ── LEG 3 · a HALF pointer is refused at the writer, both directions ──────────────────────────
  const goalOnly = refusal(() => store.registerJob({ jobId: 'half-a', ...BASE, goalName: 'g' }));
  check('goal_name without seat_name is refused E_BAD_ARGS',
    goalOnly && goalOnly.code === E_BAD_ARGS,
    goalOnly ? `${goalOnly.code}` : 'ACCEPTED — the half-pointer guard did not fire');

  const seatOnly = refusal(() => store.registerJob({ jobId: 'half-b', ...BASE, seatName: 's' }));
  check('seat_name without goal_name is refused E_BAD_ARGS',
    seatOnly && seatOnly.code === E_BAD_ARGS,
    seatOnly ? `${seatOnly.code}` : 'ACCEPTED — the half-pointer guard did not fire');

  check('neither half-pointer landed a row (refusal wrote nothing)',
    readBack('half-a') === null && readBack('half-b') === null);

  const emptyGoal = refusal(() => store.registerJob({ jobId: 'empty', ...BASE, goalName: '', seatName: 's' }));
  check('an EMPTY-STRING goal_name is refused, not silently stored',
    emptyGoal && emptyGoal.code === E_BAD_ARGS,
    emptyGoal ? `${emptyGoal.code}` : 'ACCEPTED');

  closeHeartStore();

  // ── LEG 4 · THE ONE THAT MATTERS · an EXISTING store is walked forward by the migration ───────
  // Built at the OLD shape deliberately: `jobs` WITHOUT the two columns, user_version stamped to 2
  // (the shape before this migration). Asserting against a store that already had them would be
  // the exact blindness G-135 documents.
  {
    const old = new DatabaseSync(tmpOld);
    old.exec(`
      CREATE TABLE jobs (
        job_id TEXT PRIMARY KEY, action_type TEXT NOT NULL, function TEXT NOT NULL,
        args_schema TEXT NOT NULL DEFAULT '{}', description TEXT,
        enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
      );
    `);
    // A real v2 store also HAS `queue` and `jobs_log`; the fixture omitted them until the
    // enqueuing-seat migration (v4) was armed and the walk-forward tried to ALTER them.
    old.exec('CREATE TABLE queue (queue_id INTEGER PRIMARY KEY, job_id TEXT);');
    old.exec('CREATE TABLE jobs_log (exec_id INTEGER PRIMARY KEY, job_id TEXT);');
    old.exec("INSERT INTO jobs VALUES ('legacy','launch-agent','spawn','{}',NULL,1,'t','t');");
    old.exec('PRAGMA user_version = 2;');

    const before = old.prepare('PRAGMA table_info(jobs)').all().map((r) => r.name);
    check('migration precondition: the store genuinely LACKS the columns before migrating',
      !before.includes('goal_name') && !before.includes('seat_name'),
      `columns before: ${before.join(',')}`);

    // Injected, exactly as `migrate()` exposes for this purpose — the migration is NOT registered.
    const res = migrate(old, { migrations: [...MIGRATIONS, MIGRATION_JOB_SEAT_HOME] });
    const after = old.prepare('PRAGMA table_info(jobs)').all().map((r) => r.name);
    check('MIGRATION_JOB_SEAT_HOME adds both columns to an EXISTING store',
      after.includes('goal_name') && after.includes('seat_name'),
      `${res.from} -> ${res.to}; columns after: ${after.join(',')}`);

    const legacy = old.prepare("SELECT goal_name, seat_name FROM jobs WHERE job_id='legacy'").get();
    check('the pre-existing row survives and is UNHOMED (no backfill, per r-job-seat-home)',
      legacy && legacy.goal_name === null && legacy.seat_name === null,
      legacy ? `goal=${legacy.goal_name} seat=${legacy.seat_name}` : 'row LOST');

    // Idempotence: the guard means a second run is a no-op, which is what makes the owner's
    // eventual one-line registration safe on a store that already ran it by injection.
    const again = refusal(() => MIGRATION_JOB_SEAT_HOME.up(old));
    check('up() is idempotent — a second application is a no-op, not an error',
      again === null, again ? again.message : 'no throw');

    old.close();
  }

  // ── LEG 5 · THE MIGRATION IS ARMED ────────────────────────────────────────────────────────────
  // Inverted 2026-08-04 per p-migration-arming-granted: an accidental REMOVAL of the push now goes
  // RED. `exactly once` is deliberate — a duplicate push makes migrate() run the same ALTER twice.
  check('MIGRATION_JOB_SEAT_HOME IS in MIGRATIONS exactly once (armed, per p-migration-arming-granted)',
    MIGRATIONS.includes(MIGRATION_JOB_SEAT_HOME)
    && MIGRATIONS.filter((m) => m.version === MIGRATION_JOB_SEAT_HOME.version).length === 1,
    `MIGRATIONS versions: ${MIGRATIONS.map((m) => m.version).join(',')}; mine: ${MIGRATION_JOB_SEAT_HOME.version}`);

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`JOB_SEAT_HOME_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
} catch (err) {
  out('ERROR:', err.message, err.stack);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
} finally {
  try { closeHeartStore(); } catch {}
  for (const f of [tmpDb, tmpOld]) {
    try { fs.unlinkSync(f); } catch {}
    try { fs.unlinkSync(f + '-wal'); } catch {}
    try { fs.unlinkSync(f + '-shm'); } catch {}
  }
}
