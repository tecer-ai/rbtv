'use strict';

// ── `drop-lane` — permanently abandon ONE lane, RUN DAEMON-SIDE ─────────────────────────────────
// (owner rulings `d-recovery-drop-is-one-lane-permanent`, `d-recovery-abandoned-is-an-ending`,
// `d-recovery-drop-stops-live-work`, 2026-08-31, `redesign-continue-1`).
//
// THE GAP THIS CLOSES. `dl-abandoned-outcome` (f1b7a292) landed `abandonSeat` — the sanctioned
// write of a lane's second terminal outcome — with NO wire path to it: the bridge is a SEPARATE
// PROCESS walled off from the store, a child process and every sibling require
// (`chat/probes/probe-chat-boundary.js`), same as every other daemon effect in this tree. This is
// the SIXTEENTH intent's act function, added by name under the ratified envelope
// (`dispatch.js`'s own header: "Future intents are ADDED by name... never by widening an existing
// intent's payload semantics") — never folded into `pause-resume`'s verb enum, which its own
// header (`ignite/runtime/gateway/parse.js` ~line 839) deliberately keeps closed to two members.
//
// ⚠ MARKING ONLY. Stopping the lane's live work is NOT this module's job: `chat-bridge.js`'s
// `dropLane` port stops it over the wire FIRST, through the EXISTING `inspect` + `kill-session`
// intents (unchanged by this file) — and only calls this intent once that has succeeded or found
// nothing live. This module holds no execution-lane / heart-store handle to re-check liveness
// with, and re-deriving that here would be exactly the "two copies of one fact" defect
// `pause-resume.js`'s own header (~line 38) warns about. `abandonSeat` is the ONE marking path;
// this function calls it and invents no second one.
//
// Same ending-store resolution as `pause-resume.js`, same reason: the file the lane gate reads
// (`supervisor/ending-reads.js`), never the daemon's private lane store (`state-store/heart/
// pause-resume.js`'s "THE ENDING HOME" note is the full argument).
const { bind, openEndingStoreFor } = require('..');
const { isSafeName } = require('../../chat/bus-ferry');
const { liveGoals } = require('./pause-resume');

// `found:false` mirrors `pauseResume()`'s own contract: the ONLY non-shape refusal, and it is the
// roster's, not the filesystem's. The caller (`dispatch.js#handleDropLane`) turns it into
// `NOT_FOUND`, same as the mechanical door.
function dropLane({
  workspaceRoot, goal, seat, askId = undefined,
}) {
  if (!isSafeName(goal)) return { found: false, reason: 'bad-name', detail: 'goal is not a bare safe name' };
  if (!isSafeName(seat)) return { found: false, reason: 'bad-name', detail: 'seat is not a bare safe name' };
  if (!liveGoals(workspaceRoot).includes(String(goal))) {
    return { found: false, reason: 'no-such-goal', detail: `${goal} is not a live goal` };
  }
  const store = bind(openEndingStoreFor(workspaceRoot));
  // `abandonSeat` is idempotent on a retried or already-dropped lane (writers.js's own comment on
  // the primary key) — this act function adds NO retry/dedupe logic on top of it, since doing so
  // would be a second copy of the ONE idempotency guarantee the writer already gives.
  const { abandonment, idempotent } = store.abandonSeat({
    goal,
    seat,
    anchor: 'owner: drop-lane (recovery thread) — this lane is stuck for good, no undo',
    abandoned_by: 'owner',
    ask_id: askId != null ? String(askId) : null,
  });
  return {
    found: true, goal, seat, idempotent, abandonment,
  };
}

module.exports = { dropLane };
