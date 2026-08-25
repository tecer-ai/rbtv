'use strict';

// -- SELFTESTS FOR THE NO-PROGRESS KILL CLOCK AND ITS THREE PAUSES ------------------------------
//
// Two assertions carry this file. (1) Each of the three ruled pause conditions PAUSES the clock -
// a seat that would otherwise be killed is not. (2) Nothing else does: the "not a pause" cases are
// states that look like reasons to wait (a long-running seat, an expired backoff window, an
// unverified ask, a paused goal) and are ruled NOT to be [T1-R19, D-1-ruling].
//
// The window is read from the config the loader returns, never from a literal here: the whole point
// of the config contract is that no code carries the number.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const killClock = require('./kill-clock');
const { loadRecoveryConfig, RecoveryConfigError } = require('./recovery-config');
const registry = require('./registry');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'supervisor-killclock-'));
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

// The ruled three, restated here independently of the module under test.
const EXPECTED_PAUSES = ['verified-open-ask', 'provider-backoff', 'disarmed-incomplete'];

const config = loadRecoveryConfig({ file: path.join(__dirname, 'recovery.defaults.json') });
const NOW = new Date('2026-08-24T12:00:00.000Z');
// Well past the window, whatever the window is - derived from the config, not typed.
const STALE = new Date(NOW.getTime() - (config.no_progress_kill_min + 1) * killClock.MINUTE_MS).toISOString();
const RECENT = new Date(NOW.getTime() - killClock.MINUTE_MS).toISOString();

check('control: a stale seat with no pause condition IS killed', () => {
  const d = killClock.killDecision({ lastProgressAt: STALE, lane: {}, config, now: NOW });
  assert(d.kill === true, `expected a kill, got ${d.reason}`);
  assert(d.reason === 'no-progress', `reason ${d.reason}`);
});

check('pause 1: a verified open ask pauses the clock', () => {
  const d = killClock.killDecision({ lastProgressAt: STALE, lane: { verified_open_ask: true }, config, now: NOW });
  assert(d.kill === false && d.paused === true, 'the clock must pause');
  assert(d.pauseReason === killClock.PAUSE_OPEN_ASK, `reason ${d.pauseReason}`);
});

check('pause 2: an open provider-backoff window pauses the clock', () => {
  const until = new Date(NOW.getTime() + killClock.MINUTE_MS).toISOString();
  const d = killClock.killDecision({
    lastProgressAt: STALE, lane: { provider_backoff_until: until }, config, now: NOW,
  });
  assert(d.kill === false && d.paused === true, 'the clock must pause');
  assert(d.pauseReason === killClock.PAUSE_PROVIDER_BACKOFF, `reason ${d.pauseReason}`);
});

check('pause 3: a disarmed incomplete lane pauses until its named event', () => {
  const d = killClock.killDecision({
    lastProgressAt: STALE, lane: { disarmed: true, awaiting_event: 'resume {goal}' }, config, now: NOW,
  });
  assert(d.kill === false && d.paused === true, 'the clock must pause');
  assert(d.pauseReason === killClock.PAUSE_DISARMED_INCOMPLETE, `reason ${d.pauseReason}`);
  assert(killClock.pauseState({ disarmed: true, awaiting_event: 'resume {goal}' }, NOW).until === 'resume {goal}',
    'the named event is reported');
});

check('there is no fourth pause: every other lane state still kills', () => {
  const notPauses = [
    { label: 'a goal that is merely paused', lane: { goal_paused: true } },
    { label: 'a seat that looks busy', lane: { busy: true, tokens_growing: true } },
    { label: 'an ask that is NOT verified open', lane: { open_ask: false, verified_open_ask: false } },
    { label: 'an EXPIRED backoff window', lane: { provider_backoff_until: new Date(NOW.getTime() - killClock.MINUTE_MS).toISOString() } },
    { label: 'an unparseable backoff stamp', lane: { provider_backoff_until: 'soon' } },
    { label: 'a long-running seat with no deadline of its own', lane: { started_at: '2026-08-01T00:00:00.000Z' } },
    { label: 'a seat awaiting an event but NOT disarmed', lane: { awaiting_event: 'code deploy' } },
  ];
  for (const c of notPauses) {
    const state = killClock.pauseState(c.lane, NOW);
    assert(state.paused === false, `${c.label} paused the clock and must not (${state.reason})`);
    const d = killClock.killDecision({ lastProgressAt: STALE, lane: c.lane, config, now: NOW });
    assert(d.kill === true, `${c.label}: expected a kill, got ${d.reason}`);
  }
});

check('the pause list is exactly three, and they are the ruled three', () => {
  assert(killClock.PAUSE_REASONS.length === EXPECTED_PAUSES.length, `pause count ${killClock.PAUSE_REASONS.length}`);
  for (const reason of EXPECTED_PAUSES) {
    assert(killClock.PAUSE_REASONS.includes(reason), `missing pause ${reason}`);
  }
});

check('a seat inside the window is not killed, and one with no fact is never killed', () => {
  const inside = killClock.killDecision({ lastProgressAt: RECENT, lane: {}, config, now: NOW });
  assert(inside.kill === false && inside.reason === 'within-window', `reason ${inside.reason}`);
  const unknown = killClock.killDecision({ lastProgressAt: null, lane: {}, config, now: NOW });
  assert(unknown.kill === false && unknown.reason === 'no-progress-fact', `reason ${unknown.reason}`);
});

check('no config = no clock: the decision refuses rather than picking a number', () => {
  let threw = null;
  try { killClock.killDecision({ lastProgressAt: STALE, lane: {}, now: NOW }); } catch (err) { threw = err; }
  assert(threw instanceof RecoveryConfigError, `expected a RecoveryConfigError, got ${threw}`);
});

check('the clock reads the registry fact and nothing else', () => {
  const file = path.join(tmpRoot, 'clock.jsonl');
  registry.recordSpawn({ goal: 'g', seat: 'worker', pid: process.pid, last_progress_at: STALE }, file);
  const stale = killClock.killDecisionFor({ goal: 'g', seat: 'worker', config, now: NOW, registryFile: file });
  assert(stale.kill === true, `expected a kill, got ${stale.reason}`);
  registry.recordProgress({ goal: 'g', seat: 'worker' }, RECENT, file);
  const fresh = killClock.killDecisionFor({ goal: 'g', seat: 'worker', config, now: NOW, registryFile: file });
  assert(fresh.kill === false, `expected no kill, got ${fresh.reason}`);
});

fs.rmSync(tmpRoot, { recursive: true, force: true });
process.stdout.write(failed ? `\n${failed} FAILED\n` : '\nALL PASS\n');
process.exit(failed ? 1 : 0);
