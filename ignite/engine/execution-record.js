'use strict';

// engine/execution-record.js — THE GOAL'S EXECUTION RECORD: `<goal-folder>/executions.csv`.
//
// ONE PLACE ANSWERS "DID THIS SEAT FINISH", FOR EVERY LANE AND EVERY READER (owner ruling
// decisions.md#d-s23-single-execution-record-now, closing the Phase-6 task filed by
// #d-s18-cross-lane-refusal). Before this file the answer lived in whichever `heart.db` happened to
// have run the seat — the attached lane's `<goal>/heart.db` or the daemon's `{state_root}/heart.db`
// — two disjoint stores over one goal folder, so each lane could run the same seat once (measured:
// probes/probe-cross-lane-resume.js, direction 2).
//
// ⚠ NAMING. The record's TERM is minted registry-side (PRIN-10) and is deliberately NOT coined
// here: this file, the column names and the contract use the FILENAME and the words already in the
// ignite vocabulary (`seat`, `session`, `execution`, and the store's own turn statuses). No new noun
// is introduced by this build.
//
// ── WHAT IT IS, AND WHY IT IS NOT A MIRROR OF TWO STORES (PRIN-11) ────────────────────────────
//
// The two `heart.db` files stay exactly what they were: each lane's OPERATIONAL store — its queue,
// its turns, its messages, its liveness. What moves here is ONE question, completion, and it moves
// WHOLE: every reader that asks "is this seat done" asks this file, and each lane PUBLISHES what it
// alone witnessed into it. That is the difference between a shared record and a mirror — a mirror
// has a second reader for the same question, and after this change there is none: the store's `done`
// rows are consulted by their own lane only as a local no-double-fire guard (`seedTaskforce` is
// create-only WITHIN a store and stays so), never as the answer to "did this goal finish".
//
// The consequence the ruling names: the `done` (engine) vs `exited` (trace) divergence dissolves.
// `sessions.csv` stays LAUNCH/LIFECYCLE accounting — one row per launched session, closed by
// whoever witnessed the termination, which is a fact about a PROCESS. This file carries the
// OUTCOME, which is a fact about the WORK. Neither is overloaded into the other.
//
// ── THE SCHEMA, and why each column is here ───────────────────────────────────────────────────
//
//   seat         the taskforce seat — the cross-lane identity. NOT the job id: a job id is a
//                store-local key (the attached lane spells it `seat-<name>`, the daemon must
//                namespace it per goal because its store holds every goal at once), and keying the
//                shared record on a store-local name is what would make it lane-dependent again.
//   session-id   the join key back into BOTH operational surfaces — `jobs_log.session_id` and
//                `sessions.csv`'s own `session-id` column. It is what makes this record a POINTER
//                to the evidence rather than a copy of it, and what makes an append idempotent.
//   lane         `attached` | `daemon` — DERIVED from the store's own placement (see `laneOf`),
//                never declared by a caller. CMP-2 § Two store kinds already decides it: a store
//                inside the goal folder IS the attached lane's, and any other store is the
//                daemon's. A declared value could be wrong; a derived one cannot.
//   started      when the execution fired (the store's `started_at`, else `fired_at`).
//   ended        stamped when the outcome is known. EMPTY means "still open, as far as the lane
//                that wrote it got to say" — the same convention `sessions.csv` uses.
//   outcome      the store's OWN turn vocabulary, `done|blocked|failed|killed` — no new words
//                (module CLAUDE.md § Terminology: "if a term already exists for what you are
//                writing, USE it"). `done` is the ONLY value that stops another lane re-running the
//                seat, exactly as `seatIsFinished` has always meant it.
//
// Append-only, plus one in-place stamp of the row's `ended`/`outcome` cells — the same discipline
// (and the same reader/writer pair, `seat-identity/csv.js`) the launch trace already uses.
//
// ⚠ EVERY WRITE TAKES A LOCK, AND THAT IS NOT BELT-AND-BRACES. The first version of this file
// shipped the close as an UNLOCKED read-modify-write with a comment calling the race theoretical.
// It is not: measured in review, 300 appends racing 300 closes lost **336 of 601 rows** — WHOLE
// ROWS, silently, with nothing malformed for a reader to detect, and `finishedSeats` transiently
// reading EMPTY mid-rewrite (which is the one wrong answer that re-runs a finished seat). Two lanes
// over one goal is exactly what this record exists for, so the losing interleaving is the normal
// case, not the exotic one.
//
// The cure is the cheapest pair that closes it, and both halves are needed:
//   · a LOCKFILE around every write (`executions.csv.lock`, `O_EXCL` — the same construct
//     `.attached-run.lock` uses, self-clearing, stale-stealing after a deadline), so an append
//     cannot land inside another writer's rewrite;
//   · an ATOMIC REPLACE for the rewrite (temp file in the same directory + `rename`), so a READER
//     — which takes no lock, and must not have to — never observes a partial or empty file.

const fs = require('node:fs');
const path = require('node:path');
const { readCsv, appendRow, splitRow, quoteField } = require('../server/seat-identity/csv');
const { TERMINAL_TURN_STATUSES } = require('../server/heart/heart-store');

const RECORD_FILENAME = 'executions.csv';
const COLUMNS = ['seat', 'session-id', 'lane', 'started', 'ended', 'outcome'];
const DONE = 'done';
const LANE_ATTACHED = 'attached';
const LANE_DAEMON = 'daemon';

// A seat's home, as every lane writes it: `<workspace>/.rbtv/goals/<goal>/seats/<seat>`. This is
// the ONE derivation that makes a store row lane-independent — the daemon's store holds rows for
// every goal it serves, and `workdir` is the column that says which goal and which seat, in both
// lanes, without a workspace root to resolve or a job-id spelling to agree on.
const SEAT_DIR_RE = /^(.*[/\\]\.rbtv[/\\]goals[/\\][^/\\]+)[/\\]seats[/\\]([^/\\]+)[/\\]?$/;

function seatHomeOf(workdir) {
  if (!workdir) return null;
  const m = SEAT_DIR_RE.exec(path.resolve(workdir));
  return m ? { goalFolder: m[1], seat: m[2] } : null;
}

// The lane, DERIVED from the store's placement (CMP-2 § Two store kinds) rather than declared.
function laneOf(dbPath, goalFolder) {
  return path.resolve(path.dirname(dbPath)) === path.resolve(goalFolder) ? LANE_ATTACHED : LANE_DAEMON;
}

function recordPath(goalFolder) {
  return path.join(goalFolder, RECORD_FILENAME);
}

// Sleep, synchronously, with no dependency and no busy spin: `Atomics.wait` on a lock word nobody
// notifies is the stdlib's blocking sleep. The waits here are milliseconds.
function sleepMs(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

// The write lock. `wx` is the atomicity — the filesystem's, not a check-then-write.
//
// A holder that DIED still holds the file, so the lock is stolen after `LOCK_STALE_MS` rather than
// bricking the record forever: the protected section is a few file operations, so a lock older than
// that belongs to a process that is gone (the alternative — a pid liveness check — buys precision
// this section's length does not need, and the cost of a wrong steal here is the unlocked behaviour
// we already survived, not corruption of a longer transaction).
const LOCK_SUFFIX = '.lock';
const LOCK_STALE_MS = 5000;

function withRecordLock(goalFolder, fn) {
  const lockPath = recordPath(goalFolder) + LOCK_SUFFIX;
  const start = Date.now();
  for (;;) {
    try {
      const fd = fs.openSync(lockPath, 'wx');
      fs.closeSync(fd);
      break;
    } catch (err) {
      if (err.code !== 'EEXIST') throw err;
      if (Date.now() - start > LOCK_STALE_MS) { try { fs.unlinkSync(lockPath); } catch { /* someone else cleared it */ } }
      sleepMs(2);
    }
  }
  try {
    return fn();
  } finally {
    try { fs.unlinkSync(lockPath); } catch { /* already stolen */ }
  }
}

// Replace the file atomically: readers take no lock, so they must never see a half-written file.
// The temp file is in the SAME directory because `rename` is only atomic within a filesystem.
function atomicWrite(filePath, text) {
  const tmp = path.join(path.dirname(filePath), `.${path.basename(filePath)}.${process.pid}.${Date.now()}.tmp`);
  fs.writeFileSync(tmp, text, 'utf8');
  fs.renameSync(tmp, filePath);
}

function readExecutionRecord(goalFolder) {
  const { exists, header, rows } = readCsv(recordPath(goalFolder));
  return { exists, header, rows: rows.filter((r) => r.seat) };
}

// THE READER EVERY LANE ASKS. A seat is finished when THIS file says so — that sentence is the
// whole build.
function finishedSeats(goalFolder) {
  return new Set(readExecutionRecord(goalFolder).rows
    .filter((r) => (r.outcome || '').trim() === DONE)
    .map((r) => r.seat));
}

// The header is spelled HERE and nowhere else — this file owns this schema, the way `coord.py`
// owns `sessions.csv`'s. Created on first write; never rewritten, so a later widening can append a
// column to a live file without touching a byte of its rows.
function ensureFileLocked(goalFolder) {
  const p = recordPath(goalFolder);
  const { exists, header } = readCsv(p);
  if (!exists || header.length === 0) atomicWrite(p, `${COLUMNS.join(',')}\n`);
  return p;
}

// OPEN a row, in the dispatching act. Idempotent on `session-id`: a second call for the same
// execution appends nothing, so a sync that runs every tick does not grow the file every tick.
function openExecution({ goalFolder, seat, sessionId, lane, startedAt }) {
  if (!sessionId) return { appended: false, reason: 'no session id — the launch has not happened yet' };
  // The idempotence CHECK and the append are one critical section: outside the lock, two publishes
  // of the same execution both read "absent" and both append.
  return withRecordLock(goalFolder, () => {
    const p = ensureFileLocked(goalFolder);
    if (readCsv(p).rows.some((r) => r['session-id'] === sessionId)) {
      return { appended: false, reason: 'already recorded' };
    }
    return appendRow(p, {
      seat, 'session-id': sessionId, lane, started: startedAt || '', ended: '', outcome: '',
    });
  });
}

// CLOSE it, when the outcome is known. NEVER overwrites a stamped row: whoever recorded an outcome
// first witnessed it, and a second writer's guess must not replace a first writer's observation
// (the same posture the foreground carrier's execution-row guard takes).
function closeExecution(args) {
  return withRecordLock(args.goalFolder, () => closeExecutionLocked(args));
}

function closeExecutionLocked({ goalFolder, sessionId, outcome, endedAt }) {
  const p = recordPath(goalFolder);
  const raw = (() => { try { return fs.readFileSync(p, 'utf8'); } catch { return null; } })();
  if (raw === null) return { closed: false, reason: 'no record file' };
  const lines = raw.split('\n');
  const header = splitRow(lines[0]).map((h) => h.trim());
  const at = (name) => header.indexOf(name);
  if (at('session-id') < 0 || at('outcome') < 0) return { closed: false, reason: 'record has no session-id/outcome column' };
  for (let i = 1; i < lines.length; i += 1) {
    if (!lines[i].length) continue;
    const cells = splitRow(lines[i]);
    while (cells.length < header.length) cells.push('');
    if (cells[at('session-id')] !== sessionId) continue;
    if ((cells[at('outcome')] || '').trim()) return { closed: false, reason: 'already closed' };
    cells[at('outcome')] = outcome;
    if (at('ended') >= 0) cells[at('ended')] = endedAt || '';
    lines[i] = header.map((_, c) => quoteField(cells[c])).join(',');
    atomicWrite(p, lines.join('\n'));
    return { closed: true, outcome };
  }
  return { closed: false, reason: 'no open row for this session id' };
}

// ── THE PUBLISH PASS — how each lane's witness reaches the shared record ───────────────────────
//
// Called by `engine.tick()` (so it covers EVERY completion path there is — an agent's own
// completion message, the ticker's crash sweep, a kill, a spawn that threw — without a hook in any
// of them) and at boot before seeding (so a store that predates this file publishes its history the
// first time its lane runs again: the ADOPTION path, which is what keeps a goal already half-run
// from re-running its finished seats the day this lands).
//
// It reads the store and writes the record, and never the other way round: the record is not a
// second place to write execution state, it is where execution OUTCOMES are published.
//
// ponytail: a full scan of the store's own status partitions each tick, and one file read per goal
// touched. On the daemon's store that is O(rows) every cadence; it is nothing beside the tick's own
// SQL today, and the upgrade path when it stops being nothing is a watermark on `exec_id` plus a
// re-scan of the non-terminal rows only.
function publishToRecord(heartStore, { statuses, logger = null } = {}) {
  const all = statuses || ['launching', 'running', 'done', 'blocked', 'failed', 'stalled', 'killed'];
  const opened = [];
  const closed = [];
  for (const status of all) {
    for (const row of heartStore.listExecutionsByStatus(status)) {
      const home = seatHomeOf(row.workdir);
      if (!home || !row.session_id) continue;      // not a seat launch, or not launched yet
      const lane = laneOf(heartStore.dbPath, home.goalFolder);
      const o = openExecution({
        goalFolder: home.goalFolder,
        seat: home.seat,
        sessionId: row.session_id,
        lane,
        startedAt: row.started_at || row.fired_at || '',
      });
      if (o.appended) opened.push(`${home.seat}/${row.session_id}`);
      if (!TERMINAL_TURN_STATUSES.has(row.status)) continue;
      const c = closeExecution({
        goalFolder: home.goalFolder,
        sessionId: row.session_id,
        outcome: row.status,
        endedAt: row.ended_at || '',
      });
      if (c.closed) closed.push(`${home.seat}=${row.status}`);
    }
  }
  if (logger && (opened.length || closed.length)) {
    logger({ level: 'info', message: 'execution record published', opened, closed });
  }
  return { opened, closed };
}

module.exports = {
  RECORD_FILENAME,
  COLUMNS,
  DONE,
  LANE_ATTACHED,
  LANE_DAEMON,
  recordPath,
  readExecutionRecord,
  finishedSeats,
  openExecution,
  closeExecution,
  publishToRecord,
  seatHomeOf,
  laneOf,
  withRecordLock,
};
