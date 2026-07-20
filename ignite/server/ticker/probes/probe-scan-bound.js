'use strict';

// Task 7.19 (batch-08 item 10 parts 1+2): per-tick scan work must NOT grow
// with accumulated notes/executions.
//  - Root fix: ticker-authored owner-feed notes are marked routed AT WRITE.
//  - Durable bound: Advance fetches unrouted COMPLETIONS only (partial-index
//    backed), and the wake loop is message-watermark-driven — it examines new
//    sender messages, never every done tail.
// The probe grows the store in steps (forgetful-writer notes + synthetic done
// chains) and asserts the per-tick scan figures (the `scan-stats` action) stay
// FLAT, then proves the bound did not break function: a genuinely new sender
// message still wakes its chain.

const { setup, teardown, registerLaunchAgentJob, capture } = require('./lib');

function scanStats(r) {
  const a = r.actions.find(x => x.phase === 'advance' && x.action === 'scan-stats');
  if (!a) throw new Error('expected a scan-stats action on every tick');
  return a;
}

// A synthetic ended chain: one done launch-agent execution (a childless tail)
// with its completion message and watermark, minted straight into the store.
function insertDoneTail(ctx, jobId) {
  const now = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const res = ctx.store._prepare(`
    INSERT INTO jobs_log (job_id, action_type, args, enqueued_by, session_mode, fired_tick, fired_at, status, ended_at)
    VALUES (?, 'launch-agent', '{"profile":"test-sleep"}', 'probe', 'headless', 0, ?, 'done', ?)
  `).run(jobId, now, now);
  const execId = Number(res.lastInsertRowid);
  const msg = ctx.store.recordMessage({
    type: 'completion', sender: 'ticker', thread: `exec-${execId}`,
    corpus: 'synthetic turn answer', status: 'done', createdAt: new Date(),
  });
  ctx.store._prepare('UPDATE messages SET routed_at_tick = 0 WHERE msg_id = ?').run(msg.msg_id);
  ctx.store._prepare('UPDATE jobs_log SET completion_msg_id = ? WHERE exec_id = ?').run(msg.msg_id, execId);
  return execId;
}

async function run(lines) {
  const ctx = setup();
  try {
    registerLaunchAgentJob(ctx);

    // Boot tick: the one full tail scan.
    let r = await ctx.ticker.tick(new Date());
    let s = scanStats(r);
    lines.push(`boot tick ${r.tick}: ${JSON.stringify(s)}`);
    if (!s.wakeBootScan) throw new Error('expected the boot tick to be the full tail scan');

    // Baseline steady-state tick.
    r = await ctx.ticker.tick(new Date());
    const baseline = scanStats(r);
    lines.push(`baseline tick ${r.tick}: ${JSON.stringify(baseline)}`);
    if (baseline.wakeBootScan) throw new Error('expected watermark mode after boot');

    // Growth steps: each adds 100 UNSTAMPED ticker feed notes (a future
    // forgetful writer — the worst case the bound must absorb) plus 20
    // synthetic ended chains. The per-tick scan figures must stay flat.
    const flat = [];
    for (let step = 0; step < 3; step++) {
      for (let i = 0; i < 100; i++) {
        ctx.store.recordMessage({
          type: 'note', sender: 'ticker', thread: 'owner-feed',
          corpus: `forgetful-writer note ${step}-${i}`, createdAt: new Date(),
        });
      }
      for (let i = 0; i < 20; i++) insertDoneTail(ctx, 'launch-agent');
      r = await ctx.ticker.tick(new Date());
      s = scanStats(r);
      flat.push(s);
      lines.push(`growth step ${step + 1} tick ${r.tick}: ${JSON.stringify(s)}`);
      if (s.unroutedCompletionsScanned !== baseline.unroutedCompletionsScanned) {
        throw new Error(`unrouted-completion scan grew with notes: ${s.unroutedCompletionsScanned}`);
      }
      if (s.wakeCandidates !== 0) {
        throw new Error(`wake scan grew with accumulated executions: ${s.wakeCandidates} candidates with no new message`);
      }
      // The watermark must advance past EXAMINED rows, not only matched ones —
      // left behind the filtered-out notes it would re-walk them every tick.
      const maxId = ctx.store._prepare('SELECT MAX(msg_id) AS m FROM messages').get().m;
      if (s.wakeWatermark !== maxId) {
        throw new Error(`watermark lags the examined range: ${s.wakeWatermark} < max msg_id ${maxId}`);
      }
    }
    const unroutedAll = ctx.store.getMessages({ unroutedOnly: true }).length;
    const unroutedCompletions = ctx.store.getMessages({ unroutedOnly: true, type: 'completion' }).length;
    lines.push(`store now: unrouted total=${unroutedAll}, unrouted completions=${unroutedCompletions}, done tails=60`);
    if (unroutedAll < 300) throw new Error('expected the unstamped notes to accumulate in this simulation');
    if (unroutedCompletions !== 0) throw new Error(`expected 0 unrouted completions, got ${unroutedCompletions}`);
    lines.push('scan figures FLAT across 3 growth steps (300 notes + 60 chains)');

    // Root fix: a note the TICKER itself writes is routed at write. Trigger the
    // anomaly path with a completion for an unknown thread.
    ctx.store.recordMessage({
      type: 'completion', sender: 'probe', thread: 'exec-999999',
      corpus: 'orphan completion', status: 'done', createdAt: new Date(),
    });
    r = await ctx.ticker.tick(new Date());
    const anomaly = ctx.store.getMessages({}).find(m => m.type === 'note' && m.sender === 'ticker' && m.corpus.startsWith('anomaly:'));
    if (!anomaly) throw new Error('expected the anomaly note');
    if (anomaly.routed_at_tick === null) throw new Error('ticker-authored feed note must be routed at write');
    lines.push(`ticker-authored note routed at write: routed_at_tick=${anomaly.routed_at_tick}`);

    // Function intact: a genuinely new sender message wakes exactly its chain.
    const targetExec = insertDoneTail(ctx, 'launch-agent');
    await ctx.ticker.tick(new Date()); // absorb the tail's completion row into the watermark
    ctx.store.recordMessage({
      type: 'ask', sender: 'owner', thread: `exec-${targetExec}`,
      corpus: 'follow-up question', createdAt: new Date(),
    });
    r = await ctx.ticker.tick(new Date());
    s = scanStats(r);
    lines.push(`wake tick ${r.tick}: ${JSON.stringify(s)}`);
    const wake = r.actions.find(a => a.phase === 'advance' && a.action === 'wake-redispatch' && a.execId === targetExec);
    if (!wake) throw new Error('expected wake-redispatch of the messaged chain');
    if (s.wakeCandidates !== 1) throw new Error(`expected exactly 1 wake candidate, got ${s.wakeCandidates}`);
    lines.push(`new sender message woke exec ${targetExec} with 1 candidate examined (61 tails on disk)`);
  } finally {
    teardown(ctx);
  }
}

capture('probe-scan-bound', run);
