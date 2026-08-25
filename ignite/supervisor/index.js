'use strict';

// The supervisor's public surface. Three files, one subject: `registry.js` holds the persisted
// rows, the liveness probe and the four write moments; `readopt.js` holds the boot pass that must
// run before any stamp; `death-stamp.js` holds the evidence-to-ending path every door that used to
// stamp independently now calls; `doors.js` holds the explicit door list every launch is on, and
// `probe.js` the one `(goal, seat)` liveness answer the legacy predicates were retired into;
// `owed.js` is the single owed-work computer the two of them became, and `launch-door.js` the
// single enqueue on the owed path plus the admit checks the retired computer left behind.
// Callers require THIS file, never a path inside the folder, so the split can move without a
// sweep of every door.

const registry = require('./registry');
const readopt = require('./readopt');
const deathStamp = require('./death-stamp');
const doors = require('./doors');
const probe = require('./probe');
const owed = require('./owed');
const launchDoor = require('./launch-door');
const recoveryConfig = require('./recovery-config');
const progress = require('./progress');
const killClock = require('./kill-clock');
const checkpoint = require('./checkpoint');

// The recovery half of the same component: `recovery-config.js` is the ONE read api for the eight
// tweakable numbers (sibling seats consume it read-only and none of them opens the file itself),
// `progress.js` the only writer of `last_progress_at`, `kill-clock.js` the no-progress decision
// plus the closed list of three pause conditions, and `checkpoint.js` the operational checkpoint
// contract (progress note, side-effect journal, relaunch prompt).

module.exports = {
  ...registry,
  ...readopt,
  ...deathStamp,
  ...doors,
  ...probe,
  ...owed,
  ...launchDoor,
  ...recoveryConfig,
  ...progress,
  ...killClock,
  ...checkpoint,
};
