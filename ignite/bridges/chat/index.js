'use strict';

// Process entry for the chat bridge (chat-bridge-spec.md). Thin: resolve config,
// construct the four parts, wire the transport's onMessage to the bridge, start.
//
// The bridge runs as a SEPARATE process from the daemon — it reaches the daemon
// ONLY over the gateway HTTP API as an authenticated sender. It opens NO inbound
// listener. Secrets come from the environment (config.js), never a committed file.

const { resolveConfig } = require('./config');
const { createGatewayForwarder } = require('./gateway-forwarder');
const { createAllowlist } = require('./allowlist');
const { createThreadMap } = require('./thread-map');
const { createSlackSocketMode } = require('./slack-socket-mode');
const { createChatBridge } = require('./chat-bridge');

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function jsonLog(entry) {
  // Never echo secrets: entries carry ids/reasons/counts only (see each module).
  process.stdout.write(JSON.stringify({ ts: isoNow(), ...entry }) + '\n');
}

// Construct a fully-wired bridge from a resolved config. Exposed for the probes
// (which inject a mock transport factory + a throwaway-daemon forwarder) and for
// main().
//
// The transport and the bridge reference each other (the transport calls the
// bridge's onChatMessage; the bridge calls the transport's sendToOwner). The
// circularity is resolved by a LATE-BOUND onMessage: `makeTransport(onMessage)`
// builds the transport around a callback that resolves the (by-then-assigned)
// bridge. `makeTransport` is injectable so a probe can substitute a mock
// Socket-Mode transport.
function buildBridge(config, { logger = jsonLog, makeTransport = null, forwarderImpl = null, replyLegOptions = {} } = {}) {
  const forwarder = forwarderImpl || createGatewayForwarder({ gatewayAddr: config.gatewayAddr, token: config.bridgeToken });
  const allowlist = createAllowlist({ allowed: config.allowlist, logger });
  const threadMap = createThreadMap({ logger });

  let bridge; // late-bound: the transport's onMessage closes over this
  const onMessage = (m) => bridge.onChatMessage(m);

  const factory = makeTransport || ((onMsg) => createSlackSocketMode({
    appToken: config.slack.appToken,
    botToken: config.slack.botToken,
    apiBase: config.slack.apiBase,
    onMessage: onMsg,
    logger,
  }));
  const transport = factory(onMessage);

  bridge = createChatBridge({ config, forwarder, transport, allowlist, threadMap, logger, replyLegOptions });

  return { bridge, forwarder, allowlist, threadMap, transport };
}

async function main() {
  const config = resolveConfig();
  if (!config.gatewayAddr) {
    jsonLog({ level: 'error', message: 'no gateway address configured — set IGNITE_GATEWAY_ADDR' });
    process.exit(1);
  }
  if (!config.bridgeToken) {
    jsonLog({ level: 'error', message: 'no bridge token configured — set IGNITE_BRIDGE_TOKEN (the kind:bridge sender token)' });
    process.exit(1);
  }

  const { bridge } = buildBridge(config);
  await bridge.start();

  const shutdown = (sig) => {
    jsonLog({ level: 'info', message: `received ${sig}, stopping chat bridge` });
    try { bridge.stop(); } catch {}
    process.exit(0);
  };
  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));
}

if (require.main === module) {
  main().catch((err) => {
    jsonLog({ level: 'error', message: 'chat bridge failed to start', error: err.message });
    process.exit(1);
  });
}

module.exports = { buildBridge };
