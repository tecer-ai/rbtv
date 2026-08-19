#!/usr/bin/env node
'use strict';

// probe-enqueue-record — THE ENQUEUE→LAUNCH RECORD (enqueue-record, 2026-08-19).
//
// THE MEASURED DEFECT (root-cause-archaeology-2026-08-19.md §1 step 5): the seeding pass logged
// `enqueued seat leader` for meet-transcript-summarizer while heartStore.enqueue() had returned
// `{ deduped: true, because: 'live-turn' }` and inserted nothing. The return was discarded, the
// seat was pushed onto pickup.enqueued, and zero durable trace existed. The goal froze for hours.
//
// This probe reproduces that shape: a READY seat whose prior turn is still non-terminal (the
// live-turn arm of findSeatHolder), hidden from seatState by a relaunch grant — the 08-19
// spend-then-enqueue ordering. It then asserts the six arms the seat named. The REAL seedGoal
// and the REAL store are driven; conditionOf is never handed a hand-built pickup.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const HERE = __dirname;
const IGNITE_SRC = path.join(HERE, '..', '..');
const OUT_PATH = path.join(HERE, 'probe-enqueue-record.out');
const HEART = path.join(IGNITE_SRC, 'server', 'heart');
const SCHEMA_SQL = fs.readFileSync(path.join(HEART, 'schema.sql'), 'utf8');

const { seedGoal } = require('../seeding');
const { openHeartStore } = require('../../server/heart/heart-store');
const { migrate, LATEST, MIGRATIONS } = require('../../server/heart/migrations');
const { stallAlarmDecision, conditionOf, STALL_MS, REASONS } = require('../../server/ticker/goal-stall-alarm');

const start = Date.now();
const lines = [];
const failures = [];
function say(s) { lines.push(s); }
function check(claim, ok, detail) {
  say(`${ok ? 'ok  ' : 'FAIL'}  ${claim}${ok ? '' : ` — ${detail}`}`);
  if (!ok) failures.push(claim);
}

const GOAL = 'enq-rec';
// `leader` is a reserved ON-DEMAND staff chair (coord verdict IDLE with no mail). A
// workflow seat named `builder` is READY at the root — the 08-19 shape, not the name.
const SEAT = 'builder';

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-enqueue-record-'));
  const goalFolder = path.join(root, '.rbtv', 'goals', GOAL);
  fs.mkdirSync(path.join(goalFolder, 'seats', SEAT), { recursive: true });
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    `taskforce-id,seat,after\ntf,${SEAT},\n`);
  fs.writeFileSync(path.join(goalFolder, 'seats', SEAT, 'seat.md'),
    `---\nseat: ${SEAT}\nharness: bash\nmodel: probe-enq\n---\n\nbody\n`);
  const dbPath = path.join(root, 'heart.db');
  return { root, goalFolder, dbPath };
}

function pass({ dbPath, goalFolder, isHeld = null }) {
  const logs = [];
  const heartStore = openHeartStore({ dbPath });
  let pickup;
  try {
    pickup = seedGoal({
      heartStore, goalFolder, goal: GOAL, isHeld,
      logger: (m) => logs.push(m),
    });
    return { pickup, logs, heartStore };
  } catch (err) {
    heartStore.close();
    throw err;
  }
}

function enqueueLogRows(store) {
  try {
    return store.db.prepare('SELECT * FROM enqueue_log ORDER BY enq_id').all();
  } catch (err) {
    return { missing: String(err && err.message) };
  }
}

function isoAgo(ms) {
  return new Date(Date.now() - ms).toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function main() {
  const { root, goalFolder, dbPath } = fixture();
  let store = null;
  try {
    // ── set up the 08-19 shape: enqueue, fire (live-turn holder), grant, re-seed ──
    say('── fixture: first seed (no holder) then fire, then grant+re-seed ─────────────');
    const first = pass({ dbPath, goalFolder });
    store = first.heartStore;
    const queued = store.listQueue().filter((q) => q.job_id === `seat-${GOAL}-${SEAT}`);
    say(`  first enqueued=${JSON.stringify(first.pickup.enqueued)} queue_rows=${queued.length}`);
    if (!queued.length) {
      check('fixture: first pass enqueued the seat (precondition for the live-turn holder)',
        false, `enqueued=${JSON.stringify(first.pickup.enqueued)} logs=${JSON.stringify(first.logs.map((l) => l.message))}`);
      return;
    }
    const fired = store.fireQueueRow({ queueId: queued[0].queue_id, now: new Date(), tick: 1 });
    say(`  fired exec_id=${fired && fired.exec_id} status=${fired && fired.status}`);
    fs.writeFileSync(path.join(goalFolder, 'coordination', 'relaunch-grants'), `${SEAT}\n`);
    store.close();
    store = null;

    const second = pass({ dbPath, goalFolder });
    store = second.heartStore;
    const grantAfter = fs.existsSync(path.join(goalFolder, 'coordination', 'relaunch-grants'))
      ? fs.readFileSync(path.join(goalFolder, 'coordination', 'relaunch-grants'), 'utf8')
      : '';
    say(`  second enqueued=${JSON.stringify(second.pickup.enqueued)}`);
    say(`  second suppressedEnqueues=${JSON.stringify(second.pickup.suppressedEnqueues || null)}`);
    say(`  grant file after second pass: ${JSON.stringify(grantAfter)}`);
    say(`  second logs: ${JSON.stringify(second.logs.map((l) => ({ level: l.level, message: l.message, because: l.because, seat: l.seat })))}`);

    // ── Arm A — the warn, not the lie ───────────────────────────────────────────
    const warn = second.logs.find((l) => l.level === 'warn' && l.seat === SEAT && l.because === 'live-turn');
    const lie = second.logs.find((l) => l.level === 'info' && l.message === 'enqueued seat' && l.seat === SEAT);
    check('Arm A: warn-level log names the suppression with because: live-turn',
      Boolean(warn), warn ? JSON.stringify(warn) : 'no warn with because=live-turn');
    check('Arm A: NO info `enqueued seat` line for that seat',
      !lie, lie ? JSON.stringify(lie) : '');
    check('Arm A: seat is absent from pickup.enqueued',
      !(second.pickup.enqueued || []).includes(SEAT),
      JSON.stringify(second.pickup.enqueued));

    // ── Arm B — the durable record ──────────────────────────────────────────────
    const rows = enqueueLogRows(store);
    const suppressed = Array.isArray(rows)
      ? rows.find((r) => r.outcome === 'suppressed' && r.because === 'live-turn')
      : null;
    check('Arm B: enqueue_log row outcome=suppressed because=live-turn with goal, seat, exec_id',
      Boolean(suppressed)
        && suppressed.goal === GOAL
        && suppressed.seat === SEAT
        && Number(suppressed.exec_id) === Number(fired.exec_id),
      Array.isArray(rows) ? JSON.stringify(suppressed || rows) : JSON.stringify(rows));

    // ── Arm C — the alarm decision ──────────────────────────────────────────────
    // The grace window is 60s: a just-written row is younger than the cutoff. Backdate it so
    // the NEXT real seedGoal pass measures it the way a cadence-old suppression would be.
    if (suppressed) {
      // Keep the real order (holder fires, THEN the suppression) while aging both past the
      // 60s grace: backdating only `enqueue_log.at` would put it BEFORE the holder's fired_at
      // and the unfired predicate would clear the row.
      store.db.prepare('UPDATE jobs_log SET fired_at = ? WHERE exec_id = ?').run(isoAgo(120 * 1000), fired.exec_id);
      store.db.prepare('UPDATE enqueue_log SET at = ? WHERE enq_id = ?').run(isoAgo(90 * 1000), suppressed.enq_id);
    }
    store.close();
    store = null;
    const third = pass({ dbPath, goalFolder });
    store = third.heartStore;
    say(`  third enqueueUnfired=${JSON.stringify(third.pickup.enqueueUnfired || null)}`);
    const cond = conditionOf(third.pickup);
    say(`  conditionOf=${JSON.stringify(cond)}`);
    const state = new Map();
    const t0 = Date.now();
    const below = stallAlarmDecision({ goal: GOAL, pickup: third.pickup, now: t0, state });
    const posted = stallAlarmDecision({ goal: GOAL, pickup: third.pickup, now: t0 + STALL_MS + 1, state });
    const again = stallAlarmDecision({ goal: GOAL, pickup: third.pickup, now: t0 + STALL_MS + 2, state });
    check('Arm C: past STALL_MS the decision posts kind=enqueue-unfired naming the seat',
      posted.action === 'post'
        && cond && cond.kind === 'enqueue-unfired'
        && (cond.seats || []).includes(SEAT),
      JSON.stringify({ action: posted.action, reason: posted.reason, signature: posted.signature, cond, below: below.reason }));
    check('Arm C: text does not contain the fallback "Frozen before seeding" wording',
      typeof posted.text === 'string' && !posted.text.includes('Frozen before seeding'),
      posted.text || '(no text)');
    check('Arm C: a second call at the same signature returns already-alerted',
      again.action === 'skip' && again.reason === REASONS.ALREADY_ALERTED,
      JSON.stringify({ action: again.action, reason: again.reason }));

    // ── Arm D — the record clears ───────────────────────────────────────────────
    const jobId = `seat-${GOAL}-${SEAT}`;
    const fireAt = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
    store.db.prepare(
      'INSERT INTO jobs_log (job_id, action_type, args, enqueued_by, fired_tick, fired_at, status) '
      + "VALUES (?, 'launch-agent', '{}', 'probe', 2, ?, 'launching')"
    ).run(jobId, fireAt);
    const leftover = typeof store.listEnqueueUnfired === 'function'
      ? store.listEnqueueUnfired(GOAL, fireAt)
      : { missing: 'listEnqueueUnfired' };
    check('Arm D: after a fire at-or-after the record, listEnqueueUnfired returns nothing',
      Array.isArray(leftover) && leftover.length === 0,
      JSON.stringify(leftover));
    store.close();
    store = null;
    const fourth = pass({ dbPath, goalFolder });
    store = fourth.heartStore;
    const gone = conditionOf(fourth.pickup);
    check('Arm D: the enqueue-unfired condition goes away',
      !gone || gone.kind !== 'enqueue-unfired',
      JSON.stringify(gone));
  } finally {
    if (store) try { store.close(); } catch { /* already closed */ }
    fs.rmSync(root, { recursive: true, force: true });
  }

  // ── Arm E — the migration ───────────────────────────────────────────────────
  say('── Arm E: migration + fresh-vs-migrated equivalence ────────────────────────');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-enqueue-record-mig-'));
  try {
    const preSql = SCHEMA_SQL
      .replace(/CREATE TABLE IF NOT EXISTS enqueue_log \([\s\S]*?\n\);\n/, '')
      .replace(/CREATE INDEX IF NOT EXISTS idx_enqueue_log[^\n]*\n/, '');
    const prePath = path.join(tmp, 'pre.db');
    const pre = new DatabaseSync(prePath);
    pre.exec(preSql);
    pre.exec(`PRAGMA user_version = ${Math.max(0, LATEST - 1)}`);
    const firstMig = migrate(pre);
    const tableAfter = pre.prepare("SELECT sql FROM sqlite_master WHERE type='table' AND name='enqueue_log'").get();
    check('Arm E: migrate() from the pre-migration user_version creates enqueue_log',
      Boolean(tableAfter && tableAfter.sql),
      `applied=${JSON.stringify(firstMig.applied)} to=${firstMig.to} sql=${tableAfter && tableAfter.sql}`);
    const secondMig = migrate(pre);
    check('Arm E: a second migrate() is a no-op',
      secondMig.applied.length === 0 && secondMig.from === secondMig.to,
      JSON.stringify(secondMig));
    const freshPath = path.join(tmp, 'fresh.db');
    const fresh = new DatabaseSync(freshPath);
    fresh.exec(SCHEMA_SQL);
    const freshSql = (fresh.prepare("SELECT sql FROM sqlite_master WHERE type='table' AND name='enqueue_log'").get() || {}).sql;
    const migratedSql = tableAfter && tableAfter.sql;
    check('Arm E: fresh-vs-migrated enqueue_log sql is identical',
      Boolean(freshSql) && freshSql === migratedSql,
      `fresh=${freshSql || '(none)'} migrated=${migratedSql || '(none)'}`);
    fresh.close();
    pre.close();
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }

  // ── Arm F — the silent guard speaks ─────────────────────────────────────────
  say('── Arm F: isHeld guard logs ────────────────────────────────────────────────');
  const heldFx = fixture();
  let heldStore = null;
  try {
    const held = pass({ dbPath: heldFx.dbPath, goalFolder: heldFx.goalFolder, isHeld: (s) => s === SEAT });
    heldStore = held.heartStore;
    const heldLog = held.logs.find((l) => l.level === 'info' && l.seat === SEAT
      && /held|human-interactive|detach/i.test(String(l.message || '')));
    check('Arm F: a held seat produces an info log entry naming it',
      Boolean(heldLog),
      heldLog ? JSON.stringify(heldLog) : JSON.stringify(held.logs.map((l) => ({ level: l.level, message: l.message, seat: l.seat }))));
  } finally {
    if (heldStore) try { heldStore.close(); } catch { /* already closed */ }
    fs.rmSync(heldFx.root, { recursive: true, force: true });
  }
}

try {
  main();
} catch (err) {
  say(`FAIL probe threw: ${err.stack || err.message}`);
  failures.push('probe threw');
}
const exitCode = failures.length ? 1 : 0;
say('');
say(exitCode
  ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
  : 'RESULT: PASS — suppressed enqueue is warned, recorded, alarmed, and clears on fire; '
    + 'migration is idempotent and equivalent to a fresh store; the isHeld guard speaks.');
say(`WALL_MS ${Date.now() - start}`);
say(`EXIT ${exitCode}`);
fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n');
console.log(lines.join('\n'));
process.exit(exitCode);
