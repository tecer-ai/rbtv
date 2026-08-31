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
// ⚑ THE COLD LEG'S OWN WIRING IS A DISCLOSED GAP, NOT TESTED HERE. `deliverToOwner` takes
// `inboundMsgId` as an explicit ARGUMENT (never a lookup it performs itself — a first cut that
// tried a side-channel "currently pending" map reintroduced exactly the bug class
// `reply-leg.js`'s own header warns about; see `chat-bridge.js`'s `answeredInbound` comment for
// the full account). The warm branch (scenario a's premise) supplies it for real. The cold leg's
// OWN `deliver()` call would need the SAME one-line threading through `reply-leg.js#arm`, which
// could not land in this change (that file carries a large, unrelated, in-flight uncommitted edit
// — `dup-revive-lineage`'s session-lineage-fork fix — and committing it would publish someone
// else's unfinished work). Scenarios (a)/(c)'s "cold duplicate" calls drive `deliverToOwner`
// DIRECTLY with the `inboundMsgId` a fixed `reply-leg.js` would supply, to prove the MECHANISM
// this fix installs is correct and non-regressing (see `probe-chat-reply-leg.js`, run clean
// against this change) — not to claim the wiring is complete end to end.
//
// MUTATION EVIDENCE — verified 2026-08-31 against a clean pre-fix worktree (`git worktree add
// <tmp> HEAD`): with the guard absent, scenario (a)'s second delivery is NOT refused — both texts
// post, reproducing the duplicate. Restored (this file, against the fixed tree), (a) passes. See
// the seat's closing report for the exact commands and quoted output.

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
