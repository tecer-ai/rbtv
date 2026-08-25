'use strict';

// -- SELFTESTS FOR THE FROZEN-GOAL SCHEDULER INVARIANT ------------------------------------------
//
// The two fixtures the design names, run as a DISCRIMINATING PAIR - identical in every fact except
// the one under test, so a green FIXTURE A cannot be green for a reason that has nothing to do with
// the invariant:
//
//   FIXTURE A  running goal · no live seat · no eligible launch · no open ask · not paused,
//              held past the window on an injected clock  →  EXACTLY ONE alarm.
//   FIXTURE B  the same goal, the same facts, the same clock, plus provider-backoff-waiting
//              →  ZERO alarms. [C-5]
//
// Liveness comes from the supervisor registry and only from it, so the live-seat arm writes a REAL
// row for a REAL live process (this test's own): a fabricated pid would prove nothing about a probe
// whose job is to read the live process table.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert');

const { createAlarmEmitter } = require('./emitter');
const { createFrozenInvariant, CONDITION } = require('./frozen');
const { makeRecord, saveRegistry } = require('../supervisor/registry');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'observation-frozen-'));
let failed = 0;
const FROZEN_WINDOW_MIN = 15;   // spec-recovery's seeded `frozen_window_min`, handed in as a caller would

function pass(name) { process.stdout.write(`PASS ${name}\n`); }
function fail(name, err) {
  failed += 1;
  process.stdout.write(`FAIL ${name}: ${err && err.message ? err.message : err}\n`);
  if (err && err.stack) process.stdout.write(`${err.stack}\n`);
}

// The frozen facts, all four arms true. Every fixture below is this object plus ONE flipped fact.
function observation(extra = {}) {
  return {
    goal_id: 'ignite-engine',
    goal_state: 'running',
    paused: false,
    eligible_launch: false,
    open_ask: false,
    provider_backoff_waiting: false,
    reroute_pending: false,
    channel_id: 'C-goal-ignite-engine',
    evidence_pointer: '.rbtv/goals/ignite-engine/coordination/',
    ...extra,
  };
}

function harness(label, { registryFile = null } = {}) {
  const dir = path.join(tmpRoot, label);
  fs.mkdirSync(dir, { recursive: true });
  const posts = [];
  let ms = Date.parse('2026-08-24T10:00:00.000Z');
  const emitter = createAlarmEmitter({
    storePath: path.join(dir, 'alarm-registry.json'),
    post: async (input) => { posts.push(input); return { delivered: true, ts: 'ts', outbox_id: `ob-${posts.length}` }; },
    now: () => new Date(ms).toISOString(),
  });
  const frozen = createFrozenInvariant({
    emitter,
    frozenWindowMin: FROZEN_WINDOW_MIN,
    registryFile: registryFile || path.join(dir, 'registry.jsonl'),
    holdsPath: path.join(dir, 'frozen-holds.json'),
    now: () => ms,
  });
  return {
    posts, emitter, frozen, dir,
    advanceMin: (n) => { ms += n * 60 * 1000; },
    rows: () => {
      try { return JSON.parse(fs.readFileSync(path.join(dir, 'alarm-registry.json'), 'utf8')).rows; } catch { return []; }
    },
  };
}

// FIXTURE A — the invariant holds past the window. Exactly one alarm.
async function caseFixtureAFrozenEmitsExactlyOne() {
  const name = 'FIXTURE A: running, no live seat, no eligible launch, no open ask, not paused, held 15 min → exactly one alarm';
  const h = harness('fixture-a');
  const t0 = await h.frozen.checkOne(observation());
  assert.strictEqual(t0.frozen, true);
  assert.strictEqual(t0.emitted, null, 'the window has not elapsed at first observation');
  h.advanceMin(10);
  assert.strictEqual((await h.frozen.checkOne(observation())).emitted, null, '10 min in: still inside the window');
  h.advanceMin(6);
  const fired = await h.frozen.checkOne(observation());
  assert.strictEqual(fired.emitted, 'first', '16 min in: the alarm fires');
  // Two more passes inside the hour: still ONE alarm, not one per tick.
  h.advanceMin(1);
  await h.frozen.checkOne(observation());
  h.advanceMin(1);
  await h.frozen.checkOne(observation());
  assert.strictEqual(h.posts.length, 1, 'exactly one alarm');
  assert.strictEqual(h.rows().length, 1, 'exactly one registry row');
  assert.ok(h.posts[0].payload.includes(CONDITION), 'the alarm says what was observed');
  assert.strictEqual(h.posts[0].channel_id, 'C-goal-ignite-engine', 'a goal freeze posts in the goal channel');
  process.stdout.write(`  FIXTURE A: posts=${h.posts.length} rows=${h.rows().length}\n`);
  pass(name);
}

// FIXTURE B — identical, plus the C-5 exclusion. Zero alarms, ever.
async function caseFixtureBProviderBackoffNeverFires() {
  const name = 'FIXTURE B: the same goal but provider-backoff-waiting → zero alarms [C-5]';
  const h = harness('fixture-b');
  const o = observation({ provider_backoff_waiting: true });
  const first = await h.frozen.checkOne(o);
  assert.strictEqual(first.frozen, false);
  assert.match(first.reason, /provider-backoff/);
  h.advanceMin(20);
  await h.frozen.checkOne(o);
  h.advanceMin(120);
  await h.frozen.checkOne(o);
  assert.strictEqual(h.posts.length, 0, 'a backoff-waiting lane must NEVER page the owner');
  assert.strictEqual(h.rows().length, 0, 'and must never register a condition');
  process.stdout.write(`  FIXTURE B: posts=${h.posts.length} rows=${h.rows().length}\n`);
  pass(name);
}

async function caseRerouteExclusion() {
  const name = 'reroute-pending (uncastSeats skip) → zero alarms [C-5]';
  const h = harness('reroute');
  const o = observation({ reroute_pending: true });
  await h.frozen.checkOne(o);
  h.advanceMin(30);
  await h.frozen.checkOne(o);
  assert.strictEqual(h.posts.length, 0);
  pass(name);
}

// Each non-frozen arm on its own, so a broken conjunction cannot hide behind another true arm.
async function caseEveryArmSuppresses() {
  const name = 'each of paused / eligible-launch / open-ask / not-running suppresses on its own';
  for (const [label, extra] of [
    ['paused', { paused: true }],
    ['eligible launch', { eligible_launch: true }],
    ['open ask', { open_ask: true }],
    ['not running', { goal_state: 'completed' }],
  ]) {
    const h = harness(`arm-${label.replace(/ /g, '-')}`);
    await h.frozen.checkOne(observation(extra));
    h.advanceMin(30);
    await h.frozen.checkOne(observation(extra));
    assert.strictEqual(h.posts.length, 0, `${label} must suppress the alarm`);
  }
  pass(name);
}

// Liveness is the supervisor registry and nothing else [T4-R8] — proven against a REAL live pid.
async function caseLiveSeatOnRegistrySuppresses() {
  const name = 'a live row on the supervisor registry suppresses the alarm [T4-R8]';
  const dir = path.join(tmpRoot, 'live-seat');
  fs.mkdirSync(dir, { recursive: true });
  const registryFile = path.join(dir, 'registry.jsonl');
  saveRegistry([makeRecord({ goal: 'ignite-engine', seat: 'worker', pid: process.pid })], registryFile);
  const h = harness('live-seat-h', { registryFile });
  await h.frozen.checkOne(observation());
  h.advanceMin(30);
  const verdict = await h.frozen.checkOne(observation());
  assert.strictEqual(verdict.frozen, false);
  assert.match(verdict.reason, /live seat\(s\) on the supervisor registry/);
  assert.strictEqual(h.posts.length, 0);
  // Drop the row: the same goal, the same clock, now frozen. The registry is what changed.
  saveRegistry([], registryFile);
  h.advanceMin(30);
  await h.frozen.checkOne(observation());
  h.advanceMin(20);
  assert.strictEqual((await h.frozen.checkOne(observation())).emitted, 'first');
  assert.strictEqual(h.posts.length, 1);
  pass(name);
}

async function caseHourlyRepeatAndClear() {
  const name = 'the alarm repeats hourly while the condition holds, then clears when it lifts';
  const h = harness('hourly');
  await h.frozen.checkOne(observation());
  h.advanceMin(16);
  await h.frozen.checkOne(observation());
  h.advanceMin(30);
  await h.frozen.checkOne(observation());
  assert.strictEqual(h.posts.length, 1, '30 min after the first alarm: no repeat yet');
  h.advanceMin(31);
  const repeat = await h.frozen.checkOne(observation());
  assert.strictEqual(repeat.emitted, 'repeat');
  assert.strictEqual(h.posts.length, 2);
  assert.strictEqual(h.rows().length, 1, 'the hourly repeat is one row, not one row per hour');
  // The condition lifts: the registry row leaves the digest, silently.
  const lifted = await h.frozen.checkOne(observation({ eligible_launch: true }));
  assert.strictEqual(lifted.cleared, true);
  assert.strictEqual(h.emitter.readOpenConditions().length, 0);
  assert.strictEqual(h.posts.length, 2, 'clearing posts nothing');
  pass(name);
}

// The hold clock is on disk, so a daemon restart mid-freeze does not reset the 15 minutes.
async function caseHoldSurvivesRestart() {
  const name = 'the hold clock is persisted — a restart mid-freeze does not restart the window';
  const dir = path.join(tmpRoot, 'hold-restart');
  fs.mkdirSync(dir, { recursive: true });
  const posts = [];
  let ms = Date.parse('2026-08-24T10:00:00.000Z');
  const build = () => {
    const emitter = createAlarmEmitter({
      storePath: path.join(dir, 'alarm-registry.json'),
      post: async (i) => { posts.push(i); return { delivered: true, ts: 'ts', outbox_id: 'ob' }; },
      now: () => new Date(ms).toISOString(),
    });
    return createFrozenInvariant({
      emitter,
      frozenWindowMin: FROZEN_WINDOW_MIN,
      registryFile: path.join(dir, 'registry.jsonl'),
      holdsPath: path.join(dir, 'frozen-holds.json'),
      now: () => ms,
    });
  };
  await build().checkOne(observation());
  ms += 16 * 60 * 1000;
  const afterRestart = await build().checkOne(observation());
  assert.strictEqual(afterRestart.emitted, 'first', 'the window is counted from the persisted hold');
  assert.strictEqual(posts.length, 1);
  pass(name);
}

async function caseWindowIsRequired() {
  const name = 'frozen_window_min is required — no silent hardcoded fallback [spec-recovery §2.1]';
  const emitter = { emit: async () => ({}), clear: () => ({ cleared: false }) };
  assert.throws(() => createFrozenInvariant({ emitter }), /frozen_window_min/);
  assert.throws(() => createFrozenInvariant({ emitter, frozenWindowMin: 0 }), /frozen_window_min/);
  pass(name);
}

const cases = [
  caseFixtureAFrozenEmitsExactlyOne,
  caseFixtureBProviderBackoffNeverFires,
  caseRerouteExclusion,
  caseEveryArmSuppresses,
  caseLiveSeatOnRegistrySuppresses,
  caseHourlyRepeatAndClear,
  caseHoldSurvivesRestart,
  caseWindowIsRequired,
];

(async () => {
  for (const fn of cases) {
    try { await fn(); } catch (err) { fail(fn.name, err); }
  }
  try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch { /* tmp */ }
  if (failed) {
    process.stdout.write(`${failed} FAIL\n`);
    process.exit(1);
  }
  process.stdout.write('ALL PASS\n');
})();
