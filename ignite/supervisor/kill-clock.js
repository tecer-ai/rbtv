'use strict';

// -- THE NO-PROGRESS KILL CLOCK, and the CLOSED list of what pauses it [T1-R19, CF-1, D15] ------
//
// Kill triggers are exactly two [D5 as amended]: process exit without checkout (the death-stamp
// path, not here) and ~30 minutes of no progress (here). There is no per-seat wall-clock deadline.
//
// THIS CLOCK READS ONE FACT. `last_progress_at` off the supervisor registry row - not transcript
// growth, not the coordination-ledger fingerprint, not a pane. `progress.js` is the only writer.
//
// THREE PAUSE CONDITIONS AND NO FOURTH. The list is closed by ruling [T1-R19, D-1-ruling]:
//
//   1. a VERIFIED open ask        - the seat is waiting on the owner; killing it would throw away
//                                   work for a delay the seat does not control [D15, CF-12].
//   2. provider-backoff           - the lane is waiting out a provider window [C-5]. The STATE is
//                                   produced by the provider-lanes work; this predicate simply
//                                   never fires until that fact starts being written.
//   3. a disarmed `incomplete:` lane, until its NAMED re-arm event [D-1-ruling]. The flag is
//                                   spec-state-store's to write; this file only reads it.
//
// Anything else - a long tool call, a big model, a seat that "looks busy", a goal that is paused -
// does NOT pause this clock. The accepted consequence [CF-1, T4 Reversals] is a busy-looking
// runaway that keeps emitting listed progress signals and is therefore unkillable. Ruled, accepted,
// on the record; adding a fourth pause here would widen that hole, not close it.

const { RecoveryConfigError } = require('./recovery-config');
const progress = require('./progress');

const MINUTE_MS = 60 * 1000;

// The three reasons, spelled once. A caller reporting why a clock is paused uses THESE words, so
// two surfaces cannot invent two vocabularies for one condition.
const PAUSE_OPEN_ASK = 'verified-open-ask';
const PAUSE_PROVIDER_BACKOFF = 'provider-backoff';
const PAUSE_DISARMED_INCOMPLETE = 'disarmed-incomplete';
const PAUSE_REASONS = Object.freeze([PAUSE_OPEN_ASK, PAUSE_PROVIDER_BACKOFF, PAUSE_DISARMED_INCOMPLETE]);

// The lane facts this predicate reads, and the seats that produce them:
//
//   verified_open_ask            boolean - an ask thread verified open on this seat (owner-io).
//   provider_backoff_until       ISO-8601 - the end of the current backoff window, written by the
//                                provider-lanes work. Absent or already past = not backing off.
//   disarmed                     boolean - the lane carries the disarmed flag (state-store).
//   awaiting_event               string  - the NAMED event that will re-arm it. A disarmed lane
//                                with no named event is still paused: the pause is the flag's, and
//                                a missing event name is a bug in the writer, not a licence to
//                                kill a lane that is deliberately stopped.
function pauseState(lane = {}, now = new Date()) {
  const at = now instanceof Date ? now : new Date(now);
  if (lane.verified_open_ask) {
    return { paused: true, reason: PAUSE_OPEN_ASK, until: null };
  }
  if (lane.provider_backoff_until) {
    const until = new Date(lane.provider_backoff_until);
    if (!Number.isNaN(until.getTime()) && until.getTime() > at.getTime()) {
      return { paused: true, reason: PAUSE_PROVIDER_BACKOFF, until: until.toISOString() };
    }
  }
  if (lane.disarmed) {
    return { paused: true, reason: PAUSE_DISARMED_INCOMPLETE, until: lane.awaiting_event || null };
  }
  return { paused: false, reason: null, until: null };
}

// The config is REQUIRED and is never defaulted. A caller that reached here without a loaded
// config has a configuration-error on its hands (spec 2.1) and the correct behaviour is to arm no
// clock at all - so this throws rather than picking a number.
function assertConfig(config) {
  if (!config || typeof config.no_progress_kill_min !== 'number') {
    throw new RecoveryConfigError('no-progress clock cannot be armed without a loaded recovery config');
  }
  return config;
}

// -- THE DECISION -------------------------------------------------------------------------------
//
// `lastProgressAt` absent means the sitting has no supervisor-owned progress fact - unsupervised,
// or a row this build never wrote. That is NOT idleness: it is ignorance, and this clock never
// kills on ignorance (the same posture the liveness probe takes with its third value).
function killDecision({ lastProgressAt, lane = {}, config, now = new Date() } = {}) {
  assertConfig(config);
  const at = now instanceof Date ? now : new Date(now);
  const pause = pauseState(lane, at);
  if (pause.paused) {
    return { kill: false, reason: `paused:${pause.reason}`, paused: true, pauseReason: pause.reason, idleMin: null };
  }
  if (!lastProgressAt) {
    return { kill: false, reason: 'no-progress-fact', paused: false, pauseReason: null, idleMin: null };
  }
  const since = new Date(lastProgressAt);
  if (Number.isNaN(since.getTime())) {
    return { kill: false, reason: 'unreadable-progress-fact', paused: false, pauseReason: null, idleMin: null };
  }
  const idleMin = (at.getTime() - since.getTime()) / MINUTE_MS;
  if (idleMin >= config.no_progress_kill_min) {
    return { kill: true, reason: 'no-progress', paused: false, pauseReason: null, idleMin };
  }
  return { kill: false, reason: 'within-window', paused: false, pauseReason: null, idleMin };
}

// The same decision for a live sitting, reading the fact off the registry itself.
function killDecisionFor({ goal, seat, lane, config, now, registryFile } = {}) {
  return killDecision({
    lastProgressAt: progress.progressOf({ goal, seat }, { registryFile }),
    lane,
    config,
    now,
  });
}

module.exports = {
  MINUTE_MS,
  PAUSE_OPEN_ASK,
  PAUSE_PROVIDER_BACKOFF,
  PAUSE_DISARMED_INCOMPLETE,
  PAUSE_REASONS,
  pauseState,
  killDecision,
  killDecisionFor,
};
