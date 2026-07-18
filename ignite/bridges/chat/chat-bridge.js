'use strict';

// The chat bridge — composition of the four parts (chat-bridge-spec.md):
//   • transport      — Slack Socket Mode (outbound WS; slack-socket-mode.js)
//   • allowlist      — chat-user admission + DM pairing (allowlist.js)
//   • threadMap      — chat-thread ↔ turn-chain mapping (thread-map.js)
//   • forwardPath    — the D104/D105 forward contract to the gateway (forward-path.js)
//
// The bridge is an ORDINARY authenticated SENDER on the narrow gateway API — never
// a privileged path. It holds NO spawn/queue capability (chat-bridge-spec.md
// Behavior #5): its only outbound dependencies are the transport and the gateway
// forwarder, both injected here.

const { createForwardPath } = require('./forward-path');
const { createReplyLeg } = require('./reply-leg');

function createChatBridge({ config, forwarder, transport, allowlist, threadMap, logger = null, replyLegOptions = {} }) {
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

  // Inbound: a chat message → the forward path (admission, then session-create or
  // follow-up). Wired as the transport's onMessage.
  async function onChatMessage(chatMsg) {
    // Remember the Slack reply address for outbound delivery on this conversation.
    if (chatMsg && chatMsg.chatThreadId && chatMsg._channel) {
      replyAddr.set(chatMsg.chatThreadId, { channel: chatMsg._channel, threadTs: chatMsg._threadTs });
    }
    const outcome = await forwardPath.onChatMessage(chatMsg);
    // Arm the reply leg on every FORWARDED turn — a session-create (new conversation)
    // or a follow-up (the chain re-dispatches → a new exec on the same queue). The
    // leg then watches for the spawn, awaits turn-end, and delivers the reply.
    if (outcome && outcome.forwarded && chatMsg && chatMsg.chatThreadId) {
      replyLeg.arm(chatMsg.chatThreadId);
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

  async function start() {
    const r = await transport.start();
    replyLeg.start();
    log('info', 'chat bridge started', { transport: 'slack-socket-mode', ...r });
    return r;
  }

  function stop() {
    replyLeg.stop();
    transport.stop();
    log('info', 'chat bridge stopped');
  }

  return { onChatMessage, deliverToOwner, start, stop, _replyAddr: replyAddr, forwardPath, replyLeg };
}

module.exports = { createChatBridge };
