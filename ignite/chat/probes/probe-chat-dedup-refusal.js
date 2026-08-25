'use strict';

// THE DAEMON QUEUE REPLACES THE BRIDGE'S RETRIES — AND WHAT THE BRIDGE STILL OWES (P2).
//
// ⚠ WHAT THIS PROBE USED TO ASSERT, AND WHY IT NO LONGER DOES. The store's idempotent door
// dedups `launch-agent` enqueues on a (run, seat) key and returns BEFORE the INSERT, so a
// suppressed call's `args` — the user's text — were DISCARDED. The bridge therefore HELD that text
// and re-fired it when the seat freed: a queue reimplemented inside a transport that restarts, with
// a give-up notice for the case where it ran out of patience. Every arm of that machinery is gone.
// `forwardSessionCreate` now sends `on_seat_busy: 'queue'` and the DAEMON queues the row.
//
// The old arm that most needed rewriting asserted that a NEW inbound message DROPS the held one.
// That was correct for a bridge holding text it might double-send; it encodes LOSS in a world where
// the daemon holds the message instead, and it is deleted rather than adapted.
//
// WHAT THE BRIDGE STILL OWES, and what this probe now covers — the two things a queue that never
// refuses cannot do for us, both of which must happen BEFORE the enqueue:
//   (1) the BYTE-IDENTICAL DUPLICATE (owner-observed 2026-08-12): the owner's DM arrived twice,
//       byte-identical, 22 s apart across a Socket Mode drop/reconnect — two GENUINE Slack messages
//       with different ts, invisible to the transport's redelivery guard. The door used to absorb
//       the second; a daemon queue would run it as a second full conversation.
//   (2) the PER-SEAT PENDING CAP: an unbounded queue behind a busy seat means the owner's five
//       impatient messages become five sessions, hours later, each answering a stale question.
//
// ⚠ THE ASSERTIONS ARE COUNTS, NEVER PRESENCE — the same reasoning the deleted arms were built on.
// Against a bridge without the guards, the duplicate arm reads 2 and the cap arm reads 1; presence
// would pass either way. ARM R replays both against a SCRATCH COPY of chat-bridge.js with the guard
// block cut out, and asserts the mutation actually altered the source first.
//
// ⚠ THE FORWARDER IS A STUB, AND THAT IS NOW THE HONEST CHOICE. The arms this file used to run
// against a throwaway daemon existed to prove the REAL door's field names (`deduped`/`because`) and
// that suppression really discards the payload. Neither is what the bridge keys on any more: the
// bridge's side of the contract is the `on_seat_busy` field it SENDS and the `inspect queue` rows it
// READS, both asserted here directly. The daemon half is the daemon's own probe's business.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { makeCapture, nowMs } = require('./lib');
const forwardPathModule = require('../forward-path');
const { createThreadMap } = require('../thread-map');
const { createAllowlist } = require('../allowlist');
const { buildBridge } = require('../index');
const { createChatBridge } = require('../chat-bridge');

const OUT = path.join(__dirname, 'probe-chat-dedup-refusal.out');
const BRIDGE_SRC = path.join(__dirname, '..', 'chat-bridge.js');
// The scratch copy MUST live beside the original: chat-bridge.js requires `./forward-path`,
// `./reply-leg`, `./live-sessions` and `./bus-ferry`, none of which resolve from a tmpdir or from
// this probes/ folder. Removed in `finally`. It is not named `probe-*` and does not sit in a
// `probes/` dir, so the suite's discovery never sees it.
const scratchPath = path.join(__dirname, '..', `chat-bridge.__capscratch-${process.pid}.js`);

const USER = 'U_OWNER';
const SEAT = '/shared/master/seat';   // every master sitting homes here — one seat, many threads

// ── THE STUB DAEMON DOOR ─────────────────────────────────────────────────────────────────────
// It ENQUEUES EVERYTHING, which is the new daemon's behaviour under `on_seat_busy: 'queue'`: a
// create arriving at a busy seat becomes a queue row rather than a discarded payload. `queueRows`
// is what `inspect queue` returns — the cap's only input.
function makeDoor({ queueRows = [] } = {}) {
  const enqueued = [];
  let nextId = 500;
  const door = {
    enqueued,
    queueRows,
    liveSessions: [],
    inspectCalls: [],
    failQueueInspect: false,
    async forward(intent, payload) {
      if (intent === 'record-bus-answer') {
        enqueued.push({ intent, payload, jobId: null });
        return { ok: true, result: { recorded: true, msg_id: 1, re: null } };
      }
      if (intent === 'live-feed') {
        enqueued.push({ intent, payload, jobId: null });
        return { ok: true, result: { fed: false, reason: 'no-warm-session' } };
      }
      const jobId = nextId++;
      enqueued.push({ intent, payload, jobId });
      return { ok: true, result: { jobId } };
    },
    async inspect(target) {
      door.inspectCalls.push(target);
      if (target === 'queue') {
        if (door.failQueueInspect) return { ok: false, error: { code: 'TRANSPORT', message: 'scripted queue read failure' } };
        return { ok: true, result: { target: 'queue', rows: door.queueRows } };
      }
      if (target === 'ticker') {
        return { ok: true, result: { target: 'ticker', recent_ticks: [], live_sessions: door.liveSessions } };
      }
      return { ok: true, result: { recent_ticks: [], live_sessions: door.liveSessions } };
    },
  };
  return door;
}

// A pending queue row as the wire returns it (heart-store `queue` SELECT *): `args` is JSON TEXT,
// and `workdir` inside it is the seat the row homes at — exactly what the cap counts.
const queueRow = (workdir, prompt) => ({
  queue_id: Math.floor(Math.random() * 1e6), job_id: 'chat-launch',
  args: JSON.stringify({ prompt, workdir }), run_at: '2026-08-17T00:00:00Z',
});

function makeFakeSlack() {
  const posted = [];
  return {
    posted,
    async authTest() { return { ok: true, userId: 'U_BOT' }; },
    async createChannel() { return { ok: false, error: 'name_taken' }; },
    async listChannels() { return { ok: true, channels: [], nextCursor: null }; },
    async archiveChannel() { return { ok: true }; },
    async sendToOwner({ channel, threadTs, text }) { posted.push({ channel, threadTs, text }); return { delivered: true, ts: '1.0' }; },
    async start() { return { connected: true }; },
    stop() {},
  };
}

const BRIDGE_CONFIG = {
  gatewayAddr: '127.0.0.1:0', bridgeToken: 'stub',
  sessionJobId: 'chat-launch', sendMessageJobId: 'send-message',
  workdir: SEAT, workspaceRoot: null, channelPrefix: 'test-',
  stateFile: null, allowlist: [USER],
  slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
};

function makeBridgeRig({ stateFile = null, door = makeDoor(), logger = () => {} } = {}) {
  const slack = makeFakeSlack();
  const built = buildBridge({ ...BRIDGE_CONFIG, stateFile }, {
    logger,
    makeTransport: () => slack,
    forwarderImpl: door,
    replyLegOptions: { pollMs: 3600000 }, // no timer passes; nothing here drives the leg
  });
  return { ...built, slack, door };
}

const dm = (ts, text) => ({
  chatUserId: USER, chatThreadId: `D_IM:${ts}`, text,
  _channel: 'D_IM', _threadTs: ts, _channelType: 'im', _inThread: false, _msgTs: ts,
});

// How many session-creates actually carried this text into the queue. The whole double-delivery
// question is a COUNT, never a presence.
const createsCarrying = (door, needle) => door.enqueued
  .filter((e) => e.payload.job_id === 'chat-launch' && String(e.payload.args && e.payload.args.prompt).includes(needle))
  .length;

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const checks = [];
  const check = (name, pass, detail = {}) => { checks.push({ name, pass, ...detail }); cap.log({ check: name, pass, ...detail }); };

  try {
    // ── ARM 1 · EVERY SESSION-CREATE ASKS THE DAEMON TO QUEUE, NEVER TO DEDUPE ────────────────
    //
    // The wire field IS the P2 change. Without it the daemon's default is `dedupe`: the create is
    // suppressed and the owner's text discarded, which is the loss the whole rework deletes.
    {
      const r = makeBridgeRig();
      await r.bridge.start();
      const out = await r.bridge.onChatMessage(dm('1.1', 'ARM1 start the audit'));
      const payload = r.door.enqueued[0] && r.door.enqueued[0].payload;
      check('arm1-session-create-carries-on_seat_busy-queue',
        out.forwarded === true && Boolean(payload) && payload.on_seat_busy === 'queue',
        { forwarded: out.forwarded, on_seat_busy: payload && payload.on_seat_busy, payloadKeys: payload && Object.keys(payload) });

      // …and it is the ONLY execution-shaped field the transport names. The bare-prompt / no-effort
      // discipline is unchanged: a queue instruction is not a launch instruction.
      check('arm1-control-the-payload-still-names-no-execution',
        Boolean(payload) && payload.effort === undefined && payload.profile === undefined
          && payload.session_mode === 'headless',
        { effort: payload && payload.effort, profile: payload && payload.profile, sessionMode: payload && payload.session_mode });

      // ── THE SEAT SHARD (2026-08-17) ────────────────────────────────────────────────────────
      // `queue` made a busy master seat lossless; it did not make it concurrent. EVERY DM homes at
      // the one configured workdir, so the daemon's seat key was identical for every conversation
      // and thread B waited behind thread A's turn. The shard is this transport's half: the thread
      // id, on the wire, verbatim — the daemon suffixes its seat key with it.
      const second = await r.bridge.onChatMessage(dm('1.2', 'ARM1 a different conversation entirely'));
      const p2 = r.door.enqueued[1] && r.door.enqueued[1].payload;
      check('arm1-session-create-carries-its-own-thread-as-seat_shard',
        payload.seat_shard === 'D_IM:1.1' && Boolean(p2) && p2.seat_shard === 'D_IM:1.2',
        { first: payload.seat_shard, second: p2 && p2.seat_shard, secondForwarded: second.forwarded });

      // ⚑ THE DISCRIMINATING HALF. A shard that were a CONSTANT would satisfy the check above's
      // shape and shard nothing — two conversations would still collide on one key.
      check('arm1-control-two-threads-get-DIFFERENT-shards',
        Boolean(p2) && payload.seat_shard !== p2.seat_shard,
        { a: payload.seat_shard, b: p2 && p2.seat_shard });
      r.bridge.stop();
    }

    // ── ARM 2 · ⚠ THE BYTE-IDENTICAL DUPLICATE IS DROPPED BEFORE THE ENQUEUE ──────────────────
    //
    // Two GENUINE Slack messages, same text, DIFFERENT threads — the observed incident exactly
    // (he re-sent across a reconnect, so the two DMs were two conversations sharing ONE seat). The
    // drop must happen before `enqueue-job`, because the daemon queue collapses nothing.
    {
      const r = makeBridgeRig();
      await r.bridge.start();
      const TEXT = 'ARM2 create a goal for the meeting digest';
      const first = await r.bridge.onChatMessage(dm('2.1', TEXT));
      const second = await r.bridge.onChatMessage(dm('2.2', TEXT));
      const notice = r.slack.posted[r.slack.posted.length - 1];

      check('arm2-the-duplicate-runs-EXACTLY-ONE-conversation',
        first.forwarded === true && second.forwarded === false
          && createsCarrying(r.door, 'ARM2') === 1,
        { firstForwarded: first.forwarded, secondForwarded: second.forwarded, secondReason: second.reason,
          createsCarryingTheText: createsCarrying(r.door, 'ARM2'),
          note: '2 = the duplicate agent chain a daemon queue would have run' });

      // The owner is never dropped in silence, and the notice leaks no internals (D111).
      check('arm2-the-owner-is-told-the-duplicate-was-not-sent-again',
        Boolean(notice) && /identical/i.test(notice.text) && /NOT sent again/i.test(notice.text)
          && !/queue|seat_key|exec|job_id|dedup|workdir|\d{2,}/i.test(notice.text),
        { notice: notice && notice.text });

      // ⚑ THE DISCRIMINATING CONTROL. A guard that dropped EVERY second message would pass both
      // checks above; two DIFFERENT messages must BOTH reach the queue, which is the whole point of
      // the daemon queue replacing the retries.
      const other = await r.bridge.onChatMessage(dm('2.3', 'ARM2 a COMPLETELY different question'));
      check('arm2-control-two-DIFFERENT-messages-are-BOTH-enqueued',
        other.forwarded === true
          && createsCarrying(r.door, 'a COMPLETELY different question') === 1
          && r.door.enqueued.filter((e) => e.payload.job_id === 'chat-launch').length === 2,
        { otherForwarded: other.forwarded, creates: r.door.enqueued.filter((e) => e.payload.job_id === 'chat-launch').length });
      r.bridge.stop();
    }

    // ── ARM 3 · THE PER-SEAT PENDING CAP ──────────────────────────────────────────────────────
    //
    // The signal is the DAEMON's own pending queue, read through `inspect queue` — not a counter
    // this process keeps, which would be wrong across a restart and wrong about rows already
    // launched. Rows are attributed to a seat by the `workdir` the enqueue itself put in `args`.
    {
      const rows = [1, 2, 3, 4, 5].map((n) => queueRow(SEAT, `chat-thread: D_IM:0.${n}\n\nwaiting ${n}`));
      const r = makeBridgeRig({ door: makeDoor({ queueRows: rows }) });
      await r.bridge.start();
      const out = await r.bridge.onChatMessage(dm('3.1', 'ARM3 one more question'));
      const notice = r.slack.posted[r.slack.posted.length - 1];

      check('arm3-a-sixth-message-at-a-backed-up-seat-is-REFUSED-and-never-enqueued',
        out.forwarded === false && out.reason === 'pending-cap'
          && createsCarrying(r.door, 'ARM3') === 0
          && Boolean(notice) && /already waiting/i.test(notice.text) && /hold on/i.test(notice.text)
          && !/seat_key|exec|job_id|workdir/i.test(notice.text),
        { forwarded: out.forwarded, reason: out.reason, enqueued: createsCarrying(r.door, 'ARM3'), notice: notice && notice.text });
      r.bridge.stop();
    }

    // ⚑ CONTROL A · UNDER the cap it goes through. Without this, a cap that refused everything
    // would pass the arm above.
    {
      const rows = [1, 2, 3, 4].map((n) => queueRow(SEAT, `chat-thread: D_IM:0.${n}\n\nwaiting ${n}`));
      const r = makeBridgeRig({ door: makeDoor({ queueRows: rows }) });
      await r.bridge.start();
      const out = await r.bridge.onChatMessage(dm('3.2', 'ARM3B still under the cap'));
      check('arm3-control-four-waiting-still-lets-the-fifth-through',
        out.forwarded === true && createsCarrying(r.door, 'ARM3B') === 1,
        { forwarded: out.forwarded, enqueued: createsCarrying(r.door, 'ARM3B') });
      r.bridge.stop();
    }

    // ⚑ CONTROL B · ANOTHER SEAT'S BACKLOG IS NOT THIS SEAT'S. The cap is per seat; counting every
    // pending row in the daemon would refuse a quiet seat because a busy goal was backed up.
    {
      const rows = [1, 2, 3, 4, 5, 6, 7].map((n) => queueRow('/some/other/goal/seat', `waiting ${n}`));
      const r = makeBridgeRig({ door: makeDoor({ queueRows: rows }) });
      await r.bridge.start();
      const out = await r.bridge.onChatMessage(dm('3.3', 'ARM3C a different seat is busy, not mine'));
      check('arm3-control-a-backlog-at-ANOTHER-seat-does-not-refuse-this-one',
        out.forwarded === true && createsCarrying(r.door, 'ARM3C') === 1,
        { forwarded: out.forwarded, enqueued: createsCarrying(r.door, 'ARM3C') });
      r.bridge.stop();
    }

    // ⚑ CONTROL C · THE CAP FAILS OPEN. A bridge that cannot read the queue cannot tell, and a
    // bridge that cannot tell must never refuse the owner's message.
    {
      const rows = [1, 2, 3, 4, 5, 6].map((n) => queueRow(SEAT, `waiting ${n}`));
      const door = makeDoor({ queueRows: rows });
      door.failQueueInspect = true;
      const r = makeBridgeRig({ door });
      await r.bridge.start();
      const out = await r.bridge.onChatMessage(dm('3.4', 'ARM3D the queue read is down'));
      check('arm3-control-an-unreadable-queue-FAILS-OPEN-and-still-delivers',
        out.forwarded === true && createsCarrying(r.door, 'ARM3D') === 1,
        { forwarded: out.forwarded, enqueued: createsCarrying(r.door, 'ARM3D') });
      r.bridge.stop();
    }

    // ── ARM 4 · A FOLLOW-UP IS NEVER CAPPED AND NEVER DEDUPED ─────────────────────────────────
    //
    // Both guards exist for the SESSION-CREATE door, which is the only one the seat key gates. A
    // follow-up rides `send-message` on a live chain — capping it would silence a conversation that
    // is already running, and de-duping it would swallow a legitimate repeated "yes".
    {
      const rows = [1, 2, 3, 4, 5, 6].map((n) => queueRow(SEAT, `waiting ${n}`));
      const r = makeBridgeRig({ door: makeDoor({ queueRows: rows }) });
      await r.bridge.start();
      r.threadMap.create('D_IM:4.1', { queueId: 42 });
      r.threadMap.bindSessionExecId('D_IM:4.1', 4242);
      const a = await r.bridge.onChatMessage(dm('4.1', 'ARM4 yes'));
      const b = await r.bridge.onChatMessage(dm('4.1', 'ARM4 yes'));
      const sends = r.door.enqueued.filter((e) => e.payload.job_id === 'send-message').length;
      check('arm4-follow-ups-on-a-live-chain-bypass-BOTH-guards',
        a.forwarded === true && b.forwarded === true && sends === 2,
        { first: a.forwarded, second: b.forwarded, reasonA: a.reason, reasonB: b.reason, sendMessages: sends });
      r.bridge.stop();
    }

    // ── ARM 5 · A PRE-QUEUE STATE FILE IS SURVIVED, AND ITS HELD TEXTS ARE NAMED ──────────────
    //
    // Exactly one such file exists on the box this ships to. loadState must not choke on the
    // retired `pendingRetries` key, must not restore it, and must NOT swallow the message in
    // silence — a message vanishing across a deploy is what the deleted feature existed to prevent.
    {
      const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-oldstate-'));
      const stateFile = path.join(stateDir, 'chat-state.json');
      fs.writeFileSync(stateFile, JSON.stringify({
        version: 1, savedAt: '2026-08-16T12:00:00Z',
        threads: {}, replyAddr: { 'D_IM:5.1': { channel: 'D_IM', threadTs: '5.1' } },
        pendingRetries: { 'D_IM:5.1': { text: 'ARM5 the message the old bridge was holding', route: { kind: 'master', goalId: null }, since: Date.now() } },
      }));
      const lines = [];
      const r = makeBridgeRig({ stateFile, logger: (o) => lines.push(o) });
      await r.bridge.start();
      const warn = lines.find((l) => l.level === 'warn' && /DISCARDING held re-submits/.test(l.message));
      const namesTheText = Boolean(warn) && JSON.stringify(warn.discarded || []).includes('the message the old bridge was holding');

      check('arm5-an-old-state-file-loads-and-its-held-text-is-NAMED-not-swallowed',
        r.bridge._replyAddr.has('D_IM:5.1') && Boolean(warn) && namesTheText,
        { restoredReplyAddr: r.bridge._replyAddr.has('D_IM:5.1'), warned: Boolean(warn), namesTheText,
          discarded: warn && warn.discarded });

      // …and the key does not come back on the next write.
      await r.bridge.onChatMessage(dm('5.2', 'ARM5 a new message'));
      const doc = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
      check('arm5-the-retired-key-is-not-written-back',
        doc.pendingRetries === undefined && Boolean(doc.replyAddr),
        { keys: Object.keys(doc) });
      r.bridge.stop();
      try { fs.rmSync(stateDir, { recursive: true, force: true }); } catch {}
    }

    // ── ARM 6 · THE NOTICES ARE FIXED STRINGS WITH NO INTERNALS (D111) ────────────────────────
    {
      const n = forwardPathModule.SEAT_BUSY_NOTICE;
      const clean = (s) => typeof s === 'string' && !/seat_key|exec|job_id|dedup|workdir|\d{2,}/i.test(s);
      // The seat-busy notice no longer promises a BRIDGE re-send and no longer asks for a manual
      // one: the daemon queue is what delivers it, and a manual re-send would be a second row.
      check('arm6-seat-busy-notice-says-QUEUED-and-asks-for-no-re-send',
        clean(n) && /queued/i.test(n) && !/please send it again/i.test(n) && !/automatically/i.test(n),
        { notice: n });
      check('arm6-the-retired-give-up-notice-is-gone-from-the-module',
        forwardPathModule.SEAT_BUSY_GAVE_UP_NOTICE === undefined,
        { stillExported: forwardPathModule.SEAT_BUSY_GAVE_UP_NOTICE });
    }

    // ── ARM 7 · LIVE HOLDER: no second launch-agent, bus written, arm() not called ────────────
    {
      const ws = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-liveholder-'));
      const goalId = 'hold-g';
      const seatDir = path.join(ws, '.rbtv', 'goals', goalId, 'seats', 'leader');
      fs.mkdirSync(seatDir, { recursive: true });
      const door = makeDoor();
      door.liveSessions = [{ exec_id: 77, status: 'running', workdir: seatDir }];
      const slack = makeFakeSlack();
      const threadMap = createThreadMap();
      const allowlist = createAllowlist({ allowed: [USER] });
      const goalChannels = { goalForChannel: (ch) => (ch === 'C_LIVE' ? goalId : null) };
      const bridge = createChatBridge({
        config: { ...BRIDGE_CONFIG, workspaceRoot: ws, stateFile: null },
        forwarder: door, transport: slack, allowlist, threadMap, goalChannels,
        logger: () => {},
        replyLegOptions: { pollMs: 3600000 },
      });
      await bridge.start();
      const first = await bridge.onChatMessage(dm('7.0', 'ARM7 a real new sitting first'));
      const pendingA = bridge.replyLeg._pending.get('D_IM:7.0');
      if (pendingA) pendingA.slowNoticed = true;
      bridge._agentThreads.set(`${goalId}#leader`, { threadTs: '7.1' });
      const agentMsg = {
        chatUserId: USER, chatThreadId: 'C_LIVE:7.1', text: 'ARM7 widen it',
        _channel: 'C_LIVE', _threadTs: '7.1', _channelType: 'channel', _inThread: true, _msgTs: '7.1',
      };
      const live = await bridge.onChatMessage(agentMsg);
      const launches = door.enqueued.filter((e) => e.intent !== 'record-bus-answer' && e.intent !== 'live-feed'
        && e.payload && e.payload.job_id === 'chat-launch');
      const busWrites = door.enqueued.filter((e) => e.intent === 'record-bus-answer');
      const nudges = door.enqueued.filter((e) => e.intent === 'live-feed');
      check('arm7-live-holder-does-not-enqueue-a-second-launch-agent',
        first.forwarded === true && live.forwarded === true && live.liveHolder === true
          && launches.length === 1 && !launches.some((e) => String(e.payload.args && e.payload.args.prompt).includes('ARM7 widen')),
        { firstForwarded: first.forwarded, live, launchCount: launches.length, intents: door.enqueued.map((e) => e.intent) });
      check('arm7-live-holder-writes-the-bus-and-nudges-by-workdir',
        busWrites.length === 1 && busWrites[0].payload.seat === 'leader'
          && nudges.length === 1 && String(nudges[0].payload.workdir).replace(/\/+$/, '') === seatDir.replace(/\/+$/, '')
          && nudges[0].payload.start === false,
        { bus: busWrites[0] && busWrites[0].payload, nudge: nudges[0] && nudges[0].payload });
      check('arm7-live-holder-does-not-arm-and-does-not-reset-slowNoticed',
        !bridge.replyLeg._pending.has('C_LIVE:7.1')
          && pendingA && pendingA.slowNoticed === true,
        { agentArmed: bridge.replyLeg._pending.has('C_LIVE:7.1'), slowNoticed: pendingA && pendingA.slowNoticed });
      bridge.stop();
      try { fs.rmSync(ws, { recursive: true, force: true }); } catch {}
    }

    // ── ARM R · RED ARM · the guard block cut out of a SCRATCH chat-bridge.js ─────────────────
    //
    // Without it arms 2 and 3 would pass identically against a bridge that had never been changed.
    const original = fs.readFileSync(BRIDGE_SRC, 'utf8');
    const GUARD_START = '    if (route && chatMsg.chatThreadId && !threadMap.has(chatMsg.chatThreadId) && allowlist.isAdmitted(chatMsg.chatUserId)) {';
    const GUARD_END = '    const outcome = await forwardPath.onChatMessage(chatMsg);';
    const startIdx = original.indexOf(GUARD_START);
    const endIdx = original.indexOf(GUARD_END, startIdx);
    const mutated = startIdx !== -1 && endIdx !== -1
      ? original.slice(0, startIdx) + original.slice(endIdx)
      : null;

    check('armR-mutation-actually-applied',
      mutated !== null && mutated !== original && !mutated.includes(GUARD_START) && mutated.length < original.length,
      mutated === null
        ? { detail: 'ANCHORS NOT FOUND — the guard block was not located in chat-bridge.js' }
        : { cutBytes: original.length - mutated.length });

    if (mutated) {
      fs.writeFileSync(scratchPath, mutated);
      const scratch = require(scratchPath);
      const build = (door) => {
        const slack = makeFakeSlack();
        const bridge = scratch.createChatBridge({
          config: { ...BRIDGE_CONFIG, stateFile: null },
          forwarder: door, transport: slack,
          allowlist: createAllowlist({ allowed: [USER] }),
          threadMap: createThreadMap(), goalChannels: null, logger: () => {},
          replyLegOptions: { pollMs: 3600000 },
        });
        return { bridge, slack, door };
      };

      const dupDoor = makeDoor();
      const u = build(dupDoor);
      await u.bridge.start();
      const T = 'ARMR the same question twice';
      await u.bridge.onChatMessage(dm('R.1', T));
      await u.bridge.onChatMessage(dm('R.2', T));
      check('armR-UNGUARDED-bridge-enqueues-the-duplicate-TWICE',
        createsCarrying(dupDoor, 'ARMR') === 2,
        { createsCarryingTheText: createsCarrying(dupDoor, 'ARMR'), note: '1 = the guard is still present, so arm 2 proves nothing' });
      u.bridge.stop();

      const capDoor = makeDoor({ queueRows: [1, 2, 3, 4, 5, 6].map((n) => queueRow(SEAT, `waiting ${n}`)) });
      const v = build(capDoor);
      await v.bridge.start();
      await v.bridge.onChatMessage(dm('R.3', 'ARMR past the cap'));
      check('armR-UNGUARDED-bridge-enqueues-past-the-cap',
        createsCarrying(capDoor, 'past the cap') === 1,
        { enqueued: createsCarrying(capDoor, 'past the cap'), note: '0 = the guard is still present, so arm 3 proves nothing' });
      v.bridge.stop();
    } else {
      check('armR-UNGUARDED-bridge-enqueues-the-duplicate-TWICE', false, { detail: 'SKIPPED — the mutation could not be built, so the red arm proves nothing' });
    }
  } finally {
    try { fs.unlinkSync(scratchPath); } catch {}
  }

  const pass = checks.every((c) => c.pass);
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-dedup-refusal', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-dedup-refusal EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
}

if (require.main === module) main();
