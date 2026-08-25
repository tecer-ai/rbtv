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
const { seatKeyOf, SEAT_SHARD_ARG } = require('../../../state-store/heart/heart-store');

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
    config: {
      tick_interval_ms: 10000, max_live_agent_sessions: 4, slot_max_repeats: 10, ...config,
    },
    feedPath: ctx.feedPath,
    logPath: ctx.logPath,
  });
}

const iso = (d) => d.toISOString().replace(/\.\d{3}Z$/, 'Z');

function enqueue(ctx, workdir, {
  onSeatBusy, runAt = new Date(), triggerKind = 'scheduled', intervalSeconds, seatShard, reason,
} = {}) {
  return ctx.store.enqueue({
    jobId: 'launch-agent', args: SEAT_ARGS(workdir), sessionMode: 'headless',
    triggerKind, runAt: iso(runAt), intervalSeconds,
    enqueuedBy: 'probe', onSeatBusy, seatShard, reason,
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

      // D52/D66 · FOUR ROWS, ONE SEAT, IDENTICAL ARGS — each `reason` below is what a real caller
      // supplies (or a distinct prompt gives it implicitly): the admission brake merges a
      // reasonless caller's budget by design (heart-store.js `BRAKE_REASON_FLOOR`), and this
      // fixture's four rows are deliberately byte-identical in `args`, which the brake would
      // otherwise read as one seat asking the same no-progress question four times. Distinct
      // `reason` values keep this scenario testing the SEAT-BUSY GATE, not the brake.
      enqueue(ctx, seat, { reason: 'holder' });
      await ticker.tick(new Date());

      // Two hours past due. Nothing else about it differs from scenario A's row.
      const stale = enqueue(ctx, seat, { onSeatBusy: 'queue', runAt: new Date(Date.now() - 7200 * 1000), reason: 'stale' });
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
      const fresh = enqueue(ctx, seat, { onSeatBusy: 'queue', reason: 'fresh' });
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
        runAt: new Date(Date.now() - 86400 * 1000), reason: 'periodic',
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

  // ── C · THE SEAT SHARD · two conversations at ONE seat run side by side ─────────────────────
  //
  // What B guarantees is that a busy seat loses nothing. It does NOT make the seat concurrent, and
  // on the master/DM surface the seat is EVERY conversation the owner has: `forward-path.js`
  // #workdirFor falls through to one configured workdir for every DM thread, so thread B's question
  // waited behind thread A's twenty-minute turn. The shard splits the gate's key per conversation.
  //
  // ⚠ THE PAIR IS THE POINT — neither half is evidence alone. "Two rows fired" proves nothing if
  // the gate is simply toothless, and "the second row deferred" proves nothing if the gate defers
  // everything. So the SAME scenario runs twice: sharded (both fire) and shardless (the second
  // defers), and the shardless run IS the red arm — it is what this code does with the sharding
  // mutated away, driven through the real store and the real dispatch path rather than simulated.
  {
    const ctx = setup();
    try {
      registerLaunchAgentJob(ctx);
      const ticker = makeTicker(ctx);
      const seat = ctx.seatDir;
      const job = ctx.store.getJob('launch-agent');

      // C0 · the key itself. Unit-level and deliberately spelled with LITERALS on both sides: a
      // check whose expectation reads the value under test would move with any change to it.
      const bare = seatKeyOf(job, { workdir: '/seat/x' });
      const shardA = seatKeyOf(job, { workdir: '/seat/x', [SEAT_SHARD_ARG]: 'D_IM:1' });
      const shardA2 = seatKeyOf(job, { workdir: '/seat/x', [SEAT_SHARD_ARG]: 'D_IM:1' });
      const shardB = seatKeyOf(job, { workdir: '/seat/x', [SEAT_SHARD_ARG]: 'D_IM:2' });
      check('unsharded-key-is-byte-identical-to-before',
        bare === 'workdir:/seat/x',
        `seatKeyOf({workdir}) = ${bare} — every producer that sends no shard must key exactly as it did`);
      check('same-shard-same-key-different-shard-different',
        shardA === 'workdir:/seat/x#D_IM:1' && shardA === shardA2 && shardB === 'workdir:/seat/x#D_IM:2',
        `A=${shardA} A2=${shardA2} B=${shardB}`);

      // C0b · THE STORE IS THE SHARD'S SOLE MINTER. Reading the key out of `args` is safe only
      // because no CALLER can put it there: `__seat_shard` is declared by no job's `args_schema`,
      // so `validateArgs`'s unknown-argument arm refuses it. Without this, any sender able to
      // enqueue could hand itself a private seat key and walk past the busy gate.
      let forged = null;
      try {
        ctx.store.enqueue({
          jobId: 'launch-agent', args: JSON.stringify({ workdir: seat, [SEAT_SHARD_ARG]: 'forged' }),
          sessionMode: 'headless', triggerKind: 'scheduled', runAt: iso(new Date()), enqueuedBy: 'probe',
        });
      } catch (err) { forged = err; }
      check('a-caller-CANNOT-put-the-shard-in-args-itself',
        forged !== null && /unknown argument/.test(forged.message) && forged.message.includes(SEAT_SHARD_ARG),
        forged ? forged.message : 'ENQUEUED — a caller-supplied shard reached the row, so the key is caller-controlled');

      // C1 · TWO DIFFERENT CONVERSATIONS, ONE SEAT — neither defers behind the other.
      const a = enqueue(ctx, seat, { onSeatBusy: 'queue', seatShard: 'D_IM:1786501607' });
      const b = enqueue(ctx, seat, { onSeatBusy: 'queue', seatShard: 'D_IM:1786509999' });
      const r1 = await ticker.tick(new Date());
      const spawned = actionsOf(r1, 'spawn').map((x) => x.queueId).sort();
      const seatBusy = r1.actions.filter((x) => x.action === 'defer' && x.reason === 'seat-busy');
      check('two-shards-of-one-seat-BOTH-fire',
        spawned.length === 2 && spawned.includes(a.queue_id) && spawned.includes(b.queue_id)
          && seatBusy.length === 0,
        `spawned=${JSON.stringify(spawned)} seat-busy defers=${JSON.stringify(seatBusy)}`);

      // C2 · ONE conversation still serializes. The second message of thread A carries the SAME
      // shard, so it is the held case — this is the ordering the shard must NOT break.
      const a2 = enqueue(ctx, seat, { onSeatBusy: 'queue', seatShard: 'D_IM:1786501607' });
      const r2 = await ticker.tick(new Date());
      const held = r2.actions.filter((x) => x.action === 'defer' && x.reason === 'seat-busy' && x.queueId === a2.queue_id);
      check('same-shard-second-message-DEFERS',
        held.length === 1 && held[0].seatKey === `workdir:${seat}#D_IM:1786501607`
          && ctx.store.getQueueRow(a2.queue_id) !== null
          && actionsOf(r2, 'spawn').length === 0,
        `defers=${JSON.stringify(held)} spawns this tick=${actionsOf(r2, 'spawn').length}`);
    } finally {
      teardown(ctx);
    }
  }

  // ── C-RED · THE SAME TWO CONVERSATIONS, SHARDING MUTATED AWAY ───────────────────────────────
  //
  // Byte-for-byte scenario C1 with `seatShard` dropped — which is precisely the state of this code
  // before the shard, and the state it returns to if `seatKeyOf`'s suffix is deleted. The second
  // conversation MUST defer here. If it does not, C1's green means the gate stopped working, not
  // that the shard started working.
  {
    const ctx = setup();
    try {
      registerLaunchAgentJob(ctx);
      const ticker = makeTicker(ctx);
      const seat = ctx.seatDir;

      const a = enqueue(ctx, seat, { onSeatBusy: 'queue' });
      const b = enqueue(ctx, seat, { onSeatBusy: 'queue' });
      const r = await ticker.tick(new Date());
      const spawned = actionsOf(r, 'spawn').map((x) => x.queueId);
      const defers = r.actions.filter((x) => x.action === 'defer' && x.reason === 'seat-busy');
      check('RED-ARM-shardless-second-conversation-DEFERS',
        spawned.length === 1 && spawned[0] === a.queue_id
          && defers.length === 1 && defers[0].queueId === b.queue_id
          && defers[0].seatKey === `workdir:${seat}`,
        `spawned=${JSON.stringify(spawned)} defers=${JSON.stringify(defers)} — this is C1 with the sharding removed`);
    } finally {
      teardown(ctx);
    }
  }

  lines.push(`FAILURES: ${failures}`);
  if (failures) throw new Error(`${failures} check(s) failed`);
}

capture('probe-seat-queue', run);
