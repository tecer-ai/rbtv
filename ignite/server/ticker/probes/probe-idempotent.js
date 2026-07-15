'use strict';

const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture } = require('./lib');

async function run(lines) {
  const ctx = setup();
  try {
    registerLaunchAgentJob(ctx);
    const now = new Date();
    enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt: now });

    lines.push('enqueued one due launch-agent job');

    const r1 = await ctx.ticker.tick(now);
    lines.push(`tick ${r1.tick}: ${JSON.stringify(r1.actions)}`);

    const r2 = await ctx.ticker.tick(now);
    lines.push(`tick ${r2.tick}: ${JSON.stringify(r2.actions)}`);

    const dump = ctx.store.dump();
    lines.push(`jobs_log rows: ${dump.jobs_log.length}`);
    if (dump.jobs_log.length !== 1) throw new Error(`expected 1 jobs_log row, got ${dump.jobs_log.length}`);

    const hasLaunch = r1.actions.some(a => a.phase === 'dispatch' && a.action === 'spawn');
    const hasSecondLaunch = r2.actions.some(a => a.phase === 'dispatch' && a.action === 'spawn');
    if (!hasLaunch) throw new Error('first tick did not launch');
    if (hasSecondLaunch) throw new Error('second tick launched again (not idempotent)');

    const exec = dump.jobs_log[0];
    const live = await ctx.mgr.status(exec.exec_id);
    lines.push(`spawn live: ${live.live}`);
    if (!live.live) throw new Error('spawn reports session not live');

    try { await ctx.mgr.kill(exec.exec_id); } catch {}
  } finally {
    teardown(ctx);
  }
}

capture('probe-idempotent', run);
