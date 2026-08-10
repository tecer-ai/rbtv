'use strict';

// engine/seeding.js — SEEDING A GOAL'S TASKFORCE, for whichever lane is doing it.
//
// This is the code that used to live inside `attached-execution.js`, unchanged in behaviour and
// moved for ONE reason: it was never attached-lane machinery. It reads `taskforce.csv`, registers
// one job per seat, and enqueues the seats whose turn it is — none of which is a property of the
// terminal the run is attached to. It lived there because the attached lane was its only caller,
// and that accident is exactly what the B3 probe measured as "the daemon lane has no path that
// seeds a goal's taskforce into its own store" (owner ruling
// decisions.md#d-s23-single-execution-record-now, criterion 2).
//
// TWO THINGS ARE NEW HERE, and both exist because a SECOND store may now do this:
//
//  1. THE COMPLETION AUTHORITY IS THE GOAL'S EXECUTION RECORD (`execution-record.js`), not the
//     store. `seatState` answers `done` from `<goal>/executions.csv` FIRST, and only then from the
//     rows the caller's own store carries. The store half stays because it is the local
//     no-double-fire guard create-only seeding has always been — it can only ADD done-ness, so the
//     union can never cause a double run, only decline to re-run something a lane already ran.
//
//  2. THE JOB-ID NAMESPACE. `seat-<name>` is unique inside a per-goal store and is NOT unique
//     inside the daemon's single store, which holds every goal it serves — two goals with a seat
//     named `alpha` would collide there and silently share one job row. So a caller whose store is
//     shared passes `goal`, and the id becomes `seat-<goal>-<name>`. The attached lane passes
//     nothing and its ids are byte-identical to what it has always written, so every goal already
//     on disk resumes exactly as before. Cross-lane identity does NOT ride on this id — it rides on
//     the seat name in the shared record, which is the whole reason that record exists.

const fs = require('node:fs');
const path = require('node:path');
const { readExecutionRecord, finishedSeats, DONE, BLOCKED } = require('./execution-record');

const TASKFORCE = 'taskforce.csv';

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

// Minimal CSV read — the taskforce file is written by `rbtv goal` with plain comma-joined fields
// and no embedded commas or quotes. Reading it with a general CSV parser would be a dependency
// bought for a shape this repo already writes by hand (goal_cli.py write_csv).
function readCsv(file) {
  const text = fs.readFileSync(file, 'utf8');
  const lines = text.split('\n').filter((l) => l.trim().length);
  if (!lines.length) return [];
  const cols = lines[0].split(',').map((c) => c.trim());
  return lines.slice(1).map((line) => {
    const cells = line.split(',');
    const row = {};
    cols.forEach((c, i) => { row[c] = (cells[i] === undefined ? '' : cells[i]).trim(); });
    return row;
  });
}

function taskforcePath(goalFolder) {
  return path.join(goalFolder, TASKFORCE);
}

function readTaskforce(goalFolder) {
  const tfPath = taskforcePath(goalFolder);
  if (!fs.existsSync(tfPath)) {
    throw new Error(
      `${tfPath}: no taskforce — a run executes the run's seats, and the taskforce is ` +
      `where they are declared (CMP-4 goals tree). Nothing to run.`
    );
  }
  const rows = readCsv(tfPath).filter((r) => r.seat);
  if (!rows.length) throw new Error(`${tfPath}: no seat rows`);
  return rows;
}

// ── WHAT THE RECORD SAYS ABOUT EACH SEAT, from the perspective of THIS store ──────────────────
//
// Two answers, not one, and the second is the review finding F3/F6 this exists to close.
//
//   done      the record carries a `done` outcome for the seat. Nobody re-runs it.
//   foreign   the record carries a row for the seat that THIS STORE HAS NO EXECUTION FOR, and that
//             row is not `done` — either still OPEN (a seat live in the other lane RIGHT NOW) or
//             ended non-`done` (failed / blocked / killed elsewhere).
//
// WHY `foreign` HAS TO EXIST AT ALL. Without it the record only ever stopped a re-run when the
// other lane had already FINISHED — so a seat the other lane was in the middle of running read
// `ready` here and was dispatched a second time, concurrently. The at-dispatch row was being
// written and read by nothing; the whole point of writing it at dispatch is that the other lane can
// see the seat is taken. And on the terminal-non-`done` side the two lanes were ASYMMETRIC: a
// locally failed seat needs an explicit `--relaunch` grant, while the same failure in the other
// lane was invisible and re-ran silently — conferring the grant nobody gave. `foreign` makes both
// cases behave like the local one: the seat is not `ready`, and an explicit grant is what releases
// it.
//
// ⚠ THE MEMBERSHIP TEST IS THE SESSION-ID JOIN, NOT THE `lane` COLUMN. `lane` says which KIND of
// store wrote the row (CMP-2), and two attached runs on two machines share that value — so a lane
// comparison would call another machine's live seat "ours" and dispatch it again. What actually
// answers "is this row mine" is whether an execution in THIS store owns that session id, which is
// the same join the retired v1 guard used and the one honest thing it had.
//
// ⚠ THE DISCLOSED BOUND: a foreign writer that CRASHED leaves its row open, and this holds the seat
// until that lane republishes. That is not a dead end — the other lane's next boot runs the
// adoption pass, which stamps the row from its own store (a crashed foreground row reconciles to
// `failed`, a killed detached one to `failed`/`killed`) and the seat becomes grantable. The operator
// path when that lane will never run again: `--relaunch <seat>`, which is the same explicit act a
// local failure already requires. Holding is the safe direction — the unsafe one is running a seat
// somebody else may still be running.
//
// ── AND A THIRD: `notFinished` — THE RECORD'S LAST WORD (owner ruling
// decisions.md#d-block-and-queue-mechanical-hold, which also closes the 7.626 review's F6) ─────
//
//   notFinished   the seat's LAST row in the record is not a finish — it is either still OPEN (a
//                 session is running for this seat RIGHT NOW) or it ended `blocked`. Either way the
//                 seat is NOT done, and — this is the part that needed code — an EARLIER `done`
//                 row, or the store's own `done` turn, does not make it done either.
//
// TWO FACTS RIDE ONE SET, because they are the same fact: `done` has always been "any row says
// done", which is right for the cross-lane no-double-run guarantee and WRONG as an answer to "is
// this seat finished now". F6 measured the difference: the chat revival opens a SECOND row for a
// seat whose first row is `done`, and the `done` row outranked it — so `--status` reported the seat
// done while a live session ran in its home, and the dependents that `done` released ran CONCURRENT
// with it. The last word settles both that and the hold, with one rule instead of two.
//
// And the HOLD is the `blocked` half of it: a `block-and-queue` seat that asked the owner and
// exited 0 has a store turn of `done` (the process really did exit) and a record row of `blocked`
// (`execution-record.js` § THE BLOCK-AND-QUEUE HOLD, where the word is decided). The record is THE
// completion authority, so its word wins over the store's — the sentence this file already opens
// with, now true in the direction that REMOVES done-ness as well.
//
// Derived, not stored: the last row per seat, out of the same file `done` and `foreign` come from.
// A LATER row clears it — which is exactly what the owner's answer mints (a revival session at the
// seat's home), so the hold releases through machinery that already existed. A `--relaunch` grant
// clears it for the same reason it clears `foreign`: an explicit human act.
function recordView(heartStore, goalFolder, { relaunch = null } = {}) {
  const rows = readExecutionRecord(goalFolder).rows;
  const done = new Set();
  const foreign = new Map();
  const notFinished = new Map();
  const blocked = new Map();
  if (!rows.length) return { done, finished: done, foreign, notFinished, blocked };

  // The seat's LAST row, in file order — the record is append-only, so the last row for a seat is
  // its most recent execution. `failed`/`killed` are terminal words that were never `done`; they
  // keep the behaviour they had (the seat is not done and an explicit grant re-runs it), so only
  // the two non-finishes below are collected here.
  const last = new Map();
  for (const r of rows) last.set(r.seat, r);
  for (const [seat, r] of last) {
    const outcome = (r.outcome || '').trim();
    if (outcome === BLOCKED) {
      blocked.set(seat, `its last execution ended '${BLOCKED}' — the seat is waiting on an answer, so its dependents wait with it`);
      notFinished.set(seat, blocked.get(seat));
    } else if (!outcome) {
      notFinished.set(seat, `its last execution is still OPEN in the ${r.lane || 'other'} lane (session ${r['session-id']})`);
    }
  }

  // A NULL store is the `--status` case on a goal this lane has never run: nothing is ours, so
  // every non-done row is somebody else's — which is exactly what is true there.
  const ours = new Set();
  if (heartStore) {
    for (const status of ALL_TURN_STATUSES) {
      for (const row of heartStore.listExecutionsByStatus(status)) {
        if (row.session_id) ours.add(row.session_id);
      }
    }
  }
  for (const r of rows) {
    const outcome = (r.outcome || '').trim();
    if (outcome === DONE) { done.add(r.seat); continue; }
    if (ours.has(r['session-id'])) continue;            // our own store already governs this one
    foreign.set(r.seat, outcome
      ? `ended '${outcome}' in the ${r.lane || 'other'} lane (session ${r['session-id']})`
      : `still OPEN in the ${r.lane || 'other'} lane (session ${r['session-id']})`);
  }
  // ── `finished` — "IS THIS SEAT DONE **NOW**", AND THE ONE ANSWER EVERY OUTRANKING TEST TAKES ──
  //
  // ⚠ THIS SET EXISTS BECAUSE `done` AND `notFinished` ARE INDEPENDENT, AND EVERY TEST THAT USED TO
  // WRITE `done.has(seat)` MEANT THIS. `done` is "ANY row says done" — the cross-lane no-double-run
  // guarantee, which must stay any-row. `notFinished` is the LAST row. Between them sits the seat
  // this build created: rows `done, blocked` or `done, open`, which `done` calls finished and the
  // last word calls not. Review findings F1 and F2 were both that gap, at the two call sites below
  // — the review's own words, a signature change that did not sweep its callers.
  //
  //   F1 (HIGH): the relaunch grant bailed on `done.has(seat)`, so `--relaunch` was a NO-OP for a
  //   seat held on its SECOND ask (`blocked, done, blocked`) — the documented escape did nothing
  //   and hand-editing `executions.csv` was the only way out of a permanently stuck wave.
  //   F2: the `foreign` deletion did the same, so a crashed foreign revival (`done, open`) was
  //   reported by NOTHING while `skippedAsFinished` called it finished and `states` called it live.
  //
  // Computed BEFORE the grant's deletes, so a grant can never make a seat read finished.
  const finished = new Set([...done].filter((seat) => !notFinished.has(seat)));

  // A later `done` outranks an earlier non-done row for the same seat: the seat IS finished — but
  // only when `done` IS the last word (see above). An OPEN or `blocked` row after it is the seat's
  // current state and outranks the older `done`.
  for (const seat of finished) foreign.delete(seat);
  // The one-shot relaunch grant releases a foreign hold exactly as it releases a local failure —
  // and, exactly as there, it can never release a FINISHED seat. It releases the record's last-word
  // hold too: an operator saying "run this seat again" is the same explicit act, and the answer
  // that would otherwise release it is the one thing he is saying will not come.
  if (relaunch) {
    for (const seat of relaunch) {
      if (finished.has(seat)) continue;
      foreign.delete(seat);
      notFinished.delete(seat);
      blocked.delete(seat);
    }
  }
  return { done, finished, foreign, notFinished, blocked };
}

function jobIdFor(seat, goal = null) {
  return goal ? `seat-${goal}-${seat}` : `seat-${seat}`;
}

// ── Seeding: the taskforce IS the workflow ────────────────────────────────────────────────────
//
// `taskforce.csv` already carries one row per seat with an `after` column naming the seat it
// follows. That column IS the wave structure — nothing new is invented here, and no second
// scheduler is written: seeding only decides WHICH seats are eligible now, and the ticker decides
// what actually launches and how many run at once (`max_live_agent_sessions` — the parallel wave).
//
// The PROFILE is not derived from the row's `harness`/`model`. Mapping an elected (model, variant)
// onto exactly one profile NAME is task 7.54's catalog, and inventing a second mapping here is the
// drift that DEC-1's shared-profile-source ruling exists to prevent. So the profile is passed by
// NAME by the caller, resolved from the ONE shared config.
function seedTaskforce(heartStore, goalFolder, { profile, logger, goal = null }) {
  const rows = readTaskforce(goalFolder);

  // CREATE-ONLY, and that is what makes a re-run a RESUME rather than a replay. registerJob is
  // create-only in the store (it throws E_JOB_EXISTS); a second boot finds every job already
  // registered and registers nothing.
  for (const row of rows) {
    const jobId = jobIdFor(row.seat, goal);
    if (heartStore.getJob(jobId)) continue;
    heartStore.registerJob({
      jobId,
      actionType: 'launch-agent',
      function: `attached-execution seat ${row.seat}`,
      // `required`/`optional` are OBJECTS of name -> type, not arrays — the store parses them
      // that way (parseArgsSchema) and REFUSES an array. Registration is strict on purpose: a
      // schema a future enqueue could never satisfy is what campaign issue S-2(a) was.
      argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { workdir: 'string', prompt: 'string' } }),
      description: `seat ${row.seat} of ${row.taskforce_id || row['taskforce-id'] || 'this run'}`,
      createdAt: isoNow(),
      updatedAt: isoNow(),
    });
    if (logger) logger({ level: 'info', message: 'registered seat job', jobId, seat: row.seat });
  }
  return rows;
}

// The execution picture, read ONCE per pass from the store's own partition of jobs_log.
//
// `relaunch` is the ONE-SHOT RELAUNCH GRANT (console-run B1): a seat named in it is presented to
// the predicate WITHOUT its execution history, so a seat whose last attempt died reads `ready`
// again. The grant hides the rows from THIS VIEW only — nothing in the store is rewritten, so the
// failed attempt stays on the record it was written to. A FINISHED seat is never hidden: a grant
// must not be able to re-run completed work, and that is enforced here rather than trusted to the
// caller who typed the seat name. (Nor can a grant re-open a seat the RECORD calls done — that
// check is in `seatState`, ahead of everything the grant can touch.)
const ALL_TURN_STATUSES = ['launching', 'running', 'done', 'blocked', 'failed', 'stalled', 'killed'];

function executionsByJob(heartStore, relaunch = null, goal = null) {
  const byJob = new Map();
  for (const status of ALL_TURN_STATUSES) {
    for (const row of heartStore.listExecutionsByStatus(status)) {
      const list = byJob.get(row.job_id) || [];
      list.push(row);
      byJob.set(row.job_id, list);
    }
  }
  if (relaunch) {
    for (const seat of relaunch) {
      const jobId = jobIdFor(seat, goal);
      if (!seatIsFinished(byJob.get(jobId))) byJob.delete(jobId);
    }
  }
  return byJob;
}

function seatIsFinished(rows) {
  return Boolean(rows) && rows.some((r) => r.status === 'done');
}

function seatHasRun(rows) {
  return Boolean(rows) && rows.length > 0;
}

// THE ELIGIBILITY PREDICATE, in ONE place. Both the enqueue pass and the read-only status verb
// answer "what is this seat's state right now" from here — a second copy of the wave math is a
// status surface that can disagree with the engine it reports on, which is worse than no surface.
//
//   done     the goal's execution record says so, or a finished execution exists in this store
//   live     an execution exists that has not finished (running / stalled / failed / …)
//   queued   a pending queue row exists
//   ready    never fired, and its `after` is done — the next thing the engine enqueues
//   waiting  never fired, and its `after` is not done
//
// `done` is a Set of seat names from `<goal>/executions.csv` — THE completion authority, and the
// one arm that makes a seat finished in one lane invisible-to-re-running in the other. It is
// optional so a caller with no goal folder in hand (a probe exercising the wave math on a
// hand-built map) still gets the store-only answer it always got.
const SEAT_STATES = ['done', 'live', 'queued', 'ready', 'waiting'];

// `notFinished` is the MECHANICAL HOLD (and the F6 fix), applied INSIDE `isDone` rather than as a
// state of its own — deliberately, and it is the whole ruling in one line. A held seat is not done,
// and neither is it done FOR ITS DEPENDENTS: `isDone(after)` is the same call, so the wave stops
// with no second rule to keep in step. No sixth seat state is minted: such a seat reads `live` for
// the same reason a foreign one does — it is neither dispatchable nor finished, and every reader of
// SEAT_STATES already understands that pair. WHY it is not moving is reported alongside the state
// (`seedGoal().blockedOnOwner`, `statusAttached()`'s `blockedOnOwner` flag), never as a state word.
function seatState(row, byJob, queued, { done = null, goal = null, foreign = null, notFinished = null } = {}) {
  const isDone = (seat) => !(notFinished && notFinished.has(seat))
    && ((done && done.has(seat)) || seatIsFinished(byJob.get(jobIdFor(seat, goal))));
  if (isDone(row.seat)) return 'done';
  if (notFinished && notFinished.has(row.seat)) return 'live';
  const jobId = jobIdFor(row.seat, goal);
  // A seat the record shows running-or-ended-badly ELSEWHERE is `live` here — the same word the
  // local answer uses for exactly the same situation, so no reader learns a sixth state and no
  // caller can treat "live over there" as dispatchable.
  if (foreign && foreign.has(row.seat)) return 'live';
  if (seatHasRun(byJob.get(jobId))) return 'live';
  if (queued.has(jobId)) return 'queued';
  const after = (row.after || '').trim();
  if (after && !isDone(after)) return 'waiting';
  return 'ready';
}

// Enqueue every seat whose `after` dependency has finished and which has never been fired. Returns
// the seats enqueued this pass.
//
// `isHeld` is the ONE place the engine can DETACH a human-interactive seat, and it is where it is
// stopped (console-run ruling 1: such a seat is dispatched through the foreground carrier or not at
// all). Skipping it here rather than filtering the rows earlier keeps the wave math on the WHOLE
// taskforce — a held seat still blocks its dependents exactly as it would if it had been queued.
function enqueueEligible(heartStore, rows, {
  profile, goalFolder, logger, isHeld = null, relaunch = null, goal = null, view = null,
}) {
  const byJob = executionsByJob(heartStore, relaunch, goal);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  const { done: finished, foreign, notFinished, blocked } = view || recordView(heartStore, goalFolder, { relaunch });
  const enqueued = [];

  for (const row of rows) {
    const jobId = jobIdFor(row.seat, goal);
    if (foreign && foreign.has(row.seat) && logger) {
      logger({ level: 'info', message: 'seat held — the execution record shows it elsewhere', seat: row.seat, evidence: foreign.get(row.seat) });
    }
    if (blocked && blocked.has(row.seat) && logger) {
      logger({ level: 'info', message: 'seat held — it is BLOCKED on the owner and its dependents wait with it', seat: row.seat, evidence: blocked.get(row.seat) });
    }
    if (seatState(row, byJob, queued, { done: finished, goal, foreign, notFinished }) !== 'ready') continue;
    if (isHeld && isHeld(row.seat)) continue;
    if (relaunch) relaunch.delete(row.seat);

    const after = (row.after || '').trim();
    const seatDir = path.join(goalFolder, 'seats', row.seat);
    heartStore.enqueue({
      jobId,
      args: JSON.stringify({ profile, workdir: seatDir }),
      sessionMode: 'headless',
      triggerKind: 'scheduled',
      runAt: isoNow(),
      enqueuedBy: 'attached-execution',
    });
    enqueued.push(row.seat);
    if (logger) logger({ level: 'info', message: 'enqueued seat', seat: row.seat, after: after || null });
  }
  return enqueued;
}

// ── THE DAEMON LANE'S PICKUP (criterion 2 of #d-s23-single-execution-record-now) ──────────────
//
// One call: read the goal's execution record, seed the taskforce into THIS store, enqueue the seats
// whose turn it is — skipping every seat the record says is finished, whichever lane finished it.
// The attached lane reaches the same two functions directly (it also owns a foreground carriage
// this does not); a shared store reaches them through here, with the namespace argument set.
//
// It is deliberately a FUNCTION AND NOT A TRIGGER. What tells the daemon to pick a goal up is a
// separate, owner-facing question — arming is per-package today (edge-fastpath) and deliberately
// unreachable from a flag — and answering it by, say, seeding every goal folder the daemon can see
// would be a policy this build was not asked to invent. `engine.seedGoal()` is the seam; the caller
// that fires it is named in the contract as the follow-on.
function seedGoal({ heartStore, goalFolder, profile, goal, logger = null, isHeld = null, relaunch = null }) {
  if (!goal) {
    throw new Error(
      'seedGoal requires the goal NAME: it namespaces the job ids so two goals with a seat of the ' +
      'same name cannot share one job row in a store that holds every goal (the daemon\'s).'
    );
  }
  const view = recordView(heartStore, goalFolder, { relaunch });
  const rows = seedTaskforce(heartStore, goalFolder, { profile, logger, goal });
  const enqueued = enqueueEligible(heartStore, rows, { profile, goalFolder, logger, goal, view, isHeld, relaunch });
  const byJob = executionsByJob(heartStore, null, goal);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  const seats = rows.map((r) => r.seat);
  return {
    goalFolder,
    goal,
    seats,
    // ⚠ `finished`, NOT `done` (review F2): a seat with a `done` row and a LATER open or `blocked`
    // one was reported here as FINISHED while `states` said `live` — one report contradicting the
    // other, about the seat this build exists to hold.
    skippedAsFinished: seats.filter((s) => view.finished.has(s)),
    // Named separately from `skippedAsFinished` because the two are different facts and an operator
    // must be able to tell them apart: one seat is DONE, the other is somebody else's right now.
    // Since F2 this also carries the seat whose LAST row is somebody else's OPEN one — a crashed
    // foreign revival used to be deleted from this map by an older `done` row and reported nowhere.
    heldByOtherLane: Object.fromEntries(seats.filter((s) => view.foreign.has(s)).map((s) => [s, view.foreign.get(s)])),
    // The THIRD held-for-a-reason set, named separately for the same reason the second is: an
    // operator must be able to tell "somebody else is running it" from "it is waiting on YOU".
    blockedOnOwner: Object.fromEntries(seats.filter((s) => view.blocked.has(s)).map((s) => [s, view.blocked.get(s)])),
    enqueued,
    states: Object.fromEntries(rows.map((r) => [r.seat, seatState(r, byJob, queued, { done: view.done, goal, foreign: view.foreign, notFinished: view.notFinished })])),
  };
}

module.exports = {
  TASKFORCE,
  ALL_TURN_STATUSES,
  SEAT_STATES,
  readCsv,
  taskforcePath,
  readTaskforce,
  jobIdFor,
  seedTaskforce,
  executionsByJob,
  seatIsFinished,
  seatHasRun,
  seatState,
  recordView,
  enqueueEligible,
  seedGoal,
};
