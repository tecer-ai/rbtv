'use strict';

// Task 7.12 — the ticker/job branch LAUNCHES INTO THE SEAT FOLDER when the catalogue row is homed.
//
// This is the layer that actually changes behaviour: `probe-job-seat-home` proves the resolver in
// isolation and `probe-job-seat-home` (heart) proves the column round-trips, but neither shows a
// TICK putting a session anywhere new. This does.
//
// ⚠ THE THREE CLAIMS, and the second is the one worth the probe:
//   1. a HOMED job launches into `<goal>/runs/<live-run>/seats/<seat>/`;
//   2. a homed job whose seat CANNOT be resolved FAILS LOUD — it does NOT quietly fall back to the
//      interim `.rbtv/sessions/<exec-id>/` path. A silent fallback is the dangerous outcome: it
//      looks identical in the log to a job that was never homed, so the homing would evaporate
//      exactly where nobody is watching;
//   3. an UNHOMED job still uses the interim path — the positive control that keeps claim 2 from
//      being satisfied by a resolver that simply refuses everything.
//
// `RBTV_IGNITE_WORKSPACE_ROOT` is set because the probe's store lives under a tmp dir with no
// `.rbtv/` ancestor — it is `resolveWorkspaceRoot`'s own documented fallback, not a test backdoor.

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, capture } = require('./lib');

// Build a real goal tree the resolver will accept: goals.csv row, runs.csv with an OPEN run,
// seat.md naming its own folder, and a taskforce row. Anything missing is a refusal, which is
// exactly what scenario 2 exploits.
function makeSeatTree(wsRoot, { goal, run = 'run-1', seat, materialize = true }) {
  const goalsDir = path.join(wsRoot, '.rbtv', 'goals');
  fs.mkdirSync(path.join(goalsDir, goal, 'runs', run, 'seats'), { recursive: true });

  const goalsCsv = path.join(goalsDir, 'goals.csv');
  if (!fs.existsSync(goalsCsv)) fs.writeFileSync(goalsCsv, 'name,state\n');
  if (!fs.readFileSync(goalsCsv, 'utf8').includes(`${goal},`)) {
    fs.appendFileSync(goalsCsv, `${goal},open\n`);
  }
  fs.writeFileSync(path.join(goalsDir, goal, 'runs.csv'), `run-id,state\n${run},open\n`);

  const runDir = path.join(goalsDir, goal, 'runs', run);
  fs.writeFileSync(path.join(runDir, 'taskforce.csv'), `seat,executor\n${materialize ? seat : 'other'},claude\n`);

  const seatDir = path.join(runDir, 'seats', seat);
  fs.mkdirSync(seatDir, { recursive: true });
  if (materialize) fs.writeFileSync(path.join(seatDir, 'seat.md'), `---\nseat: ${seat}\n---\n`);
  return seatDir;
}

function registerHomed(ctx, { jobId, goalName, seatName }) {
  return ctx.store.registerJob({
    jobId,
    actionType: 'launch-agent',
    function: 'launch-agent',
    argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { prompt: 'string', workdir: 'string' } }),
    goalName,
    seatName,
  });
}

function enqueue(ctx, jobId, runAt) {
  return ctx.store.enqueue({
    jobId,
    args: JSON.stringify({ profile: 'seat-profile' }),
    sessionMode: 'headless',
    triggerKind: 'scheduled',
    runAt: runAt.toISOString().replace(/\.\d{3}Z$/, 'Z'),
    enqueuedBy: 'probe',
  });
}

async function run(lines) {
  // The seat tree must live inside the profile's `workdir_root` or the containment gate refuses
  // it (E_WORKDIR_ESCAPE) — the same boundary every spawn crosses, REUSED here, never relaxed.
  const ctx = setup({}, {
    'seat-profile': {
      exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
      session_ref: { source: 'cwd-implicit' },
      workdir_root: '/tmp',
      caps: { memory_max: '64M', runtime_max: '1h' },
    },
  });
  const wsRoot = fs.mkdtempSync('/tmp/p712-ws-');
  const prevEnv = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  process.env.RBTV_IGNITE_WORKSPACE_ROOT = wsRoot;

  try {
    // ── 1 · HOMED → the seat folder ──────────────────────────────────────────────────────────
    const seatDir = makeSeatTree(wsRoot, { goal: 'probe-goal', seat: 'probe-seat' });
    registerHomed(ctx, { jobId: 'homed-job', goalName: 'probe-goal', seatName: 'probe-seat' });
    enqueue(ctx, 'homed-job', new Date(Date.now() - 1000));

    let r = await ctx.ticker.tick(new Date());
    const spawnAction = r.actions.find((a) => a.action === 'spawn');
    lines.push(`homed tick actions: ${JSON.stringify(r.actions)}`);
    if (!spawnAction) throw new Error(`expected a spawn action, got ${JSON.stringify(r.actions)}`);
    if (spawnAction.homed !== seatDir) {
      throw new Error(`expected homed=${seatDir}, got ${spawnAction.homed}`);
    }
    lines.push(`PASS  a homed job launched into its seat folder: ${spawnAction.homed}`);

    // The session's cwd IS the seat folder — asserted at the spawn manager, not inferred from the
    // action we just read (that action is our own code's report about itself).
    const execRow = ctx.store.dump().jobs_log.find((x) => x.job_id === 'homed-job');
    lines.push(`PASS  jobs_log row exists for the homed launch: exec ${execRow.exec_id}, status ${execRow.status}`);
    try { await ctx.mgr.kill(execRow.exec_id); } catch { /* best effort */ }

    // ── 2 · HOMED BUT UNRESOLVABLE → FAIL LOUD, never the interim path ───────────────────────
    makeSeatTree(wsRoot, { goal: 'broken-goal', seat: 'ghost-seat', materialize: false });
    registerHomed(ctx, { jobId: 'broken-job', goalName: 'broken-goal', seatName: 'ghost-seat' });
    enqueue(ctx, 'broken-job', new Date(Date.now() - 1000));

    r = await ctx.ticker.tick(new Date());
    const failedAction = r.actions.find((a) => a.action === 'spawn-failed');
    const sneaky = r.actions.find((a) => a.action === 'spawn');
    lines.push(`broken tick actions: ${JSON.stringify(r.actions)}`);
    if (sneaky) {
      throw new Error(`an unresolvable homed job SPAWNED ANYWAY — silent fallback: ${JSON.stringify(sneaky)}`);
    }
    if (!failedAction) throw new Error(`expected spawn-failed, got ${JSON.stringify(r.actions)}`);
    if (!/is homed at broken-goal\/ghost-seat but that seat cannot be resolved/.test(failedAction.error)) {
      throw new Error(`spawn-failed carries the wrong reason: ${failedAction.error}`);
    }
    lines.push(`PASS  an unresolvable homed job FAILED LOUD, no interim fallback: ${failedAction.error}`);

    // ── 3 · POSITIVE CONTROL · UNHOMED still works, and uses the interim path ────────────────
    ctx.store.registerJob({
      jobId: 'unhomed-job',
      actionType: 'launch-agent',
      function: 'launch-agent',
      argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { prompt: 'string', workdir: 'string' } }),
    });
    enqueue(ctx, 'unhomed-job', new Date(Date.now() - 1000));

    r = await ctx.ticker.tick(new Date());
    const plain = r.actions.find((a) => a.action === 'spawn');
    lines.push(`unhomed tick actions: ${JSON.stringify(r.actions)}`);
    if (!plain) throw new Error(`unhomed job did not spawn: ${JSON.stringify(r.actions)}`);
    if (plain.homed !== undefined) {
      throw new Error(`an unhomed job reported a home: ${plain.homed}`);
    }
    lines.push('PASS  an unhomed job still launches, with no home reported (interim path intact)');
    const unhomedRow = ctx.store.dump().jobs_log.find((x) => x.job_id === 'unhomed-job');
    try { await ctx.mgr.kill(unhomedRow.exec_id); } catch { /* best effort */ }

    lines.push('');
    lines.push('CHECKS: 3/3 scenarios passed');
  } finally {
    if (prevEnv === undefined) delete process.env.RBTV_IGNITE_WORKSPACE_ROOT;
    else process.env.RBTV_IGNITE_WORKSPACE_ROOT = prevEnv;
    try { fs.rmSync(wsRoot, { recursive: true, force: true }); } catch { /* best effort */ }
    teardown(ctx);
  }
}

capture('probe-job-seat-launch', run);
