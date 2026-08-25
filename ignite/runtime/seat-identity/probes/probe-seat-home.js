'use strict';

// Task 7.12 — `resolveSeatHome()`: a job's (goal, seat) pointer -> the goal's seat folder.
//
// Isolation: a throwaway goal tree under os.tmpdir(). Nothing here touches a real `.rbtv/`.
//
// ── 7.607 E2a — WHAT THIS PROBE NOW ASSERTS, AND WHAT LEFT IT WITH ITS SUBJECT ─────────────────
//
// The layout is GOAL-DIRECT (`decisions.md#d-runs-extinguished`): `<goal>/seats/<seat>/`. Two of
// the old arms measured properties of the run REGISTER and are deleted WITH their subject rather
// than weakened into something that still passes — recorded here because a silently vanished
// assertion is indistinguishable from one that was never there:
//
//   · "reports which run it picked"  — there is no run to pick. `resolveSeatHome` no longer
//     returns a `run` field at all, so an arm asserting one would be asserting `undefined`.
//   · "TWO open runs is a typed refusal" — the ambiguity had exactly one source, two `state=open`
//     rows in one register. With no register there are no two rows; and the lease's own reasoning
//     (one-live-run.js) is that two rooms of one goal are both evidence of the SAME goal
//     executing, so there is nothing to arbitrate and nothing to refuse arbitrating.
//
// What REPLACES them is not a weaker check, it is the property the ruling actually created:
// GOAL-DURABILITY. The same pointer resolves to the same folder across executions, which is the
// owner's memory mechanism, and the old "a pointer FOLLOWS the goal to its new live run" arm is
// its exact inverse — that arm existed because the folder MOVED, and this one exists because it
// must not.
//
// ⚠ WHAT THIS PROBE IS FOR, and it is NOT "does the happy path work". It is the REFUSALS. The
// resolver's whole job is to decline to guess: a goal that is not executing, a seat that is not
// materialized, a seat with no roster row, a goal the index does not carry, and — new here —
// evidence it could not read at all. Each is a state where returning *a* path would fire a job
// into a place nobody pointed it at.
//
// ⚠ POSITIVE CONTROL (bars.md 11's second half): the happy path is asserted in the SAME run as
// every refusal, and FIRST. A resolver that refused everything would satisfy all the negative
// checks and is caught only by the positive one — "it refused correctly" and "it cannot resolve
// anything" print the same thing otherwise.
//
// ⚠ THE LEASE IS REAL; ONLY `tmux` IS A FIXTURE. `readLease` here is `deriveLease` itself with an
// injected `tmuxProbe` supplying the exact bytes the binary prints. Every line of the room
// predicate, the seat verification and the unreadable classification runs for real. A hand-written
// stub returning `{live:true}` would be the probe supplying its own verdict, which measures the
// probe rather than the code.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-seat-home.out');
fs.writeFileSync(outPath, '');

const { resolveSeatHome, parseSeatPath } = require('../seat-folder');
const { deriveLease } = require('../../lease/lease');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-seat-home-'));

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// The lease as the daemon computes it, off a fixture tmux. `rooms` is what `list-sessions` prints.
function leaseOver(rooms) {
  return (args) => deriveLease({
    ...args,
    tmuxProbe: () => ({ sessions: rooms.join('\n') + (rooms.length ? '\n' : ''), panes: '' }),
  });
}
// tmux itself unreadable — the ignorance case, which is NOT "no lease".
const leaseUnreadable = (args) => deriveLease({
  ...args,
  tmuxProbe: () => { const e = new Error('permission denied'); e.stderr = 'error connecting to /x (Permission denied)'; throw e; },
});

// Build a GOAL-DIRECT goal tree. `seats` is the list of seat names to materialize (seat.md + a
// taskforce row at GOAL level). Anything omitted is the defect under test.
function makeGoal(goal, { seats = ['worker'], roster = null, inGoalsIndex = true } = {}) {
  const goalsDir = path.join(root, '.rbtv', 'goals');
  const goalDir = path.join(goalsDir, goal);
  fs.mkdirSync(path.join(goalDir, 'seats'), { recursive: true });

  const goalsCsv = path.join(goalsDir, 'goals.csv');
  if (!fs.existsSync(goalsCsv)) fs.writeFileSync(goalsCsv, 'name,state\n');
  if (inGoalsIndex) fs.appendFileSync(goalsCsv, `${goal},open\n`);

  const rostered = roster === null ? seats : roster;
  fs.writeFileSync(path.join(goalDir, 'taskforce.csv'), 'seat,executor\n' + rostered.map((s) => `${s},claude`).join('\n') + '\n');
  for (const seat of seats) {
    const seatDir = path.join(goalDir, 'seats', seat);
    fs.mkdirSync(seatDir, { recursive: true });
    fs.writeFileSync(path.join(seatDir, 'seat.md'), `---\nseat: ${seat}\n---\n\n# ${seat}\n`);
  }
  return goalDir;
}

try {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  // ── POSITIVE CONTROL · the happy path resolves, and to the RIGHT folder ───────────────────────
  makeGoal('good-goal');
  const live = leaseOver(['good-goal']);
  const ok = resolveSeatHome({ workspaceRoot: root, goal: 'good-goal', seat: 'worker', readLease: live });
  const expected = path.join(root, '.rbtv', 'goals', 'good-goal', 'seats', 'worker');
  check('POSITIVE CONTROL: an executing goal\'s materialized, rostered seat resolves',
    ok.ok === true, ok.ok ? '' : ok.reason);
  check('…and resolves to the canonical GOAL-DIRECT seat folder, exactly (no runs/ segment)',
    ok.ok && ok.seatDir === expected, ok.ok ? ok.seatDir : 'n/a');
  check('…and the returned path carries NO run segment at all',
    ok.ok && !/[\\/]runs[\\/]/.test(ok.seatDir), ok.ok ? ok.seatDir : 'n/a');

  // ── NO DUAL GRAMMAR · the OLD shape is REFUSED, not tolerated alongside the new one ────────────
  // 7.607 E2a §2 review. `resolveSeatHome` ASSEMBLES a path and can never meet the old shape, so
  // every arm above passes unchanged whether or not the parser still accepts `runs/run-N`. The
  // cut-clean property (`seat-folder.js` header: "this parser does NOT accept the old shape
  // alongside the new one") therefore had NO guard at all — a re-admitting mutant left this probe
  // GREEN, measured. It is asserted here directly, against the parser, in both directions: the
  // new shape parses to the goal, the extinguished compartment parses to NOTHING.
  const oldShape = path.join(root, '.rbtv', 'goals', 'good-goal', 'runs', 'run-1', 'seats', 'worker');
  const newShape = path.join(root, '.rbtv', 'goals', 'good-goal', 'seats', 'worker');
  const parsedNew = parseSeatPath(newShape);
  check('GRAMMAR CONTROL: the goal-direct shape parses, and to the goal (else the next arm is vacuous)',
    parsedNew !== null && parsedNew.goal === 'good-goal' && parsedNew.seat === 'worker',
    parsedNew ? `goal=${parsedNew.goal} seat=${parsedNew.seat}` : 'PARSED NULL — the arm below proves nothing');
  const parsedOld = parseSeatPath(oldShape);
  check('NO DUAL GRAMMAR: an OLD-SHAPE `runs/run-N/seats/<seat>` path is REFUSED by the parser',
    parsedOld === null,
    parsedOld === null ? oldShape : `ADMITTED as goal=${parsedOld.goal} seatDir=${parsedOld.seatDir}`);

  // ── GOAL-DURABILITY · the seat folder is the SAME across executions ───────────────────────────
  // The ruling's memory mechanism (owner clarification to `d-runs-extinguished`): "the seats boot
  // from the SAME seats/<seat>/ folders on every execution". Measured as a property rather than
  // asserted in a comment.
  //
  // ⚠ 7.607 E2b RE-KEYS WHAT "A LATER EXECUTION" LOOKS LIKE HERE, and the change is the point.
  // E2a expressed it as a DIFFERENTLY-NAMED room (`good-goal-run-9`) because two executions of a
  // goal still had two room names. Design-lock item 2 settles ONE room per goal, named for the
  // goal, and E2b deleted the legacy spelling from the lease predicate — so a later execution is
  // the SAME room name, and goal-durability is the stronger statement that the resolution does
  // not depend on the execution at all. Executions are told apart by the dated stamp, which is a
  // record on the rows, never a component of a path.
  const secondExecution = resolveSeatHome({
    workspaceRoot: root, goal: 'good-goal', seat: 'worker', readLease: leaseOver(['good-goal']),
  });
  check('GOAL-DURABLE: a later execution resolves the SAME seat folder (the memory mechanism)',
    secondExecution.ok === true && secondExecution.seatDir === expected,
    secondExecution.ok ? secondExecution.seatDir : secondExecution.reason.slice(0, 90));

  // ── THE LEASE IS ASKED AT FIRE TIME · a goal that is NOT executing is not a home ──────────────
  // This is the old CLOSED-run arm re-founded: the register said `state=closed`, the lease says
  // "no room exists right now". Same refusal, live evidence instead of a stored status.
  const notExecuting = resolveSeatHome({
    workspaceRoot: root, goal: 'good-goal', seat: 'worker', readLease: leaseOver([]),
  });
  check('a goal that is NOT executing is refused (r-job-seat-home: jobs retire with the execution)',
    notExecuting.ok === false && /not executing/.test(notExecuting.reason || ''),
    notExecuting.ok ? 'RESOLVED — a finished goal was treated as a home' : notExecuting.reason.slice(0, 100));

  // ── ANOTHER GOAL'S ROOM IS NOT THIS GOAL'S LEASE ──────────────────────────────────────────────
  // Discriminates the room PREDICATE from "any room at all" — a lease that matched on the
  // existence of a tmux server would pass every arm above and this one catches it.
  const foreignRoom = resolveSeatHome({
    workspaceRoot: root, goal: 'good-goal', seat: 'worker', readLease: leaseOver(['some-other-goal', 'default']),
  });
  check('another goal\'s room does NOT lease this goal',
    foreignRoom.ok === false, foreignRoom.ok ? 'RESOLVED on a foreign room' : foreignRoom.reason.slice(0, 90));

  // ── UNREADABLE EVIDENCE FAILS CLOSED ─────────────────────────────────────────────────────────
  // Ignorance is not absence and it is certainly not permission. The lease reports `{ok:false}`
  // and this resolver's posture on that is CLOSED — a job may not fire on a fact nobody measured.
  const blind = resolveSeatHome({
    workspaceRoot: root, goal: 'good-goal', seat: 'worker', readLease: leaseUnreadable,
  });
  check('an UNREADABLE lease is refused, and named as ignorance rather than as "not executing"',
    blind.ok === false && /UNREADABLE/.test(blind.reason || ''),
    blind.ok ? 'RESOLVED on unmeasured evidence' : blind.reason.slice(0, 110));

  // ── THE SEAT MUST BE REAL, not merely a path of the right shape ───────────────────────────────
  const absent = resolveSeatHome({ workspaceRoot: root, goal: 'good-goal', seat: 'no-such-seat', readLease: live });
  check('a seat that does not exist is refused',
    absent.ok === false, absent.ok ? 'RESOLVED' : absent.reason.slice(0, 90));

  // A folder of the right SHAPE with no seat.md — the hand-made imposter case.
  fs.mkdirSync(path.join(root, '.rbtv', 'goals', 'good-goal', 'seats', 'imposter'), { recursive: true });
  const imposter = resolveSeatHome({ workspaceRoot: root, goal: 'good-goal', seat: 'imposter', readLease: live });
  check('a bare folder of the right shape (no seat.md) is refused — materialization is checked',
    imposter.ok === false, imposter.ok ? 'RESOLVED' : imposter.reason.slice(0, 90));

  // Materialized but NOT rostered.
  makeGoal('unrostered', { seats: ['ghost'], roster: ['someone-else'] });
  const ghost = resolveSeatHome({
    workspaceRoot: root, goal: 'unrostered', seat: 'ghost', readLease: leaseOver(['unrostered']),
  });
  check('a materialized seat with NO taskforce row is refused — roster is checked too',
    ghost.ok === false, ghost.ok ? 'RESOLVED' : ghost.reason.slice(0, 90));

  // A goal absent from the goals index. The index read is a DIFFERENT question from liveness and
  // survives the re-founding: a room named after a goal the index never heard of grants nothing.
  makeGoal('unindexed', { inGoalsIndex: false });
  const unindexed = resolveSeatHome({
    workspaceRoot: root, goal: 'unindexed', seat: 'worker', readLease: leaseOver(['unindexed']),
  });
  check('a goal missing from goals.csv is refused EVEN WITH a room of its name',
    unindexed.ok === false && /goals\.csv/.test(unindexed.reason || ''),
    unindexed.ok ? 'RESOLVED' : unindexed.reason.slice(0, 90));

  // ── ARGUMENT HYGIENE ─────────────────────────────────────────────────────────────────────────
  const partial = resolveSeatHome({ workspaceRoot: root, goal: 'good-goal', readLease: live });
  check('a half pointer (goal, no seat) is refused at the resolver too',
    partial.ok === false, partial.ok ? 'RESOLVED' : partial.reason.slice(0, 90));

  const missingGoal = resolveSeatHome({ workspaceRoot: root, goal: 'nope', seat: 'worker', readLease: leaseOver(['nope']) });
  check('a goal with no goals-index entry at all is refused, naming the file',
    missingGoal.ok === false && /goals\.csv/.test(missingGoal.reason || ''),
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
