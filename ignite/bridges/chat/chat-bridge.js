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

function createChatBridge({ config, forwarder, transport, allowlist, threadMap, logger = null }) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  const forwardPath = createForwardPath({ forwarder, threadMap, allowlist, config, logger });

  // Inbound: a chat message → the forward path (admission, then session-create or
  // follow-up). Wired as the transport's onMessage.
  async function onChatMessage(chatMsg) {
    // Remember the Slack reply address for outbound delivery on this conversation.
    if (chatMsg && chatMsg.chatThreadId && chatMsg._channel) {
      replyAddr.set(chatMsg.chatThreadId, { channel: chatMsg._channel, threadTs: chatMsg._threadTs });
    }
    const outcome = await forwardPath.onChatMessage(chatMsg);
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
    log('info', 'chat bridge started', { transport: 'slack-socket-mode', ...r });
    return r;
  }

  function stop() {
    transport.stop();
    log('info', 'chat bridge stopped');
  }

  return { onChatMessage, deliverToOwner, start, stop, _replyAddr: replyAddr, forwardPath };
}

module.exports = { createChatBridge };
