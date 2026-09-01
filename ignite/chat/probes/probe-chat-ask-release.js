'use strict';

// probe-chat-ask-release — `spec-owner-io.md` §2.1/§2.4 (release) and §3 (opening line).
//
// NO SLACK AND NO DAEMON. The outbox, the `record-owner-ask` sender and `chat.update` are all
// injected fakes, so every claim here is about THIS module's decisions: which thread, which
// sender, which token, and what is recorded. The gateway/daemon halves are proven where they live
// (`runtime/gateway/probes`, `state-store/heart`), and a live post is an owner-gated act, never a probe's.
//
// ⚑ THE RELAUNCH SIGNAL IS COUNTED, NOT ASSUMED. `reapAsk` is what fires it (§2.8, one
// transaction), so "exactly once" is measured as the number of reap calls the fake received —
// a released ask that reaped twice and a released ask that reaped never both go RED here.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const {
  createAskThreads, openingLine, displaySuffix, replyCopyPath, MARKER_ASK, MARKER_NOTE, ASK_REPLY_SPLIT,
} = require('../ask-thread');
const { NACK_ASK } = require('../reply-grammar');
const { buildBridge } = require('../index');

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

// `d-owner-ask-shape` R-A3: the id moves OFF the reserved lead line entirely — `openingLine` no
// longer takes `threadTs` into account for a ❓ line at all, only for the (unchanged) 💭 one.
const line = openingLine({
  marker: MARKER_ASK, threadTs: '1724508123.123456', seatName: SEAT, label: 'work-content', subject: 'the leader seat keeps failing to start',
});
check('§3 [`d-owner-ask-shape`] rendered ❓ line is exactly `NEEDS YOUR ANSWER — {subject}`, no id and no seat/label',
  line === '❓ NEEDS YOUR ANSWER — the leader seat keeps failing to start', { line });

check('§3 [`d-owner-ask-shape`] an absent subject falls back to `{seat} needs your answer`',
  openingLine({ marker: MARKER_ASK, threadTs: '1724508123.123456', seatName: SEAT, label: 'work-content' })
    === '❓ NEEDS YOUR ANSWER — draft-seat needs your answer', {});

check('§3 note line is UNCHANGED by this redesign — still `{marker} {display_suffix} · {seat_name} · {label}`, and never both markers',
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
    check('the posted message carries the §3 lead line (fallback subject, no options table), the body, then `ref <suffix>` as the LAST line',
      h.updates.length === 1
      && h.updates[0].text.split('\n')[0] === '❓ NEEDS YOUR ANSWER — draft-seat needs your answer'
      && h.updates[0].text.includes('Which binder')
      && h.updates[0].text.trim().split('\n').pop() === 'ref 123456',
      { first: h.updates[0].text.split('\n')[0], last: h.updates[0].text.trim().split('\n').pop() });
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

  // ── TYPE-GATED ADMISSION (`d-escalation-surface` part 1, seat `esc-door-split`) ────────────────
  // The door is bypassed by `kind`, never by `label`. `label` stays a two-value digest taxonomy
  // (`work-content`/`recovery`) and decides admission for nobody — proven here by holding `label`
  // fixed at `'recovery'` across all four arms and varying only `kind` and `interactive`.
  {
    const h = harness({ interactive: false });
    const r = await h.threads.postAsk({
      goalId: GOAL, channelId: CHANNEL, seatName: 'leader', label: 'recovery', kind: 'escalation',
      body: 'nobody in this run can clear this halt',
    });
    check('`kind: \'escalation\'` is admitted regardless of seat designation and mints EXACTLY ONE ask record — the ❓ door for a real halt',
      r.posted === true && h.opens.length === 1 && h.opens[0].chatThreadId === r.askId,
      { posted: r.posted, opens: h.opens.length });
  }
  {
    const h = harness({ interactive: false });
    const r = await h.threads.postAsk({
      goalId: GOAL, channelId: CHANNEL, seatName: 'leader', label: 'recovery', kind: 'recovery',
      body: 'LANE: demo-goal / worker',
    });
    check('`kind: \'recovery\'` (a daemon-decided exhausted-lane ask, `recovery-poster.js`\'s own use — unrelated to this seat\'s work) is UNCHANGED by the type-gate: still admitted, still mints a record',
      r.posted === true && h.opens.length === 1,
      { posted: r.posted, opens: h.opens.length });
  }
  {
    // THE REGRESSION THIS SEAT FIXES: `label: 'recovery'` ALONE (the ferry's OLD bypass — every
    // `leader` row, escalation or not, was labelled `recovery`) no longer admits anything.
    // `kind` defaults to `'ordinary'`, so an undesignated seat's row is refused exactly like any
    // other ordinary ask — mints ZERO records, the discriminating observation for DoD 2/3.
    const h = harness({ interactive: false });
    const r = await h.threads.postAsk({
      goalId: GOAL, channelId: CHANNEL, seatName: 'leader', label: 'recovery',
      body: 'FYI: proceeding with the default binder, no owner input needed',
    });
    check('`label: \'recovery\'` alone (no `kind`) NO LONGER bypasses [T2-R14] — an ordinary `leader` message is refused as an ask and mints ZERO records',
      r.posted === false && r.reason === 'seat-not-interact' && h.opens.length === 0,
      { posted: r.posted, reason: r.reason, opens: h.opens.length });
  }
  {
    // The note door mints no record regardless of `kind` or designation — it never checked
    // [T2-R14] to begin with (`postAsk`'s reason verbatim), so this is the "posts as 💭, mints
    // ZERO rows" half of DoD 2, on the SAME body an ask would have refused.
    const h = harness({ interactive: false });
    const r = await h.threads.postNote({
      goalId: GOAL, channelId: CHANNEL, seatName: 'leader', label: 'recovery',
      body: 'FYI: proceeding with the default binder, no owner input needed',
    });
    check('the SAME ordinary body posts as 💭 through `postNote` and mints ZERO ask records',
      r.posted === true && h.opens.length === 0 && h.updates[0].text.startsWith('💭 '),
      { posted: r.posted, opens: h.opens.length, head: h.updates[0].text.split('\n')[0] });
  }

  // ── THE TOP-LEVEL / FIRST-REPLY BODY SPLIT (`d-escalation-surface` part 9) ─────────────────────
  // `ask-thread.js#openThread` owns the MECHANICS (post the top, stamp §3, post the overflow as a
  // reply on the SAME thread_ts) — `bus-ferry.js#splitAskBody` owns the DECISION of where the
  // marker goes (only it knows the row) and is proven separately, end to end, in
  // `probe-chat-bus-ferry.js`. Here the marker is inserted directly, exactly as that decision
  // would leave it, to prove the mechanics alone.
  {
    const h = harness({ tsSeq: ['1724510000.100000'] });
    const body = [
      'one sentence naming the decision',
      '',
      'TLDR: the cage refuses the write; two ways to unblock it.',
      '',
      'a) widen the grant — fast, touches the sandbox policy',
      'b) move the file — slower, no policy change',
      'Recommend (a).',
      '',
      ASK_REPLY_SPLIT,
      '',
      'Reasoning:',
      'the full trace, step by step, is long — see the evidence file for all of it.',
      'evidence: /tmp/evidence/trace.log',
    ].join('\n');
    const r = await h.threads.postAsk({ goalId: GOAL, channelId: CHANNEL, seatName: SEAT, body });
    const topPost = h.posts.find((p) => p.thread_ts === null);
    const replyPost = h.posts.find((p) => p.thread_ts === r.askId);
    check('the TOP-LEVEL post carries the ❓ line + decision + TLDR + alternatives, and stops before "Reasoning:"',
      !!topPost && h.updates[0].text.startsWith(`❓ `) && h.updates[0].text.includes('TLDR:')
      && h.updates[0].text.includes('Recommend (a)') && !h.updates[0].text.includes('Reasoning:')
      && !h.updates[0].text.includes('trace.log'),
      { topHead: h.updates[0].text.split('\n')[0], topIncludesReasoning: h.updates[0].text.includes('Reasoning:') });
    check('the FIRST THREADED REPLY carries the full reasoning + the evidence pointer, and its thread_ts EQUALS the top-level ask id — the ask id never moved',
      !!replyPost && replyPost.payload.includes('Reasoning:') && replyPost.payload.includes('trace.log')
      && replyPost.thread_ts === r.askId && r.askId === '1724510000.100000',
      { replyThreadTs: replyPost && replyPost.thread_ts, askId: r.askId });
  }
  {
    // NEVER FABRICATED: a body with no discernible "Reasoning:"/"Full reasoning:" heading degrades
    // to everything above the fold — one post, nothing in a reply.
    const h = harness({ tsSeq: ['1724510500.200000'] });
    const r = await h.threads.postAsk({ goalId: GOAL, channelId: CHANNEL, seatName: SEAT, body: 'no structure here, just a question' });
    check('a body with no TLDR/reasoning heading is left WHOLE — one post, no threaded reply',
      h.posts.length === 1 && h.posts[0].thread_ts === null
      && h.updates[0].text.includes('no structure here'),
      { posts: h.posts.length });
  }

  {
    // §2.4.5 — a re-ask is a FRESH thread and costs nothing. Two asks, two ids, two records.
    const h = harness({ tsSeq: ['1724508123.111111', '1724509999.222222'] });
    const a = await h.threads.postAsk({ goalId: GOAL, channelId: CHANNEL, seatName: SEAT, body: 'first batch' });
    const b = await h.threads.postAsk({ goalId: GOAL, channelId: CHANNEL, seatName: SEAT, body: 'the reply was insufficient — second batch' });
    check('a re-ask mints a FRESH thread with its own id and its own record, free of any budget [§2.4.5, C-11]',
      a.askId !== b.askId && h.opens.length === 2
      && h.posts.every((p) => p.thread_ts === null)
      && h.updates[1].text.startsWith('❓ NEEDS YOUR ANSWER — draft-seat needs your answer')
      && h.updates[1].text.trim().split('\n').pop() === 'ref 222222',
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
    check('§2.4.4 the RIGHT thread + an AUTHORIZED sender + a recognized token RELEASES: reap fires EXACTLY once — an ordinary ask (`kind: null`) is OUTSIDE `d-owner-ask-shape`\'s letter table (§5.5\'s scope limit), so a bare letter is UNCHANGED by this redesign',
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

  // ── R-A5: THE LETTER → ARM MAPPING (`d-owner-ask-shape`) ──────────────────────────────────────
  //
  // Root cause #2 (`inv-reply-grammar`): a bare letter used to parse and REAP any ask — including a
  // recovery/goal-disposition thread's own kind-gated grammar, which never tries a letter at all —
  // with the raw letter as a meaningless `outcome` nothing downstream understood. These arms prove
  // the fix: a letter is resolved against THIS ask's own options table into the SAME arm tokens the
  // typed verb produces (never a second parser), and an unresolved letter NACKS instead of reaping.
  {
    const h = harness();
    const RECOVERY_OPTIONS = [
      { letter: 'a', arm: 'retry-with-change', text: 'restart it once more' },
      { letter: 'b', arm: 'drop-lane', text: "drop this seat's work" },
      { letter: 'c', arm: 'pause-goal', text: 'pause the whole goal', recommended: true, why: 'reason' },
    ];
    const a = await h.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID, threadTs: ASK_ID,
      senderId: OWNER, text: 'a please use --skip-tests', kind: 'recovery', options: RECOVERY_OPTIONS,
    });
    check("R-A5 letter `a` on a recovery ask resolves to the SAME arm token `retry with change` (`reply-grammar.js`) produces, and the owner's comment after the letter carries through (`rr-correction-carry`)",
      a.released === true && a.outcome === 'retry-with-change' && a.family === 'recovery'
      && a.comments === 'please use --skip-tests',
      { outcome: a.outcome, family: a.family, comments: a.comments });

    const h2 = harness();
    const b = await h2.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID, threadTs: ASK_ID,
      senderId: OWNER, text: 'b)', kind: 'recovery', options: RECOVERY_OPTIONS,
    });
    check('R-A5 letter `b` on a recovery ask resolves to `drop-lane`',
      b.released === true && b.outcome === 'drop-lane' && b.family === 'recovery', { outcome: b.outcome });

    const h3 = harness();
    const c = await h3.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID, threadTs: ASK_ID,
      senderId: OWNER, text: 'c', kind: 'recovery', options: RECOVERY_OPTIONS,
    });
    check('R-A5 letter `c` on a recovery ask resolves to `pause-goal`',
      c.released === true && c.outcome === 'pause-goal' && c.family === 'recovery', { outcome: c.outcome });

    const DISPOSITION_OPTIONS = [
      { letter: 'a', arm: 'keep', text: 'keep it open' },
      { letter: 'b', arm: 'close', text: 'close it' },
    ];
    const h4 = harness();
    const keep = await h4.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID, threadTs: ASK_ID,
      senderId: OWNER, text: 'a', kind: 'goal-disposition', options: DISPOSITION_OPTIONS,
    });
    const h5 = harness();
    const close = await h5.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID, threadTs: ASK_ID,
      senderId: OWNER, text: 'b', kind: 'goal-disposition', options: DISPOSITION_OPTIONS,
    });
    check('R-A5 `keep`/`close` on a goal-disposition ask are reachable BY LETTER, resolving to the same two tokens the typed word produces',
      keep.released === true && keep.outcome === 'keep' && keep.family === 'disposition'
      && close.released === true && close.outcome === 'close' && close.family === 'disposition',
      { keep: keep.outcome, close: close.outcome });

    // A letter on an ask with NO table (recovery/disposition kind-gated grammar never tries a
    // letter, and no `options` were supplied) NACKS — never reaps on a meaningless outcome.
    const h6 = harness();
    const noTable = await h6.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID, threadTs: ASK_ID,
      senderId: OWNER, text: 'a', kind: 'recovery',
    });
    check('R-A5 a letter on an ask with NO options table NACKS — the ask stays open, nothing reaped',
      noTable.released === false && noTable.reason === 'unparsed' && noTable.nacked === true
      && h6.reaps.length === 0,
      { reason: noTable.reason, reaps: h6.reaps.length, nack: noTable.nack });

    // A letter OUTSIDE this ask's own table NACKS with THIS ask's real letters, not the generic
    // recovery-ladder NACK — the owner is told what actually answers THIS question.
    const h7 = harness();
    const outside = await h7.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID, threadTs: ASK_ID,
      senderId: OWNER, text: 'd', kind: 'recovery', options: RECOVERY_OPTIONS,
    });
    check("R-A5 a syntactically-valid letter (a–g) OUTSIDE this ask's table nacks naming THIS ask's own real letters",
      outside.released === false && outside.reason === 'unparsed' && h7.reaps.length === 0
      && /a\) restart it once more/.test(outside.nack) && /b\) drop this seat's work/.test(outside.nack)
      && /c\) pause the whole goal/.test(outside.nack),
      { nack: outside.nack, reaps: h7.reaps.length });

    // Scope-limit regression guard: an ORDINARY ask (`kind: null`, no `options` table —
    // escalation/approval/ordinary are "not reshaped in this cluster", §5.5's own closing note) is
    // UNCHANGED by this letter→arm mapping — its bare letter still parses and reaps exactly as it
    // did before (proved at scale in §2.4.4 above); the mapping engages ONLY for `kind: 'recovery'`/
    // `'goal-disposition'`, the two kinds that actually carry a table.
    const h8 = harness();
    const ordinaryLetter = await h8.threads.release({
      goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId: ASK_ID, threadTs: ASK_ID,
      senderId: OWNER, text: 'd) some other letter',
    });
    check('R-A5 scope limit: a bare letter on an ORDINARY ask (`kind: null`) is untouched by this redesign — it still parses and would reap, never nacked for lack of a table that this kind never gets',
      ordinaryLetter.released === true && ordinaryLetter.outcome === 'd' && ordinaryLetter.family === 'lettered'
      && h8.reaps.length === 1,
      { released: ordinaryLetter.released, outcome: ordinaryLetter.outcome, reaps: h8.reaps.length });
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

  // ── E — END TO END THROUGH THE BRIDGE ────────────────────────────────────────────────────────
  //
  // Everything above drives `ask-thread.js` directly. This section drives the REAL BRIDGE, because
  // a door that is built and proven but never wired is exactly the state this sitting inherited:
  // `chat-bridge.js` must CONSTRUCT the module, the bus ferry must reach it instead of parking,
  // and an inbound Slack message in an ask's thread must reach `release` — three wirings, none of
  // which any check on the module alone can see.
  //
  // Still no Slack and still no daemon: the transport and the gateway forwarder are fakes.
  {
    const eRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ask-release-e2e-'));
    const E_GOAL = 'e2e-goal';
    const E_SEAT = 'writer';
    const DM = 'D_OWNER';
    const goalDir = path.join(eRoot, '.rbtv', 'goals', E_GOAL);
    fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
    fs.writeFileSync(path.join(goalDir, 'coordination', 'execution'), '2026-08-24a\n');
    fs.mkdirSync(path.join(goalDir, 'seats', E_SEAT), { recursive: true });
    // [T2-R14] the seat IS designated, so the ask door accepts it. The refusal half is the
    // `seat-not-interact` check further down, on a seat that declares nothing.
    fs.writeFileSync(path.join(goalDir, 'seats', E_SEAT, 'seat.md'),
      `---\nseat: ${E_SEAT}\nhuman-interactive: yes\nfallback: block-and-queue\n---\nbody\n`);
    fs.mkdirSync(path.join(goalDir, 'seats', 'silent'), { recursive: true });
    fs.writeFileSync(path.join(goalDir, 'seats', 'silent', 'seat.md'), '---\nseat: silent\n---\nbody\n');
    const busFile = path.join(goalDir, 'coordination', 'messages.md');
    const row = (id, from, to, type, body) => `## ${id} | from: ${from} | to: ${to} | type: ${type} | 2026-08-24 10:00\n\n${body}\n\n`;
    fs.writeFileSync(busFile, '# messages\n\n' + row(1, E_SEAT, E_SEAT, 'note', 'history — first sight seeds the cursor here'));

    const posted = [];
    const updated = [];
    const reactions = [];
    const unreactions = [];
    // The reaction chain is a promise chain nothing on the handling path awaits (fail-open, by
    // construction), so an assertion made in the same tick would read an empty array and pass for
    // the wrong reason. Every reaction claim below is made AFTER this flush.
    const settleReactions = () => new Promise((r) => setTimeout(r, 5));
    const acksOn = (ts) => reactions.filter((r) => r.ts === ts && r.name === 'white_check_mark');
    let nextTs = 100;
    let nextChan = 1;
    const chans = [];
    const slack = {
      posted,
      postsIn(c) { return posted.filter((q) => q.channel === c); },
      async authTest() { return { ok: true, userId: BOT }; },
      async openDm(userId) { return { ok: true, channel: DM, userId }; },
      async createChannel({ name }) {
        const ch = { id: `C${String(nextChan++).padStart(4, '0')}`, name, is_archived: false };
        chans.push(ch);
        return { ok: true, channel: { id: ch.id, name: ch.name } };
      },
      async listChannels() { return { ok: true, channels: chans.map((c) => ({ id: c.id, name: c.name })), nextCursor: null }; },
      async archiveChannel() { return { ok: true }; },
      async sendToOwner({ channel, threadTs, text }) {
        // A DISTINCT §2.1 `display_suffix` per post: the suffix is the last six digits of the ts,
        // so a fake that reuses them would let "the re-ask minted a FRESH id" pass on two threads
        // that render identically to the owner.
        const ts = `${nextTs}.${String(nextTs++).padStart(6, '0')}`;
        posted.push({ channel, threadTs: threadTs ?? null, text, ts });
        return { delivered: true, ts };
      },
      // The one transport call the ask door REQUIRES — the §3 lead line is stamped by rewriting
      // the message Slack just minted an id for.
      async updateMessage(u) { updated.push(u); const t = posted.find((q) => q.ts === u.ts); if (t) t.text = u.text; return { updated: true }; },
      // The reaction transport (G-second-brain-43-0828-2119). Every call is RECORDED WITH ITS
      // NAME, never counted: ⏳ and ✅ ride the same chain, so a probe that only counted calls
      // could not tell the landed-answer ack apart from the pending marker a fall-through stamps.
      async react({ channel, ts, name }) { reactions.push({ channel, ts, name }); return { reacted: true }; },
      async unreact({ channel, ts, name }) { unreactions.push({ channel, ts, name }); return { reacted: true }; },
      async start() { return { connected: true }; },
      stop() {},
    };
    const eLogs = [];
    const forwarded = [];
    const forwarder = {
      forwarded,
      askOps() { return forwarded.filter((f) => f.intent === 'record-owner-ask').map((f) => f.payload.act); },
      async forward(intent, payload) { forwarded.push({ intent, payload }); return { ok: true, result: { recorded: true, ask_id: payload.thread || null, state: payload.act === 'reap' ? 'closed' : 'open', relaunch: { queued: true } } }; },
      async inspect() { return { ok: true, result: { live_sessions: [], recent_ticks: [] } }; },
    };
    const built = buildBridge({
      gatewayAddr: '127.0.0.1:0',
      bridgeToken: 'stub',
      sessionJobId: 'chat-launch',
      sendMessageJobId: 'send-message',
      workdir: null,
      workspaceRoot: eRoot,
      channelPrefix: 'test-',
      stateFile: path.join(eRoot, 'state.json'),
      busFerry: true,
      busFerryDmUser: OWNER,
      allowlist: [OWNER],
      slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
    }, {
      logger: (e) => eLogs.push(e),
      makeTransport: () => slack,
      forwarderImpl: forwarder,
      replyLegOptions: { pollMs: 3600000 },
      busFerryOptions: { pollMs: 3600000 },
    });
    const bridge = built.bridge;
    await bridge.start();
    const reg = await bridge.registerGoal(E_GOAL);
    await bridge.busFerry.tick();                       // first sight → cursor at tail
    const before = posted.length;

    // E1 — THE PARKING TEST [DoD 4]. A work-content `to: owner` row on a goal with NO
    // `execution-mode` file at all — the fixture that was the guaranteed park under the deleted
    // gate ladder — is posted as a REAL ❓ ASK THREAD.
    fs.appendFileSync(busFile, row(2, E_SEAT, 'owner', 'ask', 'which folder should the draft land in?'));
    await bridge.busFerry.tick();
    const askPost = posted[before];
    const askId = askPost && askPost.ts;
    check('E1 [DoD 4]: a work-content owner-bound bus row is posted as a REAL ❓ ASK THREAD in the goal channel — NEW thread, §3 lead line (fallback subject, this composer is not reshaped in this cluster), and NOT parked',
      posted.length === before + 1 && askPost.channel === reg.channelId && askPost.threadTs === null
      && askPost.text.startsWith(`${MARKER_ASK} NEEDS YOUR ANSWER — ${E_SEAT} needs your answer`)
      && /which folder should the draft land in\?/.test(askPost.text)
      && askPost.text.trim().split('\n').pop() === `ref ${displaySuffix(askId)}`
      && bridge.busFerry._cursors.get(`${E_GOAL}/2026-08-24a`) === 2,
      { head: askPost && askPost.text.split('\n')[0], threadTs: askPost && askPost.threadTs, cursor: bridge.busFerry._cursors.get(`${E_GOAL}/2026-08-24a`) });
    check('E1: the bridge MINTED the ask record through the `record-owner-ask` intent — exactly one open, no reap',
      forwarder.askOps().join(',') === 'open'
      && forwarded.find((f) => f.intent === 'record-owner-ask').payload.thread === askId,
      { ops: forwarder.askOps() });

    // E2 — THE INBOUND DOOR. A reply in the WRONG thread of the SAME channel releases nothing and
    // is not even recognized as an ask reply.
    const wrong = await bridge.onChatMessage({
      chatUserId: OWNER, chatThreadId: `${reg.channelId}:99.9`, text: 'a) yes',
      _channel: reg.channelId, _threadTs: '99.9', _msgTs: '99.91', _inThread: true, _channelType: 'channel',
    });
    check('E2 §2.4.1: an authorized reply in the WRONG thread reaches no ask door at all — no reap, and the ask is still the only record',
      wrong.leg !== 'ask-release' && forwarder.askOps().join(',') === 'open',
      { leg: wrong.leg, ops: forwarder.askOps() });

    // E3 — the RIGHT thread, an UNAUTHORIZED sender: recognized as an ask reply and refused in
    // SILENCE (§2.4.2) — no reap, no NACK, and nothing minted anywhere.
    const postsBeforeStranger = posted.length;
    const stranger = await bridge.onChatMessage({
      chatUserId: STRANGER, chatThreadId: `${reg.channelId}:${askId}`, text: 'a) yes',
      _channel: reg.channelId, _threadTs: askId, _msgTs: '101.1', _inThread: true, _channelType: 'channel',
    });
    await settleReactions();
    check('E3 §2.4.2: the RIGHT thread with an UNAUTHORIZED sender is handled AT the ask door and released NOTHING — no reap, no NACK posted, NO ✅ ack, and it never fell through to a session-create',
      stranger.leg === 'ask-release' && stranger.released === false && stranger.reason === 'unauthorized'
      && posted.length === postsBeforeStranger && forwarder.askOps().join(',') === 'open'
      && acksOn('101.1').length === 0
      && forwarded.every((f) => f.intent === 'record-owner-ask'),
      { reason: stranger.reason, posts: posted.length - postsBeforeStranger, acks: acksOn('101.1').length, intents: forwarded.map((f) => f.intent) });

    // E4 — an UNPARSED first token: the verbatim §4.5 NACK, in the SAME thread, ask still open.
    const nackBefore = posted.length;
    const garbled = await bridge.onChatMessage({
      chatUserId: OWNER, chatThreadId: `${reg.channelId}:${askId}`, text: 'whatever you think best',
      _channel: reg.channelId, _threadTs: askId, _msgTs: '102.1', _inThread: true, _channelType: 'channel',
    });
    const nackPost = posted[nackBefore];
    await settleReactions();
    check('E4 §2.4.3: an UNRECOGNIZED first token posts the verbatim NACK IN THE ASK THREAD through the outbox, the ask stays OPEN, and NO ✅ ack is stamped — a refusal is not a landed answer',
      garbled.released === false && garbled.reason === 'unparsed' && posted.length === nackBefore + 1
      && nackPost.channel === reg.channelId && nackPost.threadTs === askId && nackPost.text === NACK_ASK
      && forwarder.askOps().join(',') === 'open'
      && acksOn('102.1').length === 0,
      { threadTs: nackPost && nackPost.threadTs, ops: forwarder.askOps(), acks: acksOn('102.1').length });

    // E5 — the release itself, through the bridge: reap exactly once, reply on disk.
    const released = await bridge.onChatMessage({
      chatUserId: OWNER, chatThreadId: `${reg.channelId}:${askId}`, text: 'b) the project folder\nand keep the draft',
      _channel: reg.channelId, _threadTs: askId, _msgTs: '103.1', _inThread: true, _channelType: 'channel',
    });
    const dest = replyCopyPath(eRoot, E_GOAL, askId);
    await settleReactions();
    check('E5 §2.4.4/§2.4.5 END TO END: the authorized reply in the exact thread RELEASES through the bridge — reap fires EXACTLY once and the reply is on disk for the relaunched seat',
      released.leg === 'ask-release' && released.released === true && released.outcome === 'b'
      && forwarder.askOps().join(',') === 'open,reap'
      && fs.existsSync(dest) && fs.readFileSync(dest, 'utf8').includes('the project folder'),
      { ops: forwarder.askOps(), outcome: released.outcome, dest });

    // E5a — THE LANDED-ANSWER ACK [G-second-brain-43-0828-2119]. The owner's own message carries
    // exactly one ✅, and it is NOT the ⏳ pending marker: the release leg forwards nothing, so a
    // ⏳ on it would promise an answer that is never coming.
    check('E5a [G-second-brain-43-0828-2119]: the released reply gets EXACTLY ONE ✅ reaction, on the OWNER\'S OWN message ts, in the ask\'s channel — and no ⏳ anywhere on the ask-release leg',
      acksOn('103.1').length === 1
      && acksOn('103.1')[0].channel === reg.channelId
      && reactions.filter((r) => r.name === 'hourglass_flowing_sand' && r.ts === '103.1').length === 0,
      { acks: acksOn('103.1'), allReactions: reactions.map((r) => `${r.name}@${r.ts}`) });

    // E6 — RE-ASK IS FREE [§2.4.5, C-11] and lands in a FRESH thread; and the RELEASED thread stays
    // an ask door that now REFUSES [G-second-brain-43-0828-2119].
    //
    // ⚑ THIS ARM'S SECOND HALF WAS INVERTED ON 2026-08-30, and the inversion is the fix. It used
    // to assert `again.leg !== 'ask-release'` — the released thread was DELETED from the map, so
    // the owner's next message in it was not recognized as an ask reply at all. That is precisely
    // the defect: with no ✅ on the release the owner re-sends, the re-send misses this door, falls
    // through to the goal-channel forward path, and buys a goal-master sitting that reads a bare
    // `a` as a check-in (3× on 2026-08-28, one of them joining a planning roster as a paneless
    // owner door). "Reaps nothing" was true then and is still asserted; what changed is WHERE the
    // message is answered — in its own thread, by this door, instead of out in the channel.
    fs.appendFileSync(busFile, row(3, E_SEAT, 'owner', 'ask', 'and the filename?'));
    await bridge.busFerry.tick();
    const second = posted[posted.length - 1];
    const beforeAgain = posted.length;
    const forwardedBeforeAgain = forwarded.length;
    const again = await bridge.onChatMessage({
      chatUserId: OWNER, chatThreadId: `${reg.channelId}:${askId}`, text: 'a) yes',
      _channel: reg.channelId, _threadTs: askId, _msgTs: '104.1', _inThread: true, _channelType: 'channel',
    });
    const againNack = posted[beforeAgain];
    await settleReactions();
    check('E6 [C-11]: the re-ask opens a FRESH thread with its own id and its own record',
      second.threadTs === null && second.ts !== askId
      && second.text.startsWith(`${MARKER_ASK} NEEDS YOUR ANSWER — ${E_SEAT} needs your answer`)
      && second.text.trim().split('\n').pop() === `ref ${displaySuffix(second.ts)}`,
      { secondHead: second.text.split('\n')[0] });
    check('E6a [G-second-brain-43-0828-2119]: a SECOND authorized reply in the RELEASED thread is still handled at the ask door — `leg: ask-release`, refused as already-answered, and NOTHING was reaped a second time',
      again.leg === 'ask-release' && again.alreadyAnswered === true && again.released === false
      && again.reason === 'no-reap'
      && forwarder.askOps().join(',') === 'open,reap,open',
      { leg: again.leg, reason: again.reason, alreadyAnswered: again.alreadyAnswered, ops: forwarder.askOps() });
    check('E6b [G-second-brain-43-0828-2119]: it is answered by EXACTLY ONE in-thread NACK naming the outcome already recorded — and nothing was forwarded, enqueued or session-created for it',
      posted.length === beforeAgain + 1
      && againNack.channel === reg.channelId && againNack.threadTs === askId
      && /already answered/.test(againNack.text) && againNack.text.includes('`b`')
      && again.forwarded === false
      && forwarded.length === forwardedBeforeAgain
      && forwarded.every((f) => f.intent === 'record-owner-ask'),
      { posts: posted.length - beforeAgain, nack: againNack && againNack.text, newIntents: forwarded.length - forwardedBeforeAgain });
    check('E6c: the second reply gets NO second ✅ and no ⏳ — the ack belongs to the reply that actually released, and nothing is pending for a message that goes nowhere',
      acksOn('104.1').length === 0
      && reactions.filter((r) => r.ts === '104.1').length === 0,
      { reactionsOn104: reactions.filter((r) => r.ts === '104.1') });

    // E7 — [T2-R14] AT THE WIRED DOOR, UPDATED FOR `d-escalation-surface` part 7 (seat
    // `esc-door-split`). A seat that declares nothing is still REFUSED as an ASK — no ❓ thread, no
    // record minted, [T2-R14] unreversed and unweakened — but the row is `to: owner`, so it is
    // never silently discarded any more: the SAME door rescues it as a 💭 NOTICE
    // (`ask-thread.js#postNote`, which never checks [T2-R14] and mints no record). `forwarder
    // .askOps()` is the exact-record proof: it names every `record-owner-ask` open/reap the
    // gateway saw, and the notice adds NONE — `open,reap,open` stays `open,reap,open` after row 4.
    //
    // Was (quoted verbatim, pre-fix — the claim this replaces): "an UNDESIGNATED seat is REFUSED at
    // the ask door — nothing posted on any surface and no record minted", asserting
    // `posted.length === beforeSilent` (literally zero posts) and a `REFUSED at the ask door` log
    // line. Both are now WRONG on purpose: `d-escalation-surface` explicitly ruled that class of
    // silence closed (measured cost: the daemon's own seed-refusal notice could never post).
    //
    // ⚑ STILL NOT A PARK, unchanged: a park advances the cursor and posts nothing, telling nobody.
    // Here the cursor advances BECAUSE the row was actually delivered (as a notice), not because it
    // was swallowed — the distinction is the notice thread existing at all.
    const beforeSilent = posted.length;
    const cursorBefore = bridge.busFerry._cursors.get(`${E_GOAL}/2026-08-24a`);
    const askOpsBefore = forwarder.askOps().join(',');
    fs.appendFileSync(busFile, row(4, 'silent', 'owner', 'ask', 'an undesignated seat asking'));
    await bridge.busFerry.tick();
    const rescued = eLogs.filter((l) => /rescued as a 💭 notice/.test(l.message));
    const noticePost = posted[posted.length - 1];
    check('E7 [T2-R14]: an UNDESIGNATED seat\'s ASK is refused (no record minted — `askOps()` '
      + 'unchanged) and RESCUED as a 💭 NOTICE — a new thread posts, the refusal is logged by name, '
      + 'and the row is not a park (the cursor advances because it WAS delivered)',
      posted.length === beforeSilent + 1
      && noticePost && noticePost.text.startsWith(`${MARKER_NOTE} `)
      && forwarder.askOps().join(',') === askOpsBefore
      && rescued.length === 1 && rescued[0].from === 'silent'
      && bridge.busFerry._cursors.get(`${E_GOAL}/2026-08-24a`) === cursorBefore + 1
      && eLogs.every((l) => !/PARK/i.test(l.message)),
      {
        posts: posted.length - beforeSilent, noticeHead: noticePost && noticePost.text.split('\n')[0],
        rescued: rescued.length, askOpsBefore, askOpsAfter: forwarder.askOps().join(','),
        cursorBefore, cursorAfter: bridge.busFerry._cursors.get(`${E_GOAL}/2026-08-24a`),
      });

    // E8 — PERSISTENCE. The ask-thread map is in the state file and survives a restart, or the
    // owner's answer after one lands as ordinary goal traffic and the ask is never released.
    const openThreadTs = second.ts;
    bridge.stop();
    const doc = JSON.parse(fs.readFileSync(path.join(eRoot, 'state.json'), 'utf8'));
    const rebuilt = buildBridge({
      gatewayAddr: '127.0.0.1:0', bridgeToken: 'stub', sessionJobId: 'chat-launch', sendMessageJobId: 'send-message',
      workdir: null, workspaceRoot: eRoot, channelPrefix: 'test-', stateFile: path.join(eRoot, 'state.json'),
      busFerry: true, busFerryDmUser: OWNER, allowlist: [OWNER],
      slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
    }, { logger: () => {}, makeTransport: () => slack, forwarderImpl: forwarder, replyLegOptions: { pollMs: 3600000 }, busFerryOptions: { pollMs: 3600000 } });
    await rebuilt.bridge.start();
    const afterRestart = await rebuilt.bridge.onChatMessage({
      chatUserId: OWNER, chatThreadId: `${reg.channelId}:${openThreadTs}`, text: 'a) draft.md',
      _channel: reg.channelId, _threadTs: openThreadTs, _msgTs: '105.1', _inThread: true, _channelType: 'channel',
    });
    check('E8: the ask-thread map is PERSISTED (version 1, additive) and restored — the owner\'s answer AFTER A RESTART still releases the ask it belongs to',
      doc.version === 1 && doc.askThreads && Object.keys(doc.askThreads).length === 2
      && afterRestart.leg === 'ask-release' && afterRestart.released === true
      && forwarder.askOps().join(',') === 'open,reap,open,reap',
      { version: doc.version, persisted: doc.askThreads && Object.keys(doc.askThreads), ops: forwarder.askOps() });

    // E8a — THE RELEASED MARKER MAKES THE ROUND TRIP [G-second-brain-43-0828-2119]. The state
    // loader whitelists the fields it restores, so a marker written but not read would be lost at
    // the exact moment it matters most: the bridge is a systemd unit with Restart=on-failure, and
    // a restart between the owner's answer and their re-send is the ordinary case, not the exotic
    // one. Asserted on disk AND through the restored bridge's behaviour.
    const releasedKey = `${reg.channelId}:${askId}`;
    const onDisk = doc.askThreads[releasedKey];
    const afterRestartAgain = await rebuilt.bridge.onChatMessage({
      chatUserId: OWNER, chatThreadId: releasedKey, text: 'a) yes again',
      _channel: reg.channelId, _threadTs: askId, _msgTs: '106.1', _inThread: true, _channelType: 'channel',
    });
    check('E8a [G-second-brain-43-0828-2119]: the RELEASED entry survives the state round trip carrying its marker and its recorded outcome, and the restarted bridge still refuses a reply in that thread in-thread — never forwarding it',
      Boolean(onDisk) && onDisk.released === true && onDisk.outcome === 'b'
      && typeof onDisk.releasedAt === 'number'
      && afterRestartAgain.leg === 'ask-release' && afterRestartAgain.alreadyAnswered === true
      && afterRestartAgain.forwarded === false
      && forwarder.askOps().join(',') === 'open,reap,open,reap',
      { onDisk, leg: afterRestartAgain.leg, ops: forwarder.askOps() });

    // E9 — THE REPLAY, END TO END THROUGH THE REAL BRIDGE (`d-escalation-surface` acceptance bar):
    // an ESCALATION from the SAME non-designated `silent` seat that E7 just proved gets REFUSED as
    // an ordinary ask — admitted regardless of designation, rendered with the ruled post shape
    // (part 9: ❓ + decision + TLDR + alternatives on top, full reasoning + evidence pointer as the
    // FIRST THREADED REPLY), and its thread_ts is the ask id, unmoved.
    const beforeE9 = posted.length;
    const askOpsBeforeE9 = forwarder.askOps().join(',');
    fs.appendFileSync(busFile, row(5, 'silent', 'owner', 'escalation', [
      'the cage refuses the write and nobody in this run can widen it',
      '',
      'TLDR: two ways to unblock it, both change the sandbox policy.',
      '',
      'a) widen the grant — fast, touches the sandbox policy',
      'b) move the file — slower, no policy change',
      'Recommend (a).',
      '',
      'Reasoning:',
      'the full trace, step by step — see the evidence file for all of it.',
      'evidence: /tmp/evidence/e9-trace.log',
    ].join('\n')));
    await rebuilt.bridge.busFerry.tick();
    const e9Top = posted[beforeE9];
    const e9Reply = posted[beforeE9 + 1];
    check('E9 [d-escalation-surface parts 1+9]: an escalation from a NON-designated seat is ADMITTED (mints a new record) and posts TWO messages — a TOP-LEVEL ❓ + decision + TLDR + alternatives, and a FIRST THREADED REPLY carrying the full reasoning + evidence pointer, on the SAME thread_ts as the ask id',
      posted.length === beforeE9 + 2
      && forwarder.askOps().join(',') === `${askOpsBeforeE9},open`
      && e9Top && e9Top.threadTs === null && e9Top.text.startsWith(`${MARKER_ASK} `)
      && e9Top.text.includes('TLDR:') && e9Top.text.includes('Recommend (a)')
      && !e9Top.text.includes('Reasoning:') && !e9Top.text.includes('e9-trace.log')
      && e9Reply && e9Reply.threadTs === e9Top.ts && e9Reply.text.includes('Reasoning:')
      && e9Reply.text.includes('e9-trace.log'),
      {
        posts: posted.length - beforeE9, askOps: forwarder.askOps().join(','),
        topHead: e9Top && e9Top.text.split('\n')[0], topTs: e9Top && e9Top.ts,
        replyThreadTs: e9Reply && e9Reply.threadTs, replyIncludesReasoning: e9Reply && e9Reply.text.includes('Reasoning:'),
      });

    rebuilt.bridge.stop();
  }

  // ── R-A1: THE CHANNEL-LESS FALLBACK (`d-owner-ask-shape`, `chat-bridge.js#postOwnerAsk`) ──────
  //
  // A recovery/goal-disposition ask for a goal with NO Slack channel used to log a `warn` and
  // retry forever — the owner was told NOTHING (`inv-ask-paths` Held-but-dropped #1). It now posts
  // the SAME shaped ask straight into `#system-channel`, the goal name prefixed to the subject so
  // the owner can tell whose ask it is without a channel to place it in.
  {
    const fRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ask-release-fallback-'));
    const F_GOAL = 'no-channel-goal';
    const posted = [];
    let nextTs = 9000;
    const chans = [];
    let nextChan = 1;
    const slack = {
      async authTest() { return { ok: true, userId: BOT }; },
      async openDm(userId) { return { ok: true, channel: DM, userId }; },
      async createChannel({ name }) { const ch = { id: `CF${String(nextChan++).padStart(4, '0')}`, name }; chans.push(ch); return { ok: true, channel: ch }; },
      async listChannels() { return { ok: true, channels: chans, nextCursor: null }; },
      async archiveChannel() { return { ok: true }; },
      async sendToOwner({ channel, threadTs, text }) {
        const ts = `${nextTs}.${String(nextTs++).padStart(6, '0')}`;
        posted.push({ channel, threadTs: threadTs ?? null, text, ts });
        return { delivered: true, ts };
      },
      async updateMessage(u) { const t = posted.find((q) => q.ts === u.ts); if (t) t.text = u.text; return { updated: true }; },
      async react() { return { reacted: true }; },
      async unreact() { return { reacted: true }; },
      async start() { return { connected: true }; },
      stop() {},
    };
    const forwarder = {
      async forward(intent, payload) { return { ok: true, result: { recorded: true, ask_id: payload.thread || null, state: 'open' } }; },
      async inspect() { return { ok: true, result: { live_sessions: [], recent_ticks: [] } }; },
    };
    const built = buildBridge({
      gatewayAddr: '127.0.0.1:0', bridgeToken: 'stub', sessionJobId: 'chat-launch', sendMessageJobId: 'send-message',
      workdir: null, workspaceRoot: fRoot, channelPrefix: 'test-', stateFile: path.join(fRoot, 'state.json'),
      busFerry: false, allowlist: [OWNER],
      // R-A1's own target — the daemon-wide alarm/system channel, injected exactly as
      // `chat/index.js:103` wires it from `config.systemChannelId`.
      systemChannelId: 'C-SYSTEM',
      slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
    }, {
      logger: () => {}, makeTransport: () => slack, forwarderImpl: forwarder,
      replyLegOptions: { pollMs: 3600000 }, busFerryOptions: { pollMs: 3600000 },
    });
    await built.bridge.start();
    // F_GOAL is deliberately NEVER `registerGoal`'d — `resolveChannel` answers null, same as a
    // genuinely channel-less goal.
    const out = await built.bridge.postOwnerAsk({
      goalId: F_GOAL, seatName: 'leader', label: 'recovery', kind: 'recovery',
      body: 'What happened: the leader keeps failing.\nQuestion: what should I do?',
      subject: 'the leader seat keeps failing to start',
    });
    const landed = posted.find((p) => p.ts === out.askId);
    check('R-A1 a recovery ask for a CHANNEL-LESS goal posts into the system channel instead of {posted:false}+retry-forever',
      out.posted === true && !!landed && landed.channel === 'C-SYSTEM',
      { posted: out.posted, channel: landed && landed.channel });
    check('R-A1 the subject carries the GOAL NAME prefix (`<goal>: <subject>`) so the owner can tell whose ask it is with no channel to place it in',
      !!landed && landed.text.startsWith(`${MARKER_ASK} NEEDS YOUR ANSWER — ${F_GOAL}: the leader seat keeps failing to start`),
      { head: landed && landed.text.split('\n')[0] });
    check('R-A1 the SAME shaped ask — body + `ref <suffix>` — not a stripped-down alarm',
      !!landed && landed.text.includes('What happened:')
      && landed.text.trim().split('\n').pop() === `ref ${displaySuffix(out.askId)}`,
      { text: landed && landed.text });

    // An ORDINARY ask (not recovery/goal-disposition) on the SAME channel-less goal is UNCHANGED —
    // R-A1 is scoped to the two daemon-decided kinds, never a seat's own traffic.
    const beforeOrdinary = posted.length;
    const ordinaryOut = await built.bridge.postOwnerAsk({
      goalId: F_GOAL, seatName: 'leader', label: 'work-content', kind: 'ordinary', body: 'anything',
    });
    check('R-A1 scope limit: an ORDINARY ask on the same channel-less goal still gets {posted:false} — the fallback never widens past recovery/goal-disposition',
      ordinaryOut.posted === false && posted.length === beforeOrdinary,
      { posted: ordinaryOut.posted, newPosts: posted.length - beforeOrdinary });

    built.bridge.stop();
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
