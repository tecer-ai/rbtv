'use strict';

// -- DOOR FIXTURES - wrapped vs marked-unsupervised vs refused [T4-R7, T4-R8, C-15] --------------
//
// Three claims, one per arm of the door list, and every one of them on a REAL child process: a
// fabricated pid proves nothing about a probe whose job is to read the live process table.
//
//   (a) WRAPPED        - a launch arriving through a wrapped door's launcher lands a SUPERVISED
//                        registry row, and the sitting probes alive. The control is the same
//                        launch with an unrecognised launcher: it is still recorded, flagged
//                        `unsupervised`. Without the control this row could not tell a door list
//                        that classifies from one that writes `supervised` on everything.
//   (b) UNSUPERVISED   - the console-uncaged door is MARKED, never silently live: before any row
//                        exists the probe answers `alive: null` + `supervised: false` (and never
//                        `true`), the marked row answers `supervised: false` while genuinely
//                        running, and check-in FLIPS it to supervised. Three states, because the
//                        defect is the middle one reading as either of the other two.
//   (c) REFUSAL        - `E_GOAL_NOT_LIVE` refuses with NO process, NO stamp and NO enqueue. The
//                        registry file is asserted ABSENT afterwards rather than merely rowless:
//                        a refusal that creates its own empty file has still touched the surface
//                        it was supposed to leave alone.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');

const doors = require('./doors');
const { loadRegistry, SUPERVISED, UNSUPERVISED } = require('./registry');
const { probeSitting } = require('./probe');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'supervisor-doors-'));
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
function liveChild() {
  return spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { stdio: 'ignore' });
}

// -- (a) A WRAPPED DOOR LAUNCHES THROUGH SUPERVISOR SPAWN, AND THE ROW APPEARS -------------------
function caseWrappedDoorsRegister() {
  const file = regFile();
  const kids = [];
  try {
    // Driven off the door list itself rather than a hand-typed list of three names: a door added to
    // the table with no wiring must redden here rather than be quietly untested.
    const wrapped = Object.values(doors.DOORS).filter((d) => d.disposition === doors.WRAPPED && d.launcher);
    assert(wrapped.length >= 3, `expected the three launching wrapped doors, got ${wrapped.length}`);
    for (const row of wrapped) {
      const child = liveChild();
      kids.push(child);
      // The launcher is what the launch already carries (`enqueued_by` / the `--rerun` reason
      // token) - the door name is DERIVED from it, never passed separately by the caller.
      const carried = row.door === 'rerun' ? `${row.launcher}-p-1234-anchor` : row.launcher;
      const rec = doors.superviseSpawn({
        launcher: carried, goal: 'g', seat: row.door, pid: child.pid, launch_token: `tok-${row.door}`,
      }, file);
      assert(rec.door === row.door, `${row.door}: launcher ${carried} resolved to ${rec.door}`);
      assert(rec.supervision === SUPERVISED, `${row.door}: row is ${rec.supervision}, not supervised`);
      const probed = probeSitting({ goal: 'g', seat: row.door }, file);
      assert(probed.supervised === true && probed.alive === true,
        `${row.door}: probe answered ${JSON.stringify(probed)}`);
    }
    assert(loadRegistry(file).length === wrapped.length,
      `expected ${wrapped.length} rows, got ${loadRegistry(file).length}`);

    // THE CONTROL. Same call, a launcher no door claims: recorded, and flagged unsupervised.
    const stray = liveChild();
    kids.push(stray);
    const adhoc = doors.superviseSpawn({ launcher: 'some-ad-hoc-caller', goal: 'g', seat: 'stray', pid: stray.pid }, file);
    assert(adhoc.door === null && adhoc.supervision === UNSUPERVISED,
      `an unmapped launcher must be MARKED, not supervised: ${JSON.stringify(adhoc)}`);
    pass('(a) every wrapped door lands a SUPERVISED registry row; an unmapped launcher is marked instead');
  } finally {
    for (const k of kids) { try { k.kill('SIGKILL'); } catch { /* gone */ } }
  }
}

// -- (b) THE UNSUPERVISED DOOR IS MARKED, AND NEVER SILENTLY LIVE -------------------------------
function caseConsoleUncagedIsMarked() {
  const file = regFile();
  const child = liveChild();
  try {
    assert(doors.DOORS['console-uncaged'].disposition === doors.MARKED_UNSUPERVISED,
      'console-uncaged must be marked-unsupervised in the door list');

    // (i) Before anything is written the sitting is UNSUPERVISED and its liveness is UNKNOWN -
    // never `true` (that is the pane's answer) and never `false` (that is the mass-restamp hole).
    const unknown = probeSitting({ goal: 'g', seat: 'console' }, file);
    assert(unknown.supervised === false && unknown.alive === null,
      `an unregistered sitting must read {supervised:false, alive:null}: ${JSON.stringify(unknown)}`);

    // (ii) Marked while genuinely running: the process IS alive and the row still says unsupervised.
    doors.markUnsupervised({ goal: 'g', seat: 'console', pid: child.pid }, file);
    const marked = probeSitting({ goal: 'g', seat: 'console' }, file);
    assert(marked.alive === true, 'the marked sitting is a live process and must probe alive');
    assert(marked.supervised === false, 'a marked row must NOT read supervised before check-in');

    // (iii) Check-in is the flip, and it is the ONLY thing that performs it.
    doors.registerCheckIn({ goal: 'g', seat: 'console', pid: child.pid, launch_token: 'tok' }, file);
    const after = probeSitting({ goal: 'g', seat: 'console' }, file);
    assert(after.supervised === true && after.alive === true,
      `check-in must flip unsupervised -> supervised: ${JSON.stringify(after)}`);
    assert(loadRegistry(file).length === 1, 'check-in must FLIP the row, never add a second one');
    pass('(b) console-uncaged is marked unsupervised, never silently live, and check-in flips it');
  } finally {
    try { child.kill('SIGKILL'); } catch { /* gone */ }
  }
}

// -- (c) E_GOAL_NOT_LIVE REFUSES: NO PROCESS, NO STAMP, NO ENQUEUE ------------------------------
function caseGoalNotLiveRefuses() {
  const file = regFile();
  const refusal = doors.refuseLaunch({
    door: 'goal-not-live', goal: 'g', seat: 'alpha',
    evidence: 'goal g has NO live room (tmux session named `g`)',
  });
  assert(refusal.refused === true, 'the door must answer a refusal');
  assert(refusal.code === 'E_GOAL_NOT_LIVE', `wrong code: ${refusal.code}`);
  assert(refusal.spawned === false && refusal.stamped === false && refusal.enqueued === false,
    `all three must be false: ${JSON.stringify(refusal)}`);
  // Asserted ABSENT, not merely empty: a refusal that creates its own file has touched the
  // liveness surface, and the next boot re-adopt would read that file as the whole truth.
  assert(!fs.existsSync(file), 'a refusal must write NO registry file at all');
  assert(refusal.evidence.includes('NO live room'), 'the refusal must carry the evidence it refused on');
  pass('(c) E_GOAL_NOT_LIVE refuses with no process, no stamp, no enqueue, and no registry write');
}

// -- (d) THE DOOR LIST IS THE SPEC'S TABLE, WITH NO SEVENTH ROW ---------------------------------
function caseDoorListMatchesSpec() {
  const names = Object.keys(doors.DOORS).sort();
  const expected = ['attest-exit', 'console-uncaged', 'goal-not-live', 'reconcile', 'rerun', 'seeding'];
  assert(JSON.stringify(names) === JSON.stringify(expected),
    `the door list must be spec-supervisor section 3's six rows: got ${JSON.stringify(names)}`);
  const marked = names.filter((n) => doors.DOORS[n].disposition === doors.MARKED_UNSUPERVISED);
  assert(JSON.stringify(marked) === JSON.stringify(['console-uncaged']),
    `exactly one row is marked-unsupervised: got ${JSON.stringify(marked)}`);
  pass('(d) the door list carries spec-supervisor section 3 exactly - six rows, one of them marked');
}

const cases = [
  caseWrappedDoorsRegister,
  caseConsoleUncagedIsMarked,
  caseGoalNotLiveRefuses,
  caseDoorListMatchesSpec,
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
