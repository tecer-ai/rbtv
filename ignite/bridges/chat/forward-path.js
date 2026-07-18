'use strict';

// THE FORWARD-PATH CONTRACT (chat-bridge-spec.md § Forward path, D104/D105) — the
// heart of the bridge. A chat message from an ADMITTED principal becomes ONE of
// exactly two gateway calls, both `enqueue-job` (the bridge adds NO new intent —
// D90; the set stays SEVEN, and the bridge speaks only add-job here):
//
//   1. FIRST message in a new chat thread  → a SESSION-CREATING job:
//        enqueue-job naming a launch-agent function + a named launch profile
//        (DEC-1 R3). The bridge NEVER spawns; the ticker's Dispatch phase does.
//
//   2. FOLLOW-UP in an already-mapped thread → a `send-message` ACTION-TYPE job
//        addressed to the mapped turn-chain's thread (`exec-<first exec_id>`).
//        Reply type is PINNED (D105): `answer` when it responds to a pending
//        `ask`, else `note` — the closed CMP-8 five-type vocabulary (mint nothing).
//
// ⚑ NEVER `send-to-session` (D104). That intent's ratified re-validation requires
// the execution to be `session_mode: headed` AND live (the pty keystroke rung —
// internal-api-contract-spec.md §1), while chat rides the HEADLESS model's turn-
// boundary ceiling (notes §7b). The follow-up leg is the SAME add-job path as the
// first leg — a send-message job on the chain's thread — consumed at the next turn
// boundary. There is no send-to-session code path in this file, by construction.

const { nowIsoUtc } = require('./config');

// The five CMP-8 message types (closed vocabulary — mint nothing). Only `answer`
// and `note` are produced by the follow-up leg per D105; the full set is stated
// so a future producer never invents a sixth.
const CMP8_TYPES = new Set(['completion', 'ask', 'answer', 'verdict', 'note']);

function createForwardPath({ forwarder, threadMap, allowlist, config, logger = null }) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // A first message that STARTS work → a session-creating launch-agent job.
  async function forwardSessionCreate({ chatThreadId, text }) {
    if (!config.sessionProfile) {
      // A launch-agent job MUST name a profile (DEC-1 R3; the store re-validates it
      // exists). Missing config is a loud refusal, never a silent malformed forward.
      return { forwarded: false, leg: 'session-create', reason: 'no-session-profile-configured' };
    }
    const payload = {
      job_id: config.sessionJobId,
      args: { profile: config.sessionProfile, prompt: text },
      session_mode: 'headless',                 // chat rides the headless model (notes §7b)
      trigger_kind: 'scheduled',
      run_at: nowIsoUtc(),                      // due now: the next tick dispatches it
    };
    if (config.workdir) payload.args.workdir = config.workdir;

    const res = await forwarder.forward('enqueue-job', payload);
    if (!res.ok) {
      log('warn', 'session-create enqueue refused by gateway', { chatThreadId, error: res.error });
      return { forwarded: false, leg: 'session-create', intent: 'enqueue-job', error: res.error };
    }
    const queueId = res.result && res.result.jobId;
    threadMap.create(chatThreadId, { queueId });
    log('info', 'session-create job enqueued', { chatThreadId, queueId });
    return { forwarded: true, leg: 'session-create', intent: 'enqueue-job', queueId };
  }

  // A follow-up in an already-mapped conversation → a send-message action-type
  // job on the chain's thread. NEVER send-to-session.
  async function forwardFollowUp({ chatThreadId, text }) {
    const entry = threadMap.get(chatThreadId);
    // Resolve the chain thread via inspect (D69) — the address for the message row.
    const resolved = await threadMap.resolveChainThread(chatThreadId, forwarder);
    if (!resolved.resolved) {
      // No chain thread yet: the session has not been dispatched, or the exec-id
      // is not yet known. Do NOT forward with a guessed thread (fail loud). The
      // reply stays with the owner's conversation state; a later turn consumes it
      // once the chain thread is resolvable.
      log('warn', 'follow-up not forwarded: chain thread unresolved', { chatThreadId, reason: resolved.reason });
      return { forwarded: false, leg: 'follow-up', reason: `chain-unresolved:${resolved.reason}` };
    }

    // D105 reply type: `answer` on a pending ask, else `note`.
    const replyType = entry && entry.pendingAsk ? 'answer' : 'note';
    if (!CMP8_TYPES.has(replyType)) {
      // Defensive: the closed vocabulary can never be violated from here.
      return { forwarded: false, leg: 'follow-up', reason: `bad-reply-type:${replyType}` };
    }

    const payload = {
      job_id: config.sendMessageJobId,
      args: { type: replyType, thread: resolved.chainThread, corpus: text },
      trigger_kind: 'scheduled',
      run_at: nowIsoUtc(),
    };
    const res = await forwarder.forward('enqueue-job', payload);
    if (!res.ok) {
      log('warn', 'follow-up send-message enqueue refused by gateway', { chatThreadId, error: res.error });
      return { forwarded: false, leg: 'follow-up', intent: 'enqueue-job', replyType, thread: resolved.chainThread, error: res.error };
    }
    if (replyType === 'answer') threadMap.setPendingAsk(chatThreadId, false); // the ask has now been answered
    log('info', 'follow-up send-message enqueued', { chatThreadId, replyType, thread: resolved.chainThread, queueId: res.result && res.result.jobId });
    return { forwarded: true, leg: 'follow-up', intent: 'enqueue-job', replyType, thread: resolved.chainThread, queueId: res.result && res.result.jobId };
  }

  // The single entry: an inbound chat message. Admission FIRST (chat-bridge-spec.md
  // Behavior #2) — a non-admitted principal is refused with NO forward. Then route
  // by whether the conversation already exists.
  async function onChatMessage({ chatUserId, chatThreadId, text }) {
    const admission = allowlist.check(chatUserId);
    if (!admission.allowed) {
      log('warn', 'chat message refused (not admitted) — no forward', { chatUserId, chatThreadId, reason: admission.reason });
      return { forwarded: false, refused: true, reason: admission.reason };
    }
    if (threadMap.has(chatThreadId)) {
      return forwardFollowUp({ chatThreadId, text });
    }
    return forwardSessionCreate({ chatThreadId, text });
  }

  return { onChatMessage, forwardSessionCreate, forwardFollowUp, CMP8_TYPES };
}

module.exports = { createForwardPath, CMP8_TYPES };
