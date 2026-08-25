'use strict';

// -- THE FROZEN-GOAL SCHEDULER INVARIANT [T1-R15, CF-2, C-5, F-simplicity-4] --------------------
//
// WHAT WAS BROKEN. "This goal is stuck" was answered by a TIMER - silence for N ticks - and silence
// is not stuckness. The tick-silence ladder paged healthy goals and stayed quiet through real
// freezes, and the alarm that replaced it (`goal-stall-alarm.js`, deleted) asked a seeding-local
// question that three separate miscounts could each answer wrong (memory
// `engine/20260820-i-frozen-goal-alarm-fix.md`).
//
// THE RULE. Frozen is an INVARIANT OF THE SCHEDULER, not a clock: a goal that is `running`, with
//   (a) no live seat, (b) no eligible launch, (c) no open ask, (d) not paused,
// held for the configured window, is a goal the scheduler has nothing to do for and nobody has been
// asked about. Any ONE of those four being false means the system is working and there is nothing
// to say. The window only stops a one-tick gap between a seat ending and the next launching from
// paging the owner.
//
// LIVENESS IS READ FROM THE SUPERVISOR REGISTRY AND NOWHERE ELSE [T4-R8]. This module deliberately
// does not look at a pane, a tick counter, a ledger status, or a transcript - re-deriving liveness
// here would be the fourth disjoint predicate C6 exists to delete. Everything else it needs is a
// FACT HANDED IN by the caller that already computes it (`supervisor/owed.js` answers `owed`;
// the ask store answers `open_ask`; the goal state row answers `paused`) - this file re-derives none
// of them, which is the other half of not becoming a second scheduler.
//
// THE TWO EXCLUSIONS ARE ABSOLUTE [C-5]. A lane waiting out a provider backoff, and a lane skipped
// pending a reroute, are WAITING ON PURPOSE. They look identical to frozen from outside and they are
// the opposite of it. They are excluded here, at the predicate, never "swept in and filtered later".
// Nothing in this file stamps `incomplete:` on anything and nothing kills: the hourly repeat is an
// alarm, and spec-recovery §"any other unbounded alarm re-fire" excludes exactly this repeat from
// the attempt counter for that reason.

const { loadRegistry, isRowAlive } = require('../supervisor/registry');

const SIGNATURE_CLASS = 'frozen-goal';

// [T1-R15] "repeated hourly while the condition holds" is the RULING, not a knob - it is absent from
// spec-recovery's config file on purpose. The window beside it IS a knob and is required from the
// caller below.
const HOURLY_REPEAT_MS = 60 * 60 * 1000;

const CONDITION = 'running, no live seat, no eligible launch, no open ask, not paused';
const WHAT_WOULD_CLEAR_IT = 'a seat starting, a launch becoming eligible, an ask being opened, or the goal being paused';

const OBSERVATION_FIELDS = Object.freeze([
  'goal_id',
  'goal_state',
  'paused',
  'eligible_launch',
  'open_ask',
  'provider_backoff_waiting',
  'reroute_pending',
  'channel_id',
  'evidence_pointer',
]);

function validateObservation(o) {
  if (!o || typeof o !== 'object') throw new Error('frozen observation requires an object');
  const missing = OBSERVATION_FIELDS.filter((f) => o[f] === undefined || o[f] === null || o[f] === '');
  if (missing.length > 0) {
    throw new Error(`frozen observation is missing: ${missing.join(', ')} — the observing code is the bug`);
  }
  return true;
}

function loadHolds(holdsPath) {
  if (!holdsPath) return {};
  try {
    const fs = require('node:fs');
    const parsed = JSON.parse(fs.readFileSync(holdsPath, 'utf8'));
    return parsed && typeof parsed.holds === 'object' && parsed.holds ? parsed.holds : {};
  } catch {
    return {};
  }
}

// PERSISTED, and that is the whole point of the file existing. The deleted module held its dedup in a
// process-lifetime Map, so a daemon restart forgot both what it had paged and how long a condition
// had been held - and a restart is exactly the event most likely to happen while a goal is frozen.
function saveHolds(holdsPath, holds) {
  if (!holdsPath) return;
  const fs = require('node:fs');
  const path = require('node:path');
  fs.mkdirSync(path.dirname(holdsPath), { recursive: true });
  const tmp = `${holdsPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, `${JSON.stringify({ version: 1, holds }, null, 2)}\n`);
  fs.renameSync(tmp, holdsPath);
}

// `frozenWindowMin` is REQUIRED and has no default, not even a silent one: spec-recovery §2.1 puts
// all five recovery knobs in one config file and forbids a hardcoded fallback, precisely so a
// number the owner tuned in that file cannot be quietly overridden by a constant in a module.
function createFrozenInvariant({
  emitter,
  frozenWindowMin,
  registryFile = null,
  holdsPath = null,
  now = null,
} = {}) {
  if (!emitter || typeof emitter.emit !== 'function' || typeof emitter.clear !== 'function') {
    throw new Error('createFrozenInvariant requires the alarm emitter (emit + clear)');
  }
  const windowMin = Number(frozenWindowMin);
  if (!Number.isInteger(windowMin) || windowMin <= 0) {
    throw new Error('createFrozenInvariant requires frozen_window_min from the recovery config (a positive integer)');
  }
  const windowMs = windowMin * 60 * 1000;
  const clock = now || (() => Date.now());
  let holds = loadHolds(holdsPath);

  function liveSeatCount(goalId) {
    return loadRegistry(registryFile).filter((row) => row.goal === goalId && isRowAlive(row)).length;
  }

  // The invariant itself, and it is one conjunction on purpose. It counts nothing IN by exception -
  // every arm must be positively true - so an unrecognised state can only make it quieter, never
  // louder. The inverse arithmetic ("everything except the classes I know are harmless") is what
  // re-lit the 10-second Slack loop in the deleted alarm.
  function predicate(o) {
    if (o.provider_backoff_waiting) return { frozen: false, reason: 'excluded: provider-backoff-waiting [C-5]' };
    if (o.reroute_pending) return { frozen: false, reason: 'excluded: reroute-pending (uncastSeats skip) [C-5]' };
    if (o.goal_state !== 'running') return { frozen: false, reason: `goal is ${o.goal_state}, not running` };
    if (o.paused === true) return { frozen: false, reason: 'goal is paused' };
    if (o.eligible_launch === true) return { frozen: false, reason: 'a launch is eligible' };
    if (o.open_ask === true) return { frozen: false, reason: 'an ask is open' };
    const live = liveSeatCount(o.goal_id);
    if (live > 0) return { frozen: false, reason: `${live} live seat(s) on the supervisor registry` };
    return { frozen: true, reason: CONDITION };
  }

  function signatureFor(goalId) {
    return `${SIGNATURE_CLASS}:goal:${goalId}`;
  }

  async function checkOne(observation) {
    validateObservation(observation);
    const o = observation;
    const at = clock();
    const verdict = predicate(o);

    if (!verdict.frozen) {
      if (holds[o.goal_id]) {
        delete holds[o.goal_id];
        saveHolds(holdsPath, holds);
      }
      const cleared = emitter.clear(signatureFor(o.goal_id));
      return {
        goal_id: o.goal_id, frozen: false, reason: verdict.reason, emitted: null, cleared: cleared.cleared,
      };
    }

    const since = holds[o.goal_id] || at;
    if (holds[o.goal_id] !== since) {
      holds[o.goal_id] = since;
      saveHolds(holdsPath, holds);
    }
    const heldMs = at - since;
    if (heldMs < windowMs) {
      return {
        goal_id: o.goal_id, frozen: true, held_ms: heldMs, emitted: null,
        reason: `held ${Math.round(heldMs / 1000)}s of the ${windowMin} min window`,
      };
    }

    // Goal-scoped, so it posts in the goal's own channel and is NOT the system-health class:
    // `immediate: false` is a stated answer, not an omission. One emission per signature; the
    // hourly repeat rides the emitter's own repeat window, so it is still ONE registry row.
    const result = await emitter.emit({
      condition: CONDITION,
      subject: { type: 'goal', id: o.goal_id },
      evidence_pointer: o.evidence_pointer,
      what_would_clear_it: WHAT_WOULD_CLEAR_IT,
      signature_class: SIGNATURE_CLASS,
      immediate: false,
      channel_id: o.channel_id,
      goal_id: o.goal_id,
      repeat_every_ms: HOURLY_REPEAT_MS,
    });
    return {
      goal_id: o.goal_id,
      frozen: true,
      held_ms: heldMs,
      emitted: result.posted ? result.reason : null,
      reason: result.posted ? result.reason : 'deduped — one emission per condition-signature',
    };
  }

  async function check(observations = []) {
    const out = [];
    for (const o of observations) out.push(await checkOne(o));
    return out;
  }

  return { check, checkOne, predicate, signatureFor };
}

module.exports = {
  SIGNATURE_CLASS,
  HOURLY_REPEAT_MS,
  CONDITION,
  WHAT_WOULD_CLEAR_IT,
  OBSERVATION_FIELDS,
  validateObservation,
  createFrozenInvariant,
};
