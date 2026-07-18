'use strict';

// Test Plan #3 — Outbound-only, no public ingress (chat-bridge-spec.md Behavior #4).
//
// `ss -tlnp` is snapshotted with the throwaway daemon + mock Slack already up, then
// again AFTER the bridge starts. Starting the bridge must add NO new LISTENING
// socket — it opens ONLY an outbound WebSocket (a connected client, never a
// listener) plus outbound HTTP to the gateway. The delta of listening sockets is
// the evidence; it MUST be empty.

const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { startThrowawayDaemon, startMockSlack, makeCapture, nowMs } = require('./lib');
const { resolveConfig } = require('../config');
const { createGatewayForwarder } = require('../gateway-forwarder');
const { createSlackSocketMode } = require('../slack-socket-mode');
const { buildBridge } = require('../index');

const OUT = path.join(__dirname, 'probe-chat-outbound.out');

// Parse `ss -tlnp` into a set of LISTEN "local address:port" tokens.
function listeningSockets() {
  const raw = execFileSync('ss', ['-tlnH'], { encoding: 'utf8' }); // -H: no header, -l: listening, -t: tcp, -n: numeric
  const set = new Set();
  for (const line of raw.split('\n')) {
    const cols = line.trim().split(/\s+/);
    if (cols.length >= 4) set.add(cols[3]); // local address:port column
  }
  return set;
}

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  let pass = false;
  let daemon, mock, bridgeH;
  try {
    daemon = await startThrowawayDaemon();
    mock = await startMockSlack();

    // Snapshot BEFORE the bridge exists: the daemon + mock listeners are present.
    const before = listeningSockets();
    cap.log({ step: 'listeners before bridge', count: before.size, sockets: [...before] });

    const config = resolveConfig({
      gatewayAddr: daemon.gatewayAddr, bridgeToken: daemon.bridgeToken,
      sessionProfile: 'worker', allowlist: ['U-owner'],
      slackApiBase: mock.apiBase, slackAppToken: 'xapp-fake', slackBotToken: 'xoxb-fake',
    });
    const forwarder = createGatewayForwarder({ gatewayAddr: config.gatewayAddr, token: config.bridgeToken });
    bridgeH = buildBridge(config, {
      logger: (o) => cap.log({ bridge: o }), forwarderImpl: forwarder,
      makeTransport: (onMessage) => createSlackSocketMode({
        appToken: config.slack.appToken, botToken: config.slack.botToken, apiBase: config.slack.apiBase, onMessage,
      }),
    });
    await bridgeH.bridge.start();
    await mock.connected; // the outbound WS is now established (a client, not a listener)

    const after = listeningSockets();
    const added = [...after].filter((s) => !before.has(s));
    cap.log({ step: 'listeners after bridge', count: after.size, sockets: [...after], addedByBridge: added });

    // The bridge added NO new listening socket.
    pass = added.length === 0;
  } catch (err) {
    cap.log({ error: err.message, stack: err.stack });
  } finally {
    try { bridgeH && bridgeH.bridge.stop(); } catch {}
    try { mock && mock.close(); } catch {}
    try { daemon && await daemon.close(); } catch {}
  }
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-outbound', pass, EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-outbound EXIT=${exit} WALL_MS=${wallMs} PASS=${pass}\n`);
  process.exit(exit);
}

main();
