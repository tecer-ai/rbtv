'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore } = require('../heart-store');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-jobslog.out');
const tmpDb = path.join(os.tmpdir(), `heart-probe-jobslog-${Date.now()}-${process.pid}.db`);

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

try {
  fs.writeFileSync(outPath, '');

  const store = openHeartStore({ dbPath: tmpDb });

  // Row 1: chain start.
  const row1 = store.recordExecutionStart({
    jobId: 'launch-worker',
    actionType: 'launch-agent',
    args: '{}',
    enqueuedBy: 'owner',
    sessionMode: 'headless',
    firedTick: 1,
    firedAt: new Date(),
    parentExecId: null,
  });

  // Row 2: re-dispatched turn in the same chain.
  const row2 = store.recordExecutionStart({
    jobId: 'launch-worker',
    actionType: 'launch-agent',
    args: '{}',
    enqueuedBy: 'owner',
    sessionMode: 'headless',
    firedTick: 2,
    firedAt: new Date(),
    parentExecId: row1.exec_id,
  });

  // Row 3: grandchild — a deeper turn in the same chain — proves the thread is
  // DERIVED (recursively, via parent_exec_id) not stored, and stays chain-stable.
  const row3 = store.recordExecutionStart({
    jobId: 'launch-worker',
    actionType: 'launch-agent',
    args: '{}',
    enqueuedBy: 'owner',
    sessionMode: 'headless',
    firedTick: 3,
    firedAt: new Date(),
    parentExecId: row2.exec_id,
  });

  // Prove the revert: jobs_log carries NO stored `thread` column (derived only).
  const cols = store.db.prepare("PRAGMA table_info('jobs_log')").all().map((c) => c.name);
  const threadColumnPresent = cols.includes('thread');

  // Dangling parent via direct SQL to exercise the FK (foreign_keys ON).
  let fkError = null;
  try {
    store.db.prepare(`
      INSERT INTO jobs_log (parent_exec_id, queue_id, job_id, action_type, args, enqueued_by, session_mode, fired_tick, fired_at, status)
      VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, 'launching')
    `).run(99999, 'launch-worker', 'launch-agent', '{}', 'owner', 'headless', 4, new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'));
  } catch (err) {
    fkError = err;
  }

  closeHeartStore();

  const threadMatches = row2.thread === row1.thread && row3.thread === row1.thread;
  const parentMatches = row2.parent_exec_id === row1.exec_id && row3.parent_exec_id === row2.exec_id;
  const danglingRejected = fkError && (fkError.message.includes('FOREIGN KEY') || fkError.message.includes('constraint failed') || fkError.code === 'ERR_SQLITE_CONSTRAINT');

  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out(`ROW1_EXEC_ID: ${row1.exec_id}`);
  out(`ROW1_THREAD: ${row1.thread}`);
  out(`ROW2_EXEC_ID: ${row2.exec_id}`);
  out(`ROW2_PARENT_EXEC_ID: ${row2.parent_exec_id}`);
  out(`ROW2_THREAD: ${row2.thread}`);
  out(`ROW3_EXEC_ID: ${row3.exec_id}`);
  out(`ROW3_PARENT_EXEC_ID: ${row3.parent_exec_id}`);
  out(`ROW3_THREAD (grandchild, derived): ${row3.thread}`);
  out(`THREAD_COLUMN_PRESENT (must be false — derived not stored): ${threadColumnPresent}`);
  out(`THREAD_DERIVED_STABLE: ${threadMatches}`);
  out(`PARENT_LINKED: ${parentMatches}`);
  out(`DANGLING_REJECTED: ${danglingRejected}`);
  out(`DANGLING_ERROR: ${fkError ? fkError.message : 'none'}`);
  out(`EXIT: 0`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 0;
} catch (err) {
  out('ERROR:', err.message, err.stack);
  out(`EXIT: 1`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
} finally {
  try { fs.unlinkSync(tmpDb); } catch {}
  try { fs.unlinkSync(tmpDb + '-wal'); } catch {}
  try { fs.unlinkSync(tmpDb + '-shm'); } catch {}
}
