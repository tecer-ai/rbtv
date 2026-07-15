'use strict';

const {
  setup,
  teardown,
  sleep,
  registerLaunchAgentJob,
  enqueueLaunchAgent,
  capture,
} = require('./lib');

function actionSummary(actions) {
  return JSON.stringify(
    actions.map((a) => ({
      phase: a.phase,
      action: a.action,
      execId: a.execId,
      queueId: a.queueId,
      reason: a.reason,
      watermark: a.watermark,
    }))
  );
}

async function run(lines) {
  const ctx = setup();
  try {
    registerLaunchAgentJob(ctx);

    // ---------- Part A: blocked slot wakes on a new thread message ----------
    const q1 = enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt: new Date() });
    const t1 = await ctx.ticker.tick();
    lines.push(`tick-1 actions: ${actionSummary(t1.actions)}`);

    const exec1 = ctx.store.dump().jobs_log.find((r) => r.queue_id === q1.queue_id);
    if (!exec1) throw new Error('exec1 not found after launch');
    lines.push(`exec1: exec_id=${exec1.exec_id} thread=${exec1.thread} status=${exec1.status}`);

    const blockedMsg = ctx.store.recordMessage({
      type: 'completion',
      sender: 'probe',
      thread: exec1.thread,
      corpus: 'blocked',
      status: 'blocked',
      createdAt: new Date(),
    });
    lines.push(`blocked completion msg_id=${blockedMsg.msg_id}`);

    const t2 = await ctx.ticker.tick();
    lines.push(`tick-2 actions: ${actionSummary(t2.actions)}`);
    const exec1AfterBlock = ctx.store.getExecution(exec1.exec_id);
    if (exec1AfterBlock.status !== 'blocked') throw new Error(`exec1 status ${exec1AfterBlock.status}, expected blocked`);
    if (!exec1AfterBlock.completion_msg_id) throw new Error('exec1 completion_msg_id not set');
    lines.push(`exec1 after block: status=${exec1AfterBlock.status} completion_msg_id=${exec1AfterBlock.completion_msg_id}`);

    // No re-dispatch yet — no message after the block.
    const redispatchBefore = t2.actions.find(
      (a) => a.phase === 'advance' && a.action === 'blocked-redispatch' && a.execId === exec1.exec_id
    );
    if (redispatchBefore) throw new Error('spurious blocked-redispatch before new message');

    // New message lands on the thread AFTER the block.
    const newMsg = ctx.store.recordMessage({
      type: 'answer',
      sender: 'owner',
      thread: exec1.thread,
      corpus: 'unblock please',
      createdAt: new Date(),
    });
    lines.push(`new answer msg_id=${newMsg.msg_id}`);

    const t3 = await ctx.ticker.tick();
    lines.push(`tick-3 actions: ${actionSummary(t3.actions)}`);
    const redispatchAction = t3.actions.find(
      (a) => a.phase === 'advance' && a.action === 'blocked-redispatch' && a.execId === exec1.exec_id
    );
    if (!redispatchAction) throw new Error('blocked-redispatch action not found after new message');
    if (redispatchAction.watermark !== exec1AfterBlock.completion_msg_id) {
      throw new Error(`watermark mismatch: ${redispatchAction.watermark} != ${exec1AfterBlock.completion_msg_id}`);
    }

    const queueRow = ctx.store.listQueue().find((r) => {
      const args = JSON.parse(r.args);
      return args.__rbtv_chain_parent_exec_id === exec1.exec_id;
    });
    if (!queueRow) throw new Error('re-dispatch queue row not found');
    lines.push(`re-dispatch queue row: queue_id=${queueRow.queue_id} parent_exec_id marker=${exec1.exec_id}`);

    // Wait for the re-dispatch queue row to become due, then fire it.
    await sleep(1100);
    const t4 = await ctx.ticker.tick();
    lines.push(`tick-4 actions: ${actionSummary(t4.actions)}`);

    const exec2 = ctx.store.dump().jobs_log.find((r) => r.parent_exec_id === exec1.exec_id);
    if (!exec2) throw new Error('re-dispatched execution (exec2) not found');
    if (exec2.thread !== exec1.thread) {
      throw new Error(`exec2 thread mismatch: ${exec2.thread} != ${exec1.thread}`);
    }
    lines.push(`exec2: exec_id=${exec2.exec_id} parent_exec_id=${exec2.parent_exec_id} thread=${exec2.thread} status=${exec2.status}`);

    // ---------- Part B: same slot with no new message never re-enqueues ----------
    const q2 = enqueueLaunchAgent(ctx, { profile: 'test-sleep', runAt: new Date() });
    const t5 = await ctx.ticker.tick();
    const exec3 = ctx.store.dump().jobs_log.find((r) => r.queue_id === q2.queue_id);
    if (!exec3) throw new Error('exec3 not found after launch');
    lines.push(`exec3: exec_id=${exec3.exec_id} thread=${exec3.thread}`);

    ctx.store.recordMessage({
      type: 'completion',
      sender: 'probe',
      thread: exec3.thread,
      corpus: 'blocked',
      status: 'blocked',
      createdAt: new Date(),
    });

    const t6 = await ctx.ticker.tick();
    lines.push(`tick-6 (exec3 blocked) actions: ${actionSummary(t6.actions)}`);

    const noMsgActions = [];
    for (let i = 0; i < 3; i++) {
      const t = await ctx.ticker.tick();
      noMsgActions.push(...t.actions);
      lines.push(`no-new-msg-tick-${i + 1} actions: ${actionSummary(t.actions)}`);
    }
    const spurious = noMsgActions.filter(
      (a) => a.phase === 'advance' && a.action === 'blocked-redispatch' && a.execId === exec3.exec_id
    );
    if (spurious.length > 0) {
      throw new Error(`spurious blocked-redispatch for exec3 across quiet ticks: ${spurious.length}`);
    }

    // ---------- Cleanup accounting ----------
    const live = ctx.store
      .listExecutionsByStatus('running')
      .concat(ctx.store.listExecutionsByStatus('launching'));
    lines.push(`pre-teardown live executions: ${live.length}`);
    for (const r of live) {
      lines.push(`  live exec_id=${r.exec_id} session_id=${r.session_id} status=${r.status}`);
    }
  } finally {
    teardown(ctx);
  }
}

capture('probe-blocked-redispatch', run);
