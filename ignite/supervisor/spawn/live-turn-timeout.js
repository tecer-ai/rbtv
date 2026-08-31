'use strict';

// THE ONE SOURCE for the daemon's live-session turn timeout (duplicate owner-facing replies
// fix, redesign-continue-1 `dup-idempotency`). Before this file existed, `chat/live-sessions.js`
// (the bridge, which must never give up on a turn before the daemon does) carried its OWN
// hardcoded copy of "roughly the daemon's ceiling" — 240000 next to this file's 300000 — and the
// two drifted out of the relationship they need: the bridge's feed ceiling MUST stay strictly
// GREATER than this value, or the bridge abandons a turn the daemon still owns and falls back to
// a cold retry that re-answers a question the warm leg was still working on.
//
// A tiny, dependency-free leaf on purpose: `supervisor/spawn/live-sessions.js` requiring it costs
// nothing it did not already pay, and `chat/live-sessions.js` (a DIFFERENT process — the bridge —
// which must hold no spawn capability, `probes/probe-chat-boundary.js`) can require it too without
// pulling in `child_process`, `harness-config`, `bwrap`, or any of the daemon-only machinery that
// requiring the whole `live-sessions.js` module would drag in.
const DEFAULT_TURN_TIMEOUT_MS = 300000;

module.exports = { DEFAULT_TURN_TIMEOUT_MS };
