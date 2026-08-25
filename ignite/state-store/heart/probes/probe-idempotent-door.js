'use strict';

// Task Q9 — THE IDEMPOTENT DOOR (owner-authorized ruling `d-q9-door`, 2026-08-08).
//
// The bar: a second `add-job` for a (run, seat) still HELD mints no second row and returns the
// held operation's queue id. The hazard it closes was measured by the C1 review — a periodically
// fired edge-runner re-enqueues a seat that has not registered itself yet, forever.
//
// ⚠ THE ARM THAT MATTERS IS THE LIVE-TURN ONE, and it is why check 2 FIRES the row first. A
// pending-row-only door would pass check 1 and still be vacuous in production, and the measured
// case that showed it was the edge-runner's: it enqueued `scheduled/at-now`, fireQueueRow DELETES
// such a row at fire, the ticker cadence is 10s and its shipped recipe was `--every 300` — so the
// re-fire almost always arrived when NOTHING was pending and a live turn held the seat. Check 1
// alone would be green on a door that fixes nothing. (That caller is retired; the door is not, and
// any periodic re-enqueuer lands in the same place.)
//
// ⚠ EVERY GREEN HERE CARRIES A RED ARM (check 7). The same scenario as check 2 is replayed
// against a SCRATCH COPY of heart-store.js with the guard cut out, and it MUST mint two rows.
// Without it, checks 1-6 would pass identically against a store that had never been changed —
// a check that cannot fail is not evidence. The mutation is asserted to have actually altered the
// source before it is trusted.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const heartStoreModule = require('../heart-store');
const { openHeartStore, closeHeartStore } = heartStoreModule;
const { createInternalApi } = require('../../../runtime/internal-api/dispatch');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-idempotent-door.out');
const HEART_STORE_SRC = path.join(__dirname, '..', 'heart-store.js');
// The scratch copy MUST live beside the original: heart-store.js requires `./errors`,
// `./warnings`, `./migrations` and reads `schema.sql` off its own __dirname, none of which
// resolve from a tmpdir. Removed in `finally`.
const scratchPath = path.join(__dirname, '..', `heart-store.__q9scratch-${process.pid}.js`);

const lines = [];
let failures = 0;

function out(...parts) { lines.push(parts.join(' ')); }

function check(name, ok, detail) {
  if (!ok) failures += 1;
  out(`  ${name.padEnd(38)} ${ok ? 'PASS' : 'FAIL'}  ${detail}`);
}

const PROFILES = { default: { headed: false } };
const SCHEMA = JSON.stringify({ required: {}, optional: { workdir: 'string' } });

function seatArgs(workdir) {
  return JSON.stringify({ workdir });
}

function freshStore(open, dbPath) {
  const store = open({ dbPath, profiles: PROFILES });
  store.registerJob({
    jobId: 'seat-launch', actionType: 'launch-agent', function: 'spawnLaunchAgent',
    argsSchema: SCHEMA, enabled: 1,
  });
  return store;
}

function enqueueSeat(store, workdir) {
  return store.enqueue({
    jobId: 'seat-launch', args: seatArgs(workdir), sessionMode: 'headless',
    triggerKind: 'scheduled', runAt: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    enqueuedBy: 'probe',
  });
}

// Rows currently pending for one seat — the SECOND instrument. The first is the door's own
// returned id; agreeing counts from two independent reads is what the dual-instrument bar asks
// for, and a count alone never stands as the proof (the ids are compared too).
function pendingFor(store, workdir) {
  return store.listQueue().filter((r) => {
    try { return JSON.parse(r.args).workdir === workdir; } catch { return false; }
  });
}

const SEAT_A = '/ws/.rbtv/goals/g/runs/run-1/seats/alpha';
const SEAT_B = '/ws/.rbtv/goals/g/runs/run-1/seats/beta';

const dbs = [];
function tmpDb(tag) {
  const p = path.join(os.tmpdir(), `heart-probe-q9-${tag}-${Date.now()}-${process.pid}.db`);
  dbs.push(p);
  return p;
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out('=== Q9 · the idempotent door ===');

  // ── 1. pending hold → the REAL existing row id, no second row ───────────────────────────────
  const store = freshStore(openHeartStore, tmpDb('main'));
  const first = enqueueSeat(store, SEAT_A);
  const second = enqueueSeat(store, SEAT_A);
  check('pending-hold-returns-existing-row',
    second.deduped === true && second.because === 'pending-queue-row'
      && second.queue_id === first.queue_id && pendingFor(store, SEAT_A).length === 1,
    `first=${first.queue_id} second=${second.queue_id} because=${second.because} pending=${pendingFor(store, SEAT_A).length}`);

  // ── 2. THE HAZARD ARM · the row FIRES (and is deleted), a live turn holds the seat ──────────
  const fired = store.fireQueueRow({ queueId: first.queue_id, now: new Date(Date.now() + 1000), tick: 1 });
  const queueEmptied = pendingFor(store, SEAT_A).length === 0;
  const third = enqueueSeat(store, SEAT_A);
  check('live-turn-hold-mints-no-row',
    queueEmptied && third.deduped === true && third.because === 'live-turn'
      && pendingFor(store, SEAT_A).length === 0,
    `queue emptied at fire=${queueEmptied} because=${third.because} pending_after=${pendingFor(store, SEAT_A).length}`);
  check('returns-ORIGINATING-queue-id',
    third.queue_id === first.queue_id && third.exec_id === fired.exec_id && third.held_status === 'launching',
    `originating=${third.queue_id} (expected ${first.queue_id}) exec=${third.exec_id} status=${third.held_status}`);

  // ── 3. the marker the ruling requires, on the door's own return ─────────────────────────────
  check('suppression-marker-is-emitted',
    third.seat_key === `workdir:${SEAT_A}` && typeof third.because === 'string' && third.exec_id !== null,
    `seat_key=${third.seat_key}`);

  // ── 4. NEGATIVE CONTROL · a different seat of the same run still enqueues ───────────────────
  const other = enqueueSeat(store, SEAT_B);
  check('different-seat-still-enqueues',
    !other.deduped && typeof other.queue_id === 'number' && pendingFor(store, SEAT_B).length === 1,
    `queue_id=${other.queue_id} deduped=${!!other.deduped}`);

  // ── 5. NEGATIVE CONTROL · a TERMINAL turn releases the seat (crash-retry stays alive) ───────
  store.updateExecutionStatus(fired.exec_id, { status: 'done' });
  const afterTerminal = enqueueSeat(store, SEAT_A);
  check('terminal-turn-releases-the-seat',
    !afterTerminal.deduped && typeof afterTerminal.queue_id === 'number'
      && afterTerminal.queue_id !== first.queue_id && pendingFor(store, SEAT_A).length === 1,
    `new queue_id=${afterTerminal.queue_id} deduped=${!!afterTerminal.deduped}`);

  // ── 6. the OTHER key arm · a catalogue-HOMED job keys on the goal/seat pointer, not args ────
  store.registerJob({
    jobId: 'homed-launch', actionType: 'launch-agent', function: 'spawnLaunchAgent',
    argsSchema: JSON.stringify({ required: {}, optional: {} }),
    enabled: 1, goalName: 'g', seatName: 'gamma',
  });
  const homedArgs = {
    jobId: 'homed-launch', args: JSON.stringify({}), sessionMode: 'headless',
    triggerKind: 'scheduled', runAt: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    enqueuedBy: 'probe',
  };
  const homed1 = store.enqueue(homedArgs);
  const homed2 = store.enqueue(homedArgs);
  check('homed-job-keys-on-the-pointer',
    !homed1.deduped && homed2.deduped === true && homed2.seat_key === 'goal:g/seat:gamma'
      && homed2.queue_id === homed1.queue_id,
    `seat_key=${homed2.seat_key} first=${homed1.queue_id} second=${homed2.queue_id}`);

  // ── 7. THE GATEWAY HANDLER · the audit line, and the contract that keeps the caller green ───
  // Driven through the REAL internal API (`api.dispatch`), not by inspecting dispatch.js: the
  // ruling requires the suppression to be OBSERVABLE, and an un-exercised log line is a claim.
  // The wire's `jobId` matters just as much — the caller this was measured on (the retired
  // edge-runner) treated exit-0-without-a-queue-id as a door malfunction, so a suppression that
  // returned no id would record every periodic pass `failed`. That is the whole reason the ruled
  // return is the ORIGINATING id, and it binds every enqueuer, not just that one.
  const logged = [];
  const api = createInternalApi({
    heartStore: store, spawnManager: null, secret: 'probe-secret',
    logger: (entry) => logged.push(entry),
  });
  const envelope = (payload) => ({
    v: api.ENVELOPE_VERSION, id: 'q9', ts: new Date().toISOString(), auth: 'probe-secret',
    intent: 'enqueue-job', payload, sender: { id: 'probe-sender', kind: 'agent' },
  });
  const SEAT_D = '/ws/.rbtv/goals/g/runs/run-1/seats/delta';
  const wirePayload = {
    job_id: 'seat-launch', args: { workdir: SEAT_D },
    trigger_kind: 'scheduled', run_at: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
  };
  const wire1 = await api.dispatch(envelope(wirePayload));
  const wire2 = await api.dispatch(envelope(wirePayload));
  check('gateway-returns-parseable-originating-id',
    wire1.ok && wire2.ok && wire2.result.deduped === true
      && wire2.result.jobId === wire1.result.jobId && typeof wire2.result.jobId === 'number',
    `first jobId=${wire1.result && wire1.result.jobId} second jobId=${wire2.result && wire2.result.jobId} deduped=${wire2.result && wire2.result.deduped} err1=${JSON.stringify(wire1.error)} err2=${JSON.stringify(wire2.error)}`);
  const marker = logged.find((e) => e.message === 'idempotent-suppress');
  check('gateway-emits-audit-line',
    !!marker && marker.originatingQueueId === wire1.result.jobId && marker.heldBy === 'pending-queue-row'
      && marker.seatKey === `workdir:${SEAT_D}`,
    marker ? `level=${marker.level} heldBy=${marker.heldBy} originatingQueueId=${marker.originatingQueueId}`
      : `NO 'idempotent-suppress' line among ${logged.length} logged entries`);

  // ── 9. `on_seat_busy` · the door's lossiness is now OPT-OUT ─────────────────────────────────
  // The default arm is asserted BYTE-IDENTICAL to the behaviour checks 1-2 measured, and it is
  // asserted by REPLAY rather than by reading the code: an absent field and an explicit 'dedupe'
  // must both land on the same suppression, and 'queue' must mint a real row while the seat is
  // still held by the same holder. The three run against ONE seat in sequence so the HOLDER is
  // identical across them — otherwise 'queue' could pass for the trivial reason that nothing held
  // the seat when it ran.
  const SEAT_E = '/ws/.rbtv/goals/g/runs/run-1/seats/epsilon';
  const eHold = enqueueSeat(store, SEAT_E);                                   // the holder
  const eAbsent = enqueueSeat(store, SEAT_E);                                 // on_seat_busy absent
  const eDedupe = store.enqueue({
    jobId: 'seat-launch', args: seatArgs(SEAT_E), sessionMode: 'headless',
    triggerKind: 'scheduled', runAt: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    enqueuedBy: 'probe', onSeatBusy: 'dedupe',
  });
  check('absent-and-dedupe-are-identical',
    eAbsent.deduped === true && eDedupe.deduped === true
      && eAbsent.queue_id === eHold.queue_id && eDedupe.queue_id === eHold.queue_id
      && pendingFor(store, SEAT_E).length === 1,
    `holder=${eHold.queue_id} absent→${eAbsent.queue_id} dedupe→${eDedupe.queue_id} pending=${pendingFor(store, SEAT_E).length}`);

  const eQueued = store.enqueue({
    jobId: 'seat-launch', args: seatArgs(SEAT_E), sessionMode: 'headless',
    triggerKind: 'scheduled', runAt: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    enqueuedBy: 'probe', onSeatBusy: 'queue',
  });
  check('queue-inserts-while-seat-held',
    !eQueued.deduped && typeof eQueued.queue_id === 'number' && eQueued.queue_id !== eHold.queue_id
      && pendingFor(store, SEAT_E).length === 2,
    `new queue_id=${eQueued.queue_id} (holder ${eHold.queue_id}) pending=${pendingFor(store, SEAT_E).length}`);

  // The seat-busy gate's own predicate, asked exactly as the ticker asks it: excluding a row
  // itself, the OLDER pending row is the holder — which is what serializes the two.
  const holderOfQueued = store.findSeatHolder(`workdir:${SEAT_E}`, { excludeQueueId: eQueued.queue_id });
  const holderOfHold = store.findSeatHolder(`workdir:${SEAT_E}`, { excludeQueueId: eHold.queue_id });
  check('gate-predicate-orders-the-two-rows',
    holderOfQueued && holderOfQueued.queueId === eHold.queue_id
      && holderOfHold && holderOfHold.queueId === eQueued.queue_id,
    `younger row sees holder=${holderOfQueued && holderOfQueued.queueId} (expected ${eHold.queue_id}); older sees ${holderOfHold && holderOfHold.queueId}`);

  // ── 10. THE WIRE · the enum, and its refusal ────────────────────────────────────────────────
  const SEAT_F = '/ws/.rbtv/goals/g/runs/run-1/seats/zeta';
  const wireBase = {
    job_id: 'seat-launch', trigger_kind: 'scheduled',
    run_at: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
  };
  const f1 = await api.dispatch(envelope({ ...wireBase, args: { workdir: SEAT_F } }));
  const f2 = await api.dispatch(envelope({ ...wireBase, args: { workdir: SEAT_F }, on_seat_busy: 'queue' }));
  const fBad = await api.dispatch(envelope({ ...wireBase, args: { workdir: SEAT_F }, on_seat_busy: 'later' }));
  check('wire-carries-on_seat_busy',
    f1.ok && f2.ok && !f2.result.deduped && f2.result.jobId !== f1.result.jobId,
    `first=${f1.result && f1.result.jobId} queued=${f2.result && f2.result.jobId} deduped=${f2.result && f2.result.deduped}`);
  check('wire-refuses-an-unknown-value',
    !fBad.ok && fBad.error && fBad.error.details && fBad.error.details.check === 'on_seat_busy-enum'
      && pendingFor(store, SEAT_F).length === 2,
    `ok=${fBad.ok} error=${JSON.stringify(fBad.error)} pending=${pendingFor(store, SEAT_F).length}`);

  closeHeartStore();

  // ── 8. RED ARM · the same live-turn scenario against a store with the guard CUT OUT ─────────
  const original = fs.readFileSync(HEART_STORE_SRC, 'utf8');
  // The anchor is the FIRST line of the door block — which since `on_seat_busy` is the enum read,
  // not the `seatKey` line. Cutting from here removes the whole door (enum validation included),
  // which is exactly what the red arm needs: the scenario below passes no `onSeatBusy`.
  const GUARD_START = "    const onSeatBusy = req.onSeatBusy === undefined";
  const GUARD_END = '    const enqueuedAt = req.enqueuedAt || isoNow();';
  const startIdx = original.indexOf(GUARD_START);
  const endIdx = original.indexOf(GUARD_END, startIdx);
  const mutated = startIdx !== -1 && endIdx !== -1
    ? original.slice(0, startIdx) + original.slice(endIdx)
    : null;
  // A mutation that did not mutate would make this arm pass for the wrong reason.
  check('red-arm-mutation-actually-applied',
    mutated !== null && mutated !== original && !mutated.includes(GUARD_START)
      && mutated.length < original.length,
    mutated === null ? 'ANCHORS NOT FOUND — the guard was not located' :
      `cut ${original.length - mutated.length} bytes; guard anchor present after cut=${mutated.includes(GUARD_START)}`);

  if (mutated) {
    fs.writeFileSync(scratchPath, mutated);
    const scratch = require(scratchPath);
    const unguarded = freshStore(scratch.openHeartStore, tmpDb('redarm'));
    const r1 = enqueueSeat(unguarded, SEAT_A);
    unguarded.fireQueueRow({ queueId: r1.queue_id, now: new Date(Date.now() + 1000), tick: 1 });
    const r2 = enqueueSeat(unguarded, SEAT_A);
    const rowsAfter = pendingFor(unguarded, SEAT_A).length;
    check('red-arm-UNGUARDED-mints-a-second-row',
      !r2.deduped && r2.queue_id !== r1.queue_id && rowsAfter === 1,
      `unguarded second enqueue minted queue_id=${r2.queue_id} (first=${r1.queue_id}) pending=${rowsAfter} — the guard is what check 2 measures`);
    scratch.closeHeartStore();
  } else {
    check('red-arm-UNGUARDED-mints-a-second-row', false, 'SKIPPED — mutation could not be built');
  }

  out(`FAILURES: ${failures}`);
  out(`EXIT: ${failures === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failures === 0 ? 0 : 1;
}

main().catch((err) => {
  out('ERROR:', err.message, err.stack);
  out(`EXIT: 1`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
}).finally(() => {
  try { fs.unlinkSync(scratchPath); } catch {}
  for (const p of dbs) {
    for (const suffix of ['', '-wal', '-shm']) {
      try { fs.unlinkSync(p + suffix); } catch {}
    }
  }
  fs.writeFileSync(outPath, lines.join('\n') + '\n');
});
