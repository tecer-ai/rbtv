'use strict';

// -- WHAT A CLASSIFIED PROVIDER FAULT DOES TO A LANE [spec-recovery §3, T1-R13, T1-R17, C-10] ---
//
// `provider-classify.js` decides the WORD. This file is the BEHAVIOUR, and the two are split
// because a recognition-list edit (data, owner-facing) must never have to reach into policy, and
// policy must never grow a second opinion about what an error text means.
//
// THE TWO BEHAVIOURS, and they are opposites:
//
//   TRANSIENT (quota, rate-limit, provider-down)
//     * NO strike. Nothing the seat did caused it, so nothing it did may be counted against it.
//     * ONE pass through the eligible alternates of the shared routing table — per LAUNCH ATTEMPT,
//       never twice. `tried` is what makes "one pass" mechanical rather than a promise.
//     * EVERY reroute RECORDED on the seat. A silent reroute is how a plan's model pin quietly
//       stops being the model that ran (the ST-19 shape, from the other direction).
//     * All alternates transient-fail -> BACKOFF. `provider_backoff_until` is written as ISO-8601
//       under exactly that name, because `kill-clock.js#pauseState` reads that field to pause the
//       no-progress clock, and `observation/frozen.js` reads `provider_backoff_waiting` to keep
//       the frozen alarm quiet through an outage [C-5]. The monitor must not report healthy
//       through a provider outage [T1-R13] — which is why the facts are readable, not internal.
//
//   CONFIGURATION (model-not-found, bad slug, auth-rejected, and anything UNRECOGNISED)
//     * Ordinary `failed` + strike, through the counters-budget strike path. Never a silent
//       no-strike dead end (ST-19 class). This file does not strike anything itself: it says
//       `strike: true` and the caller spends it on the ONE attempt counter.
//
// THE OVERRIDE RULING [C-10, CP1 — RULED, FINAL, do not re-litigate]. A per-seat model override
// SUPPRESSES reroute. First configuration fault on an override is `failed` + strike, full stop.
// A transient fault on an override still does not strike (it is still not the seat's fault) and
// still does not reroute — it goes straight to backoff, because a pinned lane has no alternates by
// definition. Rationale on the record: ST-19 was a plan-declared bad slug, and rerouting would
// have hidden the pin instead of surfacing it.
//
// THE NUMBERS ARE NEVER LITERALS HERE. `provider_backoff_initial_min`, `_multiplier` and `_cap_h`
// come from `recovery-config.js` [spec-recovery §2.1]. A missing config is a configuration-error,
// not a licence to pick 15 minutes in code.

const fs = require('node:fs');
const path = require('node:path');

const { classifyProviderError, TRANSIENT, CONFIGURATION } = require('./provider-classify');
const { eligibleAlternates } = require('./routing-table');
const { RecoveryConfigError } = require('./recovery-config');

const LANES_FILENAME = 'provider-lanes.json';
const DEFAULT_LANES_PATH = path.join(__dirname, LANES_FILENAME);

// The key separator, spelled as an ESCAPE for `attempt-counters.js`'s reason: a literal NUL in
// source makes the file binary to git, to grep and to every reviewer's diff.
const SEP = '\u0000';

const MINUTE_MS = 60 * 1000;

function lanesPath(override) {
  return path.resolve(override || DEFAULT_LANES_PATH);
}

function keyOf({ goal, seat }) {
  if (!goal || !seat) throw new Error('a provider lane is keyed on (goal, seat)');
  return [String(goal), String(seat)].join(SEP);
}

function readAll(file) {
  try {
    const parsed = JSON.parse(fs.readFileSync(lanesPath(file), 'utf8'));
    return (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) ? parsed : {};
  } catch {
    return {};   // absent or unreadable is "no provider history", never a death
  }
}

// tmp-then-rename, for `attempt-counters.js`'s reason: an interrupted truncate-write is how a
// ledger becomes an empty file — here, one that would forget every live backoff at once.
function writeAll(file, rows) {
  const target = lanesPath(file);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const tmp = `${target}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(rows, null, 2)}\n`, 'utf8');
  fs.renameSync(tmp, target);
}

function blankLane(goal, seat) {
  return {
    goal,
    seat,
    tried: [],                    // alternates already spent in THIS launch attempt
    reroutes: [],                 // every reroute ever recorded on this seat
    provider_backoff_until: null, // ISO-8601 — the name `kill-clock.js#pauseState` reads
    backoff_streak: 0,
    reroute_pending: false,
    last_classification: null,
    last_error: null,
  };
}

// -- THE BACKOFF LADDER [spec-recovery §2] ------------------------------------------------------
//
// 15 min, double, cap 4 h — as CONFIG VALUES, never as literals. The streak is the number of
// completed all-alternates-failed passes, so the first backoff is the initial value and each
// further one doubles until the cap. The cap bounds the wait without the lane looking frozen
// (frozen excludes a backoff-waiting lane [C-5]).
function assertConfig(config) {
  const keys = ['provider_backoff_initial_min', 'provider_backoff_multiplier', 'provider_backoff_cap_h'];
  for (const k of keys) {
    if (!config || typeof config[k] !== 'number') {
      throw new RecoveryConfigError(
        `provider backoff cannot be computed without \`${k}\` from the recovery config [spec-recovery §2.1]`,
      );
    }
  }
  return config;
}

function backoffMinutes(streak, config) {
  assertConfig(config);
  const capMin = config.provider_backoff_cap_h * 60;
  const grown = config.provider_backoff_initial_min
    * (config.provider_backoff_multiplier ** Math.max(0, streak - 1));
  return Math.min(grown, capMin);
}

// -- THE READABLE FACTS [C-5] -------------------------------------------------------------------
//
// impl-alarms reads these and NOTHING here emits an alarm or posts anything: the frozen invariant
// is a READER of supervisor facts, never a second liveness predicate. Two names are load-bearing
// and are spelled to match their one consumer each:
//   `provider_backoff_until`     -> `kill-clock.js#pauseState` (the no-progress clock's pause)
//   `provider_backoff_waiting`   -> `observation/frozen.js#predicate` (the frozen exclusion)
//   `reroute_pending`            -> `observation/frozen.js#predicate` (the same exclusion, mid-pass)
function laneFacts({ goal, seat }, { lanesFile, now } = {}) {
  const row = readAll(lanesFile)[keyOf({ goal, seat })] || blankLane(goal, seat);
  const at = now instanceof Date ? now : new Date(now || Date.now());
  const until = row.provider_backoff_until ? new Date(row.provider_backoff_until) : null;
  const waiting = Boolean(until && !Number.isNaN(until.getTime()) && until.getTime() > at.getTime());
  return {
    goal: row.goal || goal,
    seat: row.seat || seat,
    provider_backoff_until: row.provider_backoff_until || null,
    provider_backoff_waiting: waiting,
    reroute_pending: Boolean(row.reroute_pending),
    backoff_streak: Number(row.backoff_streak || 0),
    reroutes: Array.isArray(row.reroutes) ? row.reroutes : [],
    tried: Array.isArray(row.tried) ? row.tried : [],
    last_classification: row.last_classification || null,
  };
}

// -- THE DECISION -------------------------------------------------------------------------------
//
// One call per observed launch failure. It classifies, records what it decided ON THE SEAT, and
// returns what the caller must do — it never strikes, never launches, never emits.
//
// Returned shape:
//   classification  'transient' | 'configuration'
//   strike          true only for CONFIGURATION. The caller spends it on the attempt counter.
//   failed          true only for CONFIGURATION — the ordinary `failed` ending.
//   reroute         {from, to} when this pass rerouted, else null
//   backoff_until   ISO-8601 when this pass ENTERED backoff, else null
//   pass_exhausted  true when the one pass through the alternates is over
function onLaunchFailure({
  goal, seat, errorText, harness = null, model = null, override = false,
  config, at = null, lanesFile, tableFile, lists,
} = {}) {
  const stamp = at ? new Date(at) : new Date();
  const iso = stamp.toISOString();
  const verdict = classifyProviderError(errorText, lists || {});
  const rows = readAll(lanesFile);
  const key = keyOf({ goal, seat });
  const lane = rows[key] || blankLane(goal, seat);
  lane.goal = goal;
  lane.seat = seat;
  lane.last_classification = verdict.classification;
  lane.last_error = String(errorText === null || errorText === undefined ? '' : errorText).slice(0, 500);

  // -- CONFIGURATION: strike, full stop. The one path that spends the counter.
  if (verdict.classification === CONFIGURATION) {
    lane.reroute_pending = false;
    lane.tried = [];
    rows[key] = lane;
    writeAll(lanesFile, rows);
    return {
      classification: CONFIGURATION,
      strike: true,
      failed: true,
      reroute: null,
      backoff_until: null,
      pass_exhausted: true,
      override: Boolean(override),
      evidence: verdict,
    };
  }

  // -- TRANSIENT: never a strike, whatever happens below.
  // An OVERRIDE has no alternates by ruling, so its one pass is empty and it backs off at once.
  const alternates = override
    ? []
    : eligibleAlternates({ harness, model, tried: lane.tried }, { tableFile });

  if (alternates.length) {
    const to = alternates[0];
    const from = harness && model ? `${harness}/${model}` : null;
    lane.tried = [...lane.tried, to.label];
    lane.reroute_pending = true;
    lane.reroutes = [...lane.reroutes, {
      at: iso, from, to: to.label, reason: verdict.matched || 'transient', classification: TRANSIENT,
    }];
    rows[key] = lane;
    writeAll(lanesFile, rows);
    return {
      classification: TRANSIENT,
      strike: false,
      failed: false,
      reroute: { from, to: to.label, harness: to.harness, model: to.model },
      backoff_until: null,
      pass_exhausted: false,
      alternates_left: alternates.length - 1,
      override: false,
      evidence: verdict,
    };
  }

  // -- THE PASS IS OVER: every eligible alternate transient-failed (or the lane is pinned).
  // Backoff, and the pass RESETS so the next attempt after the window is a fresh single pass —
  // never a second pass inside this one.
  const streak = Number(lane.backoff_streak || 0) + 1;
  const minutes = backoffMinutes(streak, config);
  const until = new Date(stamp.getTime() + minutes * MINUTE_MS).toISOString();
  lane.backoff_streak = streak;
  lane.provider_backoff_until = until;
  lane.reroute_pending = false;
  lane.tried = [];
  rows[key] = lane;
  writeAll(lanesFile, rows);
  return {
    classification: TRANSIENT,
    strike: false,
    failed: false,
    reroute: null,
    backoff_until: until,
    backoff_minutes: minutes,
    backoff_streak: streak,
    pass_exhausted: true,
    override: Boolean(override),
    evidence: verdict,
  };
}

// -- IS THIS LANE PINNED? [C-10, CP1 ruled] ----------------------------------------------------
//
// PURE on purpose: it takes the two values its caller has ALREADY read and does no file IO, so
// the ruling can be asserted without a goal folder, and so this module never grows a second
// reader of `seat.md`.
//
// THE PIN IS A DISAGREEMENT, and it is measured off surfaces that already exist rather than a new
// declaration nobody has agreed to. `taskforce.csv` carries the seat's BINDING (`rbtv-bindings
// set` writes it); `seat.md` carries the DESCRIPTOR the launch actually reads
// (`spawn.js#launchSpecForSeat`). Ordinarily they agree and the seat is running its binding — a
// reroutable lane. When the descriptor names a DIFFERENT model, somebody pinned that seat by hand
// against its binding, and that pin is exactly what the ruling protects: ST-19 was a plan-declared
// bad slug, and rerouting would have replaced the pin instead of surfacing it.
//
// An absent value on either side is NOT an override: an unbound seat and an unmaterialized seat
// are both "no pin was expressed", never "a pin was expressed and differs".
function seatModelOverride({ declaredModel, boundModel } = {}) {
  const declared = String(declaredModel || '').trim();
  const bound = String(boundModel || '').trim();
  if (!declared || !bound) return false;
  return declared.toLowerCase() !== bound.toLowerCase();
}

// A launch that actually got through ends the attempt: the pass and the backoff ladder both clear.
// Recorded reroutes are NOT cleared — they are the seat's history, and the whole point of
// recording them is that somebody can later ask what this lane really ran.
function onLaunchSucceeded({ goal, seat }, { lanesFile } = {}) {
  const rows = readAll(lanesFile);
  const key = keyOf({ goal, seat });
  if (!rows[key]) return { cleared: false };
  rows[key].tried = [];
  rows[key].reroute_pending = false;
  rows[key].provider_backoff_until = null;
  rows[key].backoff_streak = 0;
  writeAll(lanesFile, rows);
  return { cleared: true };
}

module.exports = {
  LANES_FILENAME,
  DEFAULT_LANES_PATH,
  MINUTE_MS,
  lanesPath,
  keyOf,
  backoffMinutes,
  laneFacts,
  seatModelOverride,
  onLaunchFailure,
  onLaunchSucceeded,
};
