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

    const exec = ctx.store.dump().jobs_log[0];
    lines.push(`exec id=${exec.exec_id}, status=${exec.status}`);

    // Let it settle, then kill the underlying process.
    await sleep(500);
    const liveInfo = await ctx.mgr.status(exec.exec_id);
    lines.push(`unit name: ${liveInfo.unitName}`);

    // Kill via systemctl --signal=SIGKILL to simulate a crash.
    const { execFileSync } = require('node:child_process');
    try {
      execFileSync('systemctl', ['--user', 'kill', '--signal=SIGKILL', liveInfo.unitName], { stdio: 'ignore', timeout: 10000 });
    } catch (err) {
      lines.push(`kill warning: ${err.message}`);
    }

    await sleep(500);

    // Tick to trigger crash sweep.
    r = await ctx.ticker.tick(new Date());
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);

    const crashAction = r.actions.find(a => a.phase === 'enforce' && a.action === 'crash-sweep');
    if (!crashAction) throw new Error('expected crash-sweep action');

    // Next tick: Advance resolves the synthetic completion.
    r = await ctx.ticker.tick(new Date());
    lines.push(`tick ${r.tick}: ${JSON.stringify(r.actions)}`);

    const dump = ctx.store.dump();
    const finalExec = dump.jobs_log[0];
    lines.push(`final status: ${finalExec.status}`);
    if (finalExec.status !== 'failed') throw new Error(`expected failed, got ${finalExec.status}`);

    const completions = dump.messages.filter(m => m.type === 'completion' && m.thread === finalExec.thread);
    lines.push(`completions on thread: ${completions.length}`);
    if (completions.length !== 1) throw new Error('expected one synthetic completion');
    if (completions[0].status !== 'failed') throw new Error('expected failed completion');

    // `owner-feed` is a SHARED destination aggregating every ticker note, so a count
    // does not identify THIS note. Assert the crash note by its corpus.
    const notes = dump.messages.filter(m => m.type === 'note' && m.sender === 'ticker' && m.thread === 'owner-feed');
    lines.push(`notes on owner-feed: ${notes.length}`);
    const crashNote = notes.find(m => m.corpus.includes(`slot halted: session crashed (exec ${finalExec.exec_id})`));
    if (!crashNote) throw new Error(`expected the session-crashed note on owner-feed; got: ${JSON.stringify(notes.map(m => m.corpus))}`);
    lines.push(`crash note: ${crashNote.corpus}`);

    const seatNotes = dump.messages.filter(m => m.type === 'note' && m.sender === 'ticker' && m.thread === finalExec.thread);
    if (seatNotes.length > 0) throw new Error(`ticker note found on seat thread ${finalExec.thread}: ${JSON.stringify(seatNotes)}`);

    // No retry: queue should be empty.
    if (dump.queue.length !== 0) throw new Error('expected no retry queue row');
  } finally {
    teardown(ctx);
  }
}

capture('probe-crash', run);
