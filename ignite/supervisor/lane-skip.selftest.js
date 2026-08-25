'use strict';

// -- THE PER-LANE SKIP [D16, C-9] ---------------------------------------------------------------
//
// THE DEFECT: `lane-watch.js` used to `continue` the WHOLE GOAL when `uncastSeats` was non-empty,
// and again when any taskforce row had no seat folder. One unbuilt or uncast lane therefore froze
// every healthy sibling on that goal, for as long as the one bad row stood (inventory ST-19 /
// ST-20 / ST-10 are that shape).
//
// WHAT THIS MEASURES: the sibling LAUNCHES while the skipped lane does not. It drives `launchOwed`
// — the function that actually decides which seats are enqueued — against a real store and a real
// goal folder, because the whole point is what reaches the queue, not what a predicate returns.
//
// Run: `node --test`.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { openHeartStore, closeHeartStore } = require('../state-store/heart/heart-store');
const {
  launchOwed, readTaskforce, uncastSeats, seedTaskforce,
} = require('./seeding');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'lane-skip-'));

function writeSeat(goalFolder, seat, cast) {
  const dir = path.join(goalFolder, 'seats', seat);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'seat.md'), cast
    ? `---\nseat: ${seat}\nharness: bash\nmodel: probe-lane-skip\n---\n\nbody\n`
    : `---\nseat: ${seat}\n---\n\nbody\n`);
}

function writeTaskforce(goalFolder, seats) {
  const rows = seats.map((s) => `tf,${s},,bash,probe-lane-skip,high,35,`);
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n${rows.join('\n')}\n`);
}

// Two seats, both READY as far as coord is concerned. One of them is the lane the pass will skip.
function fixture({ uncastSeat = null, unbuiltSeat = null } = {}) {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'goal-'));
  const seats = ['sibling', 'problem-lane'];
  writeSeat(goalFolder, 'sibling', true);
  if (unbuiltSeat !== 'problem-lane') writeSeat(goalFolder, 'problem-lane', uncastSeat !== 'problem-lane');
  writeTaskforce(goalFolder, seats);
  fs.writeFileSync(path.join(goalFolder, 'session-log.csv'),
    'session-id,seat,started,ended,disposition,disposition-writer,checkin\n');
  const dbPath = path.join(fs.mkdtempSync(path.join(tmpRoot, 'db-')), 'heart.db');
  return { goalFolder, store: openHeartStore({ dbPath }), seats };
}

// coord's answer: both seats READY, so nothing but the lane skip can hold either back.
function readyFor(seats) {
  return {
    ready: new Map(seats.map((s) => [s, []])),
    rows: seats.map((s) => ({ seat: s, verdict: 'READY', dead: false })),
  };
}

function pass(store, goalFolder, seats, laneSkips) {
  const rows = readTaskforce(goalFolder);
  // What `seedGoal` does immediately before `launchOwed`: register a job row per seat, so the
  // enqueue door has something to enqueue against.
  seedTaskforce(store, goalFolder, { logger: null, goal: 'g-lane-skip', rows });
  const { ready, rows: readyRows } = readyFor(seats);
  const laneSkipped = {};
  const logged = [];
  const enqueued = launchOwed(store, rows, {
    goalFolder,
    goal: 'g-lane-skip',
    logger: (r) => logged.push(r),
    ready,
    readyRows,
    heldByStore: {},
    suppressedEnqueues: {},
    laneSkips,
    laneSkipped,
  });
  return { enqueued, laneSkipped, logged };
}

test('an UNCAST lane is skipped BY ITSELF — its sibling launches [C-9]', () => {
  const { goalFolder, store, seats } = fixture({ uncastSeat: 'problem-lane' });
  try {
    // The predicate still names the bad seat — the computer is unchanged, only its readers are.
    assert.deepStrictEqual(uncastSeats(goalFolder), ['problem-lane']);

    const laneSkips = new Map(uncastSeats(goalFolder).map((s) => [s, 'uncast-seat']));
    const out = pass(store, goalFolder, seats, laneSkips);

    assert.deepStrictEqual(out.enqueued, ['sibling'],
      `the sibling must launch while the uncast lane does not: ${JSON.stringify(out.enqueued)}`);
    assert.deepStrictEqual(out.laneSkipped, { 'problem-lane': 'uncast-seat' });
    // The refusal is UNCHANGED and still NAMED — only its blast radius moved.
    const skipLog = out.logged.find((l) => l.seat === 'problem-lane' && l.because === 'uncast-seat');
    assert.ok(skipLog, 'the skipped lane is still named at warn');
    assert.strictEqual(skipLog.level, 'warn');
  } finally {
    store.close();
    closeHeartStore();
  }
});

test('an UNBUILT lane is skipped BY ITSELF — its sibling launches [C-9]', () => {
  const { goalFolder, store, seats } = fixture({ unbuiltSeat: 'problem-lane' });
  try {
    assert.ok(!fs.existsSync(path.join(goalFolder, 'seats', 'problem-lane')),
      'the fixture really has a registered row with no seat folder');
    const laneSkips = new Map([['problem-lane', 'unbuilt-seat']]);
    const out = pass(store, goalFolder, seats, laneSkips);
    assert.deepStrictEqual(out.enqueued, ['sibling']);
    assert.deepStrictEqual(out.laneSkipped, { 'problem-lane': 'unbuilt-seat' });
  } finally {
    store.close();
    closeHeartStore();
  }
});

test('RED: with the skip set EMPTY the same fixture enqueues both — the arm discriminates', () => {
  const { goalFolder, store, seats } = fixture();
  try {
    const out = pass(store, goalFolder, seats, null);
    assert.deepStrictEqual(out.enqueued.sort(), ['problem-lane', 'sibling'],
      'without a skip set nothing is held back, so the arms above measure the skip and not the fixture');
    assert.deepStrictEqual(out.laneSkipped, {});
  } finally {
    store.close();
    closeHeartStore();
  }
});

test('RED: the WHOLE-GOAL skip is gone from lane-watch — no `continue` survives on that list', () => {
  const src = fs.readFileSync(path.join(__dirname, 'lane-watch.js'), 'utf8');
  // The two branches that used to cancel the goal now fill a per-lane map and fall through.
  assert.match(src, /const laneSkips = new Map\(\);/);
  assert.match(src, /for \(const seat of unbuilt\) laneSkips\.set\(seat, 'unbuilt-seat'\);/);
  assert.match(src, /for \(const seat of uncastOnly\) laneSkips\.set\(seat, 'uncast-seat'\);/);
  // And nothing between the uncast branch and the seed call cancels the goal on that list.
  // Sliced to the branch itself: the `console-run-live` skip further down IS a whole-goal skip and
  // is nothing to do with this list — a goal an operator is driving by hand is not seeded, ruled
  // long before C-9.
  const uncastBranch = src.slice(src.indexOf('if (uncastOnly.length) {'), src.indexOf('if (consoleRunIsLive('));
  assert.ok(!/\n\s*continue;/.test(uncastBranch),
    `a whole-goal continue survives on the uncast list:\n${uncastBranch}`);
  // Same for the unbuilt branch.
  const unbuiltBranch = src.slice(src.indexOf('if (unbuilt.length) {'), src.indexOf('// ── EVERY SEAT MUST BE CAST'));
  assert.ok(!/\n\s*continue;/.test(unbuiltBranch),
    `a whole-goal continue survives on the unbuilt list:\n${unbuiltBranch}`);
  assert.match(src, /laneSkips\.size \? \{ laneSkips \} : \{\}/);
});

test('RED: the engine facade FORWARDS laneSkips — a destructuring facade drops what it does not name', () => {
  // MEASURED, not theoretical: `index.js#seedGoal` destructures its argument, so `laneSkips`
  // reached NOTHING until it was named there — every arm above passed while the production path
  // was inert, because they drive `launchOwed` directly. `probe-daemon-lane-watch` is what caught
  // it. This arm is the cheap standing guard for the same shape.
  const src = fs.readFileSync(path.join(__dirname, 'index.js'), 'utf8');
  const facade = src.slice(src.indexOf('seedGoal: ({'), src.indexOf('// Idempotent:'));
  assert.match(facade, /laneSkips = null,/, 'the facade must NAME laneSkips in its destructuring');
  assert.match(facade, /laneSkips,/, 'and pass it on to seedGoal');
});
