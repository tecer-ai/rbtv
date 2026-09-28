'use strict';

const {
  getCurrentEnding, getGoalState, getAsk, getSeatHold,
} = require('./writers');
const { checkDoneOutputs } = require('./outputs-check');

function seatWaitingOnOwner(db, { goal, seat }) {
  const row = db.prepare(
    `SELECT 1 AS hit FROM open_asks
     WHERE goal = ? AND seat = ? AND state = 'open' AND posted = 1
     LIMIT 1`,
  ).get(goal, seat);
  return Boolean(row);
}

// §2.1 restated as a LIST rather than a count, for the reader that must NAME the asks it holds
// on (`coord/ready.py`'s `HELD` row prints them). The WHERE clause is character-for-character
// `seatWaitingOnOwner`'s, and that is the point: the boolean and the list are one predicate read
// two ways, so a row can never be held by one and clean by the other. Ordered by `posted_at` so
// two readers of the same goal print the same order.
// ⚠ `posted` DEFAULTS TO 1 AND THAT DEFAULT IS §2.1. Passing `posted: 0` (asks the owner was
// never told about) or `posted: null` (both) is a DIFFERENT question and never the wait predicate:
// an undelivered ask holds nothing, because no answer to it can ever arrive. The one caller that
// asks it — the check-out door's parked-ask note — says so at its own site.
function listOpenAsks(db, { goal, seat = null, posted = 1 }) {
  const where = ["goal = ?", "state = 'open'"];
  const params = [goal];
  if (posted !== null) { where.push('posted = ?'); params.push(Number(posted)); }
  if (seat) { where.push('seat = ?'); params.push(seat); }
  return db.prepare(
    `SELECT ask_id, goal, seat, label, posted, posted_at, evidence_pointer FROM open_asks
     WHERE ${where.join(' AND ')} ORDER BY posted_at, ask_id`,
  ).all(...params);
}

// EVERY open ask, ALL GOALS — the FLEET read the 2-hourly system digest renders (`spec-owner-io`
// §5: the ONE digest is SYSTEM-WIDE, so a per-goal question cannot answer it). The WHERE clause is
// `listOpenAsks`'s with the goal clause dropped and NOTHING else changed, which is the point: the
// digest and the per-goal wait predicate must never disagree about what an open ask is.
//
// ⚠ A SEPARATE FUNCTION, NOT `listOpenAsks({goal: null})`. §2.1's predicate is per-goal and its
// caller must NAME the goal it is asking about; making the goal optional there would turn a
// forgotten argument into a silent fleet-wide read. A different question gets a different name.
//
// ⚠ `posted` DEFAULTS TO 1 for `listOpenAsks`'s reason and it is the same default: an ask the
// owner was never told about is not one the digest may report as waiting on them.
function listAllOpenAsks(db, { posted = 1 } = {}) {
  const where = ["state = 'open'"];
  const params = [];
  if (posted !== null) { where.push('posted = ?'); params.push(Number(posted)); }
  return db.prepare(
    `SELECT ask_id, goal, seat, label, posted, posted_at, evidence_pointer FROM open_asks
     WHERE ${where.join(' AND ')} ORDER BY posted_at, ask_id`,
  ).all(...params);
}

// ── IS THIS SEAT UNDER A LIVE LEADER HOLD? ────────────────────────────────────────────────────
//
// THE ONE PREDICATE, for `seatWaitingOnOwner`'s reason: a hold that one reader honours and another
// does not is two sources for one fact. Returns the hold ROW (truthy) or null, so the caller can
// NAME what is holding the seat instead of only knowing that something is.
//
// The three release conditions, and each is answered from a row this store already keeps:
//   `release`      — nothing releases it but `supervise release`, which DELETES the row. Live while
//                    the row is there.
//   `new-ending`   — live while the seat's current ending still carries the `stamped_at` it carried
//                    when the leader ruled. Any re-stamp (the seat ran again, a leader accepted it,
//                    the daemon stamped it) moves that value and the hold is spent.
//   `ask-answered` — live while the NAMED ask is still `open`. That is §2.1's own mechanism and the
//                    same one `seatWaitingOnOwner` reads, so the answer arriving through
//                    `reapAndRelaunch` releases the hold on the next pass with no second watcher.
//
// ⚠ EVERY UNKNOWN ANSWERS "NOT HELD", and the direction is deliberate. An ask id that names no row,
// an ending that vanished, a hold whose word this build does not know: each fails OPEN, so the
// worst a broken hold can do is let the daemon do what it did before holds existed. The opposite
// default — hold on doubt — is a lane stopped forever by a typo.
function seatHeld(db, { goal, seat }) {
  const hold = getSeatHold(db, { goal, seat });
  if (!hold) return null;
  if (hold.until === 'release') return hold;
  if (hold.until === 'new-ending') {
    const current = getCurrentEnding(db, { goal, seat });
    const stamp = current ? String(current.stamped_at) : '';
    return stamp === String(hold.ending_stamped_at || '') ? hold : null;
  }
  if (hold.until === 'ask-answered') {
    const ask = getAsk(db, hold.ask_id);
    return (ask && ask.state === 'open') ? hold : null;
  }
  return null;
}

// Every LIVE hold on a goal, for the surface that must list them (`inspect asks`). Filtered through
// `seatHeld` rather than selected with its own WHERE clause: the liveness rule lives in exactly one
// function, and a list that applied a second copy of it would eventually disagree with the pass.
function listSeatHolds(db, { goal }) {
  const rows = db.prepare('SELECT seat FROM seat_holds WHERE goal = ? ORDER BY seat').all(goal);
  const out = [];
  for (const r of rows) {
    const live = seatHeld(db, { goal, seat: r.seat });
    if (live) out.push(live);
  }
  return out;
}

// Every seat name this goal has EVER stamped an ending row for — the complement of
// `getCurrentEnding`, which needs a seat name to look one row up. `owed-from-endings.js#classifyOwed`
// used to build its whole candidate universe from `sessions.csv` alone (`lastBySeat`'s keys), so a
// seat whose ending was stamped with no launch ever recorded for it (nothing in the daemon's own
// launch path does this — only an external/admin tool stamping an ending directly, or a hand-built
// fixture, can) was never a candidate: not excluded, never asked about. This is that missing
// question, asked at its one authoritative source.
function listSeatsWithEndings(db, { goal }) {
  return db.prepare('SELECT seat FROM seat_endings WHERE goal = ? ORDER BY seat').all(goal)
    .map((r) => r.seat);
}

function countOpenAsks(db, goal) {
  const row = db.prepare(
    `SELECT count(*) AS n FROM open_asks
     WHERE goal = ? AND state = 'open' AND posted = 1`,
  ).get(goal);
  return Number(row && row.n || 0);
}

function goalWaitingOnOwner(db, { goal, canAdvance }) {
  if (canAdvance) return false;
  return countOpenAsks(db, goal) > 0;
}

function isGoalPaused(db, goal) {
  const row = getGoalState(db, goal);
  return Boolean(row && row.stored === 'paused');
}

function isGoalRunning(db, goal) {
  const row = getGoalState(db, goal);
  return Boolean(row && row.stored === 'running');
}

function isGoalFinished(db, goal) {
  const row = getGoalState(db, goal);
  return Boolean(row && row.stored === 'finished');
}

function isLaunchable({ predecessorsDone, ending, armed, failedTerminal }) {
  if (!predecessorsDone) return false;
  if (failedTerminal) return false;
  if (ending == null) return true;
  if (ending === 'incomplete' && Number(armed) === 1) return true;
  if (ending === 'failed' && !failedTerminal) return true;
  return false;
}

function killClockPauses(db, { goal, seat, providerBackoff }) {
  if (providerBackoff) return true;
  if (seatWaitingOnOwner(db, { goal, seat })) return true;
  const current = getCurrentEnding(db, { goal, seat });
  if (current && current.ending === 'incomplete' && Number(current.armed) === 0) return true;
  return false;
}

module.exports = {
  seatWaitingOnOwner,
  seatHeld,
  listSeatHolds,
  listSeatsWithEndings,
  listOpenAsks,
  listAllOpenAsks,
  goalWaitingOnOwner,
  countOpenAsks,
  isGoalPaused,
  isGoalRunning,
  isGoalFinished,
  isLaunchable,
  checkDoneOutputs,
  killClockPauses,
  getCurrentEnding,
  getGoalState,
  getAsk,
  getSeatHold,
};
