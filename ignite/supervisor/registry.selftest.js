'use strict';

// -- SELFTESTS FOR THE SUPERVISOR REGISTRY + BOOT RE-ADOPT --------------------------------------
//
// The two load-bearing cases are (b) and (c), and both use REAL processes: a fake pid proves
// nothing about a probe whose whole job is to read the live process table.
//
//   (b) re-adopt        - a persisted row for a genuinely live child survives a simulated watchdog
//                         restart (the module state is dropped and the file is re-read from disk).
//                         It lands in `adopted`, not in `dead`, and nothing is stamped for it.
//   (c) mass-restamp    - the regression that names this module's reason to exist: an EMPTY
//       regression       registry while live processes are running yields ZERO `failed` stamps.
//                         The assertion is on the STAMP COUNT, not on a message, because the
//                         incident was a count: every live seat stamped at once.
//
// The stamper here is a counting stub on purpose. The real stamp is the death-stamp seat's act;
// what this file has to prove is that the re-adopt pass hands it NOTHING to stamp in the two
// situations that used to hand it everything.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'supervisor-registry-'));
let failed = 0;

function pass(name) { process.stdout.write(`PASS ${name}\n`); }
function fail(name, err) {
  failed += 1;
  process.stdout.write(`FAIL ${name}: ${err && err.stack ? err.stack : err}\n`);
}

function regFile(name) {
  return path.join(fs.mkdtempSync(path.join(tmpRoot, 'r-')), name || 'registry.jsonl');
}

// A real child that stays alive until we kill it, and whose pid+start-time pair is therefore a real
// entry in the live process table.
function liveChild() {
  const child = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { stdio: 'ignore' });
  return child;
}

// A killed child of THIS process stays a ZOMBIE until node's SIGCHLD handler collects it, and this
// file is synchronous throughout, so the event loop never gets the chance: `kill(pid, 0)` on it
// would succeed forever. The wait therefore asks the module's own probe, which is the fact under
// test - and a zombie answering "alive" here would be the defect, not a flaky fixture.
function waitGone(isAliveProcess, pid, start, deadlineMs = 5000) {
  const until = Date.now() + deadlineMs;
  while (Date.now() < until) {
    if (!isAliveProcess(pid, start)) return true;
  }
  return false;
}

// A stamper that only counts. Any call is a stamp that the incident says must not happen.
function makeStamper() {
  const calls = [];
  return {
    calls,
    stampFailed(row) { calls.push(row); },
  };
}

// Every case re-requires the module through a cleared cache, which is what "the watchdog restarted"
// means at this level: no in-memory state carries over, only the file on disk.
function freshModule() {
  for (const key of Object.keys(require.cache)) {
    if (key.startsWith(__dirname + path.sep) && !key.endsWith('registry.selftest.js')) {
      delete require.cache[key];
    }
  }
  return require('./index');
}

// -- (a) the four write moments, the probe, and the shapes they persist -------------------------

function caseWriteMoments() {
  const sup = freshModule();
  const file = regFile();
  const child = liveChild();
  try {
    const row = sup.recordSpawn({
      goal: 'g', seat: 'alpha', pid: child.pid, launch_token: 'tok-1',
    }, file);
    if (row.pid !== child.pid) throw new Error('spawn row lost the pid');
    if (!row.start_time) throw new Error('spawn row persisted no start-time');
    if (row.launch_token !== 'tok-1') throw new Error('spawn row lost the launch token');
    if (row.supervision !== sup.SUPERVISED) throw new Error('spawn row is not supervised');

    const lines = fs.readFileSync(file, 'utf8').trim().split('\n');
    if (lines.length !== 1) throw new Error(`expected one JSONL line, got ${lines.length}`);
    JSON.parse(lines[0]);

    // (ii) check-in of an outside-daemon seat: insert as unsupervised, then flip.
    sup.recordCheckIn({
      goal: 'g', seat: 'beta', pid: child.pid, supervision: sup.UNSUPERVISED,
    }, file);
    const beta = sup.loadRegistry(file).find((r) => r.seat === 'beta');
    if (beta.supervision !== sup.UNSUPERVISED) throw new Error('insert did not honour the unsupervised flag');
    const flipped = sup.recordCheckIn({ goal: 'g', seat: 'beta', pid: child.pid }, file);
    if (flipped.supervision !== sup.SUPERVISED) throw new Error('check-in did not flip unsupervised to supervised');

    // (iii) drop after a stamped ending + successful reap.
    if (sup.dropRow({ goal: 'g', seat: 'beta' }, file) !== true) throw new Error('dropRow did not drop');
    if (sup.loadRegistry(file).some((r) => r.seat === 'beta')) throw new Error('dropped row is still there');
    if (sup.dropRow({ goal: 'g', seat: 'nobody' }, file) !== false) throw new Error('dropRow invented a drop');

    pass('write moments persist pid + start-time + launch-token, flip, and drop');
  } finally { child.kill('SIGKILL'); }
}

function caseProbe() {
  const sup = freshModule();
  const child = liveChild();
  try {
    const start = sup.processStartTime(child.pid);
    if (!start) throw new Error('no /proc start-time for a live child');
    if (!sup.isAliveProcess(child.pid, start)) throw new Error('live child probed as dead');
    // A pid whose start-time does not match is a RECYCLED pid, not the process the row named.
    if (sup.isAliveProcess(child.pid, String(Number(start) + 999))) {
      throw new Error('start-time mismatch probed as alive');
    }
    // A killed-but-unreaped child is a ZOMBIE: it still answers kill(pid,0) and still carries the
    // same start-time, and it has EXITED. The probe must say dead, or a finished seat is alive
    // forever and can never be stamped.
    child.kill('SIGKILL');
    if (!waitGone(sup.isAliveProcess, child.pid, start)) throw new Error('zombie child probed as alive');
    if (!sup.isZombie(child.pid) && sup.processStartTime(child.pid)) {
      throw new Error('fixture never reached the zombie state the assertion is about');
    }
  } finally { child.kill('SIGKILL'); }
  pass('probe is kill(pid,0) + start-time match + not-a-zombie; mismatch and zombie are not alive');
}

// -- (b) RE-ADOPT: a persisted live pid + start-time survives a simulated restart ---------------

function caseReadoptSurvivesRestart() {
  const file = regFile();
  const child = liveChild();
  const stamper = makeStamper();
  try {
    // Before the "restart": the spawn door persists the row.
    const before = freshModule();
    before.recordSpawn({ goal: 'g', seat: 'survivor', pid: child.pid, launch_token: 'tok-b' }, file);

    // The restart. Nothing in memory carries over; the file is the only thing that does.
    const after = freshModule();
    const result = after.readopt(file);

    if (result.registryEmpty) throw new Error('registry read as empty after a persisted spawn');
    if (result.adopted.length !== 1) {
      throw new Error(`expected 1 adopted row, got ${result.adopted.length}`);
    }
    if (result.adopted[0].seat !== 'survivor') throw new Error('adopted the wrong row');
    if (result.adopted[0].launch_token !== 'tok-b') throw new Error('re-adopt lost the launch token');
    if (result.dead.length !== 0) throw new Error(`live seat classified dead: ${JSON.stringify(result.dead)}`);

    // What a stamping caller would do with this result: stamp the dead set. It is empty.
    for (const row of result.dead) stamper.stampFailed(row);
    if (stamper.calls.length !== 0) {
      throw new Error(`stamp-count must be 0 for a re-adopted live seat, got ${stamper.calls.length}`);
    }

    // And the row is still on disk: re-adopt writes nothing, so the sitting stays supervised.
    if (after.loadRegistry(file).length !== 1) throw new Error('re-adopt mutated the registry file');

    // Now the process really ends - the SAME row must classify dead, or the probe proves nothing.
    const startBefore = after.processStartTime(child.pid);
    child.kill('SIGKILL');
    if (!waitGone(after.isAliveProcess, child.pid, startBefore)) throw new Error('child did not exit');
    const post = freshModule().readopt(file);
    if (post.dead.length !== 1 || post.adopted.length !== 0) {
      throw new Error(`a truly dead pid must classify dead: ${JSON.stringify(post)}`);
    }
    pass('(b) re-adopt: persisted live pid+start-time survives a restart, 0 stamps; a real death still classifies dead');
  } finally { try { child.kill('SIGKILL'); } catch { /* already gone */ } }
}

function caseReadoptRejectsRecycledPid() {
  const file = regFile();
  const child = liveChild();
  try {
    const sup = freshModule();
    const row = sup.makeRecord({ goal: 'g', seat: 'recycled', pid: child.pid, launch_token: 'tok-r' });
    // The pid is live but a DIFFERENT process now holds it.
    sup.saveRegistry([{ ...row, start_time: String(Number(row.start_time) + 4242) }], file);
    const result = freshModule().readopt(file);
    if (result.dead.length !== 1 || result.adopted.length !== 0) {
      throw new Error(`a recycled pid must classify dead: ${JSON.stringify(result)}`);
    }
    pass('re-adopt refuses a recycled pid (start-time mismatch)');
  } finally { child.kill('SIGKILL'); }
}

// -- (c) MASS-RESTAMP REGRESSION: empty registry + live processes => ZERO failed stamps ---------

function caseMassRestampRegression() {
  const children = [liveChild(), liveChild(), liveChild()];
  const stamper = makeStamper();
  try {
    for (const c of children) {
      if (!process.kill(c.pid, 0) === false) { /* touch the pid so a dead fixture fails loudly */ }
    }
    const sup = freshModule();

    // Two spellings of "the registry is empty", both legal, both the fresh-boot case.
    const missing = regFile('absent.jsonl');            // never created
    const emptyFile = regFile('empty.jsonl');
    fs.writeFileSync(emptyFile, '', 'utf8');

    for (const [label, file] of [['absent', missing], ['empty', emptyFile]]) {
      const result = sup.readopt(file);
      if (!result.registryEmpty) throw new Error(`${label} registry did not read as empty`);
      if (result.rows.length !== 0) throw new Error(`${label} registry produced rows`);
      if (result.adopted.length !== 0) throw new Error(`${label} registry adopted something`);
      // THE ASSERTION. Every dead row is what a caller would stamp; there must be none, so the
      // stamp count after driving the stamper off this result must be exactly 0.
      for (const row of result.dead) stamper.stampFailed(row);
      if (stamper.calls.length !== 0) {
        throw new Error(`stamp-count must be 0 on an ${label} registry, got ${stamper.calls.length}`);
      }
    }

    // And the live processes are STILL live - the pass did not touch them, and rule 3 says a live
    // process with no row is not `failed`. Nothing enumerated them, so nothing could stamp them.
    for (const c of children) {
      if (!sup.isAliveProcess(c.pid, sup.processStartTime(c.pid))) {
        throw new Error('a live fixture process died during the pass - the fixture is not sound');
      }
    }
    if (stamper.calls.length !== 0) throw new Error('stamps appeared after the pass');
    process.stdout.write(`  stamp-count=${stamper.calls.length} live-processes=${children.length}\n`);
    pass('(c) mass-restamp regression: empty registry + 3 live processes => stamp-count == 0');
  } finally { for (const c of children) { try { c.kill('SIGKILL'); } catch { /* gone */ } } }
}

// -- the ordering guard and the reap-debt surface -----------------------------------------------

function caseStampBeforeReadoptIsRefused() {
  const sup = freshModule();
  let threw = null;
  try { sup.assertReadoptDone(undefined); } catch (err) { threw = err; }
  if (!threw || !/before boot re-adopt/.test(threw.message)) {
    throw new Error('a caller that never ran re-adopt was not refused');
  }
  sup.assertReadoptDone(sup.readopt(regFile()));
  pass('stamping before the re-adopt pass is refused; after it is admitted');
}

function caseAwaitingReap() {
  const sup = freshModule();
  const file = regFile();
  const child = liveChild();
  try {
    sup.recordSpawn({ goal: 'g', seat: 'stamped', pid: child.pid, launch_token: 't1' }, file);
    sup.recordSpawn({ goal: 'g', seat: 'running', pid: child.pid, launch_token: 't2' }, file);
    // The injected ending lookup stands in for the ending store: only `stamped` carries an ending.
    const debts = sup.awaitingReap((row) => row.seat === 'stamped', file);
    if (debts.length !== 1 || debts[0].seat !== 'stamped') {
      throw new Error(`reap debt must be the stamped-but-unreaped row, got ${JSON.stringify(debts)}`);
    }
    if (debts[0].alive !== true) throw new Error('reap debt did not carry live-ness');
    // After the reap completes, write moment (iii) clears the debt.
    sup.dropRow({ goal: 'g', seat: 'stamped' }, file);
    if (sup.awaitingReap(() => true, file).some((r) => r.seat === 'stamped')) {
      throw new Error('a reaped row is still a debt');
    }
    pass('reap debt = a row still present whose sitting already carries an ending');
  } finally { child.kill('SIGKILL'); }
}

function caseTornLineDoesNotEmptyTheRegistry() {
  const sup = freshModule();
  const file = regFile();
  const child = liveChild();
  try {
    sup.recordSpawn({ goal: 'g', seat: 'good', pid: child.pid, launch_token: 't' }, file);
    fs.appendFileSync(file, '{ not json\n', 'utf8');
    const result = sup.readopt(file);
    if (result.adopted.length !== 1) throw new Error('a torn line cost a live seat its re-adoption');
    pass('a torn JSONL line is skipped, not read as an empty registry');
  } finally { child.kill('SIGKILL'); }
}

const cases = [
  caseWriteMoments,
  caseProbe,
  caseReadoptSurvivesRestart,
  caseReadoptRejectsRecycledPid,
  caseMassRestampRegression,
  caseStampBeforeReadoptIsRefused,
  caseAwaitingReap,
  caseTornLineDoesNotEmptyTheRegistry,
];

for (const fn of cases) {
  try { fn(); } catch (err) { fail(fn.name, err); }
}

try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch { /* tmp */ }

if (failed) {
  process.stdout.write(`${failed} FAIL\n`);
  process.exit(1);
}
process.stdout.write('ALL PASS\n');
