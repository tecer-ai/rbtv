'use strict';

// -- THE ONE OWED-WORK COMPUTER [spec-supervisor §5, T4-R7, C-15, T1-R3] -----------------------
//
// WHAT WAS BROKEN. Two functions answered "is this seat owed a launch?", on two cadences, from two
// different pictures, and both of them called `heartStore.enqueue` (CODE-GROUND-TRUTH §4):
//
//   * `supervisor/seeding.js` `enqueueEligible` — ~10 s. Graph half: whose `after` is satisfied and who
//     has never fired. It carried five extra pre-queue gates of its own (store-disagree, hold, cage
//     admit, lane reach, boot prompt) and a sixth on the far side of the door (the store's dedup).
//   * `supervisor/reconcile.js` `classifyOwedFromLedgers` — ~300 s. Ledger half: class A (a seat whose
//     last ending is non-terminal) and class B (a chair with unread mail).
//
// They could disagree, and when they did nothing could say which was right: a seat "not owed" by
// one and "owed" by the other simply behaved differently depending on which cadence fired. There
// was no third surface to appeal to, because there was no ONE owed set anywhere.
//
// THE RULE [spec-supervisor §5]. `deriveOwed` is the survivor and it is the single "this seat is
// owed a launch" function. Graph-derived launchability [T1-R3] lands HERE, on the survivor — it is
// class R below, and it is the half that used to live inside `enqueueEligible`. Seeding retired as
// a COMPUTER: it still runs its own fast cadence, but it asks this function what is owed instead of
// working it out a second time, and it launches through the wrapped spawn door instead of
// enqueuing. That is the whole unification: ONE computer, and (see `launch-door.js`) ONE enqueue.
//
// WHAT THIS FUNCTION MUST NEVER DO. It must never call `heartStore.enqueue`. An owed set is a
// STATEMENT, not an act — the moment the computer can also launch, a second launch path exists by
// construction and the property this file was written to hold is gone. `reconcile.selftest.js`
// `single owed computer` asserts exactly that against this file's source.

const { classifyOwed } = require('./owed-from-endings');

const EMPTY_LEDGER = Object.freeze({
  seats: [],
  live: [],
  deadSeats: [],
  summonedSeats: [],
  classA: [],
  classB: [],
  classE: null,
  readyRefused: null,
  owed: false,
});

// -- CLASS R - graph-derived launchability [T1-R3] ----------------------------------------------
//
// `seatState` is the ONE state predicate and it moved here from `seeding.js` with its behaviour
// untouched: the wave arithmetic IS the owed question for the graph half, so leaving it in seeding
// would have left half the computer behind. Seeding and the attached lane both re-export it, so no
// caller learns a new name for a predicate that did not change.
//
// ⚠ `ready` IS COORD'S ANSWER, HANDED IN — never derived here (§ D1). Absent (a caller that could
// not ask, or did not) means NO seat is ready: the store may decline, never promote. That is the
// whole asymmetry, in one default.
function seatState(row, byJob, queued, {
  done = null, goal = null, foreign = null, notFinished = null, ready = null,
  jobIdFor = null, seatIsFinished = null, seatHasRun = null,
} = {}) {
  const jobId = jobIdFor(row.seat, goal);
  const isDone = (seat) => !(notFinished && notFinished.has(seat))
    && ((done && done.has(seat)) || seatIsFinished(byJob.get(jobIdFor(seat, goal))));
  if (isDone(row.seat)) return 'done';
  if (notFinished && notFinished.has(row.seat)) return 'live';
  // A seat the record shows running-or-ended-badly ELSEWHERE is `live` here — the same word the
  // local answer uses for exactly the same situation, so no reader learns a sixth state and no
  // caller can treat "live over there" as dispatchable.
  if (foreign && foreign.has(row.seat)) return 'live';
  if (seatHasRun(byJob.get(jobId))) return 'live';
  if (queued.has(jobId)) return 'queued';
  return ready && ready.has(row.seat) ? 'ready' : 'waiting';
}

// The graph half of the owed set. Returns the launchable seats AND the one disagreement an
// operator cannot reconstruct from any other surface.
//
// ⚠ THE DISAGREEMENT IS NOT A SILENT DROP (task 7.776). coord answered READY, this store's own
// `seatHasRun` answered `live` off a `failed` execution row, and the seat vanished from the pass
// with nothing said anywhere — an 18-hour stall. It is named here, carried out of the computer,
// and turned into a launch-door refusal by the caller. Every other state word (`done`, `queued`,
// `waiting`) is ordinary and stays quiet.
function deriveLaunchable({
  rows = [], byJob, queued, view = null, ready = null, goal = null,
  jobIdFor, seatIsFinished, seatHasRun,
}) {
  const opts = {
    done: view && view.done, goal, foreign: view && view.foreign,
    notFinished: view && view.notFinished, ready,
    jobIdFor, seatIsFinished, seatHasRun,
  };
  const states = {};
  const classR = [];
  const disagreements = {};
  for (const row of rows) {
    const state = seatState(row, byJob, queued, opts);
    states[row.seat] = state;
    if (state === 'ready') {
      classR.push({ seat: row.seat, reason: 'ready', source: 'r', after: (row.after || '').trim() });
      continue;
    }
    if (state === 'live' && ready && ready.has(row.seat)) {
      disagreements[row.seat] = 'coord says READY, this store says `live` — an execution row exists '
        + 'here that has not finished';
    }
  }
  return { classR, states, disagreements };
}

// -- deriveOwed - the survivor ------------------------------------------------------------------
//
// Both halves are optional because the two cadences ask different questions of the same computer:
// the watcher (~300 s) hands in `ledger` and reads classes A/B/E; seeding (~10 s) hands in `graph`
// and reads class R. Handing in both yields the whole owed set. What neither caller may do is
// compute either half itself — that is the state this file exists to make unreachable.
//
// The readers are injected rather than required, exactly as `classifyOwed` already took them: this
// module lives under `supervisor/` and the record readers live under `engine/`, and a top-level
// require in this direction would close a cycle through `seeding.js`.
function deriveOwed(goalFolder, opts = {}) {
  const { ledger = null, graph = null } = opts;
  const fromLedgers = ledger
    ? classifyOwed(goalFolder, { ...opts, ...ledger })
    : { ...EMPTY_LEDGER };
  const { classR, states, disagreements } = graph
    ? deriveLaunchable({ ...opts, ...graph })
    : { classR: [], states: {}, disagreements: {} };
  return {
    ...fromLedgers,
    classR,
    states,
    disagreements,
    owed: Boolean(fromLedgers.owed) || classR.length > 0,
  };
}

module.exports = { deriveOwed, seatState, deriveLaunchable };
