'use strict';

// probe-chat-ask-release — `spec-owner-io.md` §2.1/§2.4 (release) and §3 (opening line).
//
// NO SLACK AND NO DAEMON. The outbox, the `record-owner-ask` sender and `chat.update` are all
// injected fakes, so every claim here is about THIS module's decisions: which thread, which
// sender, which token, and what is recorded. The gateway/daemon halves are proven where they live
// (`gateway/probes`, `server/heart`), and a live post is an owner-gated act, never a probe's.
//
// ⚑ THE RELAUNCH SIGNAL IS COUNTED, NOT ASSUMED. `reapAsk` is what fires it (§2.8, one
// transaction), so "exactly once" is measured as the number of reap calls the fake received —
// a released ask that reaped twice and a released ask that reaped never both go RED here.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const {
  createAskThreads, openingLine, displaySuffix, replyCopyPath, MARKER_ASK, MARKER_NOTE,
} = require('../ask-thread');
const { NACK_ASK } = require('../reply-grammar');

const OUT = path.join(__dirname, 'probe-chat-ask-release.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence: evidence || {} }); };

const CHANNEL = 'C-GOAL-1';
const GOAL = 'demo-goal';
const SEAT = 'draft-seat';
const OWNER = 'U-OWNER';
const STRANGER = 'U-STRANGER';
const BOT = 'U-BOT';

const workspaceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ask-release-'));
fs.mkdirSync(path.join(workspaceRoot, '.rbtv', 'goals', GOAL, 'coordination'), { recursive: true });

// ── The fakes ────────────────────────────────────────────────────────────────────────────────
function harness({ interactive = true, tsSeq = ['1724508123.123456'] } = {}) {
  const posts = [];
  const updates = [];
  const opens = [];
  const reaps = [];
  let tsAt = 0;
  const outbox = {
    async post(input) {
      posts.push(input);
      if (input.thread_ts == null) {
        const ts = tsSeq[Math.min(tsAt, tsSeq.length - 1)];
        tsAt += 1;
        return { delivered: true, ts, error: null };
      }
      return { delivered: true, ts: `${input.thread_ts}-reply`, error: null };
    },
  };
  const askRecord = {
    async openAsk(a) { opens.push(a); return { recorded: true, ask_id: a.chatThreadId, already: false }; },
    async reapAsk(a) { reaps.push(a); return { recorded: true, ask_id: a.chatThreadId, state: 'closed', relaunch: { queued: true } }; },
  };
  const threads = createAskThreads({
    outbox,
    askRecord,
    updateMessage: async (u) => { updates.push(u); return { updated: true }; },
    authorizedSenders: [OWNER],
    botUserId: BOT,
    seatIsInteractive: () => interactive,
    workspaceRoot,
    logger: null,
  });
  return { threads, posts, updates, opens, reaps };
}

// ── §3 — the opening line ────────────────────────────────────────────────────────────────────
check('§2.1 display_suffix is the last 6 chars of thread_ts with the dot stripped',
  displaySuffix('1724508123.123456') === '123456' && displaySuffix('1724508123.000042') === '000042',
  { sample: displaySuffix('1724508123.123456') });

const line = openingLine({ marker: MARKER_ASK, threadTs: '1724508123.123456', seatName: SEAT, label: 'work-content' });
check('§3 rendered ❓ line is exactly `{marker} {display_suffix} · {seat_name} · {label}`',
  line === '❓ 123456 · draft-seat · work-content', { line });

check('§3 note line is the same shape with the 💭 marker and never both markers',
  openingLine({ marker: MARKER_NOTE, threadTs: '1724508123.123456', seatName: 'leader', label: 'recovery' })
    === '💭 123456 · leader · recovery'
  && !line.includes(MARKER_NOTE), {});

// ── Posting: a new thread per ask, the line stamped on it, one record ────────────────────────
(async () => {
  {
    const h = harness();
    const r = await h.threads.postAsk({ goalId: GOAL, channelId: CHANNEL, seatName: SEAT, label: 'work-content', body: 'Which binder should the vault path use?' });
    check('an ask opens a NEW thread (thread_ts null on the opening post) and its ts becomes the ask id [D18, T5-R8, D-8]',
      r.posted === true && h.posts.length === 1 && h.posts[0].thread_ts === null
      && h.posts[0].kind === 'ask' && r.askId === '1724508123.123456',
      { askId: r.askId, kind: h.posts[0].kind });
    check('the posted message carries the §3 lead line, then the body',
      h.updates.length === 1
      && h.updates[0].text.split('\n')[0] === '❓ 123456 · draft-seat · work-content'
      && h.updates[0].text.includes('Which binder'),
      { first: h.updates[0].text.split('\n')[0] });
    check('❓ mints exactly ONE ask record, keyed by the thread, carrying its label',
      h.opens.length === 1 && h.opens[0].chatThreadId === '1724508123.123456'
      && h.opens[0].seat === SEAT && h.opens[0].label === 'work-content',
      { opens: h.opens.length });
  }

  {
    const h = harness();
    const r = await h.threads.postNote({ goalId: GOAL, channelId: CHANNEL, seatName: 'leader', label: 'recovery', body: 'D13 re-plan started.' });
    check('§2.1 a 💭 note posts a thread and mints NO ask record — it can never read as `open`',
      r.posted === true && h.opens.length === 0 && h.reaps.length === 0
      && h.updates[0].text.startsWith('💭 '), { opens: h.opens.length });
  }

  {
    const h = harness({ interactive: false });
    const r = await h.threads.postAsk({ goalId: GOAL, channelId: CHANNEL, seatName: 'silent-seat', body: 'anything' });
    check('[T2-R14] a non-interact seat\'s owner-ask is REFUSED at this door — nothing posted, nothing recorded',
      r.posted === false && r.reason === 'seat-not-interact' && h.posts.length === 0 && h.opens.length === 0,
      { reason: r.reason });
  }

  {
    // §2.4.5 — a re-ask is a FRESH thread and costs nothing. Two asks, two ids, two records.
    const h = harness({ tsSeq: ['1724508123.111111', '1724509999.222222'] });
    const a = await h.threads.postAsk({ goalId: GOAL, channelId: CHANNEL, seatName: SEAT, body: 'first batch' });
    const b = await h.threads.postAsk({ goalId: GOAL, channelId: CHANNEL, seatName: SEAT, body: 'the reply was insufficient — second batch' });
    check('a re-ask mints a FRESH thread with its own id and its own record, free of any budget [§2.4.5, C-11]',
      a.askId !== b.askId && h.opens.length === 2
      && h.posts.every((p) => p.thread_ts === null)
      && h.updates[1].text.startsWith('❓ 222222 · draft-seat · work-content'),
      { first: a.askId, second: b.askId });
  }

  // ── §2.4 — release ─────────────────────────────────────────────────────────────────────────
  const ASK_ID = '1724508123.123456';
  const OTHER_THREAD = '1724500000.999999';

  {
    const h = harness();
    const r = await h.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID,
      threadTs: OTHER_THREAD, senderId: OWNER, text: 'approve',
    });
    check('§2.4.1 a reply in the WRONG thread releases nothing — no reap, no relaunch signal, no NACK',
      r.released === false && r.reason === 'wrong-thread' && h.reaps.length === 0 && h.posts.length === 0,
      { reason: r.reason, reaps: h.reaps.length });
  }

  {
    const h = harness();
    const r = await h.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID,
      threadTs: ASK_ID, senderId: STRANGER, text: 'approve',
    });
    check('§2.4.2 the RIGHT thread but an UNAUTHORIZED sender releases nothing and is ignored in silence (no NACK)',
      r.released === false && r.reason === 'unauthorized' && h.reaps.length === 0 && h.posts.length === 0,
      { reason: r.reason });
  }

  {
    const h = harness();
    const r = await h.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID,
      threadTs: ASK_ID, senderId: BOT, text: 'approve',
    });
    check('§2.4.2 the bot\'s own message can never release an ask',
      r.released === false && r.reason === 'unauthorized' && h.reaps.length === 0, { reason: r.reason });
  }

  {
    const h = harness();
    const r = await h.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID,
      threadTs: ASK_ID, senderId: OWNER, text: 'lgtm ship it',
    });
    const nackPost = h.posts.find((p) => p.kind === 'nack');
    check('§2.4.3 an UNRECOGNIZED first token posts the verbatim NACK in the SAME thread and the ask stays open',
      r.released === false && r.reason === 'unparsed' && r.nacked === true
      && !!nackPost && nackPost.payload === NACK_ASK && nackPost.thread_ts === ASK_ID
      && nackPost.ask_id === ASK_ID && h.reaps.length === 0,
      { nack: nackPost && nackPost.payload.slice(0, 40), reaps: h.reaps.length });
  }

  {
    const h = harness();
    const r = await h.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID,
      threadTs: ASK_ID, senderId: OWNER, text: 'b) rewrite to the project folder\nand keep the draft',
    });
    const dest = replyCopyPath(workspaceRoot, GOAL, ASK_ID);
    check('§2.4.4 the RIGHT thread + an AUTHORIZED sender + a recognized token RELEASES: reap fires EXACTLY once',
      r.released === true && r.outcome === 'b' && h.reaps.length === 1
      && h.reaps[0].chatThreadId === ASK_ID && h.reaps[0].seat === SEAT
      && r.reaped.relaunch && r.reaped.relaunch.queued === true,
      { outcome: r.outcome, reaps: h.reaps.length });
    check('§2.4.5 the authorized reply is PERSISTED TO DISK for the relaunched seat to read',
      r.reply.written === true && fs.existsSync(dest)
      && fs.readFileSync(dest, 'utf8').includes('rewrite to the project folder'),
      { path: dest });
    check('the release posts NOTHING — no NACK and no receipt (§2.4.4 flips state, the closing message is the seat\'s)',
      h.posts.length === 0, { posts: h.posts.length });
  }

  {
    const h = harness();
    const r = await h.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID,
      threadTs: ASK_ID, senderId: OWNER, text: 'pause demo-goal', channelGoal: GOAL, liveGoals: [GOAL],
    });
    check('§4.2 a mechanical `pause {goal}` in an ask thread does NOT release the ask',
      r.released === false && r.reason === 'mechanical' && r.outcome === 'pause' && h.reaps.length === 0,
      { outcome: r.outcome });
  }

  {
    // The door the redesign DELETED, asserted as absent rather than assumed: there is no way to
    // reach a reap without naming the exact thread [D-4-ruling, C-3].
    const src = fs.readFileSync(path.join(__dirname, '..', 'ask-thread.js'), 'utf8');
    const code = src.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
    check('no oldest-open / `re:` release door survives in the module\'s live code',
      !/oldest/i.test(code) && !/\bre:\s*<?\d/.test(code) && /String\(threadTs\) !== String\(askId\)/.test(code),
      {});
  }

  const pass = checks.every((c) => c.pass);
  const wallMs = Date.now() - t0;
  const exit = pass ? 0 : 1;
  fs.writeFileSync(OUT, `${JSON.stringify({
    summary: { probe: 'probe-chat-ask-release', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 },
    entries: checks,
  }, null, 2)}\n`);
  process.stdout.write(`PROBE probe-chat-ask-release EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
})().catch((err) => {
  process.stdout.write(`PROBE probe-chat-ask-release EXIT=1 THREW ${err.stack}\n`);
  process.exit(1);
});
