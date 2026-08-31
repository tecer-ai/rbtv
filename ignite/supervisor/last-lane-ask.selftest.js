'use strict';

// -- SELFTESTS FOR `last-lane-ask.js` + its wiring into `reconcile.js` --------------------------
//
// `d-recovery-last-lane-asks` + `d-recovery-waiting-goal-freeze` (owner ruling, 2026-08-31). The
// arms below prove, against the REAL `owed-from-endings.js#classifyOwed` predicate
// (`dl-abandoned-outcome`, live today) and the REAL `open_asks`/`seat_abandonments` store, not a
// stand-in:
//   (1) a goal whose last owed lane was ABANDONED mints ONE close-or-keep ask, and a reconcile
//       pass over that fixture neither fires the finish event nor relaunches anything;
//   (2) CONTROL — the same abandonment, but the goal still has ANOTHER owed lane: no ask is minted
//       (proves the ask fires on the LAST lane, never on any abandonment);
//   (3) CONTROL — ordinary completion with NO abandonment at all: no ask is minted (proves the ask
//       is caused by abandonment, never merely by "nothing owed" — see this seat's report for why
//       this replaces the seat.md's literal "no open ask -> pass behaves as today" framing: this
//       repo's `finishOnCompletion` is gated on `last_milestone_complete`, taskforce.csv-derived,
//       independent of owed/abandoned state — verified separately, not re-derived here);
//   (4) the SUSPENSION chain: minted-but-not-posted (`posted: 0`) answers `countOpenAsks` FALSE;
//       the SAME row after the generic `postAsk` flip (`posted: 1`) answers it TRUE — "minting the
//       ask, posted and open, IS the suspension" [seat.md], proved at the actual store predicate
//       `lane-watch.js:312` reads as `openAsk`;
//   (5) the goal's stored state stays neither `paused` nor `finished` after the mint.

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  openEndingStoreFor, closeEndingStores, bind: bindStore,
} = require('../state-store');
const {
  lastLaneAbandoned, mintLastLaneAsk, askIdForGoal, DISPOSITION_OPTIONS,
} = require('./last-lane-ask');
const { reconcileGoal } = require('./reconcile');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'last-lane-ask-selftest-'));
let failed = 0;
function pass(name) { process.stdout.write(`PASS ${name}\n`); }
function fail(name, err) {
  failed += 1;
  process.stdout.write(`FAIL ${name}: ${err && err.stack ? err.stack : err}\n`);
}

function writeSessions(goalFolder, rows) {
  const cols = ['session-id', 'seat', 'harness', 'native-session-id', 'workdir',
    'recorded', 'started', 'ended', 'pid', 'pid-starttime', 'tty', 'disposition',
    'disposition-writer', 'execution', 'checkin', 'model', 'hold-anchor'];
  const linesOut = [cols.join(',')];
  for (const r of rows) {
    linesOut.push(cols.map((c) => (r[c] == null ? '' : String(r[c]).replace(/,/g, ' '))).join(','));
  }
  fs.writeFileSync(path.join(goalFolder, 'sessions.csv'), `${linesOut.join('\n')}\n`);
}

function writeTaskforce(goalFolder, seats) {
  const rows = seats.map((s) => `tf,${s},,bash,probe-reconcile,high,35,`);
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n${rows.join('\n')}\n`);
}

function goalFolderFor(workspaceRoot, goal) {
  const dir = path.join(workspaceRoot, '.rbtv', 'goals', goal);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

// ── (1) last owed lane abandoned -> mints the ask; the pass finishes nothing, relaunches nothing ─
function caseLastLaneAbandonedMintsAsk() {
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'ws-last-'));
  const db = openEndingStoreFor(workspaceRoot);
  const api = bindStore(db);
  try {
    const goal = 'last-lane-goal';
    const goalFolder = goalFolderFor(workspaceRoot, goal);
    writeTaskforce(goalFolder, ['worker-dropped']);
    writeSessions(goalFolder, [
      {
        'session-id': 's1', seat: 'worker-dropped', started: '2026-08-31T20:00:00Z',
        ended: '2026-08-31T20:05:00Z', checkin: '2026-08-31 20:00',
      },
    ]);
    api.stampSystem({
      goal, seat: 'worker-dropped', ending: 'failed', reason_class: 'crash', evidence_pointer: '/tmp/dropped',
    });
    api.abandonSeat({
      goal, seat: 'worker-dropped', anchor: 'owner: drop-lane, this lane is stuck for good', abandoned_by: 'owner',
    });

    let focCalled = false;
    const r = reconcileGoal({
      goal,
      goalFolder,
      engine: { endingStore: api },
      workspaceRoot,
      say: () => {},
      force: true,
      readyAnswer: { ready: new Map(), granted: new Map(), rows: [], reason: null },
      live: new Set(),
      finishOnCompletionFn: () => { focCalled = true; return { fired: false }; },
    });

    assert.ok(focCalled, 'the injected finishOnCompletionFn must be reached — this pass must not skip that call');
    assert.ok(!(r.actions || []).some((a) => a.kind === 'finish-on-completion'),
      `the finish event must not fire on a last-lane-abandoned pass, got ${JSON.stringify(r.actions)}`);
    assert.ok(!(r.actions || []).some((a) => ['enqueue', 'room-rebuilt', 'room-reopened-no-leader'].includes(a.kind)),
      `nothing must be relaunched or the room rebuilt on a last-lane-abandoned pass, got ${JSON.stringify(r.actions)}`);
    const minted = (r.actions || []).find((a) => a.kind === 'last-lane-ask-minted');
    assert.ok(minted, `a close-or-keep ask must be minted, got ${JSON.stringify(r.actions)}`);

    const askId = askIdForGoal(goal);
    assert.strictEqual(minted.askId, askId);
    const record = JSON.parse(fs.readFileSync(
      path.join(workspaceRoot, '.rbtv', 'runtime', 'ignite', 'asks', `${askId}.json`), 'utf8',
    ));
    assert.strictEqual(record.kind, 'goal-disposition');
    assert.deepStrictEqual(record.options, [...DISPOSITION_OPTIONS]);
    assert.deepStrictEqual(record.abandoned_seats, ['worker-dropped']);

    const row = api.getAsk(askId);
    assert.ok(row, 'the open_asks row must exist');
    assert.strictEqual(row.state, 'open');
    assert.strictEqual(row.posted, 0, 'minting alone must never post — posted stays 0 until the chat side flips it');
    assert.strictEqual(row.label, 'recovery');

    // A second pass over the SAME state must not mint a second record or a second row (idempotent).
    const r2 = reconcileGoal({
      goal, goalFolder, engine: { endingStore: api }, workspaceRoot, say: () => {}, force: true,
      readyAnswer: { ready: new Map(), granted: new Map(), rows: [], reason: null },
      live: new Set(), finishOnCompletionFn: () => ({ fired: false }),
    });
    assert.ok(!(r2.actions || []).some((a) => a.kind === 'last-lane-ask-minted'),
      `a second pass must not mint a second ask, got ${JSON.stringify(r2.actions)}`);

    pass('last owed lane abandoned mints ONE close-or-keep ask; the pass finishes nothing and relaunches nothing; a second pass mints nothing more');
  } catch (err) { fail('last owed lane abandoned mints ask', err); } finally { closeEndingStores(); }
}

// ── (2) CONTROL — same abandonment, but ANOTHER lane is still owed: no ask is minted ────────────
function caseControlAnotherOwedLaneNoAsk() {
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'ws-control-owed-'));
  const db = openEndingStoreFor(workspaceRoot);
  const api = bindStore(db);
  try {
    const goal = 'control-owed-goal';
    const goalFolder = goalFolderFor(workspaceRoot, goal);
    writeTaskforce(goalFolder, ['worker-dropped', 'worker-still-owed']);
    writeSessions(goalFolder, [
      {
        'session-id': 's1', seat: 'worker-dropped', started: '2026-08-31T20:00:00Z',
        ended: '2026-08-31T20:05:00Z', checkin: '2026-08-31 20:00',
      },
      {
        'session-id': 's2', seat: 'worker-still-owed', started: '2026-08-31T20:00:00Z',
        ended: '2026-08-31T20:05:00Z', checkin: '2026-08-31 20:00',
      },
    ]);
    api.stampSystem({
      goal, seat: 'worker-dropped', ending: 'failed', reason_class: 'crash', evidence_pointer: '/tmp/dropped',
    });
    api.stampSystem({
      goal, seat: 'worker-still-owed', ending: 'failed', reason_class: 'crash', evidence_pointer: '/tmp/owed',
    });
    api.abandonSeat({
      goal, seat: 'worker-dropped', anchor: 'owner: drop-lane, this lane is stuck for good', abandoned_by: 'owner',
    });

    const r = reconcileGoal({
      goal, goalFolder, engine: { endingStore: api }, workspaceRoot, say: () => {}, force: true,
      readyAnswer: { ready: new Map(), granted: new Map(), rows: [], reason: null },
      live: new Set(), finishOnCompletionFn: () => ({ fired: false }),
    });
    assert.ok(!(r.actions || []).some((a) => a.kind === 'last-lane-ask-minted'),
      `no ask must be minted while another lane is still owed, got ${JSON.stringify(r.actions)}`);
    assert.strictEqual(readAskRecordCount(workspaceRoot), 0, 'no disk record must be written either');
    pass('CONTROL — an abandoned lane with another lane still owed mints NO ask (proves the ask fires on the LAST lane, not on any abandonment)');
  } catch (err) { fail('CONTROL another owed lane no ask', err); } finally { closeEndingStores(); }
}

// ── (3) CONTROL — ordinary completion, no abandonment at all: no ask is minted ──────────────────
function caseControlOrdinaryCompletionNoAsk() {
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'ws-control-done-'));
  const db = openEndingStoreFor(workspaceRoot);
  const api = bindStore(db);
  try {
    const goal = 'control-done-goal';
    const goalFolder = goalFolderFor(workspaceRoot, goal);
    // Ordinary completion: no session carries unfinished or unread work, and no seat here was ever
    // abandoned. `classifyOwed`'s `seats` set derives from `sessions.csv`'s rows (`lastBySeat`), so
    // an empty ledger is the simplest fixture that is trivially "nothing owed, nothing abandoned" —
    // no `done` stamp needed (and `stampSystem` refuses `done` from `who_stamped: 'system'` by
    // design: only a seat may declare its own work done).
    writeTaskforce(goalFolder, ['worker-done']);
    writeSessions(goalFolder, []);

    const r = reconcileGoal({
      goal, goalFolder, engine: { endingStore: api }, workspaceRoot, say: () => {}, force: true,
      readyAnswer: { ready: new Map(), granted: new Map(), rows: [], reason: null },
      live: new Set(), finishOnCompletionFn: () => ({ fired: false }),
    });
    assert.ok(!(r.actions || []).some((a) => a.kind === 'last-lane-ask-minted'),
      `ordinary completion with no abandonment must mint NO ask, got ${JSON.stringify(r.actions)}`);
    assert.strictEqual(readAskRecordCount(workspaceRoot), 0, 'no disk record must be written either');
    pass('CONTROL — ordinary completion with no abandonment mints NO ask (proves the ask is caused by abandonment, never merely by "nothing owed")');
  } catch (err) { fail('CONTROL ordinary completion no ask', err); } finally { closeEndingStores(); }
}

function readAskRecordCount(workspaceRoot) {
  const dir = path.join(workspaceRoot, '.rbtv', 'runtime', 'ignite', 'asks');
  try { return fs.readdirSync(dir).length; } catch { return 0; }
}

// ── (4) the suspension chain: minted-not-posted suspends nothing; posted=1 suspends the alarm ──
function caseSuspensionChainNeedsPosted() {
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'ws-suspend-'));
  const db = openEndingStoreFor(workspaceRoot);
  const api = bindStore(db);
  try {
    const goal = 'suspend-goal';
    const minted = mintLastLaneAsk({
      store: api,
      workspaceRoot,
      goal,
      abandonedSeats: [{ seat: 'worker-dropped', anchor: 'owner: drop-lane', abandoned_by: 'owner' }],
      at: '2026-08-31T21:00:00Z',
    });
    assert.ok(minted.minted, 'the ask must mint');
    assert.strictEqual(api.countOpenAsks(goal), 0,
      'minted but NOT posted (posted=0) must suspend nothing — countOpenAsks must read 0, matching lane-watch.js:312\'s `openAsk`');
    api.postAsk({ ask_id: minted.askId, posted_at: '2026-08-31T21:01:00Z' });
    assert.strictEqual(api.countOpenAsks(goal), 1,
      'once posted (posted=1) the SAME generic store primitive a chat-side poster calls, countOpenAsks must read 1 — this IS the suspension, per this seat\'s ruling');
    pass('the suspension chain is real and gated on `posted`: minted-not-posted suspends nothing, posted=1 suspends via the existing countOpenAsks predicate — no new freeze mechanism was built');
  } catch (err) { fail('suspension chain needs posted=1', err); } finally { closeEndingStores(); }
}

// ── (5) the goal stays visible: neither `paused` nor `finished` after the mint ──────────────────
function caseGoalStateStaysNeitherPausedNorFinished() {
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'ws-state-'));
  const db = openEndingStoreFor(workspaceRoot);
  const api = bindStore(db);
  try {
    const goal = 'state-goal';
    const goalFolder = goalFolderFor(workspaceRoot, goal);
    writeTaskforce(goalFolder, ['worker-dropped']);
    writeSessions(goalFolder, [
      {
        'session-id': 's1', seat: 'worker-dropped', started: '2026-08-31T20:00:00Z',
        ended: '2026-08-31T20:05:00Z', checkin: '2026-08-31 20:00',
      },
    ]);
    api.stampSystem({
      goal, seat: 'worker-dropped', ending: 'failed', reason_class: 'crash', evidence_pointer: '/tmp/dropped',
    });
    api.abandonSeat({
      goal, seat: 'worker-dropped', anchor: 'owner: drop-lane', abandoned_by: 'owner',
    });
    reconcileGoal({
      goal, goalFolder, engine: { endingStore: api }, workspaceRoot, say: () => {}, force: true,
      readyAnswer: { ready: new Map(), granted: new Map(), rows: [], reason: null },
      live: new Set(), finishOnCompletionFn: () => ({ fired: false }),
    });
    const row = api.getGoalState(goal);
    const stored = row && row.stored;
    assert.notStrictEqual(stored, 'paused', `the goal must not read as paused, got ${stored}`);
    assert.notStrictEqual(stored, 'finished', `the goal must not read as finished, got ${stored}`);
    pass(`the goal remains visible after the mint — stored state is ${JSON.stringify(stored)}, neither 'paused' nor 'finished'`);
  } catch (err) { fail('goal state stays neither paused nor finished', err); } finally { closeEndingStores(); }
}

// ── unit: `lastLaneAbandoned` reads `derived` and never re-derives it ───────────────────────────
function caseLastLaneAbandonedIsPure() {
  try {
    assert.strictEqual(lastLaneAbandoned(null), false);
    assert.strictEqual(lastLaneAbandoned({ owed: true, abandonedSeats: [{ seat: 'x' }] }), false,
      'owed=true must never mint regardless of abandonedSeats');
    assert.strictEqual(lastLaneAbandoned({ owed: false, abandonedSeats: [] }), false,
      'owed=false with no abandonment must never mint');
    assert.strictEqual(lastLaneAbandoned({ owed: false, abandonedSeats: [{ seat: 'x' }] }), true);
    pass('lastLaneAbandoned reads owed+abandonedSeats off the ONE owed computer\'s own return object');
  } catch (err) { fail('lastLaneAbandoned is pure', err); }
}

caseLastLaneAbandonedIsPure();
caseLastLaneAbandonedMintsAsk();
caseControlAnotherOwedLaneNoAsk();
caseControlOrdinaryCompletionNoAsk();
caseSuspensionChainNeedsPosted();
caseGoalStateStaysNeitherPausedNorFinished();

try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch { /* tmp */ }

if (failed) {
  process.stdout.write(`${failed} FAIL\n`);
  process.exit(1);
}
process.stdout.write('ALL PASS\n');
