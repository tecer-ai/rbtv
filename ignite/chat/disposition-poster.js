'use strict';

// ── THE DISPOSITION POSTER: impl-slack FOR THE CLOSE-OR-KEEP ASK ─────────────────────────────────
// `supervisor/last-lane-ask.js`'s own header names the same split `exhaustion.js` states for the
// recovery ladder: "Posting (the Slack side, the act that flips posted to 1) is a SEPARATE, later
// act." This is that reader — `recovery-poster.js`'s own shape, adapted to the disposition
// record (one row per GOAL, already fully composed at mint time, never grouped by signature).
//
// ⚑ READS THROUGH THE GATEWAY, NEVER THE FILE DIRECTLY — same wall `recovery-poster.js` states:
//   `inspect disposition-asks` (a read-only TARGET, the same ce-5/D3 shape `inspect recovery-lanes`
//   already uses) is the ONLY way this process learns a disposition ask exists.
//
// ⚑ POSTING IS WHAT MAKES A DISPOSITION ASK STOP BEING RETURNED. The gateway stamps
//   `posted_ask_id` onto the record the moment the `record-owner-ask` open succeeds
//   (`dispatch.js`, beside `markDispositionPosted`) — so an ask this poster already posted is gone
//   from the NEXT `disposition-asks` read, and a crash between the post and the next read costs at
//   most one duplicate attempt, never a silent drop.
//
// ⚑ THIS RUNS ON EVERY BEAT, NOT A DIGEST SLOT — same reason `recovery-poster.js` gives: this
//   question is the owner's only exit from a goal stuck with nothing left owed, and it must not
//   wait for the next of ten daily digest slots to reach Slack.

const DEFAULT_INTERVAL_MS = 30_000;

function createDispositionPoster({
  forwarder,
  // The bridge's own `postOwnerAsk` (`chat-bridge.js`) — resolves the goal's channel and mints the
  // thread through the SAME door a recovery ask uses: `label: 'recovery'`, `kind: 'goal-disposition'`.
  postOwnerAsk,
  logger = null,
} = {}) {
  if (!forwarder || typeof forwarder.forward !== 'function') {
    throw new Error('createDispositionPoster requires the gateway forwarder — asks are read through `inspect disposition-asks`');
  }
  if (typeof postOwnerAsk !== 'function') {
    throw new Error('createDispositionPoster requires postOwnerAsk — posting is the bridge\'s own door');
  }
  const log = (level, message, fields = {}) => { if (logger) logger({ level, message, ...fields }); };

  async function checkAndPost() {
    let res;
    try {
      res = await forwarder.forward('inspect', { target: 'disposition-asks' });
    } catch (err) {
      log('warn', 'disposition asks NOT read — the gateway call threw; this pass is skipped', { error: err.message });
      return { checked: 0, posted: 0 };
    }
    if (!res.ok) {
      log('warn', 'disposition asks NOT read — the gateway refused', { error: (res.error && res.error.code) || 'unknown' });
      return { checked: 0, posted: 0 };
    }
    const rows = (res.result && Array.isArray(res.result.rows)) ? res.result.rows : [];
    let posted = 0;
    for (const row of rows) {
      // eslint-disable-next-line no-await-in-loop -- one thread at a time, in signature order —
      // `recovery-poster.js`'s own discipline: a burst of stuck goals must not become concurrent
      // Slack posts on the same beat.
      const out = await postOwnerAsk({
        goalId: row.goal,
        seatName: (Array.isArray(row.abandoned_seats) && row.abandoned_seats[0]) || row.goal,
        label: 'recovery',
        kind: 'goal-disposition',
        body: row.body,
      });
      if (out && out.posted === true) {
        posted += 1;
        log('info', 'disposition ask posted as its own answerable thread', {
          goal: row.goal, askId: out.askId,
        });
      } else {
        log('warn', 'disposition ask NOT posted', {
          goal: row.goal, reason: out && out.reason,
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
        .catch((err) => log('warn', 'disposition poster pass THREW — skipped, the next beat retries', { error: err.message }));
    }, intervalMs);
    if (timer.unref) timer.unref();
    log('info', 'disposition poster started', { intervalMs });
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

module.exports = { createDispositionPoster };
