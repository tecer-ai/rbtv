'use strict';

// THE DOOR IS DEDUPING AND THE BRIDGE MUST NOTICE (ruling `d-q9-door`; Q9 §2 review 2026-08-08).
//
// The store's idempotent door dedups `launch-agent` enqueues on a (run, seat) key and returns
// BEFORE the INSERT, so a suppressed call's `args` — the user's text included — are DISCARDED and
// the caller is handed the HELD operation's queue id. The bridge homes EVERY session it creates at
// a SHARED seat (master traffic at `config.workdir`, goal traffic at that goal's `goal-master`), so
// a new thread opening while that seat holds a live turn is exactly the suppressed case. Pre-fix the
// bridge mapped the thread to the held id and logged success; the user's message was never enqueued,
// never delivered, and no error was raised.
//
// ⚠ THE MISSING COVERAGE THIS CLOSES: no probe in this tree exercised TWO THREADS AT ONE SEAT. Every
// existing chat probe drives one conversation at a time, and the whole defect lives in the second.
//
// ⚠ THE DOOR IS DRIVEN FOR REAL, never simulated. A stub forwarder returning `{deduped:true}` would
// prove only that the bridge reads a field a probe made up. This stands up the throwaway daemon —
// real heart store, real internal API, real gateway — fires thread A's row so a LIVE TURN genuinely
// holds the seat, and lets the real door suppress thread B. The live-turn surface is the one that
// matters: a pending row exists for ~3% of the ticker cycle, so production suppression is almost
// always a live turn.
//
// ⚠ ARMS 5-9 · AUTO-RE-SUBMIT (owner ruling task 7.541, 2026-08-11). The refusal above is honest
// but it made the HUMAN do the work: the notice told him to send it again. The bridge now holds
// the discarded text and re-fires it when the seat frees. The arm that matters is 7 — the
// SEQUENTIAL double the door cannot see (refused → seat frees → the human re-sends by hand → the
// retry fires afterwards → delivered TWICE) — and it asserts a COUNT, because presence passes
// against the very defect.
//
// ⚠ EVERY GREEN HERE CARRIES A RED ARM (arm 4). The same scenario is replayed against a SCRATCH COPY
// of forward-path.js with the guard cut out — the PRE-FIX code exactly — and it MUST map the thread
// to the held id and post no notice. Without it arms 1-3 would pass identically against a bridge
// that had never been changed. The mutation is asserted to have actually altered the source first.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { makeCapture, nowMs, startThrowawayDaemon } = require('./lib');
const forwardPathModule = require('../forward-path');
const { createThreadMap } = require('../thread-map');
const { createAllowlist } = require('../allowlist');
const { createGatewayForwarder } = require('../gateway-forwarder');
const { buildBridge } = require('../index');

const OUT = path.join(__dirname, 'probe-chat-dedup-refusal.out');
const FWD_SRC = path.join(__dirname, '..', 'forward-path.js');
// The scratch copy MUST live beside the original: forward-path.js requires `./config`, which does
// not resolve from a tmpdir or from this probes/ folder. Removed in `finally`. It is not named
// `probe-*` and does not sit in a `probes/` dir, so the suite's discovery never sees it.
const scratchPath = path.join(__dirname, '..', `forward-path.__dedupscratch-${process.pid}.js`);

const USER = 'U_OWNER';
const TEXT_A = 'first thread: please start the audit';
const TEXT_B = 'second thread: SHIP THE INVOICE TODAY';  // the text the pre-fix bridge swallowed

// A goal workspace whose `.rbtv/goals/<goal>/` carries an OPEN run with a goal-master seat — what
// `resolveGoalSeat` reads a goal session's workdir from (2026-08-06 ruling).
function seedGoalWorkspace(goalId) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-dedupws-'));
  const goalDir = path.join(root, '.rbtv', 'goals', goalId);
  // 7.607 E3: GOAL-DIRECT — the seat folder IS the home; there is no register to read.
  fs.mkdirSync(path.join(goalDir, 'seats', 'goal-master'), { recursive: true });
  return { root, seatDir: path.join(goalDir, 'seats', 'goal-master') };
}

// One forward path over the REAL gateway. `createFP` is a parameter so the red arm can build the
// same rig from the mutated scratch module instead of the real one.
function makeRig(createFP, daemon, { workdir = null, workspaceRoot = null } = {}) {
  const posted = [];
  const threadMap = createThreadMap();
  const forwarder = createGatewayForwarder({ gatewayAddr: daemon.gatewayAddr, token: daemon.bridgeToken });
  const config = {
    sessionJobId: 'chat-launch',
    sendMessageJobId: 'send-message',
    sessionProfile: 'worker',
    masterProfile: 'worker',
    goalProfile: 'worker',
    workdir,
    workspaceRoot,
  };
  const fp = createFP({
    forwarder,
    threadMap,
    allowlist: createAllowlist({ allowed: [USER] }),
    config,
    logger: null,
    deliver: async ({ chatThreadId, text }) => { posted.push({ chatThreadId, text }); return { delivered: true }; },
  });
  return { fp, threadMap, posted, forwarder };
}

// ── THE AUTO-RE-SUBMIT RIG (arms 5-8, task 7.541) ────────────────────────────────────────────
//
// These arms are about the BRIDGE'S OWN BOOKKEEPING around the refusal — holding the text,
// re-firing it, and above all DROPPING it when the human re-sends — so they drive a whole bridge
// (buildBridge, as probe-chat-state-persistence does) rather than a bare forward path.
//
// ⚠ AND THEY USE A STUB DOOR, which the header's "drive the door for real" rule permits here for
// arm 3b's exact reason: what the real door alone can prove — that `deduped`/`because` are the
// field names and that suppression really discards the text — is proved by arms 1-2 above, in this
// same probe, against the real store. What these arms need instead is a seat that frees ON DEMAND
// between two calls, which no throwaway daemon can be made to do deterministically. The busy flag
// IS the seat.
function makeDoor() {
  const enqueued = [];
  let nextId = 500;
  const door = {
    enqueued,
    busy: true,
    async forward(intent, payload) {
      const jobId = nextId++;
      if (door.busy && payload && payload.job_id === 'chat-launch') {
        // The real door's shape, measured in arms 1-2: it returns BEFORE the INSERT, so the args
        // are discarded and the caller gets the HELD operation's id.
        return { ok: true, result: { jobId: 499, deduped: true, because: 'seat-busy', seat_key: 'k' } };
      }
      enqueued.push({ intent, payload, jobId });
      return { ok: true, result: { jobId } };
    },
    async inspect() { return { ok: true, result: { recent_ticks: [], live_sessions: [] } }; },
  };
  return door;
}

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

function makeBridgeRig({ stateFile = null, door = makeDoor() } = {}) {
  const slack = makeFakeSlack();
  const built = buildBridge({
    gatewayAddr: '127.0.0.1:0', bridgeToken: 'stub',
    sessionJobId: 'chat-launch', sendMessageJobId: 'send-message',
    sessionProfile: 'worker', masterProfile: 'worker', goalProfile: 'worker',
    workdir: '/shared/master/seat', workspaceRoot: null, channelPrefix: 'test-',
    stateFile, allowlist: [USER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  }, {
    logger: () => {},
    makeTransport: () => slack,
    forwarderImpl: door,
    replyLegOptions: { pollMs: 3600000 }, // the sweep is driven by hand via replyLeg.tick()
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

// Fire a queue row so a LIVE TURN holds its seat (status `launching` — non-terminal).
function fireToLiveTurn(daemon, queueId) {
  return daemon.store.fireQueueRow({ queueId, now: new Date(Date.now() + 1000), tick: 1 });
}

// The closed `jobs_log.status` enum (ignite/CLAUDE.md § Session lifecycle states). Enumerated so
// the store sweep below reads EVERY execution, not just the pending queue — a FIRED row is deleted
// from `queue` and lives only in `jobs_log`, so a queue-only sweep would report "text absent" for
// the thread that was delivered perfectly well and pass this check for the wrong reason.
const ALL_TURN_STATUSES = ['launching', 'running', 'stalled', 'done', 'blocked', 'failed', 'killed'];

// Is the user's text anywhere in the store? The review's discriminating control: a suppressed
// create's text exists NOWHERE, which is what makes the loss silent.
function textInStore(daemon, needle) {
  const hit = (r) => String(r.args || '').includes(needle);
  if (daemon.store.listQueue().some(hit)) return true;
  return ALL_TURN_STATUSES.some((s) => daemon.store.listExecutionsByStatus(s).some(hit));
}

// ARMS 5-9 · THE AUTO-RE-SUBMIT ARMS, hoisted out of main() and EXPORTED. They need no daemon —
// only the bridge and the stub door — while arms 1-4 above cannot run without one. Keeping them
// callable on their own is what let the red-first proof run on a host where the throwaway daemon
// refuses to start (the POSIX 0600 senders-file gate). The suite still runs everything via main().
async function autoResubmitArms(check) {
  // ── ARM 5 · a refused message is HELD for automatic re-submit ─────────────────────────────
  {
    const r = makeBridgeRig();
    await r.bridge.start();
    const out = await r.bridge.onChatMessage(dm('5.1', 'ARM5 hold this for me'));
    const held = r.bridge._pendingRetries;
    check('arm5-refused-message-is-recorded-as-a-pending-re-submit',
      out.forwarded === false && Boolean(held && held.has('D_IM:5.1'))
        && (held && held.get('D_IM:5.1').text) === 'ARM5 hold this for me'
        && createsCarrying(r.door, 'ARM5') === 0,
      { forwarded: out.forwarded, reason: out.reason, pending: held ? held.size : 'NO SUCH TABLE',
        enqueued: createsCarrying(r.door, 'ARM5') });
    const notice = r.slack.posted[r.slack.posted.length - 1];
    check('arm5-notice-promises-the-automatic-re-send-and-asks-for-none',
      Boolean(notice) && notice.text === forwardPathModule.SEAT_BUSY_NOTICE
        && /automatically/i.test(notice.text) && !/please send it again/i.test(notice.text),
      { notice: notice && notice.text });
    r.bridge.stop();
  }

  // ── ARM 6 · the seat frees → the held message is re-submitted and DELIVERED ────────────────
  {
    const r = makeBridgeRig();
    await r.bridge.start();
    await r.bridge.onChatMessage(dm('6.1', 'ARM6 ship the invoice'));
    const heldBefore = createsCarrying(r.door, 'ARM6');

    // The sweep runs on the reply leg's EXISTING pass — no timer of its own. While the seat is
    // still held it changes nothing, which is the first half of the claim.
    await r.bridge.replyLeg.tick();
    const afterBusyTick = createsCarrying(r.door, 'ARM6');

    r.door.busy = false; // the turn ended; the seat is free
    await r.bridge.replyLeg.tick();

    check('arm6-re-submit-lands-when-the-seat-frees-and-not-before',
      heldBefore === 0 && afterBusyTick === 0 && createsCarrying(r.door, 'ARM6') === 1
        && Boolean(r.bridge._pendingRetries) && r.bridge._pendingRetries.size === 0
        && r.threadMap.has('D_IM:6.1') === true,
      { atRefusal: heldBefore, whileBusy: afterBusyTick, afterFree: createsCarrying(r.door, 'ARM6'),
        pendingLeft: r.bridge._pendingRetries ? r.bridge._pendingRetries.size : 'NO SUCH TABLE',
        mapped: r.threadMap.has('D_IM:6.1') });
    r.bridge.stop();
  }

  // ── ARM 7 · ⚠ THE CRITICAL ARM · a MANUAL re-send cancels the pending retry ────────────────
  //
  // The sequence the door cannot see, because it is SEQUENTIAL and not concurrent:
  //   refused → seat frees → the human re-sends by hand → the retry fires afterwards.
  // Without the drop guard both land and the owner's message is delivered TWICE. The assertion
  // is therefore a COUNT — presence would pass against the defect.
  {
    const r = makeBridgeRig();
    await r.bridge.start();
    await r.bridge.onChatMessage(dm('7.1', 'ARM7 SHIP THE INVOICE TODAY'));
    const heldAfterRefusal = Boolean(r.bridge._pendingRetries && r.bridge._pendingRetries.has('D_IM:7.1'));

    r.door.busy = false; // the seat frees
    // The human does exactly what the OLD notice told him to do — in the thread he was told it
    // in, which is the conversation the retry is keyed on.
    const manual = await r.bridge.onChatMessage({
      chatUserId: USER, chatThreadId: 'D_IM:7.1', text: 'ARM7 SHIP THE INVOICE TODAY',
      _channel: 'D_IM', _threadTs: '7.1', _channelType: 'im', _inThread: true, _msgTs: '7.2',
    });
    const droppedOnInbound = Boolean(r.bridge._pendingRetries) && !r.bridge._pendingRetries.has('D_IM:7.1');

    // …and the sweep runs afterwards, which is when the double would happen.
    await r.bridge.replyLeg.tick();
    await r.bridge.replyLeg.tick();

    check('arm7-manual-re-send-DROPS-the-pending-retry',
      heldAfterRefusal === true && droppedOnInbound === true,
      { heldAfterRefusal, droppedOnInbound,
        pending: r.bridge._pendingRetries ? Array.from(r.bridge._pendingRetries.keys()) : 'NO SUCH TABLE' });

    check('arm7-the-owners-message-is-delivered-EXACTLY-ONCE',
      manual.forwarded === true && createsCarrying(r.door, 'ARM7 SHIP THE INVOICE TODAY') === 1,
      { manualForwarded: manual.forwarded, createsCarryingTheText: createsCarrying(r.door, 'ARM7 SHIP THE INVOICE TODAY'),
        note: '2 = the double this guard exists to prevent' });
    r.bridge.stop();
  }

  // ── ARM 8 · the give-up bound fires and TELLS THE HUMAN ───────────────────────────────────
  //
  // The seat never frees. The retry is bounded and, at the bound, the owner is told honestly —
  // and told to send it again, which is safe precisely because nothing is held any more. The
  // window is reached by ageing the record rather than by adding a config knob for a probe.
  {
    const r = makeBridgeRig();
    await r.bridge.start();
    await r.bridge.onChatMessage(dm('8.1', 'ARM8 never lands'));
    const rec = r.bridge._pendingRetries && r.bridge._pendingRetries.get('D_IM:8.1');
    if (rec) rec.since = Date.now() - (11 * 60 * 1000); // past the 10-minute window
    const postedBefore = r.slack.posted.length;
    await r.bridge.replyLeg.tick();
    const last = r.slack.posted[r.slack.posted.length - 1];

    check('arm8-give-up-bound-drops-the-retry-and-says-so-in-the-thread',
      Boolean(rec) && r.bridge._pendingRetries.size === 0
        && r.slack.posted.length === postedBefore + 1
        && Boolean(last) && last.text === forwardPathModule.SEAT_BUSY_GAVE_UP_NOTICE
        && createsCarrying(r.door, 'ARM8') === 0,
      { hadRecord: Boolean(rec), pendingLeft: r.bridge._pendingRetries ? r.bridge._pendingRetries.size : 'NO SUCH TABLE',
        lastPost: last && last.text, enqueued: createsCarrying(r.door, 'ARM8') });
    r.bridge.stop();
  }

  // ── ARM 9 · a held re-submit SURVIVES A BRIDGE RESTART ────────────────────────────────────
  //
  // The bridge promised the owner it would send the message again. A systemd restart
  // (Restart=on-failure) must not swallow that promise, so the record rides the existing state
  // file — the same additive discipline the ferry cursors and agent threads ride.
  {
    const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-retrystate-'));
    const stateFile = path.join(stateDir, 'chat-state.json');
    const door = makeDoor();
    const a = makeBridgeRig({ stateFile, door });
    await a.bridge.start();
    await a.bridge.onChatMessage(dm('9.1', 'ARM9 survives a restart'));
    a.bridge.stop();
    const doc = JSON.parse(fs.readFileSync(stateFile, 'utf8'));

    const b = makeBridgeRig({ stateFile, door }); // a fresh process, same file, same daemon
    await b.bridge.start();
    const restored = Boolean(b.bridge._pendingRetries && b.bridge._pendingRetries.has('D_IM:9.1'));
    door.busy = false;
    await b.bridge.replyLeg.tick();

    check('arm9-a-held-re-submit-survives-a-restart-and-still-lands',
      Boolean(doc.pendingRetries && doc.pendingRetries['D_IM:9.1'])
        && restored === true && createsCarrying(door, 'ARM9') === 1,
      { onDisk: doc.pendingRetries ? Object.keys(doc.pendingRetries) : 'KEY ABSENT',
        restored, enqueuedAfterRestart: createsCarrying(door, 'ARM9') });
    b.bridge.stop();
    try { fs.rmSync(stateDir, { recursive: true, force: true }); } catch {}
  }

  // ── ARM 10 · ⚠ THE HELD DUPLICATE · one question, TWO Slack messages, ONE run ──────────────
  //
  // Measured 2026-08-12: the owner's DM reached the bridge twice, byte-identical, 22s apart with
  // DIFFERENT Slack ts (he re-sent across a Socket Mode reconnect). Two genuine messages, so the
  // transport's redelivery guard neither saw them nor should have. The door held the second
  // correctly — and arms 5-6 then ran it as a SECOND full conversation at the same seat when the
  // turn ended: duplicate agent chain, duplicate spend, the same garbled answer twice.
  //
  // ⚠ TWO CONVERSATIONS, ONE SEAT — the reason a per-thread check would not have caught this and
  // the drop is keyed on the seat home instead. Threads A and B are different; the master seat
  // they both home at is not.
  //
  // ⚠ THE ASSERTION IS A COUNT, and that is its own red arm: against the pre-fix bridge the held
  // text is re-submitted when the seat frees and this reads 2. Presence would pass either way —
  // the same reasoning arm 7 is built on.
  {
    const r = makeBridgeRig();
    await r.bridge.start();
    const TEXT = 'ARM10 create a goal for the meeting digest';

    r.door.busy = false;
    const first = await r.bridge.onChatMessage(dm('10.1', TEXT));
    r.door.busy = true; // that create is now a LIVE TURN holding the master seat

    // The SAME text, a second Slack message, its own thread — the observed incident exactly.
    const second = await r.bridge.onChatMessage(dm('10.2', TEXT));
    const heldAnything = Boolean(r.bridge._pendingRetries && r.bridge._pendingRetries.size > 0);
    const notice = r.slack.posted[r.slack.posted.length - 1];

    r.door.busy = false; // the turn ends — pre-fix, this is where the second chain was born
    await r.bridge.replyLeg.tick();
    await r.bridge.replyLeg.tick();

    check('arm10-identical-message-at-a-BUSY-seat-is-dropped-not-held',
      first.forwarded === true && second.forwarded === false && heldAnything === false,
      { firstForwarded: first.forwarded, secondForwarded: second.forwarded, secondReason: second.reason,
        pending: r.bridge._pendingRetries ? Array.from(r.bridge._pendingRetries.keys()) : 'NO SUCH TABLE' });

    check('arm10-the-duplicate-runs-EXACTLY-ONE-conversation',
      createsCarrying(r.door, 'ARM10') === 1,
      { createsCarryingTheText: createsCarrying(r.door, 'ARM10'),
        note: '2 = the duplicate agent chain observed on 2026-08-12' });

    // The door already promised an automatic re-send. Dropping in silence would make that a lie.
    check('arm10-the-owner-is-told-the-duplicate-was-not-sent-again',
      Boolean(notice) && /identical/i.test(notice.text) && /NOT sent again/i.test(notice.text)
        && !/queue|seat_key|exec|job_id|dedup|workdir|\d{2,}/i.test(notice.text),
      { notice: notice && notice.text });

    // ⚑ AND A DIFFERENT MESSAGE AT THE SAME BUSY SEAT IS STILL HELD — the discriminating control.
    // Without it a guard that dropped EVERY held message would pass all three checks above.
    {
      const r2 = makeBridgeRig();
      await r2.bridge.start();
      r2.door.busy = false;
      await r2.bridge.onChatMessage(dm('10.3', 'ARM10B first question'));
      r2.door.busy = true;
      const other = await r2.bridge.onChatMessage(dm('10.4', 'ARM10B a COMPLETELY different question'));
      const held = Boolean(r2.bridge._pendingRetries && r2.bridge._pendingRetries.has('D_IM:10.4'));
      r2.door.busy = false;
      await r2.bridge.replyLeg.tick();
      check('arm10-control-a-DIFFERENT-message-is-still-held-and-still-lands',
        other.forwarded === false && held === true
          && createsCarrying(r2.door, 'a COMPLETELY different question') === 1,
        { held, delivered: createsCarrying(r2.door, 'a COMPLETELY different question') });
      r2.bridge.stop();
    }
    r.bridge.stop();
  }

  // ── ARM 11 · A GATEWAY HARD REFUSAL IS NOT SILENCE (root-cause report 2026-08-12, defect 3) ──
  //
  // The sibling of every refusal above: `forwarder.forward` returns `{ok:false}` — gateway down,
  // token rejected, payload re-validated away — so NOTHING is enqueued and nothing will retry it.
  // That branch logged a warn and returned, and the owner's thread stayed empty; it was the last
  // TRUE SILENCE in the forward path. A bare forward path is enough here: the act under test is
  // one call and one notice, with no door, no seat and no bookkeeping in it.
  {
    const posted = [];
    const mkFp = () => forwardPathModule.createForwardPath({
      forwarder: { async forward() { return { ok: false, error: { code: 'E_TRANSPORT', message: 'connect ECONNREFUSED' } }; } },
      threadMap: createThreadMap(),
      allowlist: createAllowlist({ allowed: [USER] }),
      config: { sessionJobId: 'chat-launch', sendMessageJobId: 'send-message', workdir: '/shared/master/seat' },
      logger: null,
      deliver: async ({ chatThreadId, text }) => { posted.push({ chatThreadId, text }); return { delivered: true }; },
    });

    const res = await mkFp().forwardSessionCreate({
      chatThreadId: 'D_IM:11.1', text: 'ARM11 the gateway is refusing', route: { kind: 'master', goalId: null },
    });
    check('arm11-a-gateway-refused-session-create-TELLS-the-owner',
      res.forwarded === false && posted.length === 1
        && posted[0].chatThreadId === 'D_IM:11.1'
        && posted[0].text === forwardPathModule.GATEWAY_REFUSED_NOTICE
        // The D111 fixed-string discipline: no gateway internals reach chat.
        && !/E_TRANSPORT|ECONNREFUSED/.test(posted[0].text),
      { forwarded: res.forwarded, posted: posted.map((p) => p.text) });

    // ⚑ THE DISCRIMINATING CONTROL, and the reason the notice is `!retry`-guarded at all:
    // `chat-bridge.js#retryPending` treats any non-seat-busy refusal as its give-up and posts
    // SEAT_BUSY_GAVE_UP_NOTICE itself, so a notice here on the re-submit pass would put TWO lines
    // in the thread for ONE undelivered message. Drop the guard and this arm goes red; drop the
    // notice line entirely and the arm above does.
    const before = posted.length;
    await mkFp().forwardSessionCreate({
      chatThreadId: 'D_IM:11.2', text: 'ARM11 re-submit', route: { kind: 'master', goalId: null }, retry: true,
    });
    check('arm11-control-the-RE-SUBMIT-pass-posts-nothing-the-give-up-notice-is-the-bridge-s',
      posted.length === before, { postedOnRetry: posted.length - before });
  }
}

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const checks = [];
  const check = (name, pass, detail = {}) => { checks.push({ name, pass, ...detail }); cap.log({ check: name, pass, ...detail }); };

  let daemon = null;
  try {
    daemon = await startThrowawayDaemon();

    // ── ARM 1 · MASTER traffic — two DM/mention threads at ONE configured workdir ──────────────
    //
    // This is the LIVE-CONFIGURED shape on this deployment: `workdir` is set in the bridge config,
    // and `workdirFor` hands EVERY master sitting that same path, so all master traffic shares one
    // seat key. Two owner threads overlapping in time is therefore an ordinary Tuesday, not a
    // corner case — and `routeBusRowToMaster` mints a channel-master sitting per bus row.
    {
      const sharedWorkdir = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-master-seat-'));
      const rig = makeRig(forwardPathModule.createForwardPath, daemon, { workdir: sharedWorkdir });
      const route = { kind: 'master', goalId: null };

      const a = await rig.fp.forwardSessionCreate({ chatThreadId: 'D_IM:1.1', text: TEXT_A, route });
      const fired = a.forwarded ? fireToLiveTurn(daemon, a.queueId) : null;
      const b = await rig.fp.forwardSessionCreate({ chatThreadId: 'D_IM:2.2', text: TEXT_B, route });

      check('arm1-thread-A-enqueued-and-mapped',
        a.forwarded === true && rig.threadMap.has('D_IM:1.1') && Boolean(fired),
        { queueId: a.queueId, firedExecId: fired && fired.exec_id, firedStatus: fired && fired.status });

      // The whole defect: B must NOT be bound to A's turn.
      check('arm1-suppressed-create-writes-NO-mapping',
        b.forwarded === false && rig.threadMap.has('D_IM:2.2') === false,
        { forwarded: b.forwarded, reason: b.reason, mapped: rig.threadMap.has('D_IM:2.2') });

      check('arm1-refusal-is-NOT-reported-as-a-queued-success',
        b.forwarded === false && b.queueId === undefined && String(b.reason || '').startsWith('seat-busy-deduped'),
        { reason: b.reason, queueId: b.queueId });

      // ⚑ THE WORDING CHANGED AT TASK 7.541 and the assertion changed WITH it, deliberately.
      // The notice used to end "please send it again shortly" — an instruction that, now that the
      // bridge re-submits by itself, produces the DOUBLE DELIVERY arms 5-8 exist to prevent. It
      // must promise the automatic re-send and must NOT ask for a manual one.
      const notice = rig.posted[rig.posted.length - 1];
      check('arm1-honest-in-thread-notice-posted-to-THAT-thread',
        Boolean(notice) && notice.chatThreadId === 'D_IM:2.2'
          && notice.text === forwardPathModule.SEAT_BUSY_NOTICE
          && /sent again automatically/i.test(notice.text)
          && !/please send it again/i.test(notice.text),
        { posted: rig.posted.length, notice });

      // "Never drop text silently": the text the door discarded rides the refusal, so no caller
      // has to reconstruct what was not delivered.
      check('arm1-undelivered-text-present-in-the-refusal-path',
        b.undeliveredText === TEXT_B,
        { undeliveredText: b.undeliveredText, expected: TEXT_B });

      // The review's control, re-measured here: the text really is nowhere in the store. The
      // refusal is what makes that survivable rather than silent.
      check('arm1-control-suppressed-text-exists-NOWHERE-in-the-store',
        textInStore(daemon, TEXT_A) === true && textInStore(daemon, TEXT_B) === false,
        { threadA_inStore: textInStore(daemon, TEXT_A), threadB_inStore: textInStore(daemon, TEXT_B) });

      // The FIRST thread's follow-up leg is untouched — it rides `send-message`, which the door
      // does not key. This is also the TOLERANCE SWEEP: the only other bridge-side reader of an
      // enqueue response is this leg, and it is measured, not argued.
      const f = await rig.fp.forwardFollowUp({ chatThreadId: 'D_IM:1.1', text: 'follow-up on A', route });
      check('arm1-first-threads-follow-up-leg-UNAFFECTED',
        f.forwarded === true && f.leg === 'follow-up' && typeof f.queueId === 'number',
        { forwarded: f.forwarded, thread: f.thread, queueId: f.queueId, reason: f.reason });

      check('arm1-sweep-send-message-is-never-deduped-by-the-door',
        textInStore(daemon, 'follow-up on A') === true,
        { note: 'send-message enqueued a real row while the seat was held by a live turn' });
    }

    // ── ARM 2 · GOAL traffic — the path the Q9 review actually named ──────────────────────────
    //
    // `resolveGoalSeat` homes goal traffic at that goal's OPEN run's goal-master seat, a
    // completely different workdir derivation from arm 1 reaching the same shared-seat outcome.
    // The second create models the reachable shape: a thread map that does not hold the
    // conversation (a bridge restart before `state_file` persisted it, or a re-minted channel).
    {
      const ws = seedGoalWorkspace('goal-dedup');
      const route = { kind: 'goal', goalId: 'goal-dedup' };
      const rigA = makeRig(forwardPathModule.createForwardPath, daemon, { workspaceRoot: ws.root });
      const a = await rigA.fp.forwardSessionCreate({ chatThreadId: 'C_GOAL', text: 'goal thread A', route });
      const fired = a.forwarded ? fireToLiveTurn(daemon, a.queueId) : null;

      // A FRESH rig = a fresh thread map: the bridge no longer knows this conversation.
      const rigB = makeRig(forwardPathModule.createForwardPath, daemon, { workspaceRoot: ws.root });
      const b = await rigB.fp.forwardSessionCreate({ chatThreadId: 'C_GOAL', text: 'goal thread B LOST TEXT', route });

      check('arm2-goal-seat-resolved-and-held-by-a-live-turn',
        a.forwarded === true && Boolean(fired) && fired.status === 'launching',
        { queueId: a.queueId, seatDir: ws.seatDir, firedStatus: fired && fired.status });

      check('arm2-goal-suppressed-create-refuses-mapping-and-surfaces-the-text',
        b.forwarded === false && rigB.threadMap.has('C_GOAL') === false
          && b.undeliveredText === 'goal thread B LOST TEXT'
          && rigB.posted.length === 1 && rigB.posted[0].text === forwardPathModule.SEAT_BUSY_NOTICE,
        { forwarded: b.forwarded, reason: b.reason, mapped: rigB.threadMap.has('C_GOAL'), posted: rigB.posted.length });
    }

    // ── ARM 3 · the notice leaks NO internals (the D111 fixed-string discipline) ───────────────
    //
    // Every other refusal notice in this file is a fixed string carrying no reason, thread or
    // queue id. The new one must hold the same line, or the bridge starts narrating the daemon's
    // internals into the owner's chat.
    {
      const n = forwardPathModule.SEAT_BUSY_NOTICE;
      const g = forwardPathModule.SEAT_BUSY_GAVE_UP_NOTICE;
      const clean = (s) => typeof s === 'string' && !/queue|seat_key|exec|job_id|dedup|workdir|\d{2,}/i.test(s);
      check('arm3-notice-is-a-fixed-string-with-no-internals', clean(n), { notice: n });
      // Its give-up twin (task 7.541) holds the same line — it is the one the owner reads when the
      // re-submit was abandoned, and it is the ONLY one that asks him to send the message again.
      check('arm3-give-up-notice-is-a-fixed-string-with-no-internals',
        clean(g) && /send it again/i.test(g || ''), { notice: g });
    }

    // ── ARM 3b · NO REGRESSION for a daemon WITHOUT the door (the RUNNING one) ─────────────────
    //
    // The guard must fire on `deduped` being TRUE, never on the field merely being present or
    // absent. The daemon in production predates the door and answers a successful enqueue with a
    // bare `{jobId}` — if the guard read presence rather than truth, every live create would be
    // refused and the bridge would break on the deployment it runs on today.
    //
    // ⚠ THIS is the one arm a STUB forwarder belongs in, and the header's "drive the door for
    // real" rule is not bent by it: the SUPPRESSION direction must meet the real door (arms 1-2),
    // because only the real door proves the field names. This arm drives the OPPOSITE direction —
    // wire shapes the current door never emits (`deduped:false`) or emits only pre-restart
    // (absent) — which no real store here can produce. Synthesising them is the only way to pin
    // them, and getting them wrong costs the running deployment.
    {
      const shapes = [
        ['absent', { jobId: 7 }],                      // the RUNNING pre-door daemon's shape
        ['explicit-false', { jobId: 7, deduped: false }], // a door that answers symmetrically
      ];
      for (const [label, result] of shapes) {
        const posted = [];
        const threadMap = createThreadMap();
        const fp = forwardPathModule.createForwardPath({
          forwarder: { forward: async () => ({ ok: true, result }) },
          threadMap,
          allowlist: createAllowlist({ allowed: [USER] }),
          config: { sessionJobId: 'chat-launch', sessionProfile: 'worker', masterProfile: 'worker', workdir: '/tmp/p7-2-noregress' },
          logger: null,
          deliver: async ({ chatThreadId, text }) => { posted.push({ chatThreadId, text }); return { delivered: true }; },
        });
        const r = await fp.forwardSessionCreate({ chatThreadId: `N_IM:${label}`, text: 'no-regression', route: { kind: 'master', goalId: null } });
        check(`arm3b-${label}-deduped-maps-normally-and-posts-no-notice`,
          r.forwarded === true && r.queueId === 7 && threadMap.has(`N_IM:${label}`) === true
            && posted.length === 0 && r.reason === undefined,
          { shape: label, forwarded: r.forwarded, queueId: r.queueId, mapped: threadMap.has(`N_IM:${label}`), notices: posted.length });
      }
    }

    // ── ARM 4 · RED ARM · the PRE-FIX code, rebuilt by cutting the guard out ───────────────────
    const original = fs.readFileSync(FWD_SRC, 'utf8');
    const GUARD_START = '    if (res.result && res.result.deduped) {';
    const GUARD_END = '    const queueId = res.result && res.result.jobId;';
    const startIdx = original.indexOf(GUARD_START);
    const endIdx = original.indexOf(GUARD_END, startIdx);
    const mutated = startIdx !== -1 && endIdx !== -1
      ? original.slice(0, startIdx) + original.slice(endIdx)
      : null;

    // A mutation that did not mutate would make this arm pass for the wrong reason.
    check('arm4-red-arm-mutation-actually-applied',
      mutated !== null && mutated !== original && !mutated.includes(GUARD_START)
        && mutated.length < original.length,
      mutated === null
        ? { detail: 'ANCHORS NOT FOUND — the guard was not located in forward-path.js' }
        : { cutBytes: original.length - mutated.length, anchorPresentAfterCut: mutated.includes(GUARD_START) });

    if (mutated) {
      fs.writeFileSync(scratchPath, mutated);
      const scratch = require(scratchPath);
      const sharedWorkdir = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-redarm-seat-'));
      const rig = makeRig(scratch.createForwardPath, daemon, { workdir: sharedWorkdir });
      const route = { kind: 'master', goalId: null };

      const a = await rig.fp.forwardSessionCreate({ chatThreadId: 'R_IM:1.1', text: 'red arm A', route });
      if (a.forwarded) fireToLiveTurn(daemon, a.queueId);
      const b = await rig.fp.forwardSessionCreate({ chatThreadId: 'R_IM:2.2', text: 'red arm B', route });

      // The pre-fix defect, reproduced exactly: B is reported forwarded, mapped to A's queue id,
      // and nothing is posted. If the guard were decorative, this arm would look like arm 1.
      check('arm4-UNGUARDED-bridge-maps-the-new-thread-to-the-HELD-turn',
        b.forwarded === true && b.queueId === a.queueId && rig.threadMap.has('R_IM:2.2') === true
          && rig.posted.length === 0,
        { unguardedForwarded: b.forwarded, unguardedQueueId: b.queueId, heldQueueId: a.queueId,
          mapped: rig.threadMap.has('R_IM:2.2'), noticesPosted: rig.posted.length });
    } else {
      check('arm4-UNGUARDED-bridge-maps-the-new-thread-to-the-HELD-turn', false,
        { detail: 'SKIPPED — the mutation could not be built, so the red arm proves nothing' });
    }

    await autoResubmitArms(check);
  } finally {
    try { fs.unlinkSync(scratchPath); } catch {}
    if (daemon) { try { await daemon.close(); } catch {} }
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

module.exports = { autoResubmitArms };
