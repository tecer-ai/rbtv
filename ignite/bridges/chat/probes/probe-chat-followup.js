'use strict';

// Test Plan #6 — Follow-up reply reaches ongoing work as a MESSAGE on the chain's
// thread (chat-bridge-spec.md; D104/D105), EXTENDED for the D111 follow-up fix. The
// load-bearing invariants:
//
//   • a follow-up forwards as `add-job` carrying a `send-message` ACTION-TYPE job
//     addressed to the mapped turn-chain's thread (`exec-<first exec_id>`),
//   • NEVER `send-to-session` (D104 — that leg is headed-only),
//   • reply type is `answer` on a pending `ask`, else `note` (D105).
//
// The chain thread resolves via the gateway `inspect` intent (D69: job-id → exec-id
// → chain-thread) with TWO settled tiers (D111): the authoritative live_sessions
// `thread` when the session is live, else the chain-stable CONVENTION
// `exec-<first exec_id>` derived from the KNOWN first exec-id when the session is not
// live (the turn-boundary reality — short v1 turns end between the owner's messages).
//
// REAL-WIRING STYLE (matching probe-chat-reply-leg): messages enter over the mock
// Socket-Mode WS → the Slack transport → onChatMessage → the forward path (which
// also sets the outbound reply address), against a THROWAWAY in-process daemon
// (heart store + internal API + gateway) on an EPHEMERAL loopback port — NEVER the
// live daemon, NEVER port 7431. So the real ENQUEUE rows are asserted against a real
// store AND the honest owner NOTICES (D111 part 2) are asserted against real posts.
// The reply leg's interval is pinned far out so it never auto-fires (this probe
// drives only the forward path; the reply leg is exercised by probe-chat-reply-leg).
//
// D111 legs:
//   (f1) follow-up with the first exec KNOWN but NOT live → send-message enqueued
//        addressed to the DERIVED `exec-<firstExecId>` (convention fallback);
//   (f2) first-exec IMMUTABILITY — a second (later) exec-id bind is ignored
//        (first-wins), so the derived chain thread stays `exec-<firstExecId>`;
//   (f3) follow-up decline with exec-id-unknown → NOTHING enqueued + the fixed
//        DECLINE_NOTICE posted to the MAPPED thread (exact text) + NOTHING posted
//        for an unmapped/allowlist-refused user;
//   (f5) a FAILED notice post → logged and dropped, no retry loop, no enqueue, the
//        run continues (best-effort delivery).
//
// MUTATION EVIDENCE (validation #2): each guard is provable by this probe —
//   • remove the derivation fallback in thread-map.js resolveChainThread (M1) →
//     (f1) fails (declines with exec-id-not-live instead of enqueuing to exec-<E>);
//   • remove the first-wins guard in thread-map.js bindSessionExecId (M2) → (f2)
//     fails (the later exec-id overwrites; the derived thread becomes exec-<later>);
//   • remove the decline notice (postDeclineNotice) in forward-path.js (M3) →
//     (f3) fails (no notice posted on the mapped decline).
// Run each mutation → probe FAILS → restore byte-exact → passes.
//
// ⚑ Timing uses Node `Date.now()` — `date +%s%3N` is broken on this box (D64).

const path = require('node:path');
const { startThrowawayDaemon, startMockSlack, seedRunningExecution, makeCapture, sleep, nowMs } = require('./lib');
const { resolveConfig } = require('../config');
const { createGatewayForwarder } = require('../gateway-forwarder');
const { createSlackSocketMode } = require('../slack-socket-mode');
const { buildBridge } = require('../index');
const { DECLINE_NOTICE } = require('../forward-path');

const OUT = path.join(__dirname, 'probe-chat-followup.out');

function latestSendMessageRow(store) {
  const rows = store.listQueue().filter((r) => r.job_id === 'send-message');
  return rows.length ? rows[rows.length - 1] : null;
}
function sendMessageCount(store) {
  return store.listQueue().filter((r) => r.job_id === 'send-message').length;
}

// Wait (bounded) for an async condition the WS push settles into — the transport
// acks BEFORE onMessage completes, so state (an enqueue row / a posted notice) lands
// a few microtasks later.
async function waitFor(cond, { timeoutMs = 3000, stepMs = 25 } = {}) {
  const t0 = nowMs();
  while (nowMs() - t0 < timeoutMs) {
    if (cond()) return true;
    await sleep(stepMs);
  }
  return cond();
}

// Seed an ENDED execution (status `done`) — a KNOWN first exec that is NOT live, so
// resolveChainThread's convention-derivation fallback fires (`exec-<exec_id>`).
// live_sessions = running + launching only, so a done exec is absent from it.
function seedEndedExecution(store, { enqueuedBy }) {
  const ex = seedRunningExecution(store, { enqueuedBy });
  store.updateExecutionStatus(ex.exec_id, { status: 'done' });
  return ex; // ex.thread === 'exec-<exec_id>' (store-derived, chain-stable)
}

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const checks = [];
  const record = (name, ok, detail = {}) => { checks.push({ name, ok, ...detail }); cap.log({ check: name, ok, ...detail }); return ok; };
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
      // The reply leg is out of scope here — pin its interval far out so it never
      // auto-fires and never posts into the notice captures (probe-chat-reply-leg
      // exercises it). This probe drives only the forward path.
      replyLegOptions: { pollMs: 3600 * 1000 },
    });
    await bridgeH.bridge.start();
    await mock.connected;
    cap.log({ step: 'bridge connected to mock Socket Mode (outbound WS)' });

    const sent = mock.sentMessages;
    const lastPost = () => (sent.length ? sent[sent.length - 1] : null);

    // ── L1: live chain, follow-up with NO pending ask → reply type `note` ─────────
    // Authoritative live-session resolution: a RUNNING exec is in live_sessions, so
    // the chain thread comes from the store's `thread` (reason inspect-ticker).
    const execLive = seedRunningExecution(daemon.store, { enqueuedBy: daemon.bridgeSenderId });
    const liveThread = 'exec-' + execLive.exec_id; // store-derived, chain-stable
    const chanL1 = 'C-live-fu'; const tsL1 = '1700000000.010000';
    const threadL1 = `${chanL1}:${tsL1}`;
    bridgeH.threadMap.create(threadL1, { queueId: 1 });
    bridgeH.threadMap.bindSessionExecId(threadL1, execLive.exec_id);
    const beforeNote = sendMessageCount(daemon.store);
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'any progress?', channel: chanL1, thread_ts: tsL1, ts: '1700000000.010500', event_ts: '1700000000.010500', client_msg_id: 'fu-note' });
    await waitFor(() => sendMessageCount(daemon.store) > beforeNote);
    const noteRow = latestSendMessageRow(daemon.store);
    const noteArgs = noteRow ? JSON.parse(noteRow.args) : null;
    record('L1:live-chain follow-up (no pending ask) enqueues send-message type note on the chain thread',
      Boolean(noteRow) && noteRow.job_id === 'send-message' && noteArgs && noteArgs.type === 'note'
      && noteArgs.thread === execLive.thread && noteArgs.thread === liveThread,
      { row: noteRow ? { job_id: noteRow.job_id, args: noteArgs } : null });

    // ── L2: same live chain, pending ask → reply type `answer`, ask cleared ───────
    bridgeH.threadMap.setPendingAsk(threadL1, true);
    const beforeAns = sendMessageCount(daemon.store);
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'yes, ship it', channel: chanL1, thread_ts: tsL1, ts: '1700000000.010700', event_ts: '1700000000.010700', client_msg_id: 'fu-answer' });
    await waitFor(() => sendMessageCount(daemon.store) > beforeAns);
    const answerRow = latestSendMessageRow(daemon.store);
    const answerArgs = answerRow ? JSON.parse(answerRow.args) : null;
    const askCleared = bridgeH.threadMap.get(threadL1).pendingAsk === false;
    record('L2:pending-ask follow-up enqueues send-message type answer and clears the ask',
      Boolean(answerRow) && answerArgs && answerArgs.type === 'answer' && answerArgs.thread === execLive.thread && askCleared,
      { row: answerRow ? { args: answerArgs } : null, askCleared });

    // ── L3: queue-id-only conversation → exec_id learned from recent_ticks (live) ─
    // The bridge learns queue_id → exec_id from inspect ticker's recent_ticks[]
    // ({ action:'spawn', execId, queueId }, the Dispatch phase), then exec_id →
    // thread via live_sessions (the exec is running here).
    const execNav = seedRunningExecution(daemon.store, { enqueuedBy: daemon.bridgeSenderId });
    const navQueueId = 4242;
    daemon.store.recordTick({ tick: 2, actionsJson: JSON.stringify([
      { phase: 'dispatch', action: 'spawn', execId: execNav.exec_id, queueId: navQueueId, profile: 'worker' },
    ]) });
    const chanL3 = 'C-nav-fu'; const tsL3 = '1700000000.011000';
    const threadL3 = `${chanL3}:${tsL3}`;
    bridgeH.threadMap.create(threadL3, { queueId: navQueueId });
    const beforeNav = sendMessageCount(daemon.store);
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'status?', channel: chanL3, thread_ts: tsL3, ts: '1700000000.011500', event_ts: '1700000000.011500', client_msg_id: 'fu-nav' });
    await waitFor(() => sendMessageCount(daemon.store) > beforeNav);
    const navRow = latestSendMessageRow(daemon.store);
    const navArgs = navRow ? JSON.parse(navRow.args) : null;
    record('L3:queue-id-only conversation learns exec_id via recent_ticks and forwards on the true chain thread',
      Boolean(navRow) && navArgs && navArgs.type === 'note' && navArgs.thread === execNav.thread,
      { row: navRow ? { args: navArgs } : null });

    // ── f1: first exec KNOWN but NOT live → DERIVE exec-<firstExecId> (D111) ──────
    // The ended (done) exec is absent from live_sessions, so live resolution misses
    // and the convention-derivation fallback fires: the send-message is addressed to
    // `exec-<firstExecId>` — the chain-stable thread the ended chain re-consumes.
    const execEnded = seedEndedExecution(daemon.store, { enqueuedBy: daemon.bridgeSenderId });
    const derivedThread = 'exec-' + execEnded.exec_id;
    const chanF1 = 'C-derive-fu'; const tsF1 = '1700000000.014000';
    const threadF1 = `${chanF1}:${tsF1}`;
    bridgeH.threadMap.create(threadF1, { queueId: 5 });
    bridgeH.threadMap.bindSessionExecId(threadF1, execEnded.exec_id);
    const beforeF1 = sendMessageCount(daemon.store);
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'still on it?', channel: chanF1, thread_ts: tsF1, ts: '1700000000.014500', event_ts: '1700000000.014500', client_msg_id: 'fu-derive' });
    await waitFor(() => sendMessageCount(daemon.store) > beforeF1);
    const f1Row = latestSendMessageRow(daemon.store);
    const f1Args = f1Row ? JSON.parse(f1Row.args) : null;
    record('f1:exec KNOWN but NOT live → send-message enqueued addressed to the DERIVED exec-<firstExecId>',
      Boolean(f1Row) && f1Args && f1Args.type === 'note'
      && f1Args.thread === derivedThread && f1Args.thread === execEnded.thread,
      { derivedThread, storeThread: execEnded.thread, row: f1Row ? { args: f1Args } : null });

    // ── f2: first-exec IMMUTABILITY — a later exec-id bind must NOT change it ─────
    // Bind the FIRST exec (ended), then bind a LATER exec (ended, different id). The
    // later bind is IGNORED (first-wins), so the derived chain thread stays
    // exec-<firstExecId>. Under M2 (overwrite allowed) the thread would become
    // exec-<laterExecId> and this leg fails.
    const execFirst = seedEndedExecution(daemon.store, { enqueuedBy: daemon.bridgeSenderId });
    const execLater = seedEndedExecution(daemon.store, { enqueuedBy: daemon.bridgeSenderId });
    const chanF2 = 'C-immut-fu'; const tsF2 = '1700000000.015000';
    const threadF2 = `${chanF2}:${tsF2}`;
    bridgeH.threadMap.create(threadF2, { queueId: 6 });
    bridgeH.threadMap.bindSessionExecId(threadF2, execFirst.exec_id); // first — wins
    bridgeH.threadMap.bindSessionExecId(threadF2, execLater.exec_id); // later — MUST be ignored
    const boundExecId = bridgeH.threadMap.get(threadF2).sessionExecId;
    const beforeF2 = sendMessageCount(daemon.store);
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'and again', channel: chanF2, thread_ts: tsF2, ts: '1700000000.015500', event_ts: '1700000000.015500', client_msg_id: 'fu-immut' });
    await waitFor(() => sendMessageCount(daemon.store) > beforeF2);
    const f2Row = latestSendMessageRow(daemon.store);
    const f2Args = f2Row ? JSON.parse(f2Row.args) : null;
    record('f2:first-wins immutability — later exec-id bind ignored; derived chain thread stays exec-<firstExecId>',
      boundExecId === execFirst.exec_id && Boolean(f2Row) && f2Args
      && f2Args.thread === ('exec-' + execFirst.exec_id) && f2Args.thread !== ('exec-' + execLater.exec_id),
      { boundExecId, firstExecId: execFirst.exec_id, laterExecId: execLater.exec_id, thread: f2Args && f2Args.thread });

    // ── f3: decline with exec-id-unknown → DECLINE_NOTICE to the mapped thread ────
    // A conversation whose queue row never fired has no exec-id to derive from →
    // exec-id-unknown → nothing enqueued, and the fixed decline notice is posted to
    // the MAPPED thread (a reply address exists — set by the inbound message).
    const chanF3 = 'C-decline-fu'; const tsF3 = '1700000000.012000';
    const threadF3 = `${chanF3}:${tsF3}`;
    bridgeH.threadMap.create(threadF3, { queueId: 999983 }); // never fired
    const beforeDeclineQueue = daemon.store.listQueue().length;
    const beforeDeclinePosts = sent.length;
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'anyone there?', channel: chanF3, thread_ts: tsF3, ts: '1700000000.012500', event_ts: '1700000000.012500', client_msg_id: 'fu-decline' });
    await waitFor(() => sent.length > beforeDeclinePosts);
    const afterDeclineQueue = daemon.store.listQueue().length;
    const declinePost = lastPost();
    record('f3:mapped decline (exec-id-unknown) enqueues NOTHING and posts the exact DECLINE_NOTICE to the mapped thread',
      afterDeclineQueue === beforeDeclineQueue && declinePost
      && declinePost.text === DECLINE_NOTICE && declinePost.channel === chanF3 && declinePost.thread_ts === tsF3,
      { queueDelta: afterDeclineQueue - beforeDeclineQueue, post: declinePost });

    // f3 (continued): an unmapped/allowlist-REFUSED user gets NOTHING — no notice,
    // no enqueue. Refusal returns before the follow-up leg (security posture).
    const beforeRefusedPosts = sent.length;
    const beforeRefusedQueue = daemon.store.listQueue().length;
    await mock.pushMessage({ type: 'message', user: 'U-stranger', text: 'let me in', channel: 'C-refused-fu', ts: '1700000000.013000', event_ts: '1700000000.013000', client_msg_id: 'fu-refused' });
    await sleep(200); // give any (erroneous) post/enqueue time to appear — none must
    record('f3:allowlist-refused user gets NO notice and NO enqueue (never post on a refusal)',
      sent.length === beforeRefusedPosts && daemon.store.listQueue().length === beforeRefusedQueue,
      { postsDelta: sent.length - beforeRefusedPosts, queueDelta: daemon.store.listQueue().length - beforeRefusedQueue });

    // ── f5: a FAILED notice post → logged, dropped, NO retry loop, run continues ──
    // A mapped exec-id-unknown decline, but the notice's chat.postMessage is failed
    // once (ok:false). Best-effort: the failed post is logged and dropped, never
    // retried; nothing is enqueued; the run continues (no crash, no loop).
    const chanF5 = 'C-notice-fail-fu'; const tsF5 = '1700000000.016000';
    const threadF5 = `${chanF5}:${tsF5}`;
    bridgeH.threadMap.create(threadF5, { queueId: 888888 }); // never fired → exec-id-unknown
    const beforeF5Queue = daemon.store.listQueue().length;
    const beforeF5Posts = sent.length; // SUCCESSFUL posts only (the mock records ok:true posts)
    mock.failNextPostMessage(1);       // the decline notice post will fail (ok:false)
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'ping', channel: chanF5, thread_ts: tsF5, ts: '1700000000.016500', event_ts: '1700000000.016500', client_msg_id: 'fu-notice-fail' });
    await sleep(250); // allow the decline + failed notice attempt (and any erroneous retry) to complete
    const f5Ok = daemon.store.listQueue().length === beforeF5Queue && sent.length === beforeF5Posts;
    record('f5:failed notice post is logged and dropped — no retry loop, no enqueue, run continues',
      f5Ok,
      { queueDelta: daemon.store.listQueue().length - beforeF5Queue, successfulPostsDelta: sent.length - beforeF5Posts });
  } catch (err) {
    cap.log({ error: err.message, stack: err.stack });
    checks.push({ name: 'no-exception', ok: false, error: err.message });
  } finally {
    try { bridgeH && bridgeH.bridge.stop(); } catch {}
    try { mock && mock.close(); } catch {}
    try { daemon && await daemon.close(); } catch {}
  }

  const pass = checks.length > 0 && checks.every((c) => c.ok);
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-followup', pass, EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0, checks });
  process.stdout.write(`PROBE probe-chat-followup EXIT=${exit} WALL_MS=${wallMs} PASS=${pass}\n`);
  process.exit(exit);
}

main();
