'use strict';

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore } = require('../server/heart/heart-store');
const {
  deriveOwed, reconcileGoal, STRIKE_LIMIT, NON_TERMINAL_DISPOSITIONS, summonedSeats,
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
  // coord.py SESSIONS_COLS, verbatim. There is no `incomplete-reason` column and never was —
  // reconcile's old class-(c) parse read one, which is why it never fired (D32/D33a).
  const cols = ['session-id', 'seat', 'harness', 'native-session-id', 'workdir',
    'recorded', 'started', 'ended', 'pid', 'pid-starttime', 'tty', 'disposition',
    'disposition-writer', 'execution', 'checkin', 'model'];
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
      ended: '2026-08-19 10:05', disposition: 'done', checkin: '2026-08-19 10:04' },
  ]);
  writeMessages(goalFolder, [
    { num: 1, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 11:00', body: 'please sit' },
  ]);
  return goalFolder;
}

// D33(a) · the three endings side by side in ONE goal. `incomplete` is the SEAT'S word for
// unfinished — the watcher relaunches that seat by name. `unverified` (checkout's D5 refusal,
// D32) and `exited` (the harness died) are nobody's to close but the leader's.
function fixtureSplit() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'split-'));
  for (const s of ['leader', 'writer', 'checker', 'runner']) writeSeat(goalFolder, s, true);
  writeTaskforce(goalFolder, ['leader', 'writer', 'checker', 'runner']);
  writeSessions(goalFolder, [
    { 'session-id': 'w1', seat: 'writer', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'incomplete', 'disposition-writer': 'seat' },
    { 'session-id': 'c1', seat: 'checker', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:06', disposition: 'unverified', 'disposition-writer': 'seat' },
    { 'session-id': 'r1', seat: 'runner', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:07', disposition: 'exited', 'disposition-writer': 'kit' },
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-19 09:00',
      ended: '2026-08-19 09:30', disposition: 'done', 'disposition-writer': 'seat',
      checkin: '2026-08-19 09:30' },
  ]);
  writeMessages(goalFolder, []);
  return goalFolder;
}

// D34 · one owed row the LEADER owns, so the strike count for `nonterm` is unambiguous.
// `rewrite` replays a leader ruling by rewriting the ledger between passes.
function fixtureBound() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'bound-'));
  for (const s of ['leader', 'worker-a', 'worker-b']) writeSeat(goalFolder, s, true);
  writeTaskforce(goalFolder, ['leader', 'worker-a', 'worker-b']);
  writeMessages(goalFolder, []);
  return goalFolder;
}

function boundRows(goalFolder, rows) {
  writeSessions(goalFolder, [
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-19 09:00',
      ended: '2026-08-19 09:30', disposition: 'done', 'disposition-writer': 'seat',
      checkin: '2026-08-19 09:30' },
    ...rows.map(([seat, disposition, ended], i) => ({
      'session-id': `s${i}`, seat, started: '2026-08-19 10:00', ended: ended || '2026-08-19 10:05',
      disposition, 'disposition-writer': 'seat',
    })),
  ]);
}

// D35 · one chair, three messages, and the check-in stamp moved around them.
function fixtureMail({ checkin, started = '2026-08-19 10:00', row = true }) {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'mail-'));
  writeSeat(goalFolder, 'leader', true);
  writeTaskforce(goalFolder, ['leader']);
  writeSessions(goalFolder, row ? [
    { 'session-id': 'ld1', seat: 'leader', started, ended: '2026-08-19 10:30',
      disposition: 'done', 'disposition-writer': 'seat', checkin },
  ] : []);
  writeMessages(goalFolder, [
    { num: 1, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 11:00' },
    { num: 2, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 12:00' },
    { num: 3, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 13:00' },
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
      ended: '2026-08-19 10:05', disposition: 'unverified', 'disposition-writer': 'seat' },
  ]);
  writeMessages(goalFolder, []);
  return goalFolder;
}

// D24 · the summoned chair and a CONTROL staff chair in the IDENTICAL shape: both checked out
// non-terminal with no later sitting, both carrying unread mail. Only the summoned one is
// excluded — a leader relaunch on owed work is the watcher's whole purpose.
function fixtureSummoned() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 's-'));
  writeSeat(goalFolder, 'leader', true);
  writeSeat(goalFolder, 'goal-master', true);
  writeTaskforce(goalFolder, ['leader', 'goal-master']);
  writeSessions(goalFolder, [
    { 'session-id': 'gm1', seat: 'goal-master', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'incomplete', 'disposition-writer': 'seat',
      checkin: '2026-08-19 10:04' },
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'incomplete', 'disposition-writer': 'seat',
      checkin: '2026-08-19 10:04' },
  ]);
  writeMessages(goalFolder, [
    { num: 1, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 11:00' },
    { num: 2, sender: 'worker', to: 'goal-master', type: 'note', ts: '2026-08-19 11:01' },
  ]);
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

say('── D33(a): class (a) splits by WORD ──');
{
  const d = deriveOwed(fixtureSplit(), { readyAnswer: readyEmpty, live: new Set(), queued: new Set() });
  const byWord = Object.fromEntries(d.classA.map((x) => [x.seat, `${x.disposition}/${x.reason}`]));
  assert.deepStrictEqual(byWord, {
    writer: 'incomplete/incomplete',
    checker: 'unverified/nonterm',
    runner: 'exited/nonterm',
  }, JSON.stringify(byWord));
  assert.strictEqual(d.classC, undefined, 'classC survived the D33(a) delete');
  say(`ok  ${JSON.stringify(byWord)} — and classC is gone`);
}

say('── D33(a): the incomplete seat is enqueued BY NAME; the leader once, with a NAMED payload ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureSplit();
    const r = reconcileGoal({
      goal: 'fx-split', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'BOOT-PROMPT-BODY',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    const enq = r.actions.filter((a) => a.kind === 'enqueue');
    assert.deepStrictEqual(enq.map((a) => `${a.seat}:${a.reason}`).sort(),
      ['leader:nonterm', 'writer:incomplete'], JSON.stringify(r.actions));
    const q = Object.fromEntries(store.listQueue().map((row) => [row.job_id, JSON.parse(row.args)]));
    assert.deepStrictEqual(Object.keys(q).sort(), ['seat-fx-split-leader', 'seat-fx-split-writer'],
      JSON.stringify(Object.keys(q)));
    // BY NAME: the sitting is enqueued into the stranded seat's OWN folder, not the leader's.
    assert.ok(q['seat-fx-split-writer'].workdir.endsWith(`${path.sep}seats${path.sep}writer`),
      q['seat-fx-split-writer'].workdir);
    const payload = q['seat-fx-split-leader'].prompt;
    assert.ok(payload.startsWith('BOOT-PROMPT-BODY'), 'the boot prompt is no longer FIRST');
    // D39 · clearing and relaunching are TWO acts. The payload MUST name the second one, with
    // the real coord.py flag spelling (`launch --only <seat> --declare-only <anchor>`), and must
    // no longer claim a CLEAR re-arms an ordinary relaunch.
    assert.ok(!/ordinary relaunch/.test(payload), `payload still promises an ordinary relaunch: ${payload}`);
    for (const needle of ['checker', 'unverified', 'runner', 'exited', 'rule-disposition',
      'launch --only <seat> --declare-only', 'CLEARING IS NOT A RELAUNCH']) {
      assert.ok(payload.includes(needle), `leader payload never names ${needle}: ${payload}`);
    }
    assert.ok(!/^- `writer`/m.test(payload), `the by-name seat leaked into the leader payload: ${payload}`);
    say(`ok  writer workdir=…${q['seat-fx-split-writer'].workdir.slice(-20)}`);
    say(`ok  leader payload (${payload.length} chars) names checker/unverified, runner/exited and rule-disposition`);
    say(payload.slice(payload.indexOf('## The watcher woke you')));
  } finally {
    store.close();
    closeHeartStore();
  }
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

say('── launch class (a): the incomplete seat, not deduped ──');
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
    assert.strictEqual(enq.seat, 'plan-planner');
    assert.ok(enq.enq && !enq.enq.deduped, JSON.stringify(enq.enq));
    const q = store.listQueue();
    assert.strictEqual(q.length, 1);
    assert.strictEqual(q[0].job_id, 'seat-fx-a-plan-planner');
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

say('── D34: 2 strikes on a REFUSED launch, exactly one stuck ──');
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
    assert.strictEqual(STRIKE_LIMIT, 2, `D34 says 2 mechanical attempts, got ${STRIKE_LIMIT}`);
    assert.strictEqual(refused[STRIKE_LIMIT - 1].attempts, STRIKE_LIMIT);
    assert.strictEqual(refused[STRIKE_LIMIT - 1].stuckEmitted, 1);
    assert.strictEqual(sent.length, 1, `stuck sends=${sent.length}`);
    assert.strictEqual(refused[4].stuckEmitted, 1);
    assert.strictEqual(sent.length, 1);
    const row = store.getReconcileAttempt('fx-u', 'leader', 'nonterm');
    assert.strictEqual(Number(row.attempts), 5);
    assert.strictEqual(Number(row.stuck_emitted), 1);
    say(`ok  one stuck after ${STRIKE_LIMIT} refusals, zero more on passes 3-5; store attempts=${row.attempts}`);
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

// ── D34 · the counter measures NO PROGRESS ────────────────────────────────────────────────────
// This is the defect the redesign was built for: every one of these passes LAUNCHES fine (or is
// skipped because last pass's launch is still queued), so under the old `clearAttempt` on
// `launched.ok` the count reset every time, `reconcile_attempts` stayed empty and the loop never
// ended. `pass()` returns the store row for (leader, nonterm) after each pass.
function boundPass(store, goalFolder, sent, n) {
  reconcileGoal({
    goal: 'fx-bound', goalFolder, engine: { heartStore: store },
    say: () => {}, force: true, readyAnswer: readyEmpty,
    live: new Set(), promptFn: () => 'BOOT',
    sendFn: (x) => { sent.push(x.body); return { ok: true }; },
    recoverFn: () => ({ ok: true }),
  });
  return store.getReconcileAttempt('fx-bound', 'leader', 'nonterm');
}

say('── D34: unchanged owed set across 2 SUCCESSFUL passes → stuck; changed → reset; empty → cleared ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureBound();
    const sent = [];

    boundRows(goalFolder, [['worker-a', 'unverified']]);
    const p1 = boundPass(store, goalFolder, sent, 1);
    assert.strictEqual(Number(p1.attempts), 1, JSON.stringify(p1));
    assert.strictEqual(Number(p1.stuck_emitted), 0);
    assert.strictEqual(sent.length, 0, JSON.stringify(sent));
    say(`  pass 1 (owed a=unverified): attempts=${p1.attempts} stuck_emitted=${p1.stuck_emitted} sig=${p1.signature}`);

    const p2 = boundPass(store, goalFolder, sent, 2);
    assert.strictEqual(Number(p2.attempts), 2, JSON.stringify(p2));
    assert.strictEqual(Number(p2.stuck_emitted), 1, JSON.stringify(p2));
    assert.strictEqual(sent.length, 1, JSON.stringify(sent));
    assert.ok(/stuck: nonterm on `leader`/.test(sent[0]), sent[0]);
    say(`  pass 2 (owed UNCHANGED):   attempts=${p2.attempts} stuck_emitted=${p2.stuck_emitted}`);
    say(`  stuck body: ${sent[0]}`);

    // PROGRESS: the owed CONTENT changed (a second row appeared). Same seat, same reason.
    boundRows(goalFolder, [['worker-a', 'unverified'], ['worker-b', 'exited']]);
    const p3 = boundPass(store, goalFolder, sent, 3);
    assert.strictEqual(Number(p3.attempts), 1, JSON.stringify(p3));
    assert.strictEqual(Number(p3.stuck_emitted), 0, JSON.stringify(p3));
    assert.strictEqual(sent.length, 1, `a changed owed set re-sent stuck: ${JSON.stringify(sent)}`);
    assert.notStrictEqual(p3.signature, p2.signature);
    say(`  pass 3 (owed CHANGED):     attempts=${p3.attempts} stuck_emitted=${p3.stuck_emitted} sig=${p3.signature}`);

    // The leader ruled both rows `done` — the owed set is empty and the row goes.
    boundRows(goalFolder, [['worker-a', 'done'], ['worker-b', 'done']]);
    const p4 = boundPass(store, goalFolder, sent, 4);
    assert.ok(!p4, `owed set empty but the attempt row survived: ${JSON.stringify(p4)}`);
    say('  pass 4 (owed EMPTY):       attempt row cleared');
    say('ok  D34: launch success never clears; only a changed or empty owed set does');
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── RED arm: restore `clearAttempt` on launched.ok (and on skip-live-or-queued) ──');
{
  // The pre-fix code, verbatim, compiled from a COPY of the live source. If clause 2's first arm
  // does not discriminate, this mutant passes it too.
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const OK_ANCHOR = `      action = launched.ok
        ? { kind: 'enqueue', seat: t.seat, reason: t.reason, enq: launched.enq, jobId: launched.jobId }`;
  const SKIP_ANCHOR = `      action = { kind: 'skip-live-or-queued', seat: t.seat, reason: t.reason };`;
  assert.ok(src.includes(OK_ANCHOR), 'launched.ok anchor missing');
  assert.ok(src.includes(SKIP_ANCHOR), 'skip-live-or-queued anchor missing');
  const mutated = src
    .replace(OK_ANCHOR, `      if (launched.ok) clearAttempt(heartStore, goal, t.seat, t.reason);
${OK_ANCHOR}`)
    .replace(SKIP_ANCHOR, `      clearAttempt(heartStore, goal, t.seat, t.reason);
${SKIP_ANCHOR}`);
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'reconcile.js'), null);
  mut.filename = path.join(__dirname, 'reconcile.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(mutated, mut.filename);
  const store = openStore();
  try {
    const goalFolder = fixtureBound();
    boundRows(goalFolder, [['worker-a', 'unverified']]);
    const sent = [];
    const seen = [];
    for (let i = 0; i < 4; i += 1) {
      mut.exports.reconcileGoal({
        goal: 'fx-bound', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'BOOT',
        sendFn: (x) => { sent.push(x.body); return { ok: true }; },
        recoverFn: () => ({ ok: true }),
      });
      const row = store.getReconcileAttempt('fx-bound', 'leader', 'nonterm');
      seen.push(row ? Number(row.attempts) : null);
    }
    assert.strictEqual(sent.length, 0, `mutant emitted ${sent.length} stuck — the arm does not discriminate`);
    assert.ok(seen.every((n) => n === null || n === 1), JSON.stringify(seen));
    say(`ok  red: attempts across 4 passes = ${JSON.stringify(seen)}, stuck sends = 0 (the live defect)`);
  } finally {
    store.close();
    closeHeartStore();
  }
}

// ── D40 · the `incomplete` signature does NOT carry the row's end-time ───────────────────
// `ended` advances on every re-checkout, so with it in the signature an IDENTICAL give-up read as
// new work: attempts reset to 1 every sitting and D34's "2 tries then stuck" never fired.
function incPass(store, goalFolder, sent) {
  reconcileGoal({
    goal: 'fx-inc', goalFolder, engine: { heartStore: store },
    say: () => {}, force: true, readyAnswer: readyEmpty,
    live: new Set(), promptFn: () => 'BOOT',
    sendFn: (x) => { sent.push(x.body); return { ok: true }; },
    recoverFn: () => ({ ok: true }),
  });
  return store.getReconcileAttempt('fx-inc', 'worker-a', 'incomplete');
}

say('── D40: same seat, same word, DIFFERENT `ended` → attempts still reach 2 and stuck fires ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureBound();
    const sent = [];

    boundRows(goalFolder, [['worker-a', 'incomplete', '2026-08-19 10:05']]);
    const p1 = incPass(store, goalFolder, sent);
    assert.strictEqual(Number(p1.attempts), 1, JSON.stringify(p1));
    assert.strictEqual(Number(p1.stuck_emitted), 0, JSON.stringify(p1));
    assert.strictEqual(sent.length, 0, JSON.stringify(sent));
    say(`  pass 1 (ended 10:05): attempts=${p1.attempts} stuck_emitted=${p1.stuck_emitted} sig=${p1.signature}`);

    // The seat was relaunched, worked, and gave up again: SAME word, a LATER `ended`.
    boundRows(goalFolder, [['worker-a', 'incomplete', '2026-08-19 14:47']]);
    const p2 = incPass(store, goalFolder, sent);
    assert.strictEqual(Number(p2.attempts), 2, JSON.stringify(p2));
    assert.strictEqual(Number(p2.stuck_emitted), 1, JSON.stringify(p2));
    assert.strictEqual(p2.signature, p1.signature, `signature moved with ended: ${p1.signature} -> ${p2.signature}`);
    assert.strictEqual(sent.length, 1, JSON.stringify(sent));
    assert.ok(/stuck: incomplete on `worker-a`/.test(sent[0]), sent[0]);
    say(`  pass 2 (ended 14:47): attempts=${p2.attempts} stuck_emitted=${p2.stuck_emitted} sig=${p2.signature}`);
    say(`  stuck body: ${sent[0]}`);
    say('ok  D40: the attempt count survives a changed `ended`');
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── RED arm: restore `:${item.ended}` in the incomplete signature ──');
{
  // The pre-D40 line, verbatim, compiled from a COPY of the live source — the live file is never
  // touched. If the D40 arm above does not discriminate, this mutant passes it too.
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const ANCHOR = 'signature: `incomplete:${item.seat}`,';
  assert.ok(src.includes(ANCHOR), 'D40 signature anchor missing');
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'reconcile.js'), null);
  mut.filename = path.join(__dirname, 'reconcile.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(src.replace(ANCHOR, 'signature: `incomplete:${item.seat}:${item.ended}`,'), mut.filename);
  const store = openStore();
  try {
    const goalFolder = fixtureBound();
    const sent = [];
    const seen = [];
    for (const ended of ['2026-08-19 10:05', '2026-08-19 14:47', '2026-08-19 18:12']) {
      boundRows(goalFolder, [['worker-a', 'incomplete', ended]]);
      mut.exports.reconcileGoal({
        goal: 'fx-inc', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'BOOT',
        sendFn: (x) => { sent.push(x.body); return { ok: true }; },
        recoverFn: () => ({ ok: true }),
      });
      const row = store.getReconcileAttempt('fx-inc', 'worker-a', 'incomplete');
      seen.push(row ? Number(row.attempts) : null);
    }
    assert.strictEqual(sent.length, 0, `mutant emitted ${sent.length} stuck — the arm does not discriminate`);
    assert.deepStrictEqual(seen, [1, 1, 1], JSON.stringify(seen));
    say(`ok  red: attempts across 3 sittings = ${JSON.stringify(seen)}, stuck sends = 0 (the live defect)`);
  } finally {
    store.close();
    closeHeartStore();
  }
}

// ── D35 · unread mail is what was RECORDED AFTER the chair's last check-in ────────────────────
say('── D35: unread is a timestamp comparison, not a message number ──');
{
  const cases = [
    ['checkin between #2 and #3', { checkin: '2026-08-19 12:30' }, 1],
    ['checkin after #3', { checkin: '2026-08-19 13:30' }, 0],
    ['no checkin, started after #1', { checkin: '', started: '2026-08-19 11:30' }, 2],
    ['no row at all', { checkin: '', row: false }, 3],
  ];
  for (const [label, opts, want] of cases) {
    const d = deriveOwed(fixtureMail(opts), {
      readyAnswer: readyEmpty, live: new Set(), queued: new Set(),
    });
    const got = d.classB.length ? d.classB[0].unreadCount : 0;
    assert.strictEqual(got, want, `${label}: want ${want} got ${got} — ${JSON.stringify(d.classB)}`);
    say(`  ${label}: classB=${d.classB.length} unread=${got}`);
  }
  say('ok  D35: 1 / 0 / 2 / 3 — and an empty class (b) when the chair has read its mail');
}

say('── RED arm: restore the numeric mail cursor ──');
{
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const ANCHOR = '&& (!since || tsAfter(m.ts, since)));';
  assert.ok(src.includes(ANCHOR), 'class (b) unread anchor missing');
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'reconcile.js'), null);
  mut.filename = path.join(__dirname, 'reconcile.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(src.replace(ANCHOR, '&& m.num > (Number(since) || 0));'), mut.filename);
  const d = mut.exports.deriveOwed(fixtureMail({ checkin: '2026-08-19 13:30' }), {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(),
  });
  assert.strictEqual(d.classB.length, 1, JSON.stringify(d.classB));
  assert.strictEqual(d.classB[0].unreadCount, 3, JSON.stringify(d.classB));
  say('ok  red: Number(checkin) → NaN → cursor 0 → all 3 messages "unread" forever (238 on meet)');
}

say('── the dead class-(c) column is gone from the module ──');
{
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  assert.ok(!src.includes('incomplete-reason'), 'reconcile.js still reads incomplete-reason');
  assert.ok(!src.includes('outputsUnverified'), 'reconcile.js still carries outputsUnverified');
  assert.ok(!/\bclassC\b/.test(src), 'reconcile.js still derives classC');
  say('ok  no `incomplete-reason`, no `outputsUnverified`, no `classC` in reconcile.js');
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

say('── D24: summoned seats are never owed ──');
{
  const summoned = summonedSeats();
  assert.ok(summoned.has('goal-master'),
    `coord names no summoned seat — read of SUMMONED_SEATS is broken: ${JSON.stringify([...summoned])}`);
  say(`ok  summoned list read off coord.py: ${JSON.stringify([...summoned])}`);

  const goalFolder = fixtureSummoned();

  // RED: the same fixture with NO summoned set — the pre-fix behaviour, and the shape that
  // relaunched meet's goal-master every cadence.
  const red = deriveOwed(goalFolder, {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(), summoned: new Set(),
  });
  assert.ok(red.classA.some((x) => x.seat === 'goal-master'), JSON.stringify(red.classA));
  assert.ok(red.classB.some((x) => x.seat === 'goal-master'), JSON.stringify(red.classB));
  say('  red (summoned set empty): goal-master derives in BOTH class (a) and class (b)');

  const green = deriveOwed(goalFolder, {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(), summoned,
  });
  assert.ok(!green.classA.some((x) => x.seat === 'goal-master'), JSON.stringify(green.classA));
  assert.ok(!green.classB.some((x) => x.seat === 'goal-master'), JSON.stringify(green.classB));
  assert.ok(green.classA.some((x) => x.seat === 'leader'),
    `CONTROL leader lost its class (a): ${JSON.stringify(green.classA)}`);
  assert.ok(green.classB.some((x) => x.seat === 'leader'),
    `CONTROL leader lost its class (b): ${JSON.stringify(green.classB)}`);
  say('ok  green: goal-master in neither class; CONTROL leader still derives in both');
}

say('── D24: a full pass enqueues the leader and never the summoned chair ──');
{
  const store = openStore();
  try {
    const goalFolder = fixtureSummoned();
    const r = reconcileGoal({
      goal: 'fx-d24', goalFolder, engine: { heartStore: store },
      say: () => {}, force: true, readyAnswer: readyEmpty,
      live: new Set(), promptFn: () => 'fixture prompt',
      sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
    });
    const seats = r.actions.filter((a) => a.kind === 'enqueue').map((a) => a.seat);
    assert.ok(!seats.includes('goal-master'), `enqueued the summoned chair: ${JSON.stringify(r.actions)}`);
    assert.ok(seats.includes('leader'), `CONTROL leader was not enqueued: ${JSON.stringify(r.actions)}`);
    const ids = store.listQueue().map((q) => q.job_id);
    assert.deepStrictEqual(ids, ['seat-fx-d24-leader'], JSON.stringify(ids));
    say(`ok  queue holds ${JSON.stringify(ids)} — no seat-fx-d24-goal-master`);
  } finally {
    store.close();
    closeHeartStore();
  }
}

say('── D24: an unreadable coord degrades to the OLD behaviour, not a silent hole ──');
{
  const src = fs.readFileSync(path.join(__dirname, 'reconcile.js'), 'utf8');
  const ANCHOR = "const COORD_PY = path.join(__dirname, '..', 'team-kit', 'coord.py');";
  assert.ok(src.includes(ANCHOR), 'COORD_PY anchor missing');
  const Module = require('node:module');
  const mut = new Module(path.join(__dirname, 'reconcile.js'), null);
  mut.filename = path.join(__dirname, 'reconcile.js');
  mut.paths = Module._nodeModulePaths(__dirname);
  mut._compile(src.replace(ANCHOR, "const COORD_PY = '/nonexistent/coord.py';"), mut.filename);
  const warns = [];
  const set = mut.exports.summonedSeats((level, message) => warns.push(`${level}:${message}`));
  assert.strictEqual(set.size, 0, JSON.stringify([...set]));
  assert.ok(warns.some((w) => w.startsWith('warn:')), JSON.stringify(warns));
  const goalFolder = fixtureSummoned();
  const d = mut.exports.deriveOwed(goalFolder, {
    readyAnswer: readyEmpty, live: new Set(), queued: new Set(), summoned: set,
  });
  assert.ok(d.classB.some((x) => x.seat === 'goal-master'), JSON.stringify(d.classB));
  say('ok  unreadable coord → empty set + a warn, and derivation falls back to the old behaviour');
}

fs.rmSync(tmpRoot, { recursive: true, force: true });
say('reconcile.selftest OK');
