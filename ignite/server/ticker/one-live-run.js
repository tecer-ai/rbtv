'use strict';

// ── R9's ONE-LIVE-RUN RULE on the daemon's job-scheduling path (task 7.77 → 7.129 / M4-14) ──────
//
// A scheduled start that lands while a run of the SAME GOAL is open is QUEUED, never started.
//
// THE FAILURE THIS PREVENTS: two runs of one goal live at once. A run folder is the mortal working
// state of exactly ONE run; two live runs write the same registers, and the resulting state is not
// recoverable by reading it — afterwards nothing tells you which run wrote which row. Until this
// landed, one-live-run was a CONVENTION the room held by hand, and R10's goal-level watcher state
// was valid only because of that hand-held guarantee (`coord.py resolve_live_run`'s own comment
// says so, and `seat-folder.js` refuses rather than guesses for the same reason).
//
// A SKIP IS NOT AN ACCEPTABLE OUTCOME EITHER — 7.77 is explicit that the rule "never silently
// skips", and that "a probe that only shows 'no second run started' is satisfiable by a scheduler
// that dropped the start on the floor". So this rule does not cancel, delete or consume the queue
// row: it declines to FIRE it. The row stays in the queue with its due `run_at`, is re-evaluated
// every tick, and therefore STARTS BY ITSELF once the open run closes (`fireQueueRow` is the only
// thing that removes or re-arms a row, and it is never reached on this branch). The queued row is
// observable in the queue table, not inferred from an absence.
//
// THE OPEN-RUN ANSWER IS NOT COMPUTED HERE. It comes from `seat-folder.js openRunsOfGoal()` — the
// one daemon-side reader of `<goal>/runs.csv`'s `state`/`run-id` columns, which `resolveSeatHome`
// also calls. PRIN-11 forbids a second place that answers "is this run live?", and two readers of
// one file that can disagree is `issues.md` G-301's shape. Nothing here reads the folder's
// existence: a run folder exists for every run that ever ran, so its presence answers nothing.
//
// ⚠ WHAT COUNTS AS A "SCHEDULED START" — the discriminator, stated because it is the one judgment
// in this file. A queue row is a run start when its CATALOGUE row is `action_type =
// 'start-workflow'` and is homed at a goal (`goal_name`): m4's workflow-as-a-schedulable-job is
// the run start (task 7.79: "the scheduled job IS a workflow job"), and the goal it is homed at is
// the goal whose register is read. Everything else is deliberately NOT gated, and each exclusion
// matters: `launch-agent` rows are the edge-runner's seat launches INSIDE an open run, and
// `fire-tool` rows are the watchers and self-heal jobs that must keep firing precisely BECAUSE a
// run is open. Gating those would stop the room the moment it started working. The predicate is
// this file's `isRunStart()` and it is one line; a run start that later arrives under a different
// action type changes that line and nothing else.
//
// ⚠ THIS GATE CANNOT FIRE ON THIS BOX TODAY, AND THAT IS MEASURED, NOT ASSUMED. On the live store
// (2026-07-30) `pragma table_info(jobs)` carries NO `goal_name`/`seat_name` columns — the task-7.12
// migration has not run here — and no `start-workflow` job is registered (11 jobs: `launch-agent`,
// `fire-tool`, `send-message` only), with an EMPTY queue. So `action: "queued"` is a value that
// cannot currently occur on this box, and it is said here rather than left to read later as "the
// case did not arise" when the truth is "the case cannot arise yet". `describeGate()` prints this
// precondition so a caller does not have to find it in a comment.
//
// C4 (`decisions.md#r-cutover-gated`): the gate is armed by a job's own homing, so it acts only on
// the goal a run-start job names. It alters this run's own scheduling in no way — this run's seats
// are tmux/team-kit launched and no `start-workflow` job exists on this box.
//
// THRESHOLDS: this rule has NONE. It reads no floor, no cap, no interval, and therefore reads
// nothing from `budget.json` and carries no policy number in argv or the environment — there is no
// number in it to carry (`r-floor-single-source` satisfied by absence, which is stated rather than
// claimed as a read that did not happen).

const { openRunsOfGoal } = require('../seat-identity/seat-folder');

// The catalogue-side action type that STARTS A RUN. Spelled once.
const RUN_START_ACTION_TYPE = 'start-workflow';

// The `action` value the decision emits. 7.77's vocabulary, and `M4-15`'s notification path fires
// on the event carrying it, so it is load-bearing and not a log word.
const QUEUED = 'queued';

// Why a start was queued. Every value here means "did NOT start"; they differ in what was found.
const REASONS = {
  OPEN_RUN: 'open-run',                            // exactly one open run — the ordinary case
  AMBIGUOUS: 'open-run-ambiguous',                 // >1 open row: a state this code may not arbitrate
  UNRECOGNIZED_STATE: 'open-run-state-unrecognized', // a `state` value that is neither open nor closed
  REGISTER_UNREADABLE: 'register-unreadable',      // absent / no run-id / no state column / unparseable
  WORKSPACE_UNRESOLVABLE: 'workspace-root-unresolvable', // no workspace root ⇒ no register to read
  GATE_ERROR: 'gate-error',                        // the rule itself threw — contained, see below
};

function isRunStart(job) {
  return !!(job && job.action_type === RUN_START_ACTION_TYPE && job.goal_name);
}

function describeGate() {
  return [
    `run-start discriminator: jobs.action_type === "${RUN_START_ACTION_TYPE}" AND jobs.goal_name is set`,
    'open-run answer: seat-folder.js openRunsOfGoal() over <goal>/runs.csv {run-id, state}; state === "open" exactly',
    `emitted on a gated start: {scheduled-start, open-run-found, action: "${QUEUED}"} + reason`,
    'unreadable/absent/unparseable register, >1 open row, or an unrecognized state value: QUEUED (fail-closed), never started',
    'an error inside the gate itself: QUEUED and never rethrown — a throw here would abandon the whole tick',
    'thresholds: none — this rule reads no policy number',
  ].join('\n');
}

// The `scheduled-start` half of the event: which start was gated. Every field comes off the queue
// row and the catalogue row — nothing is invented, and nothing is read from a caller's assertion.
function scheduledStartOf(job, queueRow) {
  return {
    'queue-id': queueRow.queue_id,
    'job-id': queueRow.job_id,
    'action-type': job.action_type,
    goal: job.goal_name,
    'trigger-kind': queueRow.trigger_kind,
    'run-at': queueRow.run_at,
  };
}

function queuedResult(job, queueRow, reason, openRunFound) {
  return {
    action: QUEUED,
    reason,
    event: {
      'scheduled-start': scheduledStartOf(job, queueRow),
      'open-run-found': openRunFound,
      action: QUEUED,
      reason,
    },
  };
}

// THE RULE. Returns `{ action: 'start' }` — the caller proceeds exactly as before — or
// `{ action: 'queued', reason, event }`, on which the caller MUST NOT fire the row.
//
// `resolveRoot` is a thunk and is called ONLY for a run-start row: resolving a workspace root on
// every due row of every tick would be work done to answer a question that was already `no`.
function decide({ job, queueRow, resolveRoot, readRegister = openRunsOfGoal }) {
  if (!isRunStart(job)) return { action: 'start' };

  const workspaceRoot = typeof resolveRoot === 'function' ? resolveRoot() : resolveRoot;
  const queued = (reason, openRunFound) => queuedResult(job, queueRow, reason, openRunFound);

  if (!workspaceRoot) {
    // Fail CLOSED. "I could not find the register" is not "there is no open run": the second is a
    // fact, the first is ignorance, and starting a run on ignorance is the overlap this prevents.
    return queued(REASONS.WORKSPACE_UNRESOLVABLE, {
      'run-id': null,
      state: null,
      count: null,
      register: null,
      reason: 'no workspace root resolvable from the heart store path — the run register cannot be located',
    });
  }

  const register = readRegister({ workspaceRoot, goal: job.goal_name });
  if (!register.ok) {
    return queued(REASONS.REGISTER_UNREADABLE, {
      'run-id': null,
      state: null,
      count: null,
      register: register.register || null,
      reason: register.reason,
    });
  }

  // An unrecognized `state` is not "closed". The comparison against `open` is exact by design (the
  // register's writer emits exactly `open`/`closed`), so a third value — a typo, a hand edit, a
  // future vocabulary — means the record does not say this run is closed, and the gate may not
  // supply the optimistic default for a fact the record declines to state.
  if (register.unrecognized.length > 0) {
    return queued(REASONS.UNRECOGNIZED_STATE, {
      'run-id': register.unrecognized.map((r) => r[register.runCol]),
      state: register.unrecognized.map((r) => r.state),
      count: register.unrecognized.length,
      register: register.register,
      reason: 'a run row carries a state that is neither "open" nor "closed" — not provably closed',
    });
  }

  if (register.open.length === 1) {
    const row = register.open[0];
    return queued(REASONS.OPEN_RUN, {
      'run-id': row[register.runCol],
      state: row.state,
      count: 1,
      register: register.register,
    });
  }

  if (register.open.length > 1) {
    // Two open rows is the very state R9 exists to make impossible, so it is REFUSED and never
    // ranked: picking one — the newest, the first, any rule at all — would start a run against a
    // register that does not say which run is live. It is also reported to the leader as an ask,
    // once, by the seat that observes it; this code's part is to not start.
    return queued(REASONS.AMBIGUOUS, {
      'run-id': register.open.map((r) => r[register.runCol]),
      state: 'open',
      count: register.open.length,
      register: register.register,
      reason: 'more than one run is open — R9 is already violated and this refuses to choose between them',
    });
  }

  // Zero open runs: nothing to overlap. The start proceeds normally — the control that keeps this
  // rule from being "a scheduler that queues everything", which would satisfy every absence-shaped
  // check while starting nothing at all.
  return { action: 'start' };
}

// ⚠ CONTAINMENT, and it is fail-CLOSED in BOTH directions at once.
//
// `dispatch()` runs this per due row with no try around it, so an exception raised here would
// abandon the WHOLE tick — advance already done, every later due row unserved, and the daemon's
// scheduling pass dead for as long as the condition lasts. Measured, not hypothetical: a mutant of
// this file that reached `open[0]` on an empty set threw `TypeError` out of `oneLiveRunDecision` →
// `dispatch` → `tick`, and the tick died at the first row.
//
// So an internal error QUEUES: it does not start the run (starting on a rule that just crashed is
// the overlap this whole file exists to prevent) and it does not propagate (a bug in R9's gate must
// not take the scheduler with it). It is never SILENT — the error message rides the event's
// `open-run-found.reason`, so the tick log carries it and M4-15's notification path fires on it
// like any other queue.
function oneLiveRunDecision(input) {
  try {
    return decide(input);
  } catch (err) {
    const { job = {}, queueRow = {} } = input || {};
    return queuedResult(job, queueRow, REASONS.GATE_ERROR, {
      'run-id': null,
      state: null,
      count: null,
      register: null,
      reason: `the one-live-run gate itself failed (${err && err.message}) — queued rather than started, `
        + 'and never rethrown: a throw here would abandon the whole tick',
    });
  }
}

module.exports = {
  oneLiveRunDecision,
  isRunStart,
  describeGate,
  RUN_START_ACTION_TYPE,
  QUEUED,
  REASONS,
};
