'use strict';

// Task 7.7 (owner ruling 2026-07-23; heart-store-spec § Single-writer): a completion is
// messages INSERT + jobs_log UPDATE (status, completion_msg_id, ended_at) in ONE transaction.
// The former shape was TWO transactions (recordMessage, then Advance's resolveCompletion) with
// a crash window that left a finished job's completion message on disk while jobs_log still
// said `running`. This probe proves the single-transaction boundary is LOAD-BEARING:
//   (1) ATOMIC-VISIBLE — after recordMessage(completion) returns, the message AND the jobs_log
//       stamp are both visible; routed_at_tick is still NULL (the ROUTING stamp stays a
//       ticker-side Advance update — D30 deferred routing unchanged).
//   (2) EXECID-PIN — a caller that knows its execution (the ticker's sweeps) pins it with
//       execId and the stamp lands on exactly that row, exit_code included.
//   (3) MUTATION both-or-neither — a fault injected BETWEEN the two logical steps (the message
//       INSERT and the jobs_log UPDATE, inside the store's transaction) yields NEITHER write:
//       the INSERT is rolled back. The old half-recorded state (message without stamp) is
//       structurally unreachable. After the fault clears, the same call lands BOTH writes.
//   (4) UNKNOWN-THREAD — a completion on a thread with no execution inserts the message alone
//       (Advance's anomaly path still owns routing it); no jobs_log row is invented.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore } = require('../heart-store');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-completion-atomic.out');
const tmpDb = path.join(os.tmpdir(), `heart-probe-completion-atomic-${Date.now()}-${process.pid}.db`);

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

function messageCount(store) {
  return store.db.prepare('SELECT COUNT(*) AS n FROM messages').get().n;
}

try {
  fs.writeFileSync(outPath, '');
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const store = openHeartStore({ dbPath: tmpDb });

  // (1) ATOMIC-VISIBLE — thread-resolved completion on a running execution.
  const exec1 = store.recordExecutionStart({
    jobId: 'launch-worker', actionType: 'launch-agent', args: '{}', enqueuedBy: 'probe',
    sessionMode: 'headless', firedTick: 1, firedAt: new Date(), parentExecId: null,
  });
  store.updateExecutionStatus(exec1.exec_id, { status: 'running' });
  const msg1 = store.recordMessage({
    type: 'completion', sender: 'agent', thread: exec1.thread,
    corpus: 'done by report', status: 'done', createdAt: new Date(),
  });
  const exec1After = store.getExecution(exec1.exec_id);
  const case1Ok = exec1After.status === 'done'
    && exec1After.completion_msg_id === msg1.msg_id
    && exec1After.ended_at !== null
    && msg1.routed_at_tick === null;
  out(`CASE1_ATOMIC_VISIBLE (status=done, completion_msg_id=msg, ended_at set, routed_at_tick NULL): ${case1Ok}`);
  if (!case1Ok) throw new Error(`case 1 failed: ${JSON.stringify({ exec: exec1After, msg: msg1 })}`);

  // (2) EXECID-PIN — the sweep shape: execId + exitCode.
  const exec2 = store.recordExecutionStart({
    jobId: 'launch-worker', actionType: 'launch-agent', args: '{}', enqueuedBy: 'probe',
    sessionMode: 'headless', firedTick: 2, firedAt: new Date(), parentExecId: null,
  });
  store.updateExecutionStatus(exec2.exec_id, { status: 'running' });
  const msg2 = store.recordMessage({
    type: 'completion', sender: 'ticker', thread: exec2.thread,
    corpus: 'crash sweep: exit=7', status: 'failed', createdAt: new Date(),
    execId: exec2.exec_id, exitCode: 7,
  });
  const exec2After = store.getExecution(exec2.exec_id);
  const case2Ok = exec2After.status === 'failed'
    && exec2After.completion_msg_id === msg2.msg_id
    && exec2After.exit_code === 7;
  out(`CASE2_EXECID_PIN (status=failed, completion_msg_id=msg, exit_code=7): ${case2Ok}`);
  if (!case2Ok) throw new Error(`case 2 failed: ${JSON.stringify(exec2After)}`);

  // (3) MUTATION — fault injected between the INSERT and the jobs_log UPDATE.
  const exec3 = store.recordExecutionStart({
    jobId: 'launch-worker', actionType: 'launch-agent', args: '{}', enqueuedBy: 'probe',
    sessionMode: 'headless', firedTick: 3, firedAt: new Date(), parentExecId: null,
  });
  store.updateExecutionStatus(exec3.exec_id, { status: 'running' });
  const countBefore = messageCount(store);
  const savedPrepare = store._prepare;
  store._prepare = function patchedPrepare(sql) {
    if (/UPDATE jobs_log SET status = \?, completion_msg_id/.test(sql)) {
      throw new Error('injected fault between the completion INSERT and the jobs_log UPDATE');
    }
    return savedPrepare.call(this, sql);
  };
  let faultThrown = false;
  try {
    store.recordMessage({
      type: 'completion', sender: 'agent', thread: exec3.thread,
      corpus: 'will not land', status: 'done', createdAt: new Date(),
    });
  } catch (err) {
    faultThrown = true;
    out(`CASE3_FAULT_RAISED: ${err.message}`);
  }
  delete store._prepare; // restore the prototype method
  const countAfterFault = messageCount(store);
  const exec3AfterFault = store.getExecution(exec3.exec_id);
  const neitherLanded = faultThrown
    && countAfterFault === countBefore
    && exec3AfterFault.status === 'running'
    && exec3AfterFault.completion_msg_id === null;
  out(`CASE3_NEITHER_LANDED (message rolled back, exec untouched): ${neitherLanded}`);
  if (!neitherLanded) {
    throw new Error(`case 3 failed — a half-recorded completion is possible: ` +
      JSON.stringify({ faultThrown, countBefore, countAfterFault, exec: exec3AfterFault }));
  }
  // Fault cleared: the same call lands BOTH writes.
  const msg3 = store.recordMessage({
    type: 'completion', sender: 'agent', thread: exec3.thread,
    corpus: 'lands now', status: 'done', createdAt: new Date(),
  });
  const exec3After = store.getExecution(exec3.exec_id);
  const bothLanded = messageCount(store) === countBefore + 1
    && exec3After.status === 'done'
    && exec3After.completion_msg_id === msg3.msg_id;
  out(`CASE3_BOTH_LANDED_AFTER_CLEAR: ${bothLanded}`);
  if (!bothLanded) throw new Error(`case 3 post-clear failed: ${JSON.stringify(exec3After)}`);

  // (4) UNKNOWN-THREAD — message alone; nothing stamped.
  const countBefore4 = messageCount(store);
  const msg4 = store.recordMessage({
    type: 'completion', sender: 'agent', thread: 'exec-99999',
    corpus: 'orphan report', status: 'done', createdAt: new Date(),
  });
  const case4Ok = messageCount(store) === countBefore4 + 1 && msg4.routed_at_tick === null;
  out(`CASE4_UNKNOWN_THREAD (message inserted alone, unrouted for Advance's anomaly path): ${case4Ok}`);
  if (!case4Ok) throw new Error('case 4 failed');

  closeHeartStore();
  out('EXIT: 0');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 0;
} catch (err) {
  out('ERROR:', err.message, err.stack);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
} finally {
  try { closeHeartStore(); } catch { /* already closed */ }
  try { fs.unlinkSync(tmpDb); } catch { /* fine */ }
  try { fs.unlinkSync(tmpDb + '-wal'); } catch { /* fine */ }
  try { fs.unlinkSync(tmpDb + '-shm'); } catch { /* fine */ }
}
