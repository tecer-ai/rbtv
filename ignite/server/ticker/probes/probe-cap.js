'use strict';

const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture } = require('./lib');

async function run(lines) {
  const ctx = setup({ max_live_agent_sessions: 2 });
  try {
    registerLaunchAgentJob(ctx);
    const now = new Date();
    for (let i = 0; i < 3; i++) {
      enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt: now });
    }

    lines.push('enqueued 3 due launch-agent jobs with cap=2');

    let r = await ctx.ticker.tick(now);
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);

    let dump = ctx.store.dump();
    lines.push(`jobs_log rows after first tick: ${dump.jobs_log.length}`);
    if (dump.jobs_log.length !== 2) throw new Error(`expected 2 launches, got ${dump.jobs_log.length}`);

    const deferrals = r.actions.filter(a => a.phase === 'dispatch' && a.action === 'defer');
    lines.push(`deferrals: ${JSON.stringify(deferrals)}`);
    if (deferrals.length !== 1) throw new Error('expected exactly 1 deferral');

    // Wait for one session to end capacity by killing it.
    const exec1 = dump.jobs_log[0];
    try { await ctx.mgr.kill(exec1.exec_id); } catch {}

    // Need a tick for crash-sweep and advance to resolve; then the deferred job can launch.
    r = await ctx.ticker.tick(new Date());
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);

    r = await ctx.ticker.tick(new Date());
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);

    dump = ctx.store.dump();
    lines.push(`jobs_log rows after follow-up ticks: ${dump.jobs_log.length}`);
    if (dump.jobs_log.length !== 3) throw new Error(`expected 3 total launches, got ${dump.jobs_log.length}`);

    // Clean up.
    for (const exec of dump.jobs_log) {
      try { await ctx.mgr.kill(exec.exec_id); } catch {}
    }
  } finally {
    teardown(ctx);
  }
}

capture('probe-cap', run);
