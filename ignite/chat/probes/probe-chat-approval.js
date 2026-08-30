'use strict';

// probe-chat-approval — the approval thread: its §3 first message and its §4.2 post-parse
// dispatch (`spec-owner-io.md`), law `DESIGN-BASELINE.md` v2 §Planning approval rows
// [T5-R5, T3-R20, T3-R21, T3-R22, D12, D-5-ruling, C-16, CF-7].
//
// NO SLACK AND NO DAEMON. The transport and the gateway forwarder are fakes, and every effect an
// approval outcome ultimately has — materialize, close, pause, relaunch — has its CALLS COUNTED.
// That counting is the point: [D-5-ruling] is not "approve usually works in the right place", it
// is "the D12 path fires exactly once, and only from a genuine approval thread". A probe that only
// asserted the happy path would pass on a bridge where `approve` in any thread started an
// execution goal.
//
// ⚑ D12 IS COUNTED AT THE GATEWAY, NOT AT A PORT, since the fourteenth intent landed (owner
// ruling 2026-08-24, option (b)). `materialize` is no longer injectable — `chat-bridge.js` builds
// it from the forwarder and REFUSES an injected one — so the D12 counter here is the fake
// forwarder's `start-execution` log. That is deliberate: counting a stub port would prove the
// bridge calls a function, and what [D-5-ruling] needs proven is that it crosses the daemon
// boundary as an authenticated intent, exactly once, carrying the bound commit. The other three
// ports are still injected, because their intents were deliberately not minted.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const {
  createApprovalDispatch, composeApprovalBody, IRREVERSIBLE_PHRASE, APPROVAL_TOKEN_LINE, PAUSE_EXITS,
} = require('../approval-thread');
const { buildBridge } = require('../index');

const OUT = path.join(__dirname, 'probe-chat-approval.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence: evidence || {} }); };

const OWNER = 'U-OWNER';
const BOT = 'U-BOT';
const GOAL = 'approval-goal';
const SEAT = 'verify-seat';
const COMMIT = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678';

// ── The bridge harness (mock Socket-Mode transport + fake gateway forwarder) ──────────────────
function harness(extraApprovalPorts = null) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'approval-'));
  const goalDir = path.join(root, '.rbtv', 'goals', GOAL);
  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.mkdirSync(path.join(goalDir, 'seats', SEAT), { recursive: true });
  fs.writeFileSync(path.join(goalDir, 'seats', SEAT, 'seat.md'),
    `---\nseat: ${SEAT}\nhuman-interactive: yes\nfallback: block-and-queue\n---\nbody\n`);

  const posted = [];
  let nextTs = 700;
  let nextChan = 1;
  const chans = [];
  const slack = {
    posted,
    async authTest() { return { ok: true, userId: BOT }; },
    async openDm(userId) { return { ok: true, channel: 'D_OWNER', userId }; },
    async createChannel({ name }) { const ch = { id: `C${String(nextChan++).padStart(4, '0')}`, name }; chans.push(ch); return { ok: true, channel: ch }; },
    async listChannels() { return { ok: true, channels: chans, nextCursor: null }; },
    async archiveChannel() { return { ok: true }; },
    async sendToOwner({ channel, threadTs, text }) {
      const ts = `${nextTs}.${String(nextTs++).padStart(6, '0')}`;
      posted.push({ channel, threadTs: threadTs ?? null, text, ts });
      return { delivered: true, ts };
    },
    async updateMessage(u) { const t = posted.find((q) => q.ts === u.ts); if (t) t.text = u.text; return { updated: true }; },
    async start() { return { connected: true }; },
    stop() {},
  };
  // The four counters. `materialize` is counted where it now happens — on the wire, as the
  // fourteenth intent — and the other three on their still-injected ports. `materializeOk`
  // decides whether the DAEMON says the birth happened; the [C-16] failure post-back is measured
  // on the same path, not on a second fixture.
  const calls = { materialize: [], closeGoal: [], pauseGoal: [], relaunchDraftVerify: [] };
  let materializeOk = true;
  const forwarder = {
    async forward(intent, payload, opts) {
      if (intent === 'start-execution') {
        calls.materialize.push({ payload, opts: opts || null });
        return materializeOk
          ? { ok: true, result: { started: true, execution_goal: 'exec-goal-1', goal: payload.goal, thread: payload.thread, commit: payload.commit } }
          : { ok: true, result: { started: false, reason: 'materialize-failed', detail: 'commit collision on planning/current', record: { code: 'lock-collision' } } };
      }
      return { ok: true, result: { recorded: true, ask_id: payload.thread || null, state: payload.act === 'reap' ? 'closed' : 'open', relaunch: { queued: true } } };
    },
    async inspect() { return { ok: true, result: { live_sessions: [], recent_ticks: [] } }; },
  };
  const approvalPorts = {
    closeGoal: async (a) => { calls.closeGoal.push(a); return { ok: true }; },
    pauseGoal: async (a) => { calls.pauseGoal.push(a); return { ok: true }; },
    relaunchDraftVerify: async (a) => { calls.relaunchDraftVerify.push(a); return { ok: true }; },
  };
  const built = buildBridge({
    gatewayAddr: '127.0.0.1:0', bridgeToken: 'stub', sessionJobId: 'chat-launch', sendMessageJobId: 'send-message',
    workdir: null, workspaceRoot: root, channelPrefix: 'test-', stateFile: path.join(root, 'state.json'),
    busFerry: false, allowlist: [OWNER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  }, {
    logger: () => {}, makeTransport: () => slack, forwarderImpl: forwarder,
    replyLegOptions: { pollMs: 3600000 }, busFerryOptions: { pollMs: 3600000 },
    approvalPorts: extraApprovalPorts ? { ...approvalPorts, ...extraApprovalPorts } : approvalPorts,
  });
  return {
    root, slack, posted, calls, built, bridge: built.bridge,
    setMaterialize(ok) { materializeOk = ok; },
    reply(channel, threadTs, text, user = OWNER) {
      return built.bridge.onChatMessage({
        chatUserId: user, chatThreadId: `${channel}:${threadTs}`, text,
        _channel: channel, _threadTs: threadTs, _msgTs: `${Date.now()}.1`, _inThread: true, _channelType: 'channel',
      });
    },
  };
}

const harnessWith = (ports) => harness(ports);

(async () => {
  // ── A. THE §3 APPROVAL FIRST MESSAGE ────────────────────────────────────────────────────────
  {
    const body = composeApprovalBody({
      goalName: 'stools-canvas-audio-elevenlabs',
      digest: '3 milestones · 7 seats · 2 interactive seats · 1 credential-resolve · no red flags',
      commitId: COMMIT,
    });
    const lines = body.split('\n');
    check('A1: the GOAL NAME is its OWN BOLD LEAD LINE — first line of the body, nothing else on it [D-5-ruling]',
      lines[0] === '*GOAL: stools-canvas-audio-elevenlabs*', { line: lines[0] });
    check('A2: the IRREVERSIBLE EFFECT is its OWN BOLD LEAD LINE, second, and says execution starts',
      lines[1] === `*IRREVERSIBLE: ${IRREVERSIBLE_PHRASE}*` && /execution/.test(lines[1]), { line: lines[1] });
    check('A3: the BOUND COMMIT is in the body [T5-R5] — an approval that names no commit approves whatever the tree holds later',
      body.includes(`Bound commit: \`${COMMIT}\``), { has: body.includes(COMMIT) });
    check('A4: the ACCEPTED TOKENS are published in the body — all six, so the owner never has to remember the vocabulary',
      body.includes(APPROVAL_TOKEN_LINE)
      && ['approve', 'reject-and-close', 'reject-and-pause', 'reject-and-retry', 'retry with:', 'close'].every((t) => body.includes(t)),
      { tokenLine: APPROVAL_TOKEN_LINE });
    check('A5: the composer REFUSES a body with no commit id rather than posting an unbound approval [T5-R5]',
      (() => { try { composeApprovalBody({ goalName: 'g', digest: 'd' }); return false; } catch { return true; } })(), {});
  }

  // ── B. THE `kind` FORK: `approve` IS D12 ONLY IN A GENUINE APPROVAL THREAD ───────────────────
  {
    const h = harness();
    await h.bridge.start();
    const reg = await h.bridge.registerGoal(GOAL);

    const approval = await h.bridge.postOwnerAsk({
      goalId: GOAL, seatName: SEAT, kind: 'approval', commitId: COMMIT,
      body: composeApprovalBody({ goalName: GOAL, digest: '2 milestones · 4 seats', commitId: COMMIT }),
    });
    const ordinary = await h.bridge.postOwnerAsk({ goalId: GOAL, seatName: SEAT, body: 'Which binder?\n\na) keep\nb) rewrite' });

    // B1. The same word, in the ORDINARY thread, first — so a later pass cannot be explained by
    // ordering. It must be delivered to the seat and must NOT reach the D12 port.
    const b1 = await h.reply(reg.channelId, ordinary.askId, 'approve — go ahead');
    check('B1: bare `approve` in a NON-approval thread is delivered to the seat and NEVER fires D12 [D-5-ruling, CF-7]',
      b1.leg === 'ask-release' && b1.released === true && b1.outcome === 'approve'
      && !b1.approval && h.calls.materialize.length === 0,
      { released: b1.released, outcome: b1.outcome, materializeCalls: h.calls.materialize.length });

    // B2. The same word, in the APPROVAL thread. Exactly one D12 call, carrying the bound commit.
    const b2 = await h.reply(reg.channelId, approval.askId, 'approve');
    check('B2: bare `approve` in a genuine approval thread fires the D12 path EXACTLY ONCE, bound to the approval\'s commit [D12, T5-R5]',
      b2.approval === true && b2.dispatched.action === 'materialize' && b2.dispatched.ok === true
      && h.calls.materialize.length === 1 && h.calls.materialize[0].payload.commit === COMMIT
      && h.calls.materialize[0].payload.thread === approval.askId,
      { action: b2.dispatched && b2.dispatched.action, calls: h.calls.materialize });

    // THE CROSSING ITSELF. The bridge holds no child process, so D12 is only real if it left this
    // process as the fourteenth intent — naming the planning goal, the approval thread and the
    // bound commit, and NOTHING else (the payload schema is closed at the gateway, so a comments
    // field would be a refusal, not an ignored key).
    const sent = h.calls.materialize[0];
    check('B2b: D12 crossed the daemon boundary as the `start-execution` intent carrying goal + thread + commit and no other key [owner ruling 2026-08-24 (b)]',
      JSON.stringify(Object.keys(sent.payload).sort()) === JSON.stringify(['commit', 'goal', 'thread'])
      && sent.payload.goal === GOAL
      && Number(sent.opts && sent.opts.timeoutMs) > 10000,
      { payload: sent.payload, opts: sent.opts });

    // B3. The thread is finished, so a second `approve` cannot re-fire D12.
    //
    // ⚑ HOW that is achieved changed on 2026-08-30 [G-second-brain-43-0828-2119], and the claim
    // this arm exists for did not. It used to be achieved by FORGETTING the thread: the entry was
    // deleted, so the second `approve` was not recognized as an ask reply at all — and therefore
    // fell through to the goal-channel forward path, which is what was buying an unasked-for
    // goal-master sitting on every owner re-send. It is now achieved by REMEMBERING the thread and
    // refusing in it. `materialize.length === 1` is the safety property and is unchanged; what is
    // asserted additionally is that the refusal happens AT the ask door and stays in the thread.
    const b3 = await h.reply(reg.channelId, approval.askId, 'approve');
    check('B3: the approval thread is CLOSED after materialize — a repeated `approve` in it cannot fire D12 a second time, and it is refused IN THE THREAD rather than falling through to the goal channel',
      h.calls.materialize.length === 1
      && b3.leg === 'ask-release' && b3.alreadyAnswered === true && b3.forwarded === false,
      { materializeCalls: h.calls.materialize.length, leg: b3.leg, alreadyAnswered: b3.alreadyAnswered });
    h.bridge.stop();
  }

  // ── C. THE FOUR REJECT OUTCOMES AND `close` (§4.2) ───────────────────────────────────────────
  {
    const h = harness();
    await h.bridge.start();
    const reg = await h.bridge.registerGoal(GOAL);
    const open = async () => h.bridge.postOwnerAsk({
      goalId: GOAL, seatName: SEAT, kind: 'approval', commitId: COMMIT,
      body: composeApprovalBody({ goalName: GOAL, digest: 'digest', commitId: COMMIT }),
    });

    const a = await open();
    const rc = await h.reply(reg.channelId, a.askId, 'reject-and-close  not this plan');
    check('C1: `reject-and-close` closes the planning goal and ends the thread — no materialize',
      rc.dispatched.action === 'close' && rc.dispatched.done === true
      && h.calls.closeGoal.length === 1 && h.calls.materialize.length === 0, { d: rc.dispatched });

    const b = await open();
    const rr = await h.reply(reg.channelId, b.askId, 'reject-and-retry\nseat count is wrong\nno credential-resolve step');
    check('C2: `reject-and-retry` relaunches draft + verify ONLY, and the comments arrive as the FINDINGS LIST [T3-R21]',
      rr.dispatched.action === 'retry' && h.calls.relaunchDraftVerify.length === 1
      && h.calls.relaunchDraftVerify[0].findings.length === 2
      && h.calls.relaunchDraftVerify[0].findings[0] === 'seat count is wrong'
      && h.calls.materialize.length === 0,
      { findings: h.calls.relaunchDraftVerify[0] && h.calls.relaunchDraftVerify[0].findings });

    const c = await open();
    const rw = await h.reply(reg.channelId, c.askId, 'retry with: drop the canvas seat');
    check('C3: `retry with:` dispatches the same way as reject-and-retry when comments are present [§4.2]',
      rw.dispatched.action === 'retry' && h.calls.relaunchDraftVerify.length === 2
      && h.calls.relaunchDraftVerify[1].findings[0] === 'drop the canvas seat', { d: rw.dispatched });

    const d = await open();
    const cl = await h.reply(reg.channelId, d.askId, 'close');
    check('C4: `close` drops the approval and ends the thread',
      cl.dispatched.action === 'close' && cl.dispatched.done === true && h.calls.closeGoal.length === 2, { d: cl.dispatched });
    h.bridge.stop();
  }

  // ── D. `reject-and-pause` AND ITS THREE KEYS [T3-R22] ────────────────────────────────────────
  {
    const h = harness();
    await h.bridge.start();
    const reg = await h.bridge.registerGoal(GOAL);
    const a = await h.bridge.postOwnerAsk({
      goalId: GOAL, seatName: SEAT, kind: 'approval', commitId: COMMIT,
      body: composeApprovalBody({ goalName: GOAL, digest: 'digest', commitId: COMMIT }),
    });
    const rp = await h.reply(reg.channelId, a.askId, 'reject-and-pause  come back to this next week');
    const entry = h.bridge._askThreads.get(`${reg.channelId}:${a.askId}`);
    check('D1: `reject-and-pause` pauses the planning goal and KEEPS the thread — it is now the only door out [T3-R22]',
      rp.dispatched.action === 'reject-and-pause' && rp.dispatched.done === false && rp.dispatched.paused === true
      && h.calls.pauseGoal.length === 1 && entry && entry.paused === true,
      { d: rp.dispatched, entry });

    // A recognized token that is NOT one of the three keys changes nothing and is ANSWERED
    // (silence here would rebuild [F-owner-ux-2]).
    const beforeCalls = JSON.stringify(h.calls);
    const notExit = await h.reply(reg.channelId, a.askId, 'b) the other option');
    const said = h.slack.posted.filter((p) => p.threadTs === a.askId).map((p) => p.text).join('\n');
    check('D2: inside the pause, a recognized token that is NOT one of the three keys exits NOTHING, calls no port, and says so in-thread',
      notExit.dispatched.action === 'not-an-exit' && JSON.stringify(h.calls) === beforeCalls
      && PAUSE_EXITS.every((t) => said.includes(t)),
      { action: notExit.dispatched.action, said });

    // KEY 1 — `retry with:` is a named exit: it relaunches and leaves the pause.
    const k1 = await h.reply(reg.channelId, a.askId, 'retry with: fewer seats');
    const afterRetry = h.bridge._askThreads.get(`${reg.channelId}:${a.askId}`);
    check('D3: KEY `retry with:` exits the pause — draft + verify relaunched, thread kept, no longer paused [T3-R22]',
      k1.dispatched.action === 'retry' && h.calls.relaunchDraftVerify.length === 1
      && afterRetry && afterRetry.paused === false, { d: k1.dispatched, entry: afterRetry });

    // KEY 3 — `close`, on a freshly paused thread.
    const b = await h.bridge.postOwnerAsk({ goalId: GOAL, seatName: SEAT, kind: 'approval', commitId: COMMIT, body: composeApprovalBody({ goalName: GOAL, digest: 'd', commitId: COMMIT }) });
    await h.reply(reg.channelId, b.askId, 'reject-and-pause');
    const k3 = await h.reply(reg.channelId, b.askId, 'close');
    // ⚑ "ENDS THE THREAD" IS NOW A MARK, NOT A DELETION [G-second-brain-43-0828-2119]. The entry
    // stays in the map carrying `released: true` — it is what makes a later reply in this dead
    // thread answerable in-thread instead of falling through to the goal channel. The claim is
    // still that the thread is over and no longer paused, and both halves are asserted.
    const d4entry = h.bridge._askThreads.get(`${reg.channelId}:${b.askId}`);
    check('D4: KEY `close` exits the pause and ends the thread — the entry is MARKED released (not forgotten), so a later reply in it can still be refused in-thread',
      k3.dispatched.action === 'close' && k3.dispatched.done === true
      && Boolean(d4entry) && d4entry.released === true && d4entry.outcome === 'close',
      { d: k3.dispatched, entry: d4entry });

    // KEY 2 — `approve`, on a paused thread, still fires D12.
    const c = await h.bridge.postOwnerAsk({ goalId: GOAL, seatName: SEAT, kind: 'approval', commitId: COMMIT, body: composeApprovalBody({ goalName: GOAL, digest: 'd', commitId: COMMIT }) });
    await h.reply(reg.channelId, c.askId, 'reject-and-pause');
    const k2 = await h.reply(reg.channelId, c.askId, 'approve');
    check('D5: KEY `approve` exits the pause and fires D12 exactly once',
      k2.dispatched.action === 'materialize' && h.calls.materialize.length === 1, { d: k2.dispatched, calls: h.calls.materialize.length });

    // The [T3-R22] pause must survive a bridge restart: the entry carries `paused` and `kind`.
    const raw = JSON.parse(fs.readFileSync(h.bridge.stateFile, 'utf8'));
    const persisted = Object.values(raw.askThreads || {});
    check('D6: `kind` and the pause flag are PERSISTED — a restarted bridge still knows this is an approval thread and still holds the pause',
      persisted.length > 0 && persisted.every((e) => e.kind === 'approval') && persisted.some((e) => 'paused' in e),
      { persisted });
    h.bridge.stop();
  }

  // ── E. [C-16] A MATERIALIZE FAILURE REPORTS BACK INTO **THIS** THREAD ────────────────────────
  {
    const h = harness();
    await h.bridge.start();
    const reg = await h.bridge.registerGoal(GOAL);
    h.setMaterialize(false);
    const a = await h.bridge.postOwnerAsk({
      goalId: GOAL, seatName: SEAT, kind: 'approval', commitId: COMMIT,
      body: composeApprovalBody({ goalName: GOAL, digest: 'digest', commitId: COMMIT }),
    });
    const before = h.slack.posted.length;
    const out = await h.reply(reg.channelId, a.askId, 'approve');
    const backs = h.slack.posted.slice(before);
    check('E1: a D12 materialize refusal posts back INTO THE SAME APPROVAL THREAD, carrying the refusal [C-16]',
      out.dispatched.action === 'materialize-failed' && backs.length === 1
      && backs[0].threadTs === a.askId && backs[0].channel === reg.channelId
      && backs[0].text.includes('commit collision'),
      { back: backs[0], askId: a.askId });
    check('E2: after a failed materialize the thread STAYS OPEN and unpaused — the owner can retry, approve or close in it',
      h.bridge._askThreads.has(`${reg.channelId}:${a.askId}`) && out.dispatched.done === false && out.dispatched.paused === false,
      { d: out.dispatched });

    // The retry after the failure must actually work in that same thread.
    h.setMaterialize(true);
    const retry = await h.reply(reg.channelId, a.askId, 'approve');
    check('E3: a second `approve` in that same thread, once materialize can run, fires D12 — the [C-16] post-back left a usable door',
      retry.dispatched.action === 'materialize' && h.calls.materialize.length === 2, { calls: h.calls.materialize.length });
    h.bridge.stop();
  }

  // ── F. A MISSING PORT IS A FAILURE THE OWNER SEES, NEVER A SILENT SUCCESS ───────────────────
  {
    const dispatch = createApprovalDispatch({ postBack: async () => ({ delivered: true }), logger: null });
    const out = await dispatch.dispatch({
      entry: { goalId: GOAL, channelId: 'C1', askId: '1.1', commitId: COMMIT, paused: false },
      parsed: { outcome: 'approve', comments: '', findings: null },
    });
    check('F1: with NO materialize port wired, `approve` reports a [C-16] failure into the thread — it never reads as approved',
      out.action === 'materialize-failed' && out.ok === false && /no materialize port/.test(out.error), { out });
  }

  // ── G. `materialize` CANNOT BE STUBBED AROUND THE GATEWAY ───────────────────────────────────
  // The worst lie this surface can tell is "execution started" when nothing did, and the shortest
  // road to it is an embedder injecting `materialize: async () => ({ok:true})` to make a test
  // pass. Since the fourteenth intent landed there is no such seam: the bridge builds the port
  // from its own forwarder and REFUSES an injected one at construction — loudly, where it is
  // impossible to miss, not at the first approve.
  {
    let refused = null;
    try {
      const h = harnessWith({ materialize: async () => ({ ok: true }) });
      h.bridge.stop();
    } catch (err) {
      refused = err.message;
    }
    check('G1: an injected `materialize` port is REFUSED at construction — D12 goes through the fourteenth intent, never around it',
      typeof refused === 'string' && /start-execution/.test(refused), { refused });
  }

  const pass = checks.every((c) => c.pass);
  const wallMs = Date.now() - t0;
  const exit = pass ? 0 : 1;
  fs.writeFileSync(OUT, `${JSON.stringify({
    summary: { probe: 'probe-chat-approval', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 },
    entries: checks,
  }, null, 2)}\n`);
  process.stdout.write(`PROBE probe-chat-approval EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
})().catch((err) => {
  process.stdout.write(`PROBE probe-chat-approval EXIT=1 THREW ${err.stack}\n`);
  process.exit(1);
});
