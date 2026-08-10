'use strict';

// TASK 7.58 — the goal↔channel bridge (owner ruling d-channel-per-goal). Proves the
// five task criteria plus the two settled open points (goal-channel-design.md), and
// the OWNER-INVITE guard (owner ruling 2026-08-10, issue C-3 — supersedes the former
// never-invite guard this probe used to assert as a source ABSENCE).
//
// Deliberately NOT a daemon probe: every claim here is about the bridge's own
// routing and lifecycle, so the gateway is a stub and Slack is a fake admin surface
// that RECORDS EVERY CALL. That makes the negative claims — "no second create",
// "nothing enqueued", "never invited" — checkable as call-log assertions rather than
// as absence of an error.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { makeCapture, nowMs } = require('./lib');
const { buildBridge } = require('../index');
const { channelNameForGoal, goalIdFromChannelName } = require('../goal-channel-map');

const OUT = path.join(__dirname, 'probe-chat-goal-channel.out');
const SRC_DIR = path.join(__dirname, '..');

const USER = 'U_OWNER';
const PREFIX = 'test-';        // the TEST namespace — `r-slack-etiquette`'s surface: no invite here
const REAL_PREFIX = 'goal-';   // a REAL goal deployment — where the owner IS invited at creation

// ── fakes ────────────────────────────────────────────────────────────────────

// A Slack workspace that records every admin call. `existing` seeds channels that
// were created out-of-band (the adopt + recover paths).
function makeFakeSlack({ existing = [], inviteError = null } = {}) {
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
    // The C-3 invite surface. Recording it is what makes both the POSITIVE claim ("the
    // owner is invited on a real creation") and the NEGATIVE ones ("never on a test
    // channel", "never on adopt", "never twice") call-log assertions.
    async inviteToChannel({ channel, users }) {
      calls.push({ method: 'conversations.invite', channel, users: [...users] });
      if (inviteError) return { ok: false, error: inviteError };
      const ch = channels.find((c) => c.id === channel);
      if (!ch) return { ok: false, error: 'channel_not_found' };
      ch.members = Array.from(new Set([...(ch.members || []), ...users]));
      return { ok: true, already: false };
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

// A workspace whose `.rbtv/goals/<goal>/` carries an OPEN run with a goal-master seat —
// what the forward path resolves a goal session's workdir from (2026-08-06 ruling). Every
// goal this probe drives traffic for must be seated, or the session-create is refused
// (which is itself asserted, in the mention-route probe).
function seedWorkspace(goalIds) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-goalws-'));
  for (const goalId of goalIds) {
    const goalDir = path.join(root, '.rbtv', 'goals', goalId);
    // 7.607 E3: GOAL-DIRECT — the seat folder IS the home; there is no register to read.
    fs.mkdirSync(path.join(goalDir, 'seats', 'goal-master'), { recursive: true });
  }
  return root;
}

function makeBridge({ existing = [], goals = [], prefix = PREFIX, ownerUser = USER, inviteError = null } = {}) {
  const workspaceRoot = seedWorkspace(goals);
  const slack = makeFakeSlack({ existing, inviteError });
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
    workspaceRoot,
    channelPrefix: prefix,
    ownerUser,
    allowlist: [USER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  };
  const built = buildBridge(config, {
    logger: () => {},
    makeTransport: () => slack,
    forwarderImpl: forwarder,
    replyLegOptions: { pollMs: 3600000 }, // the reply leg is not under test here
  });
  return { ...built, slack, forwarder, config, workspaceRoot };
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
    const { bridge, forwarder } = makeBridge({ goals: ['goal-three'] });
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
    const { bridge, forwarder } = makeBridge({ goals: ['goal-four'] });
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
    const { bridge, slack } = makeBridge({ goals: ['goal-five'] });
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

  // 9 — THE OWNER-INVITE GUARD (owner ruling 2026-08-10, issue C-3). The former
  //     never-invite ABSENCE assertion is SUPERSEDED, not deleted: its real content —
  //     `r-slack-etiquette`'s "the owner is added to NO test channel", plus "the bridge
  //     adds nobody else to anything" — is re-asserted below as four call-log claims on
  //     a workspace that records every invite, which is strictly stronger than a grep.
  const inviteCalls = (slack) => slack.calls.filter((c) => c.method === 'conversations.invite');

  // 9a — POSITIVE: a REAL goal channel, freshly CREATED ⇒ exactly one invite, of the
  //      configured owner and nobody else, into that same channel.
  {
    const { bridge, slack } = makeBridge({ prefix: REAL_PREFIX });
    const reg = await bridge.registerGoal('goal-eight');
    const invites = inviteCalls(slack);
    check('real goal-channel creation invites the OWNER, exactly once, and nobody else',
      reg.ok && reg.created === true && reg.ownerInvited === true
        && invites.length === 1 && invites[0].channel === reg.channelId
        && invites[0].users.length === 1 && invites[0].users[0] === USER,
      { reg, invites });

    // 9b — the cached arm invites nothing: idempotence covers the invite too.
    await bridge.registerGoal('goal-eight');
    check('a second registerGoal (cached) invites nobody again', inviteCalls(slack).length === 1, { invites: inviteCalls(slack).length });
  }

  // 9c — NEGATIVE, ADOPT: a channel that already existed is not a creation. No invite,
  //      and no backfill of channels the bridge did not just make.
  {
    const { bridge, slack } = makeBridge({ prefix: REAL_PREFIX, existing: [{ id: 'C_PRE2', name: 'goal-goal-nine', is_archived: false }] });
    const res = await bridge.registerGoal('goal-nine');
    check('the ADOPT path invites nobody (new channels only — no backfill)',
      res.ok && res.created === false && res.reason === 'adopted' && inviteCalls(slack).length === 0,
      { res, invites: inviteCalls(slack).length });
  }

  // 9d — NEGATIVE, TEST NAMESPACE: `r-slack-etiquette`'s actual scope. Under a `test-`
  //      prefix the owner is invited NOWHERE, creation or not.
  {
    const { bridge, slack } = makeBridge({ prefix: PREFIX });
    const reg = await bridge.registerGoal('goal-ten');
    check('a TEST-prefixed channel NEVER invites the owner (r-slack-etiquette)',
      reg.ok && reg.created === true && reg.ownerInvited === false && inviteCalls(slack).length === 0,
      { reg, invites: inviteCalls(slack).length });
  }

  // 9e — GRACEFUL DEGRADATION: a refused invite (the missing-scope case) must not fail
  //      the creation, the binding, or the goal's message flow.
  {
    const { bridge, slack, goalChannels } = makeBridge({ prefix: REAL_PREFIX, goals: ['goal-eleven'], inviteError: 'missing_scope' });
    const reg = await bridge.registerGoal('goal-eleven');
    const inbound = await bridge.onChatMessage(msg({ channel: reg.channelId, ts: '30.1', channelType: 'channel' }));
    check('a REFUSED invite is loud but harmless — channel created, bound, and carrying traffic',
      reg.ok === true && reg.created === true && reg.ownerInvited === false
        && goalChannels.channelForGoal('goal-eleven') === reg.channelId
        && inbound.forwarded === true && inbound.route === 'goal'
        && inviteCalls(slack).length === 1,
      { reg, inbound: { forwarded: inbound.forwarded, route: inbound.route } });
  }

  // 9f — NO OWNER CONFIGURED ⇒ the pre-ruling behaviour exactly: create, invite nobody.
  {
    const { bridge, slack } = makeBridge({ prefix: REAL_PREFIX, ownerUser: null });
    const reg = await bridge.registerGoal('goal-twelve');
    check('no configured owner ⇒ no invite attempted, creation unaffected',
      reg.ok && reg.created === true && reg.ownerInvited === false && inviteCalls(slack).length === 0,
      { reg, invites: inviteCalls(slack).length });
  }

  // 9g — THE SURVIVING ABSENCES. The invite is the ONE membership call that exists, and
  //      it lives in the transport; kick/delete/admin.* must still be nowhere.
  {
    const runtime = fs.readdirSync(SRC_DIR).filter((f) => f.endsWith('.js')).sort();
    const hits = [];
    let inviteInTransport = false;
    for (const f of runtime) {
      const code = fs.readFileSync(path.join(SRC_DIR, f), 'utf8')
        .replace(/\/\*[\s\S]*?\*\//g, ' ')
        .replace(/(^|[^:])\/\/[^\n]*/g, '$1');
      if (f === 'slack-socket-mode.js' && /conversations\.invite/.test(code)) inviteInTransport = true;
      for (const re of [/conversations\.kick/, /conversations\.delete/, /admin\.conversations/]) {
        if (re.test(code)) hits.push({ file: f, pattern: String(re) });
      }
    }
    check('bridge source still contains NO kick/delete/admin channel call', hits.length === 0, { scanned: runtime, hits });
    check('the ONE conversations.invite lives in the transport (slack-socket-mode.js)', inviteInTransport, {});
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
