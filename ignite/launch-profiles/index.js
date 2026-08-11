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
  resolveProfile,
  resolveTemplateSlots,
  resolveWorkdir,
  resolveWorkspaceRoot,
  sessionsRootFor,
  CLOSED_SLOTS,
  KNOWN_EFFORT_LEVELS,
} = require('./profiles');
const { detectHostCapability, CAGED, PORTABLE } = require('./host');
const { preflightPinnedFlags, pinnedFlagsOf, readHelp } = require('./preflight');
const {
  bindingOf,
  catalogOf,
  declaresBinding,
  profileForBinding,
  E_UNMAPPED_BINDING,
  E_AMBIGUOUS_BINDING,
} = require('./catalog');
const errors = require('./errors');

module.exports = {
  // load + resolve
  loadConfig,
  resolveProfile,
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
  // the (harness, model) -> profile-name catalog (task 7.54; owner ruling D19). ONE derivation,
  // shared with `capabilities/bindings/tool/bindings.py#catalog` — see catalog.js's header.
  bindingOf,
  catalogOf,
  declaresBinding,
  profileForBinding,
  E_UNMAPPED_BINDING,
  E_AMBIGUOUS_BINDING,
  // vocabulary
  CLOSED_SLOTS,
  KNOWN_EFFORT_LEVELS,
  // errors — re-exported so a consumer never reaches into server/spawn/errors.js
  ...errors,
};
