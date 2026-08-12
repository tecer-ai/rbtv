'use strict';

// probe-deregister-purge — the PURGE arm of `deregisterJob`, at the store layer.
//
// THE FAILURE THIS COVERS. Registration is create-only, so before the purge arm every
// `register-job` burnt its id for the life of the store. That is tolerable for the ~10
// hand-authored definitions the catalogue was designed for and is not tolerable for the
// machine-minted goal-scoped ids (`<goal>-workflow-start`, one `seat-<goal>-<seat>` per
// seat) the goals machinery writes: deleting a goal folder stranded ALL of them — 18 rows
// for one goal on the live box, in a catalogue that had reached 44 rows with 22 dead.
//
// WHY THIS PROBE IS AT THE STORE LAYER AND NOT ONLY BEHIND THE CLI. The three guards are
// the feature — a delete without them is the dangerous half — and two of the three
// (`pending-queue-rows`, `live-executions`) need STATE that a CLI probe would have to
// spawn real work to produce. Here they are seeded directly and deterministically. The
// end-to-end payoff (the row is gone through the tool's own read surface, and the id
// re-registers) is covered one layer up in `cli/probes/probe-cli-deregister.js`; the two
// are deliberately not redundant.
//
// What it proves:
//   1. CONTROL — purging an ENABLED job is REFUSED (reason `enabled`) and deletes nothing.
//   2. CONTROL — purging a disabled job with a PENDING QUEUE ROW is REFUSED
//      (reason `pending-queue-rows`) and deletes nothing.
//   3. CONTROL — purging a disabled job with a NON-TERMINAL execution is REFUSED
//      (reason `live-executions`) and deletes nothing.
//   4. A TERMINAL execution does NOT block the purge — the guard is "still running",
//      never "ever ran", or a goal's seats could never be reclaimed at all.
//   5. THE PAYOFF — the row is GONE from disk and the id REGISTERS AGAIN, with a
//      different action type, proving the id is genuinely free and not merely re-enabled.
//   6. History survives: the purged job's `jobs_log` rows are still on disk afterwards,
//      which is the claim that made deletion admissible (`jobs_log.job_id` carries no FK).
//
// Isolation: a THROWAWAY db under os.tmpdir(), per the convention every heart probe
// follows. This probe DELETES catalogue rows — it must NEVER be pointed at the live store.
//
// The capture is truncated at module load, BEFORE any work, so a probe that dies at start
// leaves an EMPTY capture rather than the previous run's stale `EXIT: 0` (D51).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-deregister-purge.out');
fs.writeFileSync(outPath, '');

const {
  openHeartStore, closeHeartStore, E_JOB_PURGE_REFUSED, E_JOB_EXISTS,
} = require('../heart-store');

const tmpDb = path.join(os.tmpdir(), `heart-probe-purge-${Date.now()}-${process.pid}.db`);

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// Read back from DISK on a fresh raw connection — never the store's own in-memory view.
// A purge's whole claim is that the ROW IS GONE, and only disk can answer that.
function jobIds() {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT job_id FROM jobs ORDER BY job_id').all().map((r) => r.job_id);
  } finally {
    raw.close();
  }
}

function jobsLogIdsFor(jobId) {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT exec_id FROM jobs_log WHERE job_id = ? ORDER BY exec_id').all(jobId).map((r) => r.exec_id);
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

// `launch-agent` requires `profile` in args_schema.required (the S-2(a) register-time gate).
const SCHEMA = JSON.stringify({ required: {}, optional: { workdir: 'string' } });

function registerSeatJob(store, jobId) {
  return store.registerJob({
    jobId, actionType: 'launch-agent', function: 'spawnLaunchAgent', argsSchema: SCHEMA,
  });
}

function futureIso() {
  return new Date(Date.now() + 3600000).toISOString().replace(/\.\d{3}Z$/, 'Z');
}

try {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const store = openHeartStore({ dbPath: tmpDb, profiles: { default: { headed: false } } });

  // --- 1. CONTROL: an ENABLED job may not be purged. ---------------------------------
  registerSeatJob(store, 'seat-goal-enabled');
  const stillEnabled = refusal(() => store.deregisterJob({ jobId: 'seat-goal-enabled', purge: true }));
  check('CONTROL: purging an ENABLED job is refused (reason `enabled`)',
    stillEnabled !== null && stillEnabled.code === E_JOB_PURGE_REFUSED
      && stillEnabled.details.reason === 'enabled',
    `code=${stillEnabled && stillEnabled.code} reason=${stillEnabled && stillEnabled.details.reason}`);
  check('CONTROL: the refused purge deleted nothing',
    jobIds().includes('seat-goal-enabled'), `ids=${JSON.stringify(jobIds())}`);

  // --- 2. CONTROL: a PENDING QUEUE ROW blocks the purge. -----------------------------
  // Enqueued BEFORE the disable, because enqueue itself refuses a disabled job — which is
  // exactly how a real goal teardown produces this state: rows queued, then the definition
  // retired, leaving them deferred forever.
  registerSeatJob(store, 'seat-goal-queued');
  store.enqueue({
    jobId: 'seat-goal-queued',
    args: JSON.stringify({}),
    triggerKind: 'scheduled',
    runAt: futureIso(),
    enqueuedBy: 'probe-deregister-purge',
  });
  store.deregisterJob({ jobId: 'seat-goal-queued' });
  const queued = refusal(() => store.deregisterJob({ jobId: 'seat-goal-queued', purge: true }));
  check('CONTROL: a PENDING QUEUE ROW refuses the purge (reason `pending-queue-rows`)',
    queued !== null && queued.code === E_JOB_PURGE_REFUSED
      && queued.details.reason === 'pending-queue-rows' && queued.details.pending_queue_rows === 1,
    `code=${queued && queued.code} details=${JSON.stringify(queued && queued.details)}`);
  check('CONTROL: the queue-blocked purge deleted nothing',
    jobIds().includes('seat-goal-queued'), `ids=${JSON.stringify(jobIds())}`);
  // ⚑ The refusal must be the NAMED one, not an SQLITE_CONSTRAINT leaking out of the FK.
  check('CONTROL: the queue refusal is the guard talking, not a raw FK violation',
    queued !== null && !/FOREIGN KEY|SQLITE_CONSTRAINT/i.test(queued.message),
    `message=${queued && queued.message.slice(0, 120)}`);

  // --- 3. CONTROL: a NON-TERMINAL execution blocks the purge. ------------------------
  // The guard that is NOT visible from the schema, and the reason it exists: with the row
  // gone, `_findSeatHolder`'s `seatKeyOf(getJob(...))` reads null for this job, so the
  // idempotent door stops seeing the running turn — and a re-registration of the id (the
  // whole point of a purge) could then double-fire the seat under a turn still in flight.
  registerSeatJob(store, 'seat-goal-live');
  const liveExec = store.recordExecutionStart({
    jobId: 'seat-goal-live',
    actionType: 'launch-agent',
    args: JSON.stringify({}),
    enqueuedBy: 'probe-deregister-purge',
    sessionMode: 'headless',
    firedTick: 1,
    firedAt: new Date(),
  });
  store.updateExecutionStatus(liveExec.exec_id, { status: 'running' });
  store.deregisterJob({ jobId: 'seat-goal-live' });
  const live = refusal(() => store.deregisterJob({ jobId: 'seat-goal-live', purge: true }));
  check('CONTROL: a NON-TERMINAL execution refuses the purge (reason `live-executions`)',
    live !== null && live.code === E_JOB_PURGE_REFUSED
      && live.details.reason === 'live-executions' && live.details.live_executions === 1,
    `code=${live && live.code} details=${JSON.stringify(live && live.details)}`);
  check('CONTROL: the live-execution purge deleted nothing',
    jobIds().includes('seat-goal-live'), `ids=${JSON.stringify(jobIds())}`);

  // --- 4. A TERMINAL execution does NOT block it. -----------------------------------
  // The distinguishing check for guard 3: if it read "ever ran" instead of "still running",
  // every seat of every finished goal would be permanently unreclaimable and the whole arm
  // would be useless on exactly the population it was built for.
  store.updateExecutionStatus(liveExec.exec_id, { status: 'done', endedAt: new Date().toISOString() });
  const afterTerminal = refusal(() => store.deregisterJob({ jobId: 'seat-goal-live', purge: true }));
  check('a TERMINAL execution does NOT block the purge (the guard is "running", not "ever ran")',
    afterTerminal === null && !jobIds().includes('seat-goal-live'),
    `refusal=${afterTerminal && afterTerminal.code} ids=${JSON.stringify(jobIds())}`);

  // --- 5. THE PAYOFF: the id is genuinely FREE. -------------------------------------
  // Re-registered with a DIFFERENT action type on purpose: a row that had merely been
  // re-enabled would still carry `launch-agent`, so this distinguishes a real delete from
  // a revive-in-place. It is also the case the create-only ruling refuses in place — which
  // is the point: repointing is admissible only across a purge, never silently.
  const reborn = store.registerJob({
    jobId: 'seat-goal-live',
    actionType: 'fire-tool',
    function: 'runTool',
    argsSchema: JSON.stringify({ required: { tool: 'string' } }),
    description: 're-registered after purge',
  });
  check('PAYOFF: the purged id registers again, with a different action type',
    reborn && reborn.job_id === 'seat-goal-live' && reborn.action_type === 'fire-tool'
      && reborn.enabled === 1,
    `row=${JSON.stringify(reborn)}`);
  // And the create-only rule still holds over the reborn row — a purge frees an id, it
  // does not turn registration into an upsert.
  const dupAfter = refusal(() => registerSeatJob(store, 'seat-goal-live'));
  check('create-only still holds after a purge (a second register is E_JOB_EXISTS)',
    dupAfter !== null && dupAfter.code === E_JOB_EXISTS,
    `code=${dupAfter && dupAfter.code}`);

  // --- 6. History survives the delete. ----------------------------------------------
  // The claim that made deletion admissible at all: `queue.job_id` is the only foreign key
  // into `jobs`, and `jobs_log.job_id` is a plain column that denormalizes action_type and
  // args, so a past execution reads correctly with the catalogue row gone.
  const survivingLog = jobsLogIdsFor('seat-goal-live');
  check('the purged job\'s jobs_log rows are STILL ON DISK (no FK, history preserved)',
    survivingLog.length === 1 && survivingLog[0] === liveExec.exec_id,
    `exec_ids=${JSON.stringify(survivingLog)} expected=[${liveExec.exec_id}]`);

  out('');
  out('--- final catalogue ---', JSON.stringify(jobIds()));

  closeHeartStore();

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`DEREGISTER_PURGE_OK: ${failed.length === 0}`);
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
  try { fs.unlinkSync(tmpDb); } catch {}
  try { fs.unlinkSync(tmpDb + '-wal'); } catch {}
  try { fs.unlinkSync(tmpDb + '-shm'); } catch {}
}
