'use strict';

// probe-chat-recovery-dispatch — two wired recovery replies proven against the same fake daemon:
// `drop-lane`'s TWO wire calls, in order, that must not half-complete
// (`d-recovery-drop-stops-live-work`, `dl-teardown-wire`), and `retry-with-change`'s
// write-then-re-arm order (`d-recovery-correction-lands-in-instructions` + `d-recovery-retry-
// scope`, `rr-port-wire`).
//
// NO SLACK AND NO DAEMON, same shape as `probe-chat-approval.js`: the transport and the gateway
// forwarder are fakes, and every wire call the `dropLane`/`retryWithChange` ports make is
// RECORDED, in order — that order is the point. A probe that only asserted "the lane got dropped"
// (or "the lane got re-armed") would pass on a bridge that marked a still-running lane abandoned,
// or that re-armed a lane before the owner's correction ever reached disk — exactly the failures
// the `dl-*` cluster and `rr-port-wire` respectively exist to make impossible.
//
// The fake forwarder answers the intents `dropLane` and `retryWithChange` actually use (`inspect`
// target `ticker`, `kill-session`, `drop-lane`, `pause-resume` for both the GOAL-scoped `pause-
// goal` CONTROL arm and the LANE-scoped `verb:'resume'`+`seat` re-arm) — none of them
// re-implemented, all of them scripted by the scenario the block sets before replying.
// `retryWithChange` does NOT call the gateway for the correction half — `writeRetryCorrection`
// (`ignite/supervisor/retry-correction.js`) is a direct in-process filesystem write, so its arms
// below check the real tmpdir the harness roots `workspaceRoot` at, not a fake-forwarder call.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { buildBridge } = require('../index');

const OUT = path.join(__dirname, 'probe-chat-recovery-dispatch.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence: evidence || {} }); };

const OWNER = 'U-OWNER';
const GOAL = 'recovery-goal';
const SEAT = 'worker-seat';

// ── The bridge harness (mock Socket-Mode transport + scriptable fake gateway forwarder) ─────────
function harness() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'recovery-dispatch-'));

  const posted = [];
  let nextTs = 900;
  let nextChan = 1;
  const chans = [];
  const slack = {
    posted,
    async authTest() { return { ok: true, userId: 'U-BOT' }; },
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

  // The scenario the CURRENT reply is scripted against — mutated between replies in the same
  // harness (the retry arm needs exactly that: fail once, flip the knob, succeed the second time).
  const scenario = {
    liveSessions: [], killOk: true, markOk: true, markIdempotent: false, resumeOk: true,
  };
  const calls = [];
  const forwarder = {
    async forward(intent, payload) {
      const call = { intent, payload };
      calls.push(call);
      if (intent === 'inspect' && payload.target === 'ticker') {
        return { ok: true, result: { live_sessions: scenario.liveSessions } };
      }
      if (intent === 'kill-session') {
        return scenario.killOk
          ? { ok: true, result: { execId: payload.id, killed: true } }
          : { ok: false, error: { code: 'kill-refused' } };
      }
      if (intent === 'drop-lane') {
        return scenario.markOk
          ? { ok: true, result: { goal: payload.goal, seat: payload.seat, idempotent: scenario.markIdempotent === true } }
          : { ok: false, error: { code: 'mark-refused' } };
      }
      if (intent === 'pause-resume') {
        // A LANE-SCOPED resume (`verb:'resume'` + `seat`, `rr-lane-rearm`'s widened intent) is what
        // `retryWithChange` sends. Recorded on the call itself, at the exact moment the wire call
        // fires, whether the owner's correction payload is ALREADY on disk — that is the ordering
        // `rr-port-wire`'s port exists to guarantee (write the correction, THEN re-arm), and the
        // only place it can be proven is inside the fake that stands in for the daemon.
        if (payload.verb === 'resume' && payload.seat) {
          const correctionPath = path.join(root, '.rbtv', 'goals', String(payload.goal), 'coordination', 'correction-payloads', `${payload.seat}.md`);
          call.correctionOnDiskAtCallTime = fs.existsSync(correctionPath);
          if (!scenario.resumeOk) return { ok: false, error: { code: 'lane-refused' } };
          return { ok: true, result: { verb: payload.verb, goal: payload.goal, seat: payload.seat, applied: true, actions: [{ row: 'lane', change: 'blocked→armed', goal: payload.goal, seat: payload.seat }], refusals: [] } };
        }
        return { ok: true, result: { verb: payload.verb, goal: payload.goal, applied: true, actions: [{ row: 'goal', change: 'running→paused', goal: payload.goal }], refusals: [] } };
      }
      // `record-owner-ask` (open + reap) — the ask-store's own open/close ledger, same shape
      // `probe-chat-approval.js`'s fake forwarder answers it with, for the same reason: this probe
      // is not testing the ask-open/reap mechanism, only what happens AFTER a recovery reply
      // releases.
      return { ok: true, result: { recorded: true, ask_id: payload.thread || null, state: payload.act === 'reap' ? 'closed' : 'open', relaunch: { queued: true } } };
    },
    async inspect(target, extra = {}) { return this.forward('inspect', { target, ...extra }); },
  };

  const built = buildBridge({
    gatewayAddr: '127.0.0.1:0', bridgeToken: 'stub', sessionJobId: 'chat-launch', sendMessageJobId: 'send-message',
    workdir: null, workspaceRoot: root, channelPrefix: 'test-', stateFile: path.join(root, 'state.json'),
    busFerry: false, allowlist: [OWNER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  }, {
    logger: () => {}, makeTransport: () => slack, forwarderImpl: forwarder,
    replyLegOptions: { pollMs: 3600000 }, busFerryOptions: { pollMs: 3600000 },
  });
  return {
    root, posted, calls, scenario, bridge: built.bridge,
    reply(channel, threadTs, text, user = OWNER) {
      return built.bridge.onChatMessage({
        chatUserId: user, chatThreadId: `${channel}:${threadTs}`, text,
        _channel: channel, _threadTs: threadTs, _msgTs: `${Date.now()}.1`, _inThread: true, _channelType: 'channel',
      });
    },
  };
}

async function openRecoveryAsk(h) {
  const reg = await h.bridge.registerGoal(GOAL);
  const ask = await h.bridge.postOwnerAsk({
    goalId: GOAL, seatName: SEAT, kind: 'recovery',
    body: 'stuck lane\n\nreply retry-with-change, drop-lane or pause-goal',
  });
  return { channelId: reg.channelId, askId: ask.askId };
}

const LIVE_WORKDIR = `/x/.rbtv/goals/${GOAL}/seats/${SEAT}`;

(async () => {
  // ── A. LIVE lane: stop runs, THEN the mark runs, in that order ─────────────────────────────
  {
    const h = harness();
    await h.bridge.start();
    h.scenario.liveSessions = [{ exec_id: 77, workdir: LIVE_WORKDIR }];
    const { channelId, askId } = await openRecoveryAsk(h);
    const out = await h.reply(channelId, askId, 'drop lane');
    // `record-owner-ask` (open + reap) is the ask-store's own bookkeeping around EVERY reply,
    // approval or recovery alike — irrelevant to the ORDER this arm proves, so it is filtered out
    // rather than asserted on a second time.
    const intents = h.calls.map((c) => c.intent).filter((i) => i !== 'record-owner-ask');
    check('A1: a LIVE lane is stopped THEN marked — inspect, kill-session, drop-lane, in that exact order',
      JSON.stringify(intents) === JSON.stringify(['inspect', 'kill-session', 'drop-lane']),
      { intents });
    const killCall = h.calls.find((c) => c.intent === 'kill-session');
    const dropCall = h.calls.find((c) => c.intent === 'drop-lane');
    check('A2: kill-session targets the exec_id the ticker inspection found for this (goal, seat)',
      killCall && killCall.payload.id === 77, { payload: killCall && killCall.payload });
    check('A3: the dispatch reports success and the drop-lane intent carries the goal + seat, no more',
      out.dispatched.ok === true && out.dispatched.action === 'drop-lane'
      && dropCall && JSON.stringify(Object.keys(dropCall.payload).sort()) === JSON.stringify(['goal', 'seat']),
      { dispatched: out.dispatched, payload: dropCall && dropCall.payload });
    h.bridge.stop();
  }

  // ── B. NOTHING live: clean success, no error, and NO kill-session call at all ───────────────
  {
    const h = harness();
    await h.bridge.start();
    h.scenario.liveSessions = [];
    const { channelId, askId } = await openRecoveryAsk(h);
    const out = await h.reply(channelId, askId, 'drop lane');
    // `record-owner-ask` (open + reap) is the ask-store's own bookkeeping around EVERY reply,
    // approval or recovery alike — irrelevant to the ORDER this arm proves, so it is filtered out
    // rather than asserted on a second time.
    const intents = h.calls.map((c) => c.intent).filter((i) => i !== 'record-owner-ask');
    check('B1: nothing live is a clean no-op straight to the mark — inspect, drop-lane, no kill-session',
      JSON.stringify(intents) === JSON.stringify(['inspect', 'drop-lane']) && out.dispatched.ok === true,
      { intents, dispatched: out.dispatched });
    h.bridge.stop();
  }

  // ── C. HALF-COMPLETION: stop succeeds (nothing live), mark FAILS ────────────────────────────
  let halfCompletionHarness = null;
  {
    const h = harness();
    await h.bridge.start();
    h.scenario.liveSessions = [];
    h.scenario.markOk = false;
    const { channelId, askId } = await openRecoveryAsk(h);
    const out = await h.reply(channelId, askId, 'drop lane');
    check('C1: dispatch returns ok:false on a mark failure',
      out.dispatched.ok === false && out.dispatched.action === 'drop-lane-failed', { dispatched: out.dispatched });
    check('C2: the error names the lane as NOT marked and possibly relaunched, never silent',
      /NOT marked abandoned/.test(out.dispatched.error) && /may be relaunched/.test(out.dispatched.error),
      { error: out.dispatched.error });
    const posted = h.posted[h.posted.length - 1];
    check('C3: the thread text says the same — NOT marked, may be relaunched — and NEVER "did not run"',
      posted && /NOT marked abandoned/.test(posted.text) && /may be relaunched/.test(posted.text) && !/did not run/.test(posted.text),
      { text: posted && posted.text });
    check('C4: NO success text is posted for this arm — the only post is the failure line',
      h.posted.filter((p) => /^drop lane failed|dropped: live work stopped/.test(p.text)).length === 0
      || !h.posted.some((p) => /dropped: live work stopped/.test(p.text)),
      { posted: h.posted.map((p) => p.text) });
    halfCompletionHarness = h;
  }

  // ── D. RETRY: the SAME lane, a fresh ask, drop-lane now completes the mark ──────────────────
  {
    const h = halfCompletionHarness;
    h.scenario.markOk = true; // the daemon-side condition that refused the mark is now gone
    const { channelId, askId } = await openRecoveryAsk(h);
    const out = await h.reply(channelId, askId, 'drop lane');
    check('D1: retrying the drop after a mark failure completes the mark — ok:true this time',
      out.dispatched.ok === true && out.dispatched.action === 'drop-lane', { dispatched: out.dispatched });
    h.bridge.stop();
  }

  // ── E. IDEMPOTENCY: dropping an ALREADY-ABANDONED lane succeeds as a no-op ──────────────────
  {
    const h = harness();
    await h.bridge.start();
    h.scenario.liveSessions = []; // a prior drop already stopped it
    h.scenario.markOk = true;
    h.scenario.markIdempotent = true; // the daemon's abandonSeat reports "already abandoned"
    const { channelId, askId } = await openRecoveryAsk(h);
    const out = await h.reply(channelId, askId, 'drop lane');
    check('E1: an already-abandoned lane succeeds as a no-op, not an error',
      out.dispatched.ok === true && out.dispatched.action === 'drop-lane', { dispatched: out.dispatched });
    h.bridge.stop();
  }

  // ── F. THE DISCRIMINATING CONTROL: `pause-goal` on the same fixture pauses, and never marks ──
  {
    const h = harness();
    await h.bridge.start();
    h.scenario.liveSessions = [{ exec_id: 5, workdir: LIVE_WORKDIR }]; // even with a live lane present
    const { channelId, askId } = await openRecoveryAsk(h);
    const out = await h.reply(channelId, askId, 'pause goal');
    // `record-owner-ask` (open + reap) is the ask-store's own bookkeeping around EVERY reply,
    // approval or recovery alike — irrelevant to the ORDER this arm proves, so it is filtered out
    // rather than asserted on a second time.
    const intents = h.calls.map((c) => c.intent).filter((i) => i !== 'record-owner-ask');
    check('F1: `pause-goal` fires ONLY `pause-resume` — never `inspect`, `kill-session` or `drop-lane`',
      JSON.stringify(intents) === JSON.stringify(['pause-resume']), { intents });
    check('F2: `pause-goal` still succeeds and pauses, proving the new path is not firing on everything',
      out.dispatched.ok === true && out.dispatched.action === 'pause-goal', { dispatched: out.dispatched });
    const posted = h.posted[h.posted.length - 1];
    check('F3: the posted confirmation is the pause text, not a drop confirmation',
      posted && /paused\.$/.test(posted.text) && !/dropped/.test(posted.text), { text: posted && posted.text });
    h.bridge.stop();
  }

  // ── G. RETRY-WITH-CHANGE: the correction lands on disk BEFORE the lane is re-armed ───────────
  {
    const h = harness();
    await h.bridge.start();
    const { channelId, askId } = await openRecoveryAsk(h);
    const out = await h.reply(channelId, askId, 'retry-with-change bump the timeout to 30s');
    const intents = h.calls.map((c) => c.intent).filter((i) => i !== 'record-owner-ask');
    check('G1: retry-with-change fires ONLY pause-resume — never inspect, kill-session or drop-lane',
      JSON.stringify(intents) === JSON.stringify(['pause-resume']), { intents });
    const resumeCall = h.calls.find((c) => c.intent === 'pause-resume');
    check('G2: pause-resume is called with verb:resume and this exact (goal, seat), nothing else',
      resumeCall && resumeCall.payload.verb === 'resume' && resumeCall.payload.goal === GOAL
        && resumeCall.payload.seat === SEAT
        && JSON.stringify(Object.keys(resumeCall.payload).sort()) === JSON.stringify(['goal', 'seat', 'verb']),
      { payload: resumeCall && resumeCall.payload });
    check('G3: the correction file was ALREADY on disk the moment the re-arm wire call fired — write, then arm',
      resumeCall && resumeCall.correctionOnDiskAtCallTime === true, { resumeCall });
    const correctionPath = path.join(h.root, '.rbtv', 'goals', GOAL, 'coordination', 'correction-payloads', `${SEAT}.md`);
    const correctionText = fs.existsSync(correctionPath) ? fs.readFileSync(correctionPath, 'utf8') : null;
    check("G4: the owner's comments land in the seat's correction payload, verbatim",
      correctionText != null && correctionText.includes('bump the timeout to 30s'), { correctionText });
    check('G5: the dispatch reports success',
      out.dispatched.ok === true && out.dispatched.action === 'retry-with-change', { dispatched: out.dispatched });
    h.bridge.stop();
  }

  // ── H. RETRY-WITH-CHANGE REFUSED: the re-arm act refuses — a truthful in-thread failure line,
  //      never silent and never the retired "did not run" wording ─────────────────────────────
  {
    const h = harness();
    await h.bridge.start();
    h.scenario.resumeOk = false;
    const { channelId, askId } = await openRecoveryAsk(h);
    const out = await h.reply(channelId, askId, 'retry-with-change try again please');
    check('H1: dispatch returns ok:false on a re-arm refusal',
      out.dispatched.ok === false && out.dispatched.action === 'retry-with-change-failed', { dispatched: out.dispatched });
    const posted = h.posted[h.posted.length - 1];
    check('H2: the thread gets a truthful failure line naming the error, and NEVER the retired "did not run" wording',
      posted && /^retry-with-change failed:/.test(posted.text) && !/did not run/.test(posted.text),
      { text: posted && posted.text });
    h.bridge.stop();
  }

  // ── I. RETRY-WITH-CHANGE, EMPTY COMMENTS: the correction write is a clean no-op, the re-arm still fires ──
  {
    const h = harness();
    await h.bridge.start();
    const { channelId, askId } = await openRecoveryAsk(h);
    const out = await h.reply(channelId, askId, 'retry-with-change');
    const correctionPath = path.join(h.root, '.rbtv', 'goals', GOAL, 'coordination', 'correction-payloads', `${SEAT}.md`);
    check('I1: no free text after the token writes NO correction file at all',
      !fs.existsSync(correctionPath), { correctionPath });
    check('I2: the lane is still re-armed — an empty correction is not a reason to refuse',
      out.dispatched.ok === true && out.dispatched.action === 'retry-with-change', { dispatched: out.dispatched });
    h.bridge.stop();
  }

  const pass = checks.every((c) => c.pass);
  const wallMs = Date.now() - t0;
  const exit = pass ? 0 : 1;
  fs.writeFileSync(OUT, `${JSON.stringify({
    summary: { probe: 'probe-chat-recovery-dispatch', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 },
    entries: checks,
  }, null, 2)}\n`);
  process.stdout.write(`PROBE probe-chat-recovery-dispatch EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
})().catch((err) => {
  process.stdout.write(`PROBE probe-chat-recovery-dispatch EXIT=1 THREW ${err.stack}\n`);
  process.exit(1);
});
