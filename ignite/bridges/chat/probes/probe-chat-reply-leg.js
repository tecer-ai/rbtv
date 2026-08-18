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
//       (D111 part 2) is posted to the owner — no silent success, no unbounded retry;
//   (m) the ⏳ PENDING MARKER (owner-directed 2026-08-07 — the dead-air fix): the
//       owner's own message wears ⏳ from accept until its answer lands, in THAT
//       ORDER (the calls are recorded by the mock in arrival order), each forwarded
//       turn marks its OWN message, and no marker is ever left behind;
//   (n) THE REPLY CONTRACT'S three harness normalizations (owner ruling 2026-08-10):
//       the SAME fenced reply arrives from a claude stream-json log, a codex `--json`
//       event log, and a plain-text log carrying opencode's ANSI escapes — the
//       harness resolved from `inspect status`.profile, a field the driver already
//       fetches (no inspect surface widened);
//   (o) a CONFORMANT reply is delivered BYTE-IDENTICAL, with a body the mrkdwn
//       converter would demonstrably have altered — the "no parsing between the
//       agent and Slack" claim, made falsifiable;
//   (p) a LINT hit is non-conformance: nothing is posted, and a corrective `note`
//       lands on the SAME chain naming each ism and quoting its offending line;
//   (q) the REVIVE BOUND: a missing fence spends the second revive, the third
//       non-conformant turn is delivered best-effort (extracted text through
//       toMrkdwn behind the warning marker, never the bare fallback) and the budget
//       resets — while a genuinely TEXTLESS log still delivers the bare fallback and
//       is never revived;
//   (l) a COMPACTION spawn is WATCHED but never POSTED — its output is the chain's
//       short-term memory, and not a byte of it reaches Slack;
//   (r4) a late spawn AFTER the revive-no-spawn tombstone is reaped is re-armed
//       and delivered into the same thread (2026-08-18: 7.5 min relaunch) — the
//       dead-air notice stays; the real answer follows; nothing is silently dropped;
//   (s) the 2026-08-12 SILENT DEAD END replayed: the revive's corrective turn was
//       dispatched AS a compaction turn, the leg (which then skipped compact spawns)
//       watched nothing, the chain crashed inside it, and the conversation sat silent
//       for the full 10-minute window before disarming. Now: the compact spawn is
//       captured (s1), retired without delivery (s2), and a chain with no answering
//       turn behind it disarms on the SHORT corrective window with the dead-air notice
//       in the thread (s3) — while a pass that could not READ the ticker declares
//       nothing at all (s4), the gateway timeouts that framed the live incident;
//   (t) THE LATENCY LINE: one line per delivered reply carrying end-to-end seconds
//       (owner message armed → post landed), raised to WARN past the threshold.
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
//     (no notice posted; sent stays 6 and lastText ≠ GIVE_UP_NOTICE);
//   • drop the `clearPending(...)` call in chat-bridge.js deliverToOwner → (m1)
//     fails (the ⏳ never comes off);
//   • replace `queueReaction(...)` with a bare fire-and-forget call in
//     chat-bridge.js markPending/clearPending → the add/remove order is no longer
//     guaranteed and (m1) fails whenever the remove wins the race;
//   • drop the `profile` argument from the fetchReplyText call → n1/n2/n3 fail (every
//     harness reads as claude and only the stream-json arm extracts);
//   • run the conformant path through toMrkdwn → (o) fails (the `---` line vanishes);
//   • make `p.revives` per-exec instead of per-conversation → (q2) fails (a third
//     revive is spent and nothing is delivered);
//   • deliver FALLBACK_TEXT instead of the best-effort text at the bound → (q2) fails;
//   • restore the `|| a.compact` skip in the ticker capture loop → l/f/s1/s2/s3 fail;
//   • drop the `tickerOk` gate from the spawn-wait rung → (s4) fails (a blind pass
//     disarms a live conversation);
//   • pin `slow` to false in the delivery log → (t1) fails (a 40 s reply logs at info);
//   • put the corrective rung back on `windowMs` → s3/s4 fail (the short window is gone);
//   • drop the recoverable-stash / re-arm on late spawn → (r4) fails (reaped, then dropped).
// Run each mutation → probe FAILS → restore byte-exact → passes. All five above were RUN
// on 2026-08-12: each went red exactly as listed, and the restored control went green.
//
// ⚑ Timing uses Node `Date.now()` — `date +%s%3N` is broken on this box (D64).

const path = require('node:path');
const { startMockSlack, makeCapture, nowMs, sleep } = require('./lib');
const { resolveConfig } = require('../config');
const { createSlackSocketMode } = require('../slack-socket-mode');
const { buildBridge } = require('../index');
const { FALLBACK_TEXT, GIVE_UP_NOTICE, DEAD_AIR_NOTICE, STALL_NOTICE, RECOVERY_NOTICE, slowNoticeText, FENCE_OPEN, FENCE_CLOSE, UNFORMATTED_PREFIX } = require('../reply-leg');
const { toMrkdwn } = require('../mrkdwn');

const OUT = path.join(__dirname, 'probe-chat-reply-leg.out');

// A scripted forwarder standing in for the gateway surface. State is mutated
// between driver passes to script each leg deterministically.
//   recentTicks:  [{ tick, actions: [{ action:'spawn', execId, queueId }, …] }]
//   liveSessions: [{ exec_id, thread }]                (chain-thread resolution, leg e)
//   status:       Map<execId, { live, status, profile }>
//   logs:         Map<execId, string[]>                (the harness's own log lines)
//   logPageMax:   server-side page clamp stand-in (dispatch.js MAX_PAGE shape)
//   failLogs:     fail the next N `inspect logs` calls (transient transport error)
//   queueRows:    `inspect queue` rows — the daemon's PENDING queue. Since `on_seat_busy: 'queue'`
//                 an owner turn can WAIT here before it is ever launched, so the spawn-wait rung
//                 asks the queue before it declares a thread dead (leg u4)
//   forwarded:    every enqueue-job payload, in order — the corrective revive turns are
//                 OBSERVED here (legs p/q), never inferred from what did not reach Slack
function scriptedForwarder(state) {
  return {
    // The forward path's enqueue-job — returns the queue-row id (jobId) exactly
    // like the gateway result shape, so threadMap records the REAL enqueue result.
    forward: async (intent, payload) => {
      state.forwarded.push({ intent, payload });
      return { ok: true, result: { jobId: state.nextJobId } };
    },
    inspect: async (target, extra = {}) => {
      if (target === 'ticker') {
        return { ok: true, result: { target: 'ticker', recent_ticks: state.recentTicks, live_sessions: state.liveSessions } };
      }
      if (target === 'status') {
        const s = state.status.get(Number(extra.id));
        if (!s) return { ok: false, error: { code: 'NOT_FOUND', message: `no status for ${extra.id}` } };
        // `profile` is on the REAL status snapshot (jobs_log.profile → spawn.js#status →
        // dispatch.js) and is what selects the harness normalization — the reply leg reads it
        // from the response it already makes, so no inspect surface is widened. Defaulted here
        // to the claude profile because every pre-contract leg below scripts a stream-json log.
        return { ok: true, result: { target: 'status', id: Number(extra.id), live: s.live, status: s.status, profile: s.profile || 'claude/claude-opus-5' } };
      }
      if (target === 'queue') {
        if (state.failQueueInspect) return { ok: false, error: { code: 'TRANSPORT', message: 'scripted queue read failure' } };
        return { ok: true, result: { target: 'queue', rows: state.queueRows } };
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

// A CONFORMANT turn: the reply between the two sentinel lines (the bridge-owned reply contract,
// owner ruling 2026-08-10). Every pre-existing leg below wraps its answer in it, and each still
// asserts the delivered text equals the INNER string — which is the contract's own claim: the
// fence is the envelope, the content travels verbatim.
function fenced(text) {
  return `${FENCE_OPEN}\n${text}\n${FENCE_CLOSE}`;
}

function resultLine(text) {
  return JSON.stringify({ type: 'result', subtype: 'success', result: fenced(text), is_error: false });
}

// The same answer with NO fence — a turn that ignored the contract.
function bareResultLine(text) {
  return JSON.stringify({ type: 'result', subtype: 'success', result: text, is_error: false });
}

// codex `--json`: one event per line, the answer in `item.completed`/`agent_message`
// (measured on codex-cli 0.144.5, 2026-08-10).
function codexLog(text) {
  return [
    'Reading prompt from stdin...',                                    // real non-JSON noise
    JSON.stringify({ type: 'thread.started', thread_id: 'th-1' }),
    JSON.stringify({ type: 'turn.started' }),
    JSON.stringify({ type: 'item.completed', item: { id: 'item_0', type: 'agent_message', text: fenced(text) } }),
    JSON.stringify({ type: 'turn.completed', usage: { output_tokens: 7 } }),
  ];
}

// opencode/kimi: plain text, and opencode colours its banner even into a file (measured on a live
// log, 2026-08-10) — the escape sits on the same line as the opening sentinel here deliberately.
const ESC = String.fromCharCode(27);
function plainLog(text) {
  return [`${ESC}[0m`, '> build · glm-5.2', `${ESC}[0m${FENCE_OPEN}`, text, FENCE_CLOSE];
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

    const state = { recentTicks: [], liveSessions: [], status: new Map(), logs: new Map(), logPageMax: 500, failLogs: 0, nextJobId: 100, forwarded: [], queueRows: [], failQueueInspect: false };
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

    // ── (m1) THE ⏳ PENDING MARKER AND ITS ORDER (owner-directed 2026-08-07) ──────
    // The dead-air fix: the owner's own message wears ⏳ from the moment its turn is
    // accepted until its answer lands. The ORDER is the guard — two independent
    // fire-and-forget reactions could arrive reversed (owner-observed: the marker
    // landing after the answer), which is why the bridge serializes them and why this
    // asserts positions, not just presence.
    const rx = mock.reactionCalls;
    const marked = await waitFor(() => rx.length >= 2);
    record('m1:⏳ added to the owner message at accept and removed when its reply lands — in that order, never reversed',
      marked && rx.length === 2
      && rx[0].method === 'reactions.add' && rx[0].name === 'hourglass_flowing_sand' && rx[0].channel === CHANNEL && rx[0].ts === ROOT_TS
      && rx[1].method === 'reactions.remove' && rx[1].name === 'hourglass_flowing_sand' && rx[1].ts === ROOT_TS,
      { calls: rx.slice() });

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

    // ── (l) COMPACTION turn: WATCHED but never POSTED. A compact:true spawn is the chain's
    // short-term memory, never an owner-facing reply — so nothing of it reaches Slack. It IS
    // watched, though (changed 2026-08-12, see leg (s) for the incident that forced it): skipping
    // it made the leg blind to the one spawn standing between an owner turn and its answer. ─────
    state.recentTicks.push({ tick: 9, actions: [{ action: 'spawn', execId: 34, queueId: 778, thread: 'exec-26', compact: true }] });
    state.status.set(34, { live: false, status: 'done' });
    state.logs.set(34, [resultLine('a summary that must never reach Slack')]);
    await leg().tick();
    await leg().tick();
    record('l:compact:true spawn is watched, retired without delivery, and NOTHING of it is posted',
      !pend().watching.has(34) && pend().delivered.has(34) && pend().compacted === true
      && sent.length === 8 && lastText() !== 'a summary that must never reach Slack',
      { sentCount: sent.length, watching: [...pend().watching.keys()], compacted: pend().compacted, text: lastText() });

    // Final delivered-set sanity: 26, 27, 28, 29, 30, 31, 33 delivered exactly once
    // (seven real-reply posts), 32 retired undelivered but its give-up NOTICE posted;
    // 34 (compaction) retired WITHOUT a post; nothing left watching.
    record('f:each exec delivered exactly once; give-up exec retired with an honest notice',
      pend().delivered.size === 9 && [26, 27, 28, 29, 30, 31, 32, 33, 34].every((e) => pend().delivered.has(e))
      && pend().watching.size === 0 && sent.length === 8,
      { delivered: [...pend().delivered], watching: [...pend().watching.keys()], sentCount: sent.length });

    // ── (m2) the SECOND turn marks its OWN message, and NOTHING is left wearing ⏳ ─
    // Only the two forwarded turns mark (leg a's root message, leg e's follow-up);
    // every later delivery finds no marker and issues no call. Balanced add/remove
    // counts are the "no ⏳ left behind after the answer" guarantee.
    const marked2 = await waitFor(() => rx.length >= 4);
    const adds = rx.filter((c) => c.method === 'reactions.add');
    const removes = rx.filter((c) => c.method === 'reactions.remove');
    record('m2:the follow-up turn marks its OWN message; every ⏳ is removed by its own answer and none is left behind',
      marked2 && rx.length === 4
      && rx[2].method === 'reactions.add' && rx[2].ts === '1700000000.000200'
      && rx[3].method === 'reactions.remove' && rx[3].ts === '1700000000.000200'
      && adds.length === removes.length
      && adds.every((c) => c.name === 'hourglass_flowing_sand') && removes.every((c) => c.name === 'hourglass_flowing_sand'),
      { calls: rx.slice(), adds: adds.length, removes: removes.length });

    // ══ THE BRIDGE-OWNED REPLY CONTRACT (owner ruling 2026-08-10) ═══════════════════════════
    // Everything above already rides it — every `resultLine` is fenced and every assertion is
    // against the INNER text, which is the contract's claim. What follows tests the parts the
    // pre-contract legs cannot reach: the OTHER two harness log shapes, verbatim delivery, and
    // the feedback/revive loop.

    // ── (n) PER-HARNESS NORMALIZATION → the SAME fence, from three different log shapes ──────
    // The harness is resolved from `inspect status`.profile — the response the driver already
    // makes. Each arm scripts a REAL log shape: claude stream-json (every leg above), codex
    // `--json` events, and plain text with the ANSI escapes opencode writes into a file.
    state.status.set(40, { live: false, status: 'done', profile: 'codex/gpt-5.5' });
    state.logs.set(40, codexLog('codex answered *here*'));
    state.recentTicks.push({ tick: 10, actions: [{ action: 'spawn', execId: 40, queueId: QUEUE }] });
    await leg().tick();
    record('n1:codex --json log normalized (item.completed/agent_message) and the fenced reply delivered',
      sent.length === 9 && lastText() === 'codex answered *here*',
      { sentCount: sent.length, text: lastText() });

    state.status.set(41, { live: false, status: 'done', profile: 'opencode/zai-coding-plan/glm-5.2' });
    state.logs.set(41, plainLog('opencode answered *here*'));
    state.recentTicks.push({ tick: 11, actions: [{ action: 'spawn', execId: 41, queueId: QUEUE }] });
    await leg().tick();
    record('n2:plain-text opencode log (ANSI escapes on the sentinel line) normalized and the fenced reply delivered',
      sent.length === 10 && lastText() === 'opencode answered *here*',
      { sentCount: sent.length, text: lastText() });

    state.status.set(42, { live: false, status: 'done', profile: 'kimi/kimi-code/kimi-for-coding' });
    state.logs.set(42, [FENCE_OPEN, 'kimi answered *here*', FENCE_CLOSE]);
    state.recentTicks.push({ tick: 12, actions: [{ action: 'spawn', execId: 42, queueId: QUEUE }] });
    await leg().tick();
    record('n3:an unrecognized harness segment (kimi) resolves the plain-text arm',
      sent.length === 11 && lastText() === 'kimi answered *here*',
      { sentCount: sent.length, text: lastText() });

    // ── (o) A CONFORMANT REPLY IS DELIVERED VERBATIM — no mrkdwn pass ────────────────────────
    // The body is chosen so the converter WOULD change it and neither change is a lint hit: a
    // `---` rule (toMrkdwn drops the line) and a 3-blank-line run (toMrkdwn collapses it). If any
    // conversion pass survived on the conformant path, the delivered text could not be byte-equal.
    const VERBATIM = '*lead line*\n\n---\n\n\n_tail line_';
    state.status.set(43, { live: false, status: 'done', profile: 'claude/claude-opus-5' });
    state.logs.set(43, [resultLine(VERBATIM)]);
    state.recentTicks.push({ tick: 13, actions: [{ action: 'spawn', execId: 43, queueId: QUEUE }] });
    await leg().tick();
    record('o:conformant reply delivered BYTE-IDENTICAL — and provably not through toMrkdwn (which would have altered it)',
      sent.length === 12 && lastText() === VERBATIM && toMrkdwn(VERBATIM) !== VERBATIM,
      { sentCount: sent.length, equal: lastText() === VERBATIM, converterWouldDiffer: toMrkdwn(VERBATIM) !== VERBATIM, converted: toMrkdwn(VERBATIM) });

    // ── (p) A LINT HIT IS NON-CONFORMANCE → a corrective turn on the SAME chain ──────────────
    // Nothing reaches Slack; a send-message job carrying SPECIFIC feedback reaches the chain
    // instead — the offending line quoted, the ism named, the correct shape shown. The corrective
    // rides the forward path's own follow-up leg (`corrective: true`), so it is a `note` on the
    // conversation's chain thread and never an `answer`.
    const fwdBeforeP = state.forwarded.length;
    state.status.set(44, { live: false, status: 'done', profile: 'claude/claude-opus-5' });
    state.logs.set(44, [resultLine('# Heading\n**bold**')]);
    state.recentTicks.push({ tick: 14, actions: [{ action: 'spawn', execId: 44, queueId: QUEUE }] });
    await leg().tick();
    const corrective1 = state.forwarded.slice(fwdBeforeP);
    const corpus1 = corrective1.length ? String(corrective1[0].payload.args.corpus) : '';
    record('p:lint hit posts NOTHING to Slack and enqueues a corrective note naming BOTH isms with the offending lines quoted, plus the template',
      sent.length === 12
      && corrective1.length === 1 && corrective1[0].intent === 'enqueue-job'
      && corrective1[0].payload.args.type === 'note' && corrective1[0].payload.args.thread === 'exec-26'
      && corpus1.includes('a markdown heading (`#`) — Slack has no headings; use `*a short bold line*`')
      && corpus1.includes('markdown bold (`**text**`) — Slack bold is single asterisks, `*text*`')
      && corpus1.includes('    # Heading') && corpus1.includes('    **bold**')
      && corpus1.includes(FENCE_OPEN) && corpus1.includes(FENCE_CLOSE)
      && pend().revives === 1 && pend().delivered.has(44) && !pend().watching.has(44),
      { sentCount: sent.length, correctives: corrective1.length, revives: pend().revives, corpus: corpus1 });

    // ── (q) THE REVIVE BOUND (2) AND THE BEST-EFFORT FLOOR ───────────────────────────────────
    // The budget is spent on the CONVERSATION, not on the exec — so the revive turn's OWN bad
    // output spends the same allowance and the loop terminates. One revive is already spent (p);
    // this leg spends the second, and the THIRD non-conformant turn is delivered best-effort
    // rather than revived a third time.
    const fwdBeforeQ = state.forwarded.length;
    state.status.set(45, { live: false, status: 'done', profile: 'claude/claude-opus-5' });
    state.logs.set(45, [bareResultLine('no fence at all here')]);
    state.recentTicks.push({ tick: 15, actions: [{ action: 'spawn', execId: 45, queueId: QUEUE }] });
    await leg().tick();
    const corpus2 = state.forwarded.length > fwdBeforeQ ? String(state.forwarded[fwdBeforeQ].payload.args.corpus) : '';
    record('q1:a MISSING fence is non-conformance too — second revive spent, still nothing posted, feedback names the missing pair',
      sent.length === 12 && state.forwarded.length === fwdBeforeQ + 1 && pend().revives === 2
      && corpus2.includes(`no ${FENCE_OPEN} … ${FENCE_CLOSE} pair`),
      { sentCount: sent.length, revives: pend().revives, corpus: corpus2 });

    const fwdBeforeQ3 = state.forwarded.length;
    const BEST = 'still no fence, and **markdown** to boot';
    state.status.set(46, { live: false, status: 'done', profile: 'claude/claude-opus-5' });
    state.logs.set(46, [bareResultLine(BEST)]);
    state.recentTicks.push({ tick: 16, actions: [{ action: 'spawn', execId: 46, queueId: QUEUE }] });
    await leg().tick();
    record('q2:at the bound the reply is DELIVERED best-effort — the extracted text through toMrkdwn behind the warning marker, never the bare fallback; NO third revive; the budget resets',
      sent.length === 13
      && lastText() === `${UNFORMATTED_PREFIX}${toMrkdwn(BEST)}`
      && lastText() !== FALLBACK_TEXT && lastText().includes('*markdown*')
      && state.forwarded.length === fwdBeforeQ3
      && pend().revives === 0 && pend().delivered.has(46),
      { sentCount: sent.length, text: lastText(), extraForwards: state.forwarded.length - fwdBeforeQ3, revives: pend().revives });

    // ── (q3) THE BARE FALLBACK SURVIVES, for a log with NO text at all ───────────────────────
    // Best-effort never swallows the honest empty case: a textless log still delivers the fixed
    // fallback, and is never revived (there is nothing to correct).
    const fwdBeforeQ4 = state.forwarded.length;
    state.status.set(47, { live: false, status: 'done', profile: 'claude/claude-opus-5' });
    state.logs.set(47, [JSON.stringify({ type: 'system', subtype: 'init' })]);
    state.recentTicks.push({ tick: 17, actions: [{ action: 'spawn', execId: 47, queueId: QUEUE }] });
    await leg().tick();
    record('q3:a textless log still delivers the BARE fallback and is never revived',
      sent.length === 14 && lastText() === FALLBACK_TEXT && state.forwarded.length === fwdBeforeQ4,
      { sentCount: sent.length, text: lastText(), extraForwards: state.forwarded.length - fwdBeforeQ4 });

    // ── (r) A REVIVE WHOSE SPAWN NEVER COMES ENDS IN THE DEAD-AIR NOTICE, NOT SILENCE ─────────
    // Measured live 2026-08-10 (kimi execvp failure): the revive retired its exec into
    // `delivered`, the corrective spawn never materialized, and the conversation pended forever —
    // the never-delivered disarm rung can no longer match once `delivered` is non-empty. This leg
    // replays it: a non-conformant turn spends a revive (q2 reset the budget), then the spawn-wait
    // window blows with nothing spawned. The conversation must DISARM and the owner must be told.
    state.status.set(48, { live: false, status: 'done', profile: 'claude/claude-opus-5' });
    state.logs.set(48, [bareResultLine('one more fenceless answer')]);
    state.recentTicks.push({ tick: 18, actions: [{ action: 'spawn', execId: 48, queueId: QUEUE }] });
    await leg().tick();
    const revivedR = pend() && pend().revives === 1 && pend().watching.size === 0;
    pend().armedAt = nowMs() - (10 * 60 * 1000) - 1; // backdate past the default spawn-wait window
    await leg().tick();
    const sentAfterR = sent.length;
    record('r:a spent revive with no spawn inside the window posts the dead-air notice',
      revivedR && lastText() === DEAD_AIR_NOTICE,
      { revivedR, text: lastText() });
    // …AND KEEPS THE ENTRY AS A TOMBSTONE (2026-08-12 root cause, defect 4). The disarm used to
    // delete it outright, which is why the notice could be a LIE: the corrective spawn had in fact
    // run and answered — the daemon was mid-restart and the ticker showed it late — and with the
    // entry gone that answer had nowhere to land. The entry now survives ONE corrective window so a
    // late spawn is still captured and delivered, the notice is posted exactly ONCE while it does,
    // and the entry is reaped when the grace is spent with nothing watched. `revive-no-spawn` only:
    // a chain that died inside a compaction turn is dead, not late, and still deletes on the spot.
    const tombstoned = Boolean(pend()) && typeof pend().disarmedAt === 'number';
    await leg().tick();
    record('r2:the tombstone is kept for a late spawn, and the notice is NOT posted twice',
      tombstoned && Boolean(pend()) && sent.length === sentAfterR,
      { tombstoned, stillPending: Boolean(pend()), sentAfterR, sentNow: sent.length });
    pend().disarmedAt = nowMs() - (10 * 60 * 1000); // spend the grace with nothing watched
    await leg().tick();
    record('r3:a tombstone whose grace expires with nothing watched is reaped — never a leak',
      !pend() && sent.length === sentAfterR,
      { stillPending: Boolean(pend()), sentNow: sent.length });
    // ── (r4) A LATE SPAWN AFTER THAT REAP IS RE-ARMED AND DELIVERED, NOT DROPPED ──────────────
    // Measured 2026-08-18: an API connection drop delayed the corrective relaunch 7.5 minutes
    // — past the tombstone grace — so the entry was reaped and the answer had nowhere to land.
    // Dead-air stays posted; the real answer follows into the same thread.
    state.recentTicks = [{ tick: 99, actions: [{ action: 'spawn', execId: 49, queueId: 458, thread: 'exec-26' }] }];
    state.status.set(49, { live: false, status: 'done', profile: 'claude/claude-opus-5' });
    state.logs.set(49, [resultLine('the late corrective answer')]);
    await leg().tick();
    record('r4:a late spawn after a revive-no-spawn reap is re-armed and delivered into the same thread',
      Boolean(pend()) && pend().disarmedAt === null && pend().delivered.has(49)
      && sent.length === sentAfterR + 1 && lastText() === 'the late corrective answer'
      && postedTo(sent[sent.length - 1]),
      { stillPending: Boolean(pend()), sentAfterR, sentNow: sent.length, text: lastText(),
        chainThread: bridgeH.threadMap.get(CHAT) && bridgeH.threadMap.get(CHAT).chainThread });
    // ── (s) A COMPACTION TURN IS WATCHED, NOT IGNORED — AND A CHAIN THAT DIES INSIDE ONE ────────
    // Measured live 2026-08-12 (thread D0BJ50Y1DC6:1786501607, sessions 88136051→178e7b3d): the
    // revive's corrective send-message DID dispatch (queue 458, tick 235206) and the daemon woke
    // the chain three seconds later — but as a COMPACTION turn (tick 235208, exec 26449,
    // `compact:true`, the transcript having crossed history_compact_chars). The leg skipped every
    // compact spawn, so it watched nothing; exec 26449 then crashed (exit 1) and halted the chain,
    // and TEN MINUTES later the conversation disarmed on "corrective spawn never appeared". The
    // owner had silence for the whole window. This leg replays that exact shape.
    // The fixture's tick log is RESET first: a fresh arm carries an empty `delivered` set, so every
    // historical spawn still in `recentTicks` would be captured and delivered all over again —
    // an artefact of the stand-in, not of the driver.
    state.recentTicks = [];
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'a turn whose chain compacts', channel: CHANNEL, thread_ts: ROOT_TS, ts: '1700000000.000900', event_ts: '1700000000.000900', client_msg_id: 'reply-leg-m9' });
    const armedS = await waitFor(() => Boolean(pend()));
    const sentBeforeS = sent.length;
    state.recentTicks.push({ tick: 19, actions: [{ action: 'spawn', execId: 50, queueId: QUEUE, compact: true }] });
    state.status.set(50, { live: true, status: 'running', profile: 'claude/claude-opus-5' });
    await leg().tick();
    record('s1:a compact:true spawn on the conversation is CAPTURED and flagged (it used to be skipped entirely)',
      armedS && Boolean(pend()) && pend().watching.has(50) && pend().watching.get(50).compact === true,
      { armedS, watching: pend() ? [...pend().watching.keys()] : null, compact: pend() && pend().watching.get(50) && pend().watching.get(50).compact });

    // Its output is the chain's MEMORY, never a reply — so even a perfectly conformant fenced body
    // in a compaction log must not reach Slack.
    state.status.set(50, { live: false, status: 'failed', profile: 'claude/claude-opus-5' });
    state.logs.set(50, [resultLine('a compaction summary that must never reach the owner')]);
    await leg().tick();
    record('s2:the compaction turn is retired WITHOUT delivering — even a conformant fenced body stays out of Slack',
      sent.length === sentBeforeS && Boolean(pend()) && pend().watching.size === 0 && pend().delivered.has(50) && pend().compacted === true,
      { sentCount: sent.length, sentBeforeS, lastText: lastText(), watching: pend() ? [...pend().watching.keys()] : null, compacted: pend() && pend().compacted });

    // The chain died inside the compaction (the live crash) — no answering turn ever spawns. The
    // wait that now applies is the SHORT one, and the owner is told.
    pend().armedAt = nowMs() - (120 * 1000) - 1; // past correctiveWindowMs, far inside the 10-min windowMs
    await leg().tick();
    record('s3:a compaction with no answering turn disarms on the SHORT window and posts the dead-air notice',
      !pend() && sent.length === sentBeforeS + 1 && lastText() === DEAD_AIR_NOTICE,
      { stillPending: Boolean(pend()), sentCount: sent.length, text: lastText() });

    // ── (s4) A BLIND DRIVER NEVER DECLARES A SPAWN MISSING ───────────────────────────────────────
    // Three `inspect ticker` timeouts framed the live incident. "No spawn appeared" is a claim
    // about what the ticker showed; a pass that could not read it has seen nothing to claim.
    state.recentTicks = [];   // same stand-in artefact as above: a fresh arm re-captures old spawns
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'a turn during a gateway blackout', channel: CHANNEL, thread_ts: ROOT_TS, ts: '1700000000.001000', event_ts: '1700000000.001000', client_msg_id: 'reply-leg-m10' });
    await waitFor(() => Boolean(pend()));
    const sentBeforeS4 = sent.length;
    pend().armedAt = nowMs() - (11 * 60 * 1000); // past EVERY window
    const realInspect = forwarder.inspect;
    forwarder.inspect = async (target, extra) => (target === 'ticker'
      ? { ok: false, error: { code: 'TRANSPORT', message: 'gateway did not respond within 10000ms' } }
      : realInspect(target, extra));
    await leg().tick();
    const heldBlind = Boolean(pend()) && sent.length === sentBeforeS4;
    forwarder.inspect = realInspect;
    await leg().tick();
    record('s4:a pass that could not read the ticker does NOT disarm; the next pass that can, does',
      heldBlind && !pend() && sent.length === sentBeforeS4 + 1 && lastText() === DEAD_AIR_NOTICE,
      { heldBlind, stillPending: Boolean(pend()), sentCount: sent.length, sentBeforeS4, text: lastText() });

    // ── (t) THE LATENCY LINE — one per delivered reply, end to end ───────────────────────────────
    // Owner-facing latency is the owner's message being armed → the post landing; everything the
    // bridge does in between (dispatch, run, revives, compaction, retries) is inside it. Over the
    // threshold the same line is raised to a WARNING.
    const bridgeLines = () => cap.lines.filter((e) => e.bridge && /delivered worker reply to owner/.test(e.bridge.message));
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'a slow one', channel: CHANNEL, thread_ts: ROOT_TS, ts: '1700000000.001100', event_ts: '1700000000.001100', client_msg_id: 'reply-leg-m11' });
    await waitFor(() => Boolean(pend()));
    pend().turnStartedAt = nowMs() - 40000; // 40 s end-to-end, past the 30 s default threshold
    state.recentTicks.push({ tick: 20, actions: [{ action: 'spawn', execId: 51, queueId: QUEUE }] });
    state.status.set(51, { live: false, status: 'failed', profile: 'claude/claude-opus-5' });
    state.logs.set(51, [resultLine('the slow answer')]);
    await leg().tick();
    const slowLine = bridgeLines().pop();
    record('t1:a delivery past the threshold logs ONE line at WARN carrying the end-to-end seconds',
      Boolean(slowLine) && slowLine.bridge.level === 'warn' && /SLOW/.test(slowLine.bridge.message)
      && slowLine.bridge.latencyS >= 39 && slowLine.bridge.latencyS < 60 && slowLine.bridge.thresholdS === 30
      && lastText() === 'the slow answer',
      { line: slowLine && slowLine.bridge, text: lastText() });

    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'a fast one', channel: CHANNEL, thread_ts: ROOT_TS, ts: '1700000000.001200', event_ts: '1700000000.001200', client_msg_id: 'reply-leg-m12' });
    await waitFor(() => Boolean(pend()));
    state.recentTicks.push({ tick: 21, actions: [{ action: 'spawn', execId: 52, queueId: QUEUE }] });
    state.status.set(52, { live: false, status: 'failed', profile: 'claude/claude-opus-5' });
    state.logs.set(52, [resultLine('the fast answer')]);
    await leg().tick();
    const fastLine = bridgeLines().pop();
    record('t2:a delivery inside the threshold logs the SAME line at info, seconds still on it',
      Boolean(fastLine) && fastLine !== slowLine && fastLine.bridge.level === 'info'
      && !/SLOW/.test(fastLine.bridge.message) && typeof fastLine.bridge.latencyS === 'number'
      && fastLine.bridge.latencyS < 30 && lastText() === 'the fast answer',
      { line: fastLine && fastLine.bridge, text: lastText() });

    // ══ (u) THE THREE VISIBILITY NOTICES + THE QUEUE-AWARE DISARM (P2/P3) ═══════════════════════
    // Every silence the owner sees is indistinguishable from a broken bridge. The leg's own poll
    // already knows the difference between "stalled", "killed after stalling", "just slow" and
    // "still waiting its turn in the daemon queue" — these legs assert it now SAYS so, exactly
    // once each, and that a killed hang's partial log is never delivered as an answer.
    state.recentTicks = [];
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'a turn that goes silent', channel: CHANNEL, thread_ts: ROOT_TS, ts: '1700000000.001300', event_ts: '1700000000.001300', client_msg_id: 'reply-leg-m13' });
    await waitFor(() => Boolean(pend()));
    const sentBeforeU1 = sent.length;
    state.recentTicks.push({ tick: 22, actions: [{ action: 'spawn', execId: 60, queueId: QUEUE }] });
    state.status.set(60, { live: true, status: 'stalled', profile: 'claude/claude-opus-5' });
    await leg().tick();
    const afterFirstStall = sent.length;
    await leg().tick();   // STILL stalled — the notice is one-shot, not one-per-pass
    record('u1:a stalled-but-live exec posts the stall notice EXACTLY ONCE, however many passes see it',
      afterFirstStall === sentBeforeU1 + 1 && sent[sentBeforeU1].text === STALL_NOTICE
      && sent.length === sentBeforeU1 + 1
      && Boolean(pend()) && pend().watching.get(60) && pend().watching.get(60).stallNoticed === true,
      { sentBeforeU1, afterFirstStall, sentNow: sent.length, text: sent[sentBeforeU1] && sent[sentBeforeU1].text,
        flagged: pend() && pend().watching.get(60) && pend().watching.get(60).stallNoticed });

    // ── (u2) THE HANG WAS KILLED: one recovery notice, and NOT A BYTE of its partial log ────────
    // The daemon kills a hung agent at ~10 min of silence and the turn's status becomes `killed`.
    // Its log is a half-written hang; running it through the reply extractor would deliver that
    // fragment as "the reply", which is worse than saying nothing.
    const sentBeforeU2 = sent.length;
    const armedAtBeforeU2 = pend().armedAt;
    state.status.set(60, { live: false, status: 'killed', profile: 'claude/claude-opus-5' });
    state.logs.set(60, [resultLine('a half-written hang that must never be delivered')]);
    await leg().tick();
    await leg().tick();   // one-shot here too: the exec is retired, nothing re-posts
    record('u2:a killed hang posts ONE recovery notice, delivers NO log-derived text, and resets the spawn window instead of tombstoning',
      sent.length === sentBeforeU2 + 1 && lastText() === RECOVERY_NOTICE
      && !sent.some((m) => /half-written hang/.test(String(m.text)))
      && Boolean(pend()) && pend().delivered.has(60) && !pend().watching.has(60)
      && pend().armedAt >= armedAtBeforeU2 && pend().disarmedAt === null,
      { sentCount: sent.length, sentBeforeU2, text: lastText(),
        leakedLog: sent.filter((m) => /half-written hang/.test(String(m.text))).length,
        retired: Boolean(pend()) && pend().delivered.has(60), rearmed: Boolean(pend()) && pend().armedAt >= armedAtBeforeU2 });

    // ── (u3) A LONG TURN SAYS SO, ONCE ──────────────────────────────────────────────────────────
    // Not an error and not a promise — just the fact that would otherwise be silence. One post per
    // OWNER turn (the flag resets in arm(), beside the other per-turn resets).
    const sentBeforeU3 = sent.length;
    pend().turnStartedAt = nowMs() - (6 * 60 * 1000); // past the 300 s default
    await leg().tick();
    await leg().tick();
    record('u3:a turn past the slow threshold posts ONE hourglass notice carrying the minutes so far',
      sent.length === sentBeforeU3 + 1 && lastText() === slowNoticeText(6)
      && Boolean(pend()) && pend().slowNoticed === true,
      { sentCount: sent.length, sentBeforeU3, text: lastText(), expected: slowNoticeText(6), flagged: pend() && pend().slowNoticed });
    const slowAtU3 = pend().slowNoticed;
    leg().arm(`${CHANNEL}:other-sitting`);
    record('u3b:slowNoticed resets only on a real new sitting of THIS conversation — arming another sitting leaves it set',
      slowAtU3 === true && pend().slowNoticed === true
      && Boolean(leg()._pending.get(`${CHANNEL}:other-sitting`))
      && leg()._pending.get(`${CHANNEL}:other-sitting`).slowNoticed === false,
      { slowAtU3, stillSet: pend() && pend().slowNoticed,
        other: leg()._pending.get(`${CHANNEL}:other-sitting`) && leg()._pending.get(`${CHANNEL}:other-sitting`).slowNoticed });

    // ── (u4) A TURN STILL IN THE DAEMON QUEUE IS NOT DEAD AIR ────────────────────────────────────
    // The P2 half of the reply leg. Under `on_seat_busy: 'queue'` an owner message that lands at a
    // busy seat WAITS in the daemon's queue — no spawn appears, and behind a 20-minute turn that is
    // well past the spawn-wait window. Declaring dead air there tells the owner nothing is coming
    // minutes before his answer arrives. The queue is the authority; the conversation is identified
    // by the `chat-thread: <id>` line the forward path puts at the head of every create prompt.
    state.recentTicks = [];
    const U4_TS = '1700000000.001600';
    const CHAT_U4 = `${CHANNEL}:${U4_TS}`;
    await mock.pushMessage({ type: 'message', user: 'U-owner', text: 'a message that waits its turn', channel: CHANNEL, ts: U4_TS, event_ts: U4_TS, client_msg_id: 'reply-leg-m14' });
    const pu4 = () => leg()._pending.get(CHAT_U4);
    await waitFor(() => Boolean(pu4()));
    const sentBeforeU4 = sent.length;
    state.queueRows = [{ queue_id: 9001, job_id: 'chat-launch', args: JSON.stringify({ prompt: `chat-thread: ${CHAT_U4}\n\na message that waits its turn`, workdir: '/seat' }) }];
    pu4().armedAt = nowMs() - (11 * 60 * 1000); // past EVERY window
    await leg().tick();
    const heldWhileQueued = Boolean(pu4()) && sent.length === sentBeforeU4;
    state.queueRows = [];   // the daemon launched it — the row is gone, and no spawn ever came
    await leg().tick();
    record('u4:a conversation whose row is STILL in the daemon queue does not disarm; once the row is gone the dead-air notice fires as before',
      heldWhileQueued && !pu4() && sent.length === sentBeforeU4 + 1 && lastText() === DEAD_AIR_NOTICE,
      { heldWhileQueued, stillPending: Boolean(pu4()), sentBeforeU4, sentNow: sent.length, text: lastText() });

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
