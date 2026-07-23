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
const { runWarningCheck } = require('../warnings-check');

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

    // D45 / task §5: "the system converts minutes → ticks". The property under
    // test is the CONVERSION — pass MINUTES and assert the stored tick is the
    // store's own arithmetic, not a tick the caller handed it. The expected
    // value is spelled out here (2 min x 6 ticks/min = 12) as an independent
    // oracle; reading it from the source constant would make this tautological.
    const SNOOZE_MINUTES = 2;
    const tickAtSnooze = ctx.store.getLastTick().tick;
    const snoozed = ctx.store.snoozeWarning({ kind: KIND, subject: subjectSnooze, minutes: SNOOZE_MINUTES });
    if (!snoozed) throw new Error('snoozeWarning returned null for a standing warning');
    const snoozeUntil = tickAtSnooze + 12;
    if (snoozed.snoozed_until_tick !== snoozeUntil) {
      throw new Error(
        `store did not convert minutes->ticks: snoozed_until_tick=${snoozed.snoozed_until_tick} != ${snoozeUntil} (current_tick ${tickAtSnooze} + ${SNOOZE_MINUTES}min x 6)`
      );
    }
    lines.push(`snooze: minutes=${SNOOZE_MINUTES} at current_tick ${tickAtSnooze} -> store computed snoozed_until_tick=${snoozed.snoozed_until_tick}`);

    // §5: snoozing a (kind, subject) with no standing warning is a clean no-op
    // — never an error, never a phantom row.
    const warningsBeforeNoop = ctx.store.listWarnings({ kind: KIND }).length;
    const noop = ctx.store.snoozeWarning({ kind: KIND, subject: 'exec-no-such-seat', minutes: SNOOZE_MINUTES });
    if (noop !== null) throw new Error(`snooze on absent warning returned a row: ${JSON.stringify(noop)}`);
    const warningsAfterNoop = ctx.store.listWarnings({ kind: KIND }).length;
    if (warningsAfterNoop !== warningsBeforeNoop) {
      throw new Error(`snooze on absent warning created a phantom row: ${warningsAfterNoop} != ${warningsBeforeNoop}`);
    }

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

    // ---------- Part D: a SNOOZED warning still self-clears ----------
    // Part C's snooze window has EXPIRED by now (it resumed announcing above),
    // so the warning is standing-but-un-snoozed. Clearing it here would only
    // re-test Part B. Re-snooze first, so the condition resolves while the
    // warning is genuinely snoozed — that is what assertion #6 is about.
    const tickAtResnooze = ctx.store.getLastTick().tick;
    const resnoozed = ctx.store.snoozeWarning({ kind: KIND, subject: subjectSnooze, minutes: SNOOZE_MINUTES });
    if (!resnoozed) throw new Error('re-snooze returned null for a standing warning');
    lines.push(`re-snooze at current_tick ${tickAtResnooze} -> snoozed_until_tick=${resnoozed.snoozed_until_tick}`);

    ctx.store.updateExecutionStatus(execSnooze.exec_id, { status: 'done', endedAt: new Date() });
    r = await ctx.ticker.tick();
    lines.push(`snoozed-clear tick ${r.tick}: warning actions=${JSON.stringify(r.actions.filter((a) => a.phase === 'warnings'))}`);

    // Guard the guard: if the clearing tick were not strictly inside the snooze
    // window, everything below would pass while proving nothing about clearing
    // WHILE snoozed.
    if (!(r.tick < resnoozed.snoozed_until_tick)) {
      throw new Error(
        `clear tick ${r.tick} is not inside the snooze window (snoozed_until_tick ${resnoozed.snoozed_until_tick}) — assertion #6 would be vacuous`
      );
    }

    const clearedSnooze = ctx.store.getStandingWarning({ kind: KIND, subject: subjectSnooze });
    if (clearedSnooze) throw new Error('expected snoozed warning cleared by system while snoozed');
    const notesFinal = warningNotes(ctx.store.dump().messages).length;
    if (notesFinal !== notesAfterSnooze) {
      throw new Error(`spurious note after snoozed clear: ${notesFinal} != ${notesAfterSnooze}`);
    }

    // §1: cleared warnings are RETAINED as rows (the history is the audit
    // trail) — the system clears by stamping cleared_at_tick, never by DELETE.
    const retained = ctx.store.listWarnings({ kind: KIND, subject: subjectSnooze });
    if (retained.length !== 1) {
      throw new Error(`expected the cleared warning retained as 1 row, got ${retained.length}`);
    }
    if (retained[0].cleared_at_tick !== r.tick) {
      throw new Error(`cleared_at_tick ${retained[0].cleared_at_tick} != clearing tick ${r.tick}`);
    }
    if (retained[0].snoozed_until_tick !== resnoozed.snoozed_until_tick) {
      throw new Error('clearing altered the snooze state instead of just stamping cleared_at_tick');
    }
    lines.push(`cleared-while-snoozed row retained: ${JSON.stringify(retained[0])}`);

    // ---------- Part E: the budget determination is the ticker's, not a copy ----------
    // Task §3: "blocked and out of budget" is evaluated EXACTLY as the ticker
    // already determines it. The budget belongs to the seat-slot's whole turn
    // CHAIN, so the count is chain-scoped — the same number for every execution
    // of the chain. A node-scoped ancestor-walk (counting one execution's own
    // ancestors) under-counts every blocked execution that is not the chain's
    // deepest node, and the ticker would then halt a seat for budget exhaustion
    // while this check stayed silent — D45 defeated, in silence.
    //
    // Build exactly the shape that separates the two determinations: a chain of
    // 3 recycles whose deepest BLOCKED node has only 2 ancestors (the tail
    // failed). Chain-scoped scores it 3 and raises; node-scoped scores it 2 and
    // stays silent at slotMaxRepeats=3.
    const mkExec = (parent) => ctx.store.recordExecutionStart({
      jobId: 'launch-agent',
      actionType: 'launch-agent',
      args: JSON.stringify({ profile: 'test-sleep' }),
      enqueuedBy: 'probe',
      firedTick: 1,
      firedAt: new Date(),
      parentExecId: parent,
    });
    const eRoot = mkExec(null);
    const eMid = mkExec(eRoot.exec_id);
    const eDeepBlocked = mkExec(eMid.exec_id);
    const eTail = mkExec(eDeepBlocked.exec_id);
    for (const e of [eRoot, eMid, eDeepBlocked]) {
      ctx.store.updateExecutionStatus(e.exec_id, { status: 'blocked', endedAt: new Date() });
    }
    ctx.store.updateExecutionStatus(eTail.exec_id, { status: 'failed', endedAt: new Date() });

    const CHAIN_RECYCLES = 3; // eMid, eDeepBlocked, eTail each have a parent
    const chainSubject = ctx.store.getExecution(eRoot.exec_id).thread;
    for (const e of [eRoot, eMid, eDeepBlocked, eTail]) {
      const n = ctx.store.countChainRecycles({ execId: e.exec_id });
      if (n !== CHAIN_RECYCLES) {
        throw new Error(`budget must be chain-scoped: exec ${e.exec_id} scored ${n} != ${CHAIN_RECYCLES}`);
      }
    }
    const eActions = [];
    runWarningCheck({ heartStore: ctx.store, tick: 1000, now: new Date(), slotMaxRepeats: CHAIN_RECYCLES, actions: eActions });
    const chainWarning = ctx.store.getStandingWarning({ kind: KIND, subject: chainSubject });
    if (!chainWarning) {
      throw new Error(
        `no warning raised for a chain that exhausted its ${CHAIN_RECYCLES}-recycle budget — the check is not using the ticker's chain-scoped determination`
      );
    }
    lines.push(`chain-scoped budget: subject=${chainSubject} recycles=${CHAIN_RECYCLES} deepest-blocked-ancestors=2 -> raised warning ${chainWarning.warning_id}`);

    // ---------- Part F: announce notes are stamped routed AT WRITE (task 7.25) ----------
    // The runWarningCheck call above ran OUTSIDE tick() — tick()'s in-tick compensation
    // never saw its announce note. The write-site itself must stamp routed_at_tick, or a
    // direct caller of runWarningCheck reintroduces permanently-unrouted notes.
    const eNotes = warningNotes(ctx.store.dump().messages);
    const outOfTickNote = eNotes[eNotes.length - 1];
    if (!outOfTickNote) throw new Error('Part E announce note not found');
    if (outOfTickNote.routed_at_tick !== 1000) {
      throw new Error(
        `announce note written by runWarningCheck OUTSIDE tick() is not stamped at write: routed_at_tick=${outOfTickNote.routed_at_tick} != 1000 (task 7.25)`
      );
    }
    const unroutedTickerNotes = ctx.store.dump().messages.filter(
      (m) => m.type === 'note' && m.sender === 'ticker' && (m.routed_at_tick === null || m.routed_at_tick === undefined)
    );
    if (unroutedTickerNotes.length !== 0) {
      throw new Error(`${unroutedTickerNotes.length} ticker note(s) left unrouted: ${JSON.stringify(unroutedTickerNotes.map((m) => m.msg_id))}`);
    }
    lines.push(`out-of-tick announce note msg_id=${outOfTickNote.msg_id} stamped routed_at_tick=${outOfTickNote.routed_at_tick} at write; 0 unrouted ticker notes (task 7.25)`);
  } finally {
    teardown(ctx);
  }
}

capture('probe-warning-lifecycle', run);
