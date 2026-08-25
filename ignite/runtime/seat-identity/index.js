'use strict';

// Task 7.11 §4b — the seat-identity module's public surface.
//
// `checkIdentity` is the ADDITIVE resolver task 7.10 plugs into the gateway's D15 pluggable
// sender-identity seam: the gateway resolves a caller by the same folder+process match this
// returns, and per-sender tokens remain the fallback plug for non-seat callers. No pipeline
// change, no envelope change, and — deliberately — no gateway code in this module.

module.exports = {
  ...require('./identity'),
  ...require('./seat-folder'),
  ...require('./csv'),
};
