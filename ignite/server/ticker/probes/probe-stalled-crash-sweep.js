'use strict';

// Task 7.15 (batch-08 item 4 half B): a `stalled` execution STAYS in the
// crash-sweep set. Regression target: pre-fix, liveExecutions() returned
// running+launching only, so a worker marked `stalled` left the swept set and
// its later exit was recorded by NOTHING — the row sat `stalled` forever.
// This probe stalls a silent worker, kills its unit, and asserts the sweep
// still writes the synthetic completion + exit, while `stalled` keeps its
// dispatch semantics (owner-halted — never re-dispatched).

const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture, sleep } = require('./lib');

async function run(lines) {
  const ctx = setup();
  try {
    registerLaunchAgentJob(ctx);
    const now = new Date();
    enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt: now });
    lines.push('enqueued one due launch-agent job (silent worker)');

    let r = await ctx.ticker.tick(now);
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions.filter(a => a.phase === 'dispatch'))}`);
    const exec = ctx.store.dump().jobs_log[0];
    lines.push(`exec id=${exec.exec_id}, status=${exec.status}`);

    // Ride the silence ladder until the row is marked stalled.
    let stalled = false;
    for (let i = 0; i < 30; i++) {
      r = await ctx.ticker.tick(new Date());
      if (r.actions.some(a => a.phase === 'enforce' && a.action === 'stalled')) {
        stalled = true;
        lines.push(`stalled at tick ${r.tick}`);
        break;
      }
    }
    if (!stalled) throw new Error('expected the worker to be marked stalled');
    let row = ctx.store.getExecution(exec.exec_id);
    if (row.status !== 'stalled') throw new Error(`expected stalled, got ${row.status}`);

    // While stalled and alive: never re-dispatched (owner-halted), never swept.
    r = await ctx.ticker.tick(new Date());
    if (ctx.store.dump().queue.length !== 0) throw new Error('stalled slot must not be re-dispatched');
    if (r.actions.some(a => a.phase === 'enforce' && a.action === 'crash-sweep')) {
      throw new Error('a stalled-but-ALIVE worker must not be crash-swept');
    }
    lines.push('stalled + alive: not re-dispatched, not swept');

    // Kill the unit — the stalled worker exits. Pre-fix, nothing records this.
    const liveInfo = await ctx.mgr.status(exec.exec_id);
    lines.push(`unit name: ${liveInfo.unitName}`);
    const { execFileSync } = require('node:child_process');
    try {
      execFileSync('systemctl', ['--user', 'kill', '--signal=SIGKILL', liveInfo.unitName], { stdio: 'ignore', timeout: 10000 });
    } catch (err) {
      lines.push(`kill warning: ${err.message}`);
    }
    await sleep(500);

    // The crash sweep must sweep the stalled row exactly as it sweeps running.
    r = await ctx.ticker.tick(new Date());
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions.filter(a => a.phase === 'enforce'))}`);
    const swept = r.actions.find(a => a.phase === 'enforce' && a.action === 'crash-sweep' && a.execId === exec.exec_id);
    if (!swept) throw new Error('expected crash-sweep of the stalled execution after its exit');

    row = ctx.store.getExecution(exec.exec_id);
    lines.push(`post-sweep status: ${row.status}, ended_at: ${row.ended_at}`);
    if (row.status !== 'failed') throw new Error(`expected failed, got ${row.status}`);
    if (!row.ended_at) throw new Error('expected ended_at recorded');

    const dump = ctx.store.dump();
    const completions = dump.messages.filter(m => m.type === 'completion' && m.thread === row.thread);
    if (completions.length !== 1) throw new Error(`expected one synthetic completion, got ${completions.length}`);
    if (completions[0].status !== 'failed') throw new Error('expected failed completion');
    if (!completions[0].corpus.startsWith('crash sweep: exit=')) throw new Error(`expected crash-sweep corpus, got: ${completions[0].corpus.slice(0, 60)}`);
    lines.push(`synthetic completion recorded: ${completions[0].corpus.split('\n')[0]}`);

    // Advance resolves the completion; the outcome stays failed (owner-halted,
    // no automatic retry) — identical to a swept `running` row.
    r = await ctx.ticker.tick(new Date());
    const resolved = ctx.store.getMessage(completions[0].msg_id);
    if (resolved.routed_at_tick === null) throw new Error('expected the synthetic completion routed by Advance');
    if (ctx.store.dump().queue.length !== 0) throw new Error('expected no retry queue row');
    if (ctx.store.getExecution(exec.exec_id).status !== 'failed') throw new Error('expected final status failed');
    lines.push('completion resolved by Advance; no retry; final status failed');
  } finally {
    teardown(ctx);
  }
}

capture('probe-stalled-crash-sweep', run);
