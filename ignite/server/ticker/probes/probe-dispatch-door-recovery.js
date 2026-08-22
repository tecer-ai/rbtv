'use strict';

// Task 7.75 — THE LEADER'S G-52 RIDER (#465): THE MIRROR TRAP, CHECKED.
//
// "The refusal lands on the dispatch path every RECOVERY runs through, and this run already
// shipped a gate that disarmed the repair exactly in the state needing it; the build MUST also
// demonstrate that a normal dispatch INCLUDING A DAEMON-FIRED RECOVERY still succeeds with the
// refusal in place — both halves, or the task is not closed."
//
// The answer this probe measures is structural, and the point is that it is measured rather than
// argued: RECOVERY DOES NOT RUN THROUGH THE DOOR. Recovery is a `fire-tool` exec
// (`restart-daemon` — the sole survivor in today's catalogue; `selfheal-room`/`selfheal-watch`
// were retired 2026-08-20 and `jobs/recover-room.py` is shelled directly by `engine/reconcile.js`,
// never through the ticker's fire-tool path), and ticker.js's `runToolLikeExec` goes straight to
// the carrier: it never calls `spawnManager.spawn`, so it never reaches the 7.75 door. A code-read
// says that; this DRIVES it.
//
// THE PAIR IS THE PROOF, and both halves run in ONE tick against ONE workdir:
//
//   M1  fire-tool   , workdir = a goal-scoped SEATLESS dir  -> DISPATCHES (recovery is not blocked)
//   M2  launch-agent, workdir = THE SAME dir                -> REFUSED at the door
//
// Same tick, same path on disk, opposite verdicts. If M1 ever goes red, the mirror trap is REAL
// and 7.75's own outcome map (F-R4b) says: do NOT land, report to the leader with the trace.
// If M2 goes green (not refused), the door is not armed and M1's green means nothing.

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, capture } = require('./lib');

// The dir every arm points at: inside a goal tree, one segment short of a seat folder. It is the
// shape the door refuses — which is exactly why firing the RECOVERY lane at it is the honest test.
function makeGoalTree(wsRoot, goal, run) {
  const runDir = path.join(wsRoot, '.rbtv', 'goals', goal, 'runs', run);
  fs.mkdirSync(path.join(runDir, 'seats'), { recursive: true });
  fs.writeFileSync(path.join(wsRoot, '.rbtv', 'goals', 'goals.csv'), `name,state\n${goal},open\n`);
  fs.writeFileSync(path.join(wsRoot, '.rbtv', 'goals', goal, 'runs.csv'), `run-id,state\n${run},open\n`);
  return runDir;
}

async function run(lines) {
  const ctx = setup({}, {
    // 7.787: `setup`'s extras land in the fixture's `launch-specs.bash` block, so the argv must
    // pin the model its key names (`profiles.js#validateSpecKey`). The `bash -c` shim really runs
    // `sleep 3600`, unchanged.
    'agent-profile': {
      exec: { argv: ['bash', '-c', 'exec sleep 3600', '--model', 'agent-profile'], prompt: 'stdin' },
      session_ref: { source: 'cwd-implicit' },
      workdir_root: '/tmp',
      caps: { memory_max: '64M', runtime_max: '1h' },
    },
  });
  const wsRoot = fs.mkdtempSync('/tmp/p775-recov-ws-');
  const prevEnv = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  process.env.RBTV_IGNITE_WORKSPACE_ROOT = wsRoot;
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  try {
    const runDir = makeGoalTree(wsRoot, 'recov-goal', 'run-1');

    // A recovery-SHAPED tool: a real subprocess, launched by the carrier, with its target in argv
    // exactly as the live `selfheal-room` / `recover-room.py` entries carry theirs. What matters
    // for this probe is the LANE, not the payload.
    //
    // ⚠ THE PAYLOAD MUST OUTLIVE THE TICK (G-console-master-0807-2331). Dispatch and enforce are
    // phases of the SAME tick, so an instant tool (`bash -c 'echo recovered'`) has already exited
    // by the time the crash sweep looks — and M3's verdict then hangs on whether the carrier's
    // exit marker has landed yet: marker present -> `done`, marker not yet written -> `failed`.
    // Measured 1/5 solo and 3/10 under a concurrent `--dir server` suite, same code, same
    // selection — a `crash-sweep` on an exit-0 tool. A long-lived child fixes the ORDERING
    // M3 asserts (the process is still live when the sweep runs, so the row is `running`), which
    // is the only thing this leg is about; teardown() reaps the unit on PASS or FAIL. The
    // marker-vs-sweep window itself is a PRODUCTION race, filed separately — never probe-side.
    ctx.store.config.tools = {
      'recover-room-probe': { argv: ['sleep', '3600'] },
    };

    // The required-argument set is the ACTION TYPE'S, and the store enforces it at registration
    // (`fire-tool` needs `tool`, `launch-agent` needs `profile`) — so each job declares its own.
    const registerJob = (jobId, actionType, required) => ctx.store.registerJob({
      jobId,
      actionType,
      function: actionType,
      argsSchema: JSON.stringify({ required, optional: { workdir: 'string' } }),
    });
    const enqueue = (jobId, args) => ctx.store.enqueue({
      jobId,
      args: JSON.stringify(args),
      sessionMode: 'headless',
      triggerKind: 'scheduled',
      runAt: new Date(Date.now() - 1000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
      enqueuedBy: 'probe',
    });

    registerJob('recovery-job', 'fire-tool', { tool: 'string' });
    registerJob('agent-job', 'launch-agent', {});
    enqueue('recovery-job', { tool: 'recover-room-probe', workdir: runDir });
    enqueue('agent-job', { workdir: runDir });

    const r = await ctx.ticker.tick(new Date());
    lines.push(`tick actions: ${JSON.stringify(r.actions)}`);

    const recovery = r.actions.find((a) => a.action === 'fire-tool');
    const recoveryFailed = r.actions.find((a) => a.action === 'fire-tool-failed');
    leg('M1', 'a DAEMON-FIRED RECOVERY into a goal-scoped seatless workdir DISPATCHES with the door armed',
      Boolean(recovery) && !recoveryFailed,
      `fire-tool action=${recovery ? `exec ${recovery.execId}` : 'ABSENT'} `
      + `fire-tool-failed=${recoveryFailed ? recoveryFailed.error : 'none'}`);

    const refused = r.actions.find((a) => a.action === 'spawn-failed');
    const leaked = r.actions.find((a) => a.action === 'spawn');
    const rightCode = Boolean(refused) && /MISSING FIELD: seat/.test(refused.error || '');
    leg('M2', 'the SAME workdir on the AGENT lane IS refused — the door is armed, so M1 is not vacuous',
      Boolean(refused) && rightCode && !leaked,
      `spawn-failed=${Boolean(refused)} names-missing-field=${rightCode} spawn-leaked=${Boolean(leaked)} `
      + `— ${(refused && refused.error || '').slice(0, 120)}`);

    // The store's own record, not our code's report about itself (the fire-tool exec really exists
    // and really reached `running`; the agent exec really did not).
    const rows = ctx.store.dump().jobs_log;
    const recRow = rows.find((x) => x.job_id === 'recovery-job');
    const agentRow = rows.find((x) => x.job_id === 'agent-job');
    leg('M3', 'the STORE agrees: the recovery exec reached a live status, the refused agent exec never did',
      Boolean(recRow) && ['running', 'done'].includes(recRow.status)
      && Boolean(agentRow) && agentRow.status !== 'running' && agentRow.status !== 'done',
      `recovery exec ${recRow && recRow.exec_id} status=${recRow && recRow.status} · `
      + `agent exec ${agentRow && agentRow.exec_id} status=${agentRow && agentRow.status}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`mirror-trap probes failed: ${fails.join(', ')}`);
  } finally {
    if (prevEnv === undefined) delete process.env.RBTV_IGNITE_WORKSPACE_ROOT;
    else process.env.RBTV_IGNITE_WORKSPACE_ROOT = prevEnv;
    try { fs.rmSync(wsRoot, { recursive: true, force: true }); } catch { /* best effort */ }
    teardown(ctx);
  }
}

capture('probe-dispatch-door-recovery', run);
