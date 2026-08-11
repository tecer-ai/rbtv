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

// `E_SEATBINDS_PROFILE` was RETIRED with the seat-binds deny-list (owner ruling 2026-08-11:
// launch_profile retired, manual invocation permanent (executes d-r2-preflight-manual-plus-skill)).
// Its premise — seat profiles are the exception — died when `r-seats-only-architecture` spread the
// shared cage into every profile. `resolve.js`'s stub comment carries why the stub is safe without
// it. Named here, not silently absent, so a catch site written against the old code reads why.

// No work-target was supplied. The confinement split (dispatch-wrapper.md:36, row G1) requires TWO
// path values — guidance-root and work-target — and a profile expresses ONE.
const E_ADD_DIR_ABSENT = 'E_ADD_DIR_ABSENT';

// A work-target was supplied but is not an absolute path. A relative path resolves against the
// spawning shell's CWD, which drifts after any prior `cd` (dispatch-wrapper.md:35).
const E_ADD_DIR_RELATIVE = 'E_ADD_DIR_RELATIVE';

module.exports = {
  DispatchResolveError,
  E_ADD_DIR_ABSENT,
  E_ADD_DIR_RELATIVE,
};
