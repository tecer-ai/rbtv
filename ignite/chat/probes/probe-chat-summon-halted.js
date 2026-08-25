'use strict';

// ── A NOTE ON A HALTED CHAIN MUST ALSO SUMMON (D28, 2026-08-20) ─────────────────────────────────
//
// MEASURED ROT (2026-08-20, goal `stools-canvas-audio-elevenlabs`): exec 30110 crashed (`--resume`
// fed a foreign-harness ref), the crash sweep marked the chain `failed` — OWNER-HALTED, which the
// ticker's wake-redispatch deliberately never wakes — and the owner's follow-ups (msgs 33266 and
// 33306, "how is the goal doing?") were filed as notes on thread exec-30028 with routed_at_tick
// NULL, forever. `forwardFollowUp` persisted each note and returned `forwarded: true`; nothing
// would ever read them.
//
// THE FIX under test: on the OWNER/chat routes only, a follow-up whose chain tail is `failed`
// (the one verdict nothing wakes) and whose seat has NO live sitting ALSO summons — drops the
// dead mapping and enqueues the ordinary queued session-create, so a fresh sitting spawns with
// the owner's text and the reply leg is armed for it. The note write stays (persistence).
//
// ARMS — the REAL `createForwardPath` over a REAL gateway + heart store (lib.js throwaway daemon;
// never the live daemon, never port 7431):
//   A  halted tail, no sitting      → note enqueued AND a chat-launch enqueued; mapping reminted
//   B  healthy tail (`done`)        → note only — the daemon's own wake owns delivery (NEVER a
//                                     second launch: the anti-double-deliver bound)
//   C  halted tail, LIVE sitting    → note only — the live-holder machinery owns the live case
//                                     (commit 63413504; dedup-refusal arm7's lesson)
//   D  agent route, halted tail     → note only — agent-route follow-up semantics are ratified
//                                     and untouched
//   E  halted tail, a session-create for this conversation ALREADY queued → no second create
//   F  MUTATION: the summon call cut out of a COPY → arm A's shape goes RED (the probe can fail)
//
// ⚑ Timing uses Node `Date.now()` — `date +%s%3N` is broken on this box (D64).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { startThrowawayDaemon, seedRunningExecution, makeCapture, nowMs } = require('./lib');
const { createGatewayForwarder } = require('../gateway-forwarder');
const { createThreadMap } = require('../thread-map');

const OUT = path.join(__dirname, 'probe-chat-summon-halted.out');
const FP = path.join(__dirname, '..', 'forward-path.js');

const checks = [];
function check(name, pass, detail = {}) {
  checks.push({ name, pass: Boolean(pass), ...detail });
  return Boolean(pass);
}

function scratchWorkspace(goal) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'p-summon-'));
  const seatDir = path.join(root, '.rbtv', 'goals', goal, 'seats', 'goal-master');
  fs.mkdirSync(seatDir, { recursive: true });
  return { root, seatDir, cleanup: () => { try { fs.rmSync(root, { recursive: true, force: true }); } catch {} } };
}

// One conversation fixture: a chain whose FIRST exec is seeded, ended, and stamped with a
// completion of the given status — the exact tail shape the summon gate reads.
function seedChain(store, senderId, { tailStatus }) {
  const ex = seedRunningExecution(store, { enqueuedBy: senderId });
  store.updateExecutionStatus(ex.exec_id, { status: tailStatus === 'failed' ? 'failed' : 'done' });
  store.recordMessage({
    type: 'completion', sender: 'ticker', thread: ex.thread,
    corpus: tailStatus === 'failed' ? 'crash sweep: exit=1' : 'clean exit: 0',
    status: tailStatus, createdAt: new Date(), execId: ex.exec_id,
  });
  return ex;
}

function queueRows(store, jobId) {
  return store.listQueue().filter((r) => r.job_id === jobId);
}

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const cleanups = [];
  let daemon;
  try {
    daemon = await startThrowawayDaemon();
    const forwarder = createGatewayForwarder({ gatewayAddr: daemon.gatewayAddr, token: daemon.bridgeToken });
    cap.log({ step: 'throwaway daemon up', gatewayAddr: daemon.gatewayAddr });

    function buildPath({ root, modulePath = FP }) {
      const { createForwardPath } = require(modulePath);
      const threadMap = createThreadMap({});
      const logs = [];
      const fp = createForwardPath({
        forwarder,
        threadMap,
        allowlist: { check: () => ({ allowed: true }) },
        config: { workspaceRoot: root, workdir: null, sessionJobId: 'chat-launch', sendMessageJobId: 'send-message' },
        logger: (o) => logs.push(o),
        deliver: async () => ({ delivered: true }),
      });
      return { fp, threadMap, logs };
    }

    // ── ARM A · halted tail, no live sitting → the note AND a summon ─────────────────────────
    {
      const w = scratchWorkspace('sumgoal-a'); cleanups.push(w.cleanup);
      const { fp, threadMap } = buildPath({ root: w.root });
      const ex = seedChain(daemon.store, daemon.bridgeSenderId, { tailStatus: 'failed' });
      const CHAN = 'C-SUM-A';
      threadMap.create(CHAN, { queueId: 1 });
      threadMap.bindSessionExecId(CHAN, ex.exec_id);
      const notesBefore = queueRows(daemon.store, 'send-message').length;
      const launchesBefore = queueRows(daemon.store, 'chat-launch').length;
      const res = await fp.onChatMessage({
        chatUserId: 'U-owner', chatThreadId: CHAN,
        text: 'how is the goal doing?',
        route: { kind: 'goal', goalId: 'sumgoal-a' },
      });
      cap.log({ arm: 'A', res });
      const notes = queueRows(daemon.store, 'send-message');
      const launches = queueRows(daemon.store, 'chat-launch');
      const note = notes[notes.length - 1];
      const noteArgs = note ? JSON.parse(note.args) : null;
      const launch = launches[launches.length - 1];
      const launchArgs = launch ? JSON.parse(launch.args) : null;
      check('A: the note is still persisted on the chain thread (the message survives whatever else happens)',
        notes.length === notesBefore + 1 && noteArgs && noteArgs.type === 'note' && noteArgs.thread === ex.thread,
        { noteArgs });
      check('A: a HALTED chain with no sitting ALSO summons — a chat-launch row is enqueued at the goal-master seat',
        launches.length === launchesBefore + 1 && launchArgs
          && /how is the goal doing/.test(String(launchArgs.prompt || ''))
          && launchArgs.workdir === w.seatDir,
        { launchArgs, launchDelta: launches.length - launchesBefore });
      check('A: the result carries the summon and reports it enqueued',
        res && res.summon && res.summon.summoned === true && res.summon.leg === 'session-create',
        { summon: res && res.summon });
      const entry = threadMap.get(CHAN);
      check('A: the dead mapping was reminted onto the summon\'s own queue row (the reply leg\'s watch key)',
        entry && Number(entry.queueId) === Number(launch && launch.queue_id) && entry.sessionExecId == null,
        { entry, launchQueueId: launch && launch.queue_id });
      check('A: the follow-up still reports forwarded (the note landed) with the summon riding the result',
        res && res.forwarded === true && res.leg === 'follow-up',
        { res: { forwarded: res && res.forwarded, leg: res && res.leg } });
    }

    // ── ARM B · healthy (`done`) tail → note only; the daemon wake owns delivery ─────────────
    {
      const w = scratchWorkspace('sumgoal-b'); cleanups.push(w.cleanup);
      const { fp, threadMap } = buildPath({ root: w.root });
      const ex = seedChain(daemon.store, daemon.bridgeSenderId, { tailStatus: 'done' });
      const CHAN = 'C-SUM-B';
      threadMap.create(CHAN, { queueId: 2 });
      threadMap.bindSessionExecId(CHAN, ex.exec_id);
      const launchesBefore = queueRows(daemon.store, 'chat-launch').length;
      const notesBefore = queueRows(daemon.store, 'send-message').length;
      const res = await fp.onChatMessage({
        chatUserId: 'U-owner', chatThreadId: CHAN, text: 'status?',
        route: { kind: 'goal', goalId: 'sumgoal-b' },
      });
      cap.log({ arm: 'B', res });
      check('B: a DONE tail wakes itself — the note is enqueued and NO second launch is minted',
        queueRows(daemon.store, 'send-message').length === notesBefore + 1
          && queueRows(daemon.store, 'chat-launch').length === launchesBefore
          && res && res.forwarded === true && !res.summon,
        { launchDelta: queueRows(daemon.store, 'chat-launch').length - launchesBefore, summon: res && res.summon });
    }

    // ── ARM C · halted tail but a LIVE sitting holds the seat → no summon ────────────────────
    {
      const w = scratchWorkspace('sumgoal-c'); cleanups.push(w.cleanup);
      const { fp, threadMap } = buildPath({ root: w.root });
      const ex = seedChain(daemon.store, daemon.bridgeSenderId, { tailStatus: 'failed' });
      // A DIFFERENT chain's live turn at the same seat folder — visible in ticker live_sessions.
      daemon.store.recordExecutionStart({
        jobId: 'chat-launch', actionType: 'launch-agent',
        args: JSON.stringify({ prompt: 'hi', workdir: w.seatDir }),
        enqueuedBy: daemon.bridgeSenderId, sessionMode: 'headless',
        firedTick: 1, firedAt: new Date(), sessionId: 'sess-holder-c', pid: 999997,
        profile: 'claude/claude-opus-5', workdir: w.seatDir,
      });
      const CHAN = 'C-SUM-C';
      threadMap.create(CHAN, { queueId: 3 });
      threadMap.bindSessionExecId(CHAN, ex.exec_id);
      const launchesBefore = queueRows(daemon.store, 'chat-launch').length;
      const res = await fp.onChatMessage({
        chatUserId: 'U-owner', chatThreadId: CHAN, text: 'anyone alive?',
        route: { kind: 'goal', goalId: 'sumgoal-c' },
      });
      cap.log({ arm: 'C', res });
      check('C: a LIVE sitting at the seat suppresses the summon (arm7 lesson: never a second launch-agent)',
        queueRows(daemon.store, 'chat-launch').length === launchesBefore
          && res && res.forwarded === true && !res.summon && threadMap.has(CHAN),
        { launchDelta: queueRows(daemon.store, 'chat-launch').length - launchesBefore, summon: res && res.summon });
    }

    // ── ARM D · agent route, halted tail → semantics untouched, no summon ────────────────────
    {
      const w = scratchWorkspace('sumgoal-d'); cleanups.push(w.cleanup);
      const { fp, threadMap } = buildPath({ root: w.root });
      const ex = seedChain(daemon.store, daemon.bridgeSenderId, { tailStatus: 'failed' });
      const CHAN = 'C-SUM-D:1.1';
      threadMap.create(CHAN, { queueId: 4 });
      threadMap.bindSessionExecId(CHAN, ex.exec_id);
      const launchesBefore = queueRows(daemon.store, 'chat-launch').length;
      const notesBefore = queueRows(daemon.store, 'send-message').length;
      const res = await fp.onChatMessage({
        chatUserId: 'U-owner', chatThreadId: CHAN, text: 'here is my answer',
        route: { kind: 'agent', goalId: 'sumgoal-d', agent: 'goal-master' },
      });
      cap.log({ arm: 'D', res });
      check('D: the AGENT route never summons — its follow-up semantics are ratified and untouched',
        queueRows(daemon.store, 'send-message').length === notesBefore + 1
          && queueRows(daemon.store, 'chat-launch').length === launchesBefore
          && res && res.forwarded === true && !res.summon,
        { launchDelta: queueRows(daemon.store, 'chat-launch').length - launchesBefore, summon: res && res.summon });
    }

    // ── ARM E · a session-create for this conversation is ALREADY queued → no second one ─────
    {
      const w = scratchWorkspace('sumgoal-e'); cleanups.push(w.cleanup);
      const { fp, threadMap } = buildPath({ root: w.root });
      const ex = seedChain(daemon.store, daemon.bridgeSenderId, { tailStatus: 'failed' });
      const CHAN = 'C-SUM-E';
      // A create for THIS conversation already waiting in the daemon queue — the same
      // `chat-thread:` correlation marker the reply leg's stillQueued reads.
      daemon.store.enqueue({
        jobId: 'chat-launch',
        args: JSON.stringify({ prompt: `chat-thread: ${CHAN}\n\nearlier message`, workdir: w.seatDir }),
        sessionMode: 'headless', triggerKind: 'scheduled',
        runAt: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
        enqueuedBy: daemon.bridgeSenderId,
      });
      threadMap.create(CHAN, { queueId: 5 });
      threadMap.bindSessionExecId(CHAN, ex.exec_id);
      const launchesBefore = queueRows(daemon.store, 'chat-launch').length;
      const res = await fp.onChatMessage({
        chatUserId: 'U-owner', chatThreadId: CHAN, text: 'ping again',
        route: { kind: 'goal', goalId: 'sumgoal-e' },
      });
      cap.log({ arm: 'E', res });
      check('E: an already-queued create for this conversation suppresses a SECOND summon (no double answer)',
        queueRows(daemon.store, 'chat-launch').length === launchesBefore
          && res && res.summon && res.summon.summoned === false && res.summon.reason === 'create-already-queued'
          && threadMap.has(CHAN),
        { launchDelta: queueRows(daemon.store, 'chat-launch').length - launchesBefore, summon: res && res.summon });
    }

    // ── ARM F · MUTATION: cut the summon out of a COPY — arm A's shape must go RED ───────────
    {
      const src = fs.readFileSync(FP, 'utf8');
      const target = '? await summonHaltedChain({ chatThreadId, text, route, chainThread: resolved.chainThread })';
      if (!src.includes(target)) {
        check('F: the mutation target still exists in the source', false, { target });
      } else {
        const mutated = src.replace(target, '? null');
        check('F: the mutation ALTERED the source (a no-op mutation proves nothing)', mutated !== src);
        const beside = path.join(__dirname, '..', `forward-path.MUTANT-${process.pid}.js`);
        fs.writeFileSync(beside, mutated);
        cleanups.push(() => { try { fs.unlinkSync(beside); } catch {} });
        const w = scratchWorkspace('sumgoal-f'); cleanups.push(w.cleanup);
        const { fp, threadMap } = buildPath({ root: w.root, modulePath: beside });
        const ex = seedChain(daemon.store, daemon.bridgeSenderId, { tailStatus: 'failed' });
        const CHAN = 'C-SUM-F';
        threadMap.create(CHAN, { queueId: 6 });
        threadMap.bindSessionExecId(CHAN, ex.exec_id);
        const launchesBefore = queueRows(daemon.store, 'chat-launch').length;
        await fp.onChatMessage({
          chatUserId: 'U-owner', chatThreadId: CHAN, text: 'lost forever?',
          route: { kind: 'goal', goalId: 'sumgoal-f' },
        });
        check('F: with the summon cut, the halted chain gets a note and NOTHING ELSE — the probe can fail',
          queueRows(daemon.store, 'chat-launch').length === launchesBefore,
          { launchDelta: queueRows(daemon.store, 'chat-launch').length - launchesBefore });
      }
    }
  } catch (err) {
    check('probe ran to completion without throwing', false, { error: err.message, stack: (err.stack || '').split('\n').slice(0, 6) });
  } finally {
    for (const c of cleanups.reverse()) { try { c(); } catch {} }
    try { daemon && await daemon.close(); } catch {}
  }

  const failed = checks.filter((c) => !c.pass);
  cap.log({ step: 'checks', total: checks.length, failed: failed.length, checks });
  const pass = failed.length === 0 && checks.length > 0;
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-summon-halted', pass, EXIT: exit, WALL_MS: wallMs, CHECK_COUNT: checks.length });
  process.stdout.write(`PROBE probe-chat-summon-halted EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length} FAILED=${failed.length}\n`);
  process.exit(exit);
}

main();
