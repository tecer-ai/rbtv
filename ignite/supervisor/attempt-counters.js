'use strict';

// -- THE ATTEMPT COUNTER - what replaces the two byte-equality brakes [spec-recovery 5, T4-R3] --
//
// WHAT WAS BROKEN, and it was broken in two places at once. `reconcile.js` kept a `strike()` /
// `stuckStands()` pair that counted a retry only while an owed-content SIGNATURE stayed
// byte-identical, and `heart-store.js` kept a second, independent lock (`ADMISSION_BRAKE_LIMIT`)
// doing the same comparison at the enqueue door. Both signatures carried VOLATILE FIELDS -
// timestamps, session ids, a re-checkout's `ended` stamp - so an irrelevant change reset the count
// and the bound never fired: a periodic driver retried forever with no owner-visible exit
// (inventory IE-6 / ST-19 / ST-20). Both brakes are deleted [C-4 kill map]; this module is the
// ONE replacement, and there is deliberately no byte- or fingerprint-reset path beside it.
//
// THE SHAPE. A counter is keyed on (driver, subject, reason class). It advances on a SAME-REASON
// retry - the driver's failure/refusal CLASS is unchanged - and it is reset by NOTHING except the
// four named re-arm events in `RE_ARM_EVENTS`. That is the whole difference from the brakes: the
// old counters reset on evidence drift, this one resets on an EVENT SOMEONE CAUSED.
//
// N IS NEVER A LITERAL HERE. `attempt_counter_n` comes from `recovery-config.js`, which is the one
// read api for the tweakable numbers. This module takes `n` as an argument and refuses a missing
// one rather than defaulting - a default would be exactly the in-code number the config file
// exists to end.
//
// WHAT EXHAUSTION DOES IS NOT THIS FILE'S. `countAttempt` reports `exhausted: true` and stops.
// `exhaustion.js` owns the stamp and the ask record, so a driver that only needs to know whether
// to keep trying does not have to carry the ending store.
//
// WARNING - THE HOURLY FROZEN REPEAT IS EXCLUDED [C-5]. It is a DESIGNED repeat, not an unbounded
// retry: counting it would stamp the alarm's subject `incomplete:` after N hours and cancel the
// alarm [T1-R15]. `FROZEN_HOURLY_REPEAT` is a named driver this module REFUSES, so the exclusion
// is mechanical and provable rather than a line of prose impl-alarms has to remember.

const fs = require('node:fs');
const path = require('node:path');

const COUNTERS_FILENAME = 'attempt-counters.json';
const DEFAULT_COUNTERS_PATH = path.join(__dirname, COUNTERS_FILENAME);

// -- THE DRIVER LIST - spec-recovery section 5's table, as a closed set -------------------------
//
// Closed on purpose. A driver spelled freehand at a call site is a counter nobody can find, re-arm
// or report on; a driver that is not on this list is a driver whose unboundedness was never ruled.
const DRIVERS = Object.freeze({
  TICKER_DEFERRED: 'ticker-deferred',                  // build/compose retry: the DEFERRED re-fire
  RECONCILE_RESPAWN: 'reconcile-respawn',              // the CADENCE_MS wake / sitting re-spawn
  RECONCILE_CLASS_A: 'reconcile-class-a-relaunch',     // deriveOwed class A `incomplete` relaunch
  ALARM_REFIRE: 'alarm-refire',                        // any other unbounded alarm re-fire
});
const DRIVER_LIST = Object.freeze(Object.values(DRIVERS));

// The one driver that MUST NOT carry a counter, named so the refusal can be asserted.
const FROZEN_HOURLY_REPEAT = 'frozen-hourly-repeat';

// -- THE CLOSED RE-ARM LIST - spec-recovery section 5 -------------------------------------------
//
// Four events, and alarms are not one of them [T4-R10]: an alarm never re-arms anything and never
// counts as unread work that wakes anything.
const RE_ARM = Object.freeze({
  CODE_DEPLOY: 'code-deploy',
  CONFIG_CHANGE: 'config-change',           // includes a recognition-list edit
  OWNER_LEADER_ACT: 'owner-leader-act',
  RESUME: 'resume',                         // mechanical `resume {goal}` on a disarmed-counter lane
});
const RE_ARM_EVENTS = Object.freeze(Object.values(RE_ARM));

class AttemptCounterError extends Error {
  constructor(message) {
    super(message);
    this.name = 'AttemptCounterError';
    this.code = 'E_ATTEMPT_COUNTER';
  }
}

// -- THE VOLATILE-FIELD TRIPWIRE ----------------------------------------------------------------
//
// The defect this module exists to end was never "the counter was wrong": it was that the thing
// being compared MOVED. A reason class is a CLASS - `argv-template-refused`, `incomplete`,
// `unread` - and a class does not contain a timestamp, a session id or a content hash. Rather than
// trust every future call site to know that, the choke point refuses the shapes that made the old
// signatures volatile. A caller that genuinely needs one of these in the key has a design problem
// upstream, and a refusal here is where they find out.
const VOLATILE_PATTERNS = Object.freeze([
  [/\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/, 'an ISO-8601 timestamp'],
  [/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i, 'a uuid'],
  [/\b[0-9a-f]{8,}\b/i, 'a hex digest'],
  [/\b\d{6,}\b/, 'a long number (an id or an epoch)'],
]);

function refuseVolatile(reasonClass) {
  for (const [re, what] of VOLATILE_PATTERNS) {
    if (re.test(reasonClass)) {
      throw new AttemptCounterError(
        `reason class "${reasonClass}" carries ${what} - a counter key is a failure CLASS, never a volatile fingerprint [spec-recovery 5]`,
      );
    }
  }
}

function requireDriver(driver) {
  if (driver === FROZEN_HOURLY_REPEAT) {
    throw new AttemptCounterError(
      'the designed hourly frozen repeat is EXCLUDED from attempt counting [spec-recovery 5, C-5, T1-R15]',
    );
  }
  if (!DRIVER_LIST.includes(driver)) {
    throw new AttemptCounterError(`unknown driver: ${driver} (known: ${DRIVER_LIST.join(', ')})`);
  }
  return driver;
}

// A subject is the thing being retried: a `(goal, seat)` lane for the two reconcile drivers, a job
// or alarm identity for the other two. Spelled as one string so the key is one string.
function subjectOf({ goal, seat, subject }) {
  const spelled = subject || (seat ? `${goal || ''}/${seat}` : goal);
  if (!spelled) throw new AttemptCounterError('a counter needs a subject (goal+seat, or subject)');
  return String(spelled);
}

// The key separator, spelled as an ESCAPE. A literal NUL in source makes the file binary to
// git, to grep and to every reviewer's diff - the byte is right, writing it raw is not.
const SEP = '\u0000';

function keyOf({
  driver, goal, seat, subject, reasonClass,
}) {
  requireDriver(driver);
  if (!reasonClass) throw new AttemptCounterError('a counter needs a reason class');
  const cls = String(reasonClass);
  refuseVolatile(cls);
  return [driver, subjectOf({ goal, seat, subject }), cls].join(SEP);
}

// -- PERSISTENCE - one small JSON object, written tmp-then-rename -------------------------------
//
// Not a table in the ending store: spec-state-store pins THREE record kinds in that file and a
// counter is not one of them. Not `reconcile_attempts` either - that table's whole shape is the
// signature column this design deletes. One file, rewritten atomically, because an interrupted
// truncate-write is how a counter ledger becomes an empty file that re-arms every driver at once.
function countersPath(override) {
  return path.resolve(override || DEFAULT_COUNTERS_PATH);
}

function readAll(file) {
  try {
    const parsed = JSON.parse(fs.readFileSync(countersPath(file), 'utf8'));
    return (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) ? parsed : {};
  } catch {
    return {};   // absent or unreadable is "no counts yet", never a death
  }
}

function writeAll(file, rows) {
  const target = countersPath(file);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const tmp = `${target}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(rows, null, 2)}\n`, 'utf8');
  fs.renameSync(tmp, target);
}

// -- THE OWED-ITEM MARKER - what makes a pass a RETRY rather than a first attempt ---------------
//
// ⚠ READ THIS BEFORE TOUCHING IT, because it looks like the deleted brake and is its opposite.
// The deleted `strike()`/`stuckStands()` pair RESET the count whenever the owed signature drifted;
// that reset is still forbidden and is still nowhere in this file. What this marker does is answer
// the OTHER half of spec-recovery section 5's sentence - "increments on a SAME-REASON RETRY". A
// retry is a second attempt at work the counter already counted. A pass whose owed items are all
// NEW - every item the last advance counted has since been resolved - is a FIRST attempt at
// different work, and counting it as a retry is how three legitimate per-hop wakes reached N=3 on
// `scratch-tool-reach-note` (2026-08-27: classA plan-understander -> plan-designer -> plan-drafter,
// strictly replaced each hop) and disarmed the leader before its fourth, real, unread mail.
//
// THE RULE, and it is one line: the pass is a retry when the recorded item set INTERSECTS the
// current one. Overlap means some work this counter already counted still stands, and the bound
// must keep closing on it - which is exactly the [C-4] inversion the redesign ruled and
// `reconcile.selftest.js` asserts (owed set `{a}` then `{a,b}` reaches 3, because `a` never moved).
// No overlap means nothing it counted is left, so nothing was retried.
//
// AND IT NEVER RESETS. A no-overlap pass leaves `attempts` EXACTLY where it was; only
// `RE_ARM_EVENTS` clears a count. A driver that hands in no items is unchanged - it always counts.
//
// The marker lives in the ROW, never in the key: a key is a failure class [spec-recovery 5] and
// `refuseVolatile` still guards it. Items are allowed to move; that is their whole job.
function normalizeItems(items) {
  if (!Array.isArray(items)) return null;
  const out = [...new Set(items.map((i) => String(i)).filter(Boolean))].sort();
  return out.length ? out : null;
}

function isRetryOf(recorded, current) {
  if (!recorded || !current) return true;   // a driver that names no items always counts
  return current.some((i) => recorded.includes(i));
}

// -- THE API ------------------------------------------------------------------------------------

// One same-reason retry. Returns the new count and whether it reached N. `n` is the caller's, read
// from `recovery-config.js#loadRecoveryConfig().attempt_counter_n` - never defaulted here.
//
// `items` is OPTIONAL and is the owed-item marker above: the ids this pass is owed for (seat names,
// mail numbers - whatever the driver's owed set is made of). Omit it and the behaviour is
// unchanged. Hand it in and the count advances only when this pass retries work already counted.
function countAttempt({
  driver, goal, seat, subject, reasonClass, n, at, items = null,
}, { countersFile } = {}) {
  const key = keyOf({
    driver, goal, seat, subject, reasonClass,
  });
  if (!Number.isInteger(n) || n <= 0) {
    throw new AttemptCounterError(`attempt_counter_n must be a positive integer, got ${JSON.stringify(n)}`);
  }
  const rows = readAll(countersFile);
  const prev = rows[key] || { attempts: 0 };
  const stamp = at || new Date().toISOString();
  const current = normalizeItems(items);
  const recorded = normalizeItems(prev.owed_items);
  const advanced = isRetryOf(recorded, current);
  // NOT ADVANCING IS NOT RESETTING. `prev.attempts` is carried through untouched.
  const attempts = advanced ? Number(prev.attempts || 0) + 1 : Number(prev.attempts || 0);
  rows[key] = {
    driver,
    subject: subjectOf({ goal, seat, subject }),
    goal: goal || null,
    seat: seat || null,
    reason_class: String(reasonClass),
    attempts,
    first_at: prev.first_at || stamp,
    last_at: stamp,
    // The marker follows the CURRENT owed set, so the next pass compares against what this one
    // actually saw. A driver that names no items leaves whatever was already recorded.
    ...(current || recorded ? { owed_items: current || recorded } : {}),
    ...(prev.disarm_announced_at ? { disarm_announced_at: prev.disarm_announced_at } : {}),
  };
  writeAll(countersFile, rows);
  return {
    key, driver, attempts, n, advanced, exhausted: attempts >= n, row: rows[key],
  };
}

// The disarm announcement's once-marker. Written on the row rather than kept in the caller, because
// "once per (subject, disarm)" must survive a daemon restart, and because `rearm` deletes the row -
// so a re-armed lane that disarms again announces again, with no second thing to clear.
// It touches `attempts` never; a row that is not there is not created.
function markDisarmAnnounced({
  driver, goal, seat, subject, reasonClass, at,
}, { countersFile } = {}) {
  const key = keyOf({
    driver, goal, seat, subject, reasonClass,
  });
  const rows = readAll(countersFile);
  if (!rows[key]) return null;
  rows[key] = { ...rows[key], disarm_announced_at: at || new Date().toISOString() };
  writeAll(countersFile, rows);
  return rows[key];
}

// The read side, for a driver deciding whether to fire at all before it spends a launch.
function peekCounter({
  driver, goal, seat, subject, reasonClass,
}, { countersFile } = {}) {
  const key = keyOf({
    driver, goal, seat, subject, reasonClass,
  });
  return readAll(countersFile)[key] || null;
}

// -- RE-ARM - the ONLY reset path ---------------------------------------------------------------
//
// SCOPE IS DELIBERATELY BY EVENT, not by caller preference. A code deploy and a config change
// change the world for every driver, so they clear everything; an owner/leader act and a
// mechanical `resume` are about a lane, so they clear that lane (and, with `driver`, that one
// driver on it). Passing a scope the event does not own is not honoured - the event decides.
function rearm({
  event, goal, seat, subject, driver,
}, { countersFile } = {}) {
  if (!RE_ARM_EVENTS.includes(event)) {
    throw new AttemptCounterError(`unknown re-arm event: ${event} (closed list: ${RE_ARM_EVENTS.join(', ')})`);
  }
  const rows = readAll(countersFile);
  const wide = event === RE_ARM.CODE_DEPLOY || event === RE_ARM.CONFIG_CHANGE;
  const wantSubject = wide ? null : subjectOf({ goal, seat, subject });
  const reset = [];
  for (const key of Object.keys(rows)) {
    const row = rows[key];
    if (!wide && row.subject !== wantSubject) continue;
    if (!wide && driver && row.driver !== driver) continue;
    reset.push(key);
    delete rows[key];
  }
  if (reset.length) writeAll(countersFile, rows);
  return { event, scope: wide ? 'all' : wantSubject, reset };
}

module.exports = {
  COUNTERS_FILENAME,
  DEFAULT_COUNTERS_PATH,
  DRIVERS,
  DRIVER_LIST,
  FROZEN_HOURLY_REPEAT,
  RE_ARM,
  RE_ARM_EVENTS,
  AttemptCounterError,
  countersPath,
  keyOf,
  countAttempt,
  markDisarmAnnounced,
  peekCounter,
  rearm,
};
