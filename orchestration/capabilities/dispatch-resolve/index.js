'use strict';

// orchestration/capabilities/dispatch-resolve — the conductor's seam onto the ONE shared
// launch-profile resolver (task 7.54; registry decisions.md#d-profile-source-unification,
// DEC-1 § Shared profile source, CMP-9).
//
// The conductor is the shared resolver's THIRD consumer. Consumer 1 is the daemon's spawn path
// (`ignite/server/spawn/config.js`), consumer 2 the sub-agent dispatch capability (task 7.43).
//
// ⚠ WHAT THIS ROW DELIVERS AND WHAT IT DOES NOT — read before assuming coverage:
// 2 of 11 elected CLI (model, variant) pairs have a profile at all. The other 9 keep their package
// invocation manuals, which is DELIBERATE and is task 7.86's to close, not an oversight. And even
// for a covered pair, only the INVOCATION knowledge has a new home: exit codes, recovery
// protocols, resume mechanics, failure modes and the per-model task contract have NO FIELD in the
// profile schema and stay in the delta. Package-granularity is the gate; content-granularity is
// the cut (leader ruling 2026-07-28, #1486).

const resolve = require('./resolve');
const errors = require('./errors');
const profiles = require('../../../ignite/launch-profiles');

module.exports = {
  // the one entry point — resolution and pre-flight in a single call, so a caller cannot obtain a
  // resolved argv without the refusals having run
  preflightDispatch: resolve.preflightDispatch,
  loadProfiles: resolve.loadProfiles,
  // the individual bounds, exported so a probe can exercise each one on its own terms
  assertNoSeatBinds: resolve.assertNoSeatBinds,
  assertWorkTarget: resolve.assertWorkTarget,
  // task 7.87 criterion 4: does THIS profile write its own add-dir flag through `{extra_dir}`,
  // or does the caller still owe a hand-composed one?
  declaresExtraDir: resolve.declaresExtraDir,
  ...errors,
  // re-exported so a consumer of this lane never reaches into another module's error file: a
  // caller catches refusals from BOTH surfaces and must be able to name them without importing two
  SpawnError: profiles.SpawnError,
  E_UNKNOWN_PROFILE: profiles.E_UNKNOWN_PROFILE,
  E_RAW_FLAG: profiles.E_RAW_FLAG,
  E_PINNED_FLAG_ABSENT: profiles.E_PINNED_FLAG_ABSENT,
};
