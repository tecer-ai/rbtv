'use strict';

// ⚠ 7.42: `SpawnError` AND the profile-surface codes now LIVE IN `ignite/launch-profiles/errors.js`
// and are RE-EXPORTED here. The direction is deliberate. The shared resolver may not require
// anything under `server/`, so the class had to move outward; re-exporting keeps ONE class object
// in the process, which is what every `instanceof SpawnError` in spawn.js, carrier.js, cage.js and
// the gateway depends on. Two copies of the class would make those checks depend on which module
// raised the error — a defect that would only appear once a second consumer existed.
//
// Everything below the re-export block is daemon-only and stays here: the carrier, tmux, cage and
// identity-gate codes have no meaning outside the daemon and belong to no shared surface.
const {
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
} = require('../../launch-profiles/errors');

const E_UNKNOWN_MODE = 'E_UNKNOWN_MODE';
const E_HEADED_NOT_CAPABLE = 'E_HEADED_NOT_CAPABLE';
// G-144: the profile is WELL-FORMED — it declares the 7.42 caged/portable halves
// (`command: { caged:, portable: }`, #d-profile-source-unification (4)) — and this DAEMON spawn
// path resolves `exec:` only. Daemon-only by design, which is why it lives here and not in
// launch-profiles/errors.js: the SHARED resolver handles halves fine (that is what it is for);
// what cannot is spawn.js, and only until its ruled consumers (7.43/7.54) wire it through
// resolveProfile(). Before this code existed the same condition read `profile.exec.argv` off
// `undefined` and took the spawn path down with an untyped TypeError — on a config the daemon
// had loaded cleanly, so config validation was no backstop.
const E_PROFILE_HALVES_UNSUPPORTED = 'E_PROFILE_HALVES_UNSUPPORTED';
const E_UNKNOWN_REQUEST_KEY = 'E_UNKNOWN_REQUEST_KEY';
const E_SESSION_NOT_FOUND = 'E_SESSION_NOT_FOUND';
const E_CARRIER_FAILED = 'E_CARRIER_FAILED';

const E_SYSTEMD_NOT_AVAILABLE = 'E_SYSTEMD_NOT_AVAILABLE';
const E_FS_SANDBOX_UNAVAILABLE = 'E_FS_SANDBOX_UNAVAILABLE';
const E_ORPHAN_RESCAN_FAILED = 'E_ORPHAN_RESCAN_FAILED';
const E_BAD_REQUEST = 'E_BAD_REQUEST';
// 7.30: a tmux session/window name carrying a target separator (`:` `.`) or whitespace would
// silently re-target another pane. Names are server-composed, so this refuses before compose.
const E_TMUX_NAME_INVALID = 'E_TMUX_NAME_INVALID';

// ── 7.11 — the seat cage (cage.js) ───────────────────────────────────────────────────────────
// A malformed bind template: unknown verb, unknown slot, a slot with no value, a relative path.
// Loud at compose time, because the alternative is a literal `{seatDir}` reaching bwrap.
const E_CAGE_TEMPLATE = 'E_CAGE_TEMPLATE';
// The composed cage would leave the identity gate's ground truth (`sessions.csv`) writable from
// inside. Refused unconditionally — a seat that can rewrite the log saying who sits where can
// name itself, and under auto-approval harnesses the cage is the only remaining boundary.
const E_CAGE_GROUND_TRUTH = 'E_CAGE_GROUND_TRUTH';

// ── 7.11 — the identity gate (seat-identity/) ────────────────────────────────────────────────
// BOTH gates (§4a launch-time AND §4b command-time): the seat folder resolves, but its GOAL is not
// EXECUTING. One condition, one code, deliberately — the remedy is identical whichever gate asks
// it, and a second code would only invite a caller to handle one and miss the other.
// 7.607 E2a: renamed from `E_RUN_NOT_LIVE`. The run layer is extinguished
// (`decisions.md#d-runs-extinguished`), so a code naming a run named nothing; the condition it
// reports is now the derived lease's (`server/lease/lease.js`), not a register row's.
const E_GOAL_NOT_LIVE = 'E_GOAL_NOT_LIVE';
// BOTH gates: right shape, but not a materialized + rostered seat (no `seat.md`, or no roster row).
// ⚑ These two read "Launch-time" until task 7.10 — ACCURATELY, because the command-time gate did
// not call them. That omission was G-126.
const E_NOT_A_SEAT_FOLDER = 'E_NOT_A_SEAT_FOLDER';
// Command-time (§4b): the caller's cwd has no seat-folder ancestor. A system CLI command from a
// non-seat directory has no identity — refused, never treated as anonymous-but-allowed.
const E_IDENTITY_NO_SEAT = 'E_IDENTITY_NO_SEAT';
// Command-time: no session row for this seat (missing file, unreadable, or zero rows).
// Absence NEVER passes.
const E_IDENTITY_NO_SESSION = 'E_IDENTITY_NO_SESSION';
// Command-time: a session row exists but the live process is not the one it records. The refusal
// names the registered occupant — folder alone is not identity.
const E_IDENTITY_MISMATCH = 'E_IDENTITY_MISMATCH';
// Command-time: the session log lacks the columns identity is decided on. Measured 2026-07-27:
// the live schema carries NONE of them, so this is the default state until 7.37 settles it —
// which is exactly why it must be a typed refusal and never a fall-through to allow.
const E_IDENTITY_SCHEMA = 'E_IDENTITY_SCHEMA';

// ── 7.75 — the DISPATCH DOOR (design-760 §3, the owner rider of r-headless-visibility) ───────
// A headless spawn resolved INSIDE a goal's tree that is not a seat folder: it names no seat, so
// the session it would start could never be attributed to one. Refused AT THE DOOR rather than
// filtered at render time — "a seat-less row cannot come into existence". The refusal names the
// MISSING FIELD (`seat`), because the remedy is to supply it and a code alone does not say so.
// NOT raised for a dispatch outside `.rbtv/goals/` — the interim `.rbtv/sessions/<exec-id>/` path
// the sub-agent lane (NEED-3 carve-out) and the machine-lane jobs use is exempt BY CONSTRUCTION.
const E_SEATLESS_GOAL_DISPATCH = 'E_SEATLESS_GOAL_DISPATCH';

// ── 7.10 — resolving a caller ACROSS a socket (seat-identity/peer-identity.js, issue G-124) ──
// The peer is not on this host, so it owns no process here and holds no seat. NOT a failure: it
// is the handoff to the per-sender TOKEN resolver, which stays the plug for non-seat callers.
const E_PEER_NOT_LOCAL = 'E_PEER_NOT_LOCAL';
// The connection could not be attributed to a pid — no matching socket, or no readable holder.
const E_PEER_UNRESOLVED = 'E_PEER_UNRESOLVED';
// The connection maps to MORE THAN ONE process (an fd inherited across fork, or passed with
// SCM_RIGHTS). Refused rather than resolved to the first match: choosing among holders would make
// the identity depend on /proc enumeration order, which is a lottery, not a measurement.
const E_PEER_AMBIGUOUS = 'E_PEER_AMBIGUOUS';

module.exports = {
  SpawnError,
  E_PEER_NOT_LOCAL,
  E_PEER_UNRESOLVED,
  E_PEER_AMBIGUOUS,
  E_CONFIG_LOAD,
  E_DUPLICATE_PROFILE,
  E_UNKNOWN_SLOT,
  E_MISSING_KEY,
  E_UNKNOWN_PROFILE,
  E_UNKNOWN_MODE,
  E_HEADED_NOT_CAPABLE,
  E_PROFILE_HALVES_UNSUPPORTED,
  E_FLAG_INJECTION,
  E_WORKDIR_ESCAPE,
  E_WORKDIR_MISSING,
  E_UNKNOWN_REQUEST_KEY,
  E_SESSION_NOT_FOUND,
  E_CARRIER_FAILED,
  E_SYSTEMD_NOT_AVAILABLE,
  E_FS_SANDBOX_UNAVAILABLE,
  E_ORPHAN_RESCAN_FAILED,
  E_BAD_REQUEST,
  E_TMUX_NAME_INVALID,
  E_CAGE_TEMPLATE,
  E_CAGE_GROUND_TRUTH,
  E_GOAL_NOT_LIVE,
  E_NOT_A_SEAT_FOLDER,
  E_IDENTITY_NO_SEAT,
  E_IDENTITY_NO_SESSION,
  E_IDENTITY_MISMATCH,
  E_IDENTITY_SCHEMA,
  E_SEATLESS_GOAL_DISPATCH,
  // 7.42 — new codes on the shared surface, re-exported so daemon-side callers can catch them
  // by the same import they already use.
  E_NO_PORTABLE_HALF,
  E_UNKNOWN_EFFORT,
  E_RAW_FLAG,
  E_PINNED_FLAG_ABSENT,
  E_PREFLIGHT_UNAVAILABLE,
};
