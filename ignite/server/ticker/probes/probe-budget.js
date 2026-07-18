'use strict';

// Budget semantics per the p7-multiturn owner ruling (2026-07-18): a recycle
// triggered by SENDER input never consumes the automatic budget — the count
// "restarts on any owner action" — so done-with-pending-input recycles flow
// UNGATED past slot_max_repeats. (This supersedes the former chain-total gate
// this probe certified; ticker-engine-spec Test Plan row 8's gesture is a
// task-7.5 divergence row. The AUTOMATIC budget bound — the compaction loop —
// is certified by probe-multiturn scenario D2.) Also re-certifies D39: the
// ticker writes NO notes to a seat's thread, and a fresh owner enqueue always
// opens a NEW chain.

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

    // Helper: land owner input + a done completion for the chain's live turn,
    // then tick twice (advance routes; the +1s re-dispatch row fires).
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
      return [...rr.actions, ...rd.actions];
    }

    // Three sender-input turns with slot_max_repeats=2: ALL must recycle (the
    // superseded chain-total gate would refuse the third).
    let allActions = [];
    let lastExec = exec;
    for (let i = 1; i <= 3; i++) {
      const acts = await turn(lastExec.exec_id);
      allActions = allActions.concat(acts);
      const dump = ctx.store.dump();
      if (dump.jobs_log.length !== 1 + i) {
        throw new Error(`expected ${1 + i} execs after sender-input turn ${i}, got ${dump.jobs_log.length}`);
      }
      const child = dump.jobs_log[i];
      if (child.parent_exec_id !== lastExec.exec_id) {
        throw new Error(`turn ${i}: child parent ${child.parent_exec_id} != ${lastExec.exec_id}`);
      }
      lastExec = child;
    }
    if (allActions.some((a) => String(a.action || '').includes('budget-exhausted'))) {
      throw new Error('a sender-input recycle hit a budget gate — ruling broken');
    }
    lines.push('PASS: 3 sender-input recycles flowed ungated at slot_max_repeats=2 (linear chain of 4 execs)');

    let dump = ctx.store.dump();
    const seatNotes = dump.messages.filter(m => m.type === 'note' && m.sender === 'ticker' && m.thread === exec.thread);
    if (seatNotes.length > 0) throw new Error(`ticker note found on seat thread ${exec.thread}: ${JSON.stringify(seatNotes)}`);
    lines.push('PASS: no ticker notes on the seat thread (D39)');

    // A fresh owner enqueue opens a NEW chain (root, parent NULL).
    enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt: new Date() });
    r = await ctx.ticker.tick(new Date());
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);
    const spawnAction = r.actions.find(a => a.phase === 'dispatch' && a.action === 'spawn');
    if (!spawnAction) throw new Error('expected fresh owner enqueue to launch');

    dump = ctx.store.dump();
    if (dump.jobs_log.length !== 5) throw new Error(`expected 5 execs after fresh enqueue, got ${dump.jobs_log.length}`);
    const fresh = dump.jobs_log[4];
    if (fresh.parent_exec_id !== null) throw new Error('fresh owner enqueue should start a new chain');
    lines.push('PASS: fresh owner enqueue opened a new chain');

    // Clean up.
    for (const e of dump.jobs_log) {
      try { await ctx.mgr.kill(e.exec_id); } catch {}
    }
  } finally {
    teardown(ctx);
  }
}

capture('probe-budget', run);
