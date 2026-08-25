'use strict';

// ask-store — the bridge's SENDER for the owner-ask record. It holds no record and no handle: it
// turns the bridge's vocabulary into `record-owner-ask` gateway calls and reports what came back.
//
// ⚠ `owner-asks.json` IS GONE, AND THIS FILE IS WHY IT COULD GO. `spec-state-store` §3 makes the
// daemon-owned `open_asks` table in `heart.db` the ONE record of an owner ask, so a seat's wait is
// DERIVED (§2.1: an ask that is `posted` and still `open`) instead of stored in a file a second
// component owns. The bridge could not simply write that table — `bridges/chat` runs as a SEPARATE
// PROCESS and `probes/probe-chat-boundary.js` forbids a store handle, a child process and a
// sibling require here, because a write from this process would be a second WRITER PROCESS into
// `heart.db` (spec §7). The owner ruled option (a) on 2026-08-24
// (`redesign-implementation/decisions.md`): ask-writes get their own gateway intent, and the
// daemon stamps the table. That is the same authorizing shape the twelfth intent
// (`record-bus-answer`) cites, and the same division of labour — the bridge keeps a caller, the
// capability stays server-side (`server/heart/ask-record.js`).
//
// TWO CONSEQUENCES FOLLOW, AND NEITHER IS AN OVERSIGHT:
//
//   1. `ask_id` IS THE SLACK THREAD [T5-R7]. No allocator, no per-seat queue of asks. A second
//      owner message in a thread that already carries an open ask is the SAME ask; a genuinely new
//      question arrives in a new thread and mints a new record. The pre-D89 "a reply settles the
//      OLDEST open ask" rule is DELETED [D-4-ruling, T1-R12] — an authorized reply releases the ask
//      bound to THAT EXACT thread, which is why `reapAsk` requires a thread and refuses without it.
//   2. NOTHING HERE WRITES A SEAT ENDING. Resolution reaps the ask and signals the bound seat's
//      relaunch in ONE transaction (§2.8), daemon-side. This module only asks for that.
//
// ⚠ EVERY FAILURE IS A LOG, NEVER A THROW AND NEVER A CHANGED COURSE. Both callers run AFTER the
// owner's message has been delivered, so the bookkeeping must not be able to undo the act. A
// refusal that reached the owner as a failed message would be a lie about one that landed.

const ASK_LABEL_DEFAULT = 'work-content';

function createAskRecord({ forwarder, logger = null }) {
  const log = (level, message, fields) => {
    if (logger) logger({ level, message, ...fields });
  };

  async function send(payload, what, fields) {
    try {
      const res = await forwarder.forward('record-owner-ask', payload);
      if (!res.ok) {
        log('warn', `${what} — the gateway REFUSED the record; the message was still delivered`,
          { ...fields, error: (res.error && res.error.code) || 'unknown' });
        return { recorded: false, error: (res.error && res.error.code) || 'unknown' };
      }
      if (!res.result || res.result.recorded !== true) {
        log('warn', `${what} — the daemon recorded nothing; the message was still delivered`,
          { ...fields, reason: res.result && res.result.reason });
        return { recorded: false, reason: (res.result && res.result.reason) || 'unknown' };
      }
      return { recorded: true, ...res.result };
    } catch (err) {
      log('warn', `${what} — the record call THREW; the message was still delivered`,
        { ...fields, error: err.message });
      return { recorded: false, error: err.message };
    }
  }

  // THE READ SIDE — every OPEN owner ask, ALL GOALS, for the 2-hourly system digest (§5). One
  // ordinary `inspect` call, for the same reason the two write acts are gateway calls: the record
  // is `open_asks` in `heart.db` and this process may not open it. `inspect asks` is a read-only
  // TARGET of the existing intent (ce-5/D3), never a new one — the bridge still holds "no new
  // intent of its own".
  //
  // ⚠ A FAILED READ ANSWERS `null`, NEVER `[]`. An empty list is a real answer ("nothing is
  // waiting on the owner") and the digest's changed-only comparison acts on it: a gateway outage
  // rendered as `[]` would post "• none open" and then re-post every ask when the daemon came
  // back. `null` is what lets the caller skip the slot instead of lying about it.
  async function listOpenAsks() {
    try {
      const res = await forwarder.forward('inspect', { target: 'asks' });
      if (!res.ok) {
        log('warn', 'open asks NOT read — the gateway refused; this digest slot is skipped rather than posted empty',
          { error: (res.error && res.error.code) || 'unknown' });
        return null;
      }
      const rows = res.result && Array.isArray(res.result.rows) ? res.result.rows : null;
      if (!rows) {
        log('warn', 'open asks NOT read — the daemon returned no rows array; this digest slot is skipped', {});
        return null;
      }
      return rows;
    } catch (err) {
      log('warn', 'open asks NOT read — the read call THREW; this digest slot is skipped', { error: err.message });
      return null;
    }
  }

  // Record an owner ask on `seat` in `goalId`, keyed by the Slack thread it arrived in.
  //
  // Called only after the forward landed (`forward-path.js` gates on `outcome.forwarded === true`),
  // which is what lets the daemon mark the row `posted` at insert — §2.1 reads that flag, and a row
  // left unposted is an ask nobody is waiting on.
  async function openAsk({ goalId, seat, chatThreadId, text, label = ASK_LABEL_DEFAULT }) {
    const thread = chatThreadId != null ? String(chatThreadId) : '';
    if (!thread) {
      log('warn', 'owner-ask NOT recorded — no thread id, and the thread IS the ask id [T5-R7]', { goalId, seat });
      return { recorded: false, reason: 'no-thread' };
    }
    const out = await send(
      { act: 'open', goal: String(goalId), seat: String(seat), thread, corpus: String(text || ''), label },
      'owner-ask NOT recorded — a seat waiting on this question will not read as waiting',
      { goalId, seat, thread });
    if (out.recorded && !out.already) {
      log('info', 'recorded an open owner ask', { goalId, seat, thread, askId: out.ask_id });
    }
    return out;
  }

  // Settle the ask a conformant owner-facing reply answered. `chatThreadId` is REQUIRED: it is the
  // address [D-4-ruling], and there is no oldest-open fallback to guess with.
  async function reapAsk({ goalId, seat, chatThreadId }) {
    const thread = chatThreadId != null ? String(chatThreadId) : '';
    if (!thread) {
      log('warn', 'owner-ask NOT reaped — no thread id, and a reply settles the ask in ITS OWN thread only', { goalId, seat });
      return { recorded: false, reason: 'no-thread' };
    }
    const out = await send(
      { act: 'reap', goal: String(goalId), seat: String(seat), thread },
      'owner-ask NOT reaped — the seat stays waiting to every reader even though this reply landed',
      { goalId, seat, thread });
    if (out.recorded) {
      log('info', 'reaped the owner ask; the daemon signalled the seat\'s relaunch in the same transaction',
        { goalId, seat, thread, askId: out.ask_id, idempotent: out.idempotent === true });
    }
    return out;
  }

  return { openAsk, reapAsk, listOpenAsks };
}

module.exports = { createAskRecord, ASK_LABEL_DEFAULT };
