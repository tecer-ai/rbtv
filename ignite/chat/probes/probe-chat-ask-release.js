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
  createAskThreads, openingLine, displaySuffix, replyCopyPath, MARKER_ASK, MARKER_NOTE,
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
    check('E1 [DoD 4]: a work-content owner-bound bus row is posted as a REAL ❓ ASK THREAD in the goal channel — NEW thread, §3 lead line, and NOT parked',
      posted.length === before + 1 && askPost.channel === reg.channelId && askPost.threadTs === null
      && askPost.text.startsWith(`${MARKER_ASK} ${displaySuffix(askId)} · ${E_SEAT} · work-content`)
      && /which folder should the draft land in\?/.test(askPost.text)
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
    check('E3 §2.4.2: the RIGHT thread with an UNAUTHORIZED sender is handled AT the ask door and released NOTHING — no reap, no NACK posted, and it never fell through to a session-create',
      stranger.leg === 'ask-release' && stranger.released === false && stranger.reason === 'unauthorized'
      && posted.length === postsBeforeStranger && forwarder.askOps().join(',') === 'open'
      && forwarded.every((f) => f.intent === 'record-owner-ask'),
      { reason: stranger.reason, posts: posted.length - postsBeforeStranger, intents: forwarded.map((f) => f.intent) });

    // E4 — an UNPARSED first token: the verbatim §4.5 NACK, in the SAME thread, ask still open.
    const nackBefore = posted.length;
    const garbled = await bridge.onChatMessage({
      chatUserId: OWNER, chatThreadId: `${reg.channelId}:${askId}`, text: 'whatever you think best',
      _channel: reg.channelId, _threadTs: askId, _msgTs: '102.1', _inThread: true, _channelType: 'channel',
    });
    const nackPost = posted[nackBefore];
    check('E4 §2.4.3: an UNRECOGNIZED first token posts the verbatim NACK IN THE ASK THREAD through the outbox and the ask stays OPEN',
      garbled.released === false && garbled.reason === 'unparsed' && posted.length === nackBefore + 1
      && nackPost.channel === reg.channelId && nackPost.threadTs === askId && nackPost.text === NACK_ASK
      && forwarder.askOps().join(',') === 'open',
      { threadTs: nackPost && nackPost.threadTs, ops: forwarder.askOps() });

    // E5 — the release itself, through the bridge: reap exactly once, reply on disk.
    const released = await bridge.onChatMessage({
      chatUserId: OWNER, chatThreadId: `${reg.channelId}:${askId}`, text: 'b) the project folder\nand keep the draft',
      _channel: reg.channelId, _threadTs: askId, _msgTs: '103.1', _inThread: true, _channelType: 'channel',
    });
    const dest = replyCopyPath(eRoot, E_GOAL, askId);
    check('E5 §2.4.4/§2.4.5 END TO END: the authorized reply in the exact thread RELEASES through the bridge — reap fires EXACTLY once and the reply is on disk for the relaunched seat',
      released.leg === 'ask-release' && released.released === true && released.outcome === 'b'
      && forwarder.askOps().join(',') === 'open,reap'
      && fs.existsSync(dest) && fs.readFileSync(dest, 'utf8').includes('the project folder'),
      { ops: forwarder.askOps(), outcome: released.outcome, dest });

    // E6 — RE-ASK IS FREE [§2.4.5, C-11] and lands in a FRESH thread, and the released thread is
    // no longer an ask door: a second answer in it releases nothing twice.
    fs.appendFileSync(busFile, row(3, E_SEAT, 'owner', 'ask', 'and the filename?'));
    await bridge.busFerry.tick();
    const second = posted[posted.length - 1];
    const again = await bridge.onChatMessage({
      chatUserId: OWNER, chatThreadId: `${reg.channelId}:${askId}`, text: 'a) yes',
      _channel: reg.channelId, _threadTs: askId, _msgTs: '104.1', _inThread: true, _channelType: 'channel',
    });
    check('E6 [C-11]: the re-ask opens a FRESH thread with its own id and its own record, and the RELEASED thread has stopped being an ask door — a second answer in it reaps nothing',
      second.threadTs === null && second.ts !== askId
      && second.text.startsWith(`${MARKER_ASK} ${displaySuffix(second.ts)} · ${E_SEAT} · work-content`)
      && forwarder.askOps().join(',') === 'open,reap,open'
      && again.leg !== 'ask-release',
      { ops: forwarder.askOps(), secondHead: second.text.split('\n')[0], againLeg: again.leg });

    // E7 — [T2-R14] AT THE WIRED DOOR. A seat that declares nothing is REFUSED at send: no ❓
    // thread, no record, and — the ruling's point — the row does NOT reach the owner by some
    // other leg either, because a refusal that falls through to the agent thread is not a refusal.
    //
    // ⚑ AND IT IS STILL NOT A PARK, which is the distinction this check exists to hold. A park
    // ADVANCED THE CURSOR and told nobody: the row was gone. A refusal leaves the cursor where it
    // was — the row is held and retried, exactly like a missing channel — and it is REPORTED in
    // the log, naming the seat and the ruling. Both halves are asserted, because "nothing was
    // posted" alone reads identically to the behaviour that was deleted.
    const beforeSilent = posted.length;
    const cursorBefore = bridge.busFerry._cursors.get(`${E_GOAL}/2026-08-24a`);
    fs.appendFileSync(busFile, row(4, 'silent', 'owner', 'ask', 'an undesignated seat asking'));
    await bridge.busFerry.tick();
    const refusal = eLogs.filter((l) => /REFUSED at the ask door/.test(l.message));
    check('E7 [T2-R14]: an UNDESIGNATED seat is REFUSED at the ask door — nothing posted on any surface and no record minted — and the refusal is NOT a park: it is logged naming the seat, and the cursor does not sweep the row away',
      posted.length === beforeSilent
      && forwarder.askOps().join(',') === 'open,reap,open'
      && refusal.length === 1 && refusal[0].from === 'silent'
      && bridge.busFerry._cursors.get(`${E_GOAL}/2026-08-24a`) === cursorBefore
      && eLogs.every((l) => !/PARK/i.test(l.message)),
      { posts: posted.length - beforeSilent, refusals: refusal.length, cursorBefore, cursorAfter: bridge.busFerry._cursors.get(`${E_GOAL}/2026-08-24a`), ops: forwarder.askOps() });

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
      doc.version === 1 && doc.askThreads && Object.keys(doc.askThreads).length === 1
      && afterRestart.leg === 'ask-release' && afterRestart.released === true
      && forwarder.askOps().join(',') === 'open,reap,open,reap',
      { version: doc.version, persisted: doc.askThreads && Object.keys(doc.askThreads), ops: forwarder.askOps() });
    rebuilt.bridge.stop();
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
