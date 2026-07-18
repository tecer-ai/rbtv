'use strict';

// Test Plan #6 — Follow-up reply reaches ongoing work as a MESSAGE on the chain's
// thread (chat-bridge-spec.md; D104/D105). The load-bearing invariant:
//
//   • a follow-up forwards as `add-job` carrying a `send-message` ACTION-TYPE job
//     addressed to the mapped turn-chain's thread (`exec-<first exec_id>`),
//   • NEVER `send-to-session` (D104 — that leg is headed-only),
//   • reply type is `answer` on a pending `ask`, else `note` (D105).
//
// The chain thread is resolved via the gateway `inspect` intent (D69: job-id →
// exec-id → chain-thread). A running execution is seeded so a chain thread exists
// and inspect ticker exposes it.
//
// ⚑ STAGED (ADX-33(2)): the full live round-trip (a real dispatched session
// consuming the reply at its turn boundary) is exercised at p7-checkpoint. This
// probe validates the FORWARD SHAPE — the intent, the action type, the thread
// address, the reply type — against the throwaway daemon.

const path = require('node:path');
const { startThrowawayDaemon, seedRunningExecution, makeCapture, nowMs } = require('./lib');
const { resolveConfig } = require('../config');
const { createGatewayForwarder } = require('../gateway-forwarder');
const { buildBridge } = require('../index');

const OUT = path.join(__dirname, 'probe-chat-followup.out');

function stubTransportFactory() {
  return () => ({ start: async () => ({ connected: true }), stop() {}, sendToOwner: async (a) => ({ delivered: true, ...a }) });
}

function latestSendMessageRow(store) {
  const rows = store.listQueue().filter((r) => r.job_id === 'send-message');
  return rows.length ? rows[rows.length - 1] : null;
}

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  let pass = false;
  let daemon, bridgeH;
  try {
    daemon = await startThrowawayDaemon();
    const exec = seedRunningExecution(daemon.store, { enqueuedBy: daemon.bridgeSenderId });
    const chainThread = exec.thread; // 'exec-<exec_id>' (chain-stable, D24 Q3a)
    cap.log({ step: 'seeded running execution', execId: exec.exec_id, chainThread });

    const config = resolveConfig({
      gatewayAddr: daemon.gatewayAddr, bridgeToken: daemon.bridgeToken,
      sessionJobId: 'chat-launch', sessionProfile: 'worker', sendMessageJobId: 'send-message',
      allowlist: ['U-owner'],
    });
    const forwarder = createGatewayForwarder({ gatewayAddr: config.gatewayAddr, token: config.bridgeToken });
    bridgeH = buildBridge(config, { logger: (o) => cap.log({ bridge: o }), forwarderImpl: forwarder, makeTransport: stubTransportFactory() });

    // The conversation already exists (a first message opened it) and the bridge has
    // learned its first exec-id (D69 nav). Bind it so resolveChainThread can inspect it.
    const chatThreadId = 'C-chan:5.5';
    bridgeH.threadMap.create(chatThreadId, { queueId: 1 });
    bridgeH.threadMap.bindSessionExecId(chatThreadId, exec.exec_id);

    // (a) Follow-up with NO pending ask → reply type `note`.
    const noteOutcome = await bridgeH.bridge.forwardPath.onChatMessage({ chatUserId: 'U-owner', chatThreadId, text: 'any progress?' });
    const noteRow = latestSendMessageRow(daemon.store);
    const noteArgs = noteRow ? JSON.parse(noteRow.args) : null;
    cap.log({ step: 'follow-up (no pending ask)', outcome: noteOutcome, enqueuedRow: noteRow ? { queue_id: noteRow.queue_id, job_id: noteRow.job_id, args: noteArgs } : null });

    // (b) Arm a pending ask → the next follow-up forwards as `answer`.
    bridgeH.threadMap.setPendingAsk(chatThreadId, true);
    const answerOutcome = await bridgeH.bridge.forwardPath.onChatMessage({ chatUserId: 'U-owner', chatThreadId, text: 'yes, ship it' });
    const answerRow = latestSendMessageRow(daemon.store);
    const answerArgs = answerRow ? JSON.parse(answerRow.args) : null;
    const askCleared = bridgeH.threadMap.get(chatThreadId).pendingAsk === false;
    cap.log({ step: 'follow-up (pending ask)', outcome: answerOutcome, enqueuedRow: answerRow ? { queue_id: answerRow.queue_id, job_id: answerRow.job_id, args: answerArgs } : null, askCleared });

    // (c) A conversation holding ONLY its queue-row id (the exec-id never bound by
    // hand): the bridge learns queue_id → exec_id from inspect ticker's
    // recent_ticks[].actions[] ({ action:'spawn', execId, queueId }, recorded by
    // the ticker's Dispatch phase), then exec_id → thread via live_sessions.
    const spawnQueueId = 4242;
    daemon.store.recordTick({ tick: 2, actionsJson: JSON.stringify([
      { phase: 'dispatch', action: 'spawn', execId: exec.exec_id, queueId: spawnQueueId, profile: 'worker' },
    ]) });
    const chatThreadC = 'C-chan:7.7';
    bridgeH.threadMap.create(chatThreadC, { queueId: spawnQueueId });
    const navOutcome = await bridgeH.bridge.forwardPath.onChatMessage({ chatUserId: 'U-owner', chatThreadId: chatThreadC, text: 'status?' });
    const navRow = latestSendMessageRow(daemon.store);
    const navArgs = navRow ? JSON.parse(navRow.args) : null;
    cap.log({ step: 'follow-up (queue-id-only conversation, exec-id learned via recent_ticks)', outcome: navOutcome, enqueuedRow: navRow ? { queue_id: navRow.queue_id, job_id: navRow.job_id, args: navArgs } : null });

    // (d) A conversation whose queue row never fired: the bridge DECLINES —
    // forwarded:false, no fabricated thread, nothing enqueued.
    const chatThreadD = 'C-chan:8.8';
    bridgeH.threadMap.create(chatThreadD, { queueId: 999983 });
    const beforeDecline = daemon.store.listQueue().length;
    const declineOutcome = await bridgeH.bridge.forwardPath.onChatMessage({ chatUserId: 'U-owner', chatThreadId: chatThreadD, text: 'anyone there?' });
    const afterDecline = daemon.store.listQueue().length;
    cap.log({ step: 'follow-up (unresolvable chain) declines', outcome: declineOutcome, queueBefore: beforeDecline, queueAfter: afterDecline });

    pass =
      // note leg: enqueue-job (NOT send-to-session), send-message action type, on the chain thread, type note
      noteOutcome.forwarded === true && noteOutcome.intent === 'enqueue-job' && noteOutcome.replyType === 'note' &&
      noteOutcome.thread === chainThread && noteArgs && noteArgs.type === 'note' && noteArgs.thread === chainThread &&
      // answer leg: reply type answer, ask cleared after answering
      answerOutcome.forwarded === true && answerOutcome.intent === 'enqueue-job' && answerOutcome.replyType === 'answer' &&
      answerArgs && answerArgs.type === 'answer' && answerArgs.thread === chainThread && askCleared &&
      // nav leg: queue_id → exec_id learned from ticker actions; forwarded on the true chain thread
      navOutcome.forwarded === true && navOutcome.thread === chainThread &&
      navArgs && navArgs.type === 'note' && navArgs.thread === chainThread &&
      // decline leg: unresolvable chain → refuse to forward, nothing enqueued, no invented thread
      declineOutcome.forwarded === false && declineOutcome.reason === 'chain-unresolved:exec-id-unknown' &&
      afterDecline === beforeDecline;
  } catch (err) {
    cap.log({ error: err.message, stack: err.stack });
  } finally {
    try { daemon && await daemon.close(); } catch {}
  }
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-followup', pass, EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-followup EXIT=${exit} WALL_MS=${wallMs} PASS=${pass}\n`);
  process.exit(exit);
}

main();
