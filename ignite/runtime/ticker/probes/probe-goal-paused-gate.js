'use strict';

// probe-goal-paused-gate — the dispatch PAUSE GATE: a due queue row bound to a PAUSED goal is
// deferred, never fired, whatever its action type and WHEREVER its goal binding lives.
//
// THE HOLE THIS PINS (measured 2026-08-14, `system-health`): `rbtv-goal pause` promises "nothing
// new starts for this goal", but the promise held only on the seeding path — `lane-watch.js`
// reads a paused marker as not-`daemon`. A goal's `fire-tool` watcher row carries NO `goal_name`
// (its goal binding is a `--package .../goals/<goal>` string inside `config.tools[...].argv`),
// so the dispatch path fired it straight through a paused landing. Goals with no `execution-lane`
// file at all were unpausable in effect: pausing them changed nothing the dispatch path read.
//
// FOUR ARMS, and the controls carry the weight:
//   C1  ABSENCE IS NOT PAUSED (control) — a goal with NO `execution-lane` file fires its
//       fire-tool row. A gate that parks lane-less goals would pass C2 while breaking every
//       pre-lane goal on the tree; this arm is what makes C2's green meaningful.
//   C2  THE HOLE — the SAME tool row, goal now `paused …`: deferred `goal-paused`, no fire,
//       the queue row SURVIVES. Red against the pre-gate dispatch by construction.
//   C3  THE goal_name ARM — a `launch-agent` row homed at the paused goal (catalogue
//       `goal_name`) defers the same way: one gate, both binding shapes.
//   C4  THE DRAIN — the marker unpauses and BOTH deferred rows fire by themselves on the next
//       tick. A defer that consumed or wedged the row would pass C2 and fail here.

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, capture } = require('./lib');

function goalPausedActions(result) {
  return result.actions.filter((a) => a.phase === 'dispatch' && a.reason === 'goal-paused');
}

async function run(lines) {
  const ctx = setup();
  const prevRoot = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  try {
    // The gate resolves the workspace root from the store's db path, which in this fixture has
    // no `.rbtv/` shape — the env fallback points it at the fixture workspace instead.
    process.env.RBTV_IGNITE_WORKSPACE_ROOT = ctx.workRoot;
    const goalDir = ctx.runDir; // <workRoot>/.rbtv/goals/probe-goal
    const laneFile = path.join(goalDir, 'execution-lane');

    // The system-health shape: a fire-tool whose ONLY goal binding is an argv path.
    ctx.store.config.tools = { 'probe-watcher': { argv: ['/bin/true', '--package', goalDir] } };
    ctx.store.registerJob({
      jobId: 'probe-watcher-job',
      actionType: 'fire-tool',
      function: 'fire-tool',
      argsSchema: JSON.stringify({ required: { tool: 'string' } }),
    });
    // The goal_name shape: a launch-agent row homed at the goal through its catalogue row.
    ctx.store.registerJob({
      jobId: 'probe-goal-agent',
      actionType: 'launch-agent',
      function: 'launch-agent',
      argsSchema: JSON.stringify({ required: {}, optional: { prompt: 'string', workdir: 'string' } }),
      goalName: 'probe-goal',
      seatName: 'probe-seat', // the job->seat pointer is both or neither (E_BAD_ARGS otherwise)
    });
    const due = () => new Date(Date.now() - 1000).toISOString().replace(/\.\d{3}Z$/, 'Z');
    const enqueueTool = () => ctx.store.enqueue({
      jobId: 'probe-watcher-job',
      args: JSON.stringify({ tool: 'probe-watcher' }),
      sessionMode: 'headless',
      triggerKind: 'scheduled',
      runAt: due(),
      enqueuedBy: 'probe',
    });

    // ── C1: no execution-lane file at all — the row FIRES (absence is not paused) ──
    if (fs.existsSync(laneFile)) throw new Error('fixture goal unexpectedly carries a lane file');
    enqueueTool();
    let r = await ctx.ticker.tick(new Date());
    lines.push(`C1 tick ${r.tick}: ${JSON.stringify(r.actions.filter((a) => a.phase === 'dispatch'))}`);
    if (goalPausedActions(r).length !== 0) throw new Error('C1: lane-less goal was gated as paused');
    if (ctx.store.dump().jobs_log.length !== 1) throw new Error('C1: fire-tool row did not fire on a lane-less goal');

    // ── C2 + C3: paused — both binding shapes defer, nothing fires, the rows survive ──
    fs.writeFileSync(laneFile, 'paused daemon\n');
    enqueueTool();
    // Enqueued WITHOUT a workdir: the job is homed (goal_name/seat_name), and a homed row that
    // also names a workdir is its own refusal at dispatch.
    ctx.store.enqueue({
      jobId: 'probe-goal-agent',
      args: JSON.stringify({}),
      sessionMode: 'headless',
      triggerKind: 'scheduled',
      runAt: due(),
      enqueuedBy: 'probe',
    });
    r = await ctx.ticker.tick(new Date());
    const gated = goalPausedActions(r);
    lines.push(`C2/C3 tick ${r.tick}: ${JSON.stringify(gated)}`);
    if (gated.length !== 2) throw new Error(`C2/C3: expected 2 goal-paused defers, got ${gated.length}`);
    if (!gated.every((a) => a.goal === 'probe-goal')) throw new Error('C2/C3: defer does not name the paused goal');
    if (ctx.store.dump().jobs_log.length !== 1) throw new Error('C2/C3: a row FIRED for a paused goal — the pause gate is open');
    if (ctx.store.dump().queue.length !== 2) throw new Error('C2/C3: a deferred row was consumed');

    // ── C4: the drain — unpause, both rows fire by themselves on the next tick ──
    fs.writeFileSync(laneFile, 'daemon\n');
    r = await ctx.ticker.tick(new Date());
    lines.push(`C4 tick ${r.tick}: ${JSON.stringify(r.actions.filter((a) => a.phase === 'dispatch'))}`);
    if (goalPausedActions(r).length !== 0) throw new Error('C4: unpaused goal still gated');
    if (ctx.store.dump().jobs_log.length !== 3) throw new Error('C4: the deferred rows did not fire after resume');

    for (const exec of ctx.store.dump().jobs_log) {
      try { await ctx.mgr.kill(exec.exec_id); } catch {}
    }
  } finally {
    if (prevRoot === undefined) delete process.env.RBTV_IGNITE_WORKSPACE_ROOT;
    else process.env.RBTV_IGNITE_WORKSPACE_ROOT = prevRoot;
    teardown(ctx);
  }
}

capture('probe-goal-paused-gate', run);
