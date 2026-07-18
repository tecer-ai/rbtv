'use strict';

// Test Plan #4 — Owner receives worker output (chat-bridge-spec.md Behavior #3).
//
// Worker/leader output addressed to the owner is delivered OUTBOUND to the chat
// user (turn boundary; text/attachments) via chat.postMessage. Drives the real
// outbound transport against the mock Slack server and asserts the message was
// posted to the conversation's channel + thread. Also asserts markAsk arms the
// D105 reply type (the owner's next reply becomes an `answer`).

const path = require('node:path');
const { startMockSlack, makeCapture, nowMs } = require('./lib');
const { resolveConfig } = require('../config');
const { createSlackSocketMode } = require('../slack-socket-mode');
const { buildBridge } = require('../index');

const OUT = path.join(__dirname, 'probe-chat-outbound-msg.out');

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  let pass = false;
  let mock, bridgeH;
  try {
    mock = await startMockSlack();
    const config = resolveConfig({
      gatewayAddr: '127.0.0.1:1', bridgeToken: 'unused-here', sessionProfile: 'worker', allowlist: ['U-owner'],
      slackApiBase: mock.apiBase, slackAppToken: 'xapp-fake', slackBotToken: 'xoxb-fake',
    });
    bridgeH = buildBridge(config, {
      logger: (o) => cap.log({ bridge: o }),
      forwarderImpl: { forward: async () => ({ ok: false, error: { code: 'UNUSED' } }), inspect: async () => ({ ok: false }) },
      makeTransport: (onMessage) => createSlackSocketMode({
        appToken: config.slack.appToken, botToken: config.slack.botToken, apiBase: config.slack.apiBase, onMessage,
      }),
    });

    // A conversation exists (opened by a first message) and has a known reply
    // address (the bridge records this on inbound messages). Set both directly to
    // isolate the outbound leg.
    const chatThreadId = 'C-chan:9.9';
    bridgeH.threadMap.create(chatThreadId, { queueId: 1 });
    bridgeH.bridge._replyAddr.set(chatThreadId, { channel: 'C-chan', threadTs: '9.9' });

    const res = await bridgeH.bridge.deliverToOwner({ chatThreadId, text: 'here is your PDF report', markAsk: true });
    cap.log({ step: 'delivered owner output', res, sentMessages: mock.sentMessages });

    const posted = mock.sentMessages.find((m) => m.channel === 'C-chan' && m.thread_ts === '9.9' && /PDF report/.test(m.text));
    const askArmed = bridgeH.threadMap.get(chatThreadId).pendingAsk === true;
    cap.log({ step: 'assertions', posted: Boolean(posted), askArmed });

    pass = res.delivered === true && Boolean(posted) && askArmed;
  } catch (err) {
    cap.log({ error: err.message, stack: err.stack });
  } finally {
    try { bridgeH && bridgeH.bridge.stop(); } catch {}
    try { mock && mock.close(); } catch {}
  }
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-outbound-msg', pass, EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-outbound-msg EXIT=${exit} WALL_MS=${wallMs} PASS=${pass}\n`);
  process.exit(exit);
}

main();
