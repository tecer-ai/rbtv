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

// ── B11 · THE ASK GOES OUT AND THE ANSWER COMES BACK ──────────────────────────────────────────
//
// Before 2026-08-26 neither half existed: `leaderHandoff` and `executeLeaderInstruction` had no
// production caller anywhere in the repo, so the leader was never asked for the four instructions
// and had no path to report one. These arms measure the two halves the wiring added.

test('B11 · the ask names the four instructions, the budget it tripped, and where to answer', () => {
  const f = fixture('ask-text');
  armedLane(f.store, 'g', 's');
  for (let i = 0; i < f.config.relaunch_budget_failures; i += 1) {
    f.store.stampSystem({
      goal: 'g', seat: 's', ending: 'failed', reason_class: 'crash', evidence_pointer: `t-${i}`, replace: true,
    });
    budget.spendRecoveryRelaunch({
      store: f.store, goal: 'g', seat: 's', cause: 'crash',
    });
  }
  const { payload } = budget.leaderHandoff({
    store: f.store,
    goal: 'g',
    seat: 's',
    brief: 'the seat brief, verbatim',
    sittingDirs: twoSittings(f.root, 's'),
    killReasons: ['no-progress kill at 30 min', 'crash with no checkout'],
    transcriptPointers: ['/tmp/transcript-1.jsonl'],
  }, f.config);

  const answerPath = budget.leaderInstructionPath(f.root, 'g', 's');
  const text = budget.handoffPayloadText(payload, answerPath);

  // Every one of the four, spelled — the leader must not have to remember a closed list [T2-R5].
  for (const kind of budget.INSTRUCTION_LIST) {
    assert.ok(text.includes(kind), `the ask does not name \`${kind}\``);
  }
  // The measured facts, not adjectives: which cap tripped and at what counts.
  assert.match(text, /EXHAUSTED/);
  assert.ok(text.includes(`${payload.budget.failures}/${payload.budget.capFailures} failures`), text.slice(0, 400));
  assert.ok(text.includes(payload.budget.tripped), 'the tripped cap is not named');
  // The brief and BOTH sittings' notes ride the ask, so the one bounded attempt is not spent
  // guessing [T4-R6].
  assert.ok(text.includes('the seat brief, verbatim'));
  assert.strictEqual((text.match(/sitting `?sitting/g) || []).length + (text.match(/progress note:/g) || []).length, 2,
    'both sittings must appear in the ask');
  assert.ok(text.includes('no-progress kill at 30 min') && text.includes('/tmp/transcript-1.jsonl'));
  // The half the payload itself cannot carry: WHERE to write the answer.
  assert.ok(text.includes(answerPath), 'the ask does not say where to answer');
  assert.ok(/one bounded|ONE attempt/i.test(text), 'the ask does not say the attempt is bounded');
  // The wall, stated to the leader and not only enforced behind its back [CF-3].
  assert.match(text, /Do not do the seat's work/);
});

test('B11 · the drain applies the leader\'s answer ONCE and gets the file out of the inbox', () => {
  const f = fixture('drain');
  armedLane(f.store, 'g', 'one');
  const dir = budget.leaderInstructionsDir(f.root);
  fs.mkdirSync(dir, { recursive: true });

  // The leader answers `reassign` — a judgment, no work product.
  const answer = budget.leaderInstructionPath(f.root, 'g', 'one');
  fs.writeFileSync(answer, JSON.stringify({ kind: 'reassign', to_seat: 'a-narrower-seat' }), 'utf8');

  // A SECOND goal's answer sits in the same inbox and must NOT be touched by this goal's drain.
  fs.writeFileSync(budget.leaderInstructionPath(f.root, 'other-goal', 'x'),
    JSON.stringify({ kind: 'escalate', report: 'not this goal' }), 'utf8');

  const applied = budget.drainLeaderInstructions({ store: f.store, workspaceRoot: f.root, goal: 'g' });
  assert.strictEqual(applied.length, 1, JSON.stringify(applied));
  assert.strictEqual(applied[0].applied, true, JSON.stringify(applied[0]));
  assert.strictEqual(applied[0].kind, 'reassign');
  assert.match(applied[0].result.ending.diagnostic, /a-narrower-seat/);

  // OUT of the pending directory, in the same act. A file that stayed would re-apply the same
  // judgment on every cadence.
  assert.ok(!fs.existsSync(answer), 'the applied instruction is still pending');
  assert.ok(fs.existsSync(applied[0].file), 'the applied instruction was not filed under done/');
  assert.ok(fs.existsSync(budget.leaderInstructionPath(f.root, 'other-goal', 'x')),
    'another goal\'s pending answer was drained by this goal\'s pass');

  // A SECOND drain finds nothing — the judgment is applied once.
  assert.deepStrictEqual(
    budget.drainLeaderInstructions({ store: f.store, workspaceRoot: f.root, goal: 'g' }), [],
  );

  // A REFUSED answer also leaves the inbox, with its reason beside it — a judgment the leader can
  // never see refused is a judgment silently dropped.
  fs.writeFileSync(budget.leaderInstructionPath(f.root, 'g', 'two'),
    JSON.stringify({ kind: 'rewrite-brief', brief: 'x', brief_path: path.join(f.root, 'b.md'), patch: 'the work' }),
    'utf8');
  const refused = budget.drainLeaderInstructions({ store: f.store, workspaceRoot: f.root, goal: 'g' });
  assert.strictEqual(refused[0].applied, false);
  assert.match(refused[0].error, /never the seat's work/);
  assert.ok(!fs.existsSync(budget.leaderInstructionPath(f.root, 'g', 'two')));
  assert.ok(fs.existsSync(path.join(dir, 'refused', 'g--two.outcome.json')));

  // Unreadable JSON is the same shape of answer: refused, moved, reason recorded — never a throw
  // that takes the pass down.
  fs.writeFileSync(budget.leaderInstructionPath(f.root, 'g', 'three'), '{not json', 'utf8');
  const broken = budget.drainLeaderInstructions({ store: f.store, workspaceRoot: f.root, goal: 'g' });
  assert.strictEqual(broken[0].applied, false);
  assert.match(broken[0].error, /unreadable JSON/);

  // NO inbox at all is the ordinary state — no leader has answered anything — and answers [].
  const g = fixture('drain-empty');
  assert.deepStrictEqual(
    budget.drainLeaderInstructions({ store: g.store, workspaceRoot: g.root, goal: 'g' }), [],
  );
});
