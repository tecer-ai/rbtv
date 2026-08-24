'use strict';

// -- SELFTESTS FOR THE DEATH STAMP --------------------------------------------------------------
//
// Two cases carry the whole change, and they are the two the seat's definition of done names:
//
//   (a) death before check-in - a process that DIED with no checkout is stamped `failed` with
//       reason class `crash`, and the killed word `exited` is unreachable. The store is the REAL
//       ending store, not a stub, precisely so the killed-vocabulary refusal and the mandatory
//       reason field are the ones that would run in production.
//   (d) done confirm-and-reap - a `done` checkout reaps EVERY seat, not only `ephemeral: yes`:
//       the process ends up GONE and the registry row ends up GONE, and no `failed` is invented
//       on top of the seat's own declaration.
//
// Both use REAL child processes. A fake pid proves nothing about a path whose reap step is a real
// signal to a real process, and (d)'s whole claim is that the process is actually gone afterwards.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, execFileSync } = require('node:child_process');

const { stampDeath, confirmAndReap, providerShaped } = require('./death-stamp');
const { recordSpawn, loadRegistry, isAliveProcess } = require('./registry');
const { openHeartStore, closeHeartStore } = require('../server/heart/heart-store');
const endingStore = require('../state-store');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'supervisor-death-'));
let failed = 0;

function pass(name) { process.stdout.write(`PASS ${name}\n`); }
function fail(name, err) {
  failed += 1;
  process.stdout.write(`FAIL ${name}: ${err && err.stack ? err.stack : err}\n`);
}
function assert(cond, msg) { if (!cond) throw new Error(msg); }

function regFile() {
  return path.join(fs.mkdtempSync(path.join(tmpRoot, 'r-')), 'registry.jsonl');
}

let heartCount = 0;
function freshStore() {
  heartCount += 1;
  const dbPath = path.join(fs.mkdtempSync(path.join(tmpRoot, 'db-')), `heart-${heartCount}.db`);
  const heart = openHeartStore({ dbPath });
  return { api: endingStore.bind(heart.db), close: () => { heart.close(); closeHeartStore(); } };
}

function liveChild() {
  return spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { stdio: 'ignore' });
}

// A child killed and REAPED by this process leaves the process table entirely, which is the state
// a witnessed death actually presents. Waiting on the exit event is what makes it deterministic.
function deadPid(cb) {
  const child = liveChild();
  const pid = child.pid;
  child.on('exit', () => cb(pid));
  child.kill('SIGKILL');
}

// -- (a) DEATH BEFORE CHECK-IN -> failed: crash, and NEVER `exited` -----------------------------
function caseCrashBeforeCheckIn(done) {
  const store = freshStore();
  const file = regFile();
  deadPid((pid) => {
    try {
      recordSpawn({ goal: 'g1', seat: 'alpha', pid, start_time: '999', launch_token: 'tok' }, file);
      const out = stampDeath({
        goal: 'g1',
        seat: 'alpha',
        pid,
        start_time: '999',
        checkedIn: false,
        exitCode: 137,
        session: 'sess-a',
      }, { store: store.api, registryFile: file });

      assert(out.stamped === true, 'a death with no checkout must be stamped');
      assert(out.ending === 'failed', `ending must be failed, got ${out.ending}`);
      assert(out.reason_class === 'crash', `reason class must be crash, got ${out.reason_class}`);
      const row = store.api.getCurrentEnding({ goal: 'g1', seat: 'alpha' });
      assert(row.ending === 'failed', `stored ending must be failed, got ${row.ending}`);
      assert(row.reason_class === 'crash', `stored reason class must be crash, got ${row.reason_class}`);
      assert(row.who_stamped === 'system', 'a death nobody witnessed is a SYSTEM stamp');
      assert(String(row.evidence_pointer).includes('exit=137'),
        `the evidence pointer must carry the observed exit code: ${row.evidence_pointer}`);
      // The whole vocabulary claim, asserted rather than assumed: NOTHING on this row spells it.
      assert(!JSON.stringify(row).includes('exited'), `the killed word survived on the row: ${JSON.stringify(row)}`);
      // And the store REFUSES it at the boundary, so no future caller can reintroduce it either.
      let refused = false;
      try {
        store.api.stampSystem({ goal: 'g1', seat: 'beta', ending: 'exited', evidence_pointer: 'x' });
      } catch (err) { refused = /killed vocabulary|unknown ending/i.test(err.message); }
      assert(refused, '`exited` must be refused by the ending store, not merely unused');
      // The row was reaped: the process is gone, so write moment (iii) fires.
      assert(out.reaped === true && loadRegistry(file).length === 0,
        'a stamped death whose process is gone must drop its registry row');
      pass('(a) death before check-in stamps failed:crash and never `exited`');
    } catch (err) { fail('(a) death before check-in', err); }
    store.close();
    done();
  });
}

// -- (a2) THE CHECKED-IN CRASH CARRIES ITS EXIT CODE AND TRANSCRIPT TAIL [T1-R18] ----------------
function caseCrashAfterCheckIn(done) {
  const store = freshStore();
  const file = regFile();
  deadPid((pid) => {
    try {
      recordSpawn({ goal: 'g1', seat: 'gamma', pid, start_time: '999' }, file);
      const out = stampDeath({
        goal: 'g1', seat: 'gamma', pid, start_time: '999',
        checkedIn: true, exitCode: 1, transcriptTail: '/tmp/gamma.log', session: 'sess-g',
      }, { store: store.api, registryFile: file });
      assert(out.reason_class === 'crash', 'a checked-in death is still a crash');
      assert(out.checkedIn === true, 'the check-in fact must survive onto the result');
      const row = store.api.getCurrentEnding({ goal: 'g1', seat: 'gamma' });
      assert(String(row.evidence_pointer).includes('exit=1'), 'exit code missing from the pointer');
      assert(String(row.evidence_pointer).includes('transcript-tail:/tmp/gamma.log'),
        `transcript-tail pointer missing: ${row.evidence_pointer}`);
      pass('(a2) a checked-in crash carries exit code + transcript-tail [T1-R18]');
    } catch (err) { fail('(a2) checked-in crash evidence', err); }
    store.close();
    done();
  });
}

// -- (d) A `done` CHECKOUT CONFIRM-AND-REAPS - EVERY SEAT, NOT ONLY `ephemeral: yes` -------------
function caseDoneConfirmAndReap(done) {
  const store = freshStore();
  const file = regFile();
  const child = liveChild();
  const pid = child.pid;
  // The seat declared `done` itself; the descriptor carries NO `ephemeral: yes`, which is exactly
  // the seat today's code would leave running forever.
  const outFile = path.join(tmpRoot, 'declared-output.txt');
  fs.writeFileSync(outFile, 'the work', 'utf8');
  store.api.stampSeatDeclare({
    goal: 'g2', seat: 'delta', ending: 'done',
    declared_outputs: [outFile], evidence_pointer: outFile,
  });
  const row = recordSpawn({ goal: 'g2', seat: 'delta', pid, start_time: null }, file);
  child.on('exit', () => {
    try {
      assert(!isAliveProcess(pid, row.start_time), 'the reaped process must be gone');
      assert(loadRegistry(file).length === 0, 'the registry row must be gone after the reap');
      const stored = store.api.getCurrentEnding({ goal: 'g2', seat: 'delta' });
      assert(stored.ending === 'done', `the seat's own done must stand, got ${stored.ending}`);
      pass('(d) a `done` checkout confirm-and-reaps: process gone, registry row gone, no `failed`');
    } catch (err) { fail('(d) done confirm-and-reap', err); }
    store.close();
    done();
  });
  try {
    const out = stampDeath({ goal: 'g2', seat: 'delta', pid, start_time: row.start_time },
      { store: store.api, registryFile: file });
    assert(out.act === 'confirm-and-reap', `expected confirm-and-reap, got ${out.act}`);
    assert(out.stamped === false, 'a done checkout must never be stamped `failed`');
    assert(out.signalled === true, 'a live process must be signalled by the reap');
  } catch (err) { fail('(d) done confirm-and-reap (stamp call)', err); child.kill('SIGKILL'); }
}

// -- (b) `incomplete` - the seat-declared ending STANDS, and the row is still reaped -------------
function caseIncompleteStands(done) {
  const store = freshStore();
  const file = regFile();
  store.api.stampSeatDeclare({
    goal: 'g3', seat: 'eps', ending: 'incomplete', diagnostic: 'context full',
    evidence_pointer: 'checkout:eps',
  });
  deadPid((pid) => {
    try {
      recordSpawn({ goal: 'g3', seat: 'eps', pid, start_time: '999' }, file);
      const out = stampDeath({ goal: 'g3', seat: 'eps', pid, start_time: '999' },
        { store: store.api, registryFile: file });
      assert(out.act === 'declared-ending-stands', `got ${out.act}`);
      assert(out.stamped === false, 'a declared incomplete is never overwritten by a crash stamp');
      assert(store.api.getCurrentEnding({ goal: 'g3', seat: 'eps' }).ending === 'incomplete',
        'the seat-declared incomplete must survive');
      assert(loadRegistry(file).length === 0, 'a declared ending is still owed its reap');
      pass('(b) an `incomplete` checkout stands and is reaped');
    } catch (err) { fail('(b) incomplete stands', err); }
    store.close();
    done();
  });
}

// -- (c) PROVIDER-SHAPED EVIDENCE CLASSIFIES `provider-error`, NOT `crash` ----------------------
function caseProviderShaped(done) {
  const store = freshStore();
  const file = regFile();
  deadPid((pid) => {
    try {
      assert(providerShaped('overloaded_error from the API') === true, 'marker must match');
      assert(providerShaped('Segmentation fault') === false, 'an ordinary crash is not a provider error');
      recordSpawn({ goal: 'g4', seat: 'zeta', pid, start_time: '999' }, file);
      const out = stampDeath({
        goal: 'g4', seat: 'zeta', pid, start_time: '999', checkedIn: true,
        exitCode: 1, detail: 'anthropic: overloaded_error (529)',
      }, { store: store.api, registryFile: file });
      assert(out.reason_class === 'provider-error', `got ${out.reason_class}`);
      assert(store.api.getCurrentEnding({ goal: 'g4', seat: 'zeta' }).reason_class === 'provider-error',
        'the stored reason class must be provider-error');
      pass('(c) provider-shaped evidence classifies `failed: provider-error`');
    } catch (err) { fail('(c) provider-shaped evidence', err); }
    store.close();
    done();
  });
}

// -- (e) A LIVE PROCESS THAT REFUSES THE SIGNAL IS NOT REAPED, AND THE DEBT STAYS VISIBLE --------
//
// FAIL-CLOSED, and this is the direction that matters: a row dropped for a process still running is
// a leak nobody can see afterwards, while an undropped row is exactly the reap debt `awaitingReap`
// reports. The terminate stub is injected so the refusal can be staged without an unkillable pid.
function caseReapRefusesWhileAlive(done) {
  const store = freshStore();
  const file = regFile();
  const child = liveChild();
  const row = recordSpawn({ goal: 'g5', seat: 'eta', pid: child.pid }, file);
  try {
    const out = confirmAndReap(row, { registryFile: file, terminate: () => {} });
    assert(out.reaped === false && out.rowDropped === false,
      'a still-live process must not have its row dropped');
    assert(loadRegistry(file).length === 1, 'the reap debt must stay on the books');
    pass('(e) a process that survives the reap signal keeps its registry row (fail-closed)');
  } catch (err) { fail('(e) reap refuses while alive', err); }
  child.kill('SIGKILL');
  child.on('exit', () => { store.close(); done(); });
}

// -- (f) THE KIT DOOR ANSWERS THE SAME WAY THE LIBRARY DOES -------------------------------------
//
// team-kit's python reaches this path through `cli.js`, so the door is asserted on the real
// subprocess: a door that agrees with the library in a unit test and disagrees on the wire is the
// two-answers-to-one-question shape this whole component exists to prevent.
function caseKitDoor(done) {
  const dbPath = path.join(fs.mkdtempSync(path.join(tmpRoot, 'door-')), 'heart.db');
  const file = regFile();
  deadPid((pid) => {
    try {
      recordSpawn({ goal: 'g6', seat: 'theta', pid, start_time: '999' }, file);
      const out = execFileSync(process.execPath, [
        path.join(__dirname, 'cli.js'), '--op', 'stampDeath', '--registry', file, '--db', dbPath,
        '--payload', JSON.stringify({ goal: 'g6', seat: 'theta', pid, start_time: '999', exitCode: 9 }),
      ], { encoding: 'utf8' });
      const parsed = JSON.parse(out);
      assert(parsed.ending === 'failed' && parsed.reason_class === 'crash',
        `the kit door must return failed/crash, got ${out}`);
      assert(loadRegistry(file).length === 0, 'the kit door must reap too');
      pass('(f) the kit door (`cli.js --op stampDeath`) answers failed:crash and reaps');
    } catch (err) { fail('(f) kit door', err); }
    done();
  });
}

const cases = [
  caseCrashBeforeCheckIn,
  caseCrashAfterCheckIn,
  caseDoneConfirmAndReap,
  caseIncompleteStands,
  caseProviderShaped,
  caseReapRefusesWhileAlive,
  caseKitDoor,
];

// The cases are asynchronous (real children, real exits), so they run in sequence rather than in
// parallel: a shared tmp root and a process-wide heart-store writer slot are not two-at-a-time safe.
function runNext(i) {
  if (i >= cases.length) {
    try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch { /* tmp */ }
    if (failed) {
      process.stdout.write(`${failed} FAIL\n`);
      process.exit(1);
    }
    process.stdout.write('ALL PASS\n');
    return;
  }
  try { cases[i](() => runNext(i + 1)); } catch (err) { fail(cases[i].name, err); runNext(i + 1); }
}

runNext(0);
