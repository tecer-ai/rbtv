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
// via the gateway `inspect` intent — it NEVER conflates the spaces and NEVER
// guesses. The exec-id → chain-thread step has TWO settled resolutions: the
// authoritative live_sessions `thread` when the session is live, else the
// chain-stable CONVENTION `exec-<first exec_id>` (D24 Q3a) derived from the KNOWN
// first exec-id (see resolveChainThread). Deriving by that fixed convention is a
// resolution, not a guess — an UNKNOWN first exec-id derives nothing.
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
  // learned from the daemon. FIRST-WINS immutable (D111 guard): once set, a later
  // bind is IGNORED — the chain-stable thread is `exec-<FIRST exec_id>` (D24 Q3a),
  // so a later turn's exec must never overwrite it, or the convention-derivation
  // fallback below would address a NONEXISTENT thread. resolveChainThread prefers
  // the authoritative live_sessions thread, then DERIVES `exec-<first exec_id>`
  // from this id when the session is not live (convention-derivation, not a guess).
  function bindSessionExecId(chatThreadId, execId) {
    const entry = get(chatThreadId);
    if (!entry) return null;
    if (entry.sessionExecId != null) {
      if (Number(execId) !== entry.sessionExecId) {
        log('info', 'ignored later exec-id bind (first-wins; chain thread is exec-<first exec_id>)', { chatThreadId: String(chatThreadId), keptExecId: entry.sessionExecId, ignoredExecId: Number(execId) });
      }
      return entry;
    }
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
  // ⚑ RESOLUTION ORDER (D111) — two tiers, authoritative first, and it NEVER
  // guesses:
  //   1. live_sessions[] — when the chain's session is CURRENTLY live, the store's
  //      own `thread` is the authoritative address (reason 'inspect-ticker').
  //   2. CONVENTION-DERIVATION fallback — when the FIRST exec_id is KNOWN (bound,
  //      or learned from recent_ticks below) but its session is not live (the
  //      turn-boundary reality: short v1 turns end between the owner's messages, so
  //      live_sessions no longer carries it), DERIVE `exec-<first exec_id>`. This
  //      is not a guess: the chain-stable thread id IS `exec-<first exec_id>` by
  //      settled convention (D24 Q3a; this module's header; ticker-engine-spec
  //      § v1 turn-chain), and `sessionExecId` is FIRST-WINS immutable
  //      (bindSessionExecId), so the derived id always names the chain's real
  //      thread (reason 'derived-convention').
  // When NO first exec_id can be established at all (`exec-id-unknown` — nothing
  // dispatched yet, or the spawn aged out of the window), resolution is honestly
  // deferred, never fabricated: the caller declines rather than forward a wrong
  // thread (fail loud). There is still nothing to derive FROM.
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

    // The session is not live — the turn-boundary reality: the chain's first exec
    // ended between the owner's short v1 turns, so live_sessions no longer carries
    // it. We KNOW the first exec_id (bound, or learned above) and the chain-stable
    // thread id IS `exec-<first exec_id>` by settled convention (D24 Q3a), so DERIVE
    // it rather than decline. Cache it on the entry (subsequent turns hit the cache).
    const derived = `exec-${entry.sessionExecId}`;
    entry.chainThread = derived;
    log('info', 'chain thread derived from first exec-id (convention fallback; session not live)', { chatThreadId: String(chatThreadId), execId: entry.sessionExecId, chainThread: derived });
    return { resolved: true, chainThread: derived, reason: 'derived-convention' };
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
