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
