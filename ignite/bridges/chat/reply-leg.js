'use strict';

// THE OUTBOUND REPLY LEG (chat-bridge-spec.md Behavior #3; Test Plan #4; owner
// ruling D110). The bridge's missing production DRIVER: when the agent worker
// spawned for a chat conversation finishes its turn, this leg fetches the
// worker's answer from the daemon (over the SAME narrow gateway `inspect` surface
// the rest of the bridge uses) and posts it into the mapped Slack thread via the
// bridge's existing `deliverToOwner`. It closes the loop the forward path opened.
//
// ⚑ NO NEW CAPABILITY. The driver reaches the daemon ONLY through the injected
// `forwarder.inspect` (the closed seven-intent surface, D90) — no store handle,
// no spawn path, no new intent, no new inbound listener. It is pure polling over
// `inspect ticker | status | logs` plus a call to the bridge's own delivery.
//
// ⚑ IN-MEMORY, v1 (D110 floor). Per-conversation driver state lives in this
// process only — a restart forgets it (owner-known caveat, matches the existing
// thread-map / replyAddr). Sessions are cattle; no persistence.
//
// ⚑ `live` FLAG, NEVER `status`, is the turn-finished signal. The daemon's crash
// sweep marks EVERY exited detached (`systemd --collect`) execution `failed`, so a
// clean success is recorded `status:'failed'` (no exit-code visibility). Keying
// "turn finished" on `status === 'done'` would miss every real reply. We key on
// the `live` flag transitioning to false (dispatch.js inspect status → `live`).

// Fixed fallback delivered when a run ends with no parseable reply line — the raw
// log is NEVER dumped into Slack (D110 step 4).
const FALLBACK_TEXT = '⚠ agent run ended without a parseable reply';

const DEFAULT_POLL_MS = 3000;                 // single driver cadence (D110 step 3)
const DEFAULT_WINDOW_MS = 10 * 60 * 1000;     // bound: wait for a spawn ≤ 10 min (step 6)
const DEFAULT_LOG_LIMIT = 1000;               // per-page log fetch bound (server clamps to its MAX_PAGE)
const DEFAULT_MAX_LOG_PAGES = 50;             // cap the log paging loop (never unbounded)
const DEFAULT_MAX_STATUS_ERRORS = 20;         // disarm after persistent status errors (step 6)
const DEFAULT_MAX_DELIVER_ATTEMPTS = 20;      // per-exec fetch/delivery retry bound (step 6 — never unbounded)

// stream-json extraction (D110 step 4): the worker log is one JSON object per
// line (`claude -p --output-format stream-json`); the answer is the LAST line of
// shape `{ type:'result', result:'<text>', … }`. Non-JSON / non-result lines are
// skipped. No parseable result line → null (caller substitutes the fallback).
function extractReplyText(lines) {
  let text = null;
  for (const line of lines) {
    if (!line) continue;
    let obj;
    try { obj = JSON.parse(line); } catch { continue; }
    if (obj && obj.type === 'result' && typeof obj.result === 'string') {
      text = obj.result; // keep scanning — take the LAST result line
    }
  }
  return text;
}

// The driver. `deliver({ chatThreadId, text, markAsk })` is the bridge's own
// outbound delivery (chat-bridge.js deliverToOwner) — injected so the leg holds
// no transport of its own. `forwarder.inspect(target, extra)` is the gateway read
// surface. `threadMap` supplies each conversation's session queue-row id.
function createReplyLeg({
  threadMap,
  forwarder,
  deliver,
  logger = null,
  pollMs = DEFAULT_POLL_MS,
  windowMs = DEFAULT_WINDOW_MS,
  logLimit = DEFAULT_LOG_LIMIT,
  maxLogPages = DEFAULT_MAX_LOG_PAGES,
  maxStatusErrors = DEFAULT_MAX_STATUS_ERRORS,
  maxDeliverAttempts = DEFAULT_MAX_DELIVER_ATTEMPTS,
} = {}) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // chatThreadId -> {
  //   queueId,           // the conversation's SESSION queue-row id — the watch key.
  //                      //   Every turn's spawn action carries this queueId; a new
  //                      //   turn re-dispatches a NEW exec on the same queue.
  //   armedAt,           // ms — refreshed each turn (arm) and on delivery; bounds
  //                      //   the wait for a spawn to appear (step 6 window).
  //   watching,          // Map execId -> { capturedAt } — spawns seen, awaiting turn-end.
  //   delivered,         // Set<execId> — execs already delivered; NEVER delivered twice.
  //   statusErrors,      // consecutive status-poll errors (bound, step 6).
  // }
  const pending = new Map();
  let timer = null;
  let ticking = false;

  // Arm (or re-arm) a conversation as PENDING-REPLY. Called after the forward path
  // enqueues a session-create job (new conversation) AND after a follow-up
  // send-message lands on a mapped chain (the chain re-dispatches → a new exec on
  // the same queue). Re-arming refreshes the spawn-wait window for the new turn.
  function arm(chatThreadId) {
    const id = String(chatThreadId);
    const entry = threadMap.get(id);
    const queueId = entry ? entry.queueId : null;
    let p = pending.get(id);
    if (!p) {
      p = { queueId, armedAt: Date.now(), watching: new Map(), delivered: new Set(), statusErrors: 0 };
      pending.set(id, p);
    } else {
      p.armedAt = Date.now();
      if (p.queueId == null) p.queueId = queueId;
    }
    log('info', 'reply leg armed for conversation', { chatThreadId: id, queueId: p.queueId });
    return p;
  }

  // Fetch + extract one exec's reply text, paging the bounded log surface to its
  // end so the LAST result line is seen even when the log spans pages (the server
  // clamps `limit` to its MAX_PAGE; we follow `nextOffset` until `eof`).
  //
  // Returns { fetched: false } on a FAILED page read (a transient gateway/transport
  // error — the real answer may still be on disk, so the caller RETRIES, bounded),
  // or { fetched: true, text } where text === null means the log was read to eof
  // and genuinely holds no parseable result line (the fallback case, D110 step 4).
  // Conflating the two would post the fallback — and burn the exec as delivered —
  // on a mere transport blip, silently losing the worker's real answer.
  async function fetchReplyText(execId, chatThreadId) {
    const lines = [];
    let offset = 0;
    for (let page = 0; page < maxLogPages; page++) {
      const res = await forwarder.inspect('logs', { id: execId, offset, limit: logLimit });
      if (!res || !res.ok || !res.result) {
        log('warn', 'reply leg logs inspect failed — will retry next pass', { chatThreadId, execId, offset, error: res && res.error && res.error.code });
        return { fetched: false, text: null };
      }
      const pageLines = Array.isArray(res.result.lines) ? res.result.lines : [];
      for (const l of pageLines) lines.push(l);
      const next = res.result.nextOffset;
      offset = Number.isInteger(next) ? next : (offset + pageLines.length);
      if (res.result.eof || pageLines.length === 0) return { fetched: true, text: extractReplyText(lines) };
    }
    // Page cap hit without eof: an absurdly long log (> maxLogPages × server page).
    // The result line is the LAST line, so it was NOT reached — treat as no
    // parseable reply (honest fallback), never deliver a mid-log line as the answer.
    log('warn', 'reply leg log page cap hit before eof — treating as no parseable reply', { chatThreadId, execId, pagesRead: maxLogPages, linesRead: lines.length });
    return { fetched: true, text: null };
  }

  // One driver pass (the setInterval body; also directly drivable for tests). A
  // re-entrancy guard keeps two passes from overlapping their async inspects.
  async function _runOnce() {
    if (ticking) return;
    ticking = true;
    try {
      if (pending.size === 0) return;

      // 1. Capture new execIds from ticker spawn actions, per conversation queueId.
      //    A conversation may see MULTIPLE execs over its life (one per turn) — every
      //    spawn action with an execId not yet delivered is a turn to deliver.
      const tickerRes = await forwarder.inspect('ticker');
      if (tickerRes && tickerRes.ok && tickerRes.result) {
        const ticks = Array.isArray(tickerRes.result.recent_ticks) ? tickerRes.result.recent_ticks : [];
        for (const [id, p] of pending) {
          if (p.queueId == null) continue;
          for (const t of ticks) {
            const actions = Array.isArray(t.actions) ? t.actions : [];
            for (const a of actions) {
              if (a && a.action === 'spawn' && a.execId != null
                && Number(a.queueId) === Number(p.queueId)) {
                const execId = Number(a.execId);
                if (!p.delivered.has(execId) && !p.watching.has(execId)) {
                  p.watching.set(execId, { capturedAt: Date.now(), attempts: 0 });
                  log('info', 'reply leg captured spawn exec for conversation', { chatThreadId: id, queueId: p.queueId, execId });
                }
              }
            }
          }
        }
      } else {
        log('warn', 'reply leg ticker inspect failed', { error: tickerRes && tickerRes.error });
      }

      // 2. Poll each watched exec's status; on `live === false`, fetch + extract +
      //    deliver exactly once. Key on the live flag, NEVER on status (crash-sweep
      //    mislabels clean successes `failed`).
      for (const [id, p] of pending) {
        for (const execId of Array.from(p.watching.keys())) {
          const statusRes = await forwarder.inspect('status', { id: execId });
          if (!statusRes || !statusRes.ok || !statusRes.result) {
            p.statusErrors += 1;
            log('warn', 'reply leg status inspect failed', { chatThreadId: id, execId, error: statusRes && statusRes.error, statusErrors: p.statusErrors });
            continue;
          }
          p.statusErrors = 0;
          if (statusRes.result.live !== false) continue; // still live (or unknown) — keep polling

          // Turn ended — fetch, extract, deliver. Failures here are ISOLATED per
          // exec (a throw must not abort the pass for other execs/conversations)
          // and RETRIED next pass, bounded per exec (step 6 — never unbounded):
          // the exec is marked delivered ONLY on a confirmed delivery, so a
          // transient logs/transport/Slack failure never burns the reply.
          const watch = p.watching.get(execId);
          let failure = null;
          try {
            const read = await fetchReplyText(execId, id);
            if (!read.fetched) {
              failure = 'logs-fetch-failed';
            } else {
              const text = read.text != null ? read.text : FALLBACK_TEXT;
              if (read.text == null) log('warn', 'reply leg found no parseable result line — delivering fallback', { chatThreadId: id, execId });
              const d = await deliver({ chatThreadId: id, text, markAsk: false }); // plain agent output (D105 note; ask-detection out of scope v1)
              if (d && d.delivered === false) {
                failure = `deliver-refused:${d.reason || d.error || 'unknown'}`;
              } else {
                p.watching.delete(execId);
                p.delivered.add(execId);
                p.armedAt = Date.now(); // healthy activity — reset the spawn-wait window
                log('info', 'reply leg delivered worker reply to owner', { chatThreadId: id, execId, chars: text.length });
              }
            }
          } catch (err) {
            failure = `deliver-threw:${err.message}`;
          }
          if (failure) {
            watch.attempts += 1;
            if (watch.attempts >= maxDeliverAttempts) {
              // Give up HONESTLY: stop retrying, keep the exec in `delivered` so a
              // lingering recent_ticks spawn row cannot re-capture it. The reply is
              // NOT delivered and the warn says so — never a silent success.
              p.watching.delete(execId);
              p.delivered.add(execId);
              log('warn', 'reply leg giving up on exec after persistent fetch/delivery failures — reply NOT delivered', { chatThreadId: id, execId, attempts: watch.attempts, failure });
            } else {
              log('warn', 'reply leg fetch/delivery failed — will retry next pass', { chatThreadId: id, execId, attempts: watch.attempts, failure });
            }
          }
        }
      }

      // 3. Bound (step 6): disarm a conversation that errored persistently, or whose
      //    expected spawn never appeared within the window (never delivered, nothing
      //    in flight). No crash, no unbounded retry.
      const now = Date.now();
      for (const [id, p] of Array.from(pending.entries())) {
        if (p.statusErrors >= maxStatusErrors) {
          log('warn', 'reply leg disarming conversation — persistent status errors', { chatThreadId: id, statusErrors: p.statusErrors });
          pending.delete(id);
          continue;
        }
        if (p.watching.size === 0 && p.delivered.size === 0 && (now - p.armedAt) > windowMs) {
          log('warn', 'reply leg disarming conversation — no spawn within window', { chatThreadId: id, queueId: p.queueId, windowMs });
          pending.delete(id);
        }
      }
    } finally {
      ticking = false;
    }
  }

  function start() {
    if (timer) return;
    timer = setInterval(() => {
      _runOnce().catch((err) => log('warn', 'reply leg tick error', { error: err.message }));
    }, pollMs);
    if (timer.unref) timer.unref();
    log('info', 'reply leg started', { pollMs, windowMs });
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
    log('info', 'reply leg stopped');
  }

  return { arm, start, stop, tick: _runOnce, _pending: pending };
}

module.exports = { createReplyLeg, extractReplyText, FALLBACK_TEXT };
