'use strict';

// -- THE SUPERVISED-SITTING REGISTRY - the ONE liveness surface [T4-R8, T4-R7, C-15] ------------
//
// WHAT WAS BROKEN. "Is this seat alive?" was answered by three disjoint predicates (a tmux pane, a
// cgroup carrier, tick silence) and by NO persisted record of what the daemon had actually spawned.
// A watchdog restart therefore booted with an EMPTY in-memory view of the world, and absence read
// as death: every live seat was eligible to be stamped `failed` at once (C-15 / F-adversarial-7).
//
// THE CURE, and it is two halves that only work together. (1) The set of supervised sittings is
// PERSISTED - a durable JSONL file, one live row per sitting, written at the four moments below and
// at no other. (2) On boot, `readopt.js` matches every persisted row against the live process table
// BEFORE any outcome stamp runs. A row that still matches is re-adopted, not stamped; a row that
// does not is classified dead and handed to the death-stamp path; and - the hole this whole module
// exists to close - a live OS process with NO row is NOT dead, and an empty file is a legal fresh
// boot, never a mass death.
//
// WHAT THIS FILE IS NOT. Not `jobs_log.status` (history [T4-R8]), not the ending store (endings are
// spec-state-store's record, written elsewhere), not an in-memory Map. It holds NO outcome: nothing
// here stamps anything. Liveness is a fact about a process; an ending is a fact about a sitting.
//
// THE PROBE IS SPELLED HERE, and that is deliberate. `engine/attached-execution.js` carries the
// same `kill(pid, 0)` + start-time comparison today (`runnerAlive` / `processStartTime`) - it is the
// LEGACY copy, reached by the attached-operator lane, and the doors seat retires it into this one.
// Depending on it from here would point the dependency the wrong way: the operator lane is a
// CONSUMER of liveness, and supervisor is where liveness is answered.

const fs = require('node:fs');
const path = require('node:path');

// The spec pins the file name and the JSONL shape; `spec-component-map` homes the folder here
// (`ignite/supervisor/`, replacing the spec's interim `ignite/engine/supervisor/`). The path is a
// DEFAULT, not a constant a caller cannot escape: a probe, a selftest and a second instance each
// need their own file, and a module that can only write one absolute path cannot be tested at all.
const REGISTRY_FILENAME = 'registry.jsonl';
const DEFAULT_REGISTRY_PATH = path.join(__dirname, REGISTRY_FILENAME);

const SUPERVISED = 'supervised';
const UNSUPERVISED = 'unsupervised';

function registryPath(override) {
  return path.resolve(override || DEFAULT_REGISTRY_PATH);
}

// -- /proc/<pid>/stat FIELD 22 - the process start time, in clock ticks since boot --------------
//
// Read from AFTER the comm field's closing paren: comm can contain spaces AND parens, so splitting
// the whole line is the classic wrong answer. Index 0 of what `procStatFields` returns is field 3,
// so field 22 is index 19. Paired with the pid this is the only cheap identity that SURVIVES pid
// recycling - a pid alone says nothing, because the kernel hands it back out.
function procStatFields(pid) {
  try {
    const stat = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
    return stat.slice(stat.lastIndexOf(')') + 2).split(' ');
  } catch { return null; }   // not Linux, or the process is gone - the caller classifies, not throws
}

function processStartTime(pid) {
  const f = procStatFields(pid);
  return (f && f[19]) || null;
}

// Field 3 - the state char, index 0 of what `procStatFields` returns. `Z` is a ZOMBIE: the process
// HAS EXITED and only its exit status is still uncollected, waiting for a parent that may never
// wait() on it. `kill(pid, 0)` succeeds on a zombie and its start-time still matches, so a probe
// built on those two alone calls a finished seat alive FOREVER - which is the one answer this
// module must never give, because a sitting that can never be classified dead can never be stamped
// and never reaped.
function isZombie(pid) {
  const f = procStatFields(pid);
  return !!f && f[0] === 'Z';
}

// "Is it alive" - the ONLY liveness answer in the redesigned daemon [T4-R8]. A pane is a viewport;
// a stored ledger status is history; neither is consulted here.
function isAliveProcess(pid, startTime) {
  const n = Number(pid);
  if (!Number.isInteger(n) || n <= 0) return false;
  try {
    process.kill(n, 0);
  } catch (err) {
    // EPERM means a process with that pid EXISTS and is not ours to signal - alive.
    if (err.code !== 'EPERM') return false;
  }
  if (isZombie(n)) return false;
  const nowStart = processStartTime(n);
  // Both known and different means the pid was recycled and the process this row was written for is
  // gone. Unknown on either side is NOT a death: a /proc read can fail for reasons that are not
  // "the process ended", and this module never turns an unreadable fact into a death.
  if (startTime && nowStart && String(startTime) !== String(nowStart)) return false;
  return true;
}

function isRowAlive(row) {
  return isAliveProcess(row && row.pid, row && row.start_time);
}

// -- THE RECORD --------------------------------------------------------------------------------
//
// One live row per supervised sitting. `goal` is here because a sitting identity in ignite is the
// PAIR (goal, seat) - every ending-store API is keyed that way, so a row that carried only `seat`
// could not name the sitting it supervises to the store that stamps its ending, and two goals
// running a same-named seat would collide into one row.
function makeRecord({ goal, seat, pid, start_time: startTime, launch_token: launchToken, supervision }) {
  if (!seat) throw new Error('registry record requires seat');
  const n = Number(pid);
  if (!Number.isInteger(n) || n <= 0) throw new Error(`registry record requires a positive pid, got ${pid}`);
  const flag = supervision || SUPERVISED;
  if (flag !== SUPERVISED && flag !== UNSUPERVISED) {
    throw new Error(`supervision must be ${SUPERVISED} or ${UNSUPERVISED}, got ${flag}`);
  }
  return {
    goal: goal || '',
    seat,
    pid: n,
    // Resolved HERE when the caller did not carry it, so a spawn door cannot persist a pid with no
    // start-time - a pid-only row is exactly the recycling hole the pair exists to close.
    start_time: startTime === undefined || startTime === null ? processStartTime(n) : String(startTime),
    launch_token: launchToken || '',
    supervision: flag,
  };
}

function keyOf(row) {
  return `${row.goal || ''} ${row.seat}`;
}

// -- PERSISTENCE - JSONL, one record per line ---------------------------------------------------
//
// An ABSENT file and an EMPTY file are the same legal state: a fresh daemon that has spawned
// nothing. Neither is an error and neither is evidence of anything (spec 2.1). A malformed line is
// SKIPPED rather than thrown on, for the module's founding reason: a registry that refuses to load
// is a registry that re-adopts nothing, and re-adopting nothing is the mass-restamp hole.
function loadRegistry(pathOverride) {
  const file = registryPath(pathOverride);
  let text;
  try {
    text = fs.readFileSync(file, 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') return [];
    throw err;
  }
  const rows = [];
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      const row = JSON.parse(trimmed);
      if (row && row.seat && row.pid) rows.push(row);
    } catch { /* a torn or hand-mangled line is not a death sentence for the rest of the file */ }
  }
  return rows;
}

// Whole-file rewrite through a temp file + rename: the rows a flip or a reap changes are IN PLACE
// in the file, so append-only would need a compaction pass nobody asked for. The registry holds one
// row per LIVE sitting - tens of rows, not thousands - so the simplest durable write wins.
function saveRegistry(rows, pathOverride) {
  const file = registryPath(pathOverride);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.tmp-${process.pid}`;
  const body = rows.map((r) => JSON.stringify(r)).join('\n');
  fs.writeFileSync(tmp, rows.length ? `${body}\n` : '', 'utf8');
  fs.renameSync(tmp, file);
  return file;
}

// -- THE FOUR WRITE MOMENTS (spec 1) - and there are no others ----------------------------------

// (i) Immediately after spawn returns a pid: persist pid + start-time + the minted launch token.
function recordSpawn(fields, pathOverride) {
  const row = makeRecord({ ...fields, supervision: fields.supervision || SUPERVISED });
  const rows = loadRegistry(pathOverride).filter((r) => keyOf(r) !== keyOf(row));
  rows.push(row);
  saveRegistry(rows, pathOverride);
  return row;
}

// (ii) Check-in of a seat born OUTSIDE the daemon: insert it, or flip `unsupervised` to
// `supervised`. A console-uncaged seat is not a defect and never a death - it is a sitting the
// daemon did not spawn, and check-in is the moment it becomes supervisable [T4-R8].
function recordCheckIn(fields, pathOverride) {
  const rows = loadRegistry(pathOverride);
  const incoming = makeRecord({ ...fields, supervision: fields.supervision || SUPERVISED });
  const idx = rows.findIndex((r) => keyOf(r) === keyOf(incoming));
  if (idx < 0) {
    rows.push(incoming);
    saveRegistry(rows, pathOverride);
    return incoming;
  }
  // The check-in's own identity pair wins where it carries one, and the flag always ends
  // `supervised`: that flip IS the write moment.
  const merged = { ...rows[idx], ...incoming, supervision: SUPERVISED };
  rows[idx] = merged;
  saveRegistry(rows, pathOverride);
  return merged;
}

// (iii) After an ending is stamped AND confirm-and-reap succeeds: drop the row. NOT after the stamp
// alone - a stamped-but-unreaped sitting is precisely the reap debt `awaitingReap` below reports.
function dropRow({ goal, seat }, pathOverride) {
  const rows = loadRegistry(pathOverride);
  const key = keyOf({ goal: goal || '', seat });
  const kept = rows.filter((r) => keyOf(r) !== key);
  if (kept.length === rows.length) return false;
  saveRegistry(kept, pathOverride);
  return true;
}

// (iv) Boot re-adopt is the fourth moment and it WRITES NOTHING - see `readopt.js`. It is listed
// here so the count stays honest: the pass may only keep or drop rows after spec 2 has classified
// them, and it may never invent a death from a row that is not there.

// -- THE REAP-DEBT SURFACE - successor to team-kit's retired `awaiting-close.json` --------------
//
// The debt file is gone and `load_awaiting` answers `{}`, which left every reap consumer inert: a
// reaper that can never find a debt cannot leak-guard anything. The successor fact is derivable and
// needs no second store - a row that is STILL HERE while its sitting already carries an ending is,
// by write moment (iii), a sitting whose reap has not completed. `hasEnding` is injected rather
// than imported so this module keeps no ending-store handle: liveness and endings stay two files.
function awaitingReap(hasEnding, pathOverride) {
  if (typeof hasEnding !== 'function') throw new Error('awaitingReap requires a hasEnding(row) function');
  return loadRegistry(pathOverride)
    .filter((row) => hasEnding(row))
    .map((row) => ({ ...row, alive: isRowAlive(row) }));
}

module.exports = {
  REGISTRY_FILENAME,
  DEFAULT_REGISTRY_PATH,
  SUPERVISED,
  UNSUPERVISED,
  registryPath,
  processStartTime,
  isAliveProcess,
  isZombie,
  isRowAlive,
  makeRecord,
  keyOf,
  loadRegistry,
  saveRegistry,
  recordSpawn,
  recordCheckIn,
  dropRow,
  awaitingReap,
};
