'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { openHeartStore, closeHeartStore, E_SECOND_WRITER } = require('../heart-store');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-single-writer.out');
const tmpDb = path.join(os.tmpdir(), `heart-probe-single-writer-${Date.now()}-${process.pid}.db`);
const brokenDb = tmpDb.replace(/\.db$/, '-broken.db');
const recoverDb = tmpDb.replace(/\.db$/, '-recover.db');
const contendDb = tmpDb.replace(/\.db$/, '-contend.db');
const marker = contendDb + '.locked';
const childScript = path.join(__dirname, '_busy-child.js');
const lockScript = path.join(__dirname, '_lock-holder.js');
const HOLD_MS = 1200;

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

// How many of THIS process's fds point at `p`. Linux-only, which is what the daemon runs on.
function fdsFor(p) {
  return fs.readdirSync('/proc/self/fd').filter((fd) => {
    try { return fs.readlinkSync(`/proc/self/fd/${fd}`) === p; } catch { return false; }
  }).length;
}

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
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

  // (c) A constructor that THROWS must leave the writer slot unclaimed. The throw is forced after
  // `new DatabaseSync` succeeds by planting a DIRECTORY where the WAL file must go, so the
  // `PRAGMA journal_mode = WAL` inside the constructor fails with a disk I/O error — the same shape
  // as the live `database is locked` failure of 2026-08-14. If the slot is claimed before that
  // point, the next openHeartStore below dies with E_SECOND_WRITER instead of succeeding.
  new (require('node:sqlite').DatabaseSync)(brokenDb).close();
  fs.mkdirSync(brokenDb + '-wal');
  let ctorThrew = null;
  try {
    openHeartStore({ dbPath: brokenDb });
  } catch (err) {
    ctorThrew = err;
  }
  // (c2) …and must leave no open DatabaseSync handle either. Same forced throw, one extra
  // observation: the handle opened before it must not still be in /proc/self/fd.
  const leakedFds = fdsFor(brokenDb);
  let reopenErr = null;
  try {
    openHeartStore({ dbPath: recoverDb }).close();
  } catch (err) {
    reopenErr = err;
  }
  const slotReleased = ctorThrew !== null && reopenErr === null;
  const handleClosed = ctorThrew !== null && leakedFds === 0;

  // (d) R3(b): `busy_timeout` is set BEFORE WAL/schema/migrate, so an open that meets a concurrent
  // writer WAITS for it instead of throwing `database is locked` on the spot. A child holds a write
  // lock for HOLD_MS; the open below must survive it and must have taken roughly that long. Move
  // the pragma back after the sequence and this arm goes red on the throw.
  const holder = spawn(process.execPath, [lockScript, contendDb, String(HOLD_MS), marker],
    { stdio: 'ignore' });
  const waitStart = Date.now();
  while (!fs.existsSync(marker) && Date.now() - waitStart < 10000) sleep(25);
  const lockHeld = fs.existsSync(marker);
  const openStart = Date.now();
  let contendErr = null;
  try {
    openHeartStore({ dbPath: contendDb }).close();
  } catch (err) {
    contendErr = err;
  }
  const contendMs = Date.now() - openStart;
  holder.kill();
  // Waited for the lock rather than sailing past it: no throw AND it actually blocked.
  const contendWaited = lockHeld && contendErr === null && contendMs >= HOLD_MS / 2;

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
  out(`CTOR_THREW: ${ctorThrew ? ctorThrew.message : 'NONE'}`);
  out(`SLOT_RELEASED_ON_THROW: ${slotReleased}`);
  out(`REOPEN_ERROR: ${reopenErr ? `${reopenErr.code || ''} ${reopenErr.message}` : 'NONE'}`);
  out(`HANDLE_CLOSED_ON_THROW: ${handleClosed}`);
  out(`LEAKED_FDS: ${leakedFds}`);
  out(`LOCK_HELD: ${lockHeld}`);
  out(`CONTENDED_OPEN_WAITED: ${contendWaited}`);
  out(`CONTENDED_OPEN_ERROR: ${contendErr ? `${contendErr.code || ''} ${contendErr.message}` : 'NONE'}`);

  // ASSERT the invariant, never merely record it: both arms below were computed, printed and
  // thrown away behind an unconditional exitCode 0, so the probe could not fail. No other probe
  // exercises E_SECOND_WRITER or SQLITE_BUSY — this is the single-writer guard's only witness.
  if (!secondWriterOk || !busyCaught || !noDoubleWrite || !slotReleased || !handleClosed || !contendWaited) {
    throw new Error(`single-writer invariant broken — SECOND_WRITER_CAUGHT=${secondWriterOk} (code ${secondWriterCaught ? secondWriterCaught.code : 'NONE'}, expected ${E_SECOND_WRITER}) BUSY_CAUGHT=${busyCaught} (child said '${childOutput}') NO_DOUBLE_WRITE=${noDoubleWrite} (rows ${rowsAfter}) SLOT_RELEASED_ON_THROW=${slotReleased} (ctor threw: ${ctorThrew ? ctorThrew.message : 'NOTHING — arm is vacuous'}, reopen: ${reopenErr ? `${reopenErr.code || ''} ${reopenErr.message}` : 'ok'}) HANDLE_CLOSED_ON_THROW=${handleClosed} (${leakedFds} fd(s) still open on the failed db) CONTENDED_OPEN_WAITED=${contendWaited} (lock held: ${lockHeld}, took ${contendMs}ms of ${HOLD_MS}, error: ${contendErr ? `${contendErr.code || ''} ${contendErr.message}` : 'none'})`);
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
  try { fs.rmSync(marker, { force: true }); } catch {}
  for (const p of [brokenDb, recoverDb, contendDb]) {
    for (const suffix of ['', '-wal', '-shm']) {
      try { fs.rmSync(p + suffix, { recursive: true, force: true }); } catch {}
    }
  }
}
