'use strict';

// -- THE WRAPPED SPAWN DOOR'S ADMIT CHECKS AND ITS ONE ENQUEUE [spec-supervisor §5, T4-R7] ------
//
// WHERE THIS CAME FROM. `engine/seeding.js` `enqueueEligible` was retired as an owed-work computer
// (see `owed.js`), and it did not only compute: it also ran five pre-queue gates and then called
// `heartStore.enqueue` itself. The computer half moved to `deriveOwed`. THE GATES MOVED HERE, and
// spec-supervisor §5 says what they became — "launch-door refusals on the wrapped spawn", not a
// second owed set. A refusal answers "this launch does not happen"; it never answers "this seat is
// not owed work". The seat stays owed and the next cadence asks again, which is the behaviour the
// gates always had and the reason they must not be folded back into the computer.
//
// WHAT A REFUSAL IS NOT. Not an ending — a refused launch is not a dead seat, and stamping one
// would put a `failed` on a seat that never ran (`doors.js#refuseLaunch` states the same three
// absences for `E_GOAL_NOT_LIVE`). Not an envelope class either: `launch-refused` and the cage
// vocabulary are spec-envelope's, and this file quotes the envelope's own evidence string verbatim
// rather than minting a second word for it.
//
// THE ONE ENQUEUE. `launchThroughDoor` is the ONLY `heartStore.enqueue` call on the owed path.
// Seeding's and reconcile's launches both come through it, so `enqueued_by` (which is what
// `doors.js#doorForLauncher` turns back into a door name at the pid moment) can only ever be a
// value off the door list. Both callers used to enqueue independently; that is the second launch
// path the unification removes.
//
// ⚠ THE ADMISSION BRAKE IS INSIDE `HeartStore.enqueue()` AND MUST STAY REACHED (D52, memory
// `20260822-c-admission-brake-door`). It is fail-closed by design and has no opt-out; routing the
// owed path around it — a direct queue write, a "trusted caller" flag — reopens the 356-sitting
// burn it exists to bound. This file therefore calls `enqueue()` and reads its verdict; it never
// replaces it.

const REFUSED_DOOR = 'launch-admit';

// The refusal document. Same three assertions `doors.js#refuseLaunch` makes, because they are the
// same three facts: nothing was spawned, nothing was stamped, nothing was enqueued.
function refusal(kind, { seat = null, goal = null, evidence = '', ...extra } = {}) {
  return {
    refused: true,
    door: REFUSED_DOOR,
    kind,
    code: 'E_LAUNCH_REFUSED',
    goal,
    seat,
    evidence: String(evidence || ''),
    spawned: false,
    stamped: false,
    enqueued: false,
    ...extra,
  };
}

// ⚠ THE DISAGREEMENT REFUSAL, and it is the one that cost a live investigation (task 7.776). The
// store may DECLINE, never PROMOTE (§ D1): coord ruling a seat READY while this store holds an
// unfinished execution row for it is a refusal, not a launch — and, before it was named, not even
// a log line. `deriveOwed` carries the disagreement out of the computer; this turns it into the
// refusal an operator can actually read.
function storeDisagreeRefusal({ seat, goal = null, evidence }) {
  return refusal('store-disagree', { seat, goal, evidence });
}

// -- admitLaunch - the four pre-queue gates, in the order they always ran -----------------------
//
// Ordered exactly as the Python `enqueueEligible` replaced was, and then as `enqueueEligible`
// itself was: hold, cage admissibility, lane reach, boot prompt. No seat that would have been
// declined for an earlier reason is now declined for a later one.
//
// `admitDeclaredOutputs` / `admitLaneReach` are required lazily: they live in `engine/` (they are
// spec-envelope's subject and travel there with the component map), and a top-level require from
// `supervisor/` would close a load cycle through `seeding.js`.
function admitLaunch({
  seat, goal = null, goalFolder, isHeld = null,
  seatBinds = null, successorReads = [], workspaceRoot = null,
  promptFn,
}) {
  // THE HUMAN-INTERACTIVE DETACH, and it is stopped HERE rather than filtered earlier on purpose:
  // a held seat still blocks its dependents exactly as it would if it had been queued, so the wave
  // math must keep seeing it (console-run ruling 1 — such a seat is dispatched through the
  // foreground carrier or not at all).
  if (isHeld && isHeld(seat)) {
    return refusal('hold', {
      seat,
      goal,
      evidence: 'held for human-interactive detach (dispatched through the foreground carrier or not at all)',
    });
  }

  const { admitDeclaredOutputs, admitLaneReach } = require('../engine/cage-admission');

  // § D5 · CAGE ADMISSIBILITY. Could this seat actually WRITE its declared outputs once sandboxed,
  // and could a successor READING them read them? A row that declares a token the cage refuses
  // fails at the FAR end, after a launch, as a missing artifact marked against the seat's WORK —
  // when the truth is that its DECLARATION named a place it was never able to write.
  const declared = admitDeclaredOutputs({ seatBinds, goalFolder, seat, successorReads, workspaceRoot });
  if (declared) {
    return refusal('cage-admit', { seat, goal, evidence: declared, surface: true });
  }

  // D5 (seed-gates) · LANE REACH, the refusal beside the one above. Checks REACH (declaration/bind
  // present), never behavior (`exit 0`) — see `cage-admission.js#admitLaneReach` for the honest limit.
  const reach = admitLaneReach({ seatBinds, goalFolder, seat, workspaceRoot });
  if (reach) {
    return refusal('lane-reach', { seat, goal, evidence: reach, surface: true });
  }

  // THE BOOT PROMPT. Composed by coord, for THIS seat, from THIS goal's package — never here. A
  // seat queued without one boots a harness that exits immediately on empty input.
  const { prompt, reason } = promptFn(goalFolder, seat);
  if (prompt === null || prompt === undefined) {
    return refusal('boot-prompt', { seat, goal, evidence: reason || 'no-boot-prompt' });
  }

  return { refused: false, seat, goal, prompt };
}

// -- launchThroughDoor - the ONE enqueue on the owed path ---------------------------------------
//
// `enqueuedBy` is READ OFF the door list by the caller and passed through, never spelled here:
// that string is what travels (the queue row carries it as `enqueued_by`, `ticker.js#launchAgent`
// threads it into `spawn()`), and a second spelling of it is a launch that silently registers
// UNSUPERVISED.
//
// `reason` / `progressSignature` are threaded only when the caller has them. A caller that omits
// `reason` shares the door's merged floor budget (`door:__enqueue`) with every other reasonless
// caller at that (goal, seat) — which is STRICTER, and is the shape seeding's launches have always
// had. Inventing a reason for them here would silently widen their brake budget.
function launchThroughDoor({
  heartStore, seat, goal = null, jobId, args, enqueuedBy,
  sessionMode = 'headless', triggerKind = 'scheduled', runAt,
  onSeatBusy = null, reason = null, progressSignature = null,
}) {
  const req = { jobId, args, sessionMode, triggerKind, runAt, enqueuedBy };
  if (onSeatBusy) req.onSeatBusy = onSeatBusy;
  if (reason) req.reason = reason;
  if (progressSignature) req.progressSignature = progressSignature;

  const enq = heartStore.enqueue(req);

  // The store's own dedup — the sixth gate, on the far side of the door.
  if (enq && enq.deduped) {
    return {
      ...refusal('store-dedup', {
        seat,
        goal,
        evidence: `${enq.because} — queue_id=${enq.queue_id} exec_id=${enq.exec_id} held_status=${enq.held_status}`,
      }),
      enq,
    };
  }
  // D52 · the admission brake's own verdict. The typed `stuck` message still comes from the
  // watcher's `strike()`, never from the door (HeartStore must not import engine).
  if (enq && enq.braked) {
    return {
      ...refusal('braked', {
        seat,
        goal,
        evidence: `${enq.because} — attempts=${enq.attempts} signature=${enq.signature}`,
      }),
      enq,
    };
  }
  return { refused: false, ok: true, seat, goal, jobId, enq };
}

module.exports = { admitLaunch, launchThroughDoor, storeDisagreeRefusal, refusal, REFUSED_DOOR };
