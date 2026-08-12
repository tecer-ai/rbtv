'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore, E_UNKNOWN_TOOL } = require('../heart-store');

// ⚠ THE SUBJECT MOVED FROM `launch-agent` TO `fire-tool` AT 7.787, AND THE CLAIM IS UNCHANGED.
// This probe is the ONE witness at the store door itself that an enqueue naming something the
// catalogue does not carry is REFUSED and writes NOTHING. It used to plant an unknown launch
// PROFILE — the argument `#d-abolish-profile-names` deletes: a `launch-agent` row now names no
// spec at all, so there is nothing at that door left to be unknown (what replaced it is the
// seat's own cast, refused at SPAWN with `E_UNCAST_SEAT`/`E_UNMAPPED_BINDING`, which
// `probe-binding-catalog` owns). `fire-tool`'s `tool` is the same guard on the same line of code
// — `Object.hasOwn(this.config.<catalogue>, …)` — so the door keeps its witness.

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
    tools: { 'known-tool': { exec: { argv: ['true'] } } },
  });
  store.registerJob({
    jobId: 'fire-known',
    actionType: 'fire-tool',
    function: 'fireTool',
    argsSchema: JSON.stringify({ required: { tool: 'string' }, optional: {} }),
    enabled: 1,
  });

  const now = new Date();
  const runAt = now.toISOString().replace(/\.\d{3}Z$/, 'Z');

  let caught = null;
  try {
    store.enqueue({
      jobId: 'fire-known',
      args: JSON.stringify({ tool: 'no-such-tool' }),
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

  const rejectOk = Boolean(caught) && caught.code === E_UNKNOWN_TOOL && queueRows.length === 0;

  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out(`ERROR_CODE: ${caught ? caught.code : 'NONE'}`);
  out(`ERROR_MESSAGE: ${caught ? caught.message : 'no error thrown'}`);
  out(`EXPECTED_CODE: ${E_UNKNOWN_TOOL}`);
  out(`QUEUE_ROWS_AFTER: ${queueRows.length}`);
  out(`REJECT_OK: ${rejectOk}`);

  // ASSERT it, never merely record it: REJECT_OK was printed behind an unconditional exitCode 0,
  // so the probe could not fail. The same guard is exercised through the wire by probe-revalidate
  // and probe-dryrun; this is the only witness at the store door itself.
  if (!rejectOk) {
    throw new Error(`REJECT_OK false — expected ${E_UNKNOWN_TOOL} and 0 queue rows, got ${caught ? caught.code : 'NO THROW'} and ${queueRows.length} row(s)`);
  }

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
