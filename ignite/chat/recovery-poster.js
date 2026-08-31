'use strict';

// ── THE RECOVERY POSTER: `impl-slack` FOR THE EXHAUSTION EXIT ────────────────────────────────────
// `supervisor/exhaustion.js`'s own header names the gap this closes: "NO SLACK, NO OUTBOX, NOT ONE
// BYTE. This module writes a RECORD and stops... impl-slack reads the record and does the posting."
// This is that reader. `d-ask14-recovery-thread-shape` (a): each lane gets its OWN thread, in its
// OWN goal's channel — so the thread itself is the reply's address and no lane can be misrouted.
//
// ⚑ READS THROUGH THE GATEWAY, NEVER THE FILE DIRECTLY. This subtree holds no store handle and no
//   sibling reach into `supervisor/` (`probes/probe-chat-boundary.js`) — `inspect recovery-lanes`
//   (a read-only TARGET, not a new intent — the same ce-5/D3 shape `inspect asks` already uses) is
//   the ONLY way this process learns a lane exists.
//
// ⚑ POSTING IS WHAT MAKES A LANE STOP BEING RETURNED. The gateway stamps `posted_ask_id` onto the
//   lane's file record the moment the `record-owner-ask` open succeeds (`dispatch.js`, beside
//   `markLanePosted`) — so a lane this poster already posted is gone from the NEXT `recovery-lanes`
//   read, and a crash between the post and the next read costs at most one duplicate attempt, never
//   a silent drop (`postOwnerAsk` itself is idempotent per Slack ack; a genuine double-post here
//   would be visible as two threads, not as silence).
//
// ⚑ THIS RUNS ON EVERY BEAT, NOT ON A DIGEST SLOT. A recovery ask is the owner's exit from a dead
//   end — it must not wait for the next of ten daily digest slots to reach Slack.

const DEFAULT_INTERVAL_MS = 30_000;

// The ruled ladder, verbatim [T1-R8, D-2-ruling]. `chat/` may not `require()`
// `supervisor/exhaustion.js#ASK_OPTIONS` (`probe-chat-boundary.js`) — this is the same hand-kept
// second copy `reply-grammar.js#RECOVERY_TOKENS` already carries, for the same reason.
const OPTIONS_LINE = 'Reply with one word: retry-with-change · drop-lane · pause-goal';

function composeRecoveryBody(lane) {
  const lines = [
    `*LANE*: ${lane.goal} / ${lane.seat}`,
    `driver: ${lane.driver || 'unknown'} · reason: ${lane.reason_class || 'unknown'} · attempts: ${lane.attempts == null ? '?' : lane.attempts}`,
    '',
    String(lane.refusal_text || '(no refusal text recorded)').trim(),
    '',
    OPTIONS_LINE,
    'Comments after the first word.',
  ];
  return lines.join('\n');
}

function createRecoveryPoster({
  forwarder,
  // The bridge's own `postOwnerAsk` (`chat-bridge.js`) — resolves the goal's channel and mints the
  // thread through the SAME door a work-content ask uses, `label: 'recovery'`.
  postOwnerAsk,
  logger = null,
} = {}) {
  if (!forwarder || typeof forwarder.forward !== 'function') {
    throw new Error('createRecoveryPoster requires the gateway forwarder — lanes are read through `inspect recovery-lanes`');
  }
  if (typeof postOwnerAsk !== 'function') {
    throw new Error('createRecoveryPoster requires postOwnerAsk — posting is the bridge\'s own door');
  }
  const log = (level, message, fields = {}) => { if (logger) logger({ level, message, ...fields }); };

  async function checkAndPost() {
    let res;
    try {
      res = await forwarder.forward('inspect', { target: 'recovery-lanes' });
    } catch (err) {
      log('warn', 'recovery lanes NOT read — the gateway call threw; this pass is skipped', { error: err.message });
      return { checked: 0, posted: 0 };
    }
    if (!res.ok) {
      log('warn', 'recovery lanes NOT read — the gateway refused', { error: (res.error && res.error.code) || 'unknown' });
      return { checked: 0, posted: 0 };
    }
    const rows = (res.result && Array.isArray(res.result.rows)) ? res.result.rows : [];
    let posted = 0;
    for (const lane of rows) {
      // eslint-disable-next-line no-await-in-loop -- one thread at a time, in signature order; a
      // burst of N failed lanes must not become N concurrent Slack posts on the same beat.
      const out = await postOwnerAsk({
        goalId: lane.goal,
        seatName: lane.seat,
        label: 'recovery',
        kind: 'recovery',
        body: composeRecoveryBody(lane),
      });
      if (out && out.posted === true) {
        posted += 1;
        log('info', 'recovery lane posted as its own answerable thread', {
          goal: lane.goal, seat: lane.seat, askId: out.askId,
        });
      } else {
        log('warn', 'recovery lane NOT posted', {
          goal: lane.goal, seat: lane.seat, reason: out && out.reason,
        });
      }
    }
    return { checked: rows.length, posted };
  }

  let timer = null;
  let checking = false;

  function start(intervalMs = DEFAULT_INTERVAL_MS) {
    if (timer) return { started: false, reason: 'already-running' };
    timer = setInterval(() => {
      if (checking) return;   // one pass at a time — same discipline as glance.js's slot driver
      checking = true;
      checkAndPost().finally(() => { checking = false; })
        .catch((err) => log('warn', 'recovery poster pass THREW — skipped, the next beat retries', { error: err.message }));
    }, intervalMs);
    if (timer.unref) timer.unref();
    log('info', 'recovery poster started', { intervalMs });
    return { started: true, intervalMs };
  }

  function stop() {
    if (!timer) return { stopped: false };
    clearInterval(timer);
    timer = null;
    return { stopped: true };
  }

  return {
    checkAndPost, start, stop,
  };
}

module.exports = { createRecoveryPoster, composeRecoveryBody, OPTIONS_LINE };
