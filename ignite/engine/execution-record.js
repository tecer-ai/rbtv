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
// The store's own word for "ended its turn blocked on something outside itself" (module CLAUDE.md
// § Session lifecycle states). It is what a HELD seat's row carries — see § THE BLOCK-AND-QUEUE
// HOLD below. No word is minted for this: `blocked` already means exactly it.
const BLOCKED = 'blocked';
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
    if ((cells[at('outcome')] || '').trim()) return { closed: false, reason: 'already closed' };
    cells[at('outcome')] = outcome;
    if (at('ended') >= 0) cells[at('ended')] = endedAt || '';
    lines[i] = header.map((_, c) => quoteField(cells[c])).join(',');
    atomicWrite(p, lines.join('\n'));
    return { closed: true, outcome };
  }
  return { closed: false, reason: 'no open row for this session id' };
}

// ── THE BLOCK-AND-QUEUE HOLD (owner ruling decisions.md#d-block-and-queue-mechanical-hold) ────
//
// A seat whose descriptor declares `fallback: block-and-queue` and that ASKED THE OWNER and exited
// without an answer is NOT `done` to the DAG. Its dependents wait. That is the arm's one-home
// definition (`meta/planning/references/file-prompt.md` § fallback: "hold the seat, queue the
// question") made mechanical — until this row the wait was procedural, i.e. an instruction to an
// LLM, and `block-and-queue` differed from `default-and-disclose` at the OWNER's surface only.
//
// ⚠ THE HOLD IS ONE WORD IN THE RECORD, AND THAT IS THE WHOLE MECHANISM. The asking session really
// did exit 0, so the STORE's turn is `done` — a fact about a process, correctly recorded. What the
// RECORD publishes is what became of the WORK, and the work is blocked on the owner. So the close
// writes `blocked` instead of `done`, and every reader that already asks the record "is this seat
// finished" (`seeding.js#recordView` → `seatState`, `attached-execution.js#evaluateExit`) answers
// NO with no new concept and no second scheduler. There is NO new state file, NO poll loop and no
// held-ness stored anywhere: held-ness IS the row (PRIN-11).
//
// ⚠ WHAT RELEASES IT — AND WHY IT IS NOT A LATER BUS ROW, though the ruling's sketch reads that
// way. This paragraph WAS true and is now HALF true; both halves matter, so it is amended rather
// than rewritten. The measurement it records stands: `bus-ferry.js` is outbound-only by
// construction ("Slack → bus stays the sittings' job") and the owner's reply in the agent's thread
// mints a SESSION at the asking seat's own home (`bridges/chat/forward-path.js`, route kind
// `agent`), so for as long as no writer put the answer on the bus, a release derived from a bus
// answer was a hold nothing could ever clear. (It was also measured the hard way: the first
// version of this file did re-derive the hold from the bus at every close, and the REVIVED
// session's own `done` republished `blocked` because the original ask was still sitting there
// unanswered. The probe's paired arm went red.)
//   ⚑ TASK 7.771 (owner ruling 2026-08-11, design § D8) MADE ONE WRITER EXIST, and it is still not
// the bridge: the reply leg makes ONE gateway call (`record-bus-answer`) and the DAEMON shells to
// `coord.py send --type answer`, so `coordination/messages.md` keeps exactly one writer — coord.
// The `open` walk above therefore now SHIFTS on a delivered reply, and `spent` stops being the only
// discriminator. Nothing here changed: both terms are computed exactly as before, and a deployment
// whose bridge predates 7.771 (or whose bus write failed — it is best-effort by ruling) is the
// unchanged `spent`-only case. See `engine/bus-answer.js`.
//   The release is therefore the REVIVAL the answer mints: it opens a SECOND record row for the
// seat, and the seat's LAST word in the record is what every reader keys on (`seeding.js#recordView`
// § notFinished) — open while the revived session works, `done` when it finishes. The owner's answer
// is still what releases the hold; it does so one leg further up, at the surface that actually
// carries answers.
//   The operator escape when no answer will ever come is the one that already exists for every
// other kind of stuck seat: `--relaunch <seat>`, which clears this hold exactly as it clears a
// foreign one.
//
// ⚠ THE ASKS ARE PAIRED AGAINST THE HOLDS ALREADY PUBLISHED, which is what makes the release above
// work and is not a second correlation: an unanswered ask that a PREVIOUS turn was already held on
// is spent. Count the seat's still-open owner-asks on the bus and the HOLD-MINTED `blocked` rows the
// record already carries for it; hold only while the first exceeds the second. So the asking turn is
// held (1 > 0), the revived turn is not (1 > 1 is false), and a revived turn that asks AGAIN is held
// again (2 > 1). Greedy, in id order, exactly like `attached-execution.js#unansweredAsks` — which
// pairs the STORE's typed ask/answer messages and cannot see a bus row at all.
//
// ⚠⚠ "HOLD-MINTED" IS THE WHOLE OF REVIEW FINDING F3, AND COUNTING EVERY `blocked` ROW WAS WRONG.
// `blocked` is a real turn status a seat can END on for its own reasons, and such a turn publishes
// a `blocked` row here too. Counting it as a spent hold made the NEXT turn's genuine ask read as
// already-held: measured — an unrelated blocked turn, then a turn that asks and exits, published
// `done` and released the dependent with the question unanswered. Precisely the failure the ruling
// exists to prevent, reached through the guard meant to enforce it.
//   THE DISCRIMINATOR IS THE STORE, and it needs no new column, no new word and nothing stored
// (PRIN-11): a hold-minted row is one whose TURN was `done` — that is the only case this function
// ever rewrites — while a genuinely blocked turn is `blocked` on both surfaces. So the count joins
// the record's `blocked` rows to the store's `done` turns on `session-id`, which is the join the
// record was built around.
//   BOUND, disclosed: a hold minted by the OTHER lane's store is invisible to this one, so a seat
// held on the daemon lane and then closed by an attached turn can hold a second time on the same
// ask. Holding twice is the safe direction (the unsafe one is advancing past the question), and the
// operator escape is the same `--relaunch`.
//
// ⚠ THE BUS IS READ EXACTLY ONCE PER ASK — HERE, at the close, and never at read time. It answers
// the one question the record cannot: was the seat's ask ALREADY ANSWERED before it exited (a peer
// answered on the bus), in which case nothing is held. Reading it at every `seatState` instead
// would put a multi-megabyte file (5.9 MB on the run the ferry was built against) on the eligibility
// path of every tick, to re-derive a fact that does not change.
//
// ⚠ THE DISCLOSED DEADLOCK: if the goal is NOT in `interactive` execution mode the ferry PARKS the
// ask (§ THE TWO GATES) — nobody is told, so nobody answers, and this hold stands until a human
// runs `--relaunch`. Holding is still the safe direction (the alternative is advancing a wave past
// an unanswered question), and the stamp below is logged at `warn` naming the seat so the condition
// is visible rather than silent.
// ── AND THE HOLD KEYS ON A **DELIVERED** ASK, NOT ON THE ARM (owner ruling
// decisions.md#d-parked-ask-autonomous-workaround) ────────────────────────────────────────────
//
// THE OWNER'S CORRECTION, which is the whole of this section: "the autonomous mechanism does not
// exist to prevent me from getting messages; it exists to make agents complete workflows fully
// autonomously." AUTONOMOUS MEANS THE WORKFLOW COMPLETES. So a `block-and-queue` seat holds the
// wave only when its question ACTUALLY REACHED THE OWNER — when an answer can come. In an
// autonomous goal the ferry PARKS the ask (§ THE TWO GATES): nobody is told, so nobody can reply,
// and holding there would stall a goal on an answer that cannot exist. That was filed as this
// build's one dead end and the owner ruled it isn't one — it is the AUTONOMOUS PATH:
//
//   · the seat executes its AUTHORED AUTONOMOUS WORKAROUND (`d-s14-autonomous-dod` + planning-v4
//     D16): derive the answer, record it with provenance in the goal's own ledgers
//     (`decisions.md` / `doubts.md`), proceed. The parked ask and the derived answer both land
//     durably for the owner to review on return.
//   · the wave CONTINUES. The record publishes the seat's real outcome (`done`), because the seat
//     really did finish its turn.
//
// ⚠ THE OBLIGATION TO CARRY A WORKAROUND IS THE SEAT'S, NOT THIS ENGINE'S. Nothing here derives an
// answer or writes a ledger; the engine's whole job is (1) not to hold a seat whose question was
// parked and (2) to report which of the two happened. What enforces the seat side today, and where
// it is thin, is stated in the contract (`bridges/chat/README.md` § The seat's fallback arm).
//
// ⚠ HOW "WAS IT DELIVERED?" IS DERIVED — the same storage-free way as everything else (PRIN-11).
// The ferry's park decision writes NOTHING: no state file, no bus row, no marker. It is a pure
// function of three files on disk, evaluated per row inside the pass (`bus-ferry.js`, the `gate`
// ladder). So the answer is re-derived here from THE FERRY'S OWN READERS — never a second parse of
// those files — and the one thing that could drift, the ladder's rung SET, is pinned by a
// structural arm in `probes/probe-block-and-queue-hold.js` that goes red if the ferry grows a
// fourth gate.
//
// ⚠ THE SKEW, disclosed: the gates are read HERE at close time and THERE at ferry time, so an owner
// who flips `<goal>/execution-mode` between the ask and the seat's exit gets the mode in force at
// the close. The window is one tick, both directions are safe (hold with an answer possible, or
// proceed on the authored workaround), and the alternative — recording the delivery verdict at ferry
// time — is the state file this ruling's design deliberately does not have.
const FALLBACK_BLOCK_AND_QUEUE = 'block-and-queue';
const BUS_RELPATH = ['coordination', 'messages.md'];

// Did an agent-initiated `to: owner` row from this seat REACH the owner? The ferry's gate ladder,
// in the ferry's own order, through the ferry's own readers.
//
// The ladder's THIRD rung — `fallback: park` — is deliberately absent: every caller here has
// already established the arm is `block-and-queue`, so that rung cannot fire. The structural arm
// named above is what keeps that assumption honest.
//
// Returns the ferry's own gate NAME when the row parks (so the report can say WHY), else null.
function askParkedAtGate(goalFolder, seat) {
  const { goalExecutionMode, seatIsHumanInteractive, INTERACTIVE_MODE } = require('../bridges/chat/bus-ferry');
  // `<workspace>/.rbtv/goals/<goal>` — the same derivation `statusAttached` makes to reach the
  // reader, which takes the workspace root and the goal NAME.
  const workspaceRoot = path.resolve(goalFolder, '..', '..', '..');
  if (goalExecutionMode(workspaceRoot, path.basename(goalFolder)) !== INTERACTIVE_MODE) return 'execution-mode';
  if (!seatIsHumanInteractive(goalFolder, seat)) return 'human-interactive';
  return null;
}

// Does `to:` address this seat? The ferry's own tolerance (`addressesOwner`), for a seat name: a
// token that merely CONTAINS the name is a different seat.
function addressesSeat(to, seat) {
  return String(to).split(/[,\s]+/).some((t) => t === seat);
}

// THE PAIRING — this seat's `to: owner` rows that no later `answer` addressed back has closed, in
// id order, as ROWS. Extracted from `blockAndQueueVerdict` (below) by task 7.771 for ONE reason:
// `engine/bus-answer.js` has to name the ask its `--re` settles, and a second walk of the same
// file with the same rule is exactly the "two readers of one question that disagree" this whole
// design removes. There is now one definition and two consumers — the hold, and the row that
// clears it.
//
// Greedy and FIFO (`shift`): the oldest open row is the one an answer settles. NOT ask-only — a
// `to: owner` note holds a slot too, because it is a thing the seat put in front of the owner;
// callers that need an ASK specifically (coord's `--re` takes nothing else) filter on `type`.
function openOwnerAsks(busText, seat) {
  const { parseMessages, addressesOwner } = require('../bridges/chat/bus-ferry');
  const open = [];
  for (const row of parseMessages(busText)) {
    if (row.from === seat && addressesOwner(row.to)) open.push(row);
    else if (row.type === 'answer' && addressesSeat(row.to, seat) && open.length) open.shift();
  }
  return open;
}

// The evidence string when the seat is HELD, else null. Held = the arm is `block-and-queue` AND the
// seat's last `to: owner` row on the coordination bus has no LATER `answer` addressed back to it.
//
// The bus readers are the ferry's OWN (`parseMessages` / `addressesOwner` / `seatFallback`) — a
// second parser of that file is a lane that disagrees with the ferry about what a seat declared and
// what it asked, which is the defect `seatIsHumanInteractive`'s F3 note describes in full.
function blockAndQueueVerdict(heartStore, goalFolder, seat) {
  const { seatFallback } = require('../bridges/chat/bus-ferry');
  if (seatFallback(goalFolder, seat) !== FALLBACK_BLOCK_AND_QUEUE) return null;
  let text;
  try { text = fs.readFileSync(path.join(goalFolder, ...BUS_RELPATH), 'utf8'); } catch { return null; }
  const open = openOwnerAsks(text, seat).map((row) => row.id); // this seat's still-unanswered asks
  if (!open.length) return null;              // never asked, or every ask was answered on the bus
  // …minus the asks a previous turn of this seat was ALREADY HELD on (see the pairing note above).
  // A `blocked` row whose TURN was also `blocked` is a genuinely blocked turn, not a spent hold —
  // only a `done` turn is ever rewritten here, so that join is what tells the two apart (F3).
  const doneTurns = new Set();
  for (const row of heartStore.listExecutionsByStatus(DONE)) {
    if (row.session_id) doneTurns.add(row.session_id);
  }
  const spent = readExecutionRecord(goalFolder).rows
    .filter((r) => r.seat === seat && (r.outcome || '').trim() === BLOCKED && doneTurns.has(r['session-id']))
    .length;
  if (open.length <= spent) return null;
  const ask = open[spent];
  // THE RULING'S FORK. An ask the ferry PARKED can never be answered, so it does not hold: the seat
  // took its authored autonomous workaround and the wave continues (d-parked-ask-autonomous-workaround).
  const gate = askParkedAtGate(goalFolder, seat);
  if (gate) {
    return {
      parked: `asked the owner on the bus (row #${ask}) but the ferry PARKED it (gate: ${gate}) — nobody was told, `
        + `so nobody can answer. NOT held: the seat proceeds on its authored autonomous workaround and its `
        + `derivation belongs in this goal's decisions.md / doubts.md for review on return (d-s14-autonomous-dod).`,
      gate,
      ask,
    };
  }
  return {
    held: `asked the owner on the bus (row #${ask}), DELIVERED to his thread, and exited with no answer `
      + '— `fallback: block-and-queue`',
    ask,
  };
}

// THE OUTCOME A LANE PUBLISHES FOR A TERMINAL TURN. Identity for every status but `done`: a seat
// that failed, was killed or already ended `blocked` is not `done` anyway, so the hold has nothing
// to add to it. ONE function, because both close sites (the per-tick publish below and the attached
// lane's foreground carriage) must reach the same verdict — the ruling is the seat's declaration,
// not a property of the lane that ran it.
function outcomeForSeat(heartStore, goalFolder, seat, status) {
  if (status !== DONE) return { outcome: status, held: null, parked: null };
  const verdict = blockAndQueueVerdict(heartStore, goalFolder, seat);
  if (verdict && verdict.held) return { outcome: BLOCKED, held: verdict.held, parked: null };
  // The PARKED branch publishes the seat's REAL outcome — it finished its turn — and carries the
  // evidence so the report can say the seat proceeded on its workaround rather than saying nothing.
  return { outcome: status, held: null, parked: (verdict && verdict.parked) || null };
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
  const held = [];
  const proceeded = [];
  // WHICH ROWS ARE ALREADY PUBLISHED, read ONCE per goal per pass. `closeExecution` refuses a
  // second stamp on its own, so this is not correctness — it is what keeps the hold's bus read
  // (below) to ONE per ask instead of one per terminal row per tick, forever, for the whole life
  // of the goal. It also spares the lock on every already-closed row.
  const closedIds = new Map();
  const alreadyClosed = (goalFolder, sessionId) => {
    if (!closedIds.has(goalFolder)) {
      closedIds.set(goalFolder, new Set(readExecutionRecord(goalFolder).rows
        .filter((r) => (r.outcome || '').trim()).map((r) => r['session-id'])));
    }
    return closedIds.get(goalFolder).has(sessionId);
  };
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
      if (alreadyClosed(home.goalFolder, row.session_id)) continue;
      // THE HOLD IS DECIDED HERE, in the act that publishes the outcome (§ THE BLOCK-AND-QUEUE
      // HOLD): a `done` turn whose seat asked the owner and got no answer publishes `blocked`.
      const verdict = outcomeForSeat(heartStore, home.goalFolder, home.seat, row.status);
      const c = closeExecution({
        goalFolder: home.goalFolder,
        sessionId: row.session_id,
        outcome: verdict.outcome,
        endedAt: row.ended_at || '',
      });
      if (c.closed) {
        closed.push(`${home.seat}=${verdict.outcome}`);
        if (verdict.held) held.push({ seat: home.seat, goalFolder: home.goalFolder, evidence: verdict.held });
        if (verdict.parked) proceeded.push({ seat: home.seat, goalFolder: home.goalFolder, gate: verdict.gate, evidence: verdict.parked });
      }
    }
  }
  if (logger && (opened.length || closed.length)) {
    logger({ level: 'info', message: 'execution record published', opened, closed });
  }
  // LOUD, and per seat: the wave is now HELD on a human. An operator who cannot see this line
  // sees a run that simply stopped advancing.
  for (const h of held) {
    if (logger) {
      logger({
        level: 'warn',
        message: 'seat HELD — it asked the owner and exited; its record row says `blocked`, not `done`, so its '
          + 'dependents do NOT start. The owner\'s reply in the seat\'s thread revives it; `--relaunch` is the escape.',
        seat: h.seat,
        goalFolder: h.goalFolder,
        evidence: h.evidence,
      });
    }
  }
  // The AUTONOMOUS branch, reported as loudly as the held one and deliberately NOT as a warning:
  // this is the ruled normal path (`d-parked-ask-autonomous-workaround`), not a fault. What an
  // operator needs from it is the POINTER — this seat asked something nobody could answer and
  // proceeded on its own derivation, so the goal's ledgers are where that derivation is.
  for (const p of proceeded) {
    if (logger) {
      logger({
        level: 'info',
        message: 'seat PROCEEDED on its autonomous workaround — its ask was parked (gate: ' + p.gate + '), so the wave '
          + 'was NOT held. Its derivation belongs in this goal\'s decisions.md / doubts.md; review it on return.',
        seat: p.seat,
        goalFolder: p.goalFolder,
        evidence: p.evidence,
      });
    }
  }
  return { opened, closed, held, proceeded };
}

module.exports = {
  RECORD_FILENAME,
  COLUMNS,
  DONE,
  BLOCKED,
  FALLBACK_BLOCK_AND_QUEUE,
  blockAndQueueVerdict,
  openOwnerAsks,
  addressesSeat,
  askParkedAtGate,
  outcomeForSeat,
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
