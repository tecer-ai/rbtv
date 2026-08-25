'use strict';

// -- SELFTESTS FOR THE RECOVERY CONFIG FILE AND ITS SEEDING -------------------------------------
//
// Every case here is a REFUSAL case except the first, and that is the shape of the contract: the
// loader's job is to say no. The one assertion that matters most is the last clause of each
// refusal - `armed === false`. A loader that threw but left a clock running on an in-code number
// would pass a test that only checked the throw.
//
// The seeding half asserts both directions: absent instance file -> copied; existing instance file
// -> left EXACTLY as it was, byte for byte, because an upgrade that overwrites owner tweaks is the
// failure the copy-if-absent rule exists to prevent.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const cfg = require('./recovery-config');
const killClock = require('./kill-clock');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'supervisor-recovery-config-'));
let failed = 0;

function pass(name) { process.stdout.write(`PASS ${name}\n`); }
function fail(name, err) {
  failed += 1;
  process.stdout.write(`FAIL ${name}: ${err && err.message ? err.message : err}\n`);
}
function check(name, fn) {
  try { fn(); pass(name); } catch (err) { fail(name, err); }
}
function assert(cond, message) {
  if (!cond) throw new Error(message || 'assertion failed');
}

// The schema and the seeded values, restated independently of the module and of the seed file.
const EXPECTED = {
  no_progress_kill_min: 30,
  attempt_counter_n: 3,
  relaunch_budget_failures: 2,
  relaunch_budget_total: 5,
  frozen_window_min: 15,
  provider_backoff_initial_min: 15,
  provider_backoff_multiplier: 2,
  provider_backoff_cap_h: 4,
};
const KEYS = Object.keys(EXPECTED);

function writeConfig(label, body) {
  const ws = path.join(tmpRoot, label);
  const file = path.join(ws, '.rbtv', 'config', 'ignite', 'recovery.json');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, typeof body === 'string' ? body : JSON.stringify(body), 'utf8');
  return ws;
}

// "No recovery clocks armed" is not a mood: it is this. The clock refuses to decide anything
// without a config, so a failed load leaves nothing armed by construction.
function armed(workspace) {
  let config = null;
  try { config = cfg.loadRecoveryConfig({ workspace }); } catch { return false; }
  try {
    killClock.killDecision({ lastProgressAt: '2026-08-24T00:00:00.000Z', lane: {}, config, now: new Date() });
    return true;
  } catch { return false; }
}

function refuses(label, workspace, needle) {
  let threw = null;
  try { cfg.loadRecoveryConfig({ workspace }); } catch (err) { threw = err; }
  assert(threw && threw.code === 'E_RECOVERY_CONFIG', `${label}: expected a configuration-error, got ${threw}`);
  if (needle) assert(threw.message.includes(needle), `${label}: message was "${threw.message}"`);
  assert(armed(workspace) === false, `${label}: recovery clocks were armed anyway`);
}

check('a valid file: all eight values readable through the api', () => {
  const ws = writeConfig('valid', EXPECTED);
  const loaded = cfg.loadRecoveryConfig({ workspace: ws });
  for (const key of KEYS) assert(loaded[key] === EXPECTED[key], `${key} read as ${loaded[key]}`);
  assert(Object.keys(loaded).length === KEYS.length, `read ${Object.keys(loaded).length} keys`);
  assert(armed(ws) === true, 'a valid config must arm the clocks');
});

check('the instance path is the one the spec pins', () => {
  const ws = path.join(tmpRoot, 'pathcheck');
  const expected = path.join(ws, '.rbtv', 'config', 'ignite', 'recovery.json');
  assert(cfg.recoveryConfigPath(ws) === expected, `path was ${cfg.recoveryConfigPath(ws)}`);
});

check('an ABSENT file is a configuration-error, never a fallback', () => {
  refuses('absent', path.join(tmpRoot, 'never-created'), 'unreadable');
});

check('an unreadable file is a configuration-error', () => {
  const ws = writeConfig('unreadable', EXPECTED);
  const file = cfg.recoveryConfigPath(ws);
  fs.chmodSync(file, 0o000);
  // Running as root defeats a permission bit, so this case only asserts when the bit actually bites.
  let readable = true;
  try { fs.readFileSync(file, 'utf8'); } catch { readable = false; }
  if (!readable) refuses('unreadable', ws);
  fs.chmodSync(file, 0o644);
});

check('malformed JSON is a configuration-error', () => {
  refuses('malformed', writeConfig('malformed', '{ this is not json'), 'not valid JSON');
});

check('a MISSING key is a configuration-error - each of the eight, one at a time', () => {
  for (const key of KEYS) {
    const partial = { ...EXPECTED };
    delete partial[key];
    refuses(`missing ${key}`, writeConfig(`missing-${key}`, partial), 'missing required keys');
  }
});

check('an EXTRA key is refused', () => {
  refuses('extra', writeConfig('extra', { ...EXPECTED, no_progress_kill_sec: 1800 }), 'unknown keys');
});

check('a NON-INTEGER value is refused - float, string, null, boolean', () => {
  const bad = [1.5, '30', null, true, [], {}];
  for (let i = 0; i < bad.length; i += 1) {
    refuses(`non-integer ${JSON.stringify(bad[i])}`,
      writeConfig(`non-int-${i}`, { ...EXPECTED, no_progress_kill_min: bad[i] }), 'must be an integer');
  }
});

check('ZERO and NEGATIVE are configuration-error, not "disabled"', () => {
  for (const key of KEYS) {
    refuses(`zero ${key}`, writeConfig(`zero-${key}`, { ...EXPECTED, [key]: 0 }), 'greater than zero');
    refuses(`negative ${key}`, writeConfig(`neg-${key}`, { ...EXPECTED, [key]: -1 }), 'greater than zero');
  }
});

check('a JSON array or a bare number is not a config object', () => {
  refuses('array', writeConfig('array', [EXPECTED]), 'must be a JSON object');
  refuses('number', writeConfig('number', '7'), 'must be a JSON object');
});

check('the packaged seed matches the spec table exactly', () => {
  const seed = JSON.parse(fs.readFileSync(cfg.SEED_PATH, 'utf8'));
  assert(JSON.stringify(seed) === JSON.stringify(EXPECTED),
    `seed reads ${JSON.stringify(seed)}`);
  // And it is a config the loader itself accepts - a seed that would not load is a bootstrap bug
  // shipped in the package.
  const loaded = cfg.loadRecoveryConfig({ file: cfg.SEED_PATH });
  assert(loaded.no_progress_kill_min === EXPECTED.no_progress_kill_min, 'the seed must load');
});

check('seeding: an ABSENT instance file is copied from the seed', () => {
  const ws = path.join(tmpRoot, 'seed-absent');
  const result = cfg.seedRecoveryConfig(ws);
  assert(result.seeded === true, `not seeded: ${result.reason}`);
  assert(result.path === cfg.recoveryConfigPath(ws), `wrote ${result.path}`);
  const loaded = cfg.loadRecoveryConfig({ workspace: ws });
  for (const key of KEYS) assert(loaded[key] === EXPECTED[key], `${key} seeded as ${loaded[key]}`);
});

check('seeding: an EXISTING instance file is never overwritten - the owner tweak survives', () => {
  const tweaked = { ...EXPECTED, no_progress_kill_min: 45 };
  const ws = writeConfig('seed-existing', tweaked);
  const before = fs.readFileSync(cfg.recoveryConfigPath(ws), 'utf8');
  const first = cfg.seedRecoveryConfig(ws);
  const second = cfg.seedRecoveryConfig(ws);   // an upgrade run, again
  assert(first.seeded === false && second.seeded === false, 'seeding must refuse an existing file');
  const after = fs.readFileSync(cfg.recoveryConfigPath(ws), 'utf8');
  assert(after === before, 'the existing file changed');
  assert(cfg.loadRecoveryConfig({ workspace: ws }).no_progress_kill_min === tweaked.no_progress_kill_min,
    'the tweak did not survive');
});

fs.rmSync(tmpRoot, { recursive: true, force: true });
process.stdout.write(failed ? `\n${failed} FAILED\n` : '\nALL PASS\n');
process.exit(failed ? 1 : 0);
