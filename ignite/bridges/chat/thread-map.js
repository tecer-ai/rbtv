'use strict';

// The v1 thread ↔ turn-chain mapping table (chat-bridge-spec.md § Thread ↔ session
// mapping; notes §7b "thread↔session mapping table"). One chat thread = one
// conversation (D105). The bridge maintains { chat-thread-id ↔ turn-chain }, the
// chain keyed by its CHAIN-STABLE thread id `exec-<first exec_id>` (D24 Q3a;
// sessions are cattle, so the chain's THREAD is the stable handle, never a
// session id).
//
// ⚑ ID-SPACE DISCIPLINE (D69): jobId (a queue-row handle), exec-id, and the
// chain/thread id are DISTINCT id spaces. The bridge navigates
//   job-id → exec-id → chain-thread id
// via the gateway `inspect` intent — it NEVER conflates or synthesizes across
// spaces, and it NEVER guesses a thread it has not resolved.
//
// ⚑ REGISTRY CONVERGENCE (surfaced, task-7.5): the settled model is deeper —
// channel → (1:1) goal thread → per-slot sub-thread → session. v1 maps
// chat-thread ↔ turn-chain directly ONLY because the v1 core has no goal /
// threads-store / slot machinery yet. This table is that v1 stand-in.

function createThreadMap({ logger = null } = {}) {
  // chatThreadId -> {
  //   queueId,        // the queue-row id enqueue-job returned for the FIRST message
  //   sessionExecId,  // the first execution's exec_id, once learned (D69 nav step)
  //   chainThread,    // 'exec-<first exec_id>', once resolved — null until known
  //   pendingAsk,     // true when the daemon has a pending `ask` on this thread (D105 reply type)
  //   createdAt,
  // }
  const byChat = new Map();

  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  function has(chatThreadId) {
    return byChat.has(String(chatThreadId));
  }

  function get(chatThreadId) {
    return byChat.get(String(chatThreadId)) || null;
  }

  // A NEW chat thread opens a NEW conversation: record the queue-row id the
  // session-creating enqueue returned. The chain thread is NOT known yet — it
  // only exists once the ticker's Dispatch phase fires the row into an execution.
  function create(chatThreadId, { queueId }) {
    const id = String(chatThreadId);
    const entry = {
      queueId: queueId ?? null,
      sessionExecId: null,
      chainThread: null,
      pendingAsk: false,
      createdAt: new Date().toISOString(),
    };
    byChat.set(id, entry);
    log('info', 'chat thread mapped to a new conversation', { chatThreadId: id, queueId: entry.queueId });
    return entry;
  }

  // Record the first execution's exec_id (the D69 job-id → exec-id nav step),
  // learned from the daemon. Deriving the chain thread from it is a pure string
  // (chain-stable convention), but we still confirm liveness via inspect before
  // trusting it as the address.
  function bindSessionExecId(chatThreadId, execId) {
    const entry = get(chatThreadId);
    if (!entry) return null;
    entry.sessionExecId = Number(execId);
    return entry;
  }

  // Record the resolved chain thread directly (e.g. learned from an outbound
  // message the daemon emitted on this conversation, which carries the thread).
  function bindChainThread(chatThreadId, chainThread) {
    const entry = get(chatThreadId);
    if (!entry) return null;
    entry.chainThread = String(chainThread);
    log('info', 'chat thread bound to chain thread', { chatThreadId: String(chatThreadId), chainThread: entry.chainThread });
    return entry;
  }

  // D105 reply type: a follow-up is `answer` when it responds to a PENDING `ask`,
  // else `note`. The outbound path sets this true when it delivers an `ask` to the
  // owner; the follow-up path reads it and clears it once answered.
  function setPendingAsk(chatThreadId, value) {
    const entry = get(chatThreadId);
    if (entry) entry.pendingAsk = Boolean(value);
    return entry;
  }

  // Resolve the chain thread `exec-<first exec_id>` for a conversation, via the
  // gateway `inspect` intent (D69 — the bridge holds no store handle). Returns
  // { resolved, chainThread, reason }.
  //
  // ⚑ NEVER GUESSES. If the chain thread cannot be resolved from the recorded
  // exec-id via inspect, it returns resolved:false — the caller then declines to
  // forward with a wrong thread (fail loud, never silent-wrong). A conversation
  // whose session has not been dispatched yet HAS no chain thread; that is the
  // turn-boundary reality, not an error to paper over.
  async function resolveChainThread(chatThreadId, forwarder) {
    const entry = get(chatThreadId);
    if (!entry) return { resolved: false, chainThread: null, reason: 'unknown-conversation' };
    if (entry.chainThread) return { resolved: true, chainThread: entry.chainThread, reason: 'cached' };

    if (entry.sessionExecId == null && entry.queueId == null) {
      // Nothing to navigate from — resolution is honestly deferred, never guessed.
      return { resolved: false, chainThread: null, reason: 'exec-id-unknown' };
    }

    // ONE inspect ticker read serves both navigation steps (D69):
    //   queue_id → exec_id  via recent_ticks[].actions[] — the ticker's Dispatch
    //     phase records { action: 'spawn', execId, queueId } per fired row
    //     (server/ticker/ticker.js; jobs_log.queue_id carries the same link in
    //     the store). The window is the surface's last-10-ticks bound: a spawn
    //     older than that ages out, and resolution defers until the exec-id is
    //     learned another way (see README "Flagged seams").
    //   exec_id → chain thread via live_sessions[].{ exec_id, thread } — the
    //     chain-stable thread the store DERIVES from parent_exec_id (heart-store
    //     _chainThread).
    const res = await forwarder.inspect('ticker');
    if (!res.ok) {
      return { resolved: false, chainThread: null, reason: `inspect-failed:${res.error && res.error.code}` };
    }

    if (entry.sessionExecId == null) {
      const ticks = (res.result && res.result.recent_ticks) || [];
      for (const t of ticks) {
        const actions = Array.isArray(t.actions) ? t.actions : [];
        const fired = actions.find((a) => a && a.action === 'spawn' && a.execId != null
          && Number(a.queueId) === Number(entry.queueId));
        if (fired) {
          entry.sessionExecId = Number(fired.execId);
          log('info', 'exec-id learned from ticker dispatch actions', { chatThreadId: String(chatThreadId), queueId: entry.queueId, execId: entry.sessionExecId });
          break;
        }
      }
      if (entry.sessionExecId == null) {
        // Not fired yet, or the spawn aged out of the recent-ticks window.
        return { resolved: false, chainThread: null, reason: 'exec-id-unknown' };
      }
    }

    const live = (res.result && res.result.live_sessions) || [];
    const match = live.find((s) => Number(s.exec_id) === Number(entry.sessionExecId));
    if (match && typeof match.thread === 'string' && match.thread.length > 0) {
      entry.chainThread = match.thread;
      log('info', 'chain thread resolved via inspect', { chatThreadId: String(chatThreadId), execId: entry.sessionExecId, chainThread: match.thread });
      return { resolved: true, chainThread: match.thread, reason: 'inspect-ticker' };
    }
    return { resolved: false, chainThread: null, reason: 'exec-id-not-live' };
  }

  function size() {
    return byChat.size;
  }

  return {
    has, get, create,
    bindSessionExecId, bindChainThread, setPendingAsk,
    resolveChainThread, size,
  };
}

module.exports = { createThreadMap };
