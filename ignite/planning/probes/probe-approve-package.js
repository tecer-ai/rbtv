'use strict';

// probe-approve-package — THE WRITER OF `planning/approve-package.json`, AND THE FOURTEENTH
// INTENT'S GATE TRANSITIONING BECAUSE OF IT.
//
// WHAT THIS PROBE IS FOR. The fourteenth gateway intent (`start-execution`, owner ruling
// 2026-08-24 option (b)) reads an approve-package on the planning goal to learn what the owner
// approved, and until this landing NOTHING wrote one — every genuine `approve` refused
// `no-approve-package`. `probe-start-execution` proves the gate refuses; it hand-writes its
// package with `fs.writeFileSync`, so it cannot prove that the REAL writer produces something the
// REAL reader admits. That join is the only thing this probe measures, and it measures it by
// running the actual `approve_package.py` subprocess against the actual `startExecution`.
//
// evidence-class: FIXTURE. A scratch workspace root, a scratch ending store, the real python
// writer, the real daemon-side reader; the Path-B birth itself is INJECTED, so nothing here
// scaffolds a goal, spawns git, or touches the live goals tree. NEVER run against the daemon.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const outPath = path.join(__dirname, 'probe-approve-package.out');
fs.writeFileSync(outPath, '');

const { startExecution, APPROVE_PACKAGE } = require('../../state-store/heart/start-execution');
const { openEndingStore, bind } = require('../../state-store');
const { requirePythonCmd } = require('../../runtime/python-cmd');

const WRITER = path.join(__dirname, '..', 'approve_package.py');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const GOAL = 'plan-goal';
const SEAT = 'plan-verifier';
const THREAD = '1724508123.123456';
const COMMIT = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678';
const EXEC_GOAL = 'born-exec-goal';

function runWriter(args) {
  try {
    const stdout = execFileSync(requirePythonCmd(), ['-B', WRITER, ...args], {
      encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
    });
    return { code: 0, stdout };
  } catch (err) {
    return { code: err.status, stdout: String(err.stdout || ''), stderr: String(err.stderr || '') };
  }
}

function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out('evidence-class: FIXTURE scratch workspace + scratch ending store; the REAL python writer and'
    + ' the REAL daemon-side reader; the Path-B birth is INJECTED (never spawned)');

  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'approve-package-probe-'));
  const goalDir = path.join(root, '.rbtv', 'goals', GOAL);
  fs.mkdirSync(path.join(goalDir, 'coordination', 'asks'), { recursive: true });
  const pkgFile = path.join(goalDir, APPROVE_PACKAGE);

  const db = openEndingStore(path.join(root, '.rbtv', 'runtime', 'ignite', 'heart.db'));
  const store = bind(db);
  // An ask opened and RELEASED exactly as the §2.4 door releases one — `reapAndRelaunch` is what
  // stamps `authorized_reply_at`, and reaching it is the whole proof an authorized owner reply
  // landed in this thread. Without it every arm below would refuse for the WRONG reason.
  store.insertAsk({ ask_id: THREAD, goal: GOAL, seat: SEAT, label: 'work-content', evidence_pointer: `/tmp/${THREAD}.txt` });
  store.postAsk({ ask_id: THREAD, posted_at: '2026-08-25 10:00' });
  store.reapAndRelaunch({ ask_id: THREAD, authorized_reply_at: '2026-08-25 10:05' });

  const births = [];
  const injectedRunPathB = (pkg) => { births.push(pkg); return { ok: true }; };
  const start = () => startExecution({ db }, {
    workspaceRoot: root, goal: GOAL, thread: THREAD, commit: COMMIT, runPathB: injectedRunPathB,
  });

  // ── G. THE GATE BEFORE THE WRITER RUNS ──────────────────────────────────────────────────────
  check('G0: the fixture starts with NO approve-package on the planning goal', !fs.existsSync(pkgFile), pkgFile);
  let r = start();
  check('G1: BEFORE the writer, an otherwise-perfect approval is REFUSED `no-approve-package` — the'
    + ' loud, honest gap the fourteenth intent shipped with',
    r.started === false && r.reason === 'no-approve-package', JSON.stringify(r));
  check('G2: and NO birth was attempted while the package was absent — a refusal above the birth is'
    + ' nothing tried, never a half-started goal', births.length === 0, `births=${births.length}`);

  // ── W. THE WRITER ───────────────────────────────────────────────────────────────────────────
  const w = runWriter([
    '--goal-dir', goalDir, '--execution-goal', EXEC_GOAL, '--bound-commit', COMMIT,
    '--lane', 'daemon', '--plan-artifacts', root, '--roster', 'exec-builder,exec-judge',
    '--workflow', 'execute',
  ]);
  check('W1: the writer exits 0 and reports the path it wrote', w.code === 0 && /approve-package written/.test(w.stdout), w.stdout.trim());
  check('W2: the package exists at the path `start-execution.js` READS (`APPROVE_PACKAGE`), never a'
    + ' second convention', fs.existsSync(pkgFile), pkgFile);
  const written = fs.existsSync(pkgFile) ? JSON.parse(fs.readFileSync(pkgFile, 'utf8')) : {};
  out('--- written package ---');
  out(fs.existsSync(pkgFile) ? fs.readFileSync(pkgFile, 'utf8').trimEnd() : '(absent)');
  out('--- end package ---');
  check('W3: it carries the four fields the reader and the birth REQUIRE',
    written.execution_goal === EXEC_GOAL && written.bound_commit === COMMIT
    && written.lane === 'daemon' && typeof written.plan_artifacts === 'string',
    JSON.stringify(written));
  check('W4: it carries NONE of the three daemon-stamped keys — a package naming its own planning'
    + ' goal or goals root is how a copy from another goal hides',
    written.planning_goal === undefined && written.goals_root === undefined && written.origin_id === undefined,
    JSON.stringify(Object.keys(written)));
  check('W5: no `.tmp` residue beside it — the write is tmp+rename, and the rename completed',
    !fs.existsSync(pkgFile + '.tmp'));

  // ── A. THE GATE AFTER THE WRITER RAN ────────────────────────────────────────────────────────
  r = start();
  check('A1: AFTER the writer, the SAME approval is ADMITTED and the birth runs — the transition'
    + ' this landing exists to produce', r.started === true && r.execution_goal === EXEC_GOAL, JSON.stringify(r));
  check('A2: the birth received the daemon-stamped trio, derived by the daemon rather than read'
    + ' from the file', births.length === 1
    && births[0].planning_goal === goalDir
    && births[0].goals_root === path.join(root, '.rbtv', 'goals')
    && births[0].origin_id === THREAD,
    JSON.stringify(births[0] || null));
  check('A3: the writer\'s own optional fields reached the birth intact (roster + workflow)',
    births.length === 1 && Array.isArray(births[0].roster)
    && births[0].roster.join(',') === 'exec-builder,exec-judge' && births[0].workflow === 'execute',
    JSON.stringify((births[0] || {}).roster));

  // ── R. THE WRITER REFUSES WHAT THE READER WOULD REFUSE ──────────────────────────────────────
  const other = path.join(root, '.rbtv', 'goals', 'other-goal');
  fs.mkdirSync(other, { recursive: true });
  const refA = runWriter(['--goal-dir', other, '--execution-goal', EXEC_GOAL, '--bound-commit', 'main',
    '--lane', 'daemon', '--plan-artifacts', root]);
  check('R1: a REF NAME as the bound commit is refused AT THE WRITER [T5-R5] — the seat can still'
    + ' fix it here; at the gate it is an owner reading a refusal in Slack',
    refA.code === 2 && /bad-bound-commit/.test(refA.stdout), refA.stdout.trim());
  const refB = runWriter(['--goal-dir', other, '--execution-goal', '../../etc', '--bound-commit', COMMIT,
    '--lane', 'daemon', '--plan-artifacts', root]);
  check('R2: an execution-goal name carrying path separators is refused — it becomes a path segment'
    + ' under .rbtv/goals/', refB.code === 2 && /bad-execution-goal/.test(refB.stdout), refB.stdout.trim());
  check('R3: neither refusal left a package behind — refused before any byte lands',
    !fs.existsSync(path.join(other, APPROVE_PACKAGE)));

  // ── D. THE DERIVED-TREE GUARD IS WALKED, NOT ASSUMED ────────────────────────────────────────
  // approve-package is PLANNING STATE, not a derived lane (the marked tree is
  // `planning/current/seat-lane/`), so this guard is expected to pass in production. It is called
  // anyway, and this arm is what proves the call is real rather than documentation.
  const derivedGoal = path.join(root, '.rbtv', 'goals', 'derived-goal');
  fs.mkdirSync(path.join(derivedGoal, 'planning'), { recursive: true });
  fs.writeFileSync(path.join(derivedGoal, 'planning', 'DERIVED.md'),
    'source: ..\nregenerator: a probe fixture\n');
  const refC = runWriter(['--goal-dir', derivedGoal, '--execution-goal', EXEC_GOAL, '--bound-commit', COMMIT,
    '--lane', 'daemon', '--plan-artifacts', root]);
  check('D1: a planning folder marked DERIVED refuses the write instead of leaving a package the'
    + ' next regenerate deletes (C10)',
    refC.code !== 0 && /DERIVED|derived/i.test(refC.stderr + refC.stdout),
    (refC.stderr || refC.stdout).trim().split('\n').slice(-1)[0]);
  check('D2: and nothing was written under the marked tree',
    !fs.existsSync(path.join(derivedGoal, APPROVE_PACKAGE)));

  const failed = checks.filter((c) => !c.pass);
  out('', `${checks.length - failed.length}/${checks.length} PASS`);
  fs.rmSync(root, { recursive: true, force: true });
  process.exit(failed.length ? 1 : 0);
}

main();
