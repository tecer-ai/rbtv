'use strict';

// Test Plan #1 — Allowlisted user enqueues via chat (chat-bridge-spec.md).
//
// FULL TRANSPORT ROUND-TRIP against the stand-ins (ADX-33(2)): a mock Socket-Mode
// server pushes a user message over an OUTBOUND WebSocket → the bridge's Slack
// transport → the forward path → the throwaway daemon's gateway → a queue row.
// Proves a validated job reaches the gateway → queue from an admitted chat user.
//
// REDELIVERY LEG (D108(C)): the bridge drops duplicate Slack events (at-least-once
// redelivery guard). The same event re-pushed under a NEW envelope id must NOT
// produce a second queue entry. Mutation evidence: disable the dedupe cache in
// slack-socket-mode.js → the leg FAILS (two entries) → restore byte-exact.

const path = require('node:path');
const { startThrowawayDaemon, startMockSlack, seedRunningExecution, makeCapture, sleep, nowMs } = require('./lib');
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
    cap.log({ step: 'enqueue result', pass });

    // ── Redelivery leg (D108(C) at-least-once guard) ──────────────────────────
    // Use the SAME client_msg_id on two DIFFERENT channels. Without dedupe, each
    // would create a session (different chatThreadId → both are "first message"
    // paths). With dedupe, the second is dropped by client_msg_id before forward.
    const redeliverMsgId = 'msg-redeliver-p7-2b';
    const afterFirst = daemon.store.listQueue().length;
    await mock.pushMessage({
      type: 'message', user: 'U-owner', text: 'redelivery test message',
      channel: 'C-redel-A', ts: '1700000000.001000',
      client_msg_id: redeliverMsgId,
    });
    cap.log({ step: 'pushed redelivery test message (channel A)', client_msg_id: redeliverMsgId });

    let redeliveryRows = [];
    for (let i = 0; i < 40; i++) {
      redeliveryRows = daemon.store.listQueue();
      if (redeliveryRows.length > afterFirst) break;
      await sleep(50);
    }
    const afterOne = redeliveryRows.length;
    cap.log({ step: 'queue after first push (channel A)', queueDepth: afterOne, delta: afterOne - afterFirst });

    // Re-push the SAME client_msg_id on a DIFFERENT channel. Without dedupe this
    // would be a first-message-on-new-thread → another session-create → a second
    // new queue row. The dedupe must drop it silently (client_msg_id match).
    await mock.pushMessage({
      type: 'message', user: 'U-owner', text: 'redelivery test message',
      channel: 'C-redel-B', ts: '1700000000.002000',
      client_msg_id: redeliverMsgId,
    });
    cap.log({ step: 're-pushed same client_msg_id on different channel (simulated redelivery)', client_msg_id: redeliverMsgId });

    await sleep(200);
    const afterTwo = daemon.store.listQueue().length;
    const redeliveryOk = afterTwo === afterOne;
    cap.log({ step: 'queue after redelivery (channel B)', queueDepth: afterTwo, delta: afterTwo - afterOne, deduped: afterTwo === afterOne });

    pass = pass && redeliveryOk;
    if (!redeliveryOk) {
      cap.log({ step: 'REDELIVERY GUARD FAILED (cross-channel)', expectedQueueDepth: afterOne, actualQueueDepth: afterTwo });
    }

    // ── SAME-channel redelivery on a LIVE chain (realistic Slack at-least-once) ─
    // The load-bearing leg (review pre-flag #1). Real Slack redelivery re-pushes the
    // SAME event on the SAME channel/event_ts — only the ENVELOPE id changes
    // (pushMessage mints a fresh one per call). NOTE the trap: a same-channel
    // redelivery of a FIRST message routes as a follow-up, and with no live chain it
    // is DECLINED (queue unchanged even WITHOUT the guard — not observable). The real
    // same-channel defect is a duplicate FOLLOW-UP double-`send-message`ing a LIVE
    // chain. So we seed a live chain, forward one follow-up (→ one send-message), then
    // redeliver the IDENTICAL event: the guard must drop it by client_msg_id BEFORE
    // the forward path, leaving exactly ONE send-message.
    const sendMsgCount = () => daemon.store.listQueue().filter((r) => r.job_id === 'send-message').length;

    const execA = seedRunningExecution(daemon.store, { enqueuedBy: daemon.bridgeSenderId });
    const liveChan = 'C-live';
    const liveTs = '1700000000.007000';
    const liveThreadId = `${liveChan}:${liveTs}`;
    bridgeH.threadMap.create(liveThreadId, { queueId: 1 });
    bridgeH.threadMap.bindChainThread(liveThreadId, execA.thread); // chain resolvable → follow-ups forward
    const liveMsgId = 'msg-followup-redeliver-p7-2b';
    const liveFollowEvent = {
      type: 'message', user: 'U-owner', text: 'follow-up on the live chain',
      channel: liveChan, thread_ts: liveTs, ts: '1700000000.007500', event_ts: '1700000000.007500',
      client_msg_id: liveMsgId,
    };
    const sendBeforeLive = sendMsgCount();
    await mock.pushMessage(liveFollowEvent);
    let sendAfterOne = sendBeforeLive;
    for (let i = 0; i < 40; i++) {
      sendAfterOne = sendMsgCount();
      if (sendAfterOne > sendBeforeLive) break;
      await sleep(50);
    }
    cap.log({ step: 'live-chain follow-up enqueued one send-message', sendMessages: sendAfterOne, delta: sendAfterOne - sendBeforeLive });

    await mock.pushMessage({ ...liveFollowEvent }); // IDENTICAL event, NEW envelope = realistic redelivery
    cap.log({ step: 're-pushed IDENTICAL follow-up on SAME channel (realistic Slack redelivery)', client_msg_id: liveMsgId });
    await sleep(200);
    const sendAfterTwo = sendMsgCount();
    const sameChanOk = sendAfterOne === sendBeforeLive + 1 && sendAfterTwo === sendAfterOne;
    cap.log({ step: 'send-message count after same-channel redelivery', sendMessages: sendAfterTwo, deduped: sendAfterTwo === sendAfterOne });
    pass = pass && sameChanOk;
    if (!sameChanOk) {
      cap.log({ step: 'REDELIVERY GUARD FAILED (same-channel live-chain double-send)', expected: sendBeforeLive + 1, actual: sendAfterTwo });
    }

    // ── Fallback-key leg: (channel, event_ts) when client_msg_id is absent ─────
    // Not every message event carries a client_msg_id; the guard falls back to
    // (channel, event_ts). Same live-chain follow-up shape, NO client_msg_id →
    // the redelivery must still be dropped by the composite fallback key.
    const execB = seedRunningExecution(daemon.store, { enqueuedBy: daemon.bridgeSenderId });
    const liveChan2 = 'C-live2';
    const liveTs2 = '1700000000.008000';
    const liveThreadId2 = `${liveChan2}:${liveTs2}`;
    bridgeH.threadMap.create(liveThreadId2, { queueId: 1 });
    bridgeH.threadMap.bindChainThread(liveThreadId2, execB.thread);
    const noIdFollowEvent = {
      type: 'message', user: 'U-owner', text: 'fallback-key follow-up',
      channel: liveChan2, thread_ts: liveTs2, ts: '1700000000.008500', event_ts: '1700000000.008500',
    };
    const sendBeforeNoId = sendMsgCount();
    await mock.pushMessage(noIdFollowEvent);
    let sendNoIdOne = sendBeforeNoId;
    for (let i = 0; i < 40; i++) {
      sendNoIdOne = sendMsgCount();
      if (sendNoIdOne > sendBeforeNoId) break;
      await sleep(50);
    }
    await mock.pushMessage({ ...noIdFollowEvent }); // IDENTICAL client_msg_id-less event, new envelope
    cap.log({ step: 're-pushed IDENTICAL client_msg_id-less follow-up (fallback key (channel,event_ts))', channel: liveChan2, event_ts: noIdFollowEvent.event_ts });
    await sleep(200);
    const sendNoIdTwo = sendMsgCount();
    const noIdOk = sendNoIdOne === sendBeforeNoId + 1 && sendNoIdTwo === sendNoIdOne;
    cap.log({ step: 'send-message count after fallback-key redelivery', sendMessages: sendNoIdTwo, deduped: sendNoIdTwo === sendNoIdOne });
    pass = pass && noIdOk;
    if (!noIdOk) {
      cap.log({ step: 'REDELIVERY GUARD FAILED (fallback (channel,event_ts) key)', expected: sendBeforeNoId + 1, actual: sendNoIdTwo });
    }

    // ── Negative control: two GENUINELY DISTINCT messages must BOTH pass ───────
    // D108(C): never drop two distinct messages. Distinct client_msg_id on DISTINCT
    // channels → both are first-messages → both must enqueue a session-create
    // (the guard must not over-drop). Distinct channels avoid the follow-up path.
    const chatLaunchCount = () => daemon.store.listQueue().filter((r) => r.job_id === 'chat-launch').length;
    const beforeDistinct = chatLaunchCount();
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'distinct A', channel: 'C-distinct-A', ts: '1700000000.005000', event_ts: '1700000000.005000', client_msg_id: 'distinct-A' });
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'distinct B', channel: 'C-distinct-B', ts: '1700000000.006000', event_ts: '1700000000.006000', client_msg_id: 'distinct-B' });
    let distinctDelta = 0;
    for (let i = 0; i < 40; i++) {
      distinctDelta = chatLaunchCount() - beforeDistinct;
      if (distinctDelta >= 2) break;
      await sleep(50);
    }
    const distinctOk = distinctDelta === 2;
    cap.log({ step: 'two distinct messages both enqueued (never-over-drop)', delta: distinctDelta, ok: distinctOk });
    pass = pass && distinctOk;
    if (!distinctOk) {
      cap.log({ step: 'OVER-DROP DEFECT: distinct messages did not both enqueue', expectedDelta: 2, actualDelta: distinctDelta });
    }
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
