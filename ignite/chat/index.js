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
const { createGoalChannelMap } = require('./goal-channel-map');
const { createChatBridge } = require('./chat-bridge');
const { createGlance } = require('./glance');

function log_noGoalChannels(logger) {
  if (logger) logger({ level: 'warn', message: 'transport exposes no channel admin surface — goal↔channel mapping disabled; channel traffic will be unroutable' });
}

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
function buildBridge(config, {
  logger = jsonLog, makeTransport = null, forwarderImpl = null, replyLegOptions = {}, busFerryOptions = {},
  // The one port the bridge process cannot hold itself — see createChatBridge's header. Neither
  // `materialize` nor the mechanical verb's applier is among them: D12 is the fourteenth gateway
  // intent `start-execution` (owner ruling 2026-08-24, option (b)) and `pause`/`resume` is the
  // `pause-resume` intent (owner direction 2026-08-28), and the bridge builds BOTH senders from
  // its own forwarder, always. `endingStore`/`listSeats`/`listLiveGoals` are gone: nothing ever
  // wired them, and an unwired applier port is a door that answers nothing.
  approvalPorts = {},
} = {}) {
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

  // The goal↔channel map (task 7.58) rides the transport's narrow admin surface
  // (create/list/archive, plus the owner-only creation-time invite ruled 2026-08-10 —
  // goal-channel-map.js § header). A transport that does not expose it (an older mock)
  // simply yields no map: the bridge then serves master (DM) traffic and treats every
  // channel as unroutable, which is the honest degradation, never a silent fallback to
  // goal traffic. A transport with `createChannel` but no `inviteToChannel` still gets
  // a map — it creates channels and invites nobody, exactly the pre-ruling behaviour.
  const goalChannels = (typeof transport.createChannel === 'function')
    ? createGoalChannelMap({ slack: transport, prefix: config.channelPrefix, ownerUser: config.ownerUser, logger })
    : null;
  if (!goalChannels) log_noGoalChannels(logger);

  bridge = createChatBridge({ config, forwarder, transport, allowlist, threadMap, goalChannels, logger, replyLegOptions, busFerryOptions, approvalPorts });

  // ── THE OWNER'S GLANCE SURFACES (spec-owner-io §5 + §6) ─────────────────────────────────────
  //
  // Built HERE and not inside `createChatBridge`, because both surfaces are composed entirely of
  // parts the bridge already owns — its one outbox, its one ask sender, its transport's status
  // port — and neither is reachable from a message the bridge routes. `glance.js` holds the
  // composition; this line is the wiring, and `main()` below is what starts the slot clock.
  //
  // ⚠ THE STATUS LINE IS CONSTRUCTED AND ITS TRANSPORT IS WIRED, BUT ITS SEVEN TRIGGERS ARE NOT
  // FIRED YET. §6's triggers (ask minted/answered/closed, blocked-on-human stamped/cleared, pause
  // and resume succeeded) live inside the ask door, the mechanical door and the reply leg; calling
  // `glance.onTrigger(...)` from those call sites is the remaining half, and it is deliberately not
  // invented here — an eighth trigger, or a trigger fired at the wrong moment, is a poll loop
  // against Slack's API (`status-line.js` ATTENTION 5).
  const glance = createGlance({
    outbox: bridge.outbox,
    askRecord: bridge.askRecord,
    setStatusText: (typeof transport.setStatusText === 'function')
      ? (text) => transport.setStatusText(text)
      : null,
    systemChannelId: config.systemChannelId,
    workspaceRoot: config.workspaceRoot,
    logger,
  });

  return { bridge, forwarder, allowlist, threadMap, transport, goalChannels, glance };
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

  const { bridge, glance } = buildBridge(config);
  await bridge.start();

  // The §5 slot driver. It is started only in `main()` — a probe or a test that builds a bridge
  // must never acquire a live 2-hourly clock as a side effect of construction.
  if (glance) glance.start();

  const shutdown = (sig) => {
    jsonLog({ level: 'info', message: `received ${sig}, stopping chat bridge` });
    try { if (glance) glance.stop(); } catch {}
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
