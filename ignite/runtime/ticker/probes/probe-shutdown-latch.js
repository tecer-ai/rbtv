'use strict';

// probe-shutdown-latch — SIGTERM must stop NEW dispatches immediately.
//
// THE DEFECT THIS PINS (measured live on the ignite VPS, 2026-08-12). The daemon has TWO tick
// drivers: the cadence `setInterval` in `runtime/index.js`, and the ticker's own nudge chain, which
// re-arms itself with `setTimeout` at the tail of every nudged tick. The SIGTERM handler cleared
// only the first. Journal, run 21:20:35 UTC — `Stopping rbtv-ignite.service` 21:20:35,
// `received SIGTERM, shutting down` 21:20:43, and then ticks 241980/241981/241982 at
// 21:21:01-21:21:05, each still dispatching. The 21:06 stop did the same and launched two workers
// (21:06:29, 21:06:41) after the signal. Both stops ended in `Failed with result 'timeout'` and a
// SIGKILL 90s later.
//
// ⚠ THE CONTROL ARM IS NOT DECORATION. "No spawn happened" is the state a BROKEN fixture reports
// too — a job that was never due, a store that never registered, a workdir refused at the door all
// produce the identical empty result. So arm 1 proves this exact fixture DOES dispatch before the
// latch is set; only then does arm 2's silence mean anything. Delete `ticker.stop()`'s effect and
// arm 2 goes red; break the fixture and arm 1 goes red first.

const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture, sleep } = require('./lib');

const spawned = (r) => r.actions.filter(a => a.phase === 'dispatch' && a.action === 'spawn').length;

async function run(lines) {
  const ctx = setup();
  try {
    registerLaunchAgentJob(ctx);

    // ── Arm 1 · CONTROL — this fixture dispatches when the ticker is live ────────────────────
    const t0 = new Date();
    enqueueLaunchAgent(ctx, { runAt: t0 });
    const live = await ctx.ticker.tick(t0);
    lines.push(`arm 1 (control, ticker live): spawns=${spawned(live)} tick=${live.tick}`);
    if (spawned(live) !== 1) {
      throw new Error(`CONTROL FAILED — the live ticker dispatched ${spawned(live)} spawns, expected 1. `
        + 'Arm 2 cannot distinguish "the latch worked" from "this fixture never dispatches".');
    }
    const execId = ctx.store.dump().jobs_log[0].exec_id;
    try { await ctx.mgr.kill(execId); } catch {}

    // ── Arm 2 · the latch — a tick after stop() dispatches NOTHING ───────────────────────────
    const t1 = new Date();
    enqueueLaunchAgent(ctx, { runAt: t1 });
    const rowsBefore = ctx.store.dump().jobs_log.length;

    ctx.ticker.stop();

    const halted = await ctx.ticker.tick(t1);
    lines.push(`arm 2 (after stop): skipped=${halted.skipped} spawns=${spawned(halted)} `
      + `actions=${JSON.stringify(halted.actions)}`);
    if (spawned(halted) !== 0) {
      throw new Error(`THE LATCH DID NOT HOLD — a tick after stop() dispatched ${spawned(halted)} spawn(s). `
        + 'This is the live defect: the daemon launches work out of a process systemd is stopping.');
    }
    const rowsAfter = ctx.store.dump().jobs_log.length;
    lines.push(`arm 2: jobs_log rows ${rowsBefore} -> ${rowsAfter}`);
    if (rowsAfter !== rowsBefore) {
      throw new Error(`a stopped ticker still opened ${rowsAfter - rowsBefore} execution row(s)`);
    }

    // ── Arm 3 · the OTHER door — nudge() after stop() arms nothing ───────────────────────────
    // The nudge chain is what actually survived SIGTERM in the incident, so a latch that only
    // guards tick() would leave the self-re-arming timer running and the process unreapable.
    const tickBefore = ctx.ticker.getTickNumber();
    ctx.ticker.nudge('probe-after-stop', 20);
    await sleep(300);                       // well past the 20ms arm and the 250ms debounce floor
    const tickAfter = ctx.ticker.getTickNumber();
    lines.push(`arm 3 (nudge after stop): tick ${tickBefore} -> ${tickAfter}`);
    if (tickAfter !== tickBefore) {
      throw new Error(`nudge() after stop() ran a tick (${tickBefore} -> ${tickAfter}) — the chain `
        + 'that outlived SIGTERM is still armable.');
    }

    lines.push('PASS — stop() halts both tick drivers; the control arm proves the fixture dispatches.');
  } finally {
    teardown(ctx);
  }
}

capture('probe-shutdown-latch', run);
