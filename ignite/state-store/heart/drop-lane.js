'use strict';

// ── `drop-lane` — permanently abandon ONE lane, RUN DAEMON-SIDE, BOTH STEPS ─────────────────────
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
// ⚠⚠ REVISED 2026-09-01 (`dl-live-proof` live-fire finding, resumed session): stopping the live
// turn was ORIGINALLY composed client-side by `chat-bridge.js`'s `dropLane` port over TWO wire
// calls, `inspect` then `kill-session` — and the live daemon PROVED that wrong: `kill-session`'s
// authorization (`authz.js#canKillSession`) grants ONLY `sender.kind === 'owner'` or a
// `creator-seat` match (`enqueued_by`/`enqueuing_seat` === the AUTHENTICATED sender's own id/seat —
// resolved from the connection's token, NEVER from a payload field). The chat bridge authenticates
// as `kind: 'bridge'` and a goal seat's live turn is never enqueued BY the bridge, so that call
// could NEVER succeed, for ANY goal, ANY seat — confirmed both by the live incident (`UNAUTHORIZED_
// SENDER` on a genuinely live session) and by two independent, code-level RED-FIRST checks run in a
// scratch worktree: (1) `gateway/parse.js#parseKillSession` REJECTS an unknown field outright —
// `chat_user` cannot even be added to that payload without ALSO widening its schema; (2)
// `authz.js#canKillSession` never reads any payload field at all — `tokenKindResolver`/
// `seatPrincipalResolver` compare the ATTESTED sender identity to the row, nothing else. Threading
// `chat_user` through (the shape `chat/pause-resume.js:177` uses) would not have helped even had it
// parsed: that field is documented, at that exact line and at `dispatch.js#handlePauseResume`'s own
// header, as "rides along as the reporting sender only... never asks the daemon to re-decide who is
// allowed" — i.e. explicitly NOT an authorization input anywhere in this tree.
//
// THE FIX: stop the live turn IN-PROCESS, inside this same act function, behind the ONE
// authorization gate the whole `drop-lane` intent already passed (`authz.js#canDropLane`, bridge-
// only) — the SAME shape `state-store/heart/pause-resume.js` already uses for its own effects
// (`applyPause`/`applyResume` write state directly, no second gateway hop back out). This is not a
// new mechanism: it is the daemon-side-executor pattern this whole intent family already follows,
// applied to the one step that was wrongly left client-side. `heartStore`/`spawnManager` are the
// SAME two handles `dispatch.js#handleKillSession` already holds and uses (`spawnManager.kill`) —
// consumed here, never reimplemented.
//
// `abandonSeat` is the ONE marking path; this function calls it and invents no second one.
//
// Same ending-store resolution as `pause-resume.js`, same reason: the file the lane gate reads
// (`supervisor/ending-reads.js`), never the daemon's private lane store (`state-store/heart/
// pause-resume.js`'s "THE ENDING HOME" note is the full argument).
const path = require('node:path');
const { bind, openEndingStoreFor } = require('..');
const { isSafeName } = require('../../chat/bus-ferry');
const { liveGoals } = require('./pause-resume');

// The lane's live turn, if any — a SECOND, DISCLOSED read of `heartStore`'s non-terminal
// `jobs_log` rows, the same two calls `dispatch.js#handleInspectTicker` already makes
// (`listExecutionsByStatus('running'/'launching')`), filtered to the ONE `(goal, seat)` this drop
// names. Not `findSeatHolder` (the seat-BUSY gate — "may a NEW job fire here", a different question
// with its own pending-row arm this act has no use for) and not a new store query — the same
// non-terminal rows `kill-session`'s own `handleKillSession` would have looked up by id, found by
// path instead of id because the caller only has the lane's address, never the exec_id.
function findLiveExecutionForLane(heartStore, workspaceRoot, goal, seat) {
  const wanted = path.join(workspaceRoot, '.rbtv', 'goals', String(goal), 'seats', String(seat));
  const rows = heartStore.listExecutionsByStatus('running')
    .concat(heartStore.listExecutionsByStatus('launching'));
  for (const row of rows) {
    let args;
    try { args = JSON.parse(row.args); } catch { args = {}; }
    const workdir = typeof args.workdir === 'string' ? args.workdir.replace(/\/+$/, '') : null;
    if (workdir === wanted) return row;
  }
  return null;
}

// `found:false` mirrors `pauseResume()`'s own contract: the ONLY non-shape refusal, and it is the
// roster's, not the filesystem's. The caller (`dispatch.js#handleDropLane`) turns it into
// `NOT_FOUND`, same as the mechanical door.
//
// `stopFailed` is a SEPARATE, named outcome from `found:false` — the goal/seat WAS real, a live
// turn WAS found, and killing it threw. The caller must NOT mark on this arm (`d-recovery-drop-
// stops-live-work`'s own "never both true") — never merge this into `found:false`, which the
// caller renders as `NOT_FOUND` (a wrong lane name), a different owner-facing claim entirely.
async function dropLane({
  workspaceRoot, goal, seat, askId = undefined, heartStore, spawnManager,
}) {
  if (!isSafeName(goal)) return { found: false, reason: 'bad-name', detail: 'goal is not a bare safe name' };
  if (!isSafeName(seat)) return { found: false, reason: 'bad-name', detail: 'seat is not a bare safe name' };
  if (!liveGoals(workspaceRoot).includes(String(goal))) {
    return { found: false, reason: 'no-such-goal', detail: `${goal} is not a live goal` };
  }

  // STEP 1 — stop anything live, BEFORE anything is marked. Nothing live is a clean no-op
  // straight to step 2, exactly as it was when this composition ran client-side.
  const liveRow = findLiveExecutionForLane(heartStore, workspaceRoot, goal, seat);
  let stoppedExecId = null;
  if (liveRow) {
    try {
      await spawnManager.kill(liveRow.exec_id);
      stoppedExecId = liveRow.exec_id;
    } catch (err) {
      return {
        found: true, goal, seat, stopFailed: true, stopError: err.message,
      };
    }
  }

  // STEP 2 — mark abandoned. `abandonSeat` is idempotent on a retried or already-dropped lane
  // (writers.js's own comment on the primary key) — this act function adds NO retry/dedupe logic
  // on top of it, since doing so would be a second copy of the ONE idempotency guarantee the
  // writer already gives. A raw store failure here (a real, rare arm — the input was already
  // validated) is its OWN named outcome, distinct from `stopFailed`: the stop already ran (or
  // nothing was live), so the caller's text must say the OPPOSITE half is now true.
  const store = bind(openEndingStoreFor(workspaceRoot));
  let abandonment;
  let idempotent;
  try {
    ({ abandonment, idempotent } = store.abandonSeat({
      goal,
      seat,
      anchor: 'owner: drop-lane (recovery thread) — this lane is stuck for good, no undo',
      abandoned_by: 'owner',
      ask_id: askId != null ? String(askId) : null,
    }));
  } catch (err) {
    return {
      found: true, goal, seat, markFailed: true, markError: err.message, stoppedExecId,
    };
  }
  return {
    found: true, goal, seat, idempotent, abandonment, stoppedExecId,
  };
}

module.exports = { dropLane };
