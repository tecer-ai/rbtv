'use strict';

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore } = require('../server/heart/heart-store');
const {
  deriveOwed, reconcileGoal, STRIKE_LIMIT, NON_TERMINAL_DISPOSITIONS,
} = require('./reconcile');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'reconcile-selftest-'));
const lines = [];
function say(s) { lines.push(s); console.log(s); }

function writeSeat(goalFolder, seat, cast) {
  const dir = path.join(goalFolder, 'seats', seat);
  fs.mkdirSync(dir, { recursive: true });
  const fm = cast
    ? `---\nseat: ${seat}\nharness: bash\nmodel: probe-reconcile\n---\n\nbody\n`
    : `---\nseat: ${seat}\n---\n\nbody\n`;
  fs.writeFileSync(path.join(dir, 'seat.md'), fm);
}

function writeTaskforce(goalFolder, seats) {
  const rows = seats.map((s) => `tf,${s},,bash,probe-reconcile,high,35,`);
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n${rows.join('\n')}\n`);
}

function writeSessions(goalFolder, rows) {
  const cols = ['session-id', 'seat', 'harness', 'native-session-id', 'workdir',
    'recorded', 'started', 'ended', 'pid', 'pid-starttime', 'tty', 'disposition',
    'disposition-writer', 'execution', 'checkin', 'model', 'incomplete-reason'];
  const linesOut = [cols.join(',')];
  for (const r of rows) {
    linesOut.push(cols.map((c) => (r[c] == null ? '' : String(r[c]).replace(/,/g, ' '))).join(','));
  }
  fs.writeFileSync(path.join(goalFolder, 'sessions.csv'), `${linesOut.join('\n')}\n`);
}

function writeMessages(goalFolder, blocks) {
  const dir = path.join(goalFolder, 'coordination');
  fs.mkdirSync(dir, { recursive: true });
  const parts = ['# messages\n'];
  for (const b of blocks) {
    parts.push(`## ${b.num} | from: ${b.sender} | to: ${b.to} | type: ${b.type} | ${b.ts || '2026-08-19 12:00'}`);
    parts.push('');
    parts.push(b.body || 'body');
    parts.push('');
  }
  fs.writeFileSync(path.join(dir, 'messages.md'), parts.join('\n'));
}

function openStore() {
  const dbPath = path.join(fs.mkdtempSync(path.join(tmpRoot, 'db-')), 'heart.db');
  return openHeartStore({ dbPath });
}

function fixtureA() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'a-'));
  writeSeat(goalFolder, 'leader', true);
  writeSeat(goalFolder, 'plan-planner', true);
  writeTaskforce(goalFolder, ['leader', 'plan-planner']);
  writeSessions(goalFolder, [
    { 'session-id': 'pp1', seat: 'plan-planner', started: '2026-08-13 13:25',
      ended: '2026-08-13 13:51', disposition: 'incomplete', 'disposition-writer': 'seat' },
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-13 12:00',
      ended: '2026-08-13 12:10', disposition: 'done', 'disposition-writer': 'seat' },
  ]);
  return goalFolder;
}

function fixtureB() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'b-'));
  writeSeat(goalFolder, 'leader', true);
  writeTaskforce(goalFolder, ['leader']);
  writeSessions(goalFolder, [
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'done', checkin: '0' },
  ]);
  writeMessages(goalFolder, [
    { num: 1, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 11:00', body: 'please sit' },
  ]);
  return goalFolder;
}

function fixtureC() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'c-'));
  writeSeat(goalFolder, 'leader', true);
  writeSeat(goalFolder, 'worker', true);
  writeTaskforce(goalFolder, ['leader', 'worker']);
  writeSessions(goalFolder, [
    { 'session-id': 'w1', seat: 'worker', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'incomplete', 'disposition-writer': 'seat',
      'incomplete-reason': 'outputs-unverified: no declared output' },
  ]);
  return goalFolder;
}

function fixtureUncast() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'u-'));
  writeSeat(goalFolder, 'leader', false);
  writeSeat(goalFolder, 'worker', true);
  writeTaskforce(goalFolder, ['leader', 'worker']);
  writeSessions(goalFolder, [
    { 'session-id': 'w1', seat: 'worker', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'incomplete', 'disposition-writer': 'seat' },
  ]);
  writeMessages(goalFolder, []);
  return goalFolder;
}

const readyEmpty = { ready: new Map(), granted: new Map(), rows: [], reason: null };

say('── dispositions ──');
assert.deepStrictEqual([...NON_TERMINAL_DISPOSITIONS].sort(),
  ['exited', 'incomplete', 'renew', 'revive']);
say('ok  closed non-terminal set is coord RECORD_DISPOSITION_WRITER minus done');

say('── class (a) ──');
{
  const d = deriveOwed(fixtureA(), { readyAnswer: readyEmpty, live: new Set(), queued: new Set() });
  assert.strictEqual(d.classA.length, 1, JSON.stringify(d.classA));
  assert.strictEqual(d.classA[0].seat, 'plan-planner');
  assert.strictEqual(d.classA[0].disposition, 'incomplete');
  assert.strictEqual(d.owed, true);
  say('ok  incomplete plan-planner with no later sitting is class (a)');
}

say('── class (b) ──');
{
  const d = deriveOwed(fixtureB(), { readyAnswer: readyEmpty, live: new Set(), queued: new Set() });
  assert.strictEqual(d.classB.length, 1, JSON.stringify(d.classB));
  assert.strictEqual(d.classB[0].seat, 'leader');
  assert.strictEqual(d.classB[0].unreadCount, 1);
  say('ok  unread staff mail with no live sitting is class (b)');
}

say('── class (c) as class (a) ──');
{
  const d = deriveOwed(fixtureC(), { readyAnswer: readyEmpty, live: new Set(), queued: new Set() });
  assert.strictEqual(d.classA.length, 1);
  assert.strictEqual(d.classC.length, 1);
  assert.strictEqual(d.classC[0].outputsUnverified, true);
  say('ok  outputs-unverified is tagged class (c) and still class (a)');
}

say('── dead seats excluded ──');
{
  const goalFolder = fixtureA();
  const d = deriveOwed(goalFolder, {
    readyAnswer: {
      ready: new Map(), granted: new Map(), reason: null,
      rows: [{ seat: 'plan-planner', verdict: 'BLOCKED', dead: true }],
    },
    live: new Set(), queued: new Set(),
  });
  assert.strictEqual(d.classA.length, 0, JSON.stringify(d.classA));
  assert.deepStrictEqual(d.deadSeats, ['plan-planner']);
  say('ok  dead:true seat is never owed');
}

say('── launch class (a) enqueues leader, not deduped ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureA();
    const sent = [];
    const r = reconcileGoal({
      goal: 'fx-a', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(),
      promptFn: () => 'fixture prompt',
      sendFn: (x) => { sent.push(x); return { ok: true }; },
      recoverFn: () => ({ ok: true }),
    });
    const enq = r.actions.find((a) => a.kind === 'enqueue');
    assert.ok(enq, JSON.stringify(r.actions));
    assert.strictEqual(enq.seat, 'leader');
    assert.ok(enq.enq && !enq.enq.deduped, JSON.stringify(enq.enq));
    const q = store.listQueue();
    assert.strictEqual(q.length, 1);
    assert.strictEqual(q[0].job_id, 'seat-fx-a-leader');
    say(`ok  enqueued ${q[0].job_id} queue_id=${q[0].queue_id} deduped=${Boolean(enq.enq.deduped)}`);
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── class (b) enqueues staff chair ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureB();
    const r = reconcileGoal({
      goal: 'fx-b', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(),
      promptFn: () => 'fixture prompt',
      sendFn: () => ({ ok: true }),
      recoverFn: () => ({ ok: true }),
    });
    const enq = r.actions.find((a) => a.kind === 'enqueue');
    assert.ok(enq, JSON.stringify(r.actions));
    assert.strictEqual(enq.seat, 'leader');
    assert.ok(enq.enq && !enq.enq.deduped);
    say(`ok  class (b) enqueued ${enq.jobId} queue_id=${enq.enq.queue_id}`);
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── 3-strikes: exactly one stuck ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureUncast();
    const sent = [];
    const passes = [];
    for (let i = 0; i < 5; i += 1) {
      passes.push(reconcileGoal({
        goal: 'fx-u', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(),
        promptFn: () => 'fixture prompt',
        sendFn: (x) => { sent.push(x.body); return { ok: true }; },
        recoverFn: () => ({ ok: true }),
      }));
    }
    const refused = passes.map((p) => p.actions.find((a) => a.kind === 'launch-refused'));
    assert.ok(refused[0] && refused[0].error === 'E_UNCAST_SEAT', JSON.stringify(refused[0]));
    assert.strictEqual(refused[2].attempts, STRIKE_LIMIT);
    assert.strictEqual(refused[2].stuckEmitted, 1);
    assert.strictEqual(sent.length, 1, `stuck sends=${sent.length}`);
    assert.strictEqual(refused[4].stuckEmitted, 1);
    assert.strictEqual(sent.length, 1);
    const row = store.getReconcileAttempt('fx-u', 'leader', 'nonterm');
    assert.strictEqual(Number(row.attempts), 5);
    assert.strictEqual(Number(row.stuck_emitted), 1);
    say(`ok  attempts 1-3 recorded, one stuck after ${STRIKE_LIMIT}, zero more on passes 4-5; store attempts=${row.attempts}`);
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── count durable across store close/reopen ──');
{
  const dbDir = fs.mkdtempSync(path.join(tmpRoot, 'dur-'));
  const dbPath = path.join(dbDir, 'heart.db');
  const goalFolder = fixtureUncast();
  let store = openHeartStore({ dbPath });
  try {
    for (let i = 0; i < 2; i += 1) {
      reconcileGoal({
        goal: 'fx-d', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(),
        promptFn: () => 'x',
        sendFn: () => ({ ok: true }),
        recoverFn: () => ({ ok: true }),
      });
    }
    const before = store.getReconcileAttempt('fx-d', 'leader', 'nonterm');
    assert.strictEqual(Number(before.attempts), 2);
    say(`  before close: attempts=${before.attempts}`);
    store.close();
    closeHeartStore();
    store = openHeartStore({ dbPath });
    reconcileGoal({
      goal: 'fx-d', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(),
      promptFn: () => 'x',
      sendFn: () => ({ ok: true }),
      recoverFn: () => ({ ok: true }),
    });
    const after = store.getReconcileAttempt('fx-d', 'leader', 'nonterm');
    assert.strictEqual(Number(after.attempts), 3, `expected 3 got ${after.attempts}`);
    say(`  after reopen+1: attempts=${after.attempts}`);
    say('ok  count survived close/reopen (2 → 3, not reset to 1)');
  } finally {
    try { store.close(); } catch { /* already */ }
    closeHeartStore();
  }
}

say('── paused goal is not reconciled ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureA();
    fs.writeFileSync(path.join(goalFolder, 'execution-lane'), 'paused console\n');
    const logs = [];
    const r = reconcileGoal({
      goal: 'fx-pause', goalFolder, engine: { heartStore: store },
      say: (level, message) => { logs.push({ level, message }); },
      force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'fixture prompt',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    assert.strictEqual(r.skipped, 'paused', JSON.stringify(r));
    assert.strictEqual(store.listQueue().length, 0, 'paused goal must not enqueue');
    assert.ok(logs.some((l) => l.message === 'reconcile: skipped — goal is paused'),
      JSON.stringify(logs));
    say('ok  paused console → skipped:paused, queue empty, skip log fired');

    fs.writeFileSync(path.join(goalFolder, 'execution-lane'), 'daemon\n');
    const unpaused = reconcileGoal({
      goal: 'fx-pause', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'fixture prompt',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    const enq = unpaused.actions && unpaused.actions.find((a) => a.kind === 'enqueue');
    assert.ok(enq, JSON.stringify(unpaused.actions));
    assert.ok(enq.enq && !enq.enq.deduped, JSON.stringify(enq.enq));
    say(`ok  control: same folder unpaused enqueued ${enq.jobId || enq.seat}`);
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── cadence skip ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureA();
    const first = reconcileGoal({
      goal: 'fx-cad', goalFolder, engine: { heartStore: store },
      say: () => {}, force: false, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'x',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
      now: Date.parse('2026-08-19T12:00:00Z'),
    });
    assert.ok(!first.skipped, JSON.stringify(first));
    const second = reconcileGoal({
      goal: 'fx-cad', goalFolder, engine: { heartStore: store },
      say: () => {}, force: false, readyAnswer: readyEmpty,
      now: Date.parse('2026-08-19T12:02:00Z'),
    });
    assert.strictEqual(second.skipped, 'cadence');
    say('ok  second pass inside 300s is cadence-skipped');
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── red arm: mutation of the strike guard ──');
{
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const ANCHOR = 'if (attempts >= STRIKE_LIMIT && !stuckWas)';
  assert.ok(src.includes(ANCHOR), 'strike guard anchor missing');
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'reconcile.js'), null);
  mut.filename = path.join(__dirname, 'reconcile.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(src.replace(ANCHOR, 'if (false && attempts >= STRIKE_LIMIT && !stuckWas)'), mut.filename);
  const store = openStore();
  try {
    const goalFolder = fixtureUncast();
    const sent = [];
    for (let i = 0; i < 4; i += 1) {
      mut.exports.reconcileGoal({
        goal: 'fx-red', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'x',
        sendFn: (x) => { sent.push(x); return { ok: true }; },
        recoverFn: () => ({ ok: true }),
      });
    }
    assert.strictEqual(sent.length, 0, `mutated guard still emitted ${sent.length} stuck`);
    say('ok  red: deleting the strike emit guard yields 0 stuck after 4 refusals');
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── red arm: mutation of the pause gate ──');
{
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const ANCHOR = 'if (goalFolder && laneIsPaused(goalFolder))';
  assert.ok(src.includes(ANCHOR), 'pause gate anchor missing');
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'reconcile.js'), null);
  mut.filename = path.join(__dirname, 'reconcile.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(src.replace(ANCHOR, 'if (false && goalFolder && laneIsPaused(goalFolder))'), mut.filename);
  const store = openStore();
  try {
    const goalFolder = fixtureA();
    fs.writeFileSync(path.join(goalFolder, 'execution-lane'), 'paused console\n');
    const r = mut.exports.reconcileGoal({
      goal: 'fx-pause-red', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'x',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    assert.notStrictEqual(r.skipped, 'paused', JSON.stringify(r));
    const enq = r.actions && r.actions.find((a) => a.kind === 'enqueue');
    assert.ok(enq, `mutated pause gate did not enqueue: ${JSON.stringify(r.actions)}`);
    say('ok  red: deleting the pause gate enqueues a paused goal');
  } finally {
    store.close();
    closeHeartStore();
  }
}

fs.rmSync(tmpRoot, { recursive: true, force: true });
say('reconcile.selftest OK');
