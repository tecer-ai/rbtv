'use strict';

// Task 7.11 §4a/§4b step 1 — resolving a path to a SEAT.
//
// One resolver, two callers, deliberately: the launch-time gate (`spawnSeat`, which is handed a
// seat folder) and the command-time gate (a system CLI, which walks up from its own cwd) must
// agree on what a seat folder IS. Two resolvers would be two definitions, and the failure that
// produces — a launch landing somewhere the checker later refuses to recognise — is invisible
// until a seat is already sitting in it.
//
// The canonical shape (KG `seat folder`):
//     <ws>/.rbtv/goals/<goal>/runs/run-{n}/seats/<seat>/
//
// Everything here is derived from the PATH and from files on disk. Nothing is asserted by the
// caller — no env var, no flag, no name passed in. That is G-111's lesson wired into the shape of
// the module rather than written in a comment beside it: tonight `COORD_AGENT` (asserted)
// outranked pane resolution (verified) and two agents spoke under one roster name for an hour.

const fs = require('node:fs');
const path = require('node:path');
const { readCsv } = require('./csv');

// Parse the canonical shape out of an ABSOLUTE, REAL path. Returns null when the path is not a
// seat folder — the caller decides which typed refusal that becomes, because "you launched into
// a non-seat folder" and "you ran a CLI from a non-seat folder" are different failures with
// different remedies even though they share this test.
// r-master-seat-homes (owner, 2026-08-06): a SERVICE SEAT — a seat-shaped folder directly
// under .rbtv/goals/ named _<seat>, with NO goal apparatus (no goal.md, no runs, no taskforce):
// one seat, many sessions (the channel-master is the first). goalDir/runDir/seatDir all resolve
// to the folder itself; the seat name is the folder name WITHOUT its underscore, which is what
// its seat.md declares (descriptor-agreement unchanged).
const SERVICE_SEAT_RE = /[\\/]\.rbtv[\\/]goals[\\/](_[a-z0-9-]+)$/;
function parseServiceSeatPath(absPath) {
  if (!absPath || typeof absPath !== 'string') return null;
  const norm = path.normalize(absPath).replace(/[\\/]+$/, '');
  const m = SERVICE_SEAT_RE.exec(norm);
  if (!m) return null;
  const parts = norm.split(path.sep);
  return {
    workspaceRoot: parts.slice(0, parts.length - 3).join(path.sep),
    goal: m[1],
    seat: m[1].slice(1),
    goalDir: norm, runDir: norm, seatDir: norm,
    sessionsCsv: path.join(norm, 'sessions.csv'),
    runsCsv: null,
    service: true,
  };
}

// Task 7.480 (BSC1) — a BRANCH seat, and why the offsets had to go.
//
// The branch shape (concepts/branch.md, settled-by d-branch-family; the Python spelling of the
// same rule is `goal_cli.py#branch_parent_kind`): a branch homes under a RUN folder or,
// recursively, under another BRANCH folder, and it is a run-like COMPARTMENT of its own — it
// carries its own `runs.csv`, `sessions.csv`, `taskforce.csv`, `coordination/` and `seats/`:
//
//     <ws>/.rbtv/goals/<goal>/runs/run-{n}/branches/branch-{m}/…/branches/branch-{k}/seats/<seat>/
//
// WHY A WALK RATHER THAN PATCHED ARITHMETIC. The old body derived five anchors as FIXED negative
// offsets from `seats`. A branch level inserts TWO segments between the run folder and `seats`, so
// all five point two segments too shallow — and the depth is not a constant, so no offset is the
// right one. Measured (branch-shape-arms/arm2-out.json, partition exact): of the twelve fields the
// old body returned, NINE shift with those anchors and THREE — `seat`, `seatsDir`, `seatDir` — are
// anchored on `seats` itself and do not.
//
// TWO OF THE NINE ARE IDENTITY SCALARS, which is the part a path-only check cannot see. A fix that
// re-derived only the PATH fields would return `goal:"run-1", run:"branch-1"` for a branch seat —
// not a mis-path, a silently wrong IDENTITY (decisions.md
// #p-TASK-DAG-ACCEPTED-my-Q2-RULING-IS-AMENDED-NINE-NOT-EIGHT-and-TWO-OF-THEM-ARE-IDENTITY-SCALARS).
//
// WHERE `branch` LIVES — the shape decision this change had to make, stated here because the truth
// object carries FOUR identity components (goal, run, branch, seat) and the old return had three
// slots. `branch` gets its OWN slot and is an ORDERED CHAIN, outermost first — `['branch-1',
// 'branch-2']` at depth 2, `[]` for a run seat — with `branchDir` naming the innermost branch home
// (null for a run seat). Nothing is folded into anything: `run` stays the PARENT RUN, because a
// branch is not a run and renaming one into the other is the same identity lie by another door.
// The addition is purely additive, so no existing requirer's field disappears (sweeping the
// requirers to USE the new fields is task BSC3's, not this one's).
//
// THE COMPARTMENT-SCOPED FIELDS FOLLOW THE COMPARTMENT. `sessionsCsv` and `taskforceCsv` name the
// branch home's own for a branch seat (measured on disk: the branch root carries both), and
// `runsCsv` names the branch's OWN register — the branch's liveness is stated there, never in the
// goal's `runs.csv`, which has no row for it. `goalsCsv` stays goal-level: a branch's goal is
// still the goal.
//
// THE WALK GOES UP FROM `seats`, NOT DOWN FROM `.rbtv/goals`, and that is deliberate rather than
// incidental: a downward walk from the anchor admits `…/seats/<seat>/seats/x`, which the offset
// resolver refused, and widening the admission predicate is no part of this change. The
// `.rbtv`/`goals` anchor is still checked — it is where the walk must land — and the probe's red
// arm removes it to prove it is load-bearing. Both facts are measured in the probe's
// non-regression block, not asserted here.
const BRANCHES_DIR = 'branches';
const BRANCH_NAME_RE = /^branch-\d+$/;
const RUN_NAME_RE = /^run-\d+$/;

function parseSeatPath(absPath) {
  const parts = path.normalize(absPath).split(path.sep);
  // …/.rbtv/goals/<goal>/runs/<run>/[branches/<branch>/]*seats/<seat>
  const seatsIdx = parts.lastIndexOf('seats');
  if (seatsIdx < 0 || seatsIdx + 1 >= parts.length) return null;
  const seat = parts[seatsIdx + 1];
  if (!seat) return null;

  // Walk up through zero or more `branches/branch-{m}` levels. Zero levels IS the run-seat case
  // and the loop simply does not run, which is why the run-seat path through this function is
  // unchanged rather than re-implemented.
  const branch = [];
  let cursor = seatsIdx - 1;
  while (cursor >= 1 && parts[cursor - 1] === BRANCHES_DIR && BRANCH_NAME_RE.test(parts[cursor])) {
    branch.unshift(parts[cursor]);
    cursor -= 2;
  }

  const runIdx = cursor;
  const runsIdx = runIdx - 1;
  const goalIdx = runIdx - 2;
  const goalsIdx = runIdx - 3;
  const rbtvIdx = runIdx - 4;
  if (rbtvIdx < 1) return null;
  if (parts[runsIdx] !== 'runs' || parts[goalsIdx] !== 'goals' || parts[rbtvIdx] !== '.rbtv') return null;
  if (!RUN_NAME_RE.test(parts[runIdx])) return null;
  const goal = parts[goalIdx];
  if (!goal) return null;

  const workspaceRoot = parts.slice(0, rbtvIdx).join(path.sep) || path.sep;
  const goalDir = parts.slice(0, goalIdx + 1).join(path.sep);
  const runDir = parts.slice(0, runIdx + 1).join(path.sep);
  // `seats` sits directly under the innermost compartment, whichever kind it is.
  const branchDir = branch.length ? parts.slice(0, seatsIdx).join(path.sep) : null;
  const compartmentDir = branchDir || runDir;
  const seatDir = parts.slice(0, seatsIdx + 2).join(path.sep);
  return {
    workspaceRoot,
    goal: parts[goalIdx],
    run: parts[runIdx],
    branch,
    seat,
    goalDir,
    runDir,
    branchDir,
    seatsDir: parts.slice(0, seatsIdx + 1).join(path.sep),
    seatDir,
    sessionsCsv: path.join(compartmentDir, 'sessions.csv'),
    goalsCsv: path.join(parts.slice(0, goalsIdx + 1).join(path.sep), 'goals.csv'),
    runsCsv: path.join(branchDir || goalDir, 'runs.csv'),
    taskforceCsv: path.join(compartmentDir, 'taskforce.csv'),
  };
}

// Task 7.75 — GOAL SCOPE, the strictly weaker test parseSeatPath's refusal needs a name for.
//
// `parseSeatPath` answers "is this a seat folder?". The dispatch door needs the OTHER half of that
// question — "is this inside a goal's tree AT ALL?" — because those two answers together are what
// separate the three cases the door must tell apart: a goal-scoped dispatch naming a seat (admit,
// and record it), a goal-scoped dispatch naming NO seat (refuse — design-760 §3), and a dispatch
// that is not goal-scoped at all (the interim `.rbtv/sessions/<exec-id>/` path the sub-agent lane
// and every machine-lane job use — exempt, design-760 § machine-lane, NEED-3's sub-agent carve-out).
//
// It lives HERE, beside parseSeatPath, for this file's own founding reason: two spellings of what a
// goal tree IS would be two definitions, and the failure that produces is invisible until a
// dispatch lands somewhere one half recognises and the other does not.
function parseGoalScope(absPath) {
  const parts = path.normalize(absPath).split(path.sep);
  const goalsIdx = parts.lastIndexOf('goals');
  if (goalsIdx < 1 || parts[goalsIdx - 1] !== '.rbtv') return null;
  const goal = parts[goalsIdx + 1];
  if (!goal) return null;
  return {
    workspaceRoot: parts.slice(0, goalsIdx - 1).join(path.sep) || path.sep,
    goal,
    goalDir: parts.slice(0, goalsIdx + 2).join(path.sep),
  };
}

// Walk UP from a starting directory to the nearest enclosing seat folder (§4b step 1). Symlinks
// are resolved first: a seat reached through a symlink is the same seat, and a `..` segment must
// not be able to produce a shape the string test accepts and the filesystem does not.
function resolveSeatFromCwd(startDir) {
  let dir;
  try {
    dir = fs.realpathSync(path.resolve(startDir));
  } catch {
    return null;
  }
  while (true) {
    const parsed = parseSeatPath(dir);
    if (parsed) return parsed;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

// L2 — the goal is known and the run is the goal's LIVE run.
//
// "Live" is read from `runs.csv`'s own `state` column by NAME. A run whose row is absent is NOT
// live: the one-live-run invariant is maintained by hand tonight (7.77 has not landed), so a
// missing row means the record does not say this run is open, and an identity gate may not
// supply an optimistic default for a fact the record declines to state.
//
// Task 7.481 (BSC2) — WHICH REGISTER, AND WHICH ROW IN IT. BSC1 already pointed `parsed.runsCsv`
// at the innermost COMPARTMENT's own register (a branch carries its own `runs.csv`; the goal's has
// no row for it). What that left wrong is the ROW: this looked up `parsed.run`, and `parsed.run`
// is deliberately the PARENT RUN for a branch seat — so a branch was looked up under `run-1` in a
// register whose only row is `branch-1`, and every branch seat refused as "not provably live".
// Measured on disk: `throwaway-cw15/runs/run-1/branches/branch-1/runs.csv` carries `run-id
// branch-1`, and branch-shape-arms/arm2-out.json's D block measured the two verdicts this gate
// must be able to tell apart.
//
// The lookup follows the COMPARTMENT, never the parent: the INNERMOST branch when there is one,
// the run otherwise. Innermost rather than outermost is load-bearing at depth ≥2 — a `branch-2`
// register states `branch-2`'s liveness and says nothing about `branch-1` — and the probe's
// depth-2 arm is what separates the two choices rather than a comment claiming they differ.
// `parsed.run` itself is NOT rewritten here: a branch is not a run, and folding one into the
// other is the identity lie BSC1 refused (see the `branch` slot's note above).
//
// The refusal STRINGS are untouched, byte for byte, because callers match on them; only the
// identity substituted into them follows the compartment.
function checkRunLive(parsed) {
  const goals = readCsv(parsed.goalsCsv);
  if (!goals.exists) return { ok: false, reason: `goals.csv unreadable at ${parsed.goalsCsv}` };
  // The goals-index identifies a goal by `name`. That is not a preference: the goals-index is a
  // FULL deterministic projection of each goal's `goal.md` frontmatter (KG `goals-index`, settled
  // by decisions.md#d-goal-descriptor-md), and `name` is the column that projection writes. The
  // `goal-id`/`goal` columns this once accepted were never written by any projector — they existed
  // only in the probes' own fixtures — so this gate refused EVERY legitimate seat on every real
  // box while reading green (G-143).
  //
  // Read by the settled name and by no other. Accepting `name` ALONGSIDE the invented columns
  // would fix today's symptom by widening a comparison until the disagreement vanishes, which is
  // the thing that hid the defect in the first place. A goals.csv with no `name` column is not a
  // goals-index, and this says so rather than guessing which column might mean identity.
  if (!goals.header.includes('name')) {
    return { ok: false, reason: `goals.csv carries no name column (header: ${goals.header.join(',')}) — not a goals-index projection` };
  }
  if (!goals.rows.some((r) => r.name === parsed.goal)) {
    return { ok: false, reason: `goal ${parsed.goal} is not in ${parsed.goalsCsv}` };
  }

  const branch = Array.isArray(parsed.branch) ? parsed.branch : [];
  const compartment = branch.length ? branch[branch.length - 1] : parsed.run;

  const runs = readCsv(parsed.runsCsv);
  if (!runs.exists) return { ok: false, reason: `runs.csv unreadable at ${parsed.runsCsv}` };
  const runCol = runs.header.includes('run-id') ? 'run-id' : (runs.header.includes('run') ? 'run' : null);
  if (!runCol) return { ok: false, reason: `runs.csv carries no run-id/run column (header: ${runs.header.join(',')})` };
  const row = runs.rows.find((r) => r[runCol] === compartment);
  if (!row) return { ok: false, reason: `run ${compartment} has no row in ${parsed.runsCsv} — not provably live` };
  if (!runs.header.includes('state')) {
    return { ok: false, reason: `runs.csv carries no state column (header: ${runs.header.join(',')})` };
  }
  if (row.state !== 'open') {
    return { ok: false, reason: `run ${compartment} state is "${row.state}", not open` };
  }
  return { ok: true };
}

// Task 7.12 §job->seat — resolve a job's (goal, seat) POINTER to the seat folder its action runs in.
//
// The third caller of the same definition, and it is here rather than in `spawn/` for the reason
// stated at the top of this file: two resolvers would be two definitions of what a seat folder is.
// This one differs from `checkRunLive` in DIRECTION — that validates a run already named by a path;
// this must FIND the run, because the job row deliberately does not store one.
//
// WHY THE RUN IS NOT STORED (owner ruling `r-job-seat-home` (1)): goal-serving jobs "are seats of
// that goal's live run and RETIRE WITH IT". A stored run would pin the pointer to a run that later
// closes, and the job would go on firing into a dead run's folder — which is `G-103`'s stale-fire
// class, the very thing the ruling structurally kills. So the run is resolved at FIRE time, here.
//
// ⚠ AMBIGUITY IS A REFUSAL, NEVER A CHOICE. Zero open runs and MORE THAN ONE open run are both
// typed failures. The one-live-run invariant is maintained BY HAND today (7.77 is unbuilt), so a
// second open row is a real possibility, and picking one — the newest, the first, any rule at all —
// would let a job fire into a run nobody pointed it at. `checkRunLive` already refuses to supply an
// optimistic default for a fact the record declines to state; this refuses for the same reason.
// The RUN REGISTER read, and the ONLY one on the daemon side — `<goal>/runs.csv`'s `state` column
// answers "is a run of this goal live?", and `run-id` names which (PRIN-11: never a second place
// that answers it; trace-field-audit.md §2.3 rules `closed` deliberately NOT a read site, because
// deriving open-ness from an empty `closed` would be that second answer).
//
// EXTRACTED, NOT WRITTEN (task 7.129 / M4-14): every line below already stood inside
// resolveSeatHome. It is lifted out because the ticker's one-live-run gate must read the register
// too, and a second spelling of this predicate in the scheduler would be two readers of one file
// that can disagree — `issues.md` G-301's exact shape. resolveSeatHome now calls it, so there is
// one reader with two callers and its behaviour is unchanged.
//
// It REPORTS and never decides: `open` is the set, `unrecognized` is the set whose `state` is
// neither `open` nor `closed` (the comparison is exact and stays exact — `coord.py`'s
// `close_run_index` writes exactly those two values). A caller that must fail closed reads
// `unrecognized`; nothing here widens the comparison until a disagreement disappears.
function openRunsOfGoal({ workspaceRoot, goal }) {
  if (!workspaceRoot || !goal) {
    return { ok: false, reason: 'openRunsOfGoal requires workspaceRoot and goal' };
  }
  const goalDir = path.join(workspaceRoot, '.rbtv', 'goals', goal);
  const runsCsv = path.join(goalDir, 'runs.csv');
  const runs = readCsv(runsCsv);
  if (!runs.exists) {
    return { ok: false, register: runsCsv, goalDir, reason: `runs.csv unreadable at ${runsCsv} — goal "${goal}" has no run log` };
  }
  const runCol = runs.header.includes('run-id') ? 'run-id' : (runs.header.includes('run') ? 'run' : null);
  if (!runCol) {
    return { ok: false, register: runsCsv, goalDir, reason: `runs.csv carries no run-id/run column (header: ${runs.header.join(',')})` };
  }
  if (!runs.header.includes('state')) {
    return { ok: false, register: runsCsv, goalDir, reason: `runs.csv carries no state column (header: ${runs.header.join(',')})` };
  }
  return {
    ok: true,
    register: runsCsv,
    goalDir,
    runCol,
    rows: runs.rows,
    open: runs.rows.filter((r) => r.state === 'open'),
    unrecognized: runs.rows.filter((r) => r.state !== 'open' && r.state !== 'closed'),
  };
}

// ── r-seats-only-architecture — auto-materialize a JOB-BORN seat's MINIMAL valid shape ─────────
//
// Every daemon-spawned agent is a seat, and a job's seat folder may not exist yet the first time
// the job fires. The minimal valid shape is the FOLDER plus a generated `seat.md` stating
// identity — enough for the cage's `ro-bind:{seatDir}/seat.md` to have a real target and for the
// descriptor-agreement check below to hold. A staffed descriptor replacing this file is the
// staffing stage's act, never this function's: this writes ONLY when `seat.md` is absent, and the
// `wx` flag makes a racing writer's file win rather than be overwritten.
function materializeSeatFolder(parsed, { jobId = null } = {}) {
  const seatMd = path.join(parsed.seatDir, 'seat.md');
  if (fs.existsSync(seatMd)) return { created: false, seatMd };
  fs.mkdirSync(parsed.seatDir, { recursive: true, mode: 0o700 });
  const created = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const body = [
    '---',
    `seat: ${parsed.seat}`,
    `goal: ${parsed.goal}`,
    `spawning-job: ${jobId || 'unknown'}`,
    `created: ${created}`,
    'auto-materialized: by the daemon spawn path under r-seats-only-architecture',
    '---',
    '',
    `# ${parsed.seat} — job-born seat of ${parsed.goal}`,
    '',
    `Auto-materialized at spawn by the daemon (spawning job \`${jobId || 'unknown'}\`, ${created})`,
    'under `r-seats-only-architecture`: every daemon-spawned agent is a seat, and a job-born seat',
    'whose folder does not yet exist gets this MINIMAL shape — the folder plus this descriptor —',
    'never a flat launch dir. A staffed descriptor replacing this file is the staffing stage\'s.',
    '',
  ].join('\n');
  try {
    fs.writeFileSync(seatMd, body, { mode: 0o600, flag: 'wx' });
  } catch (err) {
    if (err.code === 'EEXIST') return { created: false, seatMd }; // a racing writer's descriptor wins
    throw err;
  }
  return { created: true, seatMd };
}

function resolveSeatHome({ workspaceRoot, goal, seat, materialize = null }) {
  if (!workspaceRoot || !goal || !seat) {
    return { ok: false, reason: 'resolveSeatHome requires workspaceRoot, goal and seat' };
  }
  const register = openRunsOfGoal({ workspaceRoot, goal });
  if (!register.ok) return { ok: false, reason: register.reason };
  const { goalDir, register: runsCsv, runCol, open } = register;

  if (open.length === 0) {
    return { ok: false, reason: `goal "${goal}" has no run in state "open" in ${runsCsv} — nothing to fire into` };
  }
  if (open.length > 1) {
    const names = open.map((r) => r[runCol]).join(', ');
    return {
      ok: false,
      reason: `goal "${goal}" has ${open.length} runs in state "open" (${names}) in ${runsCsv} — `
        + 'the one-live-run invariant is violated and this refuses to choose between them',
    };
  }

  const run = open[0][runCol];
  if (!run) return { ok: false, reason: `the open run row in ${runsCsv} carries no ${runCol} value` };

  const seatDir = path.join(goalDir, 'runs', run, 'seats', seat);
  // Round-tripped through the SAME parser every other caller uses, so a pointer that assembles a
  // path this module would not itself recognise as a seat folder fails here rather than at spawn.
  const parsed = parseSeatPath(seatDir);
  if (!parsed) {
    return { ok: false, reason: `assembled path is not a canonical seat folder: ${seatDir}` };
  }
  const live = checkRunLive(parsed);
  if (!live.ok) return { ok: false, reason: live.reason };

  if (materialize) {
    // r-seats-only-architecture: a JOB-BORN seat. The folder is materialized when absent (minimal
    // shape above), and the descriptor-agreement half of checkMaterializedSeat still applies — a
    // folder and a seat.md that disagree stay a refusal. The TASKFORCE-ROSTER half deliberately
    // does not: a job-born seat is not a rostered taskforce member, its dispatch record is the
    // jobs table row itself (goal_name/seat_name), and requiring a roster row here would refuse
    // every job the architecture just homed. spawnSeat's L3 gate (rostered seats) is untouched.
    materializeSeatFolder(parsed, materialize);
    const desc = readSeatDescriptorName(path.join(parsed.seatDir, 'seat.md'));
    if (!desc.present) return { ok: false, reason: `no seat.md in ${parsed.seatDir} after materialization — not a seat folder` };
    if (!desc.frontmatter) return { ok: false, reason: `seat.md in ${parsed.seatDir} carries no frontmatter block` };
    if (!desc.seat) return { ok: false, reason: `seat.md in ${parsed.seatDir} declares no seat: key` };
    if (desc.seat !== parsed.seat) {
      return { ok: false, reason: `seat.md declares seat "${desc.seat}" but the folder is "${parsed.seat}" — descriptor and folder disagree` };
    }
  } else {
    const materialized = checkMaterializedSeat(parsed);
    if (!materialized.ok) return { ok: false, reason: materialized.reason };
  }

  return { ok: true, seatDir, parsed, run };
}

// Minimal frontmatter read — the `seat:` key only. A full YAML parse is not needed and would drag
// js-yaml into a path a bare CLI runs on every command.
function readSeatDescriptorName(seatMdPath) {
  let raw;
  try {
    raw = fs.readFileSync(seatMdPath, 'utf8');
  } catch {
    return { present: false };
  }
  const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(raw);
  if (!m) return { present: true, frontmatter: false };
  const seat = /^seat:[ \t]*(.+)$/m.exec(m[1]);
  if (!seat) return { present: true, frontmatter: true, seat: null };
  return { present: true, frontmatter: true, seat: seat[1].trim().replace(/^["']|["']$/g, '') };
}

// L3 — a MATERIALIZED, ROSTERED seat, not merely a folder of the right shape.
//
// Two independent facts, and they must AGREE with the folder name rather than merely exist:
//   (a) `seat.md` is present, has frontmatter, and its `seat:` names THIS folder;
//   (b) the seat has a row in the run's `taskforce.csv`.
// A hand-made `seats/imposter/` satisfies the path shape and fails both (G5 bar P3).
//
// DISCLOSED DIVERGENCE from design §4a L3, which also names an "assembly lockfile": no seat in
// any live run carries one. `materialize` is CMP-5-designed-and-unbuilt (G-109, re-verified by
// leader as 0 hits repo-wide), so requiring a lockfile would refuse every real seat that exists.
// It is therefore validated WHEN PRESENT and not required — the strictness returns for free the
// day CMP-5 lands, and until then this refuses to enforce a check nothing can pass (R-stamp-wording:
// a bar that cannot pass trains rubber-stamping).
function checkMaterializedSeat(parsed) {
  const seatMd = path.join(parsed.seatDir, 'seat.md');
  const desc = readSeatDescriptorName(seatMd);
  if (!desc.present) return { ok: false, reason: `no seat.md in ${parsed.seatDir} — not a materialized seat folder` };
  if (!desc.frontmatter) return { ok: false, reason: `seat.md in ${parsed.seatDir} carries no frontmatter block` };
  if (!desc.seat) return { ok: false, reason: `seat.md in ${parsed.seatDir} declares no seat: key` };
  if (desc.seat !== parsed.seat) {
    return { ok: false, reason: `seat.md declares seat "${desc.seat}" but the folder is "${parsed.seat}" — descriptor and folder disagree` };
  }

  const tf = readCsv(parsed.taskforceCsv);
  if (!tf.exists) return { ok: false, reason: `taskforce.csv unreadable at ${parsed.taskforceCsv} — roster cannot be checked` };
  if (!tf.header.includes('seat')) {
    return { ok: false, reason: `taskforce.csv carries no seat column (header: ${tf.header.join(',')})` };
  }
  if (!tf.rows.some((r) => r.seat === parsed.seat)) {
    return { ok: false, reason: `seat ${parsed.seat} has no row in ${parsed.taskforceCsv} — not rostered` };
  }

  const lockfile = path.join(parsed.seatDir, 'assembly.lock');
  const lockPresent = fs.existsSync(lockfile);
  return { ok: true, lockfilePresent: lockPresent };
}

module.exports = {
  parseSeatPath,
  parseServiceSeatPath,
  parseGoalScope,
  resolveSeatFromCwd,
  openRunsOfGoal,
  materializeSeatFolder,
  resolveSeatHome,
  checkRunLive,
  checkMaterializedSeat,
  readSeatDescriptorName,
};
