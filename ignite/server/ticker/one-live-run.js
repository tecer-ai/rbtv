'use strict';

// ── ONE-LIVE-EXECUTION ON THE DAEMON'S JOB-SCHEDULING PATH — RE-FOUNDED ON THE DERIVED LEASE ────
//
// Epic 7.607 stage E1 (`decisions.md#d-extinguishment-design-lock` items 1, 2, 4). A scheduled
// start that lands while the SAME GOAL is EXECUTING is QUEUED, never started.
//
// WHAT CHANGED, AND WHY IT IS A RE-FOUNDING RATHER THAN A SWAP OF READERS. Until this stage the
// answer came from `<goal>/runs.csv`'s `state` column — a STORED STATUS. That register produced
// the 7.608 deadlock: a goal whose run row read `open` while nothing at all was executing refused
// its own start FOREVER, because the only thing that could clear the row was the run that the row
// was refusing to start. A stored status has no way to be wrong quietly ONCE — it is wrong until
// somebody edits a file. So the register is not read here any more, by anything, ever:
//
//   the goal is executing  ⟺  its tmux ROOM EXISTS RIGHT NOW  (server/lease/lease.js)
//
// The deadlock's gate half dies with that sentence: a fresh goal has no room, so `deriveLease`
// reports no lease and the start is ADMITTED. That is the probe's red-first arm — it reproduces
// the deadlock's exact shape (a goal carrying a stale `state=open` register row) and asserts the
// start fires anyway, which is only possible because nothing here can see the register.
//
// A SKIP IS STILL NOT AN ACCEPTABLE OUTCOME (7.77, unchanged). This rule does not cancel, delete
// or consume the queue row: it declines to FIRE it. The row stays in the queue with its due
// `run_at`, is re-evaluated every tick, and therefore STARTS BY ITSELF once the goal's room is
// gone (`fireQueueRow` is the only thing that removes or re-arms a row, and it is never reached on
// this branch). The queued row is observable in the queue table, not inferred from an absence.
//
// THE LEASE IS NOT COMPUTED HERE (PRIN-11). `server/lease/lease.js` is the one home of "is this
// goal executing"; two places answering it is `issues.md` G-301's shape whichever evidence they
// read. This file owns exactly one judgment — the run-start DISCRIMINATOR below — and the posture
// it takes when the lease says "I do not know".
//
// ⚠ WHAT COUNTS AS A "SCHEDULED START", unchanged from 7.77 and still the one judgment in this
// file: a queue row is a start when its CATALOGUE row is `action_type = 'start-workflow'` and is
// homed at a goal (`goal_name`). Everything else is deliberately NOT gated, and each exclusion
// matters: `launch-agent` rows are the edge-runner's seat launches INSIDE a live execution, and
// `fire-tool` rows are the watchers and self-heal jobs that must keep firing precisely BECAUSE
// one is live. Gating those would stop the room the moment it started working. (Item 7 of the
// design lock renames this verb's vocabulary — "run start" becomes "start the goal's execution".
// The RENAME is a later stage's; this stage changes the BEHAVIOR under the existing names so the
// two changes stay separable in the history.)
//
// ⚠ EVENT-FIELD COMPAT SEAM, DISCLOSED RATHER THAN SILENTLY RENAMED. `queued-run-notify.js` (the
// owner notification, inventory #49) reads `event['open-run-found']`, and it is NOT in this
// stage's write surface. So the field KEEPS ITS NAME and carries lease values (`run-id` = the
// matched room name(s), `state` = the lease verdict word, `register` = the room predicate), and a
// second field `live-lease` carries the full evidence for anything reading the event fresh. E2's
// rename pass collapses the two. A rename here would have broken the notifier silently.
//
// THRESHOLDS: this rule has NONE. It reads no floor, no cap, no interval, and therefore reads
// nothing from `budget.json` and carries no policy number in argv or the environment.

const { deriveLease } = require('../lease/lease');

// The catalogue-side action type that STARTS A GOAL'S EXECUTION. Spelled once.
const RUN_START_ACTION_TYPE = 'start-workflow';

// The `action` value the decision emits. 7.77's vocabulary, and `M4-15`'s notification path fires
// on the event carrying it, so it is load-bearing and not a log word.
const QUEUED = 'queued';

// Why a start was queued. LEASE vocabulary — the register-shaped set (`open-run`,
// `open-run-ambiguous`, `open-run-state-unrecognized`, `register-unreadable`) is DELETED with the
// layer, not aliased. Two rooms matching the E1 transitional predicate need no `ambiguous` value:
// both are live evidence of the same goal executing, so there is nothing to arbitrate — the gate
// queues and names both.
const REASONS = {
  LIVE_LEASE: 'live-lease',                              // the goal is executing — the ordinary case
  LEASE_UNREADABLE: 'lease-unreadable',                  // tmux unreadable: ignorance, never "no lease"
  WORKSPACE_UNRESOLVABLE: 'workspace-root-unresolvable', // no workspace root ⇒ no goal tree to derive from
  GATE_ERROR: 'gate-error',                              // the rule itself threw — contained, see below
};

function isRunStart(job) {
  return !!(job && job.action_type === RUN_START_ACTION_TYPE && job.goal_name);
}

function describeGate() {
  return [
    `run-start discriminator: jobs.action_type === "${RUN_START_ACTION_TYPE}" AND jobs.goal_name is set`,
    'executing answer: server/lease/lease.js deriveLease() — the goal\'s tmux room existing NOW',
    'stored status read: NONE — runs.csv is not read by this gate at any point',
    `emitted on a gated start: {scheduled-start, live-lease, open-run-found (compat), action: "${QUEUED}"} + reason`,
    'lease unreadable (tmux missing/erroring): QUEUED (fail-closed), never started',
    'no live lease: START — a fresh goal with no room admits its start (the 7.608 deadlock is gone)',
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

function queuedResult(job, queueRow, reason, leaseFound) {
  return {
    action: QUEUED,
    reason,
    event: {
      'scheduled-start': scheduledStartOf(job, queueRow),
      'live-lease': leaseFound,
      // Compat seam — see the header note. Same object, legacy key, so the unmodified notifier
      // keeps rendering. E2 deletes this line in the same pass that renames the notifier.
      'open-run-found': leaseFound,
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
// `readLease` is the injection point a probe supplies a fixture tmux server through — a probe
// supplies real measurables, never a claimed verdict.
function decide({ job, queueRow, resolveRoot, readLease = deriveLease }) {
  if (!isRunStart(job)) return { action: 'start' };

  const workspaceRoot = typeof resolveRoot === 'function' ? resolveRoot() : resolveRoot;
  const queued = (reason, leaseFound) => queuedResult(job, queueRow, reason, leaseFound);

  if (!workspaceRoot) {
    // Fail CLOSED. "I could not find the goal tree" is not "this goal is not executing": the
    // second is a fact, the first is ignorance, and starting on ignorance is the overlap this
    // prevents.
    return queued(REASONS.WORKSPACE_UNRESOLVABLE, {
      'run-id': null,
      state: null,
      count: null,
      register: null,
      rooms: [],
      seats: [],
      reason: 'no workspace root resolvable from the heart store path — the lease cannot be derived',
    });
  }

  const lease = readLease({ workspaceRoot, goal: job.goal_name });
  if (!lease.ok) {
    // UNREADABLE ≠ EMPTY, and this gate's posture on ignorance is CLOSED. The watchers take the
    // opposite posture on the same signal (a broken meter may not stop a healthy loop) — which is
    // exactly why the lease module reports and never decides.
    return queued(REASONS.LEASE_UNREADABLE, {
      'run-id': null,
      state: null,
      count: null,
      register: null,
      rooms: [],
      seats: [],
      reason: lease.reason,
    });
  }

  if (lease.live) {
    const rooms = lease.rooms.map((r) => r.room);
    return queued(REASONS.LIVE_LEASE, {
      'run-id': rooms.length === 1 ? rooms[0] : rooms,
      state: 'live-lease',
      count: rooms.length,
      register: lease.evidence['room-predicate'],
      rooms,
      seats: lease.seats.map((s) => s.seat),
      reason: `goal ${job.goal_name} is executing: room(s) ${rooms.join(', ')} exist now`
        + ` with ${lease.seats.length} ancestry-verified seat process(es)`,
    });
  }

  // NO LIVE LEASE: nothing to overlap, the start proceeds. This is the branch that kills 7.608's
  // gate half AND the control that keeps this rule from being "a scheduler that queues
  // everything", which would satisfy every absence-shaped check while starting nothing at all.
  return { action: 'start' };
}

// ⚠ CONTAINMENT, and it is fail-CLOSED in BOTH directions at once.
//
// `dispatch()` runs this per due row with no try around it, so an exception raised here would
// abandon the WHOLE tick — advance already done, every later due row unserved, and the daemon's
// scheduling pass dead for as long as the condition lasts. Measured, not hypothetical: a mutant of
// the register-era body that reached `open[0]` on an empty set threw `TypeError` out of
// `oneLiveRunDecision` → `dispatch` → `tick`, and the tick died at the first row.
//
// So an internal error QUEUES: it does not start (starting on a rule that just crashed is the
// overlap this whole file exists to prevent) and it does not propagate. It is never SILENT — the
// error message rides the event, so the tick log carries it and M4-15's notification path fires on
// it like any other queue.
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
      rooms: [],
      seats: [],
      reason: `the one-live-execution gate itself failed (${err && err.message}) — queued rather than `
        + 'started, and never rethrown: a throw here would abandon the whole tick',
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
