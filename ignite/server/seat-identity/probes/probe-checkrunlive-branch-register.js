'use strict';

// Task 7.481 (BSC2) — probe: `checkRunLive` validates a BRANCH against its OWN run register.
//
// Replayable:  node server/seat-identity/probes/probe-checkrunlive-branch-register.js
// Exit 0 iff every expectation below holds; the full return of every arm is printed either way.
//
// WHY IT IS SHAPED THIS WAY, arm by arm — each of these exists because the arm above it could
// otherwise pass for the wrong reason:
//
//  * ALL ARMS RUN IN ONE INVOCATION. A gate that returned one string on every input would read
//    green arm by arm; `discriminates` is computed over the arms' returns as a SET, so a
//    one-verdict gate fails here rather than reading as three passes.
//
//  * THE `goalsCsv` READ COMES FIRST AND MASKS THIS ONE. `checkRunLive` refuses on the goals-index
//    BEFORE it ever reaches `runs.csv`; branch-shape-arms/arm1 measured exactly that and had to be
//    withheld. So the fixture carries its OWN goals-index with the fixture goal in it, and
//    `goals_gate.cleared` is not asserted — it is MEASURED, by running the identical seat path
//    against a second fixture whose goals-index omits the goal and showing that arm produces the
//    goals-level refusal while none of the runs.csv arms do.
//
//  * EVERY ARM'S `parsed` COMES FROM `parseSeatPath` ON A REAL PATH, never from a hand-typed
//    object. A hand-typed `{goal, run, runsCsv}` tests the comparison and skips the mapping — and
//    the mapping (which register, which row) is the whole subject.
//
//  * THE PRE-CHANGE CONTROL IS PINNED BY BLOB SHA, not by `HEAD`, so it keeps naming the
//    pre-change body after this change is committed. Blob 416c3c9c (commit ea2da9f, BSC1).
//    Every arm runs against BOTH bodies: the run-seat arms prove behaviour UNCHANGED, and the
//    branch arms prove the change is load-bearing (the control refuses what the new body admits),
//    which is what stops the green arms from being vacuous.
//
//  * INNERMOST-vs-OUTERMOST IS SEPARATED AT DEPTH 2. At depth 1 `branch[0]` and `branch[last]` are
//    the same element, so a depth-1-only probe cannot tell the implemented rule from the wrong
//    one. The depth-2 register carries `branch-2` and NO `branch-1` row, so outermost-selection
//    refuses there; `depth2_outermost_would_refuse` records that counterfactual as measured.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const Module = require('node:module');

const LIVE = path.resolve(__dirname, '..', 'seat-folder.js');
const CONTROL_BLOB = '416c3c9c3fbafec409d3cd2a5462fd31bc5308ae'; // pre-change body, commit ea2da9f

const SF = require(LIVE);

// Load the pinned pre-change body as a second module beside the live one. It is written next to
// the live file so its own `require('./csv')` resolves to the same reader — a control that loaded
// a different CSV reader would not be a control.
function loadControl() {
  const repoRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd: __dirname })
    .toString().trim();
  const src = execFileSync('git', ['cat-file', 'blob', CONTROL_BLOB], {
    cwd: repoRoot, maxBuffer: 8 << 20,
  }).toString();
  const file = path.join(path.dirname(LIVE), `.control-${CONTROL_BLOB.slice(0, 8)}.js`);
  fs.writeFileSync(file, src);
  try {
    const m = new Module(file, null);
    m.filename = file;
    m.paths = Module._nodeModulePaths(path.dirname(file));
    m._compile(src, file);
    return { mod: m.exports, sha: CONTROL_BLOB };
  } finally {
    fs.unlinkSync(file);
  }
}

// ── fixture ────────────────────────────────────────────────────────────────────────────────────
// Hermetic and built from scratch on every run: no live run, no shared package, nothing on the
// repo's own disk. `parseSeatPath` derives goalsCsv/runsCsv from the PATH, so the fixture only has
// to put the right files at the right places for the real mapping to be exercised.
const GOALS_HEADER = 'name,creation date,due date,type,status\n';
const RUNS_HEADER = 'run-id,type,state,taskforce-ids,opened,closed\n';

function w(file, body) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, body);
}

function buildFixture({ goalInIndex }) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'bsc2-'));
  const goals = path.join(root, '.rbtv', 'goals');
  const g = path.join(goals, 'fx-goal');
  w(path.join(goals, 'goals.csv'), GOALS_HEADER + (goalInIndex ? 'fx-goal,2026-08-07,,fixture,open\n' : ''));
  // the GOAL's register: run-1 is open; run-9 has no row at all
  w(path.join(g, 'runs.csv'), RUNS_HEADER + 'run-1,one-shot,open,tf-1,2026-08-07,\n');
  const r1 = path.join(g, 'runs', 'run-1');
  const b1 = path.join(r1, 'branches', 'branch-1');
  const b2 = path.join(b1, 'branches', 'branch-2');
  const b9 = path.join(r1, 'branches', 'branch-9');
  // each branch is a compartment carrying its OWN register, stating its OWN liveness
  w(path.join(b1, 'runs.csv'), RUNS_HEADER + 'branch-1,,open,tf-1-b1,2026-08-07,\n');
  w(path.join(b2, 'runs.csv'), RUNS_HEADER + 'branch-2,,open,tf-1-b2,2026-08-07,\n'); // NO branch-1 row
  w(path.join(b9, 'runs.csv'), RUNS_HEADER); // header only — the absent-row case
  for (const d of [
    path.join(r1, 'seats', 'run-seat'),
    path.join(g, 'runs', 'run-9', 'seats', 'run-seat-absent'),
    path.join(b1, 'seats', 'br1-seat'),
    path.join(b2, 'seats', 'br2-seat'),
    path.join(b9, 'seats', 'br9-seat'),
  ]) fs.mkdirSync(d, { recursive: true });
  return {
    root,
    runSeat: path.join(r1, 'seats', 'run-seat'),
    runSeatAbsent: path.join(g, 'runs', 'run-9', 'seats', 'run-seat-absent'),
    br1Seat: path.join(b1, 'seats', 'br1-seat'),
    br2Seat: path.join(b2, 'seats', 'br2-seat'),
    br9Seat: path.join(b9, 'seats', 'br9-seat'),
  };
}

// Reduce a refusal to its TEMPLATE by replacing the two substituted values with placeholders, so
// "byte-equal refusal text" is checked on the string the code carries, not on a value that is
// supposed to differ between a run and a branch.
//
// LONGEST VALUE FIRST, and that is not tidiness: the compartment id occurs INSIDE the register
// path (`…/branches/branch-9/runs.csv`), so substituting the id first also rewrites it inside the
// path and the path substitution then matches nothing. This probe's first run failed on exactly
// that — a red arm caused by the checker, not by the subject. Kept as a comment because the next
// person to add a placeholder here will reach for the same naive loop.
function template(s, ...values) {
  let out = String(s);
  values
    .map((v, i) => [String(v), i])
    .sort((a, b) => b[0].length - a[0].length)
    .forEach(([v, i]) => { out = out.split(v).join(`<${i}>`); });
  return out;
}

const control = loadControl();
const fx = buildFixture({ goalInIndex: true });
const fxNoGoal = buildFixture({ goalInIndex: false });

const parsed = {
  runSeat: SF.parseSeatPath(fx.runSeat),
  runSeatAbsent: SF.parseSeatPath(fx.runSeatAbsent),
  br1: SF.parseSeatPath(fx.br1Seat),
  br2: SF.parseSeatPath(fx.br2Seat),
  br9: SF.parseSeatPath(fx.br9Seat),
  noGoalRunSeat: SF.parseSeatPath(path.join(fxNoGoal.runSeat)),
};

const out = { control_blob: control.sha, fixture_root: fx.root, fixture_root_no_goal: fxNoGoal.root };

// ── the fixture is shown to CLEAR the goalsCsv read, before any runs.csv verdict is reported ───
const noGoalArm = SF.checkRunLive(parsed.noGoalRunSeat);
out.goals_gate = {
  identical_seat_path_shape_without_the_goal_in_the_index: noGoalArm,
  with_the_goal_in_the_index: SF.checkRunLive(parsed.runSeat),
  cleared: /is not in /.test(noGoalArm.reason || '') && SF.checkRunLive(parsed.runSeat).ok === true,
};

// ── the three arms, one invocation, live body and pinned pre-change control side by side ───────
out.arms = {
  A1_live_branch_depth1: { parsed_branch: parsed.br1.branch, register: parsed.br1.runsCsv, live: SF.checkRunLive(parsed.br1), control: control.mod.checkRunLive(parsed.br1) },
  A1b_live_branch_depth2: { parsed_branch: parsed.br2.branch, register: parsed.br2.runsCsv, live: SF.checkRunLive(parsed.br2), control: control.mod.checkRunLive(parsed.br2) },
  A2_absent_row_branch: { parsed_branch: parsed.br9.branch, register: parsed.br9.runsCsv, live: SF.checkRunLive(parsed.br9), control: control.mod.checkRunLive(parsed.br9) },
  A3_run_seat_live: { parsed_branch: parsed.runSeat.branch, register: parsed.runSeat.runsCsv, live: SF.checkRunLive(parsed.runSeat), control: control.mod.checkRunLive(parsed.runSeat) },
  A3b_run_seat_absent_row: { parsed_branch: parsed.runSeatAbsent.branch, register: parsed.runSeatAbsent.runsCsv, live: SF.checkRunLive(parsed.runSeatAbsent), control: control.mod.checkRunLive(parsed.runSeatAbsent) },
};

// ── a `parsed` with NO `branch` key at all — the guard no other arm reaches ─────────────────────
// Every in-repo caller passes a `parseSeatPath` return, which always carries `branch`. Callers
// outside the repo hand-build the object (branch-shape-arms/arm2-repaired.js does), so the
// `Array.isArray` fallback is a real path — and an untested branch of a gate is exactly the kind
// of line that is discovered by a caller instead of by a probe.
const noBranchKey = { ...parsed.runSeat };
delete noBranchKey.branch;
out.parsed_without_branch_key = {
  live: SF.checkRunLive(noBranchKey),
  matches_run_seat_arm: JSON.stringify(SF.checkRunLive(noBranchKey))
    === JSON.stringify(out.arms.A3_run_seat_live.live),
};

// ── innermost, not outermost: the counterfactual, measured rather than argued ───────────────────
// Feed the depth-2 seat a `branch` chain truncated to its OUTERMOST element. That is exactly what
// an outermost-selecting implementation would look up, and the depth-2 register has no such row.
out.depth2_outermost_would_refuse =
  SF.checkRunLive({ ...parsed.br2, branch: [parsed.br2.branch[0]] });

// ── the refusal text is preserved byte for byte ────────────────────────────────────────────────
const liveAbs = out.arms.A3b_run_seat_absent_row.live.reason;
const ctlAbs = out.arms.A3b_run_seat_absent_row.control.reason;
const branchAbs = out.arms.A2_absent_row_branch.live.reason;
out.refusal_text = {
  run_seat_absent_row_live: liveAbs,
  run_seat_absent_row_control: ctlAbs,
  run_seat_byte_equal: liveAbs === ctlAbs,
  branch_absent_row_live: branchAbs,
  // the same template, with the compartment id and register path being the only substitutions
  template_live_branch: template(branchAbs, parsed.br9.branch[0], parsed.br9.runsCsv),
  template_control_run: template(ctlAbs, parsed.runSeatAbsent.run, parsed.runSeatAbsent.runsCsv),
  template_byte_equal: template(branchAbs, parsed.br9.branch[0], parsed.br9.runsCsv)
    === template(ctlAbs, parsed.runSeatAbsent.run, parsed.runSeatAbsent.runsCsv),
};

// ── vacuity control for the probe itself: the gate must not be one verdict wearing five labels ──
out.discriminates = new Set(Object.values(out.arms).map((a) => JSON.stringify(a.live))).size > 1;

const checks = {
  A1_live_branch_depth1_ok: out.arms.A1_live_branch_depth1.live.ok === true,
  A1b_live_branch_depth2_ok: out.arms.A1b_live_branch_depth2.live.ok === true,
  A2_absent_row_refuses: out.arms.A2_absent_row_branch.live.ok === false,
  A3_run_seat_unchanged_vs_control:
    JSON.stringify(out.arms.A3_run_seat_live.live) === JSON.stringify(out.arms.A3_run_seat_live.control),
  A3b_run_seat_absent_unchanged_vs_control:
    JSON.stringify(out.arms.A3b_run_seat_absent_row.live) === JSON.stringify(out.arms.A3b_run_seat_absent_row.control),
  refusal_text_byte_equal: out.refusal_text.run_seat_byte_equal && out.refusal_text.template_byte_equal,
  fixture_clears_goals_read: out.goals_gate.cleared === true,
  // load-bearing: the pre-change body must REFUSE the branch the new body admits
  change_is_load_bearing: out.arms.A1_live_branch_depth1.control.ok === false
    && out.arms.A1b_live_branch_depth2.control.ok === false,
  outermost_selection_would_refuse_at_depth2: out.depth2_outermost_would_refuse.ok === false,
  parsed_without_branch_key_falls_back_to_run: out.parsed_without_branch_key.matches_run_seat_arm === true,
  gate_discriminates: out.discriminates === true,
};
out.checks = checks;
out.all_passed = Object.values(checks).every(Boolean);

fs.rmSync(fx.root, { recursive: true, force: true });
fs.rmSync(fxNoGoal.root, { recursive: true, force: true });

console.log(JSON.stringify(out, null, 2));
process.exit(out.all_passed ? 0 : 1);
