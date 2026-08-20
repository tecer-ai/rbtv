'use strict';

// ── The LIVE-HOLDER branch must never lose the owner's message ───────────────────────────────
//
// MEASURED LOSS (2026-08-20 01:20:35Z, goal `meet-transcript-summarizer`): a top-level owner post
// in a goal channel found a live sitting at the goal-master seat. The branch logged "writing the
// bus and nudging", the nudge came back `no-warm-session`, and the branch logged "bus write still
// stands" and returned `forwarded: true`. Nothing was written: `recordBusAnswer` is `kind:'agent'`
// ONLY by design (a goal-channel post is the owner INITIATING, not answering an ask), so on a goal
// route it returns null before doing anything. Nothing was enqueued either, and no thread was
// mapped, so no reply leg could ever carry an answer back. The owner's message vanished while the
// bridge logged success.
//
// ARMS — driven against the REAL `createForwardPath` with a stub forwarder (no daemon, no Slack;
// the branch under test makes exactly two gateway calls and this asserts on both).
//   1  nudge REFUSED  → the message is NOT lost: a session-create is enqueued (the daemon's
//                       `on_seat_busy: queue` makes a busy seat lossless) and the thread is mapped.
//   2  nudge ACCEPTED → no enqueue (the live turn consumed it), but the thread IS mapped and bound
//                       to the holder's exec-id, so the reply leg can ferry the answer back.
//   3  MUTATION       → the fall-through is cut out of a COPY; arm 1 must go RED.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { makeCapture, nowMs } = require('./lib');

const OUT = path.join(__dirname, 'probe-chat-live-holder.out');
const FP = path.join(__dirname, '..', 'forward-path.js');

const checks = [];
function check(name, pass, detail = {}) {
  checks.push({ name, pass: Boolean(pass), ...detail });
  return Boolean(pass);
}

const GOAL = 'probegoal';
const HOLDER_EXEC = 30026;
const CHANNEL = 'C-PROBE-LIVE';

function scratchWorkspace() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'p-liveholder-'));
  const seatDir = path.join(root, '.rbtv', 'goals', GOAL, 'seats', 'goal-master');
  fs.mkdirSync(seatDir, { recursive: true });
  return { root, seatDir, cleanup: () => { try { fs.rmSync(root, { recursive: true, force: true }); } catch {} } };
}

// A forwarder that reports ONE live sitting at the goal-master seat and answers `live-feed` with
// whatever the arm dictates. Every other intent is recorded and accepted.
function stubForwarder({ seatDir, fed }) {
  const calls = [];
  return {
    calls,
    async inspect(what) {
      if (what !== 'ticker') return { ok: false };
      return { ok: true, result: { live_sessions: [{ workdir: seatDir, exec_id: HOLDER_EXEC, status: 'running' }] } };
    },
    async forward(intent, payload) {
      calls.push({ intent, payload });
      if (intent === 'live-feed') {
        return fed
          ? { ok: true, result: { fed: true } }
          : { ok: true, result: { fed: false, reason: 'no-warm-session' } };
      }
      if (intent === 'enqueue-job') return { ok: true, result: { jobId: 4242 } };
      return { ok: true, result: {} };
    },
  };
}

function buildPath({ root, seatDir, fed, modulePath = FP }) {
  const { createForwardPath } = require(modulePath);
  const { createThreadMap } = require(path.join(__dirname, '..', 'thread-map.js'));
  const threadMap = createThreadMap({});
  const forwarder = stubForwarder({ seatDir, fed });
  const logs = [];
  const fp = createForwardPath({
    forwarder,
    threadMap,
    allowlist: { check: () => ({ allowed: true }) },
    config: { workspaceRoot: root, workdir: null, sessionJobId: 'chat-launch', sendMessageJobId: 'send-message' },
    logger: (o) => logs.push(o),
    deliver: async () => ({ delivered: true }),
  });
  return { fp, forwarder, threadMap, logs };
}

async function runArm({ root, seatDir, fed, modulePath }) {
  const { fp, forwarder, threadMap, logs } = buildPath({ root, seatDir, fed, modulePath });
  const res = await fp.onChatMessage({
    chatUserId: 'U-owner', chatThreadId: CHANNEL,
    text: 'what is the status of the summarizer?',
    route: { kind: 'goal', goalId: GOAL },
  });
  const enqueues = forwarder.calls.filter((c) => c.intent === 'enqueue-job');
  return { res, enqueues, threadMap, logs, calls: forwarder.calls };
}

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const cleanups = [];
  try {
    // ── ARM 1 — the nudge is refused: the message must survive ───────────────────────────────
    {
      const w = scratchWorkspace(); cleanups.push(w.cleanup);
      const { res, enqueues, threadMap, calls } = await runArm({ root: w.root, seatDir: w.seatDir, fed: false });
      cap.log({ arm: 1, res, calls: calls.map((c) => c.intent) });
      check('arm1: the live-holder found the sitting and TRIED the nudge (the branch under test really ran)',
        calls.some((c) => c.intent === 'live-feed'), { calls: calls.map((c) => c.intent) });
      check('arm1: a REFUSED nudge does NOT swallow the message — a session-create is enqueued',
        enqueues.length === 1 && enqueues[0].payload.job_id === 'chat-launch',
        { enqueues: enqueues.map((e) => e.payload.job_id) });
      check('arm1: the enqueued job carries the owner\'s text and is homed at the goal-master seat',
        enqueues.length === 1
          && /status of the summarizer/.test(String(enqueues[0].payload.args.prompt || ''))
          && enqueues[0].payload.args.workdir === w.seatDir,
        { args: enqueues.length ? enqueues[0].payload.args : null });
      check('arm1: the enqueue queues at a busy seat rather than being deduped away',
        enqueues.length === 1 && enqueues[0].payload.on_seat_busy === 'queue',
        { onSeatBusy: enqueues.length ? enqueues[0].payload.on_seat_busy : null });
      check('arm1: the thread is MAPPED, so the reply leg can ferry the sitting\'s answer back',
        threadMap.has(CHANNEL), { mapped: threadMap.has(CHANNEL) });
      check('arm1: the result does not claim a live-holder success', res && res.liveHolder !== true, { res });
    }

    // ── ARM 2 — the nudge lands: no enqueue, but a reply path is armed ───────────────────────
    {
      const w = scratchWorkspace(); cleanups.push(w.cleanup);
      const { res, enqueues, threadMap } = await runArm({ root: w.root, seatDir: w.seatDir, fed: true });
      cap.log({ arm: 2, res });
      check('arm2: a FED live sitting consumes the message — nothing is enqueued behind it',
        enqueues.length === 0, { enqueues: enqueues.length });
      check('arm2: the thread is mapped and BOUND to the live holder\'s exec-id (the reply leg\'s address)',
        threadMap.has(CHANNEL) && threadMap.get(CHANNEL) && Number(threadMap.get(CHANNEL).sessionExecId) === HOLDER_EXEC,
        { entry: threadMap.get(CHANNEL) });
      check('arm2: the branch reports the live-holder delivery', res && res.forwarded === true && res.liveHolder === true, { res });
    }

    // ── ARM 3 — MUTATION: cut the fall-through, arm 1 must go RED ────────────────────────────
    {
      const src = fs.readFileSync(FP, 'utf8');
      const target = 'if (nudge.nudged) {';
      if (!src.includes(target)) {
        check('arm3: the mutation target still exists in the source', false, { target });
      } else {
        // Make the nudged arm unconditional — i.e. restore the pre-fix behaviour where a refused
        // nudge still returned `forwarded: true` and enqueued nothing.
        const mutated = src.replace(target, 'if (true) {');
        check('arm3: the mutation ALTERED the source (a no-op mutation proves nothing)', mutated !== src);
        const beside = path.join(__dirname, '..', `forward-path.MUTANT-${process.pid}.js`);
        fs.writeFileSync(beside, mutated);
        cleanups.push(() => { try { fs.unlinkSync(beside); } catch {} });
        const w = scratchWorkspace(); cleanups.push(w.cleanup);
        const { enqueues } = await runArm({ root: w.root, seatDir: w.seatDir, fed: false, modulePath: beside });
        check('arm3: with the fall-through cut, the refused nudge LOSES the message — the probe can fail',
          enqueues.length === 0, { enqueues: enqueues.length });
      }
    }
  } catch (err) {
    check('probe ran to completion without throwing', false, { error: err.message, stack: (err.stack || '').split('\n').slice(0, 6) });
  } finally {
    for (const c of cleanups.reverse()) { try { c(); } catch {} }
  }

  const failed = checks.filter((c) => !c.pass);
  cap.log({ step: 'checks', total: checks.length, failed: failed.length, checks });
  const pass = failed.length === 0 && checks.length > 0;
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-live-holder', pass, EXIT: exit, WALL_MS: wallMs, CHECK_COUNT: checks.length });
  process.stdout.write(`PROBE probe-chat-live-holder EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length} FAILED=${failed.length}\n`);
  process.exit(exit);
}

main();
