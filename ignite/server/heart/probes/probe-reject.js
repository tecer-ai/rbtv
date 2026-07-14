'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore, E_UNKNOWN_PROFILE } = require('../heart-store');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-reject.out');
const tmpDb = path.join(os.tmpdir(), `heart-probe-reject-${Date.now()}-${process.pid}.db`);

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

try {
  fs.writeFileSync(outPath, '');

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

  let caught = null;
  try {
    store.enqueue({
      jobId: 'launch-worker',
      args: JSON.stringify({ profile: 'nonexistent-profile' }),
      sessionMode: 'headless',
      triggerKind: 'scheduled',
      runAt,
      enqueuedBy: 'owner',
    });
  } catch (err) {
    caught = err;
  }

  const queueRows = store.listQueue();
  closeHeartStore();

  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out(`ERROR_CODE: ${caught ? caught.code : 'NONE'}`);
  out(`ERROR_MESSAGE: ${caught ? caught.message : 'no error thrown'}`);
  out(`EXPECTED_CODE: ${E_UNKNOWN_PROFILE}`);
  out(`QUEUE_ROWS_AFTER: ${queueRows.length}`);
  out(`REJECT_OK: ${caught && caught.code === E_UNKNOWN_PROFILE && queueRows.length === 0}`);
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
