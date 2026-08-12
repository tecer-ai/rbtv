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
//   3. an UNHOMED job does NOT spawn — firing it is a refusal. Rewritten per
//      `r-seats-only-architecture` (2026-08-06): the flat `.rbtv/sessions/` launch path is
//      retired; every daemon spawn homes as a seat. The former positive control (unhomed →
//      interim path) protected the retired mechanism.
//
// `RBTV_IGNITE_WORKSPACE_ROOT` is set because the probe's store lives under a tmp dir with no
// `.rbtv/` ancestor — it is `resolveWorkspaceRoot`'s own documented fallback, not a test backdoor.

require('../../../deploy/probe-self-isolate').selfIsolateTmux(); // solo-run tmux isolation (task 7.630) — no-op under the runner
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const { setup, teardown, capture } = require('./lib');

// Build a real goal tree the resolver will accept: a goals.csv row, a REAL tmux room (the goal is
// EXECUTING — 7.607 E2a: `resolveSeatHome` asks the derived lease, not a register), seat.md naming
// its own folder, and a taskforce row. Anything missing is a refusal, which is exactly what
// scenario 2 exploits. GOAL-DIRECT: everything sits under `<goal>/`, with no run compartment.
function makeSeatTree(wsRoot, { goal, seat, materialize = true, executing = true }) {
  const goalsDir = path.join(wsRoot, '.rbtv', 'goals');
  fs.mkdirSync(path.join(goalsDir, goal, 'seats'), { recursive: true });

  const goalsCsv = path.join(goalsDir, 'goals.csv');
  if (!fs.existsSync(goalsCsv)) fs.writeFileSync(goalsCsv, 'name,state\n');
  if (!fs.readFileSync(goalsCsv, 'utf8').includes(`${goal},`)) {
    fs.appendFileSync(goalsCsv, `${goal},open\n`);
  }
  if (executing) {
    execFileSync('tmux', ['new-session', '-d', '-s', goal, 'sleep', '600'], { stdio: ['ignore', 'pipe', 'pipe'] });
  }

  const runDir = path.join(goalsDir, goal);
  fs.writeFileSync(path.join(runDir, 'taskforce.csv'), `seat,executor\n${materialize ? seat : 'other'},claude\n`);

  const seatDir = path.join(runDir, 'seats', seat);
  fs.mkdirSync(seatDir, { recursive: true });
  if (materialize) fs.writeFileSync(path.join(seatDir, 'seat.md'), `---\nseat: ${seat}\nharness: bash\nmodel: seat-profile\n---\n`);
  return seatDir;
}

function registerHomed(ctx, { jobId, goalName, seatName }) {
  return ctx.store.registerJob({
    jobId,
    actionType: 'launch-agent',
    function: 'launch-agent',
    argsSchema: JSON.stringify({ required: {}, optional: { prompt: 'string', workdir: 'string' } }),
    goalName,
    seatName,
  });
}

function enqueue(ctx, jobId, runAt) {
  return ctx.store.enqueue({
    jobId,
    args: JSON.stringify({}),
    sessionMode: 'headless',
    triggerKind: 'scheduled',
    runAt: runAt.toISOString().replace(/\.\d{3}Z$/, 'Z'),
    enqueuedBy: 'probe',
  });
}

// The tally is COUNTED, never typed: a hand-written "3/3" stops being true the moment a scenario is
// added and would read as green while covering less (the idiom probe-one-live-run and
// probe-queued-start-notify already use in this folder).
let scenarios = 0;

async function run(lines) {
  // The seat tree must live inside the profile's `workdir_root` or the containment gate refuses
  // it (E_WORKDIR_ESCAPE) — the same boundary every spawn crosses, REUSED here, never relaxed.
  const ctx = setup({}, {
    // 7.787: `setup`'s extras land in the fixture's `launch-specs.bash` block, so the argv must
    // pin the model its key names (`profiles.js#validateSpecKey`). The `bash -c` shim really runs
    // `sleep 3600`, unchanged.
    'seat-profile': {
      exec: { argv: ['bash', '-c', 'exec sleep 3600', '--model', 'seat-profile'], prompt: 'stdin' },
      session_ref: { source: 'cwd-implicit' },
      workdir_root: '/tmp',
      caps: { memory_max: '64M', runtime_max: '1h' },
    },
  });
  const wsRoot = fs.mkdtempSync('/tmp/p712-ws-');
  const prevEnv = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  process.env.RBTV_IGNITE_WORKSPACE_ROOT = wsRoot;

  // 7.607 E2a — the goal's lease is a REAL tmux room, on an ISOLATED socket. Never the box's
  // default server: it carries the owner's attached session and may be neither read as evidence
  // nor extended. Reaped in the `finally` below.
  const roomTmpdir = path.join(os.tmpdir(), `e2a-jsl-${process.pid}`);
  fs.mkdirSync(roomTmpdir, { recursive: true, mode: 0o700 });
  const prevTmux = process.env.TMUX_TMPDIR;
  const savedTmux = process.env.TMUX;
  const savedTmuxPane = process.env.TMUX_PANE;
  process.env.TMUX_TMPDIR = roomTmpdir;
  // $TMUX overrides TMUX_TMPDIR: run from inside a pane, every tmux call here — including the
  // finally's kill-server — would hit the DEFAULT server. Cleared so the redirect actually binds.
  delete process.env.TMUX;
  delete process.env.TMUX_PANE;

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

    // The session's cwd IS the seat folder — ASSERTED against the workdir the SPAWN MANAGER
    // resolved and persisted (`resolveWorkdir` → `jobs_log.workdir`), never against
    // `spawnAction.homed`, which is the ticker echoing back the argument it just passed in: the
    // claim above is our own code agreeing with itself. Realpath the expected side because
    // canonicalizeWorkdir realpaths the requested one — a raw compare would go red on symlink
    // resolution rather than on the homing. Recording this value without comparing it is what let
    // the mode-gate regression stay green (31149a02).
    const execRow = ctx.store.dump().jobs_log.find((x) => x.job_id === 'homed-job');
    if (!execRow) throw new Error('no jobs_log row for the homed launch');
    const seatReal = fs.realpathSync(seatDir);
    if (execRow.workdir !== seatReal) {
      throw new Error(`the spawn manager resolved workdir=${execRow.workdir}, expected the seat folder ${seatReal}`);
    }
    lines.push(`PASS  the spawn manager resolved the seat folder as the session workdir: ${execRow.workdir} (exec ${execRow.exec_id}, status ${execRow.status})`);
    scenarios += 1;
    try { await ctx.mgr.kill(execRow.exec_id); } catch { /* best effort */ }

    // ── 2 · HOMED BUT UNRESOLVABLE → FAIL LOUD, never the interim path ───────────────────────
    // A merely-ABSENT seat.md is no longer unresolvable: r-seats-only-architecture auto-
    // materializes a job-born seat's minimal shape at spawn (resolveSeatHome's materialize
    // branch). What stays a refusal is a descriptor that DISAGREES with its folder — so that is
    // the unresolvable case this scenario stages.
    const ghostDir = makeSeatTree(wsRoot, { goal: 'broken-goal', seat: 'ghost-seat', materialize: false });
    fs.writeFileSync(path.join(ghostDir, 'seat.md'), '---\nseat: somebody-else\nharness: bash\nmodel: seat-profile\n---\n');
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
    scenarios += 1;

    // ── 3 · UNHOMED → REFUSAL, never a flat-path spawn (r-seats-only-architecture) ───────────
    ctx.store.registerJob({
      jobId: 'unhomed-job',
      actionType: 'launch-agent',
      function: 'launch-agent',
      argsSchema: JSON.stringify({ required: {}, optional: { prompt: 'string', workdir: 'string' } }),
    });
    enqueue(ctx, 'unhomed-job', new Date(Date.now() - 1000));

    r = await ctx.ticker.tick(new Date());
    lines.push(`unhomed tick actions: ${JSON.stringify(r.actions)}`);
    const flatSpawn = r.actions.find((a) => a.action === 'spawn');
    if (flatSpawn) {
      const row = ctx.store.dump().jobs_log.find((x) => x.job_id === 'unhomed-job');
      try { if (row) await ctx.mgr.kill(row.exec_id); } catch { /* best effort */ }
      throw new Error(`an unhomed launch SPAWNED — the retired flat path is live: ${JSON.stringify(flatSpawn)}`);
    }
    // An ABSENCE alone is not the claim. "Refused for the right reason" and "never reached
    // dispatch" both leave no spawn action, so the same three assertions scenario 2 makes are made
    // here: the refusal is RECORDED (`spawn-failed`), it names the RIGHT cause, and it lands
    // against a REAL `jobs_log` row — the operator record ticker.js § resolveJobHome promises. A
    // quiet `return null` in that branch would consume the queue row and satisfy an absence check.
    //
    // ⚠ MATCHED ON `MISSING FIELDS: goal_name/seat_name`, not on the shared `REFUSING SEATLESS
    // DISPATCH` prefix. THIS IS THE TICK-LEVEL PROBE, so the refusal under test is the TICKER's —
    // and the spawn door's own seatless refusal (spawn.js § spawn, `MISSING FIELD: workdir`)
    // opens with the same prefix. Measured: replacing the throw at ticker.js § resolveJobHome
    // with `return null` left a prefix match GREEN, because the door downstream refused instead.
    // The plural-fields wording is what only the ticker's branch says.
    const refusal = r.actions.find((a) => a.action === 'spawn-failed');
    if (!refusal) throw new Error(`expected spawn-failed for the unhomed job, got ${JSON.stringify(r.actions)}`);
    if (!/MISSING FIELDS: goal_name\/seat_name/.test(refusal.error)) {
      throw new Error(`spawn-failed did not come from the ticker's own seatless branch: ${refusal.error}`);
    }
    const unhomedRow = ctx.store.dump().jobs_log.find((x) => x.job_id === 'unhomed-job');
    if (!unhomedRow || unhomedRow.exec_id !== refusal.execId) {
      throw new Error(`the refusal names exec ${refusal.execId} but jobs_log carries ${JSON.stringify(unhomedRow)}`);
    }
    lines.push(`PASS  an unhomed launch was REFUSED and recorded against exec ${unhomedRow.exec_id} (status ${unhomedRow.status}): ${refusal.error}`);
    scenarios += 1;

    lines.push('');
    lines.push(`CHECKS: ${scenarios}/${scenarios} scenarios passed`);
  } finally {
    try { execFileSync('tmux', ['kill-server'], { stdio: 'ignore' }); } catch { /* already gone */ }
    if (prevTmux === undefined) delete process.env.TMUX_TMPDIR; else process.env.TMUX_TMPDIR = prevTmux;
    if (savedTmux === undefined) delete process.env.TMUX; else process.env.TMUX = savedTmux;
    if (savedTmuxPane === undefined) delete process.env.TMUX_PANE; else process.env.TMUX_PANE = savedTmuxPane;
    try { fs.rmSync(roomTmpdir, { recursive: true, force: true }); } catch { /* best effort */ }
    if (prevEnv === undefined) delete process.env.RBTV_IGNITE_WORKSPACE_ROOT;
    else process.env.RBTV_IGNITE_WORKSPACE_ROOT = prevEnv;
    try { fs.rmSync(wsRoot, { recursive: true, force: true }); } catch { /* best effort */ }
    teardown(ctx);
  }
}

capture('probe-job-seat-launch', run);
