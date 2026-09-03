'use strict';

// ── THE DISPOSITION POSTER: impl-slack FOR THE CLOSE-OR-KEEP ASK ─────────────────────────────────
// `supervisor/last-lane-ask.js`'s own header names the same split `exhaustion.js` states for the
// recovery ladder: "Posting (the Slack side, the act that flips posted to 1) is a SEPARATE, later
// act." This is that reader — `recovery-poster.js`'s own shape, adapted to the disposition
// record (one row per GOAL, never grouped by signature). `composeDispositionBody` below composes
// the CONTRACT fields fresh from the record's raw fields, mirroring `composeRecoveryBody` — the
// body is never pre-rendered at mint time [`redesign-continue-1`, DoD 4].
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

const path = require('node:path');

const DEFAULT_INTERVAL_MS = 30_000;

// The ruled ladder [`d-recovery-last-lane-asks`], as the CONTRACT's own `options` shape — same
// interface `recovery-poster.js#RECOVERY_OPTIONS` builds against, fixed by the orchestrator for
// `redesign-continue-1`. `arm` is `reply-grammar.js`'s existing disposition-ladder tokens
// (`keep`/`close`), never a new vocabulary.
const DISPOSITION_OPTIONS_TABLE = Object.freeze([
  { letter: 'a', arm: 'keep', text: 'leave this goal open — nothing more is owed and nothing launches on its own' },
  { letter: 'b', arm: 'close', text: 'close the goal (given up on, not a success)' },
]);

// DoD 4: recommend `keep` UNLESS every abandoned lane was dropped by the owner themselves — the
// owner explicitly choosing `drop-lane` on every remaining lane already signals they are done with
// this goal, so `close` is the one worth marking. `abandoned_by` is `state-store/writers.js`'s own
// required field (`abandonSeat` refuses to write the row without it), never absent.
function everyLaneDroppedByOwner(abandonedSeats) {
  return abandonedSeats.length > 0 && abandonedSeats.every((a) => a.abandoned_by === 'owner');
}

function recommendedLetter(abandonedSeats) {
  return everyLaneDroppedByOwner(abandonedSeats) ? 'b' : 'a';
}

function whyFor(letter, abandonedSeats) {
  if (letter === 'b') return 'you dropped every lane still owed on this goal yourself';
  return 'not every dropped lane here was your own call';
}

function optionsFor(abandonedSeats) {
  const rec = recommendedLetter(abandonedSeats);
  return DISPOSITION_OPTIONS_TABLE.map((o) => (o.letter === rec
    ? { ...o, recommended: true, why: whyFor(rec, abandonedSeats) }
    : { ...o, recommended: false }));
}

// "which was the last piece of work and how it ended" [DoD 4] — `anchor` is the closest thing an
// abandoned lane's own record carries to "how it ended" (the drop reason, in the owner's own
// words when the drop itself was a reply to a recovery ask).
function whatHappenedFor(goal, abandonedSeats) {
  const parts = abandonedSeats.map((a) => (a.anchor ? `${a.seat} (${a.anchor})` : a.seat));
  return `What happened: every lane still owed work on this goal was dropped: ${parts.join(', ')}.`;
}

// The CONTRACT shape `chat-bridge.js#postOwnerAsk` takes [`redesign-continue-1` interface] — the
// same fields `recovery-poster.js#composeRecoveryBody` produces, composed fresh from the raw row
// `supervisor/last-lane-ask.js#listUnpostedDispositions` returns, never from a mint-time string.
function composeDispositionBody(row) {
  const abandonedSeats = Array.isArray(row.abandoned_seats) ? row.abandoned_seats : [];
  return {
    subject: 'the goal has nothing left to run',
    body: [
      whatHappenedFor(row.goal, abandonedSeats),
      'Question: keep the goal open or close it?',
    ].join('\n'),
    options: optionsFor(abandonedSeats),
    more: path.join('.rbtv', 'goals', String(row.goal)),
  };
}

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
      const composed = composeDispositionBody(row);
      const firstAbandoned = Array.isArray(row.abandoned_seats) ? row.abandoned_seats[0] : null;
      const out = await postOwnerAsk({
        goalId: row.goal,
        seatName: (firstAbandoned && firstAbandoned.seat) || row.goal,
        label: 'recovery',
        kind: 'goal-disposition',
        subject: composed.subject,
        body: composed.body,
        options: composed.options,
        more: composed.more,
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

module.exports = { createDispositionPoster, composeDispositionBody, DISPOSITION_OPTIONS_TABLE };
