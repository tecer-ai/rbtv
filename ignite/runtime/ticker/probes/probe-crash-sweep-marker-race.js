'use strict';

// Tasks 29 + 94 — crash-sweep marker race and named add-job failure corpus.
//
// Pins the ExecStopPost window without racing systemd: a planted turn whose process is already
// gone and whose exit marker file does not exist. Production writes that marker in ExecStopPost
// AFTER the unit reports inactive, so this is the same observation the sweep makes on a
// short-lived clean exec (probe-dispatch-door-recovery comments: 1/5 solo, 3/10 concurrent).
//
// Reverting the ticker defer + named-corpus fix makes this probe go red.

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, capture } = require('./lib');

function plant(ctx, { jobId, sessionId = null, pid = null, logPath = null }) {
  if (!ctx.store.getJob(jobId)) {
    ctx.store.registerJob({
      jobId,
      actionType: 'launch-agent',
      function: 'launch-agent',
      argsSchema: JSON.stringify({ required: {}, optional: {} }),
    });
  }
  const exec = ctx.store.recordExecutionStart({
    jobId,
    actionType: 'launch-agent',
    args: '{}',
    enqueuedBy: 'probe',
    sessionMode: 'headless',
    firedTick: 1,
    firedAt: new Date(),
    sessionId,
    pid,
    workdir: ctx.defaultWorkdir,
  });
  const patch = { status: 'running' };
  if (logPath) patch.logPath = logPath;
  ctx.store.updateExecutionStatus(exec.exec_id, patch);
  return ctx.store.getExecution(exec.exec_id);
}

function completionsFor(ctx, exec) {
  return ctx.store.dump().messages.filter((m) => m.type === 'completion' && m.thread === (exec.thread || `exec-${exec.exec_id}`));
}

function haltedNote(ctx, execId) {
  return ctx.store.dump().messages.find((m) =>
    m.type === 'note' && m.sender === 'ticker' && (m.corpus || '').includes(`slot halted: session crashed (exec ${execId})`));
}

async function run(lines) {
  const ctx = setup();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  try {
    // ── 29 · first tick, spawned, marker absent, process gone ─────────────────
    const spawned = plant(ctx, { jobId: 'marker-race-spawned', sessionId: 'probe-sess-marker-absent' });
    const r1 = await ctx.ticker.tick(new Date());
    const row1 = ctx.store.getExecution(spawned.exec_id);
    const swept1 = r1.actions.find((a) => a.phase === 'enforce' && a.action === 'crash-sweep' && a.execId === spawned.exec_id);
    const deferred1 = r1.actions.find((a) => a.phase === 'enforce' && a.action === 'crash-sweep-deferred' && a.execId === spawned.exec_id);
    leg('29-defer', 'marker-absent + process-gone is NOT failed on the first tick',
      row1.status !== 'failed' && !swept1 && !haltedNote(ctx, spawned.exec_id),
      `status=${row1.status} crash-sweep=${Boolean(swept1)} deferred=${Boolean(deferred1)} halted=${Boolean(haltedNote(ctx, spawned.exec_id))}`);

    // ── 29 · second consecutive tick, still nothing → genuine crash ───────────
    const r2 = await ctx.ticker.tick(new Date());
    const row2 = ctx.store.getExecution(spawned.exec_id);
    const swept2 = r2.actions.find((a) => a.phase === 'enforce' && a.action === 'crash-sweep' && a.execId === spawned.exec_id);
    const comps2 = completionsFor(ctx, row2);
    const corpus2 = comps2[0] ? comps2[0].corpus : '';
    leg('29-crash', 'two consecutive ticks with no marker and no result still fail and halt',
      row2.status === 'failed' && Boolean(swept2) && Boolean(haltedNote(ctx, spawned.exec_id))
        && corpus2.includes('no exit marker found') && !corpus2.includes('exit=null'),
      `status=${row2.status} crash-sweep=${Boolean(swept2)} halted=${Boolean(haltedNote(ctx, spawned.exec_id))} corpus=${JSON.stringify(corpus2.split('\n')[0])}`);

    // ── 29 · marker-absent + parseable result → done ──────────────────────────
    const resultLog = path.join(ctx.tmp, 'result.log');
    fs.writeFileSync(resultLog, `${JSON.stringify({ type: 'result', result: 'seat finished cleanly' })}\n`);
    const withResult = plant(ctx, { jobId: 'marker-race-result', sessionId: 'probe-sess-with-result', logPath: resultLog });
    const r3 = await ctx.ticker.tick(new Date());
    const row3 = ctx.store.getExecution(withResult.exec_id);
    const comps3 = completionsFor(ctx, row3);
    const clean = r3.actions.find((a) => a.phase === 'enforce' && a.action === 'clean-exit-sweep' && a.execId === withResult.exec_id);
    leg('29-result', 'marker-absent + parseable result line records done',
      row3.status === 'done' && Boolean(clean) && comps3[0] && comps3[0].corpus === 'seat finished cleanly' && !haltedNote(ctx, withResult.exec_id),
      `status=${row3.status} clean-exit-sweep=${Boolean(clean)} corpus=${JSON.stringify(comps3[0] && comps3[0].corpus)}`);

    // ── 94 · never spawned ────────────────────────────────────────────────────
    const never = plant(ctx, { jobId: 'marker-race-never' });
    const r4 = await ctx.ticker.tick(new Date());
    const row4 = ctx.store.getExecution(never.exec_id);
    const comps4 = completionsFor(ctx, row4);
    const corpus4 = comps4[0] ? comps4[0].corpus : '';
    leg('94-never', 'never-spawned failure names never spawned, not exit=null',
      row4.status === 'failed' && /never spawned/.test(corpus4) && !corpus4.includes('exit=null') && !/no exit marker found/.test(corpus4),
      `status=${row4.status} session_id=${row4.session_id} pid=${row4.pid} corpus=${JSON.stringify(corpus4.split('\n')[0])}`);

    // ── 94 · spawned-and-crashed corpus is the two-tick arm above ─────────────
    leg('94-crashed', 'spawned-and-crashed corpus names no exit marker found, distinct from never spawned',
      corpus2.includes('no exit marker found') && !corpus2.includes('never spawned') && !corpus2.includes('exit=null'),
      `spawned corpus=${JSON.stringify(corpus2.split('\n')[0])} never corpus=${JSON.stringify(corpus4.split('\n')[0])}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`crash-sweep marker-race probes failed: ${fails.join(', ')}`);
  } finally {
    teardown(ctx);
  }
}

capture('probe-crash-sweep-marker-race', run);
