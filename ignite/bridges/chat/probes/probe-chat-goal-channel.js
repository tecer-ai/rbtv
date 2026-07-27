'use strict';

// TASK 7.58 — the goal↔channel bridge (owner ruling d-channel-per-goal). Proves the
// five task criteria plus the two settled open points (goal-channel-design.md), and
// the run's `r-slack-etiquette` never-invite guard.
//
// Deliberately NOT a daemon probe: every claim here is about the bridge's own
// routing and lifecycle, so the gateway is a stub and Slack is a fake admin surface
// that RECORDS EVERY CALL. That makes the negative claims — "no second create",
// "nothing enqueued", "never invited" — checkable as call-log assertions rather than
// as absence of an error.

const path = require('node:path');
const fs = require('node:fs');
const { makeCapture, nowMs } = require('./lib');
const { buildBridge } = require('../index');
const { channelNameForGoal, goalIdFromChannelName } = require('../goal-channel-map');

const OUT = path.join(__dirname, 'probe-chat-goal-channel.out');
const SRC_DIR = path.join(__dirname, '..');

const USER = 'U_OWNER';
const PREFIX = 'test-';

// ── fakes ────────────────────────────────────────────────────────────────────

// A Slack workspace that records every admin call. `existing` seeds channels that
// were created out-of-band (the adopt + recover paths).
function makeFakeSlack({ existing = [] } = {}) {
  const channels = existing.map((c) => ({ ...c }));
  const calls = [];
  let nextId = 1;
  const posted = [];
  return {
    calls, channels, posted,
    async createChannel({ name }) {
      calls.push({ method: 'conversations.create', name });
      if (channels.some((c) => c.name === name && !c.is_archived)) return { ok: false, error: 'name_taken' };
      const ch = { id: `C${String(nextId++).padStart(4, '0')}`, name, is_archived: false };
      channels.push(ch);
      return { ok: true, channel: { id: ch.id, name: ch.name } };
    },
    async listChannels({ cursor = null, excludeArchived = true } = {}) {
      calls.push({ method: 'conversations.list', cursor });
      const visible = channels.filter((c) => (excludeArchived ? !c.is_archived : true));
      return { ok: true, channels: visible.map((c) => ({ id: c.id, name: c.name, is_archived: c.is_archived })), nextCursor: null };
    },
    async archiveChannel({ channel }) {
      calls.push({ method: 'conversations.archive', channel });
      const ch = channels.find((c) => c.id === channel);
      if (!ch) return { ok: false, error: 'channel_not_found' };
      if (ch.is_archived) return { ok: false, error: 'already_archived' };
      ch.is_archived = true;
      return { ok: true };
    },
    async sendToOwner({ channel, threadTs, text }) {
      calls.push({ method: 'chat.postMessage', channel, threadTs });
      posted.push({ channel, threadTs, text });
      return { delivered: true, ts: `${Date.now()}.000` };
    },
    async start() { return { connected: true }; },
    stop() {},
  };
}

// A gateway stub: records every enqueue, and answers `inspect ticker` with a live
// session bound to the LAST queue row, so a follow-up can resolve its chain thread.
function makeFakeForwarder() {
  const enqueued = [];
  let nextQueueId = 100;
  let lastQueueId = null;
  return {
    enqueued,
    async forward(intent, payload) {
      const jobId = nextQueueId++;
      enqueued.push({ intent, payload, jobId });
      if (payload && payload.job_id && payload.args && payload.args.prompt !== undefined) lastQueueId = jobId;
      return { ok: true, result: { jobId } };
    },
    async inspect(target) {
      if (target !== 'ticker') return { ok: true, result: {} };
      return {
        ok: true,
        result: {
          live_sessions: lastQueueId == null ? [] : [{ exec_id: 7, queue_id: lastQueueId, thread: 'exec-7' }],
          recent_ticks: [],
        },
      };
    },
  };
}

function makeBridge({ existing = [] } = {}) {
  const slack = makeFakeSlack({ existing });
  const forwarder = makeFakeForwarder();
  const config = {
    gatewayAddr: '127.0.0.1:0',
    bridgeToken: 'stub',
    sessionJobId: 'chat-launch',
    sessionProfile: 'fallback-profile',
    masterProfile: 'master-profile',
    goalProfile: 'goal-profile',
    sendMessageJobId: 'send-message',
    workdir: null,
    channelPrefix: PREFIX,
    allowlist: [USER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  };
  const built = buildBridge(config, {
    logger: () => {},
    makeTransport: () => slack,
    forwarderImpl: forwarder,
    replyLegOptions: { pollMs: 3600000 }, // the reply leg is not under test here
  });
  return { ...built, slack, forwarder, config };
}

// A Slack message event as the transport shapes it.
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

  // 1 — NAME DERIVATION IS A BIJECTION, and a non-derivable id is REFUSED rather
  //     than sanitized (sanitizing would let two goals share one channel).
  {
    const name = channelNameForGoal('build-core-daemon-mvp', PREFIX);
    const back = goalIdFromChannelName(name, PREFIX);
    let refusedBad = false;
    try { channelNameForGoal('Build Core!', PREFIX); } catch { refusedBad = true; }
    let refusedLong = false;
    try { channelNameForGoal('g'.repeat(90), PREFIX); } catch { refusedLong = true; }
    check('name derivation round-trips (bijection)', name === 'test-build-core-daemon-mvp' && back === 'build-core-daemon-mvp', { name, back });
    check('non-derivable goal id refused, never sanitized', refusedBad, {});
    check('over-long derived name refused', refusedLong, {});
  }

  // 2 — CREATION (open point a): idempotent. Second call creates NOTHING.
  {
    const { bridge, slack } = makeBridge();
    const first = await bridge.registerGoal('goal-one');
    const second = await bridge.registerGoal('goal-one');
    const creates = slack.calls.filter((c) => c.method === 'conversations.create');
    check('registerGoal creates the channel once', first.ok && first.created === true && first.channelId != null, { first });
    check('registerGoal is idempotent — second call creates nothing', second.ok && second.created === false && creates.length === 1, { second, createCalls: creates.length });
  }

  // 3 — `name_taken` is the ADOPT path, not an error.
  {
    const { bridge, slack } = makeBridge({ existing: [{ id: 'C_PRE', name: 'test-goal-two', is_archived: false }] });
    const res = await bridge.registerGoal('goal-two');
    const creates = slack.calls.filter((c) => c.method === 'conversations.create');
    check('name_taken adopts the existing channel', res.ok && res.created === false && res.channelId === 'C_PRE' && res.reason === 'adopted', { res, createAttempts: creates.length });
  }

  // 4 — RECOVERY from the workspace alone: the property that lets an in-memory
  //     bridge survive a restart with no persistence.
  {
    const { bridge, goalChannels } = makeBridge({ existing: [
      { id: 'C_A', name: 'test-alpha', is_archived: false },
      { id: 'C_B', name: 'test-beta', is_archived: false },
      { id: 'C_X', name: 'random-watercooler', is_archived: false },
    ] });
    await bridge.start();
    check('recover() rebinds every derivable channel from the workspace', goalChannels.channelForGoal('alpha') === 'C_A' && goalChannels.channelForGoal('beta') === 'C_B', { alpha: goalChannels.channelForGoal('alpha'), beta: goalChannels.channelForGoal('beta') });
    check('recover() ignores channels that derive no goal id', goalChannels.goalForChannel('C_X') === null && goalChannels.size() === 2, { size: goalChannels.size() });
    bridge.stop();
  }

  // 5 — ROUTING (criteria 2 + 3). A DM is master traffic; a mapped channel is goal
  //     traffic; anything else is refused with NOTHING enqueued.
  {
    const { bridge, forwarder } = makeBridge();
    const reg = await bridge.registerGoal('goal-three');
    const chan = reg.channelId;

    const dm = await bridge.onChatMessage(msg({ channel: 'D_IM', ts: '1.1', channelType: 'im' }));
    const goal = await bridge.onChatMessage(msg({ channel: chan, ts: '2.1', channelType: 'channel' }));
    const stray = await bridge.onChatMessage(msg({ channel: 'C_STRAY', ts: '3.1', channelType: 'channel' }));
    const group = await bridge.onChatMessage(msg({ channel: 'G_MPIM', ts: '4.1', channelType: 'mpim' }));

    const dmJob = forwarder.enqueued.find((e) => e.payload.args && e.payload.args.profile === 'master-profile');
    const goalJob = forwarder.enqueued.find((e) => e.payload.args && e.payload.args.profile === 'goal-profile');

    check('DM routes as MASTER traffic, never goal traffic', dm.forwarded === true && dm.route === 'master' && dm.goalId === null && Boolean(dmJob), { dm });
    check('mapped channel routes as GOAL traffic, attributed to its goal', goal.forwarded === true && goal.route === 'goal' && goal.goalId === 'goal-three' && Boolean(goalJob), { goal });
    check('unmapped channel refused — NOTHING enqueued', stray.forwarded === false && stray.reason === 'unroutable-surface', { stray });
    check('group DM (mpim) refused — neither master nor goal', group.forwarded === false && group.reason === 'unroutable-surface', { group });
    check('exactly two jobs enqueued across four inbound messages', forwarder.enqueued.length === 2, { enqueued: forwarder.enqueued.length });
  }

  // 6 — THE 1:1 INVARIANT: the goal thread is the CHANNEL, so two messages posted at
  //     different Slack thread roots are ONE conversation. If the bridge sharded by
  //     `thread_ts` this would open a SECOND session instead of a follow-up — the
  //     precise failure d-channel-per-goal exists to prevent.
  {
    const { bridge, forwarder } = makeBridge();
    const reg = await bridge.registerGoal('goal-four');
    const chan = reg.channelId;
    const one = await bridge.onChatMessage(msg({ channel: chan, ts: '10.1', channelType: 'channel' }));
    const two = await bridge.onChatMessage(msg({ channel: chan, ts: '11.1', channelType: 'channel', text: 'second' }));
    const sessionCreates = forwarder.enqueued.filter((e) => e.payload.args && e.payload.args.prompt !== undefined);
    const sendMessages = forwarder.enqueued.filter((e) => e.payload.job_id === 'send-message');
    check('one channel = one goal thread (second message is a FOLLOW-UP, not a second session)',
      one.leg === 'session-create' && two.leg === 'follow-up' && sessionCreates.length === 1 && sendMessages.length === 1,
      { firstLeg: one.leg, secondLeg: two.leg, sessionCreates: sessionCreates.length, sendMessages: sendMessages.length });
    check('follow-up addresses the goal thread and never send-to-session',
      two.thread === 'exec-7' && sendMessages.every((e) => e.intent === 'enqueue-job'),
      { thread: two.thread, intents: sendMessages.map((e) => e.intent) });
  }

  // 7 — REPLY ADDRESS: goal traffic answers IN-CHANNEL, so the goal's conversation
  //     is visible where the owner is looking; a threaded question is answered in
  //     its thread.
  {
    const { bridge, slack } = makeBridge();
    const reg = await bridge.registerGoal('goal-five');
    const chan = reg.channelId;
    await bridge.onChatMessage(msg({ channel: chan, ts: '20.1', channelType: 'channel' }));
    await bridge.deliverToOwner({ chatThreadId: chan, text: 'reply' });
    const post = slack.posted[slack.posted.length - 1];
    check('goal reply posts in-channel at top level', post && post.channel === chan && (post.threadTs == null), { post: post && { channel: post.channel, threadTs: post.threadTs } });

    await bridge.onChatMessage(msg({ channel: chan, ts: '21.1', threadTs: '20.9', channelType: 'channel' }));
    await bridge.deliverToOwner({ chatThreadId: chan, text: 'threaded reply' });
    const post2 = slack.posted[slack.posted.length - 1];
    check('a threaded inbound is answered inside its thread', post2 && post2.threadTs === '20.9', { post2: post2 && { threadTs: post2.threadTs } });
  }

  // 8 — CLOSE-TIME LIFECYCLE (open point b): archive, never delete; idempotent; and
  //     a REFUSED archive keeps the binding, because the channel is still live.
  {
    const { bridge, slack, goalChannels } = makeBridge();
    const reg = await bridge.registerGoal('goal-six');
    const chan = reg.channelId;
    const retired = await bridge.closeGoal('goal-six');
    const archived = slack.channels.find((c) => c.id === chan);
    const again = await bridge.closeGoal('goal-six');
    check('closeGoal ARCHIVES the channel (never deletes it)', retired.ok && retired.archived === true && archived && archived.is_archived === true && slack.channels.some((c) => c.id === chan), { retired });
    check('archived channel is unbound — later traffic is no longer goal traffic', goalChannels.goalForChannel(chan) === null, {});
    check('closeGoal is idempotent on an already-retired goal', again.ok === true && again.reason === 'not-mapped', { again });

    // A REFUSED archive (e.g. missing scope) must NOT unbind: the channel is live.
    const reg2 = await bridge.registerGoal('goal-seven');
    slack.archiveChannel = async () => ({ ok: false, error: 'missing_scope' });
    const failed = await bridge.closeGoal('goal-seven');
    check('a refused archive fails loud and KEEPS the binding', failed.ok === false && goalChannels.channelForGoal('goal-seven') === reg2.channelId, { failed });
  }

  // 9 — THE NEVER-INVITE GUARD (`r-slack-etiquette`), enforced as an ABSENCE in the
  //     runtime source. A guard the code cannot hold is stronger than a policy an
  //     agent must remember at 4 AM.
  {
    const runtime = fs.readdirSync(SRC_DIR).filter((f) => f.endsWith('.js')).sort();
    const hits = [];
    for (const f of runtime) {
      const code = fs.readFileSync(path.join(SRC_DIR, f), 'utf8')
        .replace(/\/\*[\s\S]*?\*\//g, ' ')
        .replace(/(^|[^:])\/\/[^\n]*/g, '$1');
      for (const re of [/conversations\.invite/, /conversations\.kick/, /conversations\.delete/, /admin\.conversations/]) {
        if (re.test(code)) hits.push({ file: f, pattern: String(re) });
      }
    }
    check('bridge source contains NO invite/kick/delete channel call', hits.length === 0, { scanned: runtime, hits });
  }

  const pass = checks.every((c) => c.pass);
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-goal-channel', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-goal-channel EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
}

main();
