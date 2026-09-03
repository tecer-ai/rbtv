'use strict';

// The provider split, the one-pass reroute, the backoff, the override ruling and the readable
// facts [spec-recovery §3, C-5, C-10]. Run: `node --test`.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const lanes = require('./provider-lanes');
const killClock = require('./kill-clock');
const { loadRecoveryConfig } = require('./recovery-config');

// THE NUMBERS ARE THE LOADER'S, NEVER LITERALS. Read from the packaged seed through the same
// read api every consumer uses [spec-recovery §2.1] — a hardcoded 15 here would be the very thing
// the config file exists to end, asserted green.
const CONFIG = loadRecoveryConfig({ file: path.join(__dirname, 'recovery.defaults.json') });

// A two-row fixture table: the lane's own pin plus exactly TWO eligible alternates, so "one pass"
// is countable and a second pass is visible as a third reroute that must never happen.
const FIXTURE_TABLE = [
  'mode,harness,model,efforts,image,level,reasoning,coding,cost,use,quality-override,price-override',
  'cli,opencode,pinned-model,3,N,L1,6,6,6,route,N,N',
  'cli,claude,alt-one,5,N,L1,6,6,25,route,N,N',
  'cli,codex,alt-two,5,N,L2,4,4,20,route,N,N',
  'cli,opencode,panel-only,3,N,L2,4,4,15,panel,N,N',
  'api,anthropic,not-launchable,3,N,L1,6,6,6,route,N,N',
  '',
].join('\n');

function fixture() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'provider-lanes-'));
  const tableFile = path.join(dir, 'models.csv');
  fs.writeFileSync(tableFile, FIXTURE_TABLE, 'utf8');
  return {
    dir,
    tableFile,
    lanesFile: path.join(dir, 'provider-lanes.json'),
    cleanup: () => fs.rmSync(dir, { recursive: true, force: true }),
  };
}

const LANE = { goal: 'g-fixture', seat: 'builder' };
const PIN = { harness: 'opencode', model: 'pinned-model' };

test('the packaged knobs really are the spec §2 numbers, and they come from the loader', () => {
  assert.strictEqual(CONFIG.provider_backoff_initial_min, 15);
  assert.strictEqual(CONFIG.provider_backoff_multiplier, 2);
  assert.strictEqual(CONFIG.provider_backoff_cap_h, 4);
});

test('TRANSIENT (quota) — NO strike, ONE reroute, RECORDED on the seat', () => {
  const f = fixture();
  const out = lanes.onLaunchFailure({
    ...LANE,
    ...PIN,
    errorText: 'provider returned 429: quota exceeded for this key',
    config: CONFIG,
    lanesFile: f.lanesFile,
    tableFile: f.tableFile,
    at: '2026-08-25T10:00:00Z',
  });
  assert.strictEqual(out.classification, 'transient');
  assert.strictEqual(out.strike, false, 'a transient provider fault must NEVER strike the seat');
  assert.strictEqual(out.failed, false);
  assert.strictEqual(out.backoff_until, null, 'alternates remain — backoff is not this pass');
  assert.deepStrictEqual(
    { from: out.reroute.from, to: out.reroute.to },
    { from: 'opencode/pinned-model', to: 'claude/alt-one' },
  );

  const facts = lanes.laneFacts(LANE, { lanesFile: f.lanesFile, now: '2026-08-25T10:00:01Z' });
  assert.strictEqual(facts.reroutes.length, 1, 'the reroute is RECORDED on the seat');
  assert.strictEqual(facts.reroutes[0].to, 'claude/alt-one');
  assert.strictEqual(facts.reroutes[0].at, '2026-08-25T10:00:00.000Z');
  assert.strictEqual(facts.reroute_pending, true);
  f.cleanup();
});

test('the reroute takes its alternates from the SHARED TABLE — panel/off and api rows excluded', () => {
  const f = fixture();
  const first = lanes.onLaunchFailure({
    ...LANE, ...PIN, errorText: 'rate_limit', config: CONFIG, lanesFile: f.lanesFile, tableFile: f.tableFile,
  });
  const second = lanes.onLaunchFailure({
    ...LANE, ...PIN, errorText: 'overloaded', config: CONFIG, lanesFile: f.lanesFile, tableFile: f.tableFile,
  });
  assert.strictEqual(first.reroute.to, 'claude/alt-one');
  assert.strictEqual(second.reroute.to, 'codex/alt-two');
  // `panel-only` (use=panel) and `not-launchable` (mode=api) are never offered, and the lane's own
  // pin is never offered back to it.
  const offered = [first.reroute.to, second.reroute.to];
  assert.ok(!offered.includes('opencode/panel-only'));
  assert.ok(!offered.includes('anthropic/not-launchable'));
  assert.ok(!offered.includes('opencode/pinned-model'));
  f.cleanup();
});

test('ALL alternates transient-fail — ONE pass, then backoff with LOADER-supplied numbers', () => {
  const f = fixture();
  const common = {
    ...LANE, ...PIN, config: CONFIG, lanesFile: f.lanesFile, tableFile: f.tableFile,
  };
  const a = lanes.onLaunchFailure({ ...common, errorText: 'quota', at: '2026-08-25T10:00:00Z' });
  const b = lanes.onLaunchFailure({ ...common, errorText: 'quota', at: '2026-08-25T10:01:00Z' });
  const c = lanes.onLaunchFailure({ ...common, errorText: 'quota', at: '2026-08-25T10:02:00Z' });

  assert.ok(a.reroute && b.reroute, 'both alternates are tried');
  assert.strictEqual(c.reroute, null, 'NO SECOND PASS in the same launch attempt');
  assert.strictEqual(c.pass_exhausted, true);
  assert.strictEqual(c.strike, false, 'the exhausted pass STILL does not strike — it is transient');

  // 15 min from the loader, not from code: the assertion is arithmetic on the config value.
  const expected = new Date(Date.parse('2026-08-25T10:02:00Z')
    + CONFIG.provider_backoff_initial_min * 60 * 1000).toISOString();
  assert.strictEqual(c.backoff_until, expected);
  assert.strictEqual(c.backoff_minutes, CONFIG.provider_backoff_initial_min);

  const facts = lanes.laneFacts(LANE, { lanesFile: f.lanesFile, now: '2026-08-25T10:03:00Z' });
  assert.strictEqual(facts.reroutes.length, 2, 'exactly two reroutes — one pass, both recorded');
  assert.strictEqual(facts.provider_backoff_waiting, true);
  assert.strictEqual(facts.reroute_pending, false);
  f.cleanup();
});

test('the backoff ladder DOUBLES and CAPS on the loader values', () => {
  assert.strictEqual(lanes.backoffMinutes(1, CONFIG), 15);
  assert.strictEqual(lanes.backoffMinutes(2, CONFIG), 30);
  assert.strictEqual(lanes.backoffMinutes(3, CONFIG), 60);
  assert.strictEqual(lanes.backoffMinutes(50, CONFIG), CONFIG.provider_backoff_cap_h * 60);
  assert.throws(() => lanes.backoffMinutes(1, null), /recovery config/);
  assert.throws(() => lanes.backoffMinutes(1, { provider_backoff_initial_min: 15 }), /provider_backoff_multiplier/);
});

test('the KILL CLOCK is PAUSED for the backoff — the fact is read under its contract name', () => {
  const f = fixture();
  const common = {
    ...LANE, ...PIN, config: CONFIG, lanesFile: f.lanesFile, tableFile: f.tableFile, errorText: 'provider-down',
  };
  lanes.onLaunchFailure({ ...common, at: '2026-08-25T10:00:00Z' });
  lanes.onLaunchFailure({ ...common, at: '2026-08-25T10:00:00Z' });
  lanes.onLaunchFailure({ ...common, at: '2026-08-25T10:00:00Z' });

  const lane = lanes.laneFacts(LANE, { lanesFile: f.lanesFile, now: '2026-08-25T10:05:00Z' });
  assert.ok(lane.provider_backoff_until, 'written as ISO-8601 under the name kill-clock reads');
  const decision = killClock.killDecision({
    lastProgressAt: '2026-08-25T09:00:00Z',      // two hours idle: it would be killed but for the pause
    lane,
    config: CONFIG,
    now: new Date('2026-08-25T10:05:00Z'),
  });
  assert.strictEqual(decision.kill, false);
  assert.strictEqual(decision.pauseReason, killClock.PAUSE_PROVIDER_BACKOFF);

  // And it un-pauses on its own once the window is past — no act required.
  const after = lanes.laneFacts(LANE, { lanesFile: f.lanesFile, now: '2026-08-25T23:00:00Z' });
  assert.strictEqual(after.provider_backoff_waiting, false);
  assert.strictEqual(
    killClock.killDecision({
      lastProgressAt: '2026-08-25T09:00:00Z', lane: after, config: CONFIG, now: new Date('2026-08-25T23:00:00Z'),
    }).kill,
    true,
  );
  f.cleanup();
});

test('CONFIGURATION (bad slug) — `failed` + strike, NO reroute, NO silent backoff', () => {
  const f = fixture();
  const out = lanes.onLaunchFailure({
    ...LANE,
    ...PIN,
    errorText: 'cast: bad slug — opencode/typo-model is not a known model',
    config: CONFIG,
    lanesFile: f.lanesFile,
    tableFile: f.tableFile,
  });
  assert.strictEqual(out.classification, 'configuration');
  assert.strictEqual(out.strike, true);
  assert.strictEqual(out.failed, true);
  assert.strictEqual(out.reroute, null);
  assert.strictEqual(out.backoff_until, null, 'a configuration fault must NOT hide behind a backoff');

  const facts = lanes.laneFacts(LANE, { lanesFile: f.lanesFile });
  assert.strictEqual(facts.reroutes.length, 0);
  assert.strictEqual(facts.provider_backoff_waiting, false);
  assert.strictEqual(facts.reroute_pending, false);
  f.cleanup();
});

test('model-not-found and auth-rejected take the same strike path (ST-19 class)', () => {
  const f = fixture();
  for (const text of ['404 model', 'unknown model', 'invalid_api_key', 'unauthorized', 'auth-rejected']) {
    const out = lanes.onLaunchFailure({
      ...LANE, ...PIN, errorText: text, config: CONFIG, lanesFile: f.lanesFile, tableFile: f.tableFile,
    });
    assert.strictEqual(out.strike, true, `${text} must strike`);
    assert.strictEqual(out.reroute, null, `${text} must not reroute`);
  }
  f.cleanup();
});

test('OVERRIDE + transient — NO reroute [C-10, CP1 ruled]', () => {
  const f = fixture();
  const out = lanes.onLaunchFailure({
    ...LANE,
    ...PIN,
    override: true,
    errorText: '429 temporarily unavailable',
    config: CONFIG,
    lanesFile: f.lanesFile,
    tableFile: f.tableFile,
    at: '2026-08-25T10:00:00Z',
  });
  assert.strictEqual(out.classification, 'transient');
  assert.strictEqual(out.reroute, null, 'a per-seat model override SUPPRESSES reroute');
  assert.strictEqual(out.strike, false, 'still transient — still no strike');
  assert.ok(out.backoff_until, 'a pinned lane has no alternates, so it waits the provider out');

  const facts = lanes.laneFacts(LANE, { lanesFile: f.lanesFile, now: '2026-08-25T10:01:00Z' });
  assert.strictEqual(facts.reroutes.length, 0, 'nothing was rerouted, so nothing is recorded');
  assert.strictEqual(facts.provider_backoff_waiting, true);
  f.cleanup();
});

test('OVERRIDE + configuration — `failed` + strike, FULL STOP on the first fault', () => {
  const f = fixture();
  const out = lanes.onLaunchFailure({
    ...LANE,
    ...PIN,
    override: true,
    errorText: 'model-not-found',
    config: CONFIG,
    lanesFile: f.lanesFile,
    tableFile: f.tableFile,
  });
  assert.strictEqual(out.strike, true);
  assert.strictEqual(out.failed, true);
  assert.strictEqual(out.reroute, null);
  assert.strictEqual(out.backoff_until, null);
  assert.strictEqual(out.pass_exhausted, true, 'full stop — there is no second try to make');
  f.cleanup();
});

test('the READABLE FACTS are readable on a lane that has never faulted', () => {
  const f = fixture();
  const facts = lanes.laneFacts({ goal: 'g-fixture', seat: 'never-faulted' }, { lanesFile: f.lanesFile });
  assert.strictEqual(facts.provider_backoff_until, null);
  assert.strictEqual(facts.provider_backoff_waiting, false);
  assert.strictEqual(facts.reroute_pending, false);
  assert.deepStrictEqual(facts.reroutes, []);
  f.cleanup();
});

test('a launch that GETS THROUGH ends the attempt but keeps the seat\'s reroute history', () => {
  const f = fixture();
  lanes.onLaunchFailure({
    ...LANE, ...PIN, errorText: 'quota', config: CONFIG, lanesFile: f.lanesFile, tableFile: f.tableFile,
  });
  lanes.onLaunchSucceeded(LANE, { lanesFile: f.lanesFile });
  const facts = lanes.laneFacts(LANE, { lanesFile: f.lanesFile });
  assert.strictEqual(facts.reroute_pending, false);
  assert.strictEqual(facts.provider_backoff_waiting, false);
  assert.deepStrictEqual(facts.tried, [], 'the next attempt gets a fresh single pass');
  assert.strictEqual(facts.reroutes.length, 1, 'what this lane actually ran stays on the record');
  f.cleanup();
});
