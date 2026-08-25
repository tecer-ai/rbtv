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
// ⚠ NAMING. The record's TERM is **execution record** — MINTED registry-side 2026-08-10
// (system-definition/decisions.md#d-execution-record, concepts/execution-record.md), per PRIN-10;
// this build deliberately coined nothing and the mint is now the definition's one home. This file,
// the column names and the contract use the FILENAME and the words already in the ignite
// vocabulary (`seat`, `session`, `execution`, and the store's own turn statuses).
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
//   outcome      ⚠⚠ A **PROCESS** VOCABULARY SINCE W2 — `clean|crashed|killed`, and NOT the store's
//                turn words. What this column now answers is "how did the PROCESS end", which is
//                the only question a lane that watched a process exit can honestly answer. Whether
//                the WORK is done is the seat's own CHECK-OUT DISPOSITION, read off
//                `coord.py ready-seats --json` (§ WHERE DONE-NESS LIVES NOW, below).
//                  `clean`    the turn ended normally — the store says `done` or `blocked`. BOTH
//                             are clean exits: `blocked` is a seat reporting, in its own turn, that
//                             it is waiting on something outside itself. Nothing crashed.
//                  `crashed`  terminal without a successful completion (store `failed`).
//                  `killed`   explicitly killed through the kill surface.
//
// ⚠ `exited` IS DELIBERATELY NOT A MEMBER (owner ruling D-8). It is already a DISPOSITION value in
// `sessions.csv`, and a word living in both vocabularies at once is exactly the BLOCKED/HELD
// collision class this narrowing exists to remove. And a vocabulary with no crash bit gives the
// daemon's retry trigger no honest predicate: it would either never fire on a crash or fire on
// every clean exit. (The trigger that read this pair — coord's daemon self-grant — is DELETED with
// the rest of the grant machinery, D12 2026-08-20; the narrowing stands on its own.)
//
// ── WHERE DONE-NESS LIVES NOW (W2) ────────────────────────────────────────────────────────────
//
// It was here, and being here was the defect. A seat that honestly declared FAIL-BLOCKED was
// recorded `done` by this engine, because the engine derived the WORK's outcome from a PROCESS it
// watched exit 0 — a derivation no exit code can support. So the column narrows to what the lane
// actually witnessed, and the one surface that knows what the seat DECLARED answers the rest:
// `coord.py ready-seats --json` carries a `disposition` field on every row, from the seat's own
// check-out. `supervisor/seeding.js#recordView` reads it. There is ONE parser of that answer and it is
// coord's; nothing in JS re-derives done-ness from a CSV cell again.
//
// The old `outcome` values on live goals become INERT rather than rewritten — no file is migrated
// (the D-5 disposition backfill is what makes the new reader correct on goals already running).
//
// Append-only, plus one in-place stamp of the row's `ended`/`outcome` cells — the same discipline
// (and the same reader/writer pair, `seat-identity/csv.js`) the launch trace already uses.
//
// ⚠ EVERY WRITE TAKES A LOCK, AND THAT IS NOT BELT-AND-BRACES. The first version of this file
// shipped the close as an UNLOCKED read-modify-write with a comment calling the race theoretical.
// It is not: measured in review, 300 appends racing 300 closes lost **336 of 601 rows** — WHOLE
// ROWS, silently, with nothing malformed for a reader to detect, and the record's own reader
// (`ranSeats`, then spelled `finishedSeats`) transiently reading EMPTY mid-rewrite — which is the
// one wrong answer that re-runs a seat another lane already ran. Two lanes
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
const { readCsv, appendRow, splitRow, quoteField } = require('../runtime/seat-identity/csv');
const { TERMINAL_TURN_STATUSES } = require('../state-store/heart/heart-store');

const RECORD_FILENAME = 'executions.csv';
const COLUMNS = ['seat', 'session-id', 'lane', 'started', 'ended', 'outcome'];
// THE NARROWED PROCESS VOCABULARY (§ THE SCHEMA). Three words, closed set.
// History join only — this file no longer publishes a work outcome. ended is the close stamp.

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

// WHICH SEATS THIS RECORD HAS SEEN RUN TO TERMINATION — any lane, any process outcome.
//
// ⚠ IT IS NOT `finishedSeats` AND THE RENAME IS THE WHOLE POINT (W2). That function answered "is
// this seat done" off a `done` cell in this column, and after the narrowing no cell here can answer
// that: `clean` says a process ended tidily, which is true of a seat that fail-blocked. Done-ness
// is the check-out disposition (§ WHERE DONE-NESS LIVES NOW). What this file can still say — and
// what its cross-lane readers actually spend — is "a lane ran this seat and watched it end".
// ⚠ AND IT KEYS ON `ended`, NOT ON `outcome` — the same Row D migration `closeExecutionLocked`
// carries. Spec-state-store emptied the work word out of that column, so filtering on it answered
// "no lane has ever run any seat" for every goal in the build. `ended` is the close stamp.
function ranSeats(goalFolder) {
  return new Set(readExecutionRecord(goalFolder).rows
    .filter((r) => (r.ended || '').trim())
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

// ── A DELETED GOAL IS SKIPPED, NEVER THROWN ON (IPH-15, owner-ruled `one-readiness-predicate.md`
// § D7) ───────────────────────────────────────────────────────────────────────────────────────
//
// `publishToRecord` below full-scans EVERY status partition each tick, terminal rows included, so
// it re-walks the rows of a goal whose folder was DELETED forever. The lock file's `openSync` then
// throws ENOENT on the missing parent directory, and — measured on the VPS, 2026-08-11 — that
// throw escaped into the daemon's lane-watch pass and ABORTED SEEDING FOR EVERY GOAL: the error
// line named a healthy goal (`forge-reference-seat-id-naming`) while a dead one supplied the path,
// 2160 occurrences in six hours. The workaround was two empty directories re-created by hand on
// the box, with a standing "do not delete".
//
// A TERMINAL ROW FOR A VANISHED GOAL IS NORMAL. There is no record to publish to and nothing to
// lose, so both writers answer with the same typed non-write every other refusal here uses. The
// guard is on the WRITERS rather than in the publish loop because every caller routes through
// them — the attached lane's foreground carriage writes here too, and a guard in one caller leaves
// its sibling holding the same ENOENT.
const VANISHED = 'the goal folder no longer exists — a terminal row for a deleted goal is normal, and there is no record to publish to';

function goalFolderExists(goalFolder) {
  return Boolean(goalFolder) && fs.existsSync(goalFolder);
}

// OPEN a row, in the dispatching act. Idempotent on `session-id`: a second call for the same
// execution appends nothing, so a sync that runs every tick does not grow the file every tick.
function openExecution({ goalFolder, seat, sessionId, lane, startedAt }) {
  if (!sessionId) return { appended: false, reason: 'no session id — the launch has not happened yet' };
  if (!goalFolderExists(goalFolder)) return { appended: false, reason: VANISHED };
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
  if (!goalFolderExists(args.goalFolder)) return { closed: false, reason: VANISHED };
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
    // ⚠ THE CLOSE STAMP IS `ended`, AND KEYING THIS ON `outcome` WAS A LIVE DEFECT. Row D of
    // spec-state-store emptied the work word out of this column, so `outcome` is now blank on
    // EVERY closed row — and this guard, which reads a blank cell as "still open", re-closed every
    // terminal row of every goal on every tick, forever. `ended` is what the schema calls the close
    // stamp (see COLUMNS), it is written right here, and it is never blank on a closed row.
    if ((cells[at('ended')] || '').trim()) return { closed: false, reason: 'already closed' };
    cells[at('outcome')] = outcome;
    // …which means it must never be written blank: a row stamped with an empty `ended` would be
    // closed and unrecognizable as closed, which is the defect above with one extra step.
    if (at('ended') >= 0) cells[at('ended')] = endedAt || new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
    lines[i] = header.map((_, c) => quoteField(cells[c])).join(',');
    atomicWrite(p, lines.join('\n'));
    return { closed: true, outcome };
  }
  return { closed: false, reason: 'no open row for this session id' };
}

// ── THE OWNER-ASK HOLD IS NO LONGER DECIDED HERE (W2, owner-ruled) ────────────────────────────
//
// `blockAndQueueVerdict`, `askParkedAtGate` and `outcomeForSeat` lived here and are DELETED. They
// derived the WORK's outcome from a process this engine watched exit, and published `blocked` into
// the outcome column to hold a seat's dependents. Three things were wrong with that, and all three
// are the incident this program closes:
//
//   · the hold fired ONLY on a seat declaring `fallback: block-and-queue`, so a seat that honestly
//     fail-blocked without that key was published `done` and its dependents ran on a stale product;
//   · it fired only when the ferry had DELIVERED the ask, and the delivery gates (goal execution
//     mode, `human-interactive:` on the descriptor) were the root cause of the parked-ask stall —
//     a gate deciding whether a question is real;
//   · it put the answer in a column that also had to say what became of the process, so `blocked`
//     meant two things and the two collided.
//
// The hold is now ONE verdict, `HELD`, computed in `coord.py ready-seats` — the surface that
// already knows what every seat declared — and it applies UNIVERSALLY to an unanswered owner-ask.
// The engine consumes it (`seeding.js#recordView`) exactly where it used to consume the `blocked`
// row. Nothing in JS parses that question again.
//
// TWO FUNCTIONS SURVIVE, and they were never part of the hold: they are the ASK/ANSWER PAIRING on
// the goal's own bus, and `chat/bus-answer.js` is now their ONE consumer — it must name the ask
// its `--re` settles, and a second walk of the same file with the same rule is the drift this whole
// design removes. Kept here rather than moved into `bus-answer.js` because moving them would rename
// the pairing's home for no behavioural gain and re-point every citation of it.

// Does `to:` address this seat? The ferry's own tolerance (`addressesOwner`), for a seat name: a
// token that merely CONTAINS the name is a different seat.
function addressesSeat(to, seat) {
  return String(to).split(/[,\s]+/).some((t) => t === seat);
}

// THE PAIRING — this seat's `to: owner` rows that no later `answer` addressed back has closed, in
// id order, as ROWS. Extracted by task 7.771 from the hold verdict W2 has since deleted, for ONE
// reason that outlived it:
// `chat/bus-answer.js` has to name the ask its `--re` settles, and a second walk of the same
// file with the same rule is exactly the "two readers of one question that disagree" this whole
// design removes. There is now one definition and two consumers — the hold, and the row that
// clears it.
//
// Greedy and FIFO (`shift`): the oldest open row is the one an answer settles. NOT ask-only — a
// `to: owner` note holds a slot too, because it is a thing the seat put in front of the owner;
// callers that need an ASK specifically (coord's `--re` takes nothing else) filter on `type`.
function openOwnerAsks(busText, seat) {
  const { parseMessages, addressesOwner } = require('../chat/bus-ferry');
  const open = [];
  for (const row of parseMessages(busText)) {
    if (row.from === seat && addressesOwner(row.to)) open.push(row);
    else if (row.type === 'answer' && addressesSeat(row.to, seat) && open.length) open.shift();
  }
  return open;
}
// The interim owner-note shell-out that stood here (W2, adv C25 — one owner `note` per non-clean
// close, shelled to coord from the tick) is RETIRED WITH ITS CONDITION (closeout task 17 item 2,
// 2026-08-17). W3 built the staff-mail carrier it was waiting on: the ticker's enforce sweep calls
// `spawn.js#closeSeatSessionRow` (coord `attest-exit --force-dead`) the moment a process is
// observed gone, and coord's closer (`close_session_seat` → `close_staff_mail_arm`) mints one
// leader-chair mail plus a relaunch wake for EVERY terminal non-`done` ending — a mechanical
// receiver, where the interim note reached an unreceived owner DM. Two mechanisms for one
// surfacing was the defect; the tick now carries none, and `nonClean` below is report-only.

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
// touched. On the daemon's store that is O(rows) every cadence — 131 ms at 26,791 rows on
// 2026-08-12 — and the upgrade path when that stops being cheap is a watermark on `exec_id` plus a
// re-scan of the non-terminal rows only. ⚠ It was NOT cheap until that date and the reason is worth
// keeping: `listExecutionsByStatus` attached a chain `thread` to every row with a recursive CTE per
// row, so this pass cost 874 ms a tick to act on 18 rows, and blocked the gateway's accept path for
// most of a cadence. This call now passes `withThread: false`. Anything added to this loop is paid
// once per execution EVER RECORDED, so measure it against the whole store, not against a fresh one.
function publishToRecord(heartStore, { statuses, logger = null } = {}) {
  const all = statuses || ['launching', 'running', 'done', 'blocked', 'failed', 'stalled', 'killed'];
  const opened = [];
  const closed = [];
  const nonClean = [];
  // WHICH ROWS ARE ALREADY PUBLISHED, read ONCE per goal per pass. `closeExecution` refuses a
  // second stamp on its own, so this is not correctness — it spares the lock on every already-closed
  // row, and it is what keeps `nonClean` below reporting each ending ONCE instead of once per
  // terminal row per tick, forever, for the whole life of the goal.
  const closedIds = new Map();
  const alreadyClosed = (goalFolder, sessionId) => {
    if (!closedIds.has(goalFolder)) {
      // `ended`, NOT `outcome` — the same Row D migration `closeExecutionLocked` carries. A blank
      // outcome column is now the normal shape of a CLOSED row, so filtering on it made this set
      // permanently empty and `nonClean` re-reported every terminal row of the goal every tick.
      closedIds.set(goalFolder, new Set(readExecutionRecord(goalFolder).rows
        .filter((r) => (r.ended || '').trim()).map((r) => r['session-id'])));
    }
    return closedIds.get(goalFolder).has(sessionId);
  };
  for (const status of all) {
    // `withThread: false` — this pass reads workdir/session_id/status/timestamps and never
    // `thread`, and the attach is a recursive CTE PER ROW over the store's whole history.
    for (const row of heartStore.listExecutionsByStatus(status, { withThread: false })) {
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
      if (alreadyClosed(home.goalFolder, row.session_id)) continue;
      const c = closeExecution({
        goalFolder: home.goalFolder,
        sessionId: row.session_id,
        outcome: '',
        endedAt: row.ended_at || '',
      });
      if (c.closed) {
        closed.push(`${home.seat}=ended`);
        // ⚠ NON-CLEAN IS THE LANE'S TURN STATUS, READ AS HISTORY (§5: `jobs_log` → history), and
        // it is NOT the killed `outcome` word — which is why the row's own cell stays blank. It
        // used to be pushed for EVERY close, clean ones included, because the word it tested was
        // deleted out from under it: a tidy `done` turn reported itself as a non-clean ending.
        // The DEATH-TRUTH of the work is not here at all — that is the ending store's
        // `failed:crash` plus its evidence pointer (§4.4). This list is the lane's witness of how
        // the PROCESS ended, report-only, for the log and the probes.
        if (row.status !== 'done') {
          nonClean.push({
            seat: home.seat, goalFolder: home.goalFolder, sessionId: row.session_id, status: row.status,
          });
        }
      }
    }
  }
  if (logger && (opened.length || closed.length)) {
    logger({ level: 'info', message: 'execution record published', opened, closed });
  }
  // `nonClean` is REPORT-ONLY since the interim owner-note retired (see the note above the publish
  // pass): surfacing a non-clean ending is coord's staff-mail arm, reached through the enforce
  // sweep's session-closer — never this pass. The list stays in the return so the log and the
  // probes can still see which closes were non-clean.
  return { opened, closed, nonClean };
}

module.exports = {
  RECORD_FILENAME,
  COLUMNS,
  openOwnerAsks,
  addressesSeat,
  LANE_ATTACHED,
  LANE_DAEMON,
  recordPath,
  readExecutionRecord,
  ranSeats,
  openExecution,
  closeExecution,
  publishToRecord,
  seatHomeOf,
  laneOf,
  withRecordLock,
};
