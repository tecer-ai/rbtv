'use strict';

// ── THE OWNER-NOTIFICATION PATH FOR A QUEUED START (task 7.77 → 7.130 / M4-15) ──────────────────
//
// R9's one-live-execution rule (`one-live-run.js`, 7.129 / M4-14) declines to fire a scheduled start
// that lands while the same goal is EXECUTING. THIS file is the other half of that rule: the half a
// human can see.
//
// WHY THE OTHER HALF IS NOT OPTIONAL. From outside the box, a start that was silently held is
// indistinguishable from a start that was never scheduled at all. Both look like nothing happened.
// The queue row is observable — it sits in the `queue` table with its due `run_at` — but observable
// is not the same as OBSERVED, and nobody polls a table they have no reason to suspect. So the
// queueing announces itself.
//
// ⚠ WHAT THIS FILE DOES NOT DO, STRUCTURALLY AND NOT BY PROMISE. It holds no queue handle, no store
// handle and no decision. It cannot start an execution, cannot cancel one, and cannot turn a queued row
// into a skipped one, because it has nothing to call that would do any of those things. That is
// deliberate: 7.77 designs out the failure where a broken notification quietly becomes a dropped
// start, and the cheapest way to make that impossible is to give the notifier no power to do it.
// The rule decides; this reports. A notification that never lands leaves a queued row queued.
//
// ⚠ IT NEVER THROWS. `dispatch()` calls this per due row, and 7.129 measured what an exception on
// that path costs: a `TypeError` out of the gate killed the whole tick at its first row — advance
// already done, every later due row unserved. A delivery is a NETWORK-SHAPED act, so it is the most
// likely thing on the path to fail, and it is the last thing that may take the scheduler with it.
// Every failure — a deliverer that returns `{delivered:false}`, a deliverer that throws, a
// deliverer that is missing — comes back as a RESULT, never as an exception.
//
// ⚠ THE DELIVERER IS INJECTED, AND THE DAEMON'S IS CREDENTIAL-FREE. This module renders and routes;
// it opens no socket and reads no token. The ticker wires `ownerFeedDeliverer` — a write to the
// daemon's own `owner-feed` thread, which needs no credential and reaches nothing outside the box.
// A credentialed transport (the chat bridge's Slack `sendToOwner`) is a valid deliverer and the
// send capture for `M4-15` was taken through one, but NOTHING HERE RESOLVES ONE: there is no env
// var, no config key and no code path by which a running daemon acquires it. Arming the daemon to
// reach Slack is a cutover, and a cutover is gated (`decisions.md#r-cutover-gated`; leader ruling,
// message #241 of run-3). A caller that wants Slack passes the deliverer in, at the call, in the
// open.
//
// ⚠ ONCE PER QUEUED ROW, NOT ONCE PER TICK. A queued row is re-evaluated EVERY tick and stays due
// until the goal's execution ends, so a notifier with no memory would announce the same held start
// every tick interval for as long as it lasts — hours of identical messages, which trains a reader
// to ignore the channel and is a worse outcome than silence. The dedupe key is
// `queue-id | reason`, so a CHANGE of reason (the lease became unreadable; a second room appeared)
// notifies again, because that is new information. The cache is a bounded insertion-ordered `Map`,
// oldest evicted — the same in-memory-by-design idiom the chat bridge's Slack event dedupe uses,
// and it is lost on restart, which re-announces each still-queued row exactly once. Re-announcing
// once after a restart is the right side to err on: the alternative is a held start that went
// unmentioned because a process bounced.

// The `action` value this path fires on. It is `one-live-run.js`'s `QUEUED` and is imported rather
// than re-spelled: two files that separately spell one vocabulary word can drift apart, and the
// notifier would then go silent on the exact event it exists for while every check still passed.
const { QUEUED } = require('./one-live-run');

// Bounded dedupe cache. Not a policy number — no floor, no cap, nothing from `budget.json`; it is
// the memory ceiling of an in-process Map, chosen to match the chat bridge's own dedupe bound.
const MAX_REMEMBERED = 500;

// Why a notification did not go out. Every value means "nothing was delivered"; they differ in
// whether that was correct.
const SKIPPED = {
  NOT_A_QUEUE_EVENT: 'not-a-queue-event', // correct: this event is not R9's queue event
  ALREADY_NOTIFIED: 'already-notified',   // correct: this queued row was announced already
  NO_DELIVERER: 'no-deliverer',           // NOT correct: a misconfiguration, surfaced as a failure
};

function describeNotifier() {
  return [
    `fires on: an event whose action === "${QUEUED}" — R9's queue event, and no other event`,
    'dedupe: once per `queue-id | reason`; a changed reason re-notifies; bounded in-memory, lost on restart',
    'names: the goal, the held scheduled start (job, queue row, due time) and the LIVE LEASE that held it',
    'deliverer: INJECTED. The daemon wires the credential-free owner feed; nothing here resolves a credentialed one',
    'on a failed or throwing send: surfaced as {delivered:false, error} — never thrown, never retried in-tick',
    'the queueing is untouched either way: this path holds no queue handle and cannot skip a start',
    'thresholds: none — this path reads no policy number',
  ].join('\n');
}

// A room may arrive as a string (the one room of a live lease), an array (the more-than-one case
// names every room) or null (the lease could not be read at all). All three are reported as
// themselves — "unknown" is a fact worth printing, and inventing a single name from an array would
// name a room the lease never picked.
function formatRoom(value) {
  if (Array.isArray(value)) return value.length ? value.join(', ') : '(none named)';
  if (value === null || value === undefined || value === '') return '(not readable)';
  return String(value);
}

function formatField(value) {
  if (value === null || value === undefined || value === '') return '(unknown)';
  return String(value);
}

// THE NOTICE. Criterion 3 of this task's done contract: a reader must be able to act on it WITHOUT
// opening anything, so both halves of the event are spelled out in full — which start was held, and
// which lease held it — rather than referred to by an id the reader would have to go resolve.
//
// The closing line is load-bearing, not reassurance: the single most likely wrong conclusion from
// "it did not start" is that it was lost and must be re-scheduled by hand, and a re-scheduled
// start is a second queue row racing the first. Saying it resumes by itself is what stops that.
function renderQueuedStartNotice(event) {
  const start = (event && event['scheduled-start']) || {};
  const found = (event && event['live-lease']) || {};
  const lines = [
    "ignite: a scheduled start was QUEUED, not started — the goal is already EXECUTING.",
    `  goal:           ${formatField(start.goal)}`,
    `  start held:     job ${formatField(start['job-id'])} (queue row ${formatField(start['queue-id'])})`
      + `, due ${formatField(start['run-at'])}, trigger ${formatField(start['trigger-kind'])}`,
    `  lease held by:  room ${formatRoom(found.rooms && found.rooms.length ? found.rooms : found['room'])}`
      + ` (state ${formatField(found.state)}, ${formatField(found.count)} room(s))`,
    `  evidence:       ${formatField(found.register)}`,
    `  reason:         ${formatField(event && event.reason)}`,
  ];
  if (found.reason) lines.push(`  detail:         ${found.reason}`);
  lines.push(
    '  not lost:       the queue row keeps its due time and starts by itself once that execution ends.',
    '                  Do NOT re-schedule it by hand — a second row would race the first.',
  );
  return lines.join('\n');
}

// THE PATH. Returns a result; never throws. The caller decides what to record — this module has no
// opinion about tick actions and no handle to write one.
//
// Result shapes, all four:
//   { notified: false, skipped: 'not-a-queue-event' }             nothing to announce, correct
//   { notified: false, skipped: 'already-notified', key }         announced before, correct
//   { notified: true,  delivered: true,  ts, text }               it landed
//   { notified: true,  delivered: false, error, text }            it did not — SURFACED, not swallowed
function createQueuedStartNotifier({ deliver, maxRemembered = MAX_REMEMBERED } = {}) {
  const seen = new Map();

  function remember(key) {
    seen.set(key, true);
    // Insertion-ordered eviction: the oldest key is the first the iterator yields.
    while (seen.size > maxRemembered) {
      const oldest = seen.keys().next().value;
      seen.delete(oldest);
    }
  }

  // `context` is passed through to the deliverer UNREAD — this module never looks inside it. The
  // ticker's owner-feed deliverer needs the tick's `now` and tick number (they are `recordOwnerNote`'s
  // other two arguments), and those change every tick while the notifier and its dedupe cache are
  // built once and must outlive them. Threading them through the call keeps that state out of a
  // mutable holder the two would otherwise have to share.
  async function notifyQueuedStart(event, context = {}) {
    // Criterion 1: this path fires on R9's queue event and on NO other event. The test is the
    // event's own `action` field, not the caller's good intentions — a caller that hands this a
    // `start` decision, a defer, or a half-built object gets nothing delivered.
    if (!event || event.action !== QUEUED) {
      return { notified: false, skipped: SKIPPED.NOT_A_QUEUE_EVENT };
    }

    const start = event['scheduled-start'] || {};
    const key = `${start['queue-id']}|${event.reason}`;
    if (seen.has(key)) return { notified: false, skipped: SKIPPED.ALREADY_NOTIFIED, key };

    const text = renderQueuedStartNotice(event);

    if (typeof deliver !== 'function') {
      // A missing deliverer is a MISCONFIGURATION, not a quiet no-op, so it is reported with the
      // same `delivered: false` shape a network failure gets and the caller surfaces it the same
      // way. Not remembered: a later tick with a repaired deliverer must still announce this row.
      return { notified: true, delivered: false, error: SKIPPED.NO_DELIVERER, text };
    }

    // Remembered BEFORE the await, not after. Two ticks can overlap on an async deliverer, and a
    // key written only on success would let the second tick past the dedupe while the first is
    // still in flight — a duplicate announcement in exactly the retry-shaped case where a reader is
    // least able to tell two events from one. The cost of this order is that a FAILED send is not
    // re-announced on the next tick; the failure is surfaced to the caller instead, which is where
    // a delivery problem belongs. A changed reason still re-notifies, since it is a different key.
    remember(key);

    try {
      const result = await deliver(text, event, context);
      if (result && result.delivered) {
        return { notified: true, delivered: true, ts: result.ts || null, text };
      }
      return { notified: true, delivered: false, error: (result && result.error) || 'delivery-refused', text };
    } catch (err) {
      // Contained for the reason in this file's header: a throw here abandons the whole tick. The
      // message rides out in the result so the caller can record it — contained is not silent.
      return { notified: true, delivered: false, error: (err && err.message) || String(err), text };
    }
  }

  return notifyQueuedStart;
}

// THE DAEMON'S DELIVERER. A note on the `owner-feed` thread — the daemon's own owner surface, the
// same one every stall warning and crash note uses. No credential, no socket, nothing that leaves
// the box. `recordOwnerNote` is passed in rather than imported because it is a closure over the
// ticker's store and tick number, and because a deliverer that reaches into another module for a
// store handle is the coupling this file's header refuses.
function ownerFeedDeliverer(recordOwnerNote) {
  return async function deliverToOwnerFeed(text, event, context = {}) {
    const msg = recordOwnerNote(text, context.now, context.tick);
    return { delivered: Boolean(msg && msg.msg_id), ts: msg && msg.created_at ? msg.created_at : null };
  };
}

// A CREDENTIALED DELIVERER, BUILT FROM THE BRIDGE'S OWN SENDER — never a second `chat.postMessage`.
// `sendToOwner` is `slack-socket-mode.js`'s, passed in by the caller that already holds the bot
// token; this function adds a channel and a result shape and nothing else. Two implementations of
// one delivery path drift apart exactly the way two readers of one register do (`issues.md` G-301),
// and this wave has met that shape three times.
//
// ⚠ NOTHING IN THE DAEMON CALLS THIS. It is reachable only from a caller that constructs it
// explicitly and supplies its own transport. Wiring it into the ticker is a cutover
// (`decisions.md#r-cutover-gated`), and `r-slack-etiquette` bounds where its traffic may go:
// `test-*` channels only, no direct message to the owner. The token never passes through here —
// it lives inside the transport the caller built.
function chatTransportDeliverer({ sendToOwner, channel }) {
  if (typeof sendToOwner !== 'function') throw new Error('chatTransportDeliverer needs a sendToOwner function');
  if (!channel) throw new Error('chatTransportDeliverer needs a channel');
  return async function deliverToChat(text) {
    const r = await sendToOwner({ channel, threadTs: null, text });
    return { delivered: Boolean(r && r.delivered), ts: r && r.ts, error: r && r.error };
  };
}

module.exports = {
  createQueuedStartNotifier,
  renderQueuedStartNotice,
  ownerFeedDeliverer,
  chatTransportDeliverer,
  describeNotifier,
  SKIPPED,
  MAX_REMEMBERED,
};
