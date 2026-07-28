'use strict';

// The sub-agent dispatch capability's error surface (task 7.43; registry CMP-10 § Standing
// sub-agent lane, decisions.md#d-sub-agent-standing-lane, #d-sub-agent-exposure-enforcement).
//
// ⚠ EVERY CODE BELOW IS A REFUSAL THAT SPAWNS NOTHING. This lane's cage is `restrictions`-class —
// fail-closed in THIS capability's own code, nothing left to the model's judgment
// (#d-sub-agent-exposure-enforcement). None of these may ever be softened into a warning, a log
// line, or a doc sentence: guidance is the NATIVE lane's mechanism (the rule task 7.49 ships), and
// a bound carried twice in two mechanisms is a bound enforced by neither.
//
// A SEPARATE class from `SpawnError` (launch-profiles/errors.js) and `LadderError`
// (injection-ladder/errors.js), for the reason those two are separate from each other: the three
// modules answer different questions — WHAT the command line is, WHICH method drives it, and
// WHETHER this dispatch is allowed at all — and a consumer that catches one must not silently
// swallow another. The upstream classes are re-exported by `index.js` so a caller never reaches
// into another module's error file.
class DispatchError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'DispatchError';
    this.code = code;
    this.details = details;
  }
}

// ── Boundary 1 — catalog-bound (CMP-10 boundary 1, #d-catalog-bound-exposure-manifest) ───────
// The named target is not exposed for sub-agent dispatch by any component's exposure manifest.
// FAIL CLOSED: there is no "dispatch it anyway" path, and there is deliberately no flag that
// admits a free-form target — free-form agents are what boundary 1 exists to refuse.
const E_TARGET_NOT_CATALOGED = 'E_TARGET_NOT_CATALOGED';
// No exposure manifest could be read at all. DISTINCT from E_TARGET_NOT_CATALOGED on purpose:
// "the catalog says no" and "there is no catalog" are different facts, and collapsing them would
// let a missing/renamed catalog read as a clean per-target refusal. Both refuse; only one is a
// deployment fault.
const E_NO_CATALOG = 'E_NO_CATALOG';
// A manifest row exists but is malformed (missing entry-point, entry-point off disk). A row that
// cannot be executed is not a licence to improvise one.
const E_CATALOG_ROW_INVALID = 'E_CATALOG_ROW_INVALID';

// ── Boundary 6 — no seat impersonation (CMP-10 boundary 6) ────────────────────────────────────
// The resolved workdir carries a taskforce seat's identity (`{goal}/runs/run-N/seats/…`). A
// sub-agent holds no slot in any taskforce; a workdir inside a seat folder would make its
// artifacts indistinguishable from that seat's on disk, which is the impersonation the boundary
// names. Checked BEFORE the spawn, so nothing is ever written there and then noticed.
const E_SEAT_IMPERSONATION = 'E_SEAT_IMPERSONATION';

// ── Boundary 9 — no nesting (#d-sub-agent-population-bounds) ──────────────────────────────────
// This process is itself a sub-agent (its environment carries the depth marker the dispatcher
// stamps). Depth stops ONE level below the dispatcher. Refused in code, never by guidance.
const E_NESTING_REFUSED = 'E_NESTING_REFUSED';

// ── Boundary 10 — per-dispatcher fan-out cap (#d-sub-agent-population-bounds) ─────────────────
// This dispatcher already has the maximum number of sub-agents running simultaneously.
const E_FANOUT_EXCEEDED = 'E_FANOUT_EXCEEDED';

// ── Boundary 11 — environment allowlist (#d-sub-agent-env-allowlist) ──────────────────────────
// The scrubbed environment could not be built as declared — a variable the profile names is
// absent from the dispatcher's own environment. CMP-10's words: "a missing variable is a VISIBLE
// failure, never a silent leak". So it is a refusal, not a shrug.
const E_ENV_VAR_MISSING = 'E_ENV_VAR_MISSING';
// The composed child environment failed its own post-condition (a name outside the allowlist
// survived). Asserted rather than assumed: if a future edit ever widens the composition, this
// fires here rather than in a spawned process holding the dispatcher's secrets.
const E_ENV_LEAK = 'E_ENV_LEAK';

// ── The rung the ladder WALKED to is not one this lane can drive ──────────────────────────────
// Raised only AFTER `resolveRung()` has computed a rung from the situation. It is not a private
// preference expressed as an error: this lane spawns a headless one-shot attached to the caller's
// terminal and has no pane to type into, so a walk that lands on `keystroke` (or on any rung this
// lane cannot execute) is a refusal, not a downgrade. The message carries the walk's own `skipped`
// list so the caller reads WHY the ladder got there.
const E_RUNG_NOT_DRIVABLE = 'E_RUNG_NOT_DRIVABLE';

// The profile resolves to a binary the ladder has no measured harness entry for (harnessOf/
// harnessFromBinary returned null). A sub-agent IS an agent: a profile with no harness (sleep,
// bash, a test profile) is not a sub-agent target, and guessing a harness would put unverified
// launch knowledge back into the system CMP-9 exists to hold in one place.
const E_NO_HARNESS = 'E_NO_HARNESS';

// The resolved harness binary is not on the dispatcher's PATH. Distinct from E_NO_HARNESS: "the
// ladder does not know this harness" and "this box does not have it installed" are different
// facts. Refused before the spawn so the failure names the binary rather than surfacing as an
// ENOENT from a child.
const E_HARNESS_BINARY_ABSENT = 'E_HARNESS_BINARY_ABSENT';

// The caller's own argument shape was refused (no target, no profile, no prompt). Kept typed so a
// scripted caller distinguishes "I asked wrongly" from "the cage said no".
const E_BAD_REQUEST = 'E_BAD_REQUEST';

// Two different workspaces answer "which `.rbtv/` roots this box" — the daemon's unit says one
// thing and a walk-up from the caller's cwd says another. Refused rather than guessed: launching a
// sub-agent into the wrong workspace puts its session dir and every artifact it writes somewhere
// nobody is looking. See dispatch.js:resolveWorkspaceRoot for the defect that produced this.
const E_WORKSPACE_AMBIGUOUS = 'E_WORKSPACE_AMBIGUOUS';

module.exports = {
  DispatchError,
  E_TARGET_NOT_CATALOGED,
  E_NO_CATALOG,
  E_CATALOG_ROW_INVALID,
  E_SEAT_IMPERSONATION,
  E_NESTING_REFUSED,
  E_FANOUT_EXCEEDED,
  E_ENV_VAR_MISSING,
  E_ENV_LEAK,
  E_RUNG_NOT_DRIVABLE,
  E_NO_HARNESS,
  E_HARNESS_BINARY_ABSENT,
  E_BAD_REQUEST,
  E_WORKSPACE_AMBIGUOUS,
};
