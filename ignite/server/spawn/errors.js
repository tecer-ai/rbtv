'use strict';

class SpawnError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'SpawnError';
    this.code = code;
    this.details = details;
  }
}

const E_CONFIG_LOAD = 'E_CONFIG_LOAD';
const E_DUPLICATE_PROFILE = 'E_DUPLICATE_PROFILE';
const E_UNKNOWN_SLOT = 'E_UNKNOWN_SLOT';
const E_MISSING_KEY = 'E_MISSING_KEY';
const E_UNKNOWN_PROFILE = 'E_UNKNOWN_PROFILE';
const E_UNKNOWN_MODE = 'E_UNKNOWN_MODE';
const E_HEADED_NOT_CAPABLE = 'E_HEADED_NOT_CAPABLE';
const E_FLAG_INJECTION = 'E_FLAG_INJECTION';
const E_WORKDIR_ESCAPE = 'E_WORKDIR_ESCAPE';
const E_WORKDIR_MISSING = 'E_WORKDIR_MISSING';
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
// BOTH gates (§4a launch-time AND §4b command-time): the seat folder resolves, but its run is not
// the goal's LIVE run. One condition, one code, deliberately — the remedy is identical whichever
// gate asks it, and a second code would only invite a caller to handle one and miss the other.
const E_RUN_NOT_LIVE = 'E_RUN_NOT_LIVE';
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
  E_RUN_NOT_LIVE,
  E_NOT_A_SEAT_FOLDER,
  E_IDENTITY_NO_SEAT,
  E_IDENTITY_NO_SESSION,
  E_IDENTITY_MISMATCH,
  E_IDENTITY_SCHEMA,
};
