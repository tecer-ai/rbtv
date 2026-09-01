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

// The ruled ladder [T1-R8, D-2-ruling], as the CONTRACT's own `options` shape
// (`chat-bridge.js#postOwnerAsk`'s new `options` field, `redesign-continue-1` seat `recovery-story`
// against the fixed interface `ask-marker-footer`/`ask-letters` build in parallel). `arm` is always
// one of `reply-grammar.js`'s existing recovery tokens — never a new vocabulary. `chat/` may not
// `require()` `supervisor/exhaustion.js#ASK_OPTIONS` (`probe-chat-boundary.js`) — this is the same
// hand-kept second copy `reply-grammar.js#RECOVERY_TOKENS` already carries, for the same reason.
const RECOVERY_OPTIONS = Object.freeze([
  { letter: 'a', arm: 'retry-with-change', text: 'restart it once more, with an instruction you type after the letter' },
  { letter: 'b', arm: 'drop-lane', text: "drop this seat's work and let the rest of the goal continue without it" },
  { letter: 'c', arm: 'pause-goal', text: 'pause the whole goal until you look at it' },
]);

// A driver's plain-words identity — R-A4/DoD 3: never the raw `reason_class`/`driver` token on the
// owner's phone. `outcome` (this pass's own launch attempt, `action.kind`) takes priority over the
// lane's `reason_class` when the two disagree: a seat mid-`incomplete`-relaunch whose LAUNCH itself
// keeps being refused is a "cannot be started" story, not a "keeps quitting" one.
function subjectFor(lane) {
  const seat = lane.seat || 'this seat';
  if (lane.outcome === 'launch-refused') return `the ${seat} seat cannot be started`;
  if (lane.reason_class === 'unread') return `the ${seat} seat keeps failing to start`;
  if (lane.reason_class === 'incomplete') return `the ${seat} seat keeps quitting before finishing`;
  return `the ${seat} seat needs your attention`;
}

// Elapsed-time words for the counter's own `first_at`/`last_at` span — DoD 3's "over what span".
// Deliberately coarse (minutes/hours only): this is one line on a phone screen, not a report.
function spanWords(firstAt, lastAt) {
  if (!firstAt || !lastAt) return '';
  const ms = Date.parse(lastAt) - Date.parse(firstAt);
  if (!Number.isFinite(ms) || ms <= 0) return '';
  const mins = Math.round(ms / 60000);
  if (mins < 1) return '';
  if (mins < 60) return ` over ${mins} minute${mins === 1 ? '' : 's'}`;
  const hrs = Math.round(mins / 60);
  return ` over ${hrs} hour${hrs === 1 ? '' : 's'}`;
}

function whatHappenedFor(lane) {
  const seat = lane.seat || 'this seat';
  const n = lane.attempts == null ? 'several' : lane.attempts;
  const times = `${n} time${n === 1 ? '' : 's'}`;
  const span = spanWords(lane.first_at, lane.last_at);
  if (lane.outcome === 'launch-refused') {
    return `What happened: I tried to start ${seat} ${times}${span} and it refused to launch every time.`;
  }
  if (lane.reason_class === 'unread') {
    return `What happened: ${seat} had unread messages waiting, so I restarted it to read them. I tried ${times}${span} with no change.`;
  }
  if (lane.reason_class === 'incomplete') {
    return `What happened: ${seat} said it wasn't finished, so I restarted it to continue. I tried ${times}${span}; it ended the same way every time.`;
  }
  return `What happened: I tried to move this forward ${times}${span} and it did not progress.`;
}

// R-A4 point 2 — the seat's OWN last words, trimmed to ≤3 lines; `(none…)` when there is
// structurally nothing seat-authored to quote (`unread`, `room`, or any lane `reconcile.js` never
// found a `who_stamped: 'seat'` ending for) [`inv-refusal-source`].
function lastWordsLine(lane) {
  const raw = String(lane.last_words || '').trim();
  if (!raw) return 'Its last words: (none — it never got far enough to say anything)';
  const trimmed = raw.split(/\r?\n/).filter((l) => l.trim()).slice(0, 3).join('\n');
  return `Its last words: ${trimmed}`;
}

// N identical failures recommend `pause-goal` [assumption confirmed to the owner, §2 assumptions].
// In practice every lane reaching this poster already IS an N-failure lane — this function only
// exists as an ask record ever reaches `recovery-lanes` at exhaustion, i.e. `attempts` at or past
// the configured bound — so this is the ordinary case, not a rare one; a lane with no attempt count
// at all (`relaunch-budget.js`'s leader-escalation ask, which shares this same record shape and
// poster but is not attempt-counter-driven) falls back to the plain retry instead.
function recommendedLetter(lane) {
  return (lane.attempts != null && lane.attempts >= 3) ? 'c' : 'a';
}

function whyFor(letter, lane) {
  if (letter === 'c') return `${lane.attempts} identical failures mean another blind restart will not help`;
  return 'nothing has been tried on this lane yet';
}

function optionsFor(lane) {
  const rec = recommendedLetter(lane);
  return RECOVERY_OPTIONS.map((o) => (o.letter === rec
    ? { ...o, recommended: true, why: whyFor(rec, lane) }
    : { ...o, recommended: false }));
}

// The CONTRACT shape `chat-bridge.js#postOwnerAsk` takes [`redesign-continue-1` interface]:
// `subject` (one plain sentence), `body` (the three labelled lines), `options` (the letter table),
// `more` (a vault-relative pointer or null). `ask-thread.js#postAsk` owns rendering these into the
// reserved-first-line message — this function never assembles Slack markup itself.
function composeRecoveryBody(lane) {
  return {
    subject: subjectFor(lane),
    body: [
      whatHappenedFor(lane),
      lastWordsLine(lane),
      'Question: what should I do with this seat?',
    ].join('\n'),
    options: optionsFor(lane),
    more: lane.evidence_pointer || null,
  };
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
      const composed = composeRecoveryBody(lane);
      const out = await postOwnerAsk({
        goalId: lane.goal,
        seatName: lane.seat,
        label: 'recovery',
        kind: 'recovery',
        subject: composed.subject,
        body: composed.body,
        options: composed.options,
        more: composed.more,
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

module.exports = { createRecoveryPoster, composeRecoveryBody, RECOVERY_OPTIONS };
