'use strict';

// ── THE OWNER ALARM — A FROZEN GOAL SAYS SO, IN ITS OWN CHANNEL (owner ruling Q3a, 2026-08-18) ──
//
// THE MEASURED DEFECT. On 2026-08-18 two daemon-lane goals sat frozen for over four hours —
// `meet-transcript-summarizer` since 01:22:34Z, `stools-canvas-audio-elevenlabs` since 02:25:58Z —
// refusing to seed once every ~10 s, 3,028 times, across a daemon restart, and NOTHING told the
// owner. He found out by asking. Every surface that could have spoken was mute for its own reason:
// `goal-watcher-job.py`'s `run_stall` watchdog had been DEQUEUED by the owner the day before;
// `warnings-check.js` and the silence ladder key on `heart.db` execution status, and a goal that
// never gets seeded produces no unhealthy execution row to notice (both frozen goals' last rows
// read `exit_code 0, done` — clean); `queued-start-notify.js` fires at START, not at stall; and
// `recordOwnerNote` has no bridge egress at all. The refusals were printed to the journal and
// nowhere else.
//
// THE RULING, settled and not re-opened here: an owner alarm is a Slack message posted in the
// GOAL'S OWN CHANNEL. Not a log line, not a note in a file, not an email. It fires when the goal
// holds either (a) an unresolved SKEW or adjudication, or (b) ready work with zero live seats,
// persisting past a threshold — and it re-alerts on a STATE CHANGE, never on every tick.
//
// ⚑ THE DAEMON STILL HOLDS NO CHAT CREDENTIAL, and this file grows it none. It is the same seam
// `goal-channel-start.js` opened and for the same reason (`goal-channel-design.md:25-31`): the
// bridge is a separate OS process with no inbound listener that holds the only token, so what
// crosses the boundary is a PROCESS. This module composes an argv invoking the bridge's own
// operator CLI — `goal-channel-cli.js post <goal-id> <text…>`, a verb that already exists and that
// this change does not touch — and `ticker.js#ensureGoalChannel` performs it, handing the child
// its credential through systemd's `EnvironmentFile=`. `IGNITE_SRC` and the CLI path are IMPORTED
// from `goal-channel-start.js` rather than re-derived: two answers to "where is the bridge CLI"
// is one answer too many.
//
// ⚠ THE CONDITION IS READ OFF `seedGoal`'s OWN RETURN AND NOTHING ELSE. `states` (the per-seat
// `done|live|queued|ready|waiting` map) and `skewed` (the SKEW rows `seedGoal` already computes to
// warn about) are computed ONCE, by the seeding pass, from the same coord answer the pass acted
// on. A second reader of the same fact — a fresh `ready-seats` call, a second SKEW predicate — is
// free to disagree with the pass that decided what to dispatch, and this codebase has closed that
// defect class twice already. This module derives; it does not measure.
//
// ⚠ WRITTEN AGAINST THE POST-`skew-per-seat` CONTRACT (rbtv `de271c65`, "a disposition SKEW blocks
// its own seat, never the whole goal"). Before that commit a SKEW surfaced as a whole-goal
// `readinessRefused`; it now surfaces as a per-seat `verdict === 'SKEW'` row and the goal seeds
// around it. Condition (a) therefore reads `pickup.skewed` FIRST and keeps `readinessRefused` as
// its second arm — which is not vestigial: `ready-seats` still exits non-zero for the reasons it
// always did (no python, an unreadable package, a timeout, undocumented output), and that refusal
// still seeds nothing at all for the goal.

const path = require('node:path');
const { IGNITE_SRC, ENSURE_CLI } = require('./goal-channel-start');

const POST = 'post';
const SKIP = 'skip';

const REASONS = {
  NO_PICKUP: 'no-pickup',                  // called with nothing to rule on
  HEALTHY: 'healthy',                      // neither condition holds — the ordinary case
  BELOW_THRESHOLD: 'below-threshold',      // the condition holds, but not yet for long enough
  ALREADY_ALERTED: 'already-alerted',      // this exact condition already reached the owner
  DECISION_ERROR: 'decision-error',
};

// HOW LONG A FREEZE MUST PERSIST. The pass runs every ~10 s per goal, so a threshold of "a few
// passes" would alarm on windows that are not freezes at all: the pass between a grant mint and
// its spend, a seat between its queue row and its first execution row. Five minutes is the
// smallest span in which neither of those is still true, and it is four hours short of the
// measured incident — the alarm's job is to beat the owner asking, not to beat the tick.
//
// ⚠ MEASURED IN TIME, NOT IN PASSES. A pass count would silently mean something different the day
// the cadence changes, and the cadence is config (`ticker.js`), not a constant here.
const STALL_MS = 5 * 60 * 1000;

// ── THE DEDUP, WHICH IS WHAT MAKES THIS AN ALARM AND NOT A SPAM CANNON ────────────────────────
//
// The condition is re-evaluated every ~10 s per goal, forever. Un-deduplicated, this alarm
// reproduces the measured 3,028-refusal loop as 3,028 Slack messages — a strictly worse defect
// than the silence it replaces, because the owner would mute the channel.
//
// THE KEY IS THE GOAL; THE VALUE IS THE CONDITION'S SIGNATURE. The signature is the condition kind
// plus the SORTED names of the seats it names, so:
//   · a goal still stuck for the SAME reason gets ONE message, however many passes it sits there;
//   · a goal that becomes stuck for a DIFFERENT reason (a second seat skews, a skew becomes a
//     dead-ready stall) is a new signature — the clock restarts and a new message is owed;
//   · a goal that unfreezes drops its entry entirely, so a re-freeze alarms again from zero.
// Sorted because seat ORDER is not a state change, and an unsorted key would re-alarm on a
// reshuffle of the same set.
//
// ponytail: process-lifetime Map — ONE small entry per currently-stuck goal, cleared the moment
// the goal is healthy. CEILING: it does not survive a daemon restart, and the measured freeze DID
// (the daemon restarted mid-freeze and the goals stayed frozen), so a restart re-alarms each still
// -stuck goal once, after the threshold. That is the conservative direction — one duplicate
// message per restart beats a freeze that goes unreported because the alarm remembers a send from
// a process that no longer exists. UPGRADE PATH when restarts get frequent enough for that to
// annoy: persist `{ since, alerted }` as one small JSON file at the goal folder root (the same
// place `execution-lane` lives, written by the same pass), and seed this Map from it on first
// sight of the goal — no schema, no store, no new dependency.
const alarmState = new Map();

function skip(reason, extra = {}) {
  return { action: SKIP, reason, goal: null, goalDir: null, signature: null, text: null, argv: null, ...extra };
}

// THE INVOCATION. `post <goal-id> <text…>` is `goal-channel-cli.js`'s own verb; this composes it
// and adds nothing. The message is ONE argv element, never split on its spaces: the CLI joins
// `positional.slice(2)` with a single space, so a pre-split message would have its newlines and
// runs of whitespace flattened. `--prefix` is not passed, for `goal-channel-start.js`'s reason.
function composePostArgv({ goal, text, igniteSrc = IGNITE_SRC, nodeBin = process.execPath }) {
  return [nodeBin, path.join(igniteSrc, ENSURE_CLI), 'post', String(goal), String(text)];
}

// ── THE TWO CONDITIONS ───────────────────────────────────────────────────────────────────────
//
// (a) UNRESOLVED SKEW OR ADJUDICATION. A SKEW is the two records of a seat's own ending
// disagreeing; nothing advances that seat or its dependents until a HUMAN rules on the row, so it
// is by construction a condition no amount of waiting clears. `readinessRefused` is the second
// arm: coord could not compute readiness at all, and `seedGoal` wrote nothing for the whole goal.
//
// (b) READY WORK WITH ZERO LIVE SEATS. `states` says at least one seat is READY — coord resolved
// its predecessors and it is dispatchable — and NOTHING in the goal is `live` or `queued`. That is
// the shape of the 18-hour `heldByStore` freeze (task 7.776) and of any future hold that skips a
// dispatchable seat without saying so: work that is owed and a goal in which nothing is moving.
// `queued` counts as moving deliberately — a seat with a queue row is the tick's to dispatch, and
// treating it as still would alarm on the ordinary gap between this pass and the tick that follows
// it, ~0 s later.
function conditionOf(pickup) {
  // A FREEZE NAMED BEFORE OR AT SEEDING (LE-13, 2026-08-19). The lane watch's pre-seeding
  // branches and `seedGoal`'s empty-frontier classification hand it here ALREADY SHAPED
  // (`{ kind, seats, detail }`), because the producer is the one holding the evidence — this
  // module stays a deriver and re-measures nothing. First arm on purpose: a goal frozen before
  // seeding has no rows for the arms below to read, and the measured 4-hour silence lived
  // exactly in that gap.
  const frozen = pickup.frozen;
  if (frozen && frozen.kind) {
    return {
      kind: String(frozen.kind),
      seats: (frozen.seats || []).map(String).sort(),
      detail: String(frozen.detail || ''),
    };
  }
  const skewed = pickup.skewed || [];
  if (skewed.length) {
    const seats = skewed.map((r) => r.seat).sort();
    return {
      kind: 'skew',
      seats,
      detail: skewed.map((r) => `${r.seat}: ${r.reason}`).join('  ·  '),
    };
  }
  if (pickup.readinessRefused) {
    return { kind: 'readiness-refused', seats: [], detail: String(pickup.readinessRefused) };
  }
  const states = pickup.states || {};
  const entries = Object.entries(states);
  const ready = entries.filter(([, s]) => s === 'ready').map(([seat]) => seat).sort();
  const moving = entries.some(([, s]) => s === 'live' || s === 'queued');
  if (ready.length && !moving) {
    // WHY it is not moving, when the seeding pass knows: `heldByStore` is the one hold an operator
    // cannot see anywhere else ("coord said READY and MY OWN store has already fired it").
    const held = Object.keys(pickup.heldByStore || {});
    return {
      kind: 'ready-no-live',
      seats: ready,
      detail: held.length ? `held by the execution record: ${held.join(', ')}` : 'nothing was dispatched',
    };
  }
  // LE-13 CHANGE 2 (2026-08-19) — K CONSECUTIVE PERIODIC-JOB FAILURES. Placed LAST: a goal frozen
  // at seeding, or holding an unresolved SKEW, or with ready work nobody dispatched, is a MORE
  // actionable fact than "one of its periodic jobs keeps failing" and keeps the signature when
  // both hold. Measured by `engine/lane-watch.js#alarmOnStall` (the caller that holds the store
  // handle) and handed in on `pickup.periodicFailureJobs` — this module still derives, never
  // measures. The `seats` field carries JOB IDS here, not seats — `condition.detail` says so
  // plainly because `composeText` renders `condition.seats` as a bullet list.
  const failure = pickup.periodicFailureJobs || {};
  const failingJobs = failure.jobs || [];
  if (failingJobs.length) {
    const jobs = [...failingJobs].sort();
    return {
      kind: 'periodic-job-failing',
      seats: jobs,
      detail: `periodic job id(s) — NOT seats — with ${failure.k}+ consecutive \`jobs_log\` failures: ${jobs.join(', ')}`,
    };
  }
  // enqueue-unfired LAST, after ready-no-live (and after periodic-job-failing). First-match-wins:
  // a new arm placed earlier silently changes existing verdicts; placed last, every currently-
  // firing condition keeps its exact behaviour.
  const unfired = pickup.enqueueUnfired || [];
  if (unfired.length) {
    const seats = unfired.map((r) => String(r.seat)).sort();
    return {
      kind: 'enqueue-unfired',
      seats,
      detail: unfired.map((r) => `${r.seat}: ${r.because || 'unfired'} at ${r.at || '?'}`).join('  ·  '),
    };
  }
  return null;
}

// PHONE-FIRST mrkdwn (`rbtv2-slack-message-format`): one screen, the state first, the names next,
// and what it is waiting on last. No raw markdown — `*bold*`, not `**bold**`. It carries no ask
// mark: this is a disclosure the owner acts on, and the acting happens outside Slack.
function composeText({ goal, condition, stuckMs }) {
  const mins = Math.round(stuckMs / 60000);
  const why = {
    skew: `*Seat disposition SKEW* — the two records of that seat's own ending disagree, so it and its dependents advance on neither until a human rules.`,
    'readiness-refused': `*Readiness could not be computed* — \`coordinate ready-seats\` refused, so NOTHING in this goal was seeded this pass.`,
    'ready-no-live': `*Ready, undispatched* — these seats are dispatchable and no seat in the goal is live or queued.`,
    'periodic-job-failing': `*Periodic job repeatedly failing* — a recovery/maintenance job for this goal has failed its last several consecutive runs and is not recovering on its own.`,
    'enqueue-unfired': `*Enqueued, never fired* — an enqueue was recorded and no execution ever fired for it. Look at \`enqueue_log\` (outcome / because) and whether a live turn is still holding the seat.`,
  }[condition.kind]
    // Every OTHER kind is a pre/at-seeding freeze (LE-13: taskforce-unreadable, unbuilt-seats,
    // cast-unreadable, uncast-seats, seed-failed, seeding-empty — and whatever the producers name
    // next). One sentence covers them because the specifics already ride `condition.detail`,
    // composed by the producer with the evidence in hand — a per-kind map here would be a second
    // home for facts this module never measured.
    || `*Frozen before seeding* (\`${condition.kind}\`) — the daemon re-reads this goal every cadence and hits the same refusal; nothing will be seeded until the cause is repaired.`;
  const head = condition.kind === 'ready-no-live'
    ? `:warning: *${goal} is frozen* — work is ready and nothing is running (${mins}m).`
    : (condition.kind === 'skew' || condition.kind === 'readiness-refused')
      ? `:warning: *${goal} is frozen* — it is waiting on a ruling, not on work (${mins}m).`
      : condition.kind === 'periodic-job-failing'
        ? `:warning: *${goal}* has a periodic job stuck failing (${mins}m).`
        : condition.kind === 'enqueue-unfired'
          ? `:warning: *${goal}* recorded an enqueue that never launched (${mins}m).`
          : `:warning: *${goal} is frozen* — it cannot even be seeded (${mins}m).`;
  const who = condition.seats.length ? `\n${condition.seats.map((s) => `• \`${s}\``).join('\n')}` : '';
  return `${head}\n${why}${who}\n_${condition.detail}_\nThis will not clear on its own.`;
}

// ⚠ RE-EVALUATED EVERY PASS, AND THE STATE IS MUTATED HERE — this is not a pure function and
// cannot be, because "have I already said this?" is the whole decision. Everything it needs is on
// `pickup`; `now` is injected so a harness can drive the threshold without sleeping.
function decide({ goal, goalDir = null, pickup, now = Date.now(), state = alarmState }) {
  if (!goal || !pickup) return skip(REASONS.NO_PICKUP, { goal: goal || null });

  const condition = conditionOf(pickup);
  if (!condition) {
    // HEALTHY CLEARS THE ENTRY, and that is what makes an unfreeze/re-freeze a NEW alarm rather
    // than a silence. A goal that recovers must not carry its old `alerted` mark forward.
    state.delete(goal);
    return skip(REASONS.HEALTHY, { goal, goalDir });
  }

  const signature = `${condition.kind}:${condition.seats.join(',')}`;
  let entry = state.get(goal);
  if (!entry || entry.signature !== signature) {
    // A DIFFERENT reason is a different freeze: the clock restarts and the alarm re-arms. It must
    // still persist past the threshold — a condition that flickers through three shapes in thirty
    // seconds is a pass in motion, not three freezes.
    entry = { since: now, signature, alerted: null };
    state.set(goal, entry);
  }

  const stuckMs = now - entry.since;
  if (stuckMs < STALL_MS) return skip(REASONS.BELOW_THRESHOLD, { goal, goalDir, signature, stuckMs });
  if (entry.alerted === signature) return skip(REASONS.ALREADY_ALERTED, { goal, goalDir, signature, stuckMs });

  entry.alerted = signature;
  const text = composeText({ goal, condition, stuckMs });
  return {
    action: POST,
    // The action label the performer stamps on its tick-log rows. `channel-ensure` would be a lie
    // in the journal about an act that posts rather than creates.
    act: 'goal-alarm',
    reason: null,
    goal,
    goalDir,
    signature,
    stuckMs,
    text,
    argv: composePostArgv({ goal, text }),
  };
}

// ⚠ CONTAINMENT, for `goal-channel-start.js`'s measured reason: this runs inside `runLaneWatch`'s
// per-goal loop, which serves every OTHER goal from the same pass. A throw here would abandon them.
// An internal error SKIPS — an alarm is never worth taking the seeding pass down for.
function stallAlarmDecision(input) {
  try {
    return decide(input || {});
  } catch (err) {
    return skip(`${REASONS.DECISION_ERROR}: ${err && err.message}`, { goal: (input && input.goal) || null });
  }
}

module.exports = {
  stallAlarmDecision,
  composePostArgv,
  conditionOf,
  composeText,
  alarmState,
  STALL_MS,
  POST,
  SKIP,
  REASONS,
};
