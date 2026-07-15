'use strict';

const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, capture } = require('./lib');

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

    let warned = false;
    let stalled = false;
    for (let i = 0; i < 30; i++) {
      r = await ctx.ticker.tick(new Date());
      if (r.actions.some(a => a.phase === 'enforce' && a.action === 'warn')) {
        warned = true;
        lines.push(`warn at tick ${r.tick}`);
      }
      if (r.actions.some(a => a.phase === 'enforce' && a.action === 'stalled')) {
        stalled = true;
        lines.push(`stalled at tick ${r.tick}`);
        break;
      }
    }

    if (!warned) throw new Error('expected warn note before stall');
    if (!stalled) throw new Error('expected stalled status');

    const dump = ctx.store.dump();
    const finalExec = dump.jobs_log[0];
    lines.push(`final status: ${finalExec.status}`);
    if (finalExec.status !== 'stalled') throw new Error(`expected stalled, got ${finalExec.status}`);

    // `owner-feed` is a SHARED destination that aggregates every ticker note, so a
    // count no longer identifies these two notes (any 2 notes would satisfy `>= 2`).
    // Assert each of the warn + stall notes by its corpus.
    const notes = dump.messages.filter(m => m.type === 'note' && m.sender === 'ticker' && m.thread === 'owner-feed');
    lines.push(`notes on owner-feed: ${notes.length}`);
    const warnNote = notes.find(m => m.corpus.includes('silent warning after'));
    const stallNote = notes.find(m => m.corpus.includes('slot stalled after'));
    if (!warnNote) throw new Error(`expected the silent-warning note on owner-feed; got: ${JSON.stringify(notes.map(m => m.corpus))}`);
    if (!stallNote) throw new Error(`expected the slot-stalled note on owner-feed; got: ${JSON.stringify(notes.map(m => m.corpus))}`);
    lines.push(`warn note: ${warnNote.corpus}`);
    lines.push(`stall note: ${stallNote.corpus}`);

    const seatNotes = dump.messages.filter(m => m.type === 'note' && m.sender === 'ticker' && m.thread === finalExec.thread);
    if (seatNotes.length > 0) throw new Error(`ticker note found on seat thread ${finalExec.thread}: ${JSON.stringify(seatNotes)}`);

    const live = await ctx.mgr.status(finalExec.exec_id);
    lines.push(`process live after stall: ${live.live}`);
    if (!live.live) throw new Error('process should remain alive after stall');

    try { await ctx.mgr.kill(finalExec.exec_id); } catch {}
  } finally {
    teardown(ctx);
  }
}

capture('probe-stall', run);
