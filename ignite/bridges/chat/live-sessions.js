'use strict';

// ── THE WARM LEG (live-session-design.md §1/§4) — the bridge's half ──────────────────────────────
//
// The manager itself is DAEMON-SIDE (`server/spawn/live-sessions.js`). This file is only its
// caller: it decides whether a message is a candidate for the warm path, makes ONE loopback
// gateway call, and hands the answer back for the bridge to post. It holds no process, no timer
// and no registry.
//
// ⚑ THE MANAGER CANNOT LIVE HERE, and it is not a preference. `probe-chat-boundary` scans every
// runtime `.js` in this directory for `child_process` and a bare process-launch call and fails
// the suite on a hit — chat-bridge-spec.md Behavior #5's "no spawn path" is a STRUCTURAL
// invariant of this subtree, not a habit. §4's ruled shape survives intact: the feed is DIRECT
// (one call, ~1ms of loopback) and it does NOT go through the queue, which is the whole thing the
// ruling chose. What moved is only where the child process is held.
//
// ⚑ EVERY REFUSAL FALLS THROUGH TO THE COLD PATH, and the cold path is UNCHANGED. `attempt()`
// returns `{ answered: false }` for everything that is not a delivered reply — not warm yet, not
// eligible, gateway down, turn timed out, session died mid-turn. The caller's response to all of
// them is identical: run the forward path it would have run anyway. That is what makes this
// additive: with `live_sessions: false`, or a daemon that never armed the manager, the bridge
// behaves byte-for-byte as it did before this file existed.

// A warm turn should land in 1.5–4s; the ceiling is for the long one. It bounds the HTTP call
// only — the daemon's own `turnTimeoutMs` is what actually reaps a stuck session, and it is
// deliberately the shorter-lived promise of the two.
const DEFAULT_FEED_TIMEOUT_MS = 240000;

function createLiveLeg({ forwarder, threadMap, config, logger = null, feedTimeoutMs = DEFAULT_FEED_TIMEOUT_MS }) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, component: 'live-leg', ...extra });
  }

  const enabled = config.liveSessions !== false;

  // ⚑ ONLY A CONVERSATION THAT ALREADY HAS A CHAIN. The first message of a conversation is what
  // MINTS the chain, and a live session is a `--resume` of that chain's `session_ref` — so there
  // is nothing to resume until the cold path has run once. This is the design's "start warmth for
  // the follow-ups" option, and it is chosen over "upgrade on next contact" because it needs no
  // second mechanism: the same call that answers message #2 is the one that launches the warm
  // process, so there is exactly ONE code path and no state that says "warm me later".
  //
  // Consequence, stated because it is measurable and will be measured: message #1 is cold (~12s),
  // message #2 pays the live launch (roughly cold again), message #3 onward is warm.
  function candidate({ chatThreadId, route }) {
    if (!enabled) return { ok: false, reason: 'disabled' };
    if (!route) return { ok: false, reason: 'unroutable' };
    if (!chatThreadId) return { ok: false, reason: 'no-conversation' };
    if (!threadMap.has(chatThreadId)) return { ok: false, reason: 'no-chain-yet' };
    const entry = threadMap.get(chatThreadId);
    if (!entry || entry.sessionExecId == null) return { ok: false, reason: 'exec-id-unknown' };
    return { ok: true, execId: entry.sessionExecId };
  }

  // Returns `{ answered: true, text }` ONLY when a warm session produced a reply. Everything else
  // is `{ answered: false, reason }` and the caller takes the cold path.
  async function attempt({ chatThreadId, text, route, profile, workdir }) {
    const c = candidate({ chatThreadId, route });
    if (!c.ok) return { answered: false, reason: c.reason };
    if (!profile) return { answered: false, reason: 'no-profile' };

    const startedAt = Date.now();
    const res = await forwarder.forward('live-feed', {
      conversation: String(chatThreadId),
      prompt: text,
      profile,
      workdir: workdir || null,
      exec_id: c.execId,
      start: true,
    }, { timeoutMs: feedTimeoutMs });

    if (!res.ok) {
      log('info', 'live feed refused by the gateway — falling back to the cold path', { chatThreadId, code: res.error && res.error.code });
      return { answered: false, reason: `gateway:${(res.error && res.error.code) || 'unknown'}` };
    }
    const r = res.result || {};
    if (!r.fed) {
      // `unanswered` is the one reason that is NOT routine: the owner's words were written into a
      // process that then died or timed out without producing a result. The caller still falls
      // through — the forward path's follow-up leg re-asks the chain over the SHIPPED cold resume
      // machinery — but it is logged at `warn` so a recurring one is visible rather than average.
      log(r.unanswered ? 'warn' : 'info', 'live feed did not answer — falling back to the cold path', { chatThreadId, reason: r.reason, unanswered: Boolean(r.unanswered) });
      return { answered: false, reason: r.reason || 'not-fed', unanswered: Boolean(r.unanswered) };
    }
    log('info', 'warm turn answered', { chatThreadId, ms: Date.now() - startedAt, agentMs: r.ms, sessionId: r.session_id, warm: r.warm });
    return { answered: true, text: typeof r.reply === 'string' ? r.reply : '', isError: r.is_error === true, ms: Date.now() - startedAt, sessionId: r.session_id };
  }

  return { attempt, candidate, enabled };
}

module.exports = { createLiveLeg, DEFAULT_FEED_TIMEOUT_MS };
