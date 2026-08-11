'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { openHeartStore, closeHeartStore, E_SECOND_WRITER } = require('../heart-store');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-single-writer.out');
const tmpDb = path.join(os.tmpdir(), `heart-probe-single-writer-${Date.now()}-${process.pid}.db`);
const childScript = path.join(__dirname, '_busy-child.js');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

try {
  fs.writeFileSync(outPath, '');

  const store = openHeartStore({ dbPath: tmpDb });

  // (a) Second in-process writer attempt must throw E_SECOND_WRITER.
  let secondWriterCaught = null;
  try {
    openHeartStore({ dbPath: tmpDb });
  } catch (err) {
    secondWriterCaught = err;
  }

  // (b) Out-of-process write during an open write transaction must get SQLITE_BUSY.
  store.db.exec('CREATE TABLE IF NOT EXISTS probe_w (id INTEGER PRIMARY KEY, payload TEXT)');
  store.db.exec('BEGIN EXCLUSIVE;');
  store.db.prepare('INSERT INTO probe_w (payload) VALUES (?)').run('parent');

  const child = spawnSync(process.execPath, [childScript, tmpDb], { encoding: 'utf8' });
  const childOutput = child.stdout.trim();
  store.db.exec('ROLLBACK;');

  // Confirm no child row was written.
  const rowsAfter = store.db.prepare('SELECT COUNT(*) AS n FROM probe_w').get().n;
  closeHeartStore();

  const busyCaught = childOutput.startsWith('BUSY:') && childOutput.includes('database is locked');
  const noDoubleWrite = rowsAfter === 0;
  const secondWriterOk = Boolean(secondWriterCaught && secondWriterCaught.code === E_SECOND_WRITER);

  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out(`SECOND_WRITER_CAUGHT: ${secondWriterOk}`);
  out(`SECOND_WRITER_CODE: ${secondWriterCaught ? secondWriterCaught.code : 'NONE'}`);
  out(`BUSY_CAUGHT: ${busyCaught}`);
  out(`CHILD_OUTPUT: ${childOutput}`);
  out(`NO_DOUBLE_WRITE: ${noDoubleWrite}`);
  out(`ROWS_AFTER: ${rowsAfter}`);

  // ASSERT the invariant, never merely record it: both arms below were computed, printed and
  // thrown away behind an unconditional exitCode 0, so the probe could not fail. No other probe
  // exercises E_SECOND_WRITER or SQLITE_BUSY — this is the single-writer guard's only witness.
  if (!secondWriterOk || !busyCaught || !noDoubleWrite) {
    throw new Error(`single-writer invariant broken — SECOND_WRITER_CAUGHT=${secondWriterOk} (code ${secondWriterCaught ? secondWriterCaught.code : 'NONE'}, expected ${E_SECOND_WRITER}) BUSY_CAUGHT=${busyCaught} (child said '${childOutput}') NO_DOUBLE_WRITE=${noDoubleWrite} (rows ${rowsAfter})`);
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
