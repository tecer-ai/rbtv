'use strict';

// The supervisor's public surface. Two files, one subject: `registry.js` holds the persisted rows,
// the liveness probe and the four write moments; `readopt.js` holds the boot pass that must run
// before any stamp. Callers require THIS file, never a path inside the folder, so the split can
// move without a sweep of every door.

const registry = require('./registry');
const readopt = require('./readopt');

module.exports = { ...registry, ...readopt };
