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
// `resolveGoalMasterSeat` reads a goal session's workdir from (2026-08-06 ruling).
function seedGoalWorkspace(goalId) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-2-dedupws-'));
  const goalDir = path.join(root, '.rbtv', 'goals', goalId);
  fs.mkdirSync(path.join(goalDir, 'runs', 'run-1', 'seats', 'goal-master'), { recursive: true });
  fs.writeFileSync(path.join(goalDir, 'runs.csv'),
    'run-id,type,state,taskforce-ids,opened,closed\n' +
    'run-1,fresh,open,tf-1,2026-08-03 00:00,\n');
  return { root, seatDir: path.join(goalDir, 'runs', 'run-1', 'seats', 'goal-master') };
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

      const notice = rig.posted[rig.posted.length - 1];
      check('arm1-honest-in-thread-notice-posted-to-THAT-thread',
        Boolean(notice) && notice.chatThreadId === 'D_IM:2.2'
          && notice.text === forwardPathModule.SEAT_BUSY_NOTICE
          && /not delivered/i.test(notice.text) && /again/i.test(notice.text),
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
    // `resolveGoalMasterSeat` homes goal traffic at that goal's OPEN run's goal-master seat, a
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
      check('arm3-notice-is-a-fixed-string-with-no-internals',
        typeof n === 'string' && !/queue|seat_key|exec|job_id|dedup|workdir|\d{2,}/i.test(n),
        { notice: n });
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

main();
