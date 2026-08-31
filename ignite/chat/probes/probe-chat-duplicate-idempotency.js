'use strict';

// ── THE PER-INBOUND-MESSAGE IDEMPOTENCY KEY (duplicate owner-facing replies fix,
// redesign-continue-1 `dup-idempotency`, criteria 3/4/5) ─────────────────────────────────────────
//
// `slack-duplicate-replies.md` §3 defect 2: `chat/live-sessions.js:84-87` turns ANY non-ok gateway
// result into `answered:false`, which used to be treated identically to "never delivered" — so a
// cold fallback could re-answer a message the warm leg already answered, in DIFFERENT WORDING
// (two independently-generated answers to one question are never byte-equal, which is why the
// existing byte-equality guard at `preEnqueueRefusal` — gated behind `!threadMap.has()`, so it
// never even runs on a MAPPED conversation — cannot catch this).
//
// This probe drives `chat-bridge.js#deliverToOwner` — the ONE choke point every
// conversation-addressed post passes through — through the REAL bridge, never a hand-rolled copy
// of the guard:
//   (a) a warm turn answers, and a SECOND, differently-worded delivery attempt carrying the SAME
//       `inboundMsgId` is REFUSED — the duplicate this whole fix exists to remove;
//   (b) a DIFFERENT owner message that was NEVER answered still gets its cold answer delivered —
//       the discriminating case: a guard that also blocked this would trade the duplicate for
//       silence, which is worse;
//   (c) a P3 SYSTEM NOTICE (slow/give-up/dead-air shape: `answersOwnerAsk` left at its default
//       `false`, no `inboundMsgId`) never marks the key and never blocks the real answer that
//       follows — the gate `deliverToOwner` applies (`answersOwnerAsk`, the SAME signal
//       `askRecord.reapAsk` already trusts) — and its absence would silence a real answer behind
//       an innocuous "still working" ping.
//
// Scenarios (a)/(c)'s "cold duplicate" calls drive `deliverToOwner` DIRECTLY with the
// `inboundMsgId` `reply-leg.js#arm`/`deliver()` supply for real (proving the MECHANISM at the
// choke point, independent of how the text was derived). Scenario (d) drives the COLD LEG'S OWN
// wiring end to end — a real `arm()` → ticker capture → status → logs → `deliver()` pass via
// `replyLeg.tick()` — to prove `reply-leg.js` itself, not a stand-in for it, populates the guard.
//
// MUTATION EVIDENCE — verified 2026-08-31 against a clean pre-fix worktree (`git worktree add
// <tmp> HEAD`): with the guard absent, scenario (a)'s second delivery is NOT refused — both texts
// post, reproducing the duplicate. Restored (this file, against the fixed tree), (a) passes.
// Scenario (d)'s cold-leg wiring re-verified the same way the same day: reverting ONLY
// `reply-leg.js`'s `inboundMsgId` threading (the `arm()` header + the `deliver()` call argument +
// the post-delivery clear) reproduces exactly d2's duplicate — a direct call carrying the same id
// the cold leg just answered with is NOT refused, because the cold leg's own `deliver()` never
// told `deliverToOwner` what it was answering. Restored, d2 passes. See the seat's closing report
// for the exact commands and quoted output.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { makeCapture, nowMs, sleep } = require('./lib');
const { buildBridge } = require('../index');
const { FENCE_OPEN, FENCE_CLOSE } = require('../reply-leg');

const OUT = path.join(__dirname, 'probe-chat-duplicate-idempotency.out');

const USER = 'U_OWNER';
const DM = 'D_OWNER';

function makeFakeSlack() {
  const posted = [];
  return {
    posted,
    async sendToOwner({ channel, threadTs, text }) { posted.push({ channel, threadTs, text }); return { delivered: true, ts: '1.0' }; },
    async react() { return { ok: true }; },
    async unreact() { return { ok: true }; },
    async start() { return { connected: true }; },
    stop() {},
  };
}

// `liveReply` is what the warm session answers with; `null` means the feed refuses
// (`fed: false`) — the fall-through-to-cold case (same knob as probe-chat-warm-post.js).
function makeFakeForwarder({ liveReply = null } = {}) {
  const forwards = [];
  let nextId = 100;
  return {
    forwards,
    async forward(intent, payload) {
      forwards.push({ intent, payload });
      if (intent === 'live-feed') {
        return liveReply === null
          ? { ok: true, result: { fed: false, reason: 'no-warm-session' } }
          : { ok: true, result: { fed: true, reply: liveReply, is_error: false, session_id: 'sess-warm', ms: 1200, warm: 1 } };
      }
      return { ok: true, result: { jobId: nextId++ } };
    },
    async inspect() { return { ok: true, result: { live_sessions: [], recent_ticks: [] } }; },
  };
}

function makeBridge({ liveReply = null } = {}) {
  const slack = makeFakeSlack();
  const forwarder = makeFakeForwarder({ liveReply });
  const config = {
    gatewayAddr: '127.0.0.1:0',
    bridgeToken: 'stub',
    sessionJobId: 'chat-launch',
    sendMessageJobId: 'send-message',
    workdir: '/configured/master/workdir',
    workspaceRoot: fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-dup-idem-')),
    allowlist: [USER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  };
  const built = buildBridge(config, {
    logger: () => {},
    makeTransport: () => slack,
    forwarderImpl: forwarder,
    replyLegOptions: { pollMs: 3600000 }, // the leg must never tick under us — this probe drives deliverToOwner directly
  });
  return { ...built, slack, forwarder };
}

// A scripted forwarder that ALSO answers the ticker/status/logs surface reply-leg's `tick()`
// drives, so scenario (d) can run a REAL cold delivery end to end (never `warmedBridge`'s bare
// `bindSessionExecId` shortcut, which the other scenarios use precisely because they never touch
// the cold leg's own watch loop). Minimal, self-contained subset of `probe-chat-reply-leg.js`'s
// own `scriptedForwarder` — only the shapes reply-leg's `_runOnce` actually reads.
function makeTickingForwarder() {
  const state = { forwarded: [], recentTicks: [], status: new Map(), logs: new Map(), nextJobId: 200 };
  const forwarder = {
    state,
    async forward(intent, payload) {
      state.forwarded.push({ intent, payload });
      if (intent === 'live-feed') return { ok: true, result: { fed: false, reason: 'no-warm-session' } };
      const jobId = state.nextJobId++;
      state.lastJobId = jobId;
      return { ok: true, result: { jobId } };
    },
    async inspect(target, extra = {}) {
      if (target === 'ticker') return { ok: true, result: { recent_ticks: state.recentTicks, live_sessions: [] } };
      if (target === 'status') {
        const s = state.status.get(Number(extra.id));
        if (!s) return { ok: false, error: { code: 'NOT_FOUND' } };
        return { ok: true, result: { live: s.live, status: s.status, profile: s.profile || 'claude/claude-opus-5' } };
      }
      if (target === 'logs') {
        const lines = state.logs.get(Number(extra.id)) || [];
        const offset = Number.isInteger(extra.offset) ? extra.offset : 0;
        const page = lines.slice(offset);
        return { ok: true, result: { lines: page, nextOffset: lines.length, eof: true } };
      }
      if (target === 'queue') return { ok: true, result: { rows: [] } };
      return { ok: false, error: { code: 'UNKNOWN_TARGET', message: target } };
    },
  };
  return forwarder;
}

// `fenced()` is defined once, below (shared with the warm-reply scenarios) — reused here
// unchanged: extraction only cares about the sentinel pair, not what precedes them.
function resultLine(body) {
  return JSON.stringify({ type: 'result', subtype: 'success', result: fenced(body), is_error: false });
}

function makeTickingBridge() {
  const slack = makeFakeSlack();
  const forwarder = makeTickingForwarder();
  const config = {
    gatewayAddr: '127.0.0.1:0',
    bridgeToken: 'stub',
    sessionJobId: 'chat-launch',
    sendMessageJobId: 'send-message',
    workdir: '/configured/master/workdir',
    workspaceRoot: fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-dup-idem-cold-')),
    allowlist: [USER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  };
  const built = buildBridge(config, {
    logger: () => {},
    makeTransport: () => slack,
    forwarderImpl: forwarder,
    replyLegOptions: { pollMs: 3600000 }, // manual tick() only
  });
  return { ...built, slack, forwarder };
}

// Deliver ONE cold turn end to end: a REAL `onChatMessage` call (so `arm()` gets the REAL
// `inboundMsgId` off the message it minted) mints the enqueue; its exec is then scripted onto
// the ticker with terminal status + a conformant fenced log, and `replyLeg.tick()` drives the
// capture→status→logs→deliver pass in one call (the ticker mutation happens before `tick()`
// reads it, so one pass both captures and delivers — see `reply-leg.js#_runOnce`'s own ordering).
async function deliverOneColdTurn(b, { rootTs, msgTs, answerText, chatMsgText, execId, chainThread = `exec-${execId}` }) {
  const outcome = await b.bridge.onChatMessage(msg(msgTs, chatMsgText, rootTs));
  const jobId = b.forwarder.state.lastJobId; // this call's own enqueue-job — the ONLY forward call it made (warm never attempts on an unmapped thread)
  b.forwarder.state.recentTicks.push({ tick: execId, actions: [{ action: 'spawn', execId, queueId: jobId, thread: chainThread }] });
  b.forwarder.state.status.set(execId, { live: false, status: 'done' });
  b.forwarder.state.logs.set(execId, [resultLine(answerText)]);
  await b.bridge.replyLeg.tick();
  await sleep(20);
  return { outcome, jobId };
}

function msg(msgTs, text, rootTs = '1.1') {
  return {
    chatUserId: USER,
    chatThreadId: `${DM}:${rootTs}`,
    text,
    _channel: DM,
    _threadTs: rootTs,
    _msgTs: msgTs,
    _channelType: 'im',
    _inThread: msgTs !== rootTs,
  };
}

// Mint a warm-eligible conversation: message #1 is cold (mints the chain), then the reply
// leg's exec-id bind is done by hand (the same shortcut probe-chat-warm-post.js takes) so
// message #2 onward can go warm.
async function warmedBridge({ liveReply }) {
  const b = makeBridge({ liveReply });
  await b.bridge.start();
  await b.bridge.onChatMessage(msg('1.1', 'first message'));
  b.threadMap.bindSessionExecId(`${DM}:1.1`, 5001);
  return b;
}

function fenced(body) {
  return ['Some prose the agent thinks out loud.', '', FENCE_OPEN, body, FENCE_CLOSE].join('\n');
}

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const checks = [];
  const check = (name, pass, detail = {}) => { checks.push({ name, pass, ...detail }); cap.log({ check: name, pass, ...detail }); };

  try {
    // ── (a) WARM ANSWERS, THEN A DIFFERENTLY-WORDED "COLD" DUPLICATE IS REFUSED ────────────────
    {
      const TEXT_A = 'Warm answer: the seat runs on the daemon lane.';
      const TEXT_B = 'Cold answer: per the goal decisions log, the seat is on the daemon lane already.';
      const b = await warmedBridge({ liveReply: fenced(TEXT_A) });
      const conv = `${DM}:1.1`;
      const warm = await b.bridge.onChatMessage(msg('2.1', 'is the seat running?'));
      await sleep(20);
      check('(a) premise: the owner message was answered on the WARM path',
        warm.forwarded === true && warm.leg === 'live-session' && warm.warm === true, { warm });
      check('(a) premise: the warm text posted verbatim (the fenced body)',
        b.slack.posted.length === 1 && b.slack.posted[0].text === TEXT_A, { posted: b.slack.posted.map((p) => p.text) });

      // Simulates the cold leg's OWN delivery for the SAME arm cycle — the `inboundMsgId` a fixed
      // `reply-leg.js#arm`/`deliver()` would carry through for message '2.1' (see file header for
      // why that wiring is not landed in this change). This IS `deliverToOwner`, not a stand-in.
      const dup = await b.bridge.deliverToOwner({ chatThreadId: conv, text: TEXT_B, answersOwnerAsk: true, inboundMsgId: '2.1' });
      check('(a) the second, differently-worded delivery for the SAME owner message is REFUSED',
        dup && dup.delivered === false && dup.reason === 'already-answered-inbound', { dup });
      check('(a) TEXT_A and TEXT_B are NOT byte-identical (a text-equality guard could not have caught this)',
        TEXT_A !== TEXT_B, { TEXT_A, TEXT_B });
      check('(a) exactly ONE post reached Slack — the duplicate never landed',
        b.slack.posted.length === 1, { posted: b.slack.posted.map((p) => p.text) });
      b.bridge.stop();
    }

    // ── (b) DISCRIMINATOR: a message that was NEVER answered still gets its cold answer ────────
    {
      const b = await warmedBridge({ liveReply: null }); // warm refuses every feed
      const conv = `${DM}:1.1`;
      const cold = await b.bridge.onChatMessage(msg('4.1', 'a question the warm leg could not take'));
      check('(b) premise: the warm leg refused and the message fell through to the cold path',
        cold.forwarded === true && cold.leg !== 'live-session', { cold });
      check('(b) premise: NOTHING has posted yet for this message',
        b.slack.posted.length === 0, { posted: b.slack.posted });
      const delivered = await b.bridge.deliverToOwner({ chatThreadId: conv, text: 'Cold-derived answer for 4.1', answersOwnerAsk: true, inboundMsgId: '4.1' });
      check('(b) the cold answer for a genuinely UNANSWERED message is delivered, not suppressed',
        delivered && delivered.delivered !== false, { delivered });
      check('(b) exactly ONE post reached Slack',
        b.slack.posted.length === 1 && b.slack.posted[0].text === 'Cold-derived answer for 4.1', { posted: b.slack.posted.map((p) => p.text) });
      b.bridge.stop();
    }

    // ── (c) A SYSTEM NOTICE MUST NEVER BURN THE KEY (the near-miss this probe pins down) ────────
    // A P3 notice (slow/give-up/dead-air) travels through the SAME `deliverToOwner` with
    // `answersOwnerAsk` (and `inboundMsgId`) left unset. If it marked the key, the real answer
    // that follows would read as an already-answered duplicate and be silently refused —
    // replacing the duplicate with silence, the one outcome worse than the defect.
    {
      const b = await warmedBridge({ liveReply: null });
      const conv = `${DM}:1.1`;
      await b.bridge.onChatMessage(msg('6.1', 'a slow question'));
      const notice = await b.bridge.deliverToOwner({ chatThreadId: conv, text: 'still working on it…', markAsk: false });
      check('(c) a system notice (answersOwnerAsk/inboundMsgId unset) posts normally',
        notice && notice.delivered !== false, { notice });
      const real = await b.bridge.deliverToOwner({ chatThreadId: conv, text: 'Real answer for 6.1', answersOwnerAsk: true, inboundMsgId: '6.1' });
      check('(c) the REAL answer that follows a notice is NOT blocked by it',
        real && real.delivered !== false, { real });
      const secondReal = await b.bridge.deliverToOwner({ chatThreadId: conv, text: 'A different real answer for 6.1', answersOwnerAsk: true, inboundMsgId: '6.1' });
      check('(c) but a genuine SECOND answer carrying the SAME inboundMsgId IS still refused',
        secondReal && secondReal.delivered === false && secondReal.reason === 'already-answered-inbound', { secondReal });
      check('(c) exactly TWO posts reached Slack (the notice, then the one real answer)',
        b.slack.posted.length === 2, { posted: b.slack.posted.map((p) => p.text) });
      b.bridge.stop();
    }

    // ── (d) THE COLD LEG'S OWN WIRING, END TO END — real arm()/deliver(), never a stand-in ─────
    // `reply-leg.js#arm` now stores `inboundMsgId` on its per-conversation state and threads it
    // into its own `deliver()` call (the ~3-line addition this scenario exists to prove landed).
    // Nothing here calls `deliverToOwner` to SIMULATE the cold leg — `replyLeg.tick()` IS the
    // cold leg, driven exactly as the daemon's own poll interval would.
    {
      const b = makeTickingBridge();
      const conv = `${DM}:d.1`;

      // d0 — the cold leg's real first delivery for a real owner message.
      const { outcome } = await deliverOneColdTurn(b, {
        rootTs: 'd.1', msgTs: 'd.1', chatMsgText: 'the cold-leg question', execId: 701, answerText: 'Cold-leg first answer',
      });
      check('(d0) premise: the message forwarded on the cold path (a brand-new conversation — warm never even attempts one)',
        outcome && outcome.forwarded === true && outcome.leg !== 'live-session', { outcome });
      check('(d0) the cold leg\'s OWN deliver() posted the real answer',
        b.slack.posted.length === 1 && b.slack.posted[0].text === 'Cold-leg first answer', { posted: b.slack.posted.map((p) => p.text) });
      // A follow-up's ticker row is captured by CHAIN THREAD, not queue-id (the queue-id is the
      // conversation's first-turn id; `arm()` never updates `p.queueId` past its first non-null
      // value — "the chain re-dispatches → a new exec on the SAME queue"). Bind it explicitly,
      // the same convention `resolveChainThread`'s own fallback derives (`exec-<first exec_id>`).
      b.threadMap.bindChainThread(conv, 'exec-701');

      // d1 — a system notice on the SAME conversation the cold leg just answered on. Must post
      // (notices always do) and must not disturb the guard either way — proven by d2 below still
      // catching the duplicate.
      const notice = await b.bridge.deliverToOwner({ chatThreadId: conv, text: 'still working on your next one…', markAsk: false });
      check('(d1) a system notice on the cold-leg conversation posts normally and carries no answersOwnerAsk/inboundMsgId',
        notice && notice.delivered !== false, { notice });

      // d2 — THE PIVOT. A direct delivery attempt carrying the SAME id the cold leg's `deliver()`
      // call just answered with. Refused ONLY IF `reply-leg.js#deliver()` actually told
      // `deliverToOwner` what it was answering — i.e. only if the wiring landed.
      const dup = await b.bridge.deliverToOwner({ chatThreadId: conv, text: 'A duplicate, differently-worded cold answer', answersOwnerAsk: true, inboundMsgId: 'd.1' });
      check('(d2) a duplicate carrying the SAME inboundMsgId the cold leg just answered with is REFUSED — proves reply-leg.js#deliver() populated the guard for real',
        dup && dup.delivered === false && dup.reason === 'already-answered-inbound', { dup });
      check('(d2) exactly TWO posts reached Slack (the cold answer, then the notice) — the duplicate never landed',
        b.slack.posted.length === 2, { posted: b.slack.posted.map((p) => p.text) });

      // d3 — DISCRIMINATOR, same shape as (b): a SECOND, genuinely fresh owner message on the
      // SAME conversation (a real follow-up, its own inboundMsgId) still gets its cold answer —
      // the guard must not have latched the conversation shut after d0's delivery.
      const { outcome: outcome2 } = await deliverOneColdTurn(b, {
        rootTs: 'd.1', msgTs: 'd.4', chatMsgText: 'a genuine follow-up question', execId: 702, answerText: 'Cold-leg second answer', chainThread: 'exec-701',
      });
      check('(d3) premise: the follow-up forwarded on the cold path too',
        outcome2 && outcome2.forwarded === true, { outcome2 });
      check('(d3) a genuinely NEW owner message on the SAME conversation still gets answered — the guard did not latch the conversation shut',
        b.slack.posted.length === 3 && b.slack.posted[2].text === 'Cold-leg second answer', { posted: b.slack.posted.map((p) => p.text) });

      b.bridge.stop();
    }
  } catch (err) {
    cap.log({ error: err.message, stack: err.stack });
    checks.push({ name: 'no-exception', pass: false, error: err.message });
  }

  const pass = checks.every((c) => c.pass);
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-duplicate-idempotency', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-duplicate-idempotency EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
}

main();
