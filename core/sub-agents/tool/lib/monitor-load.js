'use strict';

// cast — tolerant loader for lib/monitor.js. A mid-edit fault in that file (an undefined name
// at its top level) previously killed every `cast` invocation, including `cast seat --dry-run`,
// because monitor.js's exports (MONITOR_USAGE, DEADLINE_MS) are required unconditionally by
// lib/help.js and lib/launch.js. Everyone but `cast monitor` itself only needs those two
// constants, so a load failure here degrades to a fallback instead of propagating.

let monitor;
let monitorLoadError;
try {
  monitor = require('./monitor');
} catch (err) {
  monitorLoadError = err;
}

const FALLBACK_MONITOR_USAGE = 'cast monitor — unavailable: lib/monitor.js failed to load (run `cast monitor` for the error)';
const FALLBACK_DEADLINE_MS = 4 * 60 * 60 * 1000;

module.exports = {
  monitor,
  monitorLoadError,
  MONITOR_USAGE: monitor ? monitor.MONITOR_USAGE : FALLBACK_MONITOR_USAGE,
  DEADLINE_MS: monitor ? monitor.DEADLINE_MS : FALLBACK_DEADLINE_MS,
};
