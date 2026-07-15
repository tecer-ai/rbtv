'use strict';

const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture, sleep } = require('./lib');

async function run(lines) {
  const ctx = setup({ slot_max_repeats: 2 });
  try {
    registerLaunchAgentJob(ctx);
    const now = new Date();
    enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt: now });

    lines.push('enqueued one due launch-agent job with slot_max_repeats=2');

    // Tick 1: launch first turn.
    let r = await ctx.ticker.tick(now);
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);

    let exec = ctx.store.dump().jobs_log[0];
    lines.push(`exec1 id=${exec.exec_id}, thread=${exec.thread}`);

    // Helper to simulate a done+pending completion and advance.
    async function turn(execId) {
      const e = ctx.store.getExecution(execId);
      ctx.store.recordMessage({
        type: 'answer',
        sender: 'owner',
        thread: e.thread,
        corpus: 'more input',
        createdAt: new Date(),
      });
      ctx.store.recordMessage({
        type: 'completion',
        sender: 'agent',
        thread: e.thread,
        corpus: 'done',
        status: 'done',
        createdAt: new Date(),
      });
      const rr = await ctx.ticker.tick(new Date());
      lines.push(`tick ${rr.tick}: ${JSON.stringify(rr.actions)}`);
      await sleep(1100);
      const rd = await ctx.ticker.tick(new Date());
      lines.push(`tick ${rd.tick}: ${JSON.stringify(rd.actions)}`);
    }

    // Turn 1 -> recycle 1 (exec2).
    await turn(exec.exec_id);
    let dump = ctx.store.dump();
    if (dump.jobs_log.length !== 2) throw new Error(`expected 2 execs after turn 1, got ${dump.jobs_log.length}`);
    const exec2 = dump.jobs_log[1];

    // Turn 2 -> recycle 2 (exec3).
    await turn(exec2.exec_id);
    dump = ctx.store.dump();
    if (dump.jobs_log.length !== 3) throw new Error(`expected 3 execs after turn 2, got ${dump.jobs_log.length}`);
    const exec3 = dump.jobs_log[2];

    // Turn 3 -> budget exhausted, no recycle.
    ctx.store.recordMessage({
      type: 'answer',
      sender: 'owner',
      thread: exec3.thread,
      corpus: 'more input',
      createdAt: new Date(),
    });
    ctx.store.recordMessage({
      type: 'completion',
      sender: 'agent',
      thread: exec3.thread,
      corpus: 'done',
      status: 'done',
      createdAt: new Date(),
    });
    r = await ctx.ticker.tick(new Date());
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);
    const budgetAction = r.actions.find(a => a.phase === 'advance' && a.action === 'budget-exhausted');
    if (!budgetAction) throw new Error('expected budget-exhausted action');

    dump = ctx.store.dump();
    if (dump.queue.length !== 0) throw new Error('expected no re-dispatch queue row after budget exhausted');
    const notes = dump.messages.filter(m => m.type === 'note' && m.thread === 'owner-feed' && m.corpus.includes('budget exhausted'));
    if (notes.length === 0) throw new Error('expected owner note about exhausted budget');

    const seatNotes = dump.messages.filter(m => m.type === 'note' && m.sender === 'ticker' && m.thread === exec3.thread);
    if (seatNotes.length > 0) throw new Error(`ticker note found on seat thread ${exec3.thread}: ${JSON.stringify(seatNotes)}`);

    // Owner re-arms with a fresh enqueue.
    enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt: new Date() });
    r = await ctx.ticker.tick(new Date());
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);
    const spawnAction = r.actions.find(a => a.phase === 'dispatch' && a.action === 'spawn');
    if (!spawnAction) throw new Error('expected fresh owner enqueue to launch');

    dump = ctx.store.dump();
    if (dump.jobs_log.length !== 4) throw new Error(`expected 4 execs after re-arm, got ${dump.jobs_log.length}`);
    const exec4 = dump.jobs_log[3];
    if (exec4.parent_exec_id !== null) throw new Error('fresh owner enqueue should start a new chain');

    // Clean up.
    for (const e of dump.jobs_log) {
      try { await ctx.mgr.kill(e.exec_id); } catch {}
    }
  } finally {
    teardown(ctx);
  }
}

capture('probe-budget', run);
