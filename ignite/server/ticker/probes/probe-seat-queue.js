'use strict';

// THE SEAT-BUSY GATE — the ticker half of `on_seat_busy: 'queue'`.
//
// The store's idempotent door (Q9) used to be the only thing keeping two enqueues of one seat from
// racing, and it did it by DROPPING the second. A caller that must not lose its payload — a chat
// message typed while the seat is mid-turn — now opts out and gets a real row, which means several
// pending rows can address one seat. This gate is what makes that safe: at dispatch, a row whose
// seat is held by anyone else DEFERS, untouched and still due, and fires when the holder goes
// terminal. Past `seat_queue_max_age_s` it is REMOVED with an owner note instead — an hour-old
// chat message must never fire as if it were fresh.
//
// The spawn manager is a stub (the gate's inputs are store state, not process state), but every
// row, defer and removal below is the REAL dispatch path against the REAL store.

const { setup, teardown, registerLaunchAgentJob, capture } = require('./lib');
const { createTicker } = require('../ticker');

const SEAT_ARGS = (workdir) => JSON.stringify({ workdir });

function stubManager(ctx) {
  return {
    config: ctx.mgr.config,
    spawn: async () => {},
    status: async (execId) => ({ execId, live: true, exitCode: null, cpuNsec: null, carrierInfo: { carrier: 'systemd', active: true, cpuNsec: null } }),
    kill: async () => {},
  };
}

function makeTicker(ctx, config = {}) {
  return createTicker({
    heartStore: ctx.store,
    spawnManager: stubManager(ctx),
    // The stall ladder is parked out of range: this probe measures dispatch, and a stall or a
    // hung kill mid-scenario would free the seat for reasons the checks do not control.
    config: {
      tick_interval_ms: 10000, stall_warn_ticks: 10000, stall_halt_ticks: 10000,
      stall_kill_ticks: 0, max_live_agent_sessions: 4, slot_max_repeats: 10, ...config,
    },
    feedPath: ctx.feedPath,
    logPath: ctx.logPath,
  });
}

const iso = (d) => d.toISOString().replace(/\.\d{3}Z$/, 'Z');

function enqueue(ctx, workdir, { onSeatBusy, runAt = new Date(), triggerKind = 'scheduled', intervalSeconds } = {}) {
  return ctx.store.enqueue({
    jobId: 'launch-agent', args: SEAT_ARGS(workdir), sessionMode: 'headless',
    triggerKind, runAt: iso(runAt), intervalSeconds,
    enqueuedBy: 'probe', onSeatBusy,
  });
}

const actionsOf = (r, action) => r.actions.filter((a) => a.action === action);

async function run(lines) {
  let failures = 0;
  const check = (name, ok, detail) => {
    if (!ok) failures += 1;
    lines.push(`  ${name.padEnd(40)} ${ok ? 'PASS' : 'FAIL'}  ${detail}`);
  };

  // ── A · DEFER WHILE HELD, THEN LAUNCH ──────────────────────────────────────────────────────
  {
    const ctx = setup();
    try {
      registerLaunchAgentJob(ctx);
      const ticker = makeTicker(ctx);
      const seat = ctx.seatDir;

      const holder = enqueue(ctx, seat);
      const r1 = await ticker.tick(new Date());
      const held = ctx.store.dump().jobs_log[0];
      check('holder-fires-normally',
        actionsOf(r1, 'spawn').length === 1 && held && held.status === 'launching',
        `spawn actions=${actionsOf(r1, 'spawn').length} holder queue_id=${holder.queue_id} exec status=${held && held.status}`);

      const queued = enqueue(ctx, seat, { onSeatBusy: 'queue' });
      const r2 = await ticker.tick(new Date());
      const defers = r2.actions.filter((a) => a.action === 'defer' && a.reason === 'seat-busy');
      check('held-seat-defers-the-second-row',
        defers.length === 1 && defers[0].queueId === queued.queue_id
          && ctx.store.getQueueRow(queued.queue_id) !== null
          && ctx.store.dump().jobs_log.length === 1,
        `defers=${JSON.stringify(defers)} row still pending=${ctx.store.getQueueRow(queued.queue_id) !== null} jobs_log rows=${ctx.store.dump().jobs_log.length}`);

      // The holder reaches a terminal status — the ONE thing the gate is waiting on.
      ctx.store.updateExecutionStatus(held.exec_id, { status: 'done' });
      const r3 = await ticker.tick(new Date());
      const rows = ctx.store.dump().jobs_log;
      check('terminal-holder-releases-the-queued-row',
        actionsOf(r3, 'spawn').some((a) => a.queueId === queued.queue_id)
          && ctx.store.getQueueRow(queued.queue_id) === null && rows.length === 2,
        `spawns=${JSON.stringify(actionsOf(r3, 'spawn').map((a) => a.queueId))} jobs_log rows=${rows.length}`);
    } finally {
      teardown(ctx);
    }
  }

  // ── B · THE AGE BOUND · removed, never silently ─────────────────────────────────────────────
  {
    const ctx = setup();
    try {
      registerLaunchAgentJob(ctx);
      const ticker = makeTicker(ctx, { seat_queue_max_age_s: 3600 });
      const seat = ctx.seatDir;

      enqueue(ctx, seat);
      await ticker.tick(new Date());

      // Two hours past due. Nothing else about it differs from scenario A's row.
      const stale = enqueue(ctx, seat, { onSeatBusy: 'queue', runAt: new Date(Date.now() - 7200 * 1000) });
      const r = await ticker.tick(new Date());
      const expired = actionsOf(r, 'seat-queue-expired');
      const notes = ctx.store.dump().messages
        .filter((m) => m.type === 'note' && m.sender === 'ticker' && m.corpus.includes('queued request DROPPED'));
      check('stale-queued-row-is-removed',
        expired.length === 1 && expired[0].queueId === stale.queue_id
          && ctx.store.getQueueRow(stale.queue_id) === null
          && ctx.store.dump().jobs_log.length === 1,
        `expired=${JSON.stringify(expired)} row gone=${ctx.store.getQueueRow(stale.queue_id) === null} jobs_log rows=${ctx.store.dump().jobs_log.length}`);
      check('removal-tells-the-owner',
        notes.length === 1 && notes[0].corpus.includes('It was not run.'),
        notes.length ? notes[0].corpus : 'NO drop note on owner-feed — a silent removal is the failure this check exists for');

      // NEGATIVE CONTROL · a FRESH row in the same held state is deferred, not removed. Without
      // it, "removed" would be indistinguishable from "the gate removes everything it defers".
      const fresh = enqueue(ctx, seat, { onSeatBusy: 'queue' });
      const r2 = await ticker.tick(new Date());
      check('fresh-queued-row-is-NOT-removed',
        actionsOf(r2, 'seat-queue-expired').length === 0
          && r2.actions.some((a) => a.action === 'defer' && a.reason === 'seat-busy' && a.queueId === fresh.queue_id)
          && ctx.store.getQueueRow(fresh.queue_id) !== null,
        `expired=${actionsOf(r2, 'seat-queue-expired').length} still pending=${ctx.store.getQueueRow(fresh.queue_id) !== null}`);

      // NEGATIVE CONTROL · a RECURRING row is NEVER dropped, however long past due. Its
      // `enqueued_at` is the day it was created and `fireQueueRow` keeps moving `run_at`, so an
      // age bound reading the wrong clock — or reading the right clock without this exclusion —
      // would delete a live periodic job on its first seat-busy defer. Removal is permanent;
      // there is no next fire to recover on.
      const periodic = enqueue(ctx, seat, {
        onSeatBusy: 'queue', triggerKind: 'periodic', intervalSeconds: 300,
        runAt: new Date(Date.now() - 86400 * 1000),
      });
      const r3 = await ticker.tick(new Date());
      check('recurring-row-is-NEVER-dropped',
        actionsOf(r3, 'seat-queue-expired').length === 0
          && ctx.store.getQueueRow(periodic.queue_id) !== null,
        `a day-past-due periodic row: expired=${actionsOf(r3, 'seat-queue-expired').length} still pending=${ctx.store.getQueueRow(periodic.queue_id) !== null}`);
    } finally {
      teardown(ctx);
    }
  }

  lines.push(`FAILURES: ${failures}`);
  if (failures) throw new Error(`${failures} check(s) failed`);
}

capture('probe-seat-queue', run);
