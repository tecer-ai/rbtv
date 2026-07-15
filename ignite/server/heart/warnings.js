'use strict';

const WARNING_KINDS = {
  SEAT_BLOCKED_BUDGET_EXHAUSTED: 'seat-blocked-budget-exhausted',
};

// The D45 announcement cadence: announce every 60 s while a warning stands.
// ticker.js runs at tick_interval_ms: 10000 (10 s/tick), so 60 s = 6 ticks.
const WARNING_ANNOUNCE_INTERVAL_TICKS = 6;

// The tick-rate conversion used to turn an owner-supplied `minutes` into ticks
// (60 s/min ÷ 10 s/tick). Deliberately SEPARATE from the announce cadence
// above: the two are equal at 10 s/tick by arithmetic, not by meaning, and
// collapsing them would make any future change to the announce cadence
// silently corrupt every minutes→ticks conversion.
const TICKS_PER_MINUTE = 6;

module.exports = {
  WARNING_KINDS,
  WARNING_ANNOUNCE_INTERVAL_TICKS,
  TICKS_PER_MINUTE,
};
