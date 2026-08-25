'use strict';

// The attempt-counter suite [spec-recovery §5]. Everything the counter promises is asserted here
// against a REAL ending store and a REAL config file on disk: N is loaded from a written config,
// never typed as a literal in an assertion, so a test that passed because the number was hardcoded
// on both sides is not possible.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const counters = require('./attempt-counters');
const exhaustion = require('./exhaustion');
const { loadRecoveryConfig, seedRecoveryConfig } = require('./recovery-config');
const { openEndingStore } = require('../state-store/open');
const endingStore = require('../state-store');

// -- THE FIXTURE - a throwaway workspace with a seeded config file and its own ending store -----
function fixture(name) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `rbtv-counters-${name}-`));
  // The config file is SEEDED from the packaged defaults, then read back. N therefore comes off
  // disk in every assertion below - the DoD's "loaded from a test config file, not a literal".
  seedRecoveryConfig(root);
  const config = loadRecoveryConfig({ workspace: root });
  const db = openEndingStore(path.join(root, '.rbtv', 'runtime', 'ignite', 'heart.db'));
  const store = endingStore.bind(db);
  const countersFile = path.join(root, 'counters.json');
  return {
    root, config, store, countersFile, n: config.attempt_counter_n,
  };
}

// Every file the fixture wrote, relative to the workspace. The zero-Slack assertion reads this:
// the exit may write the ask record and the store, and nothing else.
function filesUnder(root) {
  const out = [];
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) walk(full);
      else out.push(path.relative(root, full));
    }
  };
  walk(root);
  return out;
}

// A lane needs a current ending row before the exit can replace it with the disarmed one.
function seedLane(store, goal, seat) {
  store.stampSystem({
    goal, seat, ending: 'incomplete', armed: 1, diagnostic: 'context full', evidence_pointer: `seed:${goal}/${seat}`,
  });
}

test('a same-reason retry counts to N and stops - N comes off the config file', () => {
  const f = fixture('to-n');
  const call = (i) => counters.countAttempt({
    driver: counters.DRIVERS.RECONCILE_CLASS_A,
    goal: 'g',
    seat: 's',
    reasonClass: 'incomplete',
    n: f.n,
    at: `2026-01-0${i + 1}T00:00:00.000Z`,
  }, { countersFile: f.countersFile });

  for (let i = 0; i < f.n - 1; i += 1) {
    const r = call(i);
    assert.strictEqual(r.attempts, i + 1);
    assert.strictEqual(r.exhausted, false, `attempt ${i + 1} of ${f.n} must not exhaust`);
  }
  const last = call(f.n - 1);
  assert.strictEqual(last.attempts, f.n);
  assert.strictEqual(last.exhausted, true);
});

test('a drifted volatile field does NOT reset the counter - same reason class still increments', () => {
  const f = fixture('volatile');
  const bump = () => counters.countAttempt({
    driver: counters.DRIVERS.RECONCILE_RESPAWN,
    goal: 'g',
    seat: 's',
    reasonClass: 'unread',
    n: f.n,
  }, { countersFile: f.countersFile });
  bump();
  // The old brake keyed on `unread:<seat>:<lastNum>` and on a re-checkout's `ended` stamp: those
  // fields moving read as PROGRESS and reset the count. Here the lane's volatile evidence has
  // moved (a new message number, a new timestamp) and the counter does not care, because the
  // reason CLASS is what it counts.
  const second = bump();
  assert.strictEqual(second.attempts, 2, 'a drifting volatile field must not reset the count');

  // And a key that TRIES to carry a volatile field is refused outright.
  for (const bad of ['unread:2026-08-25T10:00', 'unread:deadbeefcafe', 'unread:1724579200']) {
    assert.throws(() => counters.countAttempt({
      driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'g', seat: 's', reasonClass: bad, n: f.n,
    }, { countersFile: f.countersFile }), /volatile fingerprint/);
  }
});

test('each of the four named re-arm events resets the counter, and only those four exist', () => {
  assert.deepStrictEqual(
    [...counters.RE_ARM_EVENTS].sort(),
    ['code-deploy', 'config-change', 'owner-leader-act', 'resume'],
  );
  for (const event of counters.RE_ARM_EVENTS) {
    const f = fixture(`rearm-${event}`);
    const key = {
      driver: counters.DRIVERS.RECONCILE_CLASS_A, goal: 'g', seat: 's', reasonClass: 'incomplete',
    };
    counters.countAttempt({ ...key, n: f.n }, { countersFile: f.countersFile });
    counters.countAttempt({ ...key, n: f.n }, { countersFile: f.countersFile });
    assert.strictEqual(
      counters.peekCounter(key, { countersFile: f.countersFile }).attempts, 2, `${event}: precondition`,
    );

    const reset = counters.rearm({ event, goal: 'g', seat: 's' }, { countersFile: f.countersFile });
    assert.strictEqual(reset.reset.length, 1, `${event} must reset the lane's counter`);
    assert.strictEqual(counters.peekCounter(key, { countersFile: f.countersFile }), null, `${event} must clear it`);

    // And after the reset the driver starts from 1 again - the re-arm is a real re-arm.
    const after = counters.countAttempt({ ...key, n: f.n }, { countersFile: f.countersFile });
    assert.strictEqual(after.attempts, 1);
  }
  // Anything not on the closed list is refused - an alarm never re-arms [T4-R10].
  const f = fixture('rearm-refuse');
  assert.throws(
    () => counters.rearm({ event: 'alarm', goal: 'g', seat: 's' }, { countersFile: f.countersFile }),
    /unknown re-arm event/,
  );
});

test('every spec §5 driver row counts and exhausts; the hourly frozen repeat is EXCLUDED', () => {
  const f = fixture('drivers');
  const expected = [
    'ticker-deferred', 'reconcile-respawn', 'reconcile-class-a-relaunch', 'alarm-refire',
  ];
  assert.deepStrictEqual([...counters.DRIVER_LIST], expected, 'the driver list is spec §5\'s table');

  for (const driver of counters.DRIVER_LIST) {
    let last = null;
    for (let i = 0; i < f.n; i += 1) {
      last = counters.countAttempt({
        driver, subject: `subject-${driver}`, reasonClass: 'same-refusal', n: f.n,
      }, { countersFile: f.countersFile });
      assert.strictEqual(last.attempts, i + 1, `${driver} counts each retry`);
    }
    assert.strictEqual(last.exhausted, true, `${driver} exhausts at N=${f.n}`);
  }

  // THE EXCLUSION [C-5, T1-R15]. Counting the designed hourly frozen repeat would stamp the
  // alarm's own subject `incomplete:` after N hours and cancel the alarm - so it is refused.
  assert.throws(() => counters.countAttempt({
    driver: counters.FROZEN_HOURLY_REPEAT, subject: 'frozen-goal', reasonClass: 'frozen', n: f.n,
  }, { countersFile: f.countersFile }), /EXCLUDED from attempt counting/);
  assert.ok(!counters.DRIVER_LIST.includes(counters.FROZEN_HOURLY_REPEAT));
});

test('exhaustion: disarmed incomplete + a grouped ask record on disk, and ZERO Slack or outbox writes', () => {
  const f = fixture('exhaust');
  seedLane(f.store, 'g', 's');

  let last = null;
  for (let i = 0; i < f.n; i += 1) {
    last = counters.countAttempt({
      driver: counters.DRIVERS.TICKER_DEFERRED, goal: 'g', seat: 's', reasonClass: 'unknown-tool', n: f.n,
    }, { countersFile: f.countersFile });
  }
  assert.strictEqual(last.exhausted, true);
  // Snapshot AFTER the counting: the counter's own ledger is not the exit's write.
  const before = filesUnder(f.root);

  const out = exhaustion.exhaust({
    store: f.store,
    workspaceRoot: f.root,
    goal: 'g',
    seat: 's',
    driver: counters.DRIVERS.TICKER_DEFERRED,
    reasonClass: 'unknown-tool',
    refusalText: 'the tool this row fires does not exist',
    attempts: last.attempts,
  });

  // The ending: `incomplete` + disarmed, with the store's own listed words - not invented here.
  assert.strictEqual(out.ending.ending, 'incomplete');
  assert.strictEqual(Number(out.ending.armed), 0, 'exhaustion PRODUCES disarmed');
  assert.strictEqual(out.ending.diagnostic, 'attempt-counter exhaustion');
  assert.ok(out.ending.named_event, 'a disarmed lane names the event that re-arms it');

  // The record on disk, with the refusal text and the ladder's three options.
  const record = JSON.parse(fs.readFileSync(out.ask.file, 'utf8'));
  assert.strictEqual(record.kind, 'signature-grouped');
  assert.deepStrictEqual(record.options, ['retry-with-change', 'drop-lane', 'pause-goal']);
  assert.strictEqual(record.lanes.length, 1);
  assert.strictEqual(record.lanes[0].refusal_text, 'the tool this row fires does not exist');
  assert.strictEqual(out.ending.evidence_pointer, out.ask.file, 'the lane points at the refusal text');

  // The store row exists and is NOT posted: posting is impl-slack's, and this path never does it.
  assert.strictEqual(out.ask.row.state, 'open');
  assert.strictEqual(Number(out.ask.row.posted), 0);
  assert.strictEqual(out.ask.row.posted_at, null);

  // ZERO Slack / outbox writes. The only new files are the ask record and the store's own.
  const added = filesUnder(f.root).filter((x) => !before.includes(x));
  const stray = added.filter((x) => !x.startsWith(path.join('.rbtv', 'runtime', 'ignite', 'asks'))
    && !x.startsWith(path.join('.rbtv', 'runtime', 'ignite', 'heart.db')));
  assert.deepStrictEqual(stray, [], `the exit wrote something it may not: ${stray.join(', ')}`);
  assert.deepStrictEqual(
    added.filter((x) => /outbox|slack|digest|messages\.md/i.test(x)), [], 'no outbox or Slack write',
  );
});

test('signature grouping: two lanes with one signature make ONE ask; a second signature makes a second', () => {
  const f = fixture('grouping');
  for (const seat of ['alpha', 'beta', 'gamma']) seedLane(f.store, 'g', seat);

  const a = exhaustion.exhaust({
    store: f.store, workspaceRoot: f.root, goal: 'g', seat: 'alpha', attempts: f.n,
    driver: counters.DRIVERS.RECONCILE_CLASS_A, reasonClass: 'incomplete', refusalText: 'same refusal',
  });
  const b = exhaustion.exhaust({
    store: f.store, workspaceRoot: f.root, goal: 'g', seat: 'beta', attempts: f.n,
    driver: counters.DRIVERS.RECONCILE_CLASS_A, reasonClass: 'incomplete', refusalText: 'same refusal',
  });
  assert.strictEqual(a.ask.ask_id, b.ask.ask_id, 'one ask per SIGNATURE, never per lane');
  assert.strictEqual(b.ask.grouped, true);
  const shared = JSON.parse(fs.readFileSync(b.ask.file, 'utf8'));
  assert.deepStrictEqual(shared.lanes.map((l) => l.seat), ['alpha', 'beta']);

  const c = exhaustion.exhaust({
    store: f.store, workspaceRoot: f.root, goal: 'g', seat: 'gamma', attempts: f.n,
    driver: counters.DRIVERS.RECONCILE_CLASS_A, reasonClass: 'unread', refusalText: 'a different refusal',
  });
  assert.notStrictEqual(c.ask.ask_id, a.ask.ask_id, 'a different signature opens a second ask');
  const dir = exhaustion.asksDir(f.root);
  assert.strictEqual(fs.readdirSync(dir).filter((x) => x.endsWith('.json')).length, 2);
});

test('a mechanical resume consumes the disarmed flag and resets that counter, spending no budget', () => {
  const f = fixture('resume');
  seedLane(f.store, 'g', 's');
  const key = {
    driver: counters.DRIVERS.RECONCILE_CLASS_A, goal: 'g', seat: 's', reasonClass: 'incomplete',
  };
  for (let i = 0; i < f.n; i += 1) counters.countAttempt({ ...key, n: f.n }, { countersFile: f.countersFile });
  exhaustion.exhaust({
    store: f.store, workspaceRoot: f.root, goal: 'g', seat: 's', attempts: f.n,
    driver: key.driver, reasonClass: 'incomplete', refusalText: 'exhausted',
  });
  const before = f.store.getCurrentEnding({ goal: 'g', seat: 's' });
  assert.strictEqual(Number(before.armed), 0);

  const out = exhaustion.consumeDisarmed({
    store: f.store, goal: 'g', seat: 's', driver: key.driver,
  }, { countersFile: f.countersFile });

  assert.strictEqual(out.consumed, true);
  assert.strictEqual(Number(out.ending.armed), 1, 'resume re-arms the lane');
  assert.strictEqual(out.ending.named_event, null);
  assert.strictEqual(counters.peekCounter(key, { countersFile: f.countersFile }), null, 'and resets THAT counter');
  // [C-11] - the resume spent nothing. Both budget-bearing counters are exactly where they were.
  assert.strictEqual(
    Number(out.ending.recovery_relaunch_count), Number(before.recovery_relaunch_count),
    'an ask-resume never spends the relaunch budget',
  );
  assert.strictEqual(Number(out.ending.failure_strike_count), Number(before.failure_strike_count));
});
