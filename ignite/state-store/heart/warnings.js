'use strict';

const WARNING_KINDS = {
  SEAT_BLOCKED_BUDGET_EXHAUSTED: 'seat-blocked-budget-exhausted',
  // D80: tailnet bind degraded to loopback-only — raised by the daemon's
  // tailnet-degrade path (registered here per task 7.8).
  TAILNET_BIND_DEGRADED: 'tailnet-bind-degraded',
};

// Every duration below is expressed in WALL-CLOCK ms and converted at call time
// against the LIVE configured cadence. A stored tick count would be a hidden
// assumption that ticker.js runs at its 10 s default: at any other cadence a
// baked-in constant silently corrupts the duration it stands for.
const DEFAULT_TICK_INTERVAL_MS = 10000; // ticker.js DEFAULT_CONFIG default

function resolveTickIntervalMs(tickIntervalMs) {
  const ms = Number(tickIntervalMs);
  return Number.isFinite(ms) && ms > 0 ? ms : DEFAULT_TICK_INTERVAL_MS;
}

// The D45 announcement cadence: announce every 60 s while a warning stands.
function announceIntervalTicks(tickIntervalMs) {
  return Math.ceil(60000 / resolveTickIntervalMs(tickIntervalMs));
}

// The tick-rate conversion used to turn an owner-supplied `minutes` into ticks.
// Deliberately SEPARATE from the announce cadence above: the two are equal at
// 10 s/tick by arithmetic, not by meaning, and collapsing them would make any
// future change to the announce cadence silently corrupt every minutes→ticks
// conversion.
function minutesToTicks(minutes, tickIntervalMs) {
  return Math.ceil((minutes * 60000) / resolveTickIntervalMs(tickIntervalMs));
}

module.exports = {
  WARNING_KINDS,
  announceIntervalTicks,
  minutesToTicks,
};
