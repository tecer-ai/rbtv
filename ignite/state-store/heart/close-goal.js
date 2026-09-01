'use strict';

// ── `close-goal` — stamp a goal `closed` (owner gave up on it), RUN DAEMON-SIDE ─────────────────
// (owner rulings `d-recovery-last-lane-asks`, `d-goal-closed-word`, `redesign-continue-1`).
//
// THE GAP THIS CLOSES. `disposition-post` (756e29d5) wired the close-or-keep ask's `close` reply
// to a `closeGoal` port and shipped it `null` — `state-store/vocabulary.js#GOAL_WORDS` had no
// terminal word for "given up on, not a success" (`finished` is the only terminal word and every
// downstream reader treats it as ordinary success). `d-goal-closed-word` mints the fourth word;
// this is the SEVENTEENTH intent's act function, the same shape `drop-lane`
// (`state-store/heart/drop-lane.js`) and `pause-resume` (`./pause-resume.js`) already use: the
// bridge is a SEPARATE PROCESS walled off from the store (`chat/probes/probe-chat-boundary.js`),
// so the write happens here, behind the gateway's `close-goal` intent, never in `chat/`.
//
// Same ending-store resolution as `pause-resume.js`/`drop-lane.js`, same reason: the file the lane
// gate reads (`supervisor/ending-reads.js`), never the daemon's private lane store
// (`pause-resume.js`'s "THE ENDING HOME" note is the full argument).
//
// `closed` is TERMINAL and has no undo path — unlike `paused`, there is no `resume` for it. A goal
// already `finished` is refused (nothing to close, it already ended); a goal already `closed` is a
// no-op (idempotent on a retried reply or a repeated `close`, same shape `abandonSeat` gives
// `drop-lane`).
const { bind, openEndingStoreFor } = require('..');
const { isSafeName } = require('../../chat/bus-ferry');
const { liveGoals } = require('./pause-resume');

async function closeGoal({ workspaceRoot, goal, askId = undefined }) {
  if (!isSafeName(goal)) return { found: false, reason: 'bad-name', detail: 'goal is not a bare safe name' };
  if (!liveGoals(workspaceRoot).includes(String(goal))) {
    return { found: false, reason: 'no-such-goal', detail: `${goal} is not a live goal` };
  }

  const store = bind(openEndingStoreFor(workspaceRoot));
  const before = store.getGoalState(goal);
  if (before && before.stored === 'closed') {
    return {
      found: true, goal, idempotent: true, state: before,
    };
  }
  if (before && before.stored === 'finished') {
    return {
      found: true, goal, refused: true, reason: 'finished', detail: `${goal} is already finished — there is nothing to close.`,
    };
  }

  const evidencePointer = `owner close reply · disposition ask${askId ? ` ${askId}` : ''}`;
  let state;
  try {
    state = store.writeGoalWord({
      goal, stored: 'closed', who_stamped: 'owner', evidence_pointer: evidencePointer,
    });
  } catch (err) {
    return {
      found: true, goal, markFailed: true, markError: err.message,
    };
  }
  return {
    found: true, goal, idempotent: false, state,
  };
}

module.exports = { closeGoal };
