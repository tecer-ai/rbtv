'use strict';

// ── THE APPROVED GOAL'S EXECUTION START, RUN DAEMON-SIDE (owner ruling 2026-08-24, option (b),
// `redesign-implementation/decisions.md`) ────────────────────────────────────────────────────────
//
// THE GAP THIS CLOSES. `spec-owner-io` §4.2 makes `approve` in a `kind=approval` thread the D12
// trigger that BIRTHS AN EXECUTION GOAL [D-5-ruling, CF-7]; `ignite/planning/path_b.py#run_path_b`
// is the supervised birth it must call. The bridge could not call it: `bridges/chat` runs as a
// SEPARATE PROCESS and `probes/probe-chat-boundary.js` forbids a child process, a store handle and
// a sibling require in that subtree — so `approve` reached a `materialize` port that was never
// wired and degraded LOUDLY into the approval thread [C-16] instead of starting anything.
//
// The owner ruled option (b) on 2026-08-24: mint ONLY `start-execution`, whose daemon-side executor
// calls the Path-B birth, same pattern as the thirteenth (`record-owner-ask`). This module is that
// executor. The pause-word intent was deliberately NOT minted — pause stays store-side until the
// execution-lane reconcile gate converges onto the goal-state row — so nothing here touches a lane.
//
// ⚑ THE BRIDGE PROVES NOTHING AND IS TRUSTED FOR NOTHING. A `kind=approval` thread is a fact of
// the BRIDGE's `askThreads` map, which lives in the calling process and is therefore not evidence.
// What this module checks instead is the record the daemon itself wrote (`open_asks`, the
// thirteenth intent's table) plus the plan the planning goal itself carries:
//
//   1. THE THREAD IS AN ASK THIS DAEMON OPENED. `ask_id` IS the Slack thread [T5-R7], so a caller
//      cannot point a start at a conversation the daemon never recorded.
//   2. IT IS BOUND TO THE GOAL THE CALLER NAMES — a thread belonging to another goal must not
//      start this one, exactly as `ask-record.js#reapAsk` refuses a reap across the pair.
//   3. IT WAS RELEASED BY AN AUTHORIZED OWNER REPLY. `authorized_reply_at` is stamped by
//      `reapAndRelaunch`, which only the §2.4 release door reaches (exact thread, authorized
//      sender, parse, reap). An un-reaped thread is a thread nobody approved in, and this is the
//      check that makes a NON-APPROVAL-THREAD caller a refusal rather than an execution goal.
//   4. THE COMMIT IS THE ONE THE PLAN IS BOUND TO [T5-R5]. The approval message published a
//      `commit_id`; the approve-package on the planning goal names `bound_commit`. They must be
//      the same string, or the owner approved one tree and the daemon would build another.
//
// ⚑ THE BIRTH IS NOT PERFORMED HERE AND NOT IN JAVASCRIPT AT ALL, exactly as the twelfth intent's
// bus write is `coord.py`'s: `planning/path_b.py` is the ONE Path-B caller and it runs through
// `wrapper.py#supervised_materialize` (validate → uncast → scaffold → lock → mint → release, with
// the C-16 reclaim). This module validates, authorizes upstream, and delegates.
//
// ⚑ A SUPERVISED-MATERIALIZE FAILURE COMES BACK AS DATA CARRYING ITS RECORD, never as a throw.
// The wrapper has ALREADY written the six-field failure record onto the PLANNING goal
// (`failure.py#write_failure_record`, routed there by `record_goal_folder=` because a birth that
// failed has no execution goal to stamp). The caller's job with that record is to put it in front
// of the owner in the approval thread [C-16] — which is a report, not an error to swallow. The
// refusals ABOVE are different in kind and are typed errors at the handler: nothing was attempted.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { bind } = require('../../state-store');
const { requirePythonCmd } = require('../../lib/python-cmd');

// A THIRD copy of the name shape, checked against the module that owns it — `ask-record.js`'s
// reason verbatim: these names arrive from an internet-facing component and become PATH SEGMENTS
// under `.rbtv/goals/`.
const { isSafeName } = require('../../bridges/chat/bus-ferry');

const PATH_B_PY = path.join(__dirname, '..', '..', 'planning', 'path_b.py');

// The approve-package the planning pipeline leaves for the birth. `<planning goal>/planning/` is
// where Path B already writes its own bound-plan pointer, so the plan and the pointer to it sit in
// one folder rather than two conventions.
const APPROVE_PACKAGE = path.join('planning', 'approve-package.json');

// SHA-1 or SHA-256, lowercase hex, never a ref name. A branch or a tag would be a MOVING binding,
// which is the one thing [T5-R5] exists to prevent.
const COMMIT_RE = /^[0-9a-f]{7,64}$/;

// Long enough for scaffold + mint on a real tree, short enough that a wedged birth answers the
// owner instead of holding the request forever. The bridge's own call carries a matching override
// (`live-feed`'s precedent: one intent's patience, never a raised default).
const PATH_B_TIMEOUT_MS = 120000;

function goalDirOf(workspaceRoot, goal) {
  return path.join(workspaceRoot, '.rbtv', 'goals', String(goal));
}

function goalsRootOf(workspaceRoot) {
  return path.join(workspaceRoot, '.rbtv', 'goals');
}

// Every reason a start must NOT be attempted, as a refusal object. These are the questions the
// gateway holds no handle for and must not grow one: does the goal exist, is there a genuine
// approval record on this thread, and is the caller's commit the one the plan is bound to.
function refuseReason(heartStore, { workspaceRoot, goal, thread, commit }) {
  for (const [field, value] of [['goal', goal], ['thread', thread]]) {
    if (!isSafeName(value)) return { reason: 'bad-name', detail: `${field} is not a bare safe name` };
  }
  if (!COMMIT_RE.test(String(commit || ''))) {
    return { reason: 'bad-commit', detail: 'commit must be lowercase hex, 7-64 chars — a ref name is a moving binding [T5-R5]' };
  }
  const goalDir = goalDirOf(workspaceRoot, goal);
  if (!fs.existsSync(goalDir)) return { reason: 'no-such-goal', detail: `no goal folder for ${goal}` };

  let row;
  try {
    row = bind(heartStore.db).getAsk(String(thread));
  } catch (err) {
    return { reason: 'store-refused', detail: err.message };
  }
  // (1) THE THREAD IS AN ASK THIS DAEMON OPENED. A caller naming a thread the daemon never
  // recorded is naming a conversation, not an approval.
  if (!row) return { reason: 'no-approval-record', detail: `no ask on thread ${thread} — this is not an approval thread` };
  // (2) BOUND TO THE PAIR IT NAMES.
  if (String(row.goal) !== String(goal)) {
    return { reason: 'ask-not-bound-here', detail: `thread ${thread} belongs to ${row.goal}` };
  }
  // (3) RELEASED BY AN AUTHORIZED OWNER REPLY. Only the §2.4 door's reap stamps this.
  if (!row.authorized_reply_at || row.state === 'open') {
    return { reason: 'ask-not-released', detail: `ask ${thread} carries no authorized owner reply — nothing approved it` };
  }
  return null;
}

// The plan the owner approved, read from the planning goal's own folder. Refused rather than
// defaulted at every step: a birth with a guessed package is a birth of something nobody read.
function readApprovePackage({ workspaceRoot, goal, commit }) {
  const goalDir = goalDirOf(workspaceRoot, goal);
  const file = path.join(goalDir, APPROVE_PACKAGE);
  if (!fs.existsSync(file)) {
    return { ok: false, reason: 'no-approve-package', detail: `${goal} carries no ${APPROVE_PACKAGE}` };
  }
  let pkg;
  try {
    pkg = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (err) {
    return { ok: false, reason: 'bad-approve-package', detail: err.message };
  }
  if (!pkg || typeof pkg !== 'object' || Array.isArray(pkg)) {
    return { ok: false, reason: 'bad-approve-package', detail: 'the approve package must be a JSON object' };
  }
  if (!isSafeName(pkg.execution_goal)) {
    return { ok: false, reason: 'bad-approve-package', detail: 'execution_goal is not a bare safe name' };
  }
  // (4) THE COMMIT THE OWNER SAW IS THE COMMIT THE PLAN IS BOUND TO [T5-R5].
  if (String(pkg.bound_commit || '') !== String(commit)) {
    return {
      ok: false,
      reason: 'commit-not-bound',
      detail: `the approval names ${commit}; the package is bound to ${pkg.bound_commit || 'nothing'}`,
    };
  }
  // A package that names a DIFFERENT goal tree is a package copied here from somewhere else. The
  // daemon's derivation wins, but a disagreement is refused rather than silently overwritten —
  // overwriting would let a stale copy read as the plan this goal approved.
  const goalsRoot = goalsRootOf(workspaceRoot);
  if (pkg.planning_goal !== undefined && path.resolve(String(pkg.planning_goal)) !== path.resolve(goalDir)) {
    return { ok: false, reason: 'package-not-bound-here', detail: `package names planning goal ${pkg.planning_goal}` };
  }
  if (pkg.goals_root !== undefined && path.resolve(String(pkg.goals_root)) !== path.resolve(goalsRoot)) {
    return { ok: false, reason: 'package-not-bound-here', detail: `package names goals root ${pkg.goals_root}` };
  }
  return {
    ok: true,
    pkg: {
      ...pkg,
      // The three fields the DAEMON owns, stamped rather than read: where the birth lands, which
      // planning goal receives the D12 failure record, and which thread this act came from (the
      // failure record's `origin_id`, so a record can be traced back to the approval that caused it).
      planning_goal: goalDir,
      goals_root: goalsRoot,
      bound_commit: String(commit),
    },
    file,
  };
}

// Run the supervised Path-B birth. Injectable ONLY for the probe (`runPathB`), for the reason every
// injected port in this tree carries: a probe must be able to prove the ladder above without a git
// tree, a goals catalogue and a python interpreter — never so production can stub the birth out.
function startExecution(heartStore, { workspaceRoot, goal, thread, commit, runPathB = null }) {
  const refusal = refuseReason(heartStore, { workspaceRoot, goal, thread, commit });
  if (refusal) return { started: false, ...refusal };

  const read = readApprovePackage({ workspaceRoot, goal, commit });
  if (!read.ok) return { started: false, reason: read.reason, detail: read.detail };

  const pkg = { ...read.pkg, origin_id: String(thread) };
  const run = typeof runPathB === 'function' ? runPathB : runPathBSubprocess;
  let out;
  try {
    out = run(pkg);
  } catch (err) {
    return { started: false, reason: 'path-b-unreachable', detail: err.message };
  }
  if (!out || out.ok !== true) {
    // THE C-16 PATH THAT ALREADY EXISTS: `wrapper.py` wrote this record onto the planning goal
    // before returning. It travels back so the approval thread can show it [C-16].
    return {
      started: false,
      reason: 'materialize-failed',
      detail: (out && out.record && (out.record.reason || out.record.code)) || 'path B refused',
      record: (out && out.record) || null,
    };
  }
  return { started: true, execution_goal: pkg.execution_goal, record: null };
}

function runPathBSubprocess(pkg) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'start-execution-'));
  const file = path.join(dir, 'approve-package.json');
  try {
    fs.writeFileSync(file, `${JSON.stringify(pkg, null, 2)}\n`);
    // `path_b.py` exits 2 on a refusal and still prints its `{ok, record}` on stdout, so a
    // non-zero status is READ, never treated as a crash — the record is the whole point.
    let stdout;
    try {
      stdout = execFileSync(requirePythonCmd(), [PATH_B_PY, '--package', file], {
        encoding: 'utf8', timeout: PATH_B_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'],
      });
    } catch (err) {
      stdout = err.stdout;
      if (!stdout) throw err;
    }
    return JSON.parse(String(stdout));
  } finally {
    try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
  }
}

module.exports = { startExecution, APPROVE_PACKAGE, COMMIT_RE, PATH_B_TIMEOUT_MS };
