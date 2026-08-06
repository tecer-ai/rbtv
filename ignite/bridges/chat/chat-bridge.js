'use strict';

// The chat bridge — composition of the four parts (chat-bridge-spec.md):
//   • transport      — Slack Socket Mode (outbound WS; slack-socket-mode.js)
//   • allowlist      — chat-user admission + DM pairing (allowlist.js)
//   • threadMap      — chat-thread ↔ turn-chain mapping (thread-map.js)
//   • goalChannels   — goal ↔ Slack channel, 1:1 (goal-channel-map.js, task 7.58)
//   • forwardPath    — the D104/D105 forward contract to the gateway (forward-path.js)
//
// The bridge is an ORDINARY authenticated SENDER on the narrow gateway API — never
// a privileged path. It holds NO spawn/queue capability (chat-bridge-spec.md
// Behavior #5): its only outbound dependencies are the transport and the gateway
// forwarder, both injected here.

const { createForwardPath } = require('./forward-path');
const { createReplyLeg } = require('./reply-leg');

function createChatBridge({ config, forwarder, transport, allowlist, threadMap, goalChannels = null, logger = null, replyLegOptions = {} }) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // deliver is the bridge's own outbound delivery (deliverToOwner, hoisted below) —
  // injected so the forward path can post an honest decline notice (D111 part 2) on
  // a MAPPED conversation whose follow-up cannot reach the running work, never silence.
  const forwardPath = createForwardPath({ forwarder, threadMap, allowlist, config, logger, deliver: (args) => deliverToOwner(args) });

  // The outbound reply leg (Behavior #3, D110): drives worker answer → Slack thread.
  // It reaches the daemon ONLY via the injected forwarder's inspect surface, and
  // delivers via this bridge's own deliverToOwner — no new capability.
  const replyLeg = createReplyLeg({
    threadMap,
    forwarder,
    deliver: (args) => deliverToOwner(args),
    logger,
    ...replyLegOptions,
  });

  // THE SURFACE ROUTE (task 7.58 d-channel-per-goal; mention route added by the
  // 2026-08-06 owner ruling). Every inbound message is exactly one of three things,
  // and the difference is decided HERE, before admission or forwarding:
  //
  //   'master' — EITHER a DM to the bot identity (cold-contact MASTER traffic,
  //              explicitly UNCHANGED by the channel-per-goal ruling) OR a message in
  //              an unmapped channel/group that MENTIONS the bot (`<@BOTID>`) or that
  //              lands in a thread ALREADY known to the thread map (a mention MINTS a
  //              conversation, membership CONTINUES it — no re-mention per reply). Both
  //              carry the same conversation shape — the Slack thread
  //              `channel:thread_ts` — so a mention starts a per-thread sitting and a
  //              new thread is a new sitting. NEVER goal traffic: neither surface can
  //              be attributed to a goal.
  //   'goal'   — a message in a MAPPED goal channel. The goal thread maps 1:1 onto
  //              the channel, so the CONVERSATION IS THE CHANNEL — sharding it by
  //              `thread_ts` would split one goal thread into many and break the 1:1
  //              the ruling exists to establish.
  //   null     — an UNMENTIONED message in a channel that maps to no goal, in no
  //              already-known conversation thread. REFUSED,
  //              nothing enqueued: unattributable traffic must never mint work. The
  //              mention is what makes it attributable — without one, the bot sitting
  //              in an ordinary channel would mint work from every passing sentence.
  //
  // `mpim` (group DM) routes as neither: it is not a goal channel and it is not the
  // 1:1 owner DM the master path assumes. Refused, deliberately.
  //
  // ⚑ WHEN `_channelType` IS ABSENT. Slack's `message` events always carry it, so an
  // event without it did not come from the Slack transport — it was injected
  // directly (a probe, or an embedder driving the bridge in-process). Two sub-cases,
  // split so the strict rule lands exactly where the risk is:
  //   • the channel id looks like a Slack CHANNEL (`C…`/`G…`) → treat it as a
  //     channel and apply the strict rule. A real channel event that somehow lost
  //     the field must never fall through to master traffic.
  //   • anything else (a `D…` IM id, or no channel at all) → master, the exact
  //     pre-7.58 semantics. Refusing here would silently kill the master path.
  //
  // ⚑ THE MENTION ROUTE FAILS CLOSED. It is armed only once `botUserId` is known
  // (resolved from the transport at start — see start()). Until then, and forever if
  // resolution failed, an unmapped channel behaves exactly as it did before this
  // ruling: refused. A bridge that cannot say who it is must not guess who was meant.
  const CHANNEL_ID_RE = /^[CG]/;
  let botUserId = null;

  function mentionsBot(chatMsg) {
    return Boolean(botUserId) && typeof chatMsg.text === 'string' && chatMsg.text.includes(`<@${botUserId}>`);
  }

  function routeOf(chatMsg) {
    if (!chatMsg) return null;
    const kind = chatMsg._channelType;
    const channel = chatMsg._channel;
    const looksLikeChannel = kind === 'channel' || kind === 'group'
      || (!kind && typeof channel === 'string' && CHANNEL_ID_RE.test(channel));
    if (kind === 'mpim') return null;
    if (!looksLikeChannel) {
      return { kind: 'master', goalId: null, conversationId: chatMsg.chatThreadId };
    }
    const goalId = goalChannels ? goalChannels.goalForChannel(channel) : null;
    if (!goalId) {
      // Unmapped channel: a mention MINTS a conversation; MEMBERSHIP in one already
      // minted CONTINUES it. Anything else stays refused.
      //
      // The continuation check is `threadMap.has(<the same conversation id the mention
      // route would assign>)` — `channel:thread_ts`. It is self-limiting by
      // construction: a TOP-LEVEL message's conversation id is its own `ts`, always
      // brand new, so it can never be in the map — only replies inside a thread that
      // already IS a sitting continue without a mention. Without this, the owner had to
      // re-mention the bot on every single reply in a thread it had already answered
      // in (owner-observed 2026-08-06).
      //
      // ponytail: the thread map is IN-MEMORY, so a bridge restart forgets every
      // sitting and un-mentioned replies in old threads go back to refused until the
      // owner re-mentions (which re-mints). Accepted limit, disclosed in the README;
      // persist the map if restarts become common.
      if (mentionsBot(chatMsg) || (threadMap && threadMap.has(chatMsg.chatThreadId))) {
        return { kind: 'master', goalId: null, conversationId: chatMsg.chatThreadId };
      }
      return null;
    }
    return { kind: 'goal', goalId, conversationId: String(channel) };
  }

  // Inbound: a chat message → the surface route, then the forward path (admission,
  // then session-create or follow-up). Wired as the transport's onMessage.
  //
  // ⚑ THE ROUTE IS RESOLVED HERE BUT ENFORCED IN THE FORWARD PATH, so ADMISSION
  // STAYS FIRST (chat-bridge-spec.md Behavior #2). Refusing an unroutable surface
  // before admission would be no weaker as security, but it would stop a
  // non-admitted principal from ever reaching the allowlist's pairing queue — and
  // that queue IS the DM-pairing feature (DEC-6). Order matters for a reason that
  // has nothing to do with which refusal is stricter.
  async function onChatMessage(rawMsg) {
    const route = routeOf(rawMsg);
    // The conversation id the whole bridge keys on: the Slack thread for master
    // traffic, the CHANNEL for goal traffic. An unroutable message keeps its raw id
    // — it is refused downstream and never reaches the thread map.
    const chatMsg = { ...rawMsg, chatThreadId: route ? route.conversationId : (rawMsg && rawMsg.chatThreadId), route };

    // Remember the Slack reply address for outbound delivery on this conversation.
    // Goal traffic replies IN-CHANNEL (top level) unless the human posted inside a
    // Slack thread — the goal's surface is the channel, so burying every reply in a
    // thread would hide the goal's own conversation from the owner. Master traffic —
    // DM *and* mention — always carries `_threadTs` (the transport defaults it to the
    // message's own ts), so a mention in a busy channel is answered IN-THREAD and one
    // sitting never bleeds into another's.
    if (route && chatMsg.chatThreadId && chatMsg._channel) {
      const threadTs = route.kind === 'goal'
        ? (chatMsg._inThread ? chatMsg._threadTs : null)
        : chatMsg._threadTs;
      replyAddr.set(chatMsg.chatThreadId, { channel: chatMsg._channel, threadTs });
    }
    const outcome = await forwardPath.onChatMessage(chatMsg);
    // Arm the reply leg on every FORWARDED turn — a session-create (new conversation)
    // or a follow-up (the chain re-dispatches → a new exec on the same queue). The
    // leg then watches for the spawn, awaits turn-end, and delivers the reply.
    if (outcome && outcome.forwarded && chatMsg && chatMsg.chatThreadId) {
      replyLeg.arm(chatMsg.chatThreadId);
      // Read-receipt 🤖 (owner-directed 2026-08-06): stamped by the BRIDGE the moment the
      // message is accepted for processing — transparent to the agent, best-effort,
      // fire-and-forget so a Slack hiccup never delays the forward.
      if (typeof transport.react === 'function' && chatMsg._channel && chatMsg._msgTs) {
        transport.react({ channel: chatMsg._channel, ts: chatMsg._msgTs }).catch(() => {});
      }
    }
    log('info', 'chat message handled', { chatThreadId: chatMsg && chatMsg.chatThreadId, ...outcome });
    return outcome;
  }

  // conversation → { channel, threadTs } — where to post owner output back.
  const replyAddr = new Map();

  // Outbound: deliver worker/leader output addressed to the owner (chat-bridge-spec.md
  // Behavior #3), at the TURN BOUNDARY (notes §7b — never mid-turn). `markAsk`
  // records that the daemon posed a pending `ask` on this conversation, so the
  // owner's NEXT reply forwards as an `answer` (D105) rather than a `note`.
  async function deliverToOwner({ chatThreadId, text, markAsk = false }) {
    const addr = replyAddr.get(chatThreadId);
    if (!addr) {
      log('warn', 'no reply address for conversation — cannot deliver owner output', { chatThreadId });
      return { delivered: false, reason: 'no-reply-address' };
    }
    if (markAsk) threadMap.setPendingAsk(chatThreadId, true);
    return transport.sendToOwner({ channel: addr.channel, threadTs: addr.threadTs, text });
  }

  // ── The goal lifecycle (task 7.58, both settled open points) ────────────────
  //
  // These two calls ARE the settled answers, exposed as the bridge's public surface.
  // Their eventual caller is the goal machinery — `rbtv goal scaffold` at goal
  // registration and the goal close at retire (task 7.63). Until that hook exists an
  // explicit call stands in; the ANSWER is unchanged, only its caller. Reasoning and
  // the registry-transcription flags: `goal-channel-design.md`.

  // (a) CREATION — at goal registration. Idempotent and name-derived.
  async function registerGoal(goalId) {
    if (!goalChannels) return { ok: false, error: 'no-goal-channel-map-configured' };
    return goalChannels.ensureChannel(goalId);
  }

  // (b) CLOSE-TIME — ARCHIVE, never delete. Also forgets the conversation's reply
  // address and its thread-map-facing state, so nothing lingers pointing at a
  // channel that takes no more goal traffic.
  async function closeGoal(goalId) {
    if (!goalChannels) return { ok: false, error: 'no-goal-channel-map-configured' };
    const channelId = goalChannels.channelForGoal(goalId);
    const res = await goalChannels.retire(goalId);
    if (res.ok && channelId) replyAddr.delete(String(channelId));
    return res;
  }

  async function start() {
    const r = await transport.start();
    // Resolve THIS bot's user id — the mention route needs it and nothing else can
    // supply it (the id is a property of the installed app, not of config). Failure is
    // loud but not fatal: the mention route simply stays disabled, which is exactly
    // the pre-ruling behaviour, and DM + goal traffic are untouched.
    if (typeof transport.authTest === 'function') {
      try {
        const who = await transport.authTest();
        if (who && who.ok && who.userId) {
          botUserId = who.userId;
          log('info', 'bot identity resolved — mention route armed', { botUserId });
        } else {
          log('error', 'auth.test did not return a bot user id — MENTION ROUTE DISABLED (unmapped channels stay refused)', { error: who && who.error });
        }
      } catch (err) {
        log('error', 'auth.test threw — MENTION ROUTE DISABLED (unmapped channels stay refused)', { error: err.message });
      }
    } else {
      log('warn', 'transport exposes no auth.test — mention route disabled');
    }
    // Rebuild goal↔channel from the workspace BEFORE listening: the bridge's map is
    // in-memory, and name-derivation is what lets a restart recover it with no
    // persistence. A recovery failure is not fatal — the bridge still serves master
    // (DM) traffic, and goal channels re-bind on the next registerGoal — but it is
    // said loudly, because until it succeeds every goal channel reads as unroutable.
    let recovered = null;
    if (goalChannels) {
      try {
        recovered = await goalChannels.recover();
        if (!recovered.ok) log('warn', 'goal↔channel recovery failed — goal channels will read as unroutable until re-registered', { error: recovered.error });
      } catch (err) {
        log('warn', 'goal↔channel recovery threw — continuing with an empty map', { error: err.message });
      }
    }
    replyLeg.start();
    log('info', 'chat bridge started', { transport: 'slack-socket-mode', goalChannelsBound: recovered && recovered.bound, ...r });
    return r;
  }

  function stop() {
    replyLeg.stop();
    transport.stop();
    log('info', 'chat bridge stopped');
  }

  return {
    onChatMessage, deliverToOwner, start, stop,
    registerGoal, closeGoal, routeOf,
    _replyAddr: replyAddr, forwardPath, replyLeg, goalChannels,
  };
}

module.exports = { createChatBridge };
