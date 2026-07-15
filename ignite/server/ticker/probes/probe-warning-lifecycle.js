'use strict';

const {
  setup,
  teardown,
  registerLaunchAgentJob,
  enqueueLaunchAgent,
  capture,
  sleep,
} = require('./lib');
const { WARNING_KINDS } = require('../../heart/warnings');

const KIND = WARNING_KINDS.SEAT_BLOCKED_BUDGET_EXHAUSTED;

function warningNotes(messages) {
  return messages.filter(
    (m) => m.type === 'note' && m.sender === 'ticker' && m.thread === 'owner-feed' && m.corpus.includes('blocked and out of budget')
  );
}

async function makeBlockedBudgetExhaustedSeat(ctx, lines) {
  registerLaunchAgentJob(ctx);
  const q1 = enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt: new Date() });
  let r = await ctx.ticker.tick();
  lines.push(`launch tick ${r.tick}: warning actions=${JSON.stringify(r.actions.filter((a) => a.phase === 'warnings'))}`);

  const exec1 = ctx.store.dump().jobs_log.find((row) => row.queue_id === q1.queue_id);
  if (!exec1) throw new Error('exec1 not found after launch');

  ctx.store.recordMessage({ type: 'answer', sender: 'owner', thread: exec1.thread, corpus: 'more', createdAt: new Date() });
  ctx.store.recordMessage({
    type: 'completion',
    sender: 'agent',
    thread: exec1.thread,
    corpus: 'done',
    status: 'done',
    createdAt: new Date(),
  });
  r = await ctx.ticker.tick();
  lines.push(`recycle tick ${r.tick}: warning actions=${JSON.stringify(r.actions.filter((a) => a.phase === 'warnings'))}`);
  await sleep(1100);
  r = await ctx.ticker.tick();
  lines.push(`launch2 tick ${r.tick}: warning actions=${JSON.stringify(r.actions.filter((a) => a.phase === 'warnings'))}`);

  const exec2 = ctx.store.dump().jobs_log.find((row) => row.parent_exec_id === exec1.exec_id);
  if (!exec2) throw new Error('exec2 not recycled');

  ctx.store.recordMessage({
    type: 'completion',
    sender: 'agent',
    thread: exec2.thread,
    corpus: 'blocked',
    status: 'blocked',
    createdAt: new Date(),
  });
  r = await ctx.ticker.tick();
  lines.push(`blocked tick ${r.tick}: warning actions=${JSON.stringify(r.actions.filter((a) => a.phase === 'warnings'))}`);

  const exec2After = ctx.store.getExecution(exec2.exec_id);
  if (exec2After.status !== 'blocked') throw new Error(`expected exec2 blocked, got ${exec2After.status}`);
  return exec2;
}

async function run(lines) {
  const ctx = setup({ slot_max_repeats: 1, stall_warn_ticks: 1000, stall_halt_ticks: 10000 });
  try {
    // ---------- Part A: raise, no duplicate, cadence ----------
    const exec = await makeBlockedBudgetExhaustedSeat(ctx, lines);
    const subject = exec.thread;

    for (let i = 0; i < 12; i++) {
      const r = await ctx.ticker.tick();
      lines.push(`cadence tick ${r.tick}: warning actions=${JSON.stringify(r.actions.filter((a) => a.phase === 'warnings'))}`);
    }

    const standing = ctx.store.listWarnings({ standingOnly: true, kind: KIND });
    if (standing.length !== 1) {
      throw new Error(`expected 1 standing warning, got ${standing.length}: ${JSON.stringify(standing)}`);
    }
    if (standing[0].subject !== subject) {
      throw new Error(`expected subject ${subject}, got ${standing[0].subject}`);
    }
    lines.push(`standing warning: ${JSON.stringify(standing[0])}`);

    const notes = warningNotes(ctx.store.dump().messages);
    lines.push(`warning notes count: ${notes.length}`);
    if (notes.length !== 3) {
      throw new Error(`expected 3 warning notes, got ${notes.length}: ${JSON.stringify(notes.map((n) => ({ tick: n.broadcast_at_tick, corpus: n.corpus })))}`);
    }
    const noteTicks = notes.map((n) => n.broadcast_at_tick);
    lines.push(`warning note ticks: ${JSON.stringify(noteTicks)}`);
    if (noteTicks[0] !== standing[0].raised_at_tick) {
      throw new Error(`first note not on raise tick: ${noteTicks[0]} != ${standing[0].raised_at_tick}`);
    }
    if (noteTicks[1] - noteTicks[0] !== 6) {
      throw new Error(`second note cadence wrong: ${noteTicks[1]} - ${noteTicks[0]} != 6`);
    }
    if (noteTicks[2] - noteTicks[1] !== 6) {
      throw new Error(`third note cadence wrong: ${noteTicks[2]} - ${noteTicks[1]} != 6`);
    }

    // ---------- Part B: system clears and stream terminates ----------
    const notesBeforeClear = notes.length;
    ctx.store.updateExecutionStatus(exec.exec_id, { status: 'done', endedAt: new Date() });
    let r = await ctx.ticker.tick();
    lines.push(`clear tick ${r.tick}: warning actions=${JSON.stringify(r.actions.filter((a) => a.phase === 'warnings'))}`);

    const afterClear = ctx.store.getStandingWarning({ kind: KIND, subject });
    if (afterClear) throw new Error('expected warning cleared, still standing');
    const notesAfterClear = warningNotes(ctx.store.dump().messages).length;
    if (notesAfterClear !== notesBeforeClear) {
      throw new Error(`spurious warning note after clear: ${notesAfterClear} != ${notesBeforeClear}`);
    }

    for (let i = 0; i < 5; i++) {
      await ctx.ticker.tick();
    }
    const notesAfterQuiet = warningNotes(ctx.store.dump().messages).length;
    if (notesAfterQuiet !== notesBeforeClear) {
      throw new Error(`warning notes grew after condition cleared: ${notesAfterQuiet} != ${notesBeforeClear}`);
    }

    // ---------- Part C: snooze suppresses, never clears ----------
    const execSnooze = await makeBlockedBudgetExhaustedSeat(ctx, lines);
    const subjectSnooze = execSnooze.thread;
    const raisedSnooze = ctx.store.getStandingWarning({ kind: KIND, subject: subjectSnooze });
    if (!raisedSnooze) throw new Error('warning not raised for snooze test');

    const snoozeUntil = raisedSnooze.raised_at_tick + 12; // 2 minutes in ticks
    ctx.store.snoozeWarning({ kind: KIND, subject: subjectSnooze, snoozedUntilTick: snoozeUntil });
    const notesBeforeSnooze = warningNotes(ctx.store.dump().messages).length;

    for (let i = 0; i < 11; i++) {
      await ctx.ticker.tick();
    }
    const notesDuringSnooze = warningNotes(ctx.store.dump().messages).length;
    if (notesDuringSnooze !== notesBeforeSnooze) {
      throw new Error(`notes emitted while snoozed: ${notesDuringSnooze} != ${notesBeforeSnooze}`);
    }
    const stillStanding = ctx.store.getStandingWarning({ kind: KIND, subject: subjectSnooze });
    if (!stillStanding) throw new Error('snooze cleared the warning');
    if (stillStanding.snoozed_until_tick !== snoozeUntil) {
      throw new Error(`snooze tick mismatch: ${stillStanding.snoozed_until_tick} != ${snoozeUntil}`);
    }

    r = await ctx.ticker.tick();
    lines.push(`snooze-resume tick ${r.tick}: warning actions=${JSON.stringify(r.actions.filter((a) => a.phase === 'warnings'))}`);
    const notesAfterSnooze = warningNotes(ctx.store.dump().messages).length;
    if (notesAfterSnooze !== notesBeforeSnooze + 1) {
      throw new Error(`expected 1 note after snooze expiry, got ${notesAfterSnooze - notesBeforeSnooze}`);
    }

    // ---------- Part D: snoozed still self-clears ----------
    ctx.store.updateExecutionStatus(execSnooze.exec_id, { status: 'done', endedAt: new Date() });
    r = await ctx.ticker.tick();
    lines.push(`snoozed-clear tick ${r.tick}: warning actions=${JSON.stringify(r.actions.filter((a) => a.phase === 'warnings'))}`);

    const clearedSnooze = ctx.store.getStandingWarning({ kind: KIND, subject: subjectSnooze });
    if (clearedSnooze) throw new Error('expected snoozed warning cleared by system');
    const notesFinal = warningNotes(ctx.store.dump().messages).length;
    if (notesFinal !== notesAfterSnooze) {
      throw new Error(`spurious note after snoozed clear: ${notesFinal} != ${notesAfterSnooze}`);
    }
  } finally {
    teardown(ctx);
  }
}

capture('probe-warning-lifecycle', run);
