'use strict';

const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture, sleep } = require('./lib');

async function run(lines) {
  const ctx = setup();
  try {
    registerLaunchAgentJob(ctx);
    const now = new Date();
    enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt: now });

    lines.push('enqueued one due launch-agent job');

    let r = await ctx.ticker.tick(now);
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);

    let dump = ctx.store.dump();
    if (dump.jobs_log.length !== 1) throw new Error(`expected 1 jobs_log row, got ${dump.jobs_log.length}`);
    const exec1 = dump.jobs_log[0];
    lines.push(`exec1 id=${exec1.exec_id}, thread=${exec1.thread}, status=${exec1.status}`);
    if (!exec1.thread) throw new Error('exec1 has no thread');

    // Simulate a reply arriving while the session is live.
    ctx.store.recordMessage({
      type: 'answer',
      sender: 'owner',
      thread: exec1.thread,
      corpus: 'here is the input you asked for',
      createdAt: new Date(),
    });

    // Simulate the session reporting done.
    ctx.store.recordMessage({
      type: 'completion',
      sender: 'agent',
      thread: exec1.thread,
      corpus: 'done with turn 1',
      status: 'done',
      createdAt: new Date(),
    });

    // Advance recycles the seat-slot.
    r = await ctx.ticker.tick(new Date());
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);
    const recycleAction = r.actions.find(a => a.phase === 'advance' && a.action === 'recycle');
    if (!recycleAction) throw new Error('expected recycle action in advance phase');

    dump = ctx.store.dump();
    lines.push(`queue rows after recycle: ${dump.queue.length}`);
    if (dump.queue.length !== 1) throw new Error('expected one re-dispatch queue row');

    // Dispatch launches the recycled turn on the next tick.
    await sleep(1100);
    r = await ctx.ticker.tick(new Date());
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);
    const spawnAction = r.actions.find(a => a.phase === 'dispatch' && a.action === 'spawn');
    if (!spawnAction) throw new Error('expected spawn action for recycled turn');

    dump = ctx.store.dump();
    lines.push(`jobs_log rows: ${dump.jobs_log.length}`);
    if (dump.jobs_log.length !== 2) throw new Error(`expected 2 jobs_log rows, got ${dump.jobs_log.length}`);

    const exec2 = dump.jobs_log[1];
    lines.push(`exec2 id=${exec2.exec_id}, parent=${exec2.parent_exec_id}, thread=${exec2.thread}, status=${exec2.status}`);
    if (exec2.parent_exec_id !== exec1.exec_id) throw new Error('exec2 should be linked to exec1');
    if (exec2.thread !== exec1.thread) throw new Error('exec2 should carry the same chain thread');

    // Clean up.
    for (const exec of dump.jobs_log) {
      try { await ctx.mgr.kill(exec.exec_id); } catch {}
    }
  } finally {
    teardown(ctx);
  }
}

capture('probe-recycle', run);
