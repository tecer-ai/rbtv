'use strict';

const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture, sleep } = require('./lib');

async function run(lines) {
  const ctx = setup();
  try {
    registerLaunchAgentJob(ctx);
    const t0 = new Date();
    const runAt = new Date(t0.getTime() + 2000);
    enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt });

    lines.push(`enqueued at ${t0.toISOString()}, run_at ${runAt.toISOString()}`);

    let r = await ctx.ticker.tick(t0);
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);

    const logBefore = ctx.store.dump().jobs_log;
    if (logBefore.length !== 0) throw new Error(`expected no launch before due, got ${logBefore.length} rows`);

    await sleep(2100);
    const t1 = new Date();
    r = await ctx.ticker.tick(t1);
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);

    const dump = ctx.store.dump();
    lines.push(`jobs_log rows: ${dump.jobs_log.length}`);
    if (dump.jobs_log.length !== 1) throw new Error(`expected 1 jobs_log row, got ${dump.jobs_log.length}`);
    const exec = dump.jobs_log[0];
    lines.push(`exec status: ${exec.status}, profile: ${exec.profile}`);
    if (exec.status !== 'running' && exec.status !== 'launching') {
      throw new Error(`expected running/launching, got ${exec.status}`);
    }

    const live = await ctx.mgr.status(exec.exec_id);
    lines.push(`spawn live: ${live.live}`);
    if (!live.live) throw new Error('spawn reports session not live');

    // Clean up the spawned unit.
    try { await ctx.mgr.kill(exec.exec_id); } catch {}
  } finally {
    teardown(ctx);
  }
}

capture('probe-scheduled', run);
