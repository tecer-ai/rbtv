'use strict';

// OWNER RULINGS 2026-08-06 — the mention route (ruling 3c), descriptor-driven prompts
// (ruling 2), and goal-channel sessions homed at the goal-master seat (ruling 3a).
//
// Same posture as probe-chat-goal-channel: no daemon. Every claim here is about the
// bridge's own routing and payload shaping, so the gateway is a stub that RECORDS EVERY
// enqueue and Slack is a fake that records every post. That makes the negative claims —
// "nothing enqueued", "no charter in the prompt", "no instance path in source" — checkable
// as call-log and source assertions rather than as the absence of an error.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { makeCapture, nowMs } = require('./lib');
const { buildBridge } = require('../index');
const { NO_GOAL_SEAT_NOTICE } = require('../forward-path');

const OUT = path.join(__dirname, 'probe-chat-mention-route.out');
const SRC_DIR = path.join(__dirname, '..');

const USER = 'U_OWNER';
const BOT = 'U_BOT';
const PREFIX = 'test-';

// ── fakes ────────────────────────────────────────────────────────────────────

// A Slack transport with the narrow admin surface plus `auth.test`. `authOk: false`
// models the failure the mention route must FAIL CLOSED on (a bot that cannot say who
// it is must not guess who was meant).
function makeFakeSlack({ existing = [], authOk = true } = {}) {
  const channels = existing.map((c) => ({ ...c }));
  const posted = [];
  let nextId = 1;
  return {
    channels, posted,
    async authTest() { return authOk ? { ok: true, userId: BOT } : { ok: false, error: 'invalid_auth' }; },
    async createChannel({ name }) {
      if (channels.some((c) => c.name === name && !c.is_archived)) return { ok: false, error: 'name_taken' };
      const ch = { id: `C${String(nextId++).padStart(4, '0')}`, name, is_archived: false };
      channels.push(ch);
      return { ok: true, channel: { id: ch.id, name: ch.name } };
    },
    async listChannels({ excludeArchived = true } = {}) {
      const visible = channels.filter((c) => (excludeArchived ? !c.is_archived : true));
      return { ok: true, channels: visible.map((c) => ({ id: c.id, name: c.name, is_archived: c.is_archived })), nextCursor: null };
    },
    async archiveChannel() { return { ok: true }; },
    async sendToOwner({ channel, threadTs, text }) { posted.push({ channel, threadTs, text }); return { delivered: true, ts: '1.0' }; },
    async start() { return { connected: true }; },
    stop() {},
  };
}

function makeFakeForwarder() {
  const enqueued = [];
  let nextQueueId = 100;
  return {
    enqueued,
    async forward(intent, payload) {
      const jobId = nextQueueId++;
      enqueued.push({ intent, payload, jobId });
      return { ok: true, result: { jobId } };
    },
    // Every session-creating enqueue reads back as a LIVE session on its own queue row
    // (the D108(B) tier-1 shape), so a follow-up leg can resolve its chain thread. The
    // mint-vs-continue checks need a resolvable chain; the routing claims they make are
    // upstream of it, so a resolvable chain is exactly the right amount of daemon here.
    async inspect() {
      const live = enqueued
        .filter((e) => e.payload.job_id === 'chat-launch')
        .map((e) => ({ queue_id: e.jobId, exec_id: e.jobId, thread: `exec-${e.jobId}` }));
      return { ok: true, result: { live_sessions: live, recent_ticks: [] } };
    },
  };
}

// A workspace root shaped like the real one. 7.607 E3: the two unresolvable states left are
// SEAT MISSING and GOAL ABSENT — "no open run" was a third one until the run register was
// extinguished, and it is gone rather than re-spelled: there is no stored state to be closed.
function seedWorkspace(goals) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-mention-'));
  for (const [goalId, opts] of Object.entries(goals)) {
    // 7.607 E3: GOAL-DIRECT. No register row, no run folder — a goal-surface session is homed by
    // whether the SEAT EXISTS on disk, which is the whole question now.
    const { seat = true } = opts || {};
    const goalDir = path.join(root, '.rbtv', 'goals', goalId);
    fs.mkdirSync(goalDir, { recursive: true });
    if (seat) fs.mkdirSync(path.join(goalDir, 'seats', 'goal-master'), { recursive: true });
  }
  return root;
}

function makeBridge({ goals = {}, authOk = true, workspaceRoot = undefined } = {}) {
  const root = workspaceRoot === undefined ? seedWorkspace(goals) : workspaceRoot;
  const slack = makeFakeSlack({ authOk });
  const forwarder = makeFakeForwarder();
  const config = {
    gatewayAddr: '127.0.0.1:0',
    bridgeToken: 'stub',
    sessionJobId: 'chat-launch',
    sendMessageJobId: 'send-message',
    workdir: '/configured/master/workdir',
    workspaceRoot: root,
    channelPrefix: PREFIX,
    allowlist: [USER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  };
  const built = buildBridge(config, {
    logger: () => {},
    makeTransport: () => slack,
    forwarderImpl: forwarder,
    replyLegOptions: { pollMs: 3600000 },
  });
  return { ...built, slack, forwarder, config, workspaceRoot: root };
}

function msg({ channel, ts, threadTs = null, channelType, text = 'hello', user = USER }) {
  return {
    chatUserId: user,
    chatThreadId: `${channel}:${threadTs || ts}`,
    text,
    _channel: channel,
    _threadTs: threadTs || ts,
    _channelType: channelType,
    _inThread: Boolean(threadTs),
  };
}

// ── the probe ────────────────────────────────────────────────────────────────

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const checks = [];
  const check = (name, pass, detail = {}) => { checks.push({ name, pass, ...detail }); cap.log({ check: name, pass, ...detail }); };

  // 1 — THE MENTION ROUTE. A mention in an UNMAPPED channel is master traffic, scoped to
  //     the Slack thread, and answered IN-THREAD. Two different threads in the SAME
  //     channel are two sittings — the property that makes parallel mentions safe.
  {
    const { bridge, forwarder, slack } = makeBridge();
    await bridge.start();

    const one = await bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '1.1', channelType: 'channel', text: `<@${BOT}> what is the plan?` }));
    const two = await bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '2.1', channelType: 'channel', text: `hey <@${BOT}> again` }));

    check('mention in an unmapped channel routes as MASTER traffic',
      one.forwarded === true && one.route === 'master' && one.goalId === null && one.leg === 'session-create', { one });
    check('mention conversation is thread-scoped (channel:thread_ts), not the channel',
      forwarder.enqueued.length === 2 && one.leg === 'session-create' && two.leg === 'session-create', { legs: [one.leg, two.leg] });
    // ⚑ INVERTED 2026-08-11 (launch-cast unification, owner ruling D2). This asserted a
    // per-SURFACE profile — mention traffic ran `master_profile`, goal traffic `goal_profile` —
    // which is exactly the transport deciding what an agent runs. Those keys are DELETED; every
    // surface named execution through `session_profile`, the last such key; 7.787 deleted it, so
    // the enqueue names NOTHING about what runs. The WORKDIR half is untouched: where a sitting is
    // homed is still the transport's business, and it is the control that keeps this arm
    // non-vacuous — a bridge that stopped forwarding entirely would fail it rather than pass.
    check('mention session names NO execution at all, and still homes at the configured workdir',
      forwarder.enqueued.every((e) => !('profile' in e.payload.args) && e.payload.args.workdir === '/configured/master/workdir'),
      { args: forwarder.enqueued.map((e) => e.payload.args) });

    await bridge.deliverToOwner({ chatThreadId: 'C_RANDOM:1.1', text: 'answer' });
    const post = slack.posted[slack.posted.length - 1];
    check('mention reply posts IN-THREAD, not at channel top level',
      Boolean(post) && post.channel === 'C_RANDOM' && post.threadTs === '1.1', { post });
    bridge.stop();
  }

  // 2 — UNMENTIONED traffic in an unmapped channel stays REFUSED, nothing enqueued. The
  //     mention is what makes the message attributable; without it the bot sitting in an
  //     ordinary channel would mint work from every passing sentence.
  {
    const { bridge, forwarder } = makeBridge();
    await bridge.start();
    const stray = await bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '3.1', channelType: 'channel', text: 'just chatting' }));
    const nearMiss = await bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '3.2', channelType: 'channel', text: '<@U_SOMEONE_ELSE> ping' }));
    const mpim = await bridge.onChatMessage(msg({ channel: 'G_MPIM', ts: '3.3', channelType: 'mpim', text: `<@${BOT}> hi` }));
    check('unmentioned message in an unmapped channel refused — NOTHING enqueued',
      stray.forwarded === false && stray.reason === 'unroutable-surface' && forwarder.enqueued.length === 0, { stray });
    check('a mention of SOMEONE ELSE is not a mention of the bot', nearMiss.forwarded === false && nearMiss.reason === 'unroutable-surface', { nearMiss });
    check('group DM (mpim) stays refused even when the bot is mentioned',
      mpim.forwarded === false && mpim.reason === 'unroutable-surface' && forwarder.enqueued.length === 0, { mpim });
    bridge.stop();
  }

  // 3 — FAIL CLOSED. When `auth.test` cannot resolve the bot's own user id, the mention
  //     route is not armed and an unmapped channel behaves exactly as it did before the
  //     ruling. A DM on the same bridge still works — the failure is scoped, not fatal.
  {
    const { bridge, forwarder } = makeBridge({ authOk: false });
    await bridge.start();
    const mention = await bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '4.1', channelType: 'channel', text: `<@${BOT}> hello` }));
    const dm = await bridge.onChatMessage(msg({ channel: 'D_IM', ts: '4.2', channelType: 'im', text: 'hello' }));
    check('bot-id resolution failure DISABLES the mention route (refused, nothing enqueued)',
      mention.forwarded === false && mention.reason === 'unroutable-surface', { mention });
    check('the DM path is unaffected by a failed bot-id resolution',
      dm.forwarded === true && dm.route === 'master' && forwarder.enqueued.length === 1, { dm, enqueued: forwarder.enqueued.length });
    bridge.stop();
  }

  // 4 — GOAL SESSIONS ARE HOMED AT THE GOAL-MASTER SEAT of the goal's OPEN run — the
  //     workdir whose descriptor chain supplies the session's identity.
  {
    const { bridge, forwarder, workspaceRoot } = makeBridge({ goals: { 'goal-seated': {} } });
    await bridge.start();
    const reg = await bridge.registerGoal('goal-seated');
    const res = await bridge.onChatMessage(msg({ channel: reg.channelId, ts: '5.1', channelType: 'channel', text: 'status?' }));
    const expected = path.join(workspaceRoot, '.rbtv', 'goals', 'goal-seated', 'seats', 'goal-master');
    const args = forwarder.enqueued[0] && forwarder.enqueued[0].payload.args;
    check('goal session-create is homed at the open run\'s goal-master seat',
      res.forwarded === true && Boolean(args) && args.workdir === expected, { workdir: args && args.workdir, expected });
    // …and the same ABSENCE on goal traffic. Paired with the mention arm above: two surfaces,
    // neither naming execution, so no surface can mean anything by it.
    check('goal session-create names NO execution either — the surface decides nothing',
      Boolean(args) && !('profile' in args), { args });
    bridge.stop();
  }

  // 5 — NO SEAT, NO WORK. Each unresolvable state enqueues NOTHING and posts the ONE fixed
  //     notice on the goal's own channel. Silence here would read as the goal-master ignoring
  //     the owner. 7.607 E3: two states, not three — see `seedWorkspace`.
  {
    const cases = [
      { label: 'the goal exists with no goal-master seat', goals: { 'goal-unseated': { seat: false } }, goalId: 'goal-unseated' },
      { label: 'goal absent from the workspace', goals: {}, goalId: 'goal-absent' },
    ];
    for (const c of cases) {
      const { bridge, forwarder, slack } = makeBridge({ goals: c.goals });
      await bridge.start();
      const reg = await bridge.registerGoal(c.goalId);
      const res = await bridge.onChatMessage(msg({ channel: reg.channelId, ts: '6.1', channelType: 'channel', text: 'status?' }));
      const post = slack.posted[slack.posted.length - 1];
      check(`goal traffic refused when ${c.label} — nothing enqueued, honest notice posted`,
        res.forwarded === false && String(res.reason).startsWith('no-goal-master-seat:')
        && forwarder.enqueued.length === 0
        && Boolean(post) && post.text === NO_GOAL_SEAT_NOTICE && post.channel === reg.channelId,
        { reason: res.reason, enqueued: forwarder.enqueued.length, post });
      bridge.stop();
    }

    // And with no workspace_root configured at all — the deployment that never set the key.
    const { bridge, forwarder, slack } = makeBridge({ workspaceRoot: null });
    await bridge.start();
    const reg = await bridge.registerGoal('goal-nowhere');
    const res = await bridge.onChatMessage(msg({ channel: reg.channelId, ts: '6.2', channelType: 'channel', text: 'status?' }));
    check('unconfigured workspace_root refuses goal traffic loudly, master traffic unaffected',
      res.reason === 'no-goal-master-seat:no-workspace-root-configured' && forwarder.enqueued.length === 0
      && slack.posted.some((p) => p.text === NO_GOAL_SEAT_NOTICE),
      { reason: res.reason });
    bridge.stop();
  }

  // 6 — THE PROMPT IS THE BARE USER TEXT (ruling 2). Behaviour travels with the seat
  //     descriptor, so the bridge ships zero behavioural text on EITHER leg.
  {
    const { bridge, forwarder } = makeBridge({ goals: { 'goal-prompt': {} } });
    await bridge.start();
    const reg = await bridge.registerGoal('goal-prompt');
    await bridge.onChatMessage(msg({ channel: 'D_IM', ts: '7.1', channelType: 'im', text: 'what is the plan?' }));
    await bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '7.2', channelType: 'channel', text: `<@${BOT}> mention text` }));
    await bridge.onChatMessage(msg({ channel: reg.channelId, ts: '7.3', channelType: 'channel', text: 'goal text' }));
    // NARROWED 2026-08-07 by owner amendment `r-bare-prompt-admits-one-correlation-id`: the
    // prompt may begin with ONE `chat-thread: <channel>:<ts>` line and a blank line, and
    // nothing else. Strip exactly that shape, then the remainder must STILL be the user text
    // verbatim — so a charter, an identity line, or any second prefix fails exactly as before.
    // The ban on behavioural text is unchanged; this admits one addressed FACT.
    const CORRELATION_PREFIX = /^chat-thread: [A-Z][A-Z0-9_]{2,}(?::\d+\.\d+)?\n\n/;
    const bare = (p) => String(p).replace(CORRELATION_PREFIX, '');
    const prompts = forwarder.enqueued.map((e) => e.payload.args.prompt);
    const stripped = prompts.map(bare);
    check('every session-create prompt is the user text, behind AT MOST one correlation line — no charter on any leg',
      prompts.length === 3 && stripped[0] === 'what is the plan?' && stripped[1] === `<@${BOT}> mention text` && stripped[2] === 'goal text',
      { prompts, stripped });
    // The narrowing must not become a hole: anything the strip does NOT remove is still
    // compared verbatim, so this asserts the admitted prefix is the ONLY thing tolerated.
    check('a second prefix is still refused — only the one correlation line is admitted',
      bare(`chat-thread: D_X:1.0\n\nyou are the master.\n\nreal text`) === 'you are the master.\n\nreal text'
      && bare('you are the master.\n\nreal text') === 'you are the master.\n\nreal text',
      {});
    bridge.stop();
  }

  // 7 — NO INSTANCE-SPECIFIC PATH IN REPO SOURCE. The charter carried an absolute
  //     /home/… path; the ruling removed it and this keeps it removed. Enforced as an
  //     absence in the runtime source, which no one can forget under pressure.
  {
    const runtime = fs.readdirSync(SRC_DIR).filter((f) => f.endsWith('.js')).sort();
    const hits = [];
    for (const f of runtime) {
      const code = fs.readFileSync(path.join(SRC_DIR, f), 'utf8');
      for (const re of [/\/home\/[a-z]/i, /\/Users\/[a-z]/i, /MASTER_CHARTER/]) {
        if (re.test(code)) hits.push({ file: f, pattern: String(re) });
      }
    }
    check('bridge source carries no instance path and no hardcoded charter', hits.length === 0, { scanned: runtime, hits });
  }

  // 8 — MINT vs CONTINUE (owner-observed 2026-08-06). A mention MINTS the conversation;
  //     a reply INSIDE that thread continues it with NO re-mention. Everything else in
  //     an unmapped channel stays refused — an unknown thread, and any top-level
  //     message (whose conversation id is its own ts, always brand new).
  {
    const { bridge, forwarder } = makeBridge();
    await bridge.start();

    const mint = await bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '8.1', channelType: 'channel', text: `<@${BOT}> start` }));
    const cont = await bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '8.2', threadTs: '8.1', channelType: 'channel', text: 'and one more thing' }));
    check('mention still MINTS the conversation (session-create)',
      mint.forwarded === true && mint.leg === 'session-create', { mint });
    check('un-mentioned reply in a KNOWN thread CONTINUES it as a follow-up on that conversation',
      cont.forwarded === true && cont.route === 'master' && cont.leg === 'follow-up'
      && forwarder.enqueued.length === 2
      && forwarder.enqueued[1].payload.job_id === 'send-message',
      { cont, enqueued: forwarder.enqueued.length });

    // Each refusal below is measured against the enqueue count IMMEDIATELY BEFORE it, so
    // it fails for its OWN claim rather than inheriting the continuation's counter.
    let base = forwarder.enqueued.length;
    const unknownThread = await bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '8.4', threadTs: '8.3', channelType: 'channel', text: 'reply in a thread nobody minted' }));
    check('un-mentioned reply in an UNKNOWN thread stays refused — nothing enqueued',
      unknownThread.forwarded === false && unknownThread.reason === 'unroutable-surface' && forwarder.enqueued.length === base,
      { unknownThread, base, enqueued: forwarder.enqueued.length });

    base = forwarder.enqueued.length;
    const topLevel = await bridge.onChatMessage(msg({ channel: 'C_RANDOM', ts: '8.5', channelType: 'channel', text: 'top-level chatter' }));
    check('un-mentioned TOP-LEVEL message stays refused even in a channel that has a live sitting',
      topLevel.forwarded === false && topLevel.reason === 'unroutable-surface' && forwarder.enqueued.length === base,
      { topLevel, base, enqueued: forwarder.enqueued.length });

    // A DIFFERENT unmapped channel's thread is not this one's — the id is channel-scoped.
    base = forwarder.enqueued.length;
    const otherChannel = await bridge.onChatMessage(msg({ channel: 'C_OTHER', ts: '8.6', threadTs: '8.1', channelType: 'channel', text: 'same ts, other channel' }));
    check('the continuation is channel-scoped — the same thread_ts in another channel is refused',
      otherChannel.forwarded === false && otherChannel.reason === 'unroutable-surface' && forwarder.enqueued.length === base,
      { otherChannel, base });
    bridge.stop();
  }

  const pass = checks.every((c) => c.pass);
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-mention-route', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-mention-route EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
}

main();
