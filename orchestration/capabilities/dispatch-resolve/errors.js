'use strict';

// Typed refusals for the conductor's dispatch pre-flight (task 7.54).
//
// A SEPARATE class from `SpawnError` (ignite/launch-profiles/errors.js), deliberately, and for the
// same reason `injection-ladder/errors.js` is separate: these are refusals the CONDUCTOR raises
// about a dispatch it is about to compose, not refusals the shared resolver raises about a profile.
// Collapsing them would make "the profile is malformed" and "the conductor did not supply a
// work-target" indistinguishable at the catch site, and they have different owners and fixes.
class DispatchResolveError extends Error {
  constructor(code, message, detail = {}) {
    super(message);
    this.name = 'DispatchResolveError';
    this.code = code;
    this.detail = detail;
  }
}

// The profile declares `sandbox.SeatBinds`. The conductor loads the shared config with a
// NON-INTERPRETING validator stub (see resolve.js), so a bind template reaching this consumer is
// unvalidated by construction — this refusal is what keeps the stub from becoming a hole.
const E_SEATBINDS_PROFILE = 'E_SEATBINDS_PROFILE';

// No work-target was supplied. The confinement split (dispatch-wrapper.md:36, row G1) requires TWO
// path values — guidance-root and work-target — and a profile expresses ONE.
const E_ADD_DIR_ABSENT = 'E_ADD_DIR_ABSENT';

// A work-target was supplied but is not an absolute path. A relative path resolves against the
// spawning shell's CWD, which drifts after any prior `cd` (dispatch-wrapper.md:35).
const E_ADD_DIR_RELATIVE = 'E_ADD_DIR_RELATIVE';

module.exports = {
  DispatchResolveError,
  E_SEATBINDS_PROFILE,
  E_ADD_DIR_ABSENT,
  E_ADD_DIR_RELATIVE,
};
