'use strict';

const errors = require('./errors');
const vocabulary = require('./vocabulary');
const paths = require('./paths');
const writers = require('./writers');
const predicates = require('./predicates');
const { copyHeartHome, OPERATIONAL_TABLES } = require('./copy-home');
const { checkDoneOutputs } = require('./outputs-check');
const open = require('./open');

function bind(db) {
  return {
    stampSeatDeclare: (fields) => writers.stampSeatDeclare(db, fields),
    stampSystem: (fields) => writers.stampSystem(db, fields),
    replaceSeatEnding: (fields) => writers.replaceSeatEnding(db, fields),
    writeGoalWord: (fields) => writers.writeGoalWord(db, fields),
    insertAsk: (fields) => writers.insertAsk(db, fields),
    postAsk: (fields) => writers.postAsk(db, fields),
    reapAndRelaunch: (fields) => writers.reapAndRelaunch(db, fields),
    incrementRecoveryRelaunch: (fields) => writers.incrementRecoveryRelaunch(db, fields),
    setLeaderAttemptUsed: (fields) => writers.setLeaderAttemptUsed(db, fields),
    fireNamedEvent: (fields) => writers.fireNamedEvent(db, fields),
    holdSeat: (fields) => writers.holdSeat(db, fields),
    releaseSeat: (fields) => writers.releaseSeat(db, fields),
    getSeatHold: (fields) => writers.getSeatHold(db, fields),
    getCurrentEnding: (fields) => writers.getCurrentEnding(db, fields),
    getGoalState: (goal) => writers.getGoalState(db, goal),
    getAsk: (askId) => writers.getAsk(db, askId),
    seatWaitingOnOwner: (fields) => predicates.seatWaitingOnOwner(db, fields),
    seatHeld: (fields) => predicates.seatHeld(db, fields),
    listSeatHolds: (fields) => predicates.listSeatHolds(db, fields),
    listOpenAsks: (fields) => predicates.listOpenAsks(db, fields),
    listAllOpenAsks: (fields) => predicates.listAllOpenAsks(db, fields || {}),
    goalWaitingOnOwner: (fields) => predicates.goalWaitingOnOwner(db, fields),
    countOpenAsks: (goal) => predicates.countOpenAsks(db, goal),
    isGoalPaused: (goal) => predicates.isGoalPaused(db, goal),
    isGoalRunning: (goal) => predicates.isGoalRunning(db, goal),
    isGoalFinished: (goal) => predicates.isGoalFinished(db, goal),
    killClockPauses: (fields) => predicates.killClockPauses(db, fields),
    isLaunchable: predicates.isLaunchable,
    checkDoneOutputs,
  };
}

module.exports = {
  bind,
  ...errors,
  ...vocabulary,
  ...paths,
  ...open,
  ...writers,
  ...predicates,
  checkDoneOutputs,
  copyHeartHome,
  OPERATIONAL_TABLES,
};
