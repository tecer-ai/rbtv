'use strict';

const { reasonFrom } = require('../server/spawn/seat-grants');

// ⚠ THE WORKSPACE HOME WINS OVER THE CALLER'S OWN STORE HANDLE, and the order matters more than it
// looks. Every production caller (`spawn.js`, `live-sessions.js`) passes BOTH a `heartStore` — the
// LANE store it happens to hold, `{data_root}/heart.db` in the daemon — and the `workspaceRoot`.
// Preferring the handle wrote this ending into a file no reader consults: `engine/ending-reads.js`
// resolves the ONE store from the goal's workspace (spec-state-store §1.1), and so does the kit's
// own door, so a launch-refusal stamped into the lane store was a `failed` nobody could see.
// The handle stays as the LAST resort — a caller with no workspace at all (the envelope selftest)
// still gets its row — and it is reached through `openEndingStore`, never a second `HeartStore`,
// because that class holds a process-wide writer slot the caller is already sitting in.
function stampLaunchRefused({ heartStore, workspaceRoot, dbPath, goal, seat, refuse }) {
  const { bind, endingStorePath, openEndingStore } = require('../state-store');
  const fields = {
    goal,
    seat,
    ending: 'failed',
    reason_class: 'launch-refused',
    evidence_pointer: reasonFrom(refuse),
    diagnostic: reasonFrom(refuse),
  };
  const home = dbPath || (workspaceRoot ? endingStorePath(workspaceRoot) : null);
  if (home) return bind(openEndingStore(home)).stampSystem(fields);
  if (heartStore && heartStore.db) return bind(heartStore.db).stampSystem(fields);
  throw new Error('stampLaunchRefused needs a workspaceRoot, a dbPath or an open store');
}

module.exports = { stampLaunchRefused };
