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
// ⚑ NEVER `send-to-session` (D104). That intent's ratified re-validation required
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

// D111 part 2 — the honest decline notice. When a MAPPED conversation's follow-up
// cannot reach the running work (chain unresolved, or the gateway refused the
// enqueue), the owner sees this ONE fixed line instead of silence. Fixed string,
// NO internals (never leak a reason / thread / queue id into chat).
const DECLINE_NOTICE = "⚠ couldn't route your reply to the running work — please try again shortly";

function createForwardPath({ forwarder, threadMap, allowlist, config, logger = null, deliver = null }) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // Best-effort owner notice on a DROPPED reply path (D111 part 2). Called ONLY from
  // the follow-up leg — i.e. a MAPPED conversation. Delivery is best-effort: when no
  // reply address exists deliverToOwner returns delivered:false and we drop; a failed
  // post is logged and dropped, NEVER retried (no notice loop). Notices are NEVER
  // posted on allowlist/pairing refusals — that path returns before the follow-up leg
  // (unpaired users get nothing, by security posture, not a gap).
  async function postDeclineNotice(chatThreadId) {
    if (typeof deliver !== 'function') return;
    try {
      const d = await deliver({ chatThreadId, text: DECLINE_NOTICE, markAsk: false });
      if (d && d.delivered === false) {
        log('warn', 'decline notice not delivered (best-effort, dropped)', { chatThreadId, reason: d.reason || d.error || 'unknown' });
      } else {
        log('info', 'decline notice posted to owner thread', { chatThreadId });
      }
    } catch (err) {
      log('warn', 'decline notice threw (best-effort, dropped)', { chatThreadId, error: err.message });
    }
  }

  // The launch profile for a first message, by SURFACE (task 7.58). Master (DM) and
  // goal (channel) traffic are different work — cold-contact intake versus a message
  // on an existing goal's thread — so they may run different profiles. Both fall back
  // to the single `sessionProfile`, so an unconfigured deployment behaves exactly as
  // it did before this task. No new job payload field is introduced anywhere: the
  // surface distinction rides the EXISTING `profile` arg, because inventing a wire
  // field would put the bridge ahead of the job catalogue's own args schema.
  function profileFor(route) {
    if (route && route.kind === 'goal') return config.goalProfile || config.sessionProfile;
    return config.masterProfile || config.sessionProfile;
  }

  // A first message that STARTS work → a session-creating launch-agent job.
  async function forwardSessionCreate({ chatThreadId, text, route }) {
    const profile = profileFor(route);
    if (!profile) {
      // A launch-agent job MUST name a profile (DEC-1 R3; the store re-validates it
      // exists). Missing config is a loud refusal, never a silent malformed forward.
      return { forwarded: false, leg: 'session-create', reason: 'no-session-profile-configured' };
    }
    const payload = {
      job_id: config.sessionJobId,
      args: { profile, prompt: text },
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
    log('info', 'session-create job enqueued', { chatThreadId, queueId, route: route && route.kind, goalId: route && route.goalId, profile });
    return { forwarded: true, leg: 'session-create', intent: 'enqueue-job', queueId, route: route && route.kind, goalId: (route && route.goalId) || null };
  }

  // A follow-up in an already-mapped conversation → a send-message action-type
  // job on the chain's thread. NEVER send-to-session.
  async function forwardFollowUp({ chatThreadId, text, route }) {
    const entry = threadMap.get(chatThreadId);
    // Resolve the chain thread via inspect (D69) — the address for the message row.
    const resolved = await threadMap.resolveChainThread(chatThreadId, forwarder);
    if (!resolved.resolved) {
      // No chain thread yet: the session has not been dispatched, or the exec-id
      // is not yet known. Do NOT forward with a guessed thread (fail loud). The
      // reply stays with the owner's conversation state; a later turn consumes it
      // once the chain thread is resolvable.
      log('warn', 'follow-up not forwarded: chain thread unresolved', { chatThreadId, reason: resolved.reason });
      await postDeclineNotice(chatThreadId); // D111: honest notice, never silence, on a mapped conversation
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
      await postDeclineNotice(chatThreadId); // D111: honest notice on a mapped conversation whose enqueue was refused
      return { forwarded: false, leg: 'follow-up', intent: 'enqueue-job', replyType, thread: resolved.chainThread, error: res.error };
    }
    if (replyType === 'answer') threadMap.setPendingAsk(chatThreadId, false); // the ask has now been answered
    log('info', 'follow-up send-message enqueued', { chatThreadId, replyType, thread: resolved.chainThread, route: route && route.kind, goalId: route && route.goalId, queueId: res.result && res.result.jobId });
    return { forwarded: true, leg: 'follow-up', intent: 'enqueue-job', replyType, thread: resolved.chainThread, queueId: res.result && res.result.jobId, route: route && route.kind, goalId: (route && route.goalId) || null };
  }

  // The single entry: an inbound chat message. Admission FIRST (chat-bridge-spec.md
  // Behavior #2) — a non-admitted principal is refused with NO forward. Then route
  // by whether the conversation already exists.
  //
  // `route` (task 7.58) is resolved by the bridge and says which surface the message
  // arrived on — 'master' (a DM) or 'goal' (a mapped goal channel). It never changes
  // the ADMISSION decision (DEC-6's gate is per-principal, not per-surface) and it
  // never changes the forward CONTRACT (still exactly two enqueue-job legs). It
  // selects the launch profile and is logged, so a goal's traffic is attributable.
  //
  // THREE-VALUED, deliberately: an explicit `null` means the bridge RESOLVED the
  // surface and found it unattributable → refuse. `undefined` means no caller
  // supplied one at all (a pre-7.58 embedder) → master, the old behaviour. Collapsing
  // the two would either refuse legitimate callers or admit unattributable traffic.
  async function onChatMessage({ chatUserId, chatThreadId, text, route = { kind: 'master', goalId: null } }) {
    const admission = allowlist.check(chatUserId);
    if (!admission.allowed) {
      log('warn', 'chat message refused (not admitted) — no forward', { chatUserId, chatThreadId, reason: admission.reason });
      return { forwarded: false, refused: true, reason: admission.reason };
    }
    // Surface gate, AFTER admission (see the bridge's routeOf note): a message from
    // a channel that maps to no goal is unattributable and must never mint work.
    if (route === null) {
      log('warn', 'chat message refused — surface maps to no goal and is not a DM', { chatUserId, chatThreadId });
      return { forwarded: false, refused: true, reason: 'unroutable-surface' };
    }
    if (threadMap.has(chatThreadId)) {
      return forwardFollowUp({ chatThreadId, text, route });
    }
    return forwardSessionCreate({ chatThreadId, text, route });
  }

  return { onChatMessage, forwardSessionCreate, forwardFollowUp, CMP8_TYPES };
}

module.exports = { createForwardPath, CMP8_TYPES, DECLINE_NOTICE };
