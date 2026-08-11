'use strict';

// ── THE WARM TURN'S POSTING PATH (owner-observed defects, 2026-08-10) ────────────────────────────
//
// Two defects landed together with the warm path (df65147) and were reported from the owner's real
// Slack thread minutes later. Both live in ONE block of chat-bridge.js — the `warm.answered` arm —
// and neither is reachable from the cold path's own probe, because on the cold path both behaviours
// were always correct:
//
//   1  THE ANSWER ARRIVED TWICE. A live session's `result` event carries the WHOLE final turn text,
//      and the reply contract asks the agent to end its turn with the message between two sentinel
//      lines. So a conformant warm reply is prose + `<<<SLACK-REPLY>>>` + the message + the closing
//      marker — and the warm arm posted it RAW. The cold path never had this: it runs the same text
//      through `checkReplyContract`/`extractFenced` before delivering.
//   2  NO READ RECEIPT ON A FOLLOW-UP. The ⏳ marker was stamped only on the cold-forward branch,
//      which a warm turn returns before ever reaching — so message #1 of a thread was marked and
//      every message after it (the warm ones) showed nothing at all. The design's premise was that
//      a warm turn is too fast to need one; this box measured 13.4s / 18.5s / 25.8s.
//
// The third claim here is a NEGATIVE one and it is the reason this probe drives the bridge rather
// than the extractor: a warm turn must be posted ONCE. It writes no queue row and no `jobs_log` row
// (server/spawn/live-sessions.js), so the reply leg has no spawn action to capture — but "the cold
// leg did not also run" is a property of the bridge's control flow, and only the bridge can show it.
//
// Same posture as probe-chat-mention-route: NO daemon. The gateway is a stub that answers the
// `live-feed` intent with a scripted reply and records every other forward; Slack is a fake that
// records every post AND every reaction in arrival order.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { makeCapture, nowMs, sleep } = require('./lib');
const { buildBridge } = require('../index');
const { FENCE_OPEN, FENCE_CLOSE, UNFORMATTED_PREFIX } = require('../reply-leg');
const { toMrkdwn } = require('../mrkdwn');

const OUT = path.join(__dirname, 'probe-chat-warm-post.out');

const USER = 'U_OWNER';
const DM = 'D_OWNER';

// ── fakes ────────────────────────────────────────────────────────────────────────────────────────

// The transport surface the warm arm touches: post, and the two reaction calls. No channel admin —
// this fixture is DM (master) traffic, so the goal-channel map is deliberately absent.
function makeFakeSlack() {
  const posted = [];
  const reactions = []; // ORDERED — a remove landing before its own add is the failure this catches
  return {
    posted, reactions,
    async sendToOwner({ channel, threadTs, text }) { posted.push({ channel, threadTs, text }); return { delivered: true, ts: '1.0' }; },
    async react({ channel, ts, name }) { reactions.push({ method: 'add', channel, ts, name }); return { ok: true }; },
    async unreact({ channel, ts, name }) { reactions.push({ method: 'remove', channel, ts, name }); return { ok: true }; },
    async start() { return { connected: true }; },
    stop() {},
  };
}

// `liveReply` is what the warm session answers with — the ONE knob each arm turns. `null` means
// the feed refuses (`fed: false`), which is the fall-through-to-cold case.
function makeFakeForwarder({ liveReply = null } = {}) {
  const forwards = [];
  let nextId = 100;
  return {
    forwards,
    get enqueued() { return forwards.filter((f) => f.intent !== 'live-feed'); },
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
    sessionProfile: 'fallback-profile',
    masterProfile: 'master-profile',
    sendMessageJobId: 'send-message',
    workdir: '/configured/master/workdir',
    workspaceRoot: fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-warm-')),
    allowlist: [USER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  };
  const built = buildBridge(config, {
    logger: () => {},
    makeTransport: () => slack,
    forwarderImpl: forwarder,
    replyLegOptions: { pollMs: 3600000 }, // the leg must never tick under us — this probe is about the warm arm
  });
  return { ...built, slack, forwarder };
}

// One DM conversation, several messages in it. `msgTs` is the MESSAGE's own ts (the reaction
// target — the thing the two defects are about); `rootTs` is the thread's, and it is what the
// conversation is keyed on. Master traffic is thread-scoped, so a follow-up carries the ROOT ts —
// give every message its own and each one mints a fresh conversation that can never be warm.
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

// A conversation is warm-eligible only once it HOLDS a chain — the first message is what mints one.
// This is the real sequence, not a shortcut: cold turn #1, then the exec-id bind the reply leg
// performs when it captures that turn's spawn, then warm from #2 on.
async function warmedBridge({ liveReply }) {
  const b = makeBridge({ liveReply });
  await b.bridge.start();
  const cold = await b.bridge.onChatMessage(msg('1.1', 'first message'));
  b.threadMap.bindSessionExecId(`${DM}:1.1`, 5001);
  return { ...b, cold };
}

// ── the probe ────────────────────────────────────────────────────────────────────────────────────

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const checks = [];
  const check = (name, pass, detail = {}) => { checks.push({ name, pass, ...detail }); cap.log({ check: name, pass, ...detail }); };

  try {
    // 1 — A FENCED WARM REPLY POSTS ONLY WHAT IS INSIDE THE FENCE.
    //     The fixture is the owner's own paste, in shape: the prose answer, then the fence pair
    //     holding a compact re-version of it. Before the fix BOTH halves and both markers were
    //     posted; the check is on the WHOLE posted string, so "it contains the answer" cannot pass
    //     a post that also contains the duplicate.
    {
      const INSIDE = '*The seat runs on the daemon lane.*\n\nIt picks up on the next tick.';
      const raw = [
        'Let me answer that. The seat runs on the daemon lane and picks up on the next tick.',
        '',
        FENCE_OPEN,
        INSIDE,
        FENCE_CLOSE,
      ].join('\n');
      const { bridge, slack, forwarder } = await warmedBridge({ liveReply: raw });
      const warm = await bridge.onChatMessage(msg('2.1', 'and the follow-up?'));
      await sleep(50); // the reaction chain is fire-and-forget by construction — let it settle

      const post = slack.posted[slack.posted.length - 1];
      check('warm turn was answered on the warm path (premise)',
        warm.forwarded === true && warm.leg === 'live-session' && warm.warm === true, { warm });
      check('D1: the post carries ONLY the fenced content — no duplicate, no markers',
        Boolean(post) && post.text === INSIDE, { posted: post && post.text });
      check('D1: neither sentinel line survives into Slack',
        Boolean(post) && !post.text.includes(FENCE_OPEN) && !post.text.includes(FENCE_CLOSE), { posted: post && post.text });
      check('D1: the un-fenced prose half is NOT posted (the duplication is gone, not merely reordered)',
        Boolean(post) && !post.text.includes('Let me answer that'), { posted: post && post.text });

      // 3 — POSTED ONCE. The warm arm returns before the forward path, so no second leg runs for
      //     this turn: exactly one post, and NOTHING enqueued after the cold first message.
      const enqueuedAfterCold = forwarder.enqueued.length;
      check('D3: the warm turn is posted EXACTLY ONCE and enqueues nothing — the cold leg did not also run',
        slack.posted.length === 1 && enqueuedAfterCold === 1,
        { posts: slack.posted.length, enqueues: enqueuedAfterCold, intents: forwarder.forwards.map((f) => f.intent) });

      // 2 — THE READ RECEIPT. Added on the owner's OWN message when it is accepted, removed when
      //     the answer lands — and in THAT order (a remove that overtakes its add sticks forever).
      const rx = slack.reactions;
      check('D2: the warm turn stamps ⏳ on the owner message and takes it off when the answer posts',
        rx.length === 4
        && rx[2].method === 'add' && rx[2].ts === '2.1' && rx[2].name === 'hourglass_flowing_sand'
        && rx[3].method === 'remove' && rx[3].ts === '2.1',
        { reactions: rx });
      check('D2: the COLD first message still gets exactly one add and one remove (no flicker from the second mark)',
        rx.length === 4
        && rx[0].method === 'add' && rx[0].ts === '1.1'
        && rx[1].method === 'remove' && rx[1].ts === '1.1',
        { reactions: rx });
      bridge.stop();
    }

    // 4 — AN UNFENCED WARM REPLY IS NON-CONFORMANT, exactly as it is on the cold path. Its text
    //     still reaches the owner — through the safety net, behind the marker that attributes the
    //     shape to the agent. Nothing of the answer is lost; only its billing changes.
    //     (Was "posted byte-for-byte" until the owner ruled the warm arm mirrors the cold path's
    //     final delivery, 2026-08-11 — a no-fence verdict is `ok: false` there and now here.)
    {
      const PLAIN = 'no fence here, just an answer with a <<<not-a-sentinel>>> inside it';
      const { bridge, slack } = await warmedBridge({ liveReply: PLAIN });
      await bridge.onChatMessage(msg('3.1', 'follow-up'));
      await sleep(50);
      const post = slack.posted[slack.posted.length - 1];
      check('D4: an UNFENCED warm reply is flagged unformatted and its text survives intact',
        Boolean(post) && post.text === `${UNFORMATTED_PREFIX}${PLAIN}`, { posted: post && post.text });
      bridge.stop();
    }

    // 6 — THE MRKDWN SAFETY NET ON THE WARM ARM (owner ruling 2026-08-11, option b). A reply that
    //     IS fenced but whose fenced body is markdown is non-conformant: the cold leg converts it
    //     and flags it, and the warm arm — which has no exec to revive — must do the same rather
    //     than post raw markdown into Slack. The table is the tell: `toMrkdwn` deliberately
    //     refuses to rewrite pipe tables, so it survives verbatim INSIDE a converted body, which
    //     is exactly what proves the body went through the converter rather than around it.
    {
      const INSIDE = ['# The plan', '', '**bold** matters here.', '', '| a | b |', '| - | - |'].join('\n');
      const raw = ['Here you go.', '', FENCE_OPEN, INSIDE, FENCE_CLOSE].join('\n');
      const { bridge, slack } = await warmedBridge({ liveReply: raw });
      await bridge.onChatMessage(msg('5.1', 'follow-up with markdown in the fence'));
      await sleep(50);
      const post = slack.posted[slack.posted.length - 1];
      check('D5: a markdown-ism inside the warm fence is CONVERTED and flagged unformatted',
        Boolean(post) && post.text === `${UNFORMATTED_PREFIX}${toMrkdwn(INSIDE)}`, { posted: post && post.text });
      check('D5: the heading and the bold are mrkdwn, and no markdown syntax reaches Slack',
        Boolean(post) && post.text.includes('*The plan*') && post.text.includes('*bold* matters here.')
        && !post.text.includes('**') && !post.text.includes('# The plan'), { posted: post && post.text });
      bridge.stop();
    }

    // 5 — THE FALL-THROUGH. A refused feed takes the cold path, and the ⏳ stamped before the
    //     attempt must NOT be removed and re-added by the cold branch's own mark: one add, and it
    //     stays on until the reply leg's delivery clears it.
    {
      const { bridge, slack, forwarder } = await warmedBridge({ liveReply: null });
      const cold = await bridge.onChatMessage(msg('4.1', 'follow-up the warm session cannot take'));
      await sleep(50);
      const marks = slack.reactions.filter((r) => r.ts === '4.1');
      check('a refused feed falls through to the cold path (premise)',
        cold.forwarded === true && cold.leg !== 'live-session'
        && forwarder.forwards.some((f) => f.intent === 'live-feed'), { cold });
      check('D2: the fall-through marks the message ONCE — no remove/re-add flicker',
        marks.length === 1 && marks[0].method === 'add', { marks });
      bridge.stop();
    }
  } catch (err) {
    cap.log({ error: err.message, stack: err.stack });
    checks.push({ name: 'no-exception', pass: false, error: err.message });
  }

  const pass = checks.every((c) => c.pass);
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-warm-post', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-warm-post EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
}

main();
