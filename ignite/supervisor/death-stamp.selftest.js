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

const {
  stampDeath, confirmAndReap, providerShaped, declaredEndingIsStale,
} = require('./death-stamp');
const { recordSpawn, loadRegistry, isAliveProcess } = require('./registry');
const { openHeartStore, closeHeartStore } = require('../state-store/heart/heart-store');
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

// -- (g)/(h)/(i) DEFECT A — A STALE `done` FROM AN EARLIER SITTING MUST NOT SWALLOW A LATER
// SITTING'S PROVIDER DEATH [the `stools-canvas-audio-elevenlabs-close` incident, 2026-08-28] -----
//
// The store's own key is `(goal, seat)`, never `(goal, seat, session)` - `seat_endings` has no
// session column at all (§1 schema: goal, seat, ending, ..., stamped_at). `sessions.csv`'s
// `started` column is the fallback source of a sitting's own identity, and `stampDeath` now reads
// it through `RBTV_IGNITE_WORKSPACE_ROOT` - the same env var the daemon's own unit sets and every
// closer it spawns inherits (`runtime/index.js` reads the identical name).
function writeSessionsCsv(goalFolder, rows) {
  const dir = path.join(goalFolder, 'coordination');
  fs.mkdirSync(dir, { recursive: true });
  const header = 'session-id,seat,started';
  const lines = rows.map((r) => `${r.session},${r.seat},${r.started}`);
  fs.writeFileSync(path.join(dir, 'sessions.csv'), `${header}\n${lines.join('\n')}\n`, 'utf8');
}

function withWorkspaceRoot(root, fn) {
  const prev = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  process.env.RBTV_IGNITE_WORKSPACE_ROOT = root;
  try { return fn(); } finally {
    if (prev === undefined) delete process.env.RBTV_IGNITE_WORKSPACE_ROOT;
    else process.env.RBTV_IGNITE_WORKSPACE_ROOT = prev;
  }
}

// -- (g) THE LIVE INCIDENT, REPRODUCED OFFLINE — a stale `done` is overridden by the 429 --------
function caseStaleDoneOverriddenByProvider(done) {
  const store = freshStore();
  const file = regFile();
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'ws-'));
  const goalFolder = path.join(workspaceRoot, '.rbtv', 'goals', 'stools-canvas-audio-elevenlabs-close');
  fs.mkdirSync(goalFolder, { recursive: true });
  // Sitting 9 checked out `done` at 22:10:11 (an EARLIER sitting of the same seat).
  const outFile = path.join(tmpRoot, 'iota-declared.txt');
  fs.writeFileSync(outFile, 'work', 'utf8');
  store.api.stampSeatDeclare({
    goal: 'stools-canvas-audio-elevenlabs-close', seat: 'leader', ending: 'done',
    declared_outputs: [outFile], evidence_pointer: outFile,
    stamped_at: '2026-08-28T22:10:11.000Z',
  });
  // Sitting 10 is a LATER sitting of the SAME seat: sessions.csv names it and its own start,
  // AFTER the stale `done` above.
  writeSessionsCsv(goalFolder, [
    { session: 'b6731ba8-sitting10', seat: 'leader', started: '2026-08-28 22:17' },
  ]);
  deadPid((pid) => {
    try {
      recordSpawn({ goal: 'stools-canvas-audio-elevenlabs-close', seat: 'leader', pid, start_time: '999' }, file);
      const out = withWorkspaceRoot(workspaceRoot, () => stampDeath({
        goal: 'stools-canvas-audio-elevenlabs-close',
        seat: 'leader',
        pid,
        start_time: '999',
        session: 'b6731ba8-sitting10',
        checkedIn: true,
        exitCode: 1,
        detail: 'You\'ve hit your session limit · api_error_status:429 rate_limit',
      }, { store: store.api, registryFile: file }));
      assert(out.act === 'stamped', `stale done must NOT confirm-and-reap, got act=${out.act}`);
      assert(out.stamped === true, 'the later sitting\'s death must be stamped');
      assert(out.ending === 'failed', `expected failed, got ${out.ending}`);
      assert(out.reason_class === 'provider-error', `expected provider-error, got ${out.reason_class}`);
      const row = store.api.getCurrentEnding({ goal: 'stools-canvas-audio-elevenlabs-close', seat: 'leader' });
      assert(row.ending === 'failed' && row.reason_class === 'provider-error',
        `stored ending must be failed/provider-error, got ${row.ending}/${row.reason_class}`);
      pass('(g) a LATER sitting dying on a 429 overrides an EARLIER sitting\'s stale `done` -> failed:provider-error');
    } catch (err) { fail('(g) stale done overridden by provider death', err); }
    store.close();
    done();
  });
}

// -- (h) THE ORIGINAL CASE STILL STANDS — the SAME sitting's own `done` is still confirm-and-reaped
function caseSameSittingDoneStillStands(done) {
  const store = freshStore();
  const file = regFile();
  const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'ws-'));
  const goalFolder = path.join(workspaceRoot, '.rbtv', 'goals', 'g8');
  fs.mkdirSync(goalFolder, { recursive: true });
  // This sitting started FIRST, then declared `done` — its own declaration, stamped AFTER its
  // own start, exactly the ordinary shape every real sitting has.
  writeSessionsCsv(goalFolder, [{ session: 'sess-same', seat: 'kappa', started: '2026-08-28 09:00' }]);
  const outFile = path.join(tmpRoot, 'kappa-declared.txt');
  fs.writeFileSync(outFile, 'work', 'utf8');
  store.api.stampSeatDeclare({
    goal: 'g8', seat: 'kappa', ending: 'done',
    declared_outputs: [outFile], evidence_pointer: outFile,
    stamped_at: '2026-08-28T09:05:00.000Z',
  });
  const child = liveChild();
  const pid = child.pid;
  const row = recordSpawn({ goal: 'g8', seat: 'kappa', pid, start_time: null }, file);
  child.on('exit', () => {
    try {
      const stored = store.api.getCurrentEnding({ goal: 'g8', seat: 'kappa' });
      assert(stored.ending === 'done', `the seat's own done must still stand, got ${stored.ending}`);
      pass('(h) the ORIGINAL case (same sitting checked out done, then reaped) still -> confirm-and-reap');
    } catch (err) { fail('(h) same-sitting done still stands', err); }
    store.close();
    done();
  });
  try {
    const out = withWorkspaceRoot(workspaceRoot, () => stampDeath({
      goal: 'g8', seat: 'kappa', pid, start_time: row.start_time, session: 'sess-same',
    }, { store: store.api, registryFile: file }));
    assert(out.act === 'confirm-and-reap', `expected confirm-and-reap, got ${out.act}`);
    assert(out.stamped === false, 'the seat\'s own done must never be stamped over');
  } catch (err) { fail('(h) same-sitting done (stamp call)', err); child.kill('SIGKILL'); }
}

// -- (i) RED MUTATION — reverting `declaredEndingIsStale` to always `false` reproduces the incident
function caseRedMutationStaleGuard(doneCb) {
  try {
    const src = fs.readFileSync(path.join(__dirname, 'death-stamp.js'), 'utf8');
    const ANCHOR = 'function declaredEndingIsStale(current, evidence) {';
    assert(src.includes(ANCHOR), 'declaredEndingIsStale anchor missing');
    const mutatedSrc = src.replace(ANCHOR, `${ANCHOR}\n  return false; // eslint-disable-line no-unreachable`);
    const Module = require('node:module');
    const mut = new Module(path.join(__dirname, 'death-stamp.js'), null);
    mut.filename = path.join(__dirname, 'death-stamp.js');
    mut.paths = Module._nodeModulePaths(__dirname);
    mut._compile(mutatedSrc, mut.filename);

    const store = freshStore();
    const file = regFile();
    const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'ws-'));
    const goalFolder = path.join(workspaceRoot, '.rbtv', 'goals', 'g9');
    fs.mkdirSync(goalFolder, { recursive: true });
    writeSessionsCsv(goalFolder, [{ session: 'sess-new9', seat: 'mu', started: '2026-08-28 22:17' }]);
    const outFile = path.join(tmpRoot, 'mu-declared.txt');
    fs.writeFileSync(outFile, 'work', 'utf8');
    store.api.stampSeatDeclare({
      goal: 'g9', seat: 'mu', ending: 'done', declared_outputs: [outFile], evidence_pointer: outFile,
      stamped_at: '2026-08-28T22:10:11.000Z',
    });
    recordSpawn({ goal: 'g9', seat: 'mu', pid: process.pid, start_time: '999' }, file);
    const out = withWorkspaceRoot(workspaceRoot, () => mut.exports.stampDeath({
      goal: 'g9', seat: 'mu', pid: process.pid, start_time: '999', session: 'sess-new9',
      checkedIn: true, exitCode: 1, detail: 'http 429 rate_limit',
    }, { store: store.api, registryFile: file, terminate: () => {} }));
    assert(out.act === 'confirm-and-reap',
      `RED: with the guard reverted the stale done must wrongly stand (confirm-and-reap), got ${out.act}`);
    assert(out.stamped === false, 'RED: the mutant must reproduce the incident - no failed stamp');
    pass('(i) RED proof: reverting `declaredEndingIsStale` reproduces the incident (confirm-and-reap swallows the 429)');
    store.close();
    doneCb();
  } catch (err) { fail('(i) red mutation for the stale-done guard', err); doneCb(); }
}

// -- direct unit checks on `declaredEndingIsStale` itself, no store/process involved -------------
function checkDeclaredEndingIsStaleUnit() {
  try {
    const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'ws-unit-'));
    const goalFolder = path.join(workspaceRoot, '.rbtv', 'goals', 'g-unit');
    fs.mkdirSync(goalFolder, { recursive: true });
    writeSessionsCsv(goalFolder, [{ session: 'sess-unit', seat: 'nu', started: '2026-08-28 22:17' }]);
    withWorkspaceRoot(workspaceRoot, () => {
      const stale = declaredEndingIsStale(
        { stamped_at: '2026-08-28T22:10:11.000Z' },
        { goal: 'g-unit', session: 'sess-unit' },
      );
      assert(stale === true, 'a done stamped BEFORE the sitting started must be stale');
      const notStale = declaredEndingIsStale(
        { stamped_at: '2026-08-28T22:20:00.000Z' },
        { goal: 'g-unit', session: 'sess-unit' },
      );
      assert(notStale === false, 'a done stamped AFTER the sitting started must stand');
      const noSession = declaredEndingIsStale(
        { stamped_at: '2026-08-28T22:10:11.000Z' },
        { goal: 'g-unit' },
      );
      assert(noSession === false, 'no session in evidence -> cannot prove staleness -> stands');
    });
    pass('(unit) declaredEndingIsStale: before-start is stale, after-start stands, no-session stands');
  } catch (err) { fail('(unit) declaredEndingIsStale', err); }
}
checkDeclaredEndingIsStaleUnit();

// d-overlap-row-close: `declaredEndingIsStale` reads `started` off `sessions.csv` — a naive
// `YYYY-MM-DD HH:MM` local wall-clock string, no offset marker — and compares it against
// `stamped_at`, an ISO string with an explicit `Z`. Every unit check above runs in THIS process,
// which inherits the box's own timezone (`Etc/UTC`) — so a guard that silently mis-parsed
// `started` as UTC would still measure correct here, exactly the vacuous-check shape this run has
// already hit twice. This arm forces a NON-UTC offset (`America/New_York`, TZ env only takes
// effect in a fresh process) and re-derives what "before start" / "after start" mean in THAT
// zone, so a guard that dropped back to `Date.parse`'s implementation-defined parsing of the
// space-separated format would be caught the moment it disagreed with the constructor-based
// arithmetic below — not merely "trusted to already agree".
function checkDeclaredEndingIsStaleNonUtcTz() {
  try {
    const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'ws-tz-'));
    const goalFolder = path.join(workspaceRoot, '.rbtv', 'goals', 'g-tz');
    fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
    // The sitting's own boot, written the way `records.py#now()` actually writes it: a naive
    // local clock reading, no offset.
    const startedLocal = '2026-08-28 22:17';
    fs.writeFileSync(
      path.join(goalFolder, 'coordination', 'sessions.csv'),
      'session-id,seat,started\nsess-tz,xi,2026-08-28 22:17\n', 'utf8',
    );
    // Independently derived, in THIS (UTC) process, what that wall-clock reading means under
    // America/New_York (UTC-4 in August, EDT) — the arithmetic the guard must reproduce without
    // ever running in that zone itself.
    const [y, mo, d] = [2026, 8, 28];
    const [h, mi] = [22, 17];
    const startedUtcMs = Date.UTC(y, mo - 1, d, h + 4, mi); // EDT = UTC-4
    const beforeIso = new Date(startedUtcMs - 5 * 60 * 1000).toISOString();  // 5 min before start
    const afterIso = new Date(startedUtcMs + 5 * 60 * 1000).toISOString();   // 5 min after start

    const script = `
      process.env.RBTV_IGNITE_WORKSPACE_ROOT = ${JSON.stringify(workspaceRoot)};
      const { declaredEndingIsStale } = require(${JSON.stringify(path.join(__dirname, 'death-stamp.js'))});
      const stale = declaredEndingIsStale({ stamped_at: ${JSON.stringify(beforeIso)} }, { goal: 'g-tz', session: 'sess-tz' });
      const stands = declaredEndingIsStale({ stamped_at: ${JSON.stringify(afterIso)} }, { goal: 'g-tz', session: 'sess-tz' });
      process.stdout.write(JSON.stringify({ stale, stands }));
    `;
    const out = execFileSync(process.execPath, ['-e', script], {
      env: { ...process.env, TZ: 'America/New_York' }, encoding: 'utf8',
    });
    const { stale, stands } = JSON.parse(out);
    assert(stale === true,
      `under a non-UTC offset, a done stamped BEFORE the sitting's local start must be stale ` +
      `(started=${startedLocal} America/New_York, stamped=${beforeIso}), got stale=${stale}`);
    assert(stands === false,
      `under a non-UTC offset, a done stamped AFTER the sitting's local start must stand ` +
      `(started=${startedLocal} America/New_York, stamped=${afterIso}), got stands=${stands}`);
    pass('(tz) declaredEndingIsStale decides correctly under a non-UTC (America/New_York) offset');
  } catch (err) { fail('(tz) declaredEndingIsStale under non-UTC offset', err); }
}
checkDeclaredEndingIsStaleNonUtcTz();

const cases = [
  caseCrashBeforeCheckIn,
  caseCrashAfterCheckIn,
  caseDoneConfirmAndReap,
  caseIncompleteStands,
  caseProviderShaped,
  caseReapRefusesWhileAlive,
  caseKitDoor,
  caseStaleDoneOverriddenByProvider,
  caseSameSittingDoneStillStands,
  caseRedMutationStaleGuard,
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
