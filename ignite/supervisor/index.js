'use strict';

// The supervisor's public surface. Three files, one subject: `registry.js` holds the persisted
// rows, the liveness probe and the four write moments; `readopt.js` holds the boot pass that must
// run before any stamp; `death-stamp.js` holds the evidence-to-ending path every door that used to
// stamp independently now calls. Callers require THIS file, never a path inside the folder, so the
// split can move without a sweep of every door.

const registry = require('./registry');
const readopt = require('./readopt');
const deathStamp = require('./death-stamp');

module.exports = { ...registry, ...readopt, ...deathStamp };
