'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore } = require('../heart-store');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-session-row.out');
const tmpDb = path.join(os.tmpdir(), `heart-probe-session-row-${Date.now()}-${process.pid}.db`);

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

function dumpRow(label, row) {
  out(label);
  out(`  profile=${row.profile}`);
  out(`  carrier=${row.carrier}`);
  out(`  unit_name=${row.unit_name}`);
  out(`  pid_starttime=${row.pid_starttime}`);
  out(`  session_ref=${row.session_ref}`);
  out(`  workdir=${row.workdir}`);
  out(`  started_at=${row.started_at}`);
}

function eq(a, b) {
  return a === b;
}

let store;

try {
  fs.writeFileSync(outPath, '');

  store = openHeartStore({
    dbPath: tmpDb,
    profiles: { default: { headed: false } },
  });

  store.registerJob({
    jobId: 'launch-agent',
    actionType: 'launch-agent',
    function: 'spawnLaunchAgent',
    argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: {} }),
    enabled: 1,
  });

  // 1. Fire-time insert: profile + workdir must land.
  const rowStart = store.recordExecutionStart({
    jobId: 'launch-agent',
    actionType: 'launch-agent',
    args: JSON.stringify({ profile: 'default' }),
    enqueuedBy: 'owner',
    sessionMode: 'headless',
    firedTick: 1,
    firedAt: new Date(),
    parentExecId: null,
    profile: 'default',
    workdir: '/tmp/session-workdir',
  });

  const execId = rowStart.exec_id;
  dumpRow('AFTER recordExecutionStart', rowStart);

  const startProfileOk = eq(rowStart.profile, 'default');
  const startWorkdirOk = eq(rowStart.workdir, '/tmp/session-workdir');

  // 2. Post-spawn update: carrier/unit_name/pid_starttime/session_ref/started_at must land.
  const startedAt = new Date('2026-07-14T12:00:00.000Z');
  const rowRunning = store.updateExecutionStatus(execId, {
    status: 'running',
    carrier: 'systemd',
    unitName: 'rbtv-worker-abc123',
    pidStarttime: 1234567890,
    sessionRef: 'session-abc123',
    startedAt,
  });

  dumpRow('AFTER updateExecutionStatus (running)', rowRunning);

  const runningCarrierOk = eq(rowRunning.carrier, 'systemd');
  const runningUnitNameOk = eq(rowRunning.unit_name, 'rbtv-worker-abc123');
  const runningPidStarttimeOk = eq(rowRunning.pid_starttime, 1234567890);
  const runningSessionRefOk = eq(rowRunning.session_ref, 'session-abc123');
  const runningStartedAtOk = eq(rowRunning.started_at, '2026-07-14T12:00:00Z');
  const runningProfileOk = eq(rowRunning.profile, 'default');
  const runningWorkdirOk = eq(rowRunning.workdir, '/tmp/session-workdir');

  // 3. Second update that OMITS the five session columns → must preserve them (COALESCE proof).
  const endedAt = new Date('2026-07-14T12:05:00.000Z');
  const rowDone = store.updateExecutionStatus(execId, {
    status: 'done',
    endedAt,
  });

  dumpRow('AFTER updateExecutionStatus (done, omitted)', rowDone);

  const doneCarrierOk = eq(rowDone.carrier, 'systemd');
  const doneUnitNameOk = eq(rowDone.unit_name, 'rbtv-worker-abc123');
  const donePidStarttimeOk = eq(rowDone.pid_starttime, 1234567890);
  const doneSessionRefOk = eq(rowDone.session_ref, 'session-abc123');
  const doneStartedAtOk = eq(rowDone.started_at, '2026-07-14T12:00:00Z');
  const doneProfileOk = eq(rowDone.profile, 'default');
  const doneWorkdirOk = eq(rowDone.workdir, '/tmp/session-workdir');
  const doneEndedAtOk = eq(rowDone.ended_at, '2026-07-14T12:05:00Z');

  // 4. Close and reopen → round-trip all seven columns from disk.
  closeHeartStore();
  const store2 = openHeartStore({ dbPath: tmpDb });
  const rowReopen = store2.getExecution(execId);
  dumpRow('AFTER close + reopen', rowReopen);

  const reopenProfileOk = eq(rowReopen.profile, 'default');
  const reopenWorkdirOk = eq(rowReopen.workdir, '/tmp/session-workdir');
  const reopenCarrierOk = eq(rowReopen.carrier, 'systemd');
  const reopenUnitNameOk = eq(rowReopen.unit_name, 'rbtv-worker-abc123');
  const reopenPidStarttimeOk = eq(rowReopen.pid_starttime, 1234567890);
  const reopenSessionRefOk = eq(rowReopen.session_ref, 'session-abc123');
  const reopenStartedAtOk = eq(rowReopen.started_at, '2026-07-14T12:00:00Z');

  closeHeartStore();

  const allOk =
    startProfileOk && startWorkdirOk &&
    runningCarrierOk && runningUnitNameOk && runningPidStarttimeOk && runningSessionRefOk && runningStartedAtOk && runningProfileOk && runningWorkdirOk &&
    doneCarrierOk && doneUnitNameOk && donePidStarttimeOk && doneSessionRefOk && doneStartedAtOk && doneProfileOk && doneWorkdirOk && doneEndedAtOk &&
    reopenProfileOk && reopenWorkdirOk && reopenCarrierOk && reopenUnitNameOk && reopenPidStarttimeOk && reopenSessionRefOk && reopenStartedAtOk;

  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out(`START_PROFILE_OK: ${startProfileOk}`);
  out(`START_WORKDIR_OK: ${startWorkdirOk}`);
  out(`RUNNING_CARRIER_OK: ${runningCarrierOk}`);
  out(`RUNNING_UNIT_NAME_OK: ${runningUnitNameOk}`);
  out(`RUNNING_PID_STARTTIME_OK: ${runningPidStarttimeOk}`);
  out(`RUNNING_SESSION_REF_OK: ${runningSessionRefOk}`);
  out(`RUNNING_STARTED_AT_OK: ${runningStartedAtOk}`);
  out(`RUNNING_PROFILE_PRESERVED_OK: ${runningProfileOk}`);
  out(`RUNNING_WORKDIR_PRESERVED_OK: ${runningWorkdirOk}`);
  out(`DONE_CARRIER_PRESERVED_OK: ${doneCarrierOk}`);
  out(`DONE_UNIT_NAME_PRESERVED_OK: ${doneUnitNameOk}`);
  out(`DONE_PID_STARTTIME_PRESERVED_OK: ${donePidStarttimeOk}`);
  out(`DONE_SESSION_REF_PRESERVED_OK: ${doneSessionRefOk}`);
  out(`DONE_STARTED_AT_PRESERVED_OK: ${doneStartedAtOk}`);
  out(`DONE_PROFILE_PRESERVED_OK: ${doneProfileOk}`);
  out(`DONE_WORKDIR_PRESERVED_OK: ${doneWorkdirOk}`);
  out(`DONE_ENDED_AT_OK: ${doneEndedAtOk}`);
  out(`REOPEN_PROFILE_OK: ${reopenProfileOk}`);
  out(`REOPEN_WORKDIR_OK: ${reopenWorkdirOk}`);
  out(`REOPEN_CARRIER_OK: ${reopenCarrierOk}`);
  out(`REOPEN_UNIT_NAME_OK: ${reopenUnitNameOk}`);
  out(`REOPEN_PID_STARTTIME_OK: ${reopenPidStarttimeOk}`);
  out(`REOPEN_SESSION_REF_OK: ${reopenSessionRefOk}`);
  out(`REOPEN_STARTED_AT_OK: ${reopenStartedAtOk}`);
  out(`ALL_OK: ${allOk}`);
  out(`EXIT: ${allOk ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = allOk ? 0 : 1;
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
