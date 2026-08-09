'use strict';

// Task 7.11 §4a/§4b step 1 — resolving a path to a SEAT.
//
// One resolver, two callers, deliberately: the launch-time gate (`spawnSeat`, which is handed a
// seat folder) and the command-time gate (a system CLI, which walks up from its own cwd) must
// agree on what a seat folder IS. Two resolvers would be two definitions, and the failure that
// produces — a launch landing somewhere the checker later refuses to recognise — is invisible
// until a seat is already sitting in it.
//
// The canonical shape (KG `seat folder`) — 7.607 E2a, GOAL-DIRECT:
//     <ws>/.rbtv/goals/<goal>/seats/<seat>/
//
// ── 7.607 E2a — THE RUN SEGMENT IS GONE, AND THE GRAMMAR ACCEPTS ONLY THE NEW SHAPE ────────────
//
// `decisions.md#d-runs-extinguished` + `#d-extinguishment-design-lock` (items 6, 9): a goal's
// working content sits DIRECTLY under `goal/`. There is no `runs/run-N/` segment, no `runs.csv`,
// no `branches/branch-M/` compartment. CUT CLEAN — this parser does NOT accept the old shape
// alongside the new one. A dual grammar would be two definitions of what a seat folder is, which
// is the exact failure the header above exists to prevent, and nothing live depends on the old
// shape (E4 migrates the live goal folders before anything boots again).
//
// WHAT DIED WITH THE SEGMENT, named so a reader does not go hunting: `RUN_NAME_RE`, `parsed.run`,
// `parsed.runsCsv`, `checkRunLive`, `openRunsOfGoal`, and the WHOLE branch-compartment walk
// (`BRANCHES_DIR`/`BRANCH_NAME_RE`, `parsed.branch`, `parsed.branchDir`). The branch machinery is
// abolished by registry ruling `r-branch-folder-deleted-nested-seats-are-ordinary-run-seats` — a
// branch is a ROLE with NO file home, and a branch seat is an ordinary seat of the goal named
// `<four-letters>-<n>-<seat>`. Deleted, never migrated.
//
// SEAT LIVENESS IS NOT ANSWERED HERE ANY MORE. "Is this goal executing" is `server/lease/lease.js`
// (E1, design-lock item 1): live evidence, no stored status. `checkGoalExecuting` below is the
// thin adapter that routes the question there; it computes no lease of its own (PRIN-11).
//
// SEAT FOLDERS ARE GOAL-DURABLE. `materializeSeatFolder`/`resolveSeatHome` create and resolve at
// GOAL level, which is the ruling's memory mechanism: the same goal performed twice boots from the
// same `seats/<seat>/` folders, and whatever the seat accumulated is still there.
//
// ⚠ `parsed.runDir` SURVIVES AS AN ALIAS OF `goalDir`, DELIBERATELY, AND IT IS A DISCLOSED SEAM.
// `config/spawn-profiles.yaml`'s shipped `SeatBinds` template consumes the cage slots `{goalDir}`
// and `{runDir}` (`cage.js SCALAR_SLOTS`), and that file is outside this stage's write surface. A
// dropped field would leave the slot valueless and every caged spawn would die at compose time
// with `E_CAGE_TEMPLATE`. Aliased to the goal dir the shipped template stays CORRECT under the new
// layout — `tmpfs:{runDir}/seats` still erases peer seat folders, `bind:{runDir}/coordination` is
// still the goal's coordination dir. The profile's slot rename is a later stage's one-file edit.
//
// Everything here is derived from the PATH and from files on disk. Nothing is asserted by the
// caller — no env var, no flag, no name passed in. That is G-111's lesson wired into the shape of
// the module rather than written in a comment beside it: tonight `COORD_AGENT` (asserted)
// outranked pane resolution (verified) and two agents spoke under one roster name for an hour.

const fs = require('node:fs');
const path = require('node:path');
const { readCsv } = require('./csv');
const { deriveLease } = require('../lease/lease');

// Parse the canonical shape out of an ABSOLUTE, REAL path. Returns null when the path is not a
// seat folder — the caller decides which typed refusal that becomes, because "you launched into
// a non-seat folder" and "you ran a CLI from a non-seat folder" are different failures with
// different remedies even though they share this test.
// r-master-seat-homes (owner, 2026-08-06): a SERVICE SEAT — a seat-shaped folder directly
// under .rbtv/goals/ named _<seat>, with NO goal apparatus (no goal.md, no taskforce):
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
    service: true,
  };
}

// THE GRAMMAR, and it is now FIXED-OFFSET because the shape is fixed.
//
//     <ws>/.rbtv/goals/<goal>/seats/<seat>/
//
// The 7.480 walk this replaced existed for ONE reason: a branch level inserted a variable number
// of segments between the compartment and `seats`, so no constant offset was the right one. With
// the branch machinery abolished (`r-branch-folder-deleted-nested-seats-are-ordinary-run-seats`)
// and the run segment extinguished, the depth is a constant again — `goal` is exactly one segment
// above `seats` — and the offsets are the honest expression of that. Nothing is folded: a nested
// seat is an ORDINARY seat of the goal whose NAME carries its lineage, so there is no fourth
// identity component left to give a slot to.
//
// The anchor is still CHECKED rather than assumed: `.rbtv`/`goals` must be where the offsets say
// they are, and the probe's red arm removes one to prove the check is load-bearing. And the search
// still starts from `seats` upward rather than from `.rbtv/goals` downward, which is what keeps
// `…/seats/<seat>/seats/x` refused instead of admitted.
function parseSeatPath(absPath) {
  const parts = path.normalize(absPath).split(path.sep);
  // …/.rbtv/goals/<goal>/seats/<seat>
  const seatsIdx = parts.lastIndexOf('seats');
  if (seatsIdx < 0 || seatsIdx + 1 >= parts.length) return null;
  const seat = parts[seatsIdx + 1];
  if (!seat) return null;

  const goalIdx = seatsIdx - 1;
  const goalsIdx = seatsIdx - 2;
  const rbtvIdx = seatsIdx - 3;
  if (rbtvIdx < 1) return null;
  if (parts[goalsIdx] !== 'goals' || parts[rbtvIdx] !== '.rbtv') return null;
  const goal = parts[goalIdx];
  if (!goal) return null;

  const workspaceRoot = parts.slice(0, rbtvIdx).join(path.sep) || path.sep;
  const goalDir = parts.slice(0, goalIdx + 1).join(path.sep);
  const seatDir = parts.slice(0, seatsIdx + 2).join(path.sep);
  return {
    workspaceRoot,
    goal,
    seat,
    goalDir,
    // The disclosed cage-slot alias — see the header. Goal-direct means the goal folder IS the
    // package, so `{runDir}` and `{goalDir}` resolve to the same real directory.
    runDir: goalDir,
    seatsDir: parts.slice(0, seatsIdx + 1).join(path.sep),
    seatDir,
    sessionsCsv: path.join(goalDir, 'sessions.csv'),
    goalsCsv: path.join(parts.slice(0, goalsIdx + 1).join(path.sep), 'goals.csv'),
    taskforceCsv: path.join(goalDir, 'taskforce.csv'),
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

// L2 — the goal is KNOWN (it is in the goals-index) and it is EXECUTING RIGHT NOW.
//
// ── 7.607 E2a — THIS IS `checkRunLive` RE-FOUNDED, NOT RENAMED ─────────────────────────────────
//
// The old body read `<compartment>/runs.csv`'s `state` column: a STORED STATUS, and the register
// era's whole defect class. `state=open` outlives the thing it describes, so every reader of it
// answered a question about the past believing it read the present — G-103's stale fire, and the
// 7.608 deadlock where a stale open row refused the start of a run nobody was running.
//
// The liveness half is now `server/lease/lease.js` and NOTHING is computed here (PRIN-11, design
// lock item 1: "NO stored status of any kind"). This function is the ADAPTER its three callers
// share — the command-time gate (identity.js), the launch-time gate (spawn.js spawnSeat) and
// `resolveSeatHome` below — so there is one place that says what L2 means and one place that says
// how liveness is measured, and they are not the same place.
//
// THE GOALS-INDEX READ SURVIVES, and it is a different question from liveness. `goals.csv` is the
// deterministic projection of every goal's `goal.md` frontmatter (`d-goal-descriptor-md`), read by
// its settled column `name` and by no other — G-143 was this gate accepting invented column names
// and refusing every real seat on every real box while reading green. A goal that is not in the
// index is not a goal this daemon knows, whatever a tmux session happens to be called.
//
// ⚠ THE TWO REFUSALS ARE KEPT DISTINCT, and the order is deliberate: "this goal is unknown" is a
// different remedy from "this goal is not executing", and unreadable evidence is a THIRD thing
// again. `deriveLease` reports `{ok:false}` for ignorance (tmux gone) and never a verdict; this
// gate's posture on ignorance is CLOSED, because an identity gate may not admit on a fact it
// could not measure. That posture is stated HERE rather than in the lease, which decides nothing.
//
// `readLease` is the injection point a probe supplies a fixture tmux server through — E1's own
// pattern at `ticker/one-live-run.js#decide`. A probe supplies real measurables, never a verdict.
function checkGoalExecuting(parsed, { readLease = deriveLease } = {}) {
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

  const lease = readLease({ workspaceRoot: parsed.workspaceRoot, goal: parsed.goal });
  if (!lease.ok) {
    return {
      ok: false,
      reason: `the lease of goal ${parsed.goal} is UNREADABLE (${lease.reason}) — this gate refuses `
        + 'on ignorance rather than admitting on a fact it could not measure',
    };
  }
  if (!lease.live) {
    return {
      ok: false,
      reason: `goal ${parsed.goal} is not executing — no room of its own exists right now `
        + `(${lease.evidence['room-predicate']})`,
    };
  }
  return { ok: true };
}

// WHERE A GOAL'S FOLDER IS, spelled once (task C3). It was first spelled inside the (now deleted)
// run-register reader; a second caller needed it (`ticker/goal-channel-start.js` asks `goalKind()`
// for a goal it knows only by NAME), and a private copy of a layout constant is the cheapest drift —
// `<ws>/.rbtv/goals/` moving would leave one of the two copies right. It is a pure join and reads
// nothing: an absent folder is the caller's answer to give, not this function's.
function goalDirOf({ workspaceRoot, goal }) {
  if (!workspaceRoot || !goal) return null;
  return path.join(workspaceRoot, '.rbtv', 'goals', goal);
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

// Task 7.12 §job->seat — resolve a job's (goal, seat) POINTER to the seat folder its action runs in.
//
// ── 7.607 E2a — THERE IS NO LONGER A RUN TO FIND ───────────────────────────────────────────────
//
// The old body's hard part was RESOLUTION: the job row deliberately stores no run
// (`r-job-seat-home` (1) — a stored run pins the pointer to a run that later closes, G-103's
// stale-fire class), so this had to ASK the register which run was open, and refuse on zero or on
// two. With the layer extinguished the question has no subject: a goal has ONE seats tree, at
// `<goal>/seats/<seat>/`, and it is GOAL-DURABLE. The ambiguity refusal dies with the ambiguity —
// there is nothing left to choose between, so nothing left to refuse choosing between.
//
// What SURVIVES is the ruling's actual intent, and it is now the lease's job: a job may not fire
// into a goal that is not EXECUTING. `checkGoalExecuting` asks that at FIRE time, exactly as the
// register read did, and fails closed on unreadable evidence for the same reason it always did.
function resolveSeatHome({ workspaceRoot, goal, seat, materialize = null, readLease = deriveLease }) {
  if (!workspaceRoot || !goal || !seat) {
    return { ok: false, reason: 'resolveSeatHome requires workspaceRoot, goal and seat' };
  }
  const seatDir = path.join(goalDirOf({ workspaceRoot, goal }), 'seats', seat);
  // Round-tripped through the SAME parser every other caller uses, so a pointer that assembles a
  // path this module would not itself recognise as a seat folder fails here rather than at spawn.
  const parsed = parseSeatPath(seatDir);
  if (!parsed) {
    return { ok: false, reason: `assembled path is not a canonical seat folder: ${seatDir}` };
  }
  const live = checkGoalExecuting(parsed, { readLease });
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

  return { ok: true, seatDir, parsed };
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

// THE ONE READ SITE FOR A GOAL'S KIND (owner ruling `d-owner-batch1` (2), 2026-08-08).
//
// The ruling settles two things a consumer must not re-decide: `goal-kind` is OPTIONAL goal.md
// frontmatter defaulting to `interactive`, and the CARRIER IS THE FRONTMATTER — the kind is
// looked up here, never carried on a queue row. So a caller asks this function; it never reads
// `goal.md` itself and never spells the default a second time. Two readers of one file free to
// disagree is `issues.md` G-301's shape, and a second copy of a ruled default is how the default
// silently forks the day one copy is edited.
//
// It lives beside `readSeatDescriptorName` and copies its idiom deliberately: a regex read of one
// frontmatter key, no `js-yaml`, because this sits on the ticker's per-tick launch path and a full
// YAML parse to answer a one-word question is a dependency bought for nothing.
//
// ABSENCE IS NOT AN ERROR — it is the majority case and it is the reason this returns a value
// rather than a verdict. Every goal scaffolded before the field existed carries no key, and the
// ruling says those read `interactive`. An unreadable goal.md, a descriptor with no frontmatter,
// and a value outside the enum resolve the same way for the same reason: the caller's question is
// "which kind do I treat this goal as", and there is no answer to that question that is not one of
// the two kinds. A malformed value is REPORTED by `goal_cli.py lint`'s enum check ("goal kind in
// enum"), which is the surface built to name it; making the launch path fail on it instead would
// take the daemon down for a typo lint already catches.
//
// ⚠ THAT LAST SENTENCE IS ONLY TRUE IF THE TWO READERS AGREE ON WHAT THE VALUE IS. `goal_cli.py`
// reads this same frontmatter with `yaml.safe_load`; this reads it with a regex. Where they
// disagree, lint reports NOTHING (it sees a clean value) and the launch path silently defaults —
// so the named safety surface is blind by construction on exactly the inputs it exists to catch.
// One ordinary YAML shape lands there and it is the reason for the strip below: a trailing
// comment. `goal-kind: non-interactive # batch` is `non-interactive` to YAML and lints clean,
// while an unstripped regex read is out-of-enum and resolves `interactive` — a BATCH goal handed
// a Slack channel with nothing anywhere reporting it. Measured 2026-08-08 (A3/C3 review) on a
// scaffolded fixture: control skips, the same file plus a comment ensures, `lint` names neither.
const GOAL_KINDS = ['interactive', 'non-interactive'];
const GOAL_KIND_DEFAULT = 'interactive';

function goalKind(goalDir) {
  if (!goalDir || typeof goalDir !== 'string') return GOAL_KIND_DEFAULT;
  let raw;
  try {
    raw = fs.readFileSync(path.join(goalDir, 'goal.md'), 'utf8');
  } catch {
    return GOAL_KIND_DEFAULT;
  }
  const fm = /^---\r?\n([\s\S]*?)\r?\n---/.exec(raw);
  if (!fm) return GOAL_KIND_DEFAULT;
  const declared = /^goal-kind:[ \t]*(.+)$/m.exec(fm[1]);
  if (!declared) return GOAL_KIND_DEFAULT;
  // Strip a YAML trailing comment BEFORE the enum test, so this reader and lint's `yaml.safe_load`
  // resolve the same value (see the ⚠ above). Whitespace before `#` is what starts a comment in
  // YAML — `a#b` is the scalar `a#b` — so the pattern is `\s+#`, never a bare `#`.
  const kind = declared[1].replace(/\s+#.*$/, '').trim().replace(/^["']|["']$/g, '');
  return GOAL_KINDS.includes(kind) ? kind : GOAL_KIND_DEFAULT;
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
  goalDirOf,
  materializeSeatFolder,
  resolveSeatHome,
  checkGoalExecuting,
  checkMaterializedSeat,
  readSeatDescriptorName,
  goalKind,
  GOAL_KINDS,
  GOAL_KIND_DEFAULT,
};
