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
  E_ADD_DIR_ABSENT,
  E_ADD_DIR_RELATIVE,
} = require('./errors');

// ── The SeatBinds stub ────────────────────────────────────────────────────────────────────────
//
// ⚠ MEASURED. The shared resolver REFUSES `config/spawn-profiles.yaml` outright unless the caller
// injects a SeatBinds template validator: `profiles.js` refuses an unvalidated bind template rather
// than waving it through — correctly, "absence of a checker must never become absence of a check".
// The real validator lives in `server/spawn/cage.js`, which this module may not import: the
// conductor is a NON-DAEMON consumer by construction. Since `r-seats-only-architecture`
// (2026-08-06) the shared `cage:` block gives EVERY profile a `sandbox.SeatBinds`, so the stub is
// what makes the file loadable here at all.
//
// ⚠ WHY THE STUB IS NOT A HOLE — the honest statement, replacing the deny-list this module used to
// carry (owner ruling 2026-08-11: launch_profile retired, manual invocation permanent (executes
// d-r2-preflight-manual-plus-skill)). `resolveProfile` returns argv/binary/effort/toolset — the
// sandbox block is NOT among them, and nothing in this lane reads, renders or forwards it. The
// bind template therefore never reaches a command line through this consumer, so there is nothing
// for an unvalidated template to corrupt here. Applying the cage is the DAEMON's mechanism
// (`server/spawn/`), and a conductor's manual dispatch applies none — see dispatch-resolve.md
// § What this lane does NOT give you.
//
// (A FORMER sibling consumer, `ignite/capabilities/sub-agent-dispatch` — task 7.43, retired by
// `r-seats-only-architecture` 2026-08-06 — took the OTHER branch and imported the real validator
// read-only, which was available to it because it lived inside `ignite/`. Recorded as history so
// a reader does not mistake the two answers for a contradiction.)
function nonInterpretingSeatBindValidator() {
  // Deliberately returns without inspecting the template. Interpreting a bind vocabulary this
  // module does not own would be a SECOND interpreter — the exact drift 7.42 exists to prevent.
  return undefined;
}

function loadProfiles(configPath) {
  return profiles.loadConfig(configPath, {
    seatBindValidator: nonInterpretingSeatBindValidator,
  });
}

// ── The confinement split (row G1), enforced ──────────────────────────────────────────────────
//
// `dispatch-wrapper.md:36` requires the guidance-root and the work-target to be TWO SEPARATE path
// values. `{extra_dir}` is now a DECLARED slot (task 7.87 widened `CLOSED_SLOTS`), so a profile
// can express both — see `resolveExtraDirSlot` below for what that changes and what it does not.
//
// This bound is unchanged by the widening and is the reason the split fails LOUD rather than
// silently: a dispatch that forgot the work-target is REFUSED here rather than launching a worker
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

// ── The work-target, RESOLVED THROUGH THE PROFILE (task 7.87 criterion 4) ─────────────────────
//
// A profile that writes its own add-dir flag (`argv: [..., "--add-dir", "{extra_dir}"]`) gets the
// work-target substituted into the position THE PROFILE WROTE, by the shared resolver, exactly
// like `{workdir}`. The conductor stops hand-composing that flag, and the flag itself becomes
// subject to the pinned-flag pre-flight (`preflight.js#pinnedFlagsOf` scans profile-written argv
// elements) — a hand-composed flag was never checked against the live `--help` at all.
//
// ⚠ STRICTLY OPT-IN. A profile declaring no `{extra_dir}` is UNCHANGED: the slot is not injected
// (`resolveProfile` would refuse an undeclared slot key with `E_RAW_FLAG`), the resolved argv is
// byte-identical to before this change, and the add-dir remains the caller's to compose — the
// refusals above still make its absence loud. `addDirResolved` on the result says which of the two
// happened, so a caller never has to guess whether it still owes a flag.
//
// ⚠ EVERY declared half must carry the slot, not merely one. The half is chosen by HOST DETECTION
// inside `resolveProfile`, so a caged-only declaration would resolve the slot on a caged box and
// raise `E_RAW_FLAG` on a portable one — a resolution that depends on which machine ran it. An
// asymmetric profile therefore falls back to the hand-composed path on every host rather than
// behaving differently per host.
function declaresExtraDir(profile) {
  if (!profile) return false;
  const blocks = profile.exec ? [profile.exec] : Object.values(profile.command || {});
  if (blocks.length === 0) return false;
  return blocks.every((b) => Array.isArray(b.argv) && b.argv.some((el) => el.includes('{extra_dir}')));
}

// `addDir` is the ONE door for the work-target: a caller-supplied `slots.extra_dir` is overwritten
// by the value `assertWorkTarget` just validated, so the absent/relative bounds cannot be routed
// around by filling the slot directly.
function resolveExtraDirSlot(profile, slots, addDir) {
  return declaresExtraDir(profile) ? { ...slots, extra_dir: addDir } : slots;
}

// ── The one entry point ───────────────────────────────────────────────────────────────────────
//
// Resolves a NAMED profile and runs the dispatch pre-flight in ONE call, so a caller cannot get a
// resolved argv without the checks having run. The ordering is deliberate and is the cheap-to-
// expensive order: both refusals that need no subprocess fire BEFORE the pre-flight shells out to
// the binary's `--help`.
//
// The ordering note above once had three refusals to order; the seat-binds deny-list was RETIRED
// (owner ruling 2026-08-11: launch_profile retired, manual invocation permanent (executes
// d-r2-preflight-manual-plus-skill)) — see the stub comment for why its premise died.
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

  assertWorkTarget(addDir);

  const profile = config.profiles && config.profiles[profileName];
  const addDirResolved = declaresExtraDir(profile);
  const resolvedSlots = resolveExtraDirSlot(profile, slots, addDir);

  const resolved = profiles.resolveProfile(config, profileName, { slots: resolvedSlots, effort });
  const preflight = profiles.preflightPinnedFlags(resolved, preflightOpts);

  return { argv: resolved.argv, binary: resolved.binary, addDir, addDirResolved, preflight };
}

module.exports = {
  loadProfiles,
  assertWorkTarget,
  declaresExtraDir,
  resolveExtraDirSlot,
  preflightDispatch,
  nonInterpretingSeatBindValidator,
};
