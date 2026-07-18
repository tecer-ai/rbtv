'use strict';

// Test Plan #1 — Allowlisted user enqueues via chat (chat-bridge-spec.md).
//
// FULL TRANSPORT ROUND-TRIP against the stand-ins (ADX-33(2)): a mock Socket-Mode
// server pushes a user message over an OUTBOUND WebSocket → the bridge's Slack
// transport → the forward path → the throwaway daemon's gateway → a queue row.
// Proves a validated job reaches the gateway → queue from an admitted chat user.

const path = require('node:path');
const { startThrowawayDaemon, startMockSlack, makeCapture, sleep, nowMs } = require('./lib');
const { resolveConfig } = require('../config');
const { createGatewayForwarder } = require('../gateway-forwarder');
const { createSlackSocketMode } = require('../slack-socket-mode');
const { buildBridge } = require('../index');

const OUT = path.join(__dirname, 'probe-chat-enqueue.out');

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  let pass = false;
  let daemon, mock, bridgeH;
  try {
    daemon = await startThrowawayDaemon();
    mock = await startMockSlack();
    cap.log({ step: 'stood up throwaway daemon + mock Slack', gatewayAddr: daemon.gatewayAddr, slackApiBase: mock.apiBase });

    const config = resolveConfig({
      gatewayAddr: daemon.gatewayAddr, bridgeToken: daemon.bridgeToken,
      sessionJobId: 'chat-launch', sessionProfile: 'worker', sendMessageJobId: 'send-message',
      allowlist: ['U-owner'], slackApiBase: mock.apiBase, slackAppToken: 'xapp-fake', slackBotToken: 'xoxb-fake',
    });

    const forwarder = createGatewayForwarder({ gatewayAddr: config.gatewayAddr, token: config.bridgeToken });
    bridgeH = buildBridge(config, {
      logger: (o) => cap.log({ bridge: o }),
      forwarderImpl: forwarder,
      makeTransport: (onMessage) => createSlackSocketMode({
        appToken: config.slack.appToken, botToken: config.slack.botToken, apiBase: config.slack.apiBase,
        onMessage, logger: (o) => cap.log({ transport: o }),
      }),
    });

    await bridgeH.bridge.start();
    await mock.connected;
    cap.log({ step: 'bridge connected to mock Socket Mode (outbound WS)' });

    const before = daemon.store.listQueue().length;
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'kick off a build', channel: 'C-chan', ts: '1700000000.000100' });
    cap.log({ step: 'pushed a user message from allowlisted U-owner' });

    // Poll for the enqueued queue row (the bridge acks first, then forwards async).
    let rows = [];
    for (let i = 0; i < 40; i++) {
      rows = daemon.store.listQueue();
      if (rows.length > before) break;
      await sleep(50);
    }
    const row = rows.find((r) => r.job_id === 'chat-launch');
    cap.log({ step: 'queue after', queueDepth: rows.length, enqueuedRow: row ? { queue_id: row.queue_id, job_id: row.job_id, action: 'launch-agent', enqueued_by: row.enqueued_by, args: row.args } : null });

    // A validated launch-agent job reached the gateway → queue, enqueued_by the bridge sender.
    pass = Boolean(row) && row.job_id === 'chat-launch' && row.enqueued_by === daemon.bridgeSenderId
      && JSON.parse(row.args).profile === 'worker';
  } catch (err) {
    cap.log({ error: err.message, stack: err.stack });
  } finally {
    try { bridgeH && bridgeH.bridge.stop(); } catch {}
    try { mock && mock.close(); } catch {}
    try { daemon && await daemon.close(); } catch {}
  }
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-enqueue', pass, EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-enqueue EXIT=${exit} WALL_MS=${wallMs} PASS=${pass}\n`);
  process.exit(exit);
}

main();
