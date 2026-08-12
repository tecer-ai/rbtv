'use strict';

// ignite/launch-profiles — THE one shared launch-profile resolver.
//
// Task 7.42; registry decisions.md#d-profile-source-unification, DEC-1 § Shared profile source,
// CMP-6 § Interface (1). Three consumers resolve through THIS module and no other:
//   1. the daemon's spawn path        — LIVE (server/spawn/config.js is a thin adapter over this)
//   2. the attached dispatch capability — task 7.43, NOT BUILT
//   3. the orchestration conductor's CLI-worker dispatch — task 7.54, NOT BUILT
//
// Shipping with ONE live consumer is the correct outcome of 7.42, not an unfinished one: the
// other two are their own tasks. Said plainly here so no reader infers more completeness than
// exists.
//
// The module requires NOTHING under `server/` — that is the ruling's own bound ("ONE module with
// no daemon import"), and it is what makes the module usable from a CLI, a skill, or a test with
// no daemon in the picture. The one daemon-side dependency the profile schema has (cage.js's
// SeatBinds template validator, task 7.11) is INJECTED by the caller rather than imported.

const {
  loadConfig,
  resolveLaunchSpec,
  resolveTemplateSlots,
  resolveWorkdir,
  resolveWorkspaceRoot,
  sessionsRootFor,
  CLOSED_SLOTS,
  resolveEffort,
} = require('./profiles');
const { detectHostCapability, CAGED, PORTABLE } = require('./host');
const { preflightPinnedFlags, pinnedFlagsOf, readHelp } = require('./preflight');
const {
  bindingOf,
  catalogOf,
  declaresBinding,
  specForSeatCast,
  specKey,
  E_UNMAPPED_BINDING,
  E_UNCAST_SEAT,
} = require('./catalog');
const errors = require('./errors');

module.exports = {
  // load + resolve
  loadConfig,
  resolveLaunchSpec,
  resolveTemplateSlots,
  resolveWorkdir,
  resolveWorkspaceRoot,
  sessionsRootFor,
  // host half selection
  detectHostCapability,
  CAGED,
  PORTABLE,
  // pinned-flag pre-flight (built and exported; NOT wired into the daemon spawn path — see
  // preflight.js's header for why that would have broken 7.42's own byte-unchanged criterion)
  preflightPinnedFlags,
  pinnedFlagsOf,
  readHelp,
  // the (harness, model) -> launch-spec table (task 7.54; owner rulings D19 and
  // `#d-abolish-profile-names`). The pair is the KEY of `launch-specs:`, read — not derived — on
  // both sides; `capabilities/bindings/tool/bindings.py#catalog` reads the same keys.
  bindingOf,
  catalogOf,
  declaresBinding,
  specForSeatCast,
  specKey,
  E_UNMAPPED_BINDING,
  E_UNCAST_SEAT,
  // vocabulary
  CLOSED_SLOTS,
  // the effort ladder's ONE interpreter — shared with server/spawn/spawn.js (2026-08-11,
  // d-0811lp-effort-lane-build-now), which composes exec/resume/headed blocks resolveLaunchSpec
  // has no path for and must not own a second copy of the table.
  resolveEffort,
  // errors — re-exported so a consumer never reaches into server/spawn/errors.js
  ...errors,
};
