'use strict';

// The shared launch-profile resolver's error surface (task 7.42,
// registry decisions.md#d-profile-source-unification (2)).
//
// `SpawnError` LIVES HERE, not in server/spawn/errors.js, and that file now re-exports this
// class. The direction matters: the shared module may not require anything under `server/`
// ("ONE module with no daemon import"), and duplicating the class would give the daemon two
// distinct constructors — every `instanceof SpawnError` in spawn.js, carrier.js and cage.js
// would then depend on which copy raised the error. One class object, re-exported, keeps
// daemon-side behaviour byte-unchanged.
//
// The NAME stays `SpawnError` rather than becoming `ProfileError`: renaming it would change
// `err.name` on every error the daemon already emits, which is observable in the gateway's
// typed responses and in the probe expectations. This module is the code's new home, not a
// redefinition of what callers already catch.
class SpawnError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'SpawnError';
    this.code = code;
    this.details = details;
  }
}

// ── Codes the profile surface raises (moved verbatim from server/spawn/errors.js) ────────────
const E_CONFIG_LOAD = 'E_CONFIG_LOAD';
const E_DUPLICATE_PROFILE = 'E_DUPLICATE_PROFILE';
const E_UNKNOWN_SLOT = 'E_UNKNOWN_SLOT';
const E_MISSING_KEY = 'E_MISSING_KEY';
const E_UNKNOWN_PROFILE = 'E_UNKNOWN_PROFILE';
const E_FLAG_INJECTION = 'E_FLAG_INJECTION';
const E_WORKDIR_ESCAPE = 'E_WORKDIR_ESCAPE';
const E_WORKDIR_MISSING = 'E_WORKDIR_MISSING';

// ── Codes new at 7.42 ────────────────────────────────────────────────────────────────────────
// The host has no containment capability and the profile declares no PORTABLE half. FAIL CLOSED,
// never "fall back to the caged half without the cage" — the motivating hazard on record
// (#d-profile-source-unification (4)) is `codex-git-write`, which disables codex's OWN sandbox
// because bwrap covers it. Reused on a cage-less desktop that profile would run with NO walls at
// all, and the run would look normal. A typed refusal is the only safe answer.
const E_NO_PORTABLE_HALF = 'E_NO_PORTABLE_HALF';
// The caller passed an effort level outside the abstract vocabulary (low|medium|high|max).
const E_UNKNOWN_EFFORT = 'E_UNKNOWN_EFFORT';
// A caller tried to put something other than a declared slot value through the resolver —
// a raw flag, an extra argv element, or an undeclared slot. THE bound of DEC-1 R3.
const E_RAW_FLAG = 'E_RAW_FLAG';
// The pinned-flag pre-flight ran and the installed CLI's live `--help` does not carry a flag the
// profile pins. Orchestration's validated practice, which the daemon lacked; now every consumer's.
const E_PINNED_FLAG_ABSENT = 'E_PINNED_FLAG_ABSENT';
// The pre-flight could not RUN (binary absent, `--help` failed, timed out). Distinct from
// E_PINNED_FLAG_ABSENT on purpose: "the flag is gone" and "I could not look" are different facts,
// and collapsing them would let an unrunnable binary read as a clean bill of health.
const E_PREFLIGHT_UNAVAILABLE = 'E_PREFLIGHT_UNAVAILABLE';

module.exports = {
  SpawnError,
  E_CONFIG_LOAD,
  E_DUPLICATE_PROFILE,
  E_UNKNOWN_SLOT,
  E_MISSING_KEY,
  E_UNKNOWN_PROFILE,
  E_FLAG_INJECTION,
  E_WORKDIR_ESCAPE,
  E_WORKDIR_MISSING,
  E_NO_PORTABLE_HALF,
  E_UNKNOWN_EFFORT,
  E_RAW_FLAG,
  E_PINNED_FLAG_ABSENT,
  E_PREFLIGHT_UNAVAILABLE,
};
