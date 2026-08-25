'use strict';

// The relaunch-budget suite [spec-recovery §2, T1-R6, C-11, T4-R6, CF-3, D6]. Both caps are read
// from a config file on disk, never typed as a literal in an assertion.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const budget = require('./relaunch-budget');
const exhaustion = require('./exhaustion');
const checkpoint = require('./checkpoint');
const { loadRecoveryConfig, seedRecoveryConfig } = require('./recovery-config');
const { openEndingStore } = require('../state-store/open');
const endingStore = require('../state-store');

function fixture(name) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `rbtv-budget-${name}-`));
  seedRecoveryConfig(root);
  const config = loadRecoveryConfig({ workspace: root });
  const db = openEndingStore(path.join(root, '.rbtv', 'runtime', 'ignite', 'heart.db'));
  return { root, config, store: endingStore.bind(db) };
}

function armedLane(store, goal, seat) {
  store.stampSystem({
    goal, seat, ending: 'incomplete', armed: 1, diagnostic: 'context full', evidence_pointer: `seed:${goal}/${seat}`,
  });
}

// Two sittings' progress notes, on disk, through the checkpoint contract the leader reads them by.
function twoSittings(root, seat) {
  return ['sitting-1', 'sitting-2'].map((which, i) => {
    const dir = path.join(root, 'seats', seat, which);
    fs.mkdirSync(dir, { recursive: true });
    checkpoint.writeProgressNote(dir, {
      'done-so-far': `sitting ${i + 1} did some of it`,
      'next-step': 'continue',
      'open-questions': 'none',
    });
    return dir;
  });
}

test('an ask-resume of a disarmed lane costs 0 against BOTH budget keys [C-11]', () => {
  const f = fixture('free-resume');
  armedLane(f.store, 'g', 's');
  exhaustion.exhaust({
    store: f.store,
    workspaceRoot: f.root,
    goal: 'g',
    seat: 's',
    driver: 'reconcile-class-a-relaunch',
    reasonClass: 'incomplete',
    refusalText: 'exhausted',
    attempts: f.config.attempt_counter_n,
  });
  const before = budget.budgetState({ store: f.store, goal: 'g', seat: 's' }, f.config);

  const countersFile = path.join(f.root, 'counters.json');
  exhaustion.consumeDisarmed({
    store: f.store, goal: 'g', seat: 's', driver: 'reconcile-class-a-relaunch',
  }, { countersFile });

  const after = budget.budgetState({ store: f.store, goal: 'g', seat: 's' }, f.config);
  assert.strictEqual(after.failures, before.failures, 'ask-resume spends no failure');
  assert.strictEqual(after.total, before.total, 'ask-resume spends no total');
  // And the spend door refuses the cause by name, so nobody can route it through by accident.
  assert.throws(() => budget.spendRecoveryRelaunch({
    store: f.store, goal: 'g', seat: 's', cause: 'ask-resume',
  }), /never spends the recovery relaunch budget/);
});

test('the caps come off the config file, and a missing cap is refused rather than defaulted', () => {
  const f = fixture('caps');
  armedLane(f.store, 'g', 's');
  const state = budget.budgetState({ store: f.store, goal: 'g', seat: 's' }, f.config);
  assert.strictEqual(state.capFailures, f.config.relaunch_budget_failures);
  assert.strictEqual(state.capTotal, f.config.relaunch_budget_total);
  assert.strictEqual(state.exhausted, false);
  assert.throws(
    () => budget.budgetState({ store: f.store, goal: 'g', seat: 's' }, {}),
    /no in-code default/,
  );
});

test('reaching the FAILURES cap hands off to the leader with every payload field present', () => {
  const f = fixture('cap-failures');
  armedLane(f.store, 'g', 's');
  // Each `failed` counts against both caps: the store advances the strike when the row is
  // stamped, and the relaunch that follows advances the total.
  for (let i = 0; i < f.config.relaunch_budget_failures; i += 1) {
    f.store.stampSystem({
      goal: 'g', seat: 's', ending: 'failed', reason_class: 'crash', evidence_pointer: `tail-${i}`, replace: true,
    });
    budget.spendRecoveryRelaunch({
      store: f.store, goal: 'g', seat: 's', cause: 'crash',
    });
  }
  const state = budget.budgetState({ store: f.store, goal: 'g', seat: 's' }, f.config);
  assert.strictEqual(state.exhausted, true);
  assert.strictEqual(state.tripped, 'failures');

  const { payload, ending } = budget.leaderHandoff({
    store: f.store,
    goal: 'g',
    seat: 's',
    brief: 'the seat brief, verbatim',
    sittingDirs: twoSittings(f.root, 's'),
    killReasons: ['no-progress kill at 30 min', 'crash with no checkout'],
    transcriptPointers: ['/tmp/transcript-1.jsonl', '/tmp/transcript-2.jsonl'],
  }, f.config);

  assert.strictEqual(payload.seat_brief, 'the seat brief, verbatim');
  assert.strictEqual(payload.progress_notes.length, 2, 'BOTH sittings\' notes [T4-R6]');
  assert.ok(
    payload.progress_notes.every((n) => /done-so-far/.test(n.note) && /next-step/.test(n.note)
      && /open-questions/.test(n.note)),
    'each note carries the three checkpoint fields',
  );
  assert.strictEqual(payload.kill_reasons.length, 2);
  assert.strictEqual(payload.transcript_pointers.length, 2);
  assert.strictEqual(payload.attempt, 'one-bounded-d6');
  assert.strictEqual(payload.may_execute_seat_work, false);
  assert.deepStrictEqual(payload.instruction_kinds, [
    'rewrite-brief', 'reassign', 'blocked-pending-plan-gap', 'escalate',
  ]);

  // ONE attempt, and the bound is on the row: a second handoff is refused outright.
  assert.strictEqual(Number(ending.leader_attempt_used), 1);
  assert.throws(() => budget.leaderHandoff({
    store: f.store,
    goal: 'g',
    seat: 's',
    brief: 'again',
    sittingDirs: twoSittings(f.root, 's'),
    killReasons: ['x'],
    transcriptPointers: ['y'],
  }, f.config), /already spent/);
});

test('reaching the TOTAL cap trips the budget on its own fixture', () => {
  const f = fixture('cap-total');
  armedLane(f.store, 'g', 's');
  // Recovery relaunches with no `failed` among them: the failures cap stays untouched, and the
  // total cap is what stops the lane.
  for (let i = 0; i < f.config.relaunch_budget_total; i += 1) {
    budget.spendRecoveryRelaunch({
      store: f.store, goal: 'g', seat: 's', cause: 'armed-incomplete',
    });
  }
  const state = budget.budgetState({ store: f.store, goal: 'g', seat: 's' }, f.config);
  assert.strictEqual(state.failures, 0, 'no failure was stamped');
  assert.strictEqual(state.total, f.config.relaunch_budget_total);
  assert.strictEqual(state.exhausted, true);
  assert.strictEqual(state.tripped, 'total');
});

test('a handoff with a missing payload field is refused, never assembled with a hole', () => {
  const f = fixture('payload-holes');
  armedLane(f.store, 'g', 's');
  const full = {
    store: f.store,
    goal: 'g',
    seat: 's',
    brief: 'b',
    sittingDirs: twoSittings(f.root, 's'),
    killReasons: ['k'],
    transcriptPointers: ['t'],
  };
  assert.throws(() => budget.assembleHandoff({ ...full, brief: null }, f.config), /seat brief/);
  assert.throws(() => budget.assembleHandoff({ ...full, sittingDirs: [full.sittingDirs[0]] }, f.config), /BOTH sittings/);
  assert.throws(() => budget.assembleHandoff({ ...full, killReasons: [] }, f.config), /kill reasons/);
  assert.throws(() => budget.assembleHandoff({ ...full, transcriptPointers: [] }, f.config), /transcript pointers/);
});

test('the daemon executes each of the four leader instructions, and refuses the seat\'s own work', () => {
  const f = fixture('instructions');

  // 1. rewrite-brief - the daemon writes the words the leader reported and re-arms the lane.
  armedLane(f.store, 'g', 'one');
  const briefPath = path.join(f.root, 'seats', 'one', 'brief.md');
  const rewrite = budget.executeLeaderInstruction({
    store: f.store,
    workspaceRoot: f.root,
    goal: 'g',
    seat: 'one',
    instruction: { kind: 'rewrite-brief', brief: 'a narrower brief', brief_path: briefPath },
  });
  assert.strictEqual(rewrite.executed, true);
  assert.strictEqual(fs.readFileSync(briefPath, 'utf8'), 'a narrower brief');
  assert.strictEqual(Number(rewrite.ending.armed), 1, 'the lane is re-armed for the one authorized relaunch');

  // 2. reassign - the judgment lands on the lane, naming the seat design it goes to.
  armedLane(f.store, 'g', 'two');
  const reassign = budget.executeLeaderInstruction({
    store: f.store, workspaceRoot: f.root, goal: 'g', seat: 'two',
    instruction: { kind: 'reassign', to_seat: 'a-different-seat-design' },
  });
  assert.match(reassign.ending.diagnostic, /a-different-seat-design/);
  assert.strictEqual(Number(reassign.ending.armed), 1);

  // 3. blocked-pending-plan-gap - a D13 scoped re-plan REQUEST is recorded and the lane disarms.
  armedLane(f.store, 'g', 'three');
  const blocked = budget.executeLeaderInstruction({
    store: f.store, workspaceRoot: f.root, goal: 'g', seat: 'three',
    instruction: { kind: 'blocked-pending-plan-gap', milestone: 'm2', gap: 'the plan never named the input' },
  });
  const request = JSON.parse(fs.readFileSync(blocked.replan_request, 'utf8'));
  assert.strictEqual(request.kind, 'd13-scoped-replan');
  assert.strictEqual(request.milestone, 'm2');
  assert.strictEqual(Number(blocked.ending.armed), 0, 'a plan-side halt waits for its named event');

  // 4. escalate - a formed decision-ask RECORD, and not one byte posted.
  armedLane(f.store, 'g', 'four');
  const escalate = budget.executeLeaderInstruction({
    store: f.store, workspaceRoot: f.root, goal: 'g', seat: 'four',
    instruction: { kind: 'escalate', report: 'the leader could not produce an ending' },
  });
  const record = JSON.parse(fs.readFileSync(escalate.ask.file, 'utf8'));
  assert.deepStrictEqual(record.options, ['retry-with-change', 'drop-lane', 'pause-goal']);
  assert.strictEqual(Number(escalate.ask.row.posted), 0, 'recording is not posting');

  // THE WALL [CF-3, T2-R5]: a leader reports a judgment, never the seat's work.
  assert.throws(() => budget.executeLeaderInstruction({
    store: f.store, workspaceRoot: f.root, goal: 'g', seat: 'one',
    instruction: { kind: 'rewrite-brief', brief: 'x', brief_path: briefPath, work_product: 'the seat output' },
  }), /never the seat's work/);
  assert.throws(() => budget.executeLeaderInstruction({
    store: f.store, workspaceRoot: f.root, goal: 'g', seat: 'one', instruction: { kind: 'relaunch-it-again' },
  }), /unknown leader instruction/);
});
