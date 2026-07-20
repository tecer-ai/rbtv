'use strict';

// Test Plan #4 (production driver) — the OUTBOUND REPLY LEG (chat-bridge-spec.md
// Behavior #3; owner ruling D110). Closes the loop the forward path opens: a
// worker finishes its turn → the bridge fetches its answer from the daemon over
// the `inspect` surface → posts it into the mapped Slack thread via deliverToOwner.
//
// STAGED (ADX-33(2)): the live round-trip (a real dispatched session, real Slack)
// runs at p7-checkpoint. This probe validates the DRIVER against stand-ins: a MOCK
// Slack server (the real Socket-Mode inbound + chat.postMessage outbound paths) +
// an INJECTED forwarder scripted to return enqueue/ticker/status/logs sequences
// (the daemon surface). Arming is driven through the REAL wiring — a Slack message
// event pushed over the mock Socket-Mode WS → onChatMessage → forward path →
// chat-bridge arms the leg on the forwarded outcome — never by hand-calling the
// driver. Driver passes run deterministically via `replyLeg.tick()` (the interval
// is pinned far out). Legs:
//   (a) a REAL inbound message forwards (enqueue) → the bridge arms the leg →
//       the spawn appears in recent_ticks → execId captured; nothing posted live;
//   (b) status flips live:false → logs fetched → LAST result line extracted →
//       chat.postMessage posted to the conversation's channel+thread, text EQUAL
//       to the extracted result string (content identity);
//   (c) a log with NO parseable result line → the FIXED fallback is posted, never
//       the raw log;
//   (d) the same exec is NEVER delivered twice;
//   (e) a REAL follow-up message (same thread) re-arms via the forward path →
//       second spawn, SAME queueId, NEW execId → a second reply, text-equal;
//   (g) a log spanning MULTIPLE bounded pages → the driver pages to the log END
//       and still extracts the LAST result line (content identity);
//   (h) a TRANSIENT `inspect logs` failure posts NOTHING (no fallback — the real
//       answer is not burned), the exec stays watched, and the next healthy pass
//       delivers the REAL text;
//   (i) a REFUSED chat.postMessage (ok:false) does NOT mark the exec delivered —
//       the next pass retries and delivers;
//   (j) PERSISTENT fetch failure gives up at the bounded attempt cap: the exec is
//       retired undelivered (honest non-delivery), and the HONEST GIVE-UP NOTICE
//       (D111 part 2) is posted to the owner — no silent success, no unbounded retry.
//
// MUTATION EVIDENCE (validation #2): each guard is provable by this probe —
//   • comment the `deliver(...)` call in reply-leg.js _runOnce → b/c/e/g fail;
//   • comment `replyLeg.arm(...)` in chat-bridge.js onChatMessage → (a) fails;
//   • make fetchReplyText return {fetched:true} on a failed page → (h) fails
//     (fallback posted on a transport blip);
//   • drop the `d.delivered === false` check → (i) fails (refused post marked done);
//   • drop the attempt cap → (j) fails (unbounded retry);
//   • break the paging loop after page 0 → (g) fails;
//   • remove the give-up notice deliver at the attempt cap (M4) → (j) fails
//     (no notice posted; sent stays 6 and lastText ≠ GIVE_UP_NOTICE).
// Run each mutation → probe FAILS → restore byte-exact → passes.
//
// ⚑ Timing uses Node `Date.now()` — `date +%s%3N` is broken on this box (D64).

const path = require('node:path');
const { startMockSlack, makeCapture, nowMs, sleep } = require('./lib');
const { resolveConfig } = require('../config');
const { createSlackSocketMode } = require('../slack-socket-mode');
const { buildBridge } = require('../index');
const { FALLBACK_TEXT, GIVE_UP_NOTICE } = require('../reply-leg');

const OUT = path.join(__dirname, 'probe-chat-reply-leg.out');

// A scripted forwarder standing in for the gateway surface. State is mutated
// between driver passes to script each leg deterministically.
//   recentTicks:  [{ tick, actions: [{ action:'spawn', execId, queueId }, …] }]
//   liveSessions: [{ exec_id, thread }]                (chain-thread resolution, leg e)
//   status:       Map<execId, { live, status }>
//   logs:         Map<execId, string[]>                (stream-json lines)
//   logPageMax:   server-side page clamp stand-in (dispatch.js MAX_PAGE shape)
//   failLogs:     fail the next N `inspect logs` calls (transient transport error)
function scriptedForwarder(state) {
  return {
    // The forward path's enqueue-job — returns the queue-row id (jobId) exactly
    // like the gateway result shape, so threadMap records the REAL enqueue result.
    forward: async (intent) => ({ ok: true, result: { jobId: state.nextJobId } }),
    inspect: async (target, extra = {}) => {
      if (target === 'ticker') {
        return { ok: true, result: { target: 'ticker', recent_ticks: state.recentTicks, live_sessions: state.liveSessions } };
      }
      if (target === 'status') {
        const s = state.status.get(Number(extra.id));
        if (!s) return { ok: false, error: { code: 'NOT_FOUND', message: `no status for ${extra.id}` } };
        return { ok: true, result: { target: 'status', id: Number(extra.id), live: s.live, status: s.status } };
      }
      if (target === 'logs') {
        if (state.failLogs > 0) {
          state.failLogs -= 1;
          return { ok: false, error: { code: 'TRANSPORT', message: 'scripted transient logs failure' } };
        }
        // The bounded-page surface (dispatch.js shape): limit clamped server-side,
        // lines/nextOffset/eof — so the driver's paging loop is really exercised.
        const all = state.logs.get(Number(extra.id)) || [];
        const offset = Number.isInteger(extra.offset) ? extra.offset : 0;
        const limit = Math.min(Number.isInteger(extra.limit) ? extra.limit : 200, state.logPageMax);
        const lines = all.slice(offset, offset + limit);
        const nextOffset = offset + lines.length;
        return { ok: true, result: { target: 'logs', id: Number(extra.id), lines, nextOffset, eof: nextOffset >= all.length } };
      }
      return { ok: false, error: { code: 'UNKNOWN_TARGET', message: target } };
    },
  };
}

function resultLine(text) {
  return JSON.stringify({ type: 'result', subtype: 'success', result: text, is_error: false });
}

// Wait (bounded) for an async condition the WS push settles into — the transport
// acks BEFORE onMessage completes, so state lands a few microtasks later.
async function waitFor(cond, { timeoutMs = 2000, stepMs = 20 } = {}) {
  const t0 = nowMs();
  while (nowMs() - t0 < timeoutMs) {
    if (cond()) return true;
    await sleep(stepMs);
  }
  return cond();
}

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const checks = [];
  const record = (name, ok, detail = {}) => { checks.push({ name, ok, ...detail }); cap.log({ check: name, ok, ...detail }); return ok; };
  let mock, bridgeH;
  try {
    mock = await startMockSlack();

    const state = { recentTicks: [], liveSessions: [], status: new Map(), logs: new Map(), logPageMax: 500, failLogs: 0, nextJobId: 100 };
    const config = resolveConfig({
      gatewayAddr: '127.0.0.1:1', bridgeToken: 'unused-here', sessionProfile: 'worker', allowlist: ['U-owner'],
      slackApiBase: mock.apiBase, slackAppToken: 'xapp-fake', slackBotToken: 'xoxb-fake',
    });
    // Real Slack transport (mock Socket-Mode WS inbound; posts to the mock outbound)
    // + scripted forwarder (the daemon surface). The driver interval is pinned far
    // out (1 h) so ONLY the probe's manual `tick()` passes run; the retry bound is
    // pinned to 3 so leg (j) proves the cap in three passes.
    const forwarder = scriptedForwarder(state);
    bridgeH = buildBridge(config, {
      logger: (o) => cap.log({ bridge: o }),
      forwarderImpl: forwarder,
      makeTransport: (onMessage) => createSlackSocketMode({
        appToken: config.slack.appToken, botToken: config.slack.botToken, apiBase: config.slack.apiBase, onMessage,
      }),
      replyLegOptions: { pollMs: 3600 * 1000, maxDeliverAttempts: 3 },
    });
    await bridgeH.bridge.start();
    await mock.connected;

    const CHANNEL = 'C-chan';
    const ROOT_TS = '1700000000.000100';
    const CHAT = `${CHANNEL}:${ROOT_TS}`;
    const QUEUE = 100; // = state.nextJobId — what the scripted enqueue returned

    const sent = mock.sentMessages;
    const lastText = () => (sent.length ? sent[sent.length - 1].text : null);
    const postedTo = (m) => m && m.channel === CHANNEL && m.thread_ts === ROOT_TS;
    const leg = () => bridgeH.bridge.replyLeg;
    const pend = () => leg()._pending.get(CHAT);

    // ── (a) REAL inbound message → forward path enqueues → bridge arms the leg ───
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'kick off a build', channel: CHANNEL, ts: ROOT_TS, event_ts: ROOT_TS, client_msg_id: 'reply-leg-m1' });
    const armed = await waitFor(() => Boolean(pend()));
    const entryA = bridgeH.threadMap.get(CHAT);
    record('a1:forwarded message armed the leg with the ACTUAL enqueue queueId',
      armed && entryA && entryA.queueId === QUEUE && pend().queueId === QUEUE,
      { armed, mappedQueueId: entryA && entryA.queueId, armedQueueId: pend() && pend().queueId });

    // spawn appears → execId captured; nothing posted while live.
    state.recentTicks = [{ tick: 1, actions: [{ action: 'spawn', execId: 26, queueId: QUEUE }] }];
    state.status.set(26, { live: true, status: 'running' });
    await leg().tick();
    record('a2:exec captured while live, nothing posted', pend().watching.has(26) && sent.length === 0,
      { watching: [...pend().watching.keys()], sentCount: sent.length });

    // ── (b) status flips live:false → LAST result line extracted → posted ────────
    state.status.set(26, { live: false, status: 'failed' }); // crash-sweep mislabels success 'failed' — we key on live
    state.logs.set(26, [
      JSON.stringify({ type: 'system', subtype: 'init' }),
      JSON.stringify({ type: 'result', subtype: 'partial', result: 'an EARLIER result line' }),
      JSON.stringify({ type: 'assistant', message: { content: 'thinking' } }),
      resultLine('the answer is 42'),
    ]);
    await leg().tick();
    record('b:reply posted to channel+thread, text EQUALS the last result string',
      sent.length === 1 && postedTo(sent[0]) && sent[0].text === 'the answer is 42',
      { sentCount: sent.length, posted: postedTo(sent[0]), text: sent[0] && sent[0].text });

    // ── (d) same exec never delivered twice (spawn still present, still live:false) ─
    await leg().tick();
    record('d:same exec not redelivered', sent.length === 1, { sentCount: sent.length });

    // ── (c) a log with NO result line → fixed fallback posted, never the raw log ──
    state.recentTicks.push({ tick: 2, actions: [{ action: 'spawn', execId: 27, queueId: QUEUE }] });
    state.status.set(27, { live: false, status: 'failed' });
    state.logs.set(27, [
      JSON.stringify({ type: 'system', subtype: 'init' }),
      'this is not json at all',
      JSON.stringify({ type: 'assistant', message: { content: 'no result line here' } }),
    ]);
    await leg().tick();
    record('c:no-result-line log delivers the fixed fallback (never the raw log)',
      sent.length === 2 && lastText() === FALLBACK_TEXT && !/not json/.test(lastText()),
      { sentCount: sent.length, text: lastText(), isFallback: lastText() === FALLBACK_TEXT });

    // ── (e) REAL follow-up (same thread) re-arms via the forward path ────────────
    // The follow-up leg resolves the chain thread from the SAME ticker surface
    // (recent_ticks queue→exec + live_sessions exec→thread), then enqueues a
    // send-message — outcome.forwarded → chat-bridge re-arms the leg.
    // The fixture row matches the REAL inspect-ticker surface (dispatch.js
    // handleInspectTicker): every live_sessions row carries queue_id (D108(B)) —
    // the queue-id resolution tier (thread-map.js resolveChainThread) keys on it.
    state.liveSessions = [{ exec_id: 26, queue_id: QUEUE, thread: 'exec-26' }];
    const tickerViewE = await forwarder.inspect('ticker');
    const liveRowsE = (tickerViewE.ok && tickerViewE.result.live_sessions) || [];
    record('e0:regression guard — every live_sessions row the probe consumes carries queue_id (real-surface shape)',
      tickerViewE.ok && liveRowsE.length > 0 && liveRowsE.every((r) => Number.isInteger(r.queue_id))
      && liveRowsE.some((r) => r.exec_id === 26 && r.queue_id === QUEUE),
      { rows: liveRowsE });
    const armedAtBefore = pend().armedAt;
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'and a follow-up', channel: CHANNEL, thread_ts: ROOT_TS, ts: '1700000000.000200', event_ts: '1700000000.000200', client_msg_id: 'reply-leg-m2' });
    const rearmed = await waitFor(() => pend().armedAt > armedAtBefore);
    state.recentTicks.push({ tick: 3, actions: [{ action: 'spawn', execId: 28, queueId: QUEUE }] });
    state.status.set(28, { live: false, status: 'done' });
    state.logs.set(28, [resultLine('second turn reply')]);
    await leg().tick();
    record('e:real follow-up re-armed; new exec on same queue delivers a text-equal second reply',
      rearmed && sent.length === 3 && postedTo(sent[2]) && sent[2].text === 'second turn reply',
      { rearmed, sentCount: sent.length, text: lastText() });

    // ── (g) a log spanning MULTIPLE bounded pages → paged to the END ─────────────
    state.logPageMax = 2; // tiny server page: 7 lines → 4 pages; the result line is LAST
    state.recentTicks.push({ tick: 4, actions: [{ action: 'spawn', execId: 29, queueId: QUEUE }] });
    state.status.set(29, { live: false, status: 'failed' });
    state.logs.set(29, [
      JSON.stringify({ type: 'system', subtype: 'init' }),
      JSON.stringify({ type: 'assistant', message: { content: 'page filler 1' } }),
      JSON.stringify({ type: 'assistant', message: { content: 'page filler 2' } }),
      JSON.stringify({ type: 'assistant', message: { content: 'page filler 3' } }),
      JSON.stringify({ type: 'assistant', message: { content: 'page filler 4' } }),
      JSON.stringify({ type: 'assistant', message: { content: 'page filler 5' } }),
      resultLine('answer beyond page one'),
    ]);
    await leg().tick();
    record('g:multi-page log paged to the end — last result line extracted, text-equal',
      sent.length === 4 && lastText() === 'answer beyond page one',
      { sentCount: sent.length, text: lastText(), pageMax: state.logPageMax });
    state.logPageMax = 500;

    // ── (h) TRANSIENT logs failure: NOTHING posted (no fallback), then recovery ──
    state.recentTicks.push({ tick: 5, actions: [{ action: 'spawn', execId: 30, queueId: QUEUE }] });
    state.status.set(30, { live: false, status: 'failed' });
    state.logs.set(30, [resultLine('survived the blip')]);
    state.failLogs = 1;
    await leg().tick();
    const hHeld = sent.length === 4 && pend().watching.has(30) && pend().watching.get(30).attempts === 1;
    await leg().tick(); // logs healthy again
    record('h:transient logs failure posts nothing, exec retried, REAL text delivered',
      hHeld && sent.length === 5 && lastText() === 'survived the blip' && pend().delivered.has(30),
      { heldOnFailure: hHeld, sentCount: sent.length, text: lastText() });

    // ── (i) REFUSED chat.postMessage → not marked delivered → retried, delivered ─
    state.recentTicks.push({ tick: 6, actions: [{ action: 'spawn', execId: 31, queueId: QUEUE }] });
    state.status.set(31, { live: false, status: 'failed' });
    state.logs.set(31, [resultLine('post me twice if you dare')]);
    mock.failNextPostMessage(1);
    await leg().tick();
    const iHeld = sent.length === 5 && pend().watching.has(31) && !pend().delivered.has(31);
    await leg().tick(); // Slack healthy again
    record('i:refused post not marked delivered; retry delivers exactly once',
      iHeld && sent.length === 6 && lastText() === 'post me twice if you dare' && pend().delivered.has(31),
      { heldOnRefusal: iHeld, sentCount: sent.length, text: lastText() });

    // ── (j) PERSISTENT failure → bounded give-up (attempt cap 3) → honest notice ─
    // The reply itself is never delivered (logs keep failing), but at the cap the
    // driver posts the fixed GIVE-UP NOTICE (D111 part 2) — the mock Slack post path
    // is healthy (only logs fail), so the notice lands. That is the 7th (and last)
    // post: an honest "the agent finished but its reply couldn't be delivered".
    state.recentTicks.push({ tick: 7, actions: [{ action: 'spawn', execId: 32, queueId: QUEUE }] });
    state.status.set(32, { live: false, status: 'failed' });
    state.logs.set(32, [resultLine('never delivered')]);
    state.failLogs = 99;
    await leg().tick();
    await leg().tick();
    await leg().tick();
    const jGaveUp = !pend().watching.has(32) && pend().delivered.has(32) && sent.length === 7 && lastText() === GIVE_UP_NOTICE;
    await leg().tick(); // one more pass: must NOT resurrect, re-post, or retry
    record('j:persistent failure gives up at the attempt cap — retired undelivered, honest give-up notice posted (exact text), no unbounded retry',
      jGaveUp && !pend().watching.has(32) && sent.length === 7 && lastText() === GIVE_UP_NOTICE,
      { gaveUpAtCap: jGaveUp, sentCount: sent.length, watching: [...pend().watching.keys()], giveUpText: lastText() });
    state.failLogs = 0;

    // ── (k) CHAIN-THREAD capture (p7-multiturn): a wake re-dispatch mints a NEW
    // queue row, so its spawn action carries a DIFFERENT queueId — the driver must
    // capture it by the spawn action's `thread` matching the conversation's
    // resolved chainThread (exec-26, cached at leg e), and deliver its reply. ─────
    state.recentTicks.push({ tick: 8, actions: [{ action: 'spawn', execId: 33, queueId: 777, thread: 'exec-26' }] });
    state.status.set(33, { live: false, status: 'done' });
    state.logs.set(33, [resultLine('woken third turn reply')]);
    await leg().tick();
    record('k:wake re-dispatch (new queueId) captured via chain-thread match and delivered',
      sent.length === 8 && lastText() === 'woken third turn reply' && pend().delivered.has(33),
      { sentCount: sent.length, text: lastText() });

    // ── (l) COMPACTION turn skipped: compact:true spawns are the chain's
    // short-term memory, never an owner-facing reply — never watched, never posted. ─
    state.recentTicks.push({ tick: 9, actions: [{ action: 'spawn', execId: 34, queueId: 778, thread: 'exec-26', compact: true }] });
    state.status.set(34, { live: false, status: 'done' });
    state.logs.set(34, [resultLine('a summary that must never reach Slack')]);
    await leg().tick();
    await leg().tick();
    record('l:compact:true spawn never watched nor delivered',
      !pend().watching.has(34) && !pend().delivered.has(34) && sent.length === 8 && lastText() !== 'a summary that must never reach Slack',
      { sentCount: sent.length, watching: [...pend().watching.keys()], text: lastText() });

    // Final delivered-set sanity: 26, 27, 28, 29, 30, 31, 33 delivered exactly once
    // (seven real-reply posts), 32 retired undelivered but its give-up NOTICE posted;
    // 34 (compaction) untouched; nothing left watching.
    record('f:each exec delivered exactly once; give-up exec retired with an honest notice',
      pend().delivered.size === 8 && [26, 27, 28, 29, 30, 31, 32, 33].every((e) => pend().delivered.has(e))
      && pend().watching.size === 0 && sent.length === 8,
      { delivered: [...pend().delivered], watching: [...pend().watching.keys()], sentCount: sent.length });
  } catch (err) {
    cap.log({ error: err.message, stack: err.stack });
    checks.push({ name: 'no-exception', ok: false, error: err.message });
  } finally {
    try { bridgeH && bridgeH.bridge.stop(); } catch {}
    try { mock && mock.close(); } catch {}
  }

  const pass = checks.length > 0 && checks.every((c) => c.ok);
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-reply-leg', pass, EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0, checks });
  process.stdout.write(`PROBE probe-chat-reply-leg EXIT=${exit} WALL_MS=${wallMs} PASS=${pass}\n`);
  process.exit(exit);
}

main();
