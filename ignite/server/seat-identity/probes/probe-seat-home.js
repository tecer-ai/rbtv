'use strict';

// Task 7.12 — `resolveSeatHome()`: a job's (goal, seat) pointer -> the LIVE run's seat folder.
//
// Isolation: a throwaway goal tree under os.tmpdir(). Nothing here touches a real `.rbtv/`.
//
// ⚠ WHAT THIS PROBE IS FOR, and it is NOT "does the happy path work". It is the REFUSALS. The
// resolver's whole job is to decline to guess: a goal with no open run, a goal with TWO open runs
// (the one-live-run invariant is hand-held until 7.77), a seat that is not materialized, a seat
// with no roster row. Each of those is a state where returning *a* path would fire a job into a
// place nobody pointed it at, and each is cheap to get wrong by "helpfully" picking one.
//
// ⚠ POSITIVE CONTROL (bars.md 11's second half): the happy path is asserted in the SAME run as
// every refusal. A resolver that refused everything would satisfy all the negative checks and is
// caught only by the positive one — "it refused correctly" and "it cannot resolve anything" print
// the same thing otherwise.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-seat-home.out');
fs.writeFileSync(outPath, '');

const { resolveSeatHome } = require('../seat-folder');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-seat-home-'));

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// Build a goal tree. `runs` is a list of [runName, state]; `seats` a list of seat names to
// materialize (seat.md + a taskforce row). Anything omitted is the defect under test.
function makeGoal(goal, { runs = [['run-1', 'open']], seats = ['worker'], roster = null, inGoalsIndex = true } = {}) {
  const goalsDir = path.join(root, '.rbtv', 'goals');
  fs.mkdirSync(path.join(goalsDir, goal), { recursive: true });

  const goalsCsv = path.join(goalsDir, 'goals.csv');
  if (!fs.existsSync(goalsCsv)) fs.writeFileSync(goalsCsv, 'name,state\n');
  if (inGoalsIndex) fs.appendFileSync(goalsCsv, `${goal},open\n`);

  fs.writeFileSync(
    path.join(goalsDir, goal, 'runs.csv'),
    'run-id,state\n' + runs.map(([r, s]) => `${r},${s}`).join('\n') + '\n',
  );

  for (const [runName] of runs) {
    const runDir = path.join(goalsDir, goal, 'runs', runName);
    fs.mkdirSync(path.join(runDir, 'seats'), { recursive: true });
    const rostered = roster === null ? seats : roster;
    fs.writeFileSync(path.join(runDir, 'taskforce.csv'), 'seat,executor\n' + rostered.map((s) => `${s},claude`).join('\n') + '\n');
    for (const seat of seats) {
      const seatDir = path.join(runDir, 'seats', seat);
      fs.mkdirSync(seatDir, { recursive: true });
      fs.writeFileSync(path.join(seatDir, 'seat.md'), `---\nseat: ${seat}\n---\n\n# ${seat}\n`);
    }
  }
  return path.join(goalsDir, goal);
}

try {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  // ── POSITIVE CONTROL · the happy path resolves, and to the RIGHT folder ───────────────────────
  makeGoal('good-goal');
  const ok = resolveSeatHome({ workspaceRoot: root, goal: 'good-goal', seat: 'worker' });
  const expected = path.join(root, '.rbtv', 'goals', 'good-goal', 'runs', 'run-1', 'seats', 'worker');
  check('POSITIVE CONTROL: a live, materialized, rostered seat resolves',
    ok.ok === true, ok.ok ? '' : ok.reason);
  check('…and resolves to the canonical seat folder, exactly',
    ok.ok && ok.seatDir === expected, ok.ok ? ok.seatDir : 'n/a');
  check('…and reports which run it picked (the run is DERIVED, never stored on the job)',
    ok.ok && ok.run === 'run-1', ok.ok ? `run=${ok.run}` : 'n/a');

  // ── THE RUN IS RESOLVED AT FIRE TIME · a CLOSED run is not a home ─────────────────────────────
  makeGoal('closed-goal', { runs: [['run-1', 'closed']] });
  const closed = resolveSeatHome({ workspaceRoot: root, goal: 'closed-goal', seat: 'worker' });
  check('a goal whose only run is CLOSED is refused (r-job-seat-home: jobs retire with the run)',
    closed.ok === false, closed.ok ? 'RESOLVED — a closed run was treated as a home' : closed.reason.slice(0, 90));

  // The forward case that makes storing the run wrong: run-1 closed, run-2 open. The SAME pointer
  // must now resolve to run-2 with nothing about the job changing.
  makeGoal('moved-goal', { runs: [['run-1', 'closed'], ['run-2', 'open']] });
  const moved = resolveSeatHome({ workspaceRoot: root, goal: 'moved-goal', seat: 'worker' });
  check('a pointer FOLLOWS the goal to its new live run (this is why the run is not stored)',
    moved.ok === true && moved.run === 'run-2',
    moved.ok ? `run=${moved.run}` : moved.reason.slice(0, 90));

  // ── AMBIGUITY IS A REFUSAL, NEVER A CHOICE ────────────────────────────────────────────────────
  makeGoal('two-open', { runs: [['run-1', 'open'], ['run-2', 'open']] });
  const two = resolveSeatHome({ workspaceRoot: root, goal: 'two-open', seat: 'worker' });
  check('TWO open runs is a typed refusal — the resolver never picks one',
    two.ok === false && /2 runs in state "open"/.test(two.reason),
    two.ok ? `RESOLVED to ${two.run} — it CHOSE` : two.reason.slice(0, 100));

  makeGoal('none-open', { runs: [['run-1', 'closed'], ['run-2', 'closed']] });
  const none = resolveSeatHome({ workspaceRoot: root, goal: 'none-open', seat: 'worker' });
  check('ZERO open runs is a typed refusal, not an optimistic default',
    none.ok === false, none.ok ? 'RESOLVED' : none.reason.slice(0, 90));

  // ── THE SEAT MUST BE REAL, not merely a path of the right shape ───────────────────────────────
  const absent = resolveSeatHome({ workspaceRoot: root, goal: 'good-goal', seat: 'no-such-seat' });
  check('a seat that does not exist is refused',
    absent.ok === false, absent.ok ? 'RESOLVED' : absent.reason.slice(0, 90));

  // A folder of the right SHAPE with no seat.md — the hand-made imposter case.
  fs.mkdirSync(path.join(root, '.rbtv', 'goals', 'good-goal', 'runs', 'run-1', 'seats', 'imposter'), { recursive: true });
  const imposter = resolveSeatHome({ workspaceRoot: root, goal: 'good-goal', seat: 'imposter' });
  check('a bare folder of the right shape (no seat.md) is refused — materialization is checked',
    imposter.ok === false, imposter.ok ? 'RESOLVED' : imposter.reason.slice(0, 90));

  // Materialized but NOT rostered.
  makeGoal('unrostered', { seats: ['ghost'], roster: ['someone-else'] });
  const ghost = resolveSeatHome({ workspaceRoot: root, goal: 'unrostered', seat: 'ghost' });
  check('a materialized seat with NO taskforce row is refused — roster is checked too',
    ghost.ok === false, ghost.ok ? 'RESOLVED' : ghost.reason.slice(0, 90));

  // A goal absent from the goals index.
  makeGoal('unindexed', { inGoalsIndex: false });
  const unindexed = resolveSeatHome({ workspaceRoot: root, goal: 'unindexed', seat: 'worker' });
  check('a goal missing from goals.csv is refused',
    unindexed.ok === false, unindexed.ok ? 'RESOLVED' : unindexed.reason.slice(0, 90));

  // ── ARGUMENT HYGIENE ─────────────────────────────────────────────────────────────────────────
  const partial = resolveSeatHome({ workspaceRoot: root, goal: 'good-goal' });
  check('a half pointer (goal, no seat) is refused at the resolver too',
    partial.ok === false, partial.ok ? 'RESOLVED' : partial.reason.slice(0, 90));

  const missingGoal = resolveSeatHome({ workspaceRoot: root, goal: 'nope', seat: 'worker' });
  check('a goal with no runs.csv is refused, naming the file',
    missingGoal.ok === false && /runs\.csv/.test(missingGoal.reason),
    missingGoal.ok ? 'RESOLVED' : missingGoal.reason.slice(0, 90));

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`SEAT_HOME_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
} catch (err) {
  out('ERROR:', err.message, err.stack);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
} finally {
  try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* best effort */ }
}
