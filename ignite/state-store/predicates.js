'use strict';

const { getCurrentEnding, getGoalState, getAsk } = require('./writers');
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
// on (`team-kit/ready.py`'s `HELD` row prints them). The WHERE clause is character-for-character
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
  listOpenAsks,
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
};
