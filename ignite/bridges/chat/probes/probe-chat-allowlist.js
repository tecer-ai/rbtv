'use strict';

// Test Plan #2 — Non-allowlisted user refused (chat-bridge-spec.md Behavior #2).
//
// A message from a NON-admitted chat principal is refused with NO forward (the
// OpenClaw-style DM-pairing gate); nothing is enqueued. A message from an ADMITTED
// principal on the same daemon DOES enqueue — the contrast proves the gate is what
// refuses, not a dead forward path.

const path = require('node:path');
const { startThrowawayDaemon, makeCapture, nowMs } = require('./lib');
const { resolveConfig } = require('../config');
const { createGatewayForwarder } = require('../gateway-forwarder');
const { buildBridge } = require('../index');

const OUT = path.join(__dirname, 'probe-chat-allowlist.out');

function stubTransportFactory() {
  return () => ({ start: async () => ({ connected: true }), stop() {}, sendToOwner: async (a) => ({ delivered: true, ...a }) });
}

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  let pass = false;
  let daemon, bridgeH;
  try {
    daemon = await startThrowawayDaemon();
    const config = resolveConfig({
      gatewayAddr: daemon.gatewayAddr, bridgeToken: daemon.bridgeToken,
      sessionJobId: 'chat-launch', sessionProfile: 'worker',
      allowlist: ['U-owner'], // U-stranger is NOT admitted
    });
    const forwarder = createGatewayForwarder({ gatewayAddr: config.gatewayAddr, token: config.bridgeToken });
    bridgeH = buildBridge(config, { logger: (o) => cap.log({ bridge: o }), forwarderImpl: forwarder, makeTransport: stubTransportFactory() });

    // 1) Non-admitted principal → refused, no forward, nothing enqueued.
    const beforeStranger = daemon.store.listQueue().length;
    const strangerOutcome = await bridgeH.bridge.onChatMessage({ chatUserId: 'U-stranger', chatThreadId: 'C-chan:1.1', text: 'let me in' });
    const afterStranger = daemon.store.listQueue().length;
    const pending = bridgeH.allowlist.pendingPairings();
    cap.log({ step: 'non-allowlisted', strangerOutcome, queueBefore: beforeStranger, queueAfter: afterStranger, pendingPairings: pending });

    // 2) Admitted principal → forwards + enqueues (contrast).
    const ownerOutcome = await bridgeH.bridge.onChatMessage({ chatUserId: 'U-owner', chatThreadId: 'C-chan:2.2', text: 'kick off', _channel: 'C-chan', _threadTs: '2.2' });
    const afterOwner = daemon.store.listQueue().length;
    cap.log({ step: 'allowlisted', ownerOutcome, queueAfter: afterOwner });

    pass =
      strangerOutcome.refused === true && strangerOutcome.forwarded === false &&
      afterStranger === beforeStranger &&                       // NOTHING enqueued for the stranger
      pending.some((p) => p.id === 'U-stranger') &&             // recorded as a pending pairing
      ownerOutcome.forwarded === true && afterOwner === beforeStranger + 1; // the admitted one DID enqueue
  } catch (err) {
    cap.log({ error: err.message, stack: err.stack });
  } finally {
    try { daemon && await daemon.close(); } catch {}
  }
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-allowlist', pass, EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-allowlist EXIT=${exit} WALL_MS=${wallMs} PASS=${pass}\n`);
  process.exit(exit);
}

main();
