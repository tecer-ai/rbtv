#!/usr/bin/env node
'use strict';

// probe-enqueue-record — THE ENQUEUE→LAUNCH RECORD (enqueue-record, 2026-08-19).
//
// THE MEASURED DEFECT (root-cause-archaeology-2026-08-19.md §1 step 5): the seeding pass logged
// `enqueued seat leader` for meet-transcript-summarizer while heartStore.enqueue() had returned
// `{ deduped: true, because: 'live-turn' }` and inserted nothing. The return was discarded, the
// seat was pushed onto pickup.enqueued, and zero durable trace existed. The goal froze for hours.
//
// This probe reproduces that shape: a READY seat whose SEAT KEY is already held by a live,
// non-terminal turn the seeding pass cannot see. D12 (2026-08-20) deleted the relaunch grant that
// used to produce that split, so the holder is now a FOREIGN job over the SAME seat workdir —
// which is the truer shape anyway: `findSeatHolder` keys on the seat (`seatKeyOf` -> the workdir),
// `seatState` keys on the JOB (`jobIdFor(seat, goal)`), and the 08-19 freeze lived in exactly that
// gap. It then asserts the arms the seat named. The REAL seedGoal and the REAL store are driven;
// pickup is never hand-built.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const HERE = __dirname;
const IGNITE_SRC = path.join(HERE, '..', '..');
const OUT_PATH = path.join(HERE, 'probe-enqueue-record.out');
const HEART = path.join(IGNITE_SRC, 'state-store', 'heart');
const SCHEMA_SQL = fs.readFileSync(path.join(HEART, 'schema.sql'), 'utf8');

const { seedGoal } = require('../seeding');
const { openHeartStore } = require('../../state-store/heart/heart-store');
const { migrate, LATEST, MIGRATIONS, MIGRATION_ENQUEUE_LOG } = require('../../state-store/heart/migrations');

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
    // ── set up the 08-19 shape: a FOREIGN live turn holding the seat key, then seed ──
    // The holder is registered under its OWN job id, UNHOMED, with the seat's workdir as its
    // args — so `seatKeyOf` resolves `workdir:<goalFolder>/seats/<SEAT>` (the exact key the
    // seeding pass's own enqueue resolves) while `jobIdFor(SEAT, GOAL)` names a different job the
    // record view has never seen. That is the split the freeze lived in.
    say('── fixture: a FOREIGN live turn holds the seat key, then one seed pass ───────');
    const seatDir = path.join(goalFolder, 'seats', SEAT);
    const HOLDER_JOB = 'foreign-holder';
    store = openHeartStore({ dbPath });
    store.registerJob({
      jobId: HOLDER_JOB,
      actionType: 'launch-agent',
      function: 'foreign live turn',
      argsSchema: JSON.stringify({ required: {}, optional: { workdir: 'string' } }),
      description: 'a turn this goal\'s seeding pass cannot see',
      createdAt: isoAgo(0),
      updatedAt: isoAgo(0),
    });
    const fired = store.recordExecutionStart({
      jobId: HOLDER_JOB,
      actionType: 'launch-agent',
      args: JSON.stringify({ workdir: seatDir }),
      enqueuedBy: 'probe-foreign-lane',
      sessionMode: 'headless',
      firedTick: 1,
      firedAt: new Date(),
    });
    say(`  foreign holder exec_id=${fired && fired.exec_id} status=${fired && fired.status}`);
    store.close();
    store = null;

    const second = pass({ dbPath, goalFolder });
    store = second.heartStore;
    say(`  seed enqueued=${JSON.stringify(second.pickup.enqueued)}`);
    say(`  seed suppressedEnqueues=${JSON.stringify(second.pickup.suppressedEnqueues || null)}`);
    say(`  no grant file exists: ${JSON.stringify(fs.readdirSync(path.join(goalFolder, 'coordination')).filter((f) => /grant/.test(f)))}`);
    say(`  seed logs: ${JSON.stringify(second.logs.map((l) => ({ level: l.level, message: l.message, because: l.because, seat: l.seat })))}`);

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
      // …and RE-HOME the holder's row onto the seat's own job. While the holder is only reachable
      // by seat KEY, `states[SEAT]` reads `ready`, which is a true statement about a different
      // condition. A cadence later the record HAS attributed the
      // turn, which is the state this arm is about: the seat is LIVE, an enqueue for it was
      // recorded, and nothing ever fired FOR THAT ENQUEUE. One UPDATE, so the arm keeps its
      // subject instead of drifting onto its neighbour's.
      store.db.prepare('UPDATE jobs_log SET job_id = ? WHERE exec_id = ?')
        .run(`seat-${GOAL}-${SEAT}`, fired.exec_id);
    }
    store.close();
    store = null;
    const third = pass({ dbPath, goalFolder });
    store = third.heartStore;
    say(`  third enqueueUnfired=${JSON.stringify(third.pickup.enqueueUnfired || null)}`);
    const unfired = third.pickup.enqueueUnfired || [];
    check('Arm C: pickup.enqueueUnfired names the seat',
      unfired.some((r) => r.seat === SEAT),
      JSON.stringify(unfired));

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
    check('Arm D: the enqueue-unfired condition goes away',
      !(fourth.pickup.enqueueUnfired || []).length,
      JSON.stringify(fourth.pickup.enqueueUnfired || null));
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
    pre.exec(`PRAGMA user_version = ${Math.max(0, MIGRATION_ENQUEUE_LOG.version - 1)}`);
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
  : 'RESULT: PASS — suppressed enqueue is warned, recorded, and clears on fire; '
    + 'migration is idempotent and equivalent to a fresh store; the isHeld guard speaks.');
say(`WALL_MS ${Date.now() - start}`);
say(`EXIT ${exitCode}`);
fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n');
console.log(lines.join('\n'));
process.exit(exitCode);
