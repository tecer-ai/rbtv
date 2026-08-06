'use strict';

// The orchestration conductor's seam onto the ONE shared launch-profile resolver
// (`ignite/launch-profiles/`, task 7.42). Task 7.54; the conductor is the resolver's THIRD
// consumer (`launch-profiles/README.md` § The three consumers).
//
// WHAT THIS IS NOT: it is not a second interpreter of the profile file. Every argv element comes
// from `resolveProfile()`; nothing here composes, appends to, or rewrites a command line. This
// module contributes exactly three refusals the shared resolver cannot raise on the conductor's
// behalf, and otherwise gets out of the way.

const path = require('node:path');
const profiles = require('../../../ignite/launch-profiles');
const {
  DispatchResolveError,
  E_SEATBINDS_PROFILE,
  E_ADD_DIR_ABSENT,
  E_ADD_DIR_RELATIVE,
} = require('./errors');

// ── The SeatBinds stub, and the deny-list that keeps it honest ────────────────────────────────
//
// ⚠ MEASURED, and it is the reason this module exists in this shape. The shared resolver REFUSES
// the committed `config/spawn-profiles.yaml` outright unless the caller injects a SeatBinds
// template validator: profile `claude-seat` declares `sandbox.SeatBinds` (task 7.11), and
// `profiles.js` refuses an unvalidated bind template rather than waving it through — correctly,
// "absence of a checker must never become absence of a check". The real validator lives in
// `server/spawn/cage.js`.
//
// ⇒ ONE profile declaring `SeatBinds` poisons the load for EVERY non-daemon consumer of the whole
// file. The conductor is a non-daemon consumer BY CONSTRUCTION (its whole point is reaching the
// resolver with no daemon in the picture), so it cannot inject the real validator without coupling
// the orchestration module to daemon internals.
//
// ⚠ THE COST OF THE STUB, STATED RATHER THAN SOFTENED: a non-interpreting stub DEFEATS that guard
// for `claude-seat`. "The conductor will never resolve `claude-seat`" is DISCIPLINE, not
// ENFORCEMENT. The deny-list below is what converts it back to enforcement — which is why the stub
// and the deny-list are one mechanism and neither ships without the other.
//
// (A FORMER sibling consumer, `ignite/capabilities/sub-agent-dispatch` — task 7.43, retired by
// `r-seats-only-architecture` 2026-08-06 — took the OTHER branch and imported the real validator
// read-only, which was available to it because it lived inside `ignite/`. Recorded as history so
// a reader does not mistake the two answers for a contradiction.)
function nonInterpretingSeatBindValidator() {
  // Deliberately returns without inspecting the template. Interpreting a bind vocabulary this
  // module does not own would be a SECOND interpreter — the exact drift 7.42 exists to prevent.
  // Every profile that reaches this stub is refused at resolve time by `assertNoSeatBinds`.
  return undefined;
}

function loadProfiles(configPath) {
  return profiles.loadConfig(configPath, {
    seatBindValidator: nonInterpretingSeatBindValidator,
  });
}

// The deny-list. Fail-closed: a profile declaring `sandbox.SeatBinds` is NEVER resolved by the
// conductor, because this consumer validated nothing about that declaration.
function assertNoSeatBinds(config, profileName) {
  const profile = config.profiles[profileName];
  if (!profile) return; // unknown profile — let the shared resolver raise E_UNKNOWN_PROFILE
  const binds = profile.sandbox && profile.sandbox.SeatBinds;
  if (binds !== undefined) {
    throw new DispatchResolveError(
      E_SEATBINDS_PROFILE,
      `profile '${profileName}' declares sandbox.SeatBinds, which this consumer loaded through a ` +
      `NON-INTERPRETING validator stub — refusing to resolve it rather than dispatching against a ` +
      `bind template nothing has validated. The conductor is a non-daemon consumer and does not ` +
      `own the SeatBinds vocabulary (that is server/spawn/cage.js's).`,
      { profile: profileName, declared: binds },
    );
  }
}

// ── The confinement split (row G1), enforced ──────────────────────────────────────────────────
//
// `dispatch-wrapper.md:36` requires the guidance-root and the work-target to be TWO SEPARATE path
// values; a profile expresses ONE. `{extra_dir}` is UNAUTHORABLE — `CLOSED_SLOTS` is
// `{workdir} {prompt_file} {session_ref}`, enforced at config LOAD with `E_UNKNOWN_SLOT`
// (`profiles.js:92`/`:135`), and widening that vocabulary is task 7.87's.
//
// ⚠ SO THIS DOES NOT MAKE THE DISPATCH FULLY PROFILE-RESOLVED, AND MUST NOT CLAIM TO. The add-dir
// flag stays hand-composed by the conductor. What this does is make its ABSENCE LOUD instead of
// silent: a dispatch that forgot the work-target is REFUSED here rather than launching a worker
// rooted at its guidance root. That rule was earned by the `a3e217d` incident, where a bare kimi
// self-commit swept 5 foreign files because its guidance-root was the unmirrored nested repo.
function assertWorkTarget(addDir) {
  if (addDir === undefined || addDir === null || addDir === '') {
    throw new DispatchResolveError(
      E_ADD_DIR_ABSENT,
      `no work-target supplied — REFUSING to dispatch. The confinement split (dispatch-wrapper.md ` +
      `row G1) requires the worker's guidance-root and its work-target to be two separate path ` +
      `values. Dispatching without one roots the worker at its guidance root, which is how the ` +
      `a3e217d incident swept 5 foreign files. Pass the work-target explicitly.`,
      {},
    );
  }
  if (!path.isAbsolute(addDir)) {
    throw new DispatchResolveError(
      E_ADD_DIR_RELATIVE,
      `work-target '${addDir}' is relative — REFUSING to dispatch. Every path in a launch command ` +
      `must be absolute (dispatch-wrapper.md:35): a relative path resolves against the spawning ` +
      `shell's CWD, which drifts after any prior 'cd'.`,
      { addDir },
    );
  }
}

// ── The one entry point ───────────────────────────────────────────────────────────────────────
//
// Resolves a NAMED profile and runs the dispatch pre-flight in ONE call, so a caller cannot get a
// resolved argv without the checks having run. The ordering is deliberate and is the cheap-to-
// expensive order: both refusals that need no subprocess fire BEFORE the pre-flight shells out to
// the binary's `--help`.
//
// ⚠ THE ADD-DIR CHECK IS HOMED HERE ON A LEADER RULING (2026-07-28, #1486) AND THE REASON IS
// STRUCTURAL, not stylistic. It was first ruled as "the conductor refuses to dispatch when the
// add-dir is absent" — but there is NO conductor code path that composes a command line
// (`route.py` emits an `invocation_pointer`; `scaffold.py` only checks manual drift; the AGENT
// types the command from the rendered manual). An enforcement with nothing to live in degrades to
// card prose, which is what that ruling refused. The pinned-flag pre-flight is the one thing in
// this row that ACTUALLY EXECUTES, so the add-dir check rides it.
function preflightDispatch(config, profileName, opts = {}) {
  const { effort, slots = {}, addDir, preflightOpts = {} } = opts;

  assertNoSeatBinds(config, profileName);
  assertWorkTarget(addDir);

  const resolved = profiles.resolveProfile(config, profileName, { slots, effort });
  const preflight = profiles.preflightPinnedFlags(resolved, preflightOpts);

  return { argv: resolved.argv, binary: resolved.binary, addDir, preflight };
}

module.exports = {
  loadProfiles,
  assertNoSeatBinds,
  assertWorkTarget,
  preflightDispatch,
  nonInterpretingSeatBindValidator,
};
