'use strict';

const { reasonFrom } = require('../server/spawn/seat-grants');

function stampLaunchRefused({ heartStore, workspaceRoot, dbPath, goal, seat, refuse }) {
  const { bind, endingStorePath } = require('../state-store');
  const fields = {
    goal,
    seat,
    ending: 'failed',
    reason_class: 'launch-refused',
    evidence_pointer: reasonFrom(refuse),
    diagnostic: reasonFrom(refuse),
  };
  if (heartStore && heartStore.db) return bind(heartStore.db).stampSystem(fields);
  const { openHeartStore, closeHeartStore } = require('../server/heart/heart-store');
  const heart = openHeartStore({ dbPath: dbPath || endingStorePath(workspaceRoot) });
  try {
    return bind(heart.db).stampSystem(fields);
  } finally {
    heart.close();
    closeHeartStore();
  }
}

module.exports = { stampLaunchRefused };
