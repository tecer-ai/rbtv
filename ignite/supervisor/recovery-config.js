'use strict';

// -- THE RECOVERY CONFIG FILE - the ONLY source of the recovery numbers [spec-recovery 2.1] ------
//
// WHAT WAS BROKEN. Every recovery number lived as a literal in the code that used it: the strike
// bound in `reconcile.js`, `ADMISSION_BRAKE_LIMIT` in `heart-store.js`, the stall knobs in
// `ticker.js`. Tuning one meant editing daemon source, and two files could hold two answers to the
// same question. CP1 ruled the eight knobs into ONE tweakable JSON file under `.rbtv/config/`.
//
// THE CONTRACT, and every clause of it is a refusal. All eight keys are REQUIRED; extra keys are
// REFUSED; values are integers only; `0` or negative is a configuration-error. A missing,
// unreadable or invalid file is a configuration-error too - and the point of the whole module is
// what happens next: the daemon REFUSES TO APPLY RECOVERY CLOCKS. There is no in-code fallback,
// not even a silent one. A fallback would mean an instance whose config file never got seeded runs
// on numbers nobody can see or tweak, which is the state this file exists to end.
//
// WHY NO CACHE. The file is read at boot and again on a config-change re-arm (spec section 5), and
// those are the same act: call `loadRecoveryConfig` again. A cache would need an invalidation path
// for exactly one caller, and an invalidation path is how a re-arm silently keeps the old numbers.
//
// WHO READS IT. This module is the ONE read api. impl-recovery-counters-budget reads
// `attempt_counter_n` + both relaunch-budget keys, impl-recovery-provider-lanes reads the three
// backoff keys, impl-alarms reads `frozen_window_min` - all of them through `loadRecoveryConfig`,
// none of them by opening the file. Seats never read it at all: `.rbtv/config/` is daemon admin.

const fs = require('node:fs');
const path = require('node:path');

// The instance path spec-recovery 2.1 pins, and the packaged seed spec-component-map homes here.
// The seed ships beside this file; the instance file is per-workspace and carries owner tweaks.
const CONFIG_REL = path.join('.rbtv', 'config', 'ignite', 'recovery.json');
const SEED_PATH = path.join(__dirname, 'recovery.defaults.json');

// Every key required, no key optional, nothing else accepted. The order is the spec table's.
const RECOVERY_KEYS = Object.freeze([
  'no_progress_kill_min',
  'attempt_counter_n',
  'relaunch_budget_failures',
  'relaunch_budget_total',
  'frozen_window_min',
  'provider_backoff_initial_min',
  'provider_backoff_multiplier',
  'provider_backoff_cap_h',
]);

// One typed error for every refusal above, because a caller has exactly one correct response to
// all of them - do not arm the clocks - and a caller that has to tell "file missing" from "value
// was zero" apart in order to decide has already been given the chance to guess a number.
class RecoveryConfigError extends Error {
  constructor(message) {
    super(message);
    this.name = 'RecoveryConfigError';
    this.code = 'E_RECOVERY_CONFIG';
  }
}

function recoveryConfigPath(workspace) {
  if (!workspace) throw new RecoveryConfigError('recovery config needs a workspace root');
  return path.join(path.resolve(workspace), CONFIG_REL);
}

// -- VALIDATION - the whole schema, in one pass, refusing at the first fault --------------------
function validateRecoveryConfig(raw, where) {
  const at = where ? ` (${where})` : '';
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new RecoveryConfigError(`recovery config must be a JSON object${at}`);
  }
  const missing = RECOVERY_KEYS.filter((k) => !Object.prototype.hasOwnProperty.call(raw, k));
  if (missing.length) {
    throw new RecoveryConfigError(`recovery config is missing required keys${at}: ${missing.join(', ')}`);
  }
  const extra = Object.keys(raw).filter((k) => !RECOVERY_KEYS.includes(k));
  if (extra.length) {
    throw new RecoveryConfigError(`recovery config carries unknown keys${at}: ${extra.join(', ')}`);
  }
  for (const key of RECOVERY_KEYS) {
    const value = raw[key];
    if (typeof value !== 'number' || !Number.isInteger(value)) {
      throw new RecoveryConfigError(`recovery config key ${key} must be an integer${at}, got ${JSON.stringify(value)}`);
    }
    // Zero and negative are configuration-error by the spec, not a "disable" switch: a knob nobody
    // can read as "off" is a knob that cannot silently turn a clock off.
    if (value <= 0) {
      throw new RecoveryConfigError(`recovery config key ${key} must be greater than zero${at}, got ${value}`);
    }
  }
  return Object.freeze({ ...raw });
}

// -- THE READ API - `workspace` for the real daemon, `file` for a probe or a selftest -----------
function loadRecoveryConfig({ workspace, file } = {}) {
  const target = file ? path.resolve(file) : recoveryConfigPath(workspace);
  let text;
  try {
    text = fs.readFileSync(target, 'utf8');
  } catch (err) {
    // ENOENT gets the same treatment as EACCES on purpose: "no numbers" and "unreadable numbers"
    // are one state to a caller who may not invent numbers either way.
    throw new RecoveryConfigError(`recovery config is unreadable at ${target}: ${err.code || err.message}`);
  }
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (err) {
    throw new RecoveryConfigError(`recovery config is not valid JSON at ${target}: ${err.message}`);
  }
  return validateRecoveryConfig(parsed, target);
}

// The boot load and the config-change re-arm (spec section 5) are the SAME call - see WHY NO CACHE.
const armRecoveryClocks = loadRecoveryConfig;

// -- SEEDING - copy-if-absent, and an upgrade may never overwrite -------------------------------
//
// Deliberately NOT called from `loadRecoveryConfig`: a loader that seeds on a miss can never
// report a missing file, and "missing file is a configuration-error" is the contract. Seeding is
// an installer / first-bootstrap act, reached explicitly.
function seedRecoveryConfig(workspace, { seed = SEED_PATH } = {}) {
  const target = recoveryConfigPath(workspace);
  if (fs.existsSync(target)) return { path: target, seeded: false, reason: 'instance file already exists' };
  fs.mkdirSync(path.dirname(target), { recursive: true });
  // `wx` is the guard, not the `existsSync` above: two installs racing would both pass the check,
  // and only one may write. The loser keeps the existing file, which is the rule.
  try {
    fs.writeFileSync(target, fs.readFileSync(seed, 'utf8'), { flag: 'wx' });
  } catch (err) {
    if (err.code === 'EEXIST') return { path: target, seeded: false, reason: 'instance file already exists' };
    throw err;
  }
  return { path: target, seeded: true, reason: 'copied from the packaged seed' };
}

module.exports = {
  CONFIG_REL,
  SEED_PATH,
  RECOVERY_KEYS,
  RecoveryConfigError,
  recoveryConfigPath,
  validateRecoveryConfig,
  loadRecoveryConfig,
  armRecoveryClocks,
  seedRecoveryConfig,
};
