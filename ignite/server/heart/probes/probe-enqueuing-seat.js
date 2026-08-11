'use strict';

// Task 7.389 — the ENQUEUING-SEAT column (G-leader-0805-0625; G-137's precondition (b)).
//
// Isolation: THROWAWAY dbs under os.tmpdir(), per the convention every heart probe follows. This
// probe WRITES queue/jobs_log rows and RUNS A MIGRATION — it must NEVER be pointed at the live
// store. The capture is truncated at module load, BEFORE any work, so a probe that dies at start
// leaves an EMPTY capture rather than the previous run's stale `EXIT: 0` (the D51 evidence-husk
// hazard).
//
// ⚠ WHAT THIS PROBE EXISTS TO PROVE — four claims, and the third is the one a fresh-fixture suite
// cannot see:
//   (a) a FRESH store gets `enqueuing_seat` on BOTH tables from `schema.sql`;
//   (b) the value WRITES THROUGH the whole path — enqueue → fire → jobs_log — rather than being
//       accepted at the door and dropped one layer in (the 7.10 failure this campaign already ate
//       once: producer green, consumer green, the line between them dropping the field);
//   (c) an EXISTING store at the OLD shape is walked forward by MIGRATION_ENQUEUING_SEAT — G-135's
//       lesson is that a schema change is invisible exactly where it is tested and broken where it
//       matters, so the migration leg builds the old shape first rather than asserting against a
//       store that already had the column;
//   (d) ABSENCE NEVER BECOMES A GRANT — `undefined` and `''` both land as SQL NULL. This is not
//       tidiness: `seatPrincipalResolver` compares this column against the caller's proven seat, so
//       an empty string stored here would compare equal to an unproven caller's empty seat and hand
//       `creator-seat` over the row to whoever asked. The store half of that pair is asserted here;
//       the resolver half is asserted in `probe-remove-job`.
//
// ⚠ POSITIVE CONTROLS: every "it is NULL" check is paired with a nearest-neighbour case that is
// NON-null in the same run, so an implementation that wrote NULL unconditionally — which would
// satisfy every absence assertion — turns this suite RED instead of reading as a clean sweep.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-enqueuing-seat.out');
fs.writeFileSync(outPath, '');

const { openHeartStore, closeHeartStore } = require('../heart-store');
const { migrate, MIGRATION_ENQUEUING_SEAT, MIGRATIONS } = require('../migrations');

const tmpDb = path.join(os.tmpdir(), `heart-probe-enqseat-${Date.now()}-${process.pid}.db`);
const tmpOld = path.join(os.tmpdir(), `heart-probe-enqseat-old-${Date.now()}-${process.pid}.db`);

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// Read back from DISK on a fresh raw connection — never the store's own in-memory view.
function cols(db, table) {
  const raw = new DatabaseSync(db, { readOnly: true });
  try { return raw.prepare(`PRAGMA table_info(${table})`).all().map((r) => r.name); } finally { raw.close(); }
}
function queueRow(queueId) {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try { return raw.prepare('SELECT queue_id, enqueued_by, enqueuing_seat FROM queue WHERE queue_id = ?').get(queueId) || null; } finally { raw.close(); }
}
function execRow(execId) {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try { return raw.prepare('SELECT exec_id, queue_id, enqueued_by, enqueuing_seat FROM jobs_log WHERE exec_id = ?').get(execId) || null; } finally { raw.close(); }
}

const RUN_AT = '2026-01-01T00:00:00Z';
const ARGS = JSON.stringify({ profile: 'test-sleep' });

try {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  // ── LEG 1 · a FRESH store carries the column on BOTH tables ──────────────────────────────────
  const store = openHeartStore({ dbPath: tmpDb, profiles: { 'test-sleep': { headed: false } } });
  store.registerJob({
    jobId: 'launch-worker',
    actionType: 'launch-agent',
    function: 'spawnLaunchAgent',
    argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: {} }),
    enabled: 1,
  });

  const qCols = cols(tmpDb, 'queue');
  const jCols = cols(tmpDb, 'jobs_log');
  check('fresh store: queue carries enqueuing_seat', qCols.includes('enqueuing_seat'), `queue columns: ${qCols.join(',')}`);
  check('fresh store: jobs_log carries enqueuing_seat', jCols.includes('enqueuing_seat'), `jobs_log columns: ${jCols.join(',')}`);

  // ── LEG 2 · the seat ROUND-TRIPS to disk at enqueue ──────────────────────────────────────────
  const seated = store.enqueue({
    jobId: 'launch-worker', args: ARGS, triggerKind: 'scheduled', runAt: RUN_AT,
    enqueuedBy: 'sender-alpha', enqueuingSeat: 'client-x/leader',
  });
  const seatedRow = queueRow(seated.queue_id);
  check('a queue row enqueued by a PROVEN seat stores that seat, read back from disk',
    seatedRow && seatedRow.enqueuing_seat === 'client-x/leader',
    seatedRow ? `enqueued_by=${seatedRow.enqueued_by} enqueuing_seat=${seatedRow.enqueuing_seat}` : 'row missing');

  check('the sender-id column is UNTOUCHED by the new one — they are two different facts, not a rename',
    seatedRow && seatedRow.enqueued_by === 'sender-alpha',
    seatedRow ? `enqueued_by=${seatedRow.enqueued_by}` : 'row missing');

  // ── LEG 3 · ABSENCE IS NULL, both shapes, with a live positive control ───────────────────────
  // These two are the load-bearing absence checks. LEG 2 above is their positive control: if the
  // writer normalized EVERYTHING to NULL, that check is already red, so a green here means the
  // column genuinely discriminates present from absent.
  const unseated = store.enqueue({
    jobId: 'launch-worker', args: ARGS, triggerKind: 'scheduled', runAt: RUN_AT,
    enqueuedBy: 'sender-bravo',
  });
  const unseatedRow = queueRow(unseated.queue_id);
  check('an UNPROVEN caller (no enqueuingSeat at all) stores SQL NULL, not undefined and not a string',
    unseatedRow && unseatedRow.enqueuing_seat === null,
    unseatedRow ? `enqueuing_seat=${JSON.stringify(unseatedRow.enqueuing_seat)}` : 'row missing');

  const emptySeat = store.enqueue({
    jobId: 'launch-worker', args: ARGS, triggerKind: 'scheduled', runAt: RUN_AT,
    enqueuedBy: 'sender-charlie', enqueuingSeat: '',
  });
  const emptyRow = queueRow(emptySeat.queue_id);
  check('an EMPTY-STRING seat is normalized to NULL — else it would compare equal to an unproven '
    + "caller's empty seat at the grant and hand creator-seat over the row to anyone",
    emptyRow && emptyRow.enqueuing_seat === null,
    emptyRow ? `enqueuing_seat=${JSON.stringify(emptyRow.enqueuing_seat)}` : 'row missing');

  // ── LEG 4 · THE WRITE-THROUGH · the seat survives the FIRE into jobs_log ─────────────────────
  // This is claim (b), and it is the one that catches a field accepted at the door and dropped one
  // layer in. It matters concretely: a one-shot fire DELETES its queue row, so a jobs_log row that
  // did not carry the value would lose the seat at exactly the moment the turn it authorizes
  // begins to exist — and `canKillSession` is handed the jobs_log row, not the queue row.
  const firedSeated = store.fireQueueRow({ queueId: seated.queue_id, now: new Date(), tick: 1 });
  const firedSeatedRow = execRow(firedSeated.exec_id);
  check('FIRE denormalizes the seat into jobs_log — the row canKillSession is handed carries it',
    firedSeatedRow && firedSeatedRow.enqueuing_seat === 'client-x/leader',
    firedSeatedRow ? `enqueuing_seat=${firedSeatedRow.enqueuing_seat}` : 'exec row missing');

  check('the queue row is GONE after its one-shot fire — so the jobs_log copy is the ONLY surviving '
    + 'record of the seat, which is why it is denormalized rather than joined',
    queueRow(seated.queue_id) === null);

  const firedUnseated = store.fireQueueRow({ queueId: unseated.queue_id, now: new Date(), tick: 2 });
  const firedUnseatedRow = execRow(firedUnseated.exec_id);
  check('an unseated queue row fires to an unseated jobs_log row (NULL through, never a placeholder)',
    firedUnseatedRow && firedUnseatedRow.enqueuing_seat === null,
    firedUnseatedRow ? `enqueuing_seat=${JSON.stringify(firedUnseatedRow.enqueuing_seat)}` : 'exec row missing');

  // ── LEG 5 · recordExecutionStart — the daemon's OWN internal starts hold no seat ─────────────
  const internal = store.recordExecutionStart({
    jobId: 'launch-worker', actionType: 'launch-agent', args: ARGS,
    enqueuedBy: 'attached-foreground', firedTick: 3, firedAt: new Date(),
  });
  const internalRow = execRow(internal.exec_id);
  check('recordExecutionStart defaults the seat to NULL — the daemon\'s own starts prove no seat',
    internalRow && internalRow.enqueuing_seat === null,
    internalRow ? `enqueuing_seat=${JSON.stringify(internalRow.enqueuing_seat)}` : 'exec row missing');

  const internalSeated = store.recordExecutionStart({
    jobId: 'launch-worker', actionType: 'launch-agent', args: ARGS,
    enqueuedBy: 'sender-alpha', enqueuingSeat: 'client-x/engineer', firedTick: 4, firedAt: new Date(),
  });
  const internalSeatedRow = execRow(internalSeated.exec_id);
  check('...and it STORES one when given it — the positive control for the default above',
    internalSeatedRow && internalSeatedRow.enqueuing_seat === 'client-x/engineer',
    internalSeatedRow ? `enqueuing_seat=${internalSeatedRow.enqueuing_seat}` : 'exec row missing');

  closeHeartStore();

  // ── LEG 6 · THE ONE THAT MATTERS · an EXISTING store is walked forward by the migration ──────
  // Built at the OLD shape deliberately: queue and jobs_log WITHOUT `enqueuing_seat`, user_version
  // stamped to 3 (the shape before this migration). Asserting against a store that already had the
  // column would be the exact blindness G-135 documents.
  {
    const old = new DatabaseSync(tmpOld);
    old.exec(`
      CREATE TABLE queue (
        queue_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, args TEXT NOT NULL DEFAULT '{}',
        session_mode TEXT NOT NULL DEFAULT 'headless', trigger_kind TEXT NOT NULL, run_at TEXT NOT NULL,
        repeat_rule TEXT, interval_seconds INTEGER, max_fires INTEGER,
        enqueued_by TEXT NOT NULL, enqueued_at TEXT NOT NULL
      );
      CREATE TABLE jobs_log (
        exec_id INTEGER PRIMARY KEY AUTOINCREMENT, queue_id INTEGER, job_id TEXT NOT NULL,
        action_type TEXT NOT NULL, args TEXT NOT NULL, enqueued_by TEXT NOT NULL,
        session_mode TEXT NOT NULL DEFAULT 'headless', fired_tick INTEGER NOT NULL,
        fired_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'launching'
      );
    `);
    old.exec("INSERT INTO queue (job_id, trigger_kind, run_at, enqueued_by, enqueued_at) "
      + "VALUES ('legacy','scheduled','t','legacy-sender','t');");
    old.exec("INSERT INTO jobs_log (job_id, action_type, args, enqueued_by, fired_tick, fired_at) "
      + "VALUES ('legacy','launch-agent','{}','legacy-sender',1,'t');");
    old.exec('PRAGMA user_version = 3;');

    const qBefore = old.prepare('PRAGMA table_info(queue)').all().map((r) => r.name);
    const jBefore = old.prepare('PRAGMA table_info(jobs_log)').all().map((r) => r.name);
    check('migration precondition: the store genuinely LACKS the column on BOTH tables before migrating',
      !qBefore.includes('enqueuing_seat') && !jBefore.includes('enqueuing_seat'),
      `queue: ${qBefore.join(',')} | jobs_log: ${jBefore.join(',')}`);

    // Injected, exactly as `migrate()` exposes for this purpose — the migration is NOT registered.
    migrate(old, { migrations: [...MIGRATIONS, MIGRATION_ENQUEUING_SEAT] });

    const qAfter = old.prepare('PRAGMA table_info(queue)').all().map((r) => r.name);
    const jAfter = old.prepare('PRAGMA table_info(jobs_log)').all().map((r) => r.name);
    check('after migrating: queue carries enqueuing_seat', qAfter.includes('enqueuing_seat'), `queue: ${qAfter.join(',')}`);
    check('after migrating: jobs_log carries enqueuing_seat', jAfter.includes('enqueuing_seat'), `jobs_log: ${jAfter.join(',')}`);

    // NO BACKFILL, and it is a ruling rather than an omission: the enqueuing seat of an
    // already-written row is NOT RECOVERABLE (sender→seat is many-to-one under a shared token), so
    // any backfill would be a guess written as a fact — and the guess would then hand `creator-seat`
    // to whoever it named. A pre-existing row must read NULL.
    const legacyQ = old.prepare('SELECT enqueued_by, enqueuing_seat FROM queue WHERE job_id = ?').get('legacy');
    const legacyJ = old.prepare('SELECT enqueued_by, enqueuing_seat FROM jobs_log WHERE job_id = ?').get('legacy');
    check('NO BACKFILL: pre-existing rows read NULL on both tables, never a guess derived from enqueued_by',
      legacyQ && legacyQ.enqueuing_seat === null && legacyJ && legacyJ.enqueuing_seat === null,
      `queue=${JSON.stringify(legacyQ)} jobs_log=${JSON.stringify(legacyJ)}`);
    check('...and the migration did not disturb the sender-id it could have been tempted to copy',
      legacyQ && legacyQ.enqueued_by === 'legacy-sender' && legacyJ && legacyJ.enqueued_by === 'legacy-sender');

    // IDEMPOTENCE: `up()` carries the column-exists guard SQLite's ALTER TABLE forces. Re-running
    // must be a clean no-op, since that is what makes arming it a no-op on stores built from
    // schema.sql — which already carry the column.
    let reran = null;
    try { MIGRATION_ENQUEUING_SEAT.up(old); } catch (err) { reran = err; }
    check('up() is IDEMPOTENT — re-running against a store that already has the column does not throw',
      reran === null, reran ? `threw: ${reran.message}` : 'clean');

    old.close();
  }

  // ── LEG 7 · THE ARMING STATE IS ASSERTED, NOT ASSUMED ────────────────────────────────────────
  // Inverted 2026-08-11 with the owner's ruling on task 7.707, which armed the migration in the same
  // change that renamed the column. Before that these two rows asserted the UNARMED state, so an
  // arming could not slip in silently; now they assert the ARMED state, so an accidental REMOVAL of
  // the push goes RED instead — the same guard, pointed the other way (probe-job-seat-home's leg 5).
  check('MIGRATION_ENQUEUING_SEAT IS in MIGRATIONS (armed, per the task-7.707 ruling)',
    MIGRATIONS.includes(MIGRATION_ENQUEUING_SEAT),
    `MIGRATIONS versions: ${MIGRATIONS.map((m) => m.version).join(',')}; mine: ${MIGRATION_ENQUEUING_SEAT.version}`);

  check('its version is carried by EXACTLY ONE armed migration — a duplicate version would make the '
    + 'walk-forward ambiguous and run the same ALTER twice',
    MIGRATIONS.filter((m) => m.version === MIGRATION_ENQUEUING_SEAT.version).length === 1,
    `mine: ${MIGRATION_ENQUEUING_SEAT.version}`);

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`ENQUEUING_SEAT_OK: ${failed.length === 0}`);
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
