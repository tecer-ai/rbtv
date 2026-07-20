'use strict';

// p7-multiturn — multi-turn chat conversations in the ticker engine. Four scenarios:
//   A. Honest clean turn-end: exit-marker 0 → completion `done`, corpus = the worker's
//      extracted stream-json answer; exec ends done/exit 0 (never the failed-halt path).
//   B. Wake-on-message + history composition: a finished chain re-dispatches ONLY on a
//      genuinely new sender message (never quiet, never on ticker rows); each chained turn's
//      prompt file carries the composed conversation; history accumulates across ≥3 turns.
//   C. Compaction: a transcript over `history_compact_chars` turns the fire into a COMPACTION
//      turn (compact:true spawn action, compaction prompt); its completion always re-dispatches
//      the answering turn (linear chain), whose prompt splices at the summary.
//   D. Budget ruling: sender-message wakes never consume the automatic budget (3 wakes pass with
//      slot_max_repeats=2); automatic compaction recycles DO (exhaustion at the gate).
//
// The chat worker echoes a deterministic, prompt-dependent answer as a stream-json result line:
// ANSWER-len-<stdin length>. Distinct per turn (prompts grow), so history assertions can pin
// WHICH turn's answer appears where.

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, registerLaunchAgentJob, enqueueLaunchAgent, sleep, capture } = require('./lib');

function makeCtx(configOverrides) {
  // \173/\175 are printf octal escapes for { } and wc -c stands in for ${#P} —
  // ANY literal brace in a profile argv reads as a template slot to the spawn
  // config validator.
  const echoResult = 'P=$(cat); L=$(printf %s "$P" | wc -c); printf \'\\173"type":"result","result":"ANSWER-len-%s"\\175\\n\' "$L"';
  return setup(configOverrides, ({ workRoot }) => ({
    'test-chat': {
      exec: { argv: ['bash', '-c', echoResult], prompt: 'stdin' },
      session_ref: { source: 'cwd-implicit' },
      workdir_root: workRoot,
      caps: { memory_max: '64M', runtime_max: '1h' },
    },
  }));
}

// Drive ticks (each with a slightly-future `now` so +1s re-dispatch rows are due
// immediately) until pred(allActions) or maxTicks. Returns every action seen.
async function tickUntil(ctx, pred, maxTicks = 40, stepMs = 250) {
  const all = [];
  for (let i = 0; i < maxTicks; i++) {
    const res = await ctx.ticker.tick(new Date(Date.now() + 2000));
    all.push(...res.actions);
    if (pred(all)) return all;
    await sleep(stepMs);
  }
  throw new Error(`tickUntil: predicate not satisfied after ${maxTicks} ticks; actions=${JSON.stringify(all.filter(a => a.action))}`);
}

function findAll(actions, name) {
  return actions.filter((a) => a.action === name);
}

function promptFileOf(ctx, execId) {
  const row = ctx.store.getExecution(execId);
  if (!row || !row.session_id) throw new Error(`no session_id on exec ${execId}`);
  return fs.readFileSync(path.join(ctx.dataRoot, 'prompts', `${row.session_id}.txt`), 'utf8');
}

function assertIncludes(label, haystack, needle) {
  if (!haystack.includes(needle)) {
    throw new Error(`${label}: expected to find ${JSON.stringify(needle)} in ${JSON.stringify(haystack.slice(0, 400))}…`);
  }
}

function assertExcludes(label, haystack, needle) {
  if (haystack.includes(needle)) {
    throw new Error(`${label}: expected NOT to find ${JSON.stringify(needle)}`);
  }
}

// Run one full turn to its resolved end: tick until a new `end` (or the named
// advance action) appears beyond `priorCount`.
async function runUntilAdvance(ctx, actionName, priorCount) {
  return tickUntil(ctx, (all) => findAll(all, actionName).length > priorCount ? true : false);
}

capture('probe-multiturn', async (lines) => {
  // ── Scenario A + B: clean turn-end, wake-on-message, 3-turn history ──────────
  let ctx = makeCtx({ history_compact_chars: 100000 });
  try {
    registerLaunchAgentJob(ctx, 'chat-agent');
    const Q1 = 'Q1-first-question';
    enqueueLaunchAgent(ctx, { jobId: 'chat-agent', profile: 'test-chat', prompt: Q1, runAt: new Date() });

    // Turn 1: spawn → clean exit → sweep records done → advance ends the slot.
    let acts = await tickUntil(ctx, (all) => findAll(all, 'end').length >= 1);
    const spawn1 = findAll(acts, 'spawn')[0];
    if (!spawn1) throw new Error('turn 1: no spawn action');
    const sweep1 = findAll(acts, 'clean-exit-sweep')[0];
    if (!sweep1) throw new Error('turn 1: no clean-exit-sweep action (mislabel fix broken)');
    const exec1 = ctx.store.getExecution(spawn1.execId);
    if (exec1.status !== 'done' || exec1.exit_code !== 0) {
      throw new Error(`turn 1: exec status=${exec1.status} exit_code=${exec1.exit_code}, want done/0`);
    }
    const comp1 = ctx.store.getMessage(sweep1.completionMsgId);
    const A1 = `ANSWER-len-${Q1.length}`;
    if (comp1.corpus !== A1 || comp1.status !== 'done') {
      throw new Error(`turn 1: completion corpus=${JSON.stringify(comp1.corpus)} status=${comp1.status}, want ${A1}/done`);
    }
    if (spawn1.thread !== exec1.thread) throw new Error('turn 1: spawn action carries no chain thread');
    lines.push(`A PASS: clean exit swept done, corpus=${A1}, exec done/0, spawn action thread=${spawn1.thread}`);

    // Quiet thread: several ticks, NO wake.
    acts = [];
    for (let i = 0; i < 3; i++) acts.push(...(await ctx.ticker.tick(new Date(Date.now() + 2000))).actions);
    if (findAll(acts, 'wake-redispatch').length > 0) throw new Error('quiet thread woke — wake gate broken');
    // Ticker-sender row on the thread: still NO wake.
    ctx.store.recordMessage({ type: 'note', sender: 'ticker', thread: exec1.thread, corpus: 'ticker-noise', createdAt: new Date() });
    for (let i = 0; i < 2; i++) acts.push(...(await ctx.ticker.tick(new Date(Date.now() + 2000))).actions);
    if (findAll(acts, 'wake-redispatch').length > 0) throw new Error('ticker-sender row woke the chain — sender filter broken');
    lines.push('B PASS (negatives): quiet thread and ticker rows never wake the chain');

    // Turn 2: a sender reply wakes the chain; the new turn's prompt carries the history.
    const R1 = 'REPLY-1-now-add-nine';
    ctx.store.recordMessage({ type: 'note', sender: 'probe-bridge', thread: exec1.thread, corpus: R1, createdAt: new Date() });
    acts = await tickUntil(ctx, (all) => findAll(all, 'end').length >= 1 && findAll(all, 'spawn').length >= 1);
    const wake1 = findAll(acts, 'wake-redispatch')[0];
    if (!wake1) throw new Error('turn 2: no wake-redispatch action');
    const spawn2 = findAll(acts, 'spawn')[0];
    const exec2 = ctx.store.getExecution(spawn2.execId);
    if (exec2.parent_exec_id !== exec1.exec_id) throw new Error(`turn 2: parent ${exec2.parent_exec_id} != ${exec1.exec_id}`);
    if (exec2.thread !== exec1.thread) throw new Error(`turn 2: thread ${exec2.thread} != ${exec1.thread} (chain-stable violated)`);
    const prompt2 = promptFileOf(ctx, exec2.exec_id);
    assertIncludes('turn 2 prompt', prompt2, `[owner] ${Q1}`);
    assertIncludes('turn 2 prompt', prompt2, `[assistant] ${A1}`);
    assertIncludes('turn 2 prompt', prompt2, `[owner] ${R1}`);
    assertExcludes('turn 2 prompt', prompt2, 'ticker-noise');
    const A2 = `ANSWER-len-${prompt2.length}`;
    lines.push(`B PASS (turn 2): woke on sender reply; prompt composed (Q1+A1+R1, no ticker rows); linear chain exec${exec1.exec_id}→exec${exec2.exec_id}`);

    // Turn 3: history accumulates.
    const R2 = 'REPLY-2-and-double-it';
    ctx.store.recordMessage({ type: 'note', sender: 'probe-bridge', thread: exec1.thread, corpus: R2, createdAt: new Date() });
    acts = await tickUntil(ctx, (all) => findAll(all, 'end').length >= 1 && findAll(all, 'spawn').length >= 1);
    const spawn3 = findAll(acts, 'spawn')[0];
    const exec3 = ctx.store.getExecution(spawn3.execId);
    if (exec3.parent_exec_id !== exec2.exec_id) throw new Error(`turn 3: parent ${exec3.parent_exec_id} != ${exec2.exec_id}`);
    const prompt3 = promptFileOf(ctx, exec3.exec_id);
    assertIncludes('turn 3 prompt', prompt3, `[owner] ${Q1}`);
    assertIncludes('turn 3 prompt', prompt3, `[assistant] ${A1}`);
    assertIncludes('turn 3 prompt', prompt3, `[owner] ${R1}`);
    assertIncludes('turn 3 prompt', prompt3, `[assistant] ${A2}`);
    assertIncludes('turn 3 prompt', prompt3, `[owner] ${R2}`);
    lines.push('B PASS (turn 3): history accumulates across 3 turns');
  } finally {
    teardown(ctx);
  }

  // ── Scenario C: compaction turn + summary splice ─────────────────────────────
  ctx = makeCtx({ history_compact_chars: 150 });
  try {
    registerLaunchAgentJob(ctx, 'chat-agent');
    const Q1 = 'Q1-compact-scenario-question-with-some-length-to-it';
    enqueueLaunchAgent(ctx, { jobId: 'chat-agent', profile: 'test-chat', prompt: Q1, runAt: new Date() });
    let acts = await tickUntil(ctx, (all) => findAll(all, 'end').length >= 1);
    const exec1 = ctx.store.getExecution(findAll(acts, 'spawn')[0].execId);

    const R1 = 'REPLY-1-long-enough-to-push-the-transcript-over-the-tiny-compaction-bound-for-sure-really';
    ctx.store.recordMessage({ type: 'note', sender: 'probe-bridge', thread: exec1.thread, corpus: R1, createdAt: new Date() });

    // The wake fires a COMPACTION turn, whose completion re-dispatches the answering turn.
    acts = await tickUntil(ctx, (all) => findAll(all, 'compaction-recycle').length >= 1);
    const compactSpawn = findAll(acts, 'spawn').find((a) => a.compact === true);
    if (!compactSpawn) throw new Error('compaction: no compact:true spawn action');
    const compactExec = ctx.store.getExecution(compactSpawn.execId);
    const compactPrompt = promptFileOf(ctx, compactExec.exec_id);
    assertIncludes('compaction prompt', compactPrompt, 'Compact the following conversation');
    assertIncludes('compaction prompt', compactPrompt, `[owner] ${Q1}`);
    assertExcludes('compaction prompt', compactPrompt, `[owner] ${R1}`); // pending reply stays OUT of the summary
    const SUMMARY = `ANSWER-len-${compactPrompt.length}`;

    // The answering turn spawns with the summary spliced in place of the old
    // history — and the pending reply verbatim after it.
    acts = await tickUntil(ctx, (all) => findAll(all, 'end').length >= 1 && findAll(all, 'spawn').some((a) => !a.compact));
    const answerSpawn = findAll(acts, 'spawn').find((a) => !a.compact);
    const answerExec = ctx.store.getExecution(answerSpawn.execId);
    if (answerExec.parent_exec_id !== compactExec.exec_id) {
      throw new Error(`compaction: answering parent ${answerExec.parent_exec_id} != compaction exec ${compactExec.exec_id} (chain not linear)`);
    }
    const answerPrompt = promptFileOf(ctx, answerExec.exec_id);
    assertIncludes('answering prompt', answerPrompt, `[summary of earlier conversation] ${SUMMARY}`);
    assertIncludes('answering prompt', answerPrompt, `[owner] ${R1}`); // the pending reply, verbatim
    assertExcludes('answering prompt', answerPrompt, `[owner] ${Q1}`);
    assertExcludes('answering prompt', answerPrompt, 'Compact the following conversation');
    lines.push(`C PASS: over-bound wake became a compaction turn; answering turn spliced at the summary; chain linear exec${exec1.exec_id}→exec${compactExec.exec_id}→exec${answerExec.exec_id}`);
  } finally {
    teardown(ctx);
  }

  // ── Scenario D: budget — sender wakes free, automatic recycles gated ─────────
  ctx = makeCtx({ slot_max_repeats: 2, history_compact_chars: 100000 });
  try {
    registerLaunchAgentJob(ctx, 'chat-agent');
    enqueueLaunchAgent(ctx, { jobId: 'chat-agent', profile: 'test-chat', prompt: 'Q1-budget', runAt: new Date() });
    let acts = await tickUntil(ctx, (all) => findAll(all, 'end').length >= 1);
    const exec1 = ctx.store.getExecution(findAll(acts, 'spawn')[0].execId);

    // Three sender-message wakes with slot_max_repeats=2: ALL must fire (the
    // chain-total semantics would refuse the third).
    for (let i = 1; i <= 3; i++) {
      ctx.store.recordMessage({ type: 'note', sender: 'probe-bridge', thread: exec1.thread, corpus: `BUDGET-REPLY-${i}`, createdAt: new Date() });
      acts = await tickUntil(ctx, (all) => findAll(all, 'end').length >= 1 && findAll(all, 'wake-redispatch').length >= 1);
      if (acts.some((a) => String(a.action || '').includes('budget-exhausted'))) {
        throw new Error(`budget: sender-message wake ${i} hit a budget gate — ruling broken`);
      }
    }
    lines.push('D PASS: 3 sender-message wakes fired under slot_max_repeats=2 (sender turns never consume the automatic budget)');
  } finally {
    teardown(ctx);
  }

  // ── Scenario D2: the budget still gates AUTOMATIC recycles (compaction) ──────
  ctx = makeCtx({ slot_max_repeats: 1, history_compact_chars: 120 });
  try {
    registerLaunchAgentJob(ctx, 'chat-agent');
    enqueueLaunchAgent(ctx, { jobId: 'chat-agent', profile: 'test-chat', prompt: 'Q1-budget-compact-long-enough-first-question', runAt: new Date() });
    let acts = await tickUntil(ctx, (all) => findAll(all, 'end').length >= 1);
    const exec1 = ctx.store.getExecution(findAll(acts, 'spawn')[0].execId);

    ctx.store.recordMessage({ type: 'note', sender: 'probe-bridge', thread: exec1.thread, corpus: 'BUDGET-COMPACT-REPLY-also-long-enough-to-cross', createdAt: new Date() });
    acts = await tickUntil(ctx, (all) => findAll(all, 'compaction-budget-exhausted').length >= 1);
    if (!findAll(acts, 'spawn').some((a) => a.compact)) throw new Error('budget-compact: no compaction turn fired');
    lines.push('D2 PASS: the compaction (automatic) recycle hit the budget gate at slot_max_repeats=1');
  } finally {
    teardown(ctx);
  }
});
