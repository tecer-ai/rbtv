'use strict';

const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture, sleep } = require('./lib');

async function run(lines) {
  const ctx = setup();
  try {
    registerLaunchAgentJob(ctx);
    const t0 = new Date();
    const runAt = new Date(t0.getTime() + 2000);
    enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt, triggerKind: 'periodic', intervalSeconds: 2 });

    lines.push(`enqueued at ${t0.toISOString()}, first run_at ${runAt.toISOString()}, interval 2s`);

    // t=0: not due.
    let r = await ctx.ticker.tick(t0);
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);
    if (ctx.store.dump().jobs_log.length !== 0) throw new Error('unexpected fire before first interval');

    // t=2s: first fire.
    await sleep(2100);
    const t1 = new Date();
    r = await ctx.ticker.tick(t1);
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);
    if (ctx.store.dump().jobs_log.length !== 1) throw new Error('expected first fire at enqueue+interval');

    // t=4s: second fire.
    await sleep(2100);
    const t2 = new Date();
    r = await ctx.ticker.tick(t2);
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);

    const dump = ctx.store.dump();
    lines.push(`jobs_log rows: ${dump.jobs_log.length}`);
    if (dump.jobs_log.length !== 2) throw new Error(`expected 2 jobs_log rows, got ${dump.jobs_log.length}`);

    const queue = dump.queue;
    if (queue.length !== 1) throw new Error('periodic queue row should still exist');

    // Clean up spawned units.
    for (const exec of dump.jobs_log) {
      try { await ctx.mgr.kill(exec.exec_id); } catch {}
    }
  } finally {
    teardown(ctx);
  }
}

capture('probe-periodic', run);
