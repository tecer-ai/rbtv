'use strict';

// p4-0 — sender-initiated queue-row removal (D65(A)).
//
// Isolation: a THROWAWAY db under os.tmpdir(), per the convention every heart
// probe follows (probe-enqueue / probe-jobslog / probe-session-row). This probe
// DELETES rows — it must NEVER be pointed at the live store (.rbtv/heart/), which
// a live daemon is ticking against.
//
// The capture is truncated at module load, BEFORE any work — a probe that dies at
// start (module-resolution/syntax error) then leaves an EMPTY capture rather than
// the previous run's stale `EXIT: 0` (the D51 evidence-husk hazard). The exit code
// of the process remains the truth; this footer is a hint.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-queue-remove.out');
fs.writeFileSync(outPath, '');

const { openHeartStore, closeHeartStore, E_QUEUE_ROW_NOT_FOUND, E_BAD_ARGS } = require('../heart-store');

const tmpDb = path.join(os.tmpdir(), `heart-probe-queue-remove-${Date.now()}-${process.pid}.db`);

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// Read back from DISK on a fresh raw node:sqlite connection — never the store's
// own in-memory view. Read-only: a reader can never be a second writer.
function readBackQueueIds() {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT queue_id, trigger_kind FROM queue ORDER BY queue_id').all();
  } finally {
    raw.close();
  }
}

function readBackExecIds() {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT exec_id, queue_id, job_id, status FROM jobs_log ORDER BY exec_id').all();
  } finally {
    raw.close();
  }
}

try {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const store = openHeartStore({
    dbPath: tmpDb,
    profiles: { default: { headed: false } },
  });
  store.registerJob({
    jobId: 'launch-worker',
    actionType: 'launch-agent',
    function: 'spawnLaunchAgent',
    argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: {} }),
    enabled: 1,
  });

  const now = new Date();
  const runAt = now.toISOString().replace(/\.\d{3}Z$/, 'Z');
  const args = JSON.stringify({ profile: 'default' });

  // A: a one-shot pending row.
  const rowA = store.enqueue({
    jobId: 'launch-worker', args, sessionMode: 'headless',
    triggerKind: 'scheduled', runAt, enqueuedBy: 'owner',
  });
  // B: a REPEATING (periodic) trigger — the design point's subject.
  const rowB = store.enqueue({
    jobId: 'launch-worker', args, sessionMode: 'headless',
    triggerKind: 'periodic', runAt, intervalSeconds: 60, enqueuedBy: 'owner',
  });

  // Fire B once: its row is UPDATED (not deleted) and an execution is recorded.
  // This is what makes B a live recurring schedule with audit history.
  const execB = store.fireQueueRow({ queueId: rowB.queue_id, now, tick: 1 });
  const rowBAfterFire = store.getQueueRow(rowB.queue_id);
  check('setup: repeating row SURVIVES its fire (run_at advanced)',
    rowBAfterFire !== null && rowBAfterFire.run_at > runAt,
    `run_at ${runAt} -> ${rowBAfterFire && rowBAfterFire.run_at}`);
  check('setup: the fire recorded an execution',
    execB !== null && Number.isInteger(execB.exec_id),
    `exec_id=${execB && execB.exec_id}`);

  // --- 1. A pending row is removed; read back from disk -> GONE.
  const removedA = store.removeQueueRow({ queueId: rowA.queue_id });
  check('remove returns the REMOVED ROW, identified (not a bare boolean)',
    removedA !== null && removedA.queue_id === rowA.queue_id && removedA.job_id === 'launch-worker',
    `queue_id=${removedA && removedA.queue_id} job_id=${removedA && removedA.job_id}`);

  let ids = readBackQueueIds();
  check('one-shot row is GONE on disk (identity, not a count)',
    !ids.some((r) => r.queue_id === rowA.queue_id),
    `disk queue_ids=[${ids.map((r) => r.queue_id).join(',')}]`);
  check('the SIBLING row is untouched (removal is targeted)',
    ids.some((r) => r.queue_id === rowB.queue_id),
    `rowB queue_id=${rowB.queue_id} still present`);

  // --- 2. Removing a REPEATING row cancels the WHOLE schedule (the design point).
  const removedB = store.removeQueueRow({ queueId: rowB.queue_id });
  check('removing a repeating trigger returns its recurrence fields (lets the caller be LOUD)',
    removedB !== null && removedB.trigger_kind === 'periodic' && removedB.interval_seconds === 60,
    `trigger_kind=${removedB && removedB.trigger_kind} interval_seconds=${removedB && removedB.interval_seconds}`);

  ids = readBackQueueIds();
  check('repeating row is GONE on disk — the recurring schedule is cancelled',
    !ids.some((r) => r.queue_id === rowB.queue_id),
    `disk queue_ids=[${ids.map((r) => r.queue_id).join(',')}]`);

  // The audit survives its queue row's deletion — removal cancels FUTURE fires
  // and NEVER touches a recorded/running execution.
  const execs = readBackExecIds();
  check("the fired execution's audit row SURVIVES its queue row's removal",
    execs.some((e) => e.exec_id === execB.exec_id && e.queue_id === rowB.queue_id),
    `jobs_log exec_ids=[${execs.map((e) => e.exec_id).join(',')}]`);

  // --- 3. An unknown id -> TYPED not-found, never a silent success.
  let caught = null;
  try {
    store.removeQueueRow({ queueId: 999999 });
  } catch (err) {
    caught = err;
  }
  check('unknown id throws (never a silent no-op)', caught !== null,
    caught ? 'threw' : 'RETURNED SILENTLY');
  check('unknown id is TYPED E_QUEUE_ROW_NOT_FOUND',
    caught !== null && caught.code === E_QUEUE_ROW_NOT_FOUND,
    `code=${caught && caught.code}`);
  check('the typed error carries the offending id in details',
    caught !== null && caught.details && caught.details.queueId === 999999,
    `details=${caught && JSON.stringify(caught.details)}`);

  // A non-integer id is a bad argument, distinct from a missing row.
  let badArg = null;
  try {
    store.removeQueueRow({ queueId: 'not-an-integer' });
  } catch (err) {
    badArg = err;
  }
  check('a non-integer id is E_BAD_ARGS (distinct from not-found)',
    badArg !== null && badArg.code === E_BAD_ARGS,
    `code=${badArg && badArg.code}`);

  // --- 4. The failed removals wrote NOTHING.
  const idsFinal = readBackQueueIds();
  check('a failed removal leaves the queue exactly as it was',
    idsFinal.length === 0,
    `disk queue rows=${idsFinal.length}`);

  closeHeartStore();

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`REMOVE_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
} catch (err) {
  out('ERROR:', err.message, err.stack);
  out(`EXIT: 1`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
} finally {
  try { closeHeartStore(); } catch {}
  try { fs.unlinkSync(tmpDb); } catch {}
  try { fs.unlinkSync(tmpDb + '-wal'); } catch {}
  try { fs.unlinkSync(tmpDb + '-shm'); } catch {}
}
