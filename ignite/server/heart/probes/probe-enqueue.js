'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore } = require('../heart-store');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-enqueue.out');
const tmpDb = path.join(os.tmpdir(), `heart-probe-enqueue-${Date.now()}-${process.pid}.db`);

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

function dump(label, store) {
  out(label);
  const data = store.dump();
  out('jobs:', JSON.stringify(data.jobs));
  out('queue:', JSON.stringify(data.queue));
  out('jobs_log:', JSON.stringify(data.jobs_log));
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
  const row = store.enqueue({
    jobId: 'launch-worker',
    args: JSON.stringify({ profile: 'default' }),
    sessionMode: 'headless',
    triggerKind: 'scheduled',
    runAt,
    enqueuedBy: 'owner',
  });

  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  dump('=== BEFORE CLOSE ===', store);

  const queueIdBefore = row.queue_id;
  closeHeartStore();

  const store2 = openHeartStore({ dbPath: tmpDb });
  const after = store2.getQueueRow(queueIdBefore);
  dump('=== AFTER REOPEN ===', store2);
  closeHeartStore();

  const ok = after !== null && after.job_id === 'launch-worker';
  out(`PERSISTENCE_OK: ${ok}`);
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
