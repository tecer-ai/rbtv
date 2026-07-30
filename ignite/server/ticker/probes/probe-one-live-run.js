'use strict';

// Task 7.129 / M4-14 — R9's one-live-run queue rule: a scheduled start that finds an OPEN run of
// the same goal is QUEUED, not started, and the decision emits
// `{scheduled-start, open-run-found, action: "queued"}`.
//
// SEVEN CHECKS, and the ones that carry the weight are the CONTROLS.
//
//   C1  one open run  -> the row is NOT fired (no jobs_log row, the queue row survives) and the
//                        tick records `action: 'queued'`.
//   C2  no open run   -> the row IS fired. THE CONTROL: a scheduler that queues everything passes
//                        C1 and is not this rule. Without C2, C1 is satisfied by "never start".
//   C3  the read site -> the answer comes from `<goal>/runs.csv`'s `state` column via the ONE
//                        reader (`openRunsOfGoal`), and NOT from the run folder existing. Measured
//                        by giving the goal a run FOLDER for a run whose register row is `closed`:
//                        a folder-keyed rule starts on that; this one must too (i.e. the folder
//                        must not make it queue), and then queue when only the register says open.
//   C4  event fields  -> all three declared fields present; `open-run-found` names WHICH run.
//   C5  register bad  -> absent / no `state` column / unparseable-state register QUEUES; it never
//                        silently starts. Fail-closed, and checked, not merely intended.
//   C6  two open rows -> QUEUED with both run-ids named and no pick made.
//   C7  not a run start -> a `fire-tool` job homed at the SAME goal with the SAME open run FIRES.
//                        THE C4-relevant control: the gate must not stop the watchers and self-heal
//                        jobs that exist precisely to run while a run is open.
//
// `store.config.workflows` is assigned after `setup()` because that object IS the composition
// root's parameter — the daemon passes it at `openHeartStore`. lib.setup() opens with `{}` and this
// probe needs one workflow row, so it supplies it the same way the daemon does. Nothing about the
// rule's inputs is hand-fed: the register is a real file on disk, read by the real reader, and the
// decision is reached inside a real `ticker.tick()`.

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, capture } = require('./lib');
const { describeGate, oneLiveRunDecision } = require('../one-live-run');

const WORKFLOW = 'start-a-run';

// The tally is COUNTED, never typed: a hand-written "18/18" is a claim about the file that stops
// being true the moment a check is added, and it would read as green while covering less.
let passed = 0;
function assert(lines, ok, label, detail = '') {
  lines.push(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? ` — ${detail}` : ''}`);
  if (!ok) throw new Error(`check failed: ${label}${detail ? ` — ${detail}` : ''}`);
  passed += 1;
}

// A real goal tree: goals.csv row + runs.csv. `runsCsv` is written verbatim so a scenario can put
// any header/state in it, including a broken one.
function makeGoal(wsRoot, { goal, runsCsv, runFolders = [] }) {
  const goalsDir = path.join(wsRoot, '.rbtv', 'goals');
  const goalDir = path.join(goalsDir, goal);
  fs.mkdirSync(goalDir, { recursive: true });
  const goalsCsvPath = path.join(goalsDir, 'goals.csv');
  if (!fs.existsSync(goalsCsvPath)) fs.writeFileSync(goalsCsvPath, 'name,state\n');
  fs.appendFileSync(goalsCsvPath, `${goal},open\n`);
  if (runsCsv !== null) fs.writeFileSync(path.join(goalDir, 'runs.csv'), runsCsv);
  for (const r of runFolders) fs.mkdirSync(path.join(goalDir, 'runs', r, 'seats'), { recursive: true });
  return goalDir;
}

function registerRunStart(ctx, { jobId, goal, seat = 'entry' }) {
  return ctx.store.registerJob({
    jobId,
    actionType: 'start-workflow',
    function: 'start-workflow',
    argsSchema: JSON.stringify({ required: { workflow: 'string' }, optional: { workdir: 'string' } }),
    goalName: goal,
    seatName: seat,
  });
}

function registerHomedTool(ctx, { jobId, goal, seat = 'entry' }) {
  return ctx.store.registerJob({
    jobId,
    actionType: 'fire-tool',
    function: 'fire-tool',
    argsSchema: JSON.stringify({ required: { tool: 'string' }, optional: { workdir: 'string' } }),
    goalName: goal,
    seatName: seat,
  });
}

function enqueueDue(ctx, jobId, args) {
  return ctx.store.enqueue({
    jobId,
    args: JSON.stringify(args),
    sessionMode: 'headless',
    triggerKind: 'scheduled',
    runAt: new Date(Date.now() - 60000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
    enqueuedBy: 'probe',
  });
}

function queuedActionFor(result, queueId) {
  return result.actions.find(
    (a) => a.phase === 'dispatch' && a.action === 'queued' && a.queueId === queueId,
  ) || null;
}

function firedRowsFor(ctx, queueId) {
  return ctx.store.dump().jobs_log.filter((r) => r.queue_id === queueId);
}

function queueRowStillThere(ctx, queueId) {
  return !!ctx.store.getQueueRow(queueId);
}

async function run(lines) {
  const ctx = setup();
  // The workflow the run-start job would launch: `/bin/true` so the C2/C7 firing paths cost a
  // process that exits at once. Assigned the way the composition root assigns it.
  ctx.store.config.workflows = { [WORKFLOW]: { argv: ['/bin/true'] } };
  ctx.store.config.tools = { 'a-watcher': { argv: ['/bin/true'] } };

  const wsRoot = path.join(ctx.tmp, 'ws');
  fs.mkdirSync(wsRoot, { recursive: true });
  process.env.RBTV_IGNITE_WORKSPACE_ROOT = wsRoot;

  lines.push('--- gate description (the code\'s own output) ---');
  for (const l of describeGate().split('\n')) lines.push(`  ${l}`);
  lines.push('--- scenarios ---');

  try {
    // ── C1 + C4 — one open run: queued, not started, event complete ──────────────────────────────
    makeGoal(wsRoot, {
      goal: 'goal-open',
      runsCsv: 'run-id,type,state,opened,closed\nrun-1,fresh,closed,t0,t1\nrun-2,fresh,open,t2,\n',
      runFolders: ['run-1', 'run-2'],
    });
    registerRunStart(ctx, { jobId: 'start-open', goal: 'goal-open' });
    const qOpen = enqueueDue(ctx, 'start-open', { workflow: WORKFLOW });
    const rOpen = await ctx.ticker.tick(new Date());
    const aOpen = queuedActionFor(rOpen, qOpen.queue_id);

    assert(lines, aOpen !== null, 'C1 a scheduled start against an OPEN run records action "queued"',
      JSON.stringify(aOpen && aOpen.reason));
    assert(lines, firedRowsFor(ctx, qOpen.queue_id).length === 0,
      'C1 it did NOT start — no jobs_log row exists for that queue row');
    assert(lines, queueRowStillThere(ctx, qOpen.queue_id),
      'C1 the queued row is OBSERVABLE in the queue, not dropped on the floor (it drains when the run closes)');

    const ev = aOpen.event;
    assert(lines, !!ev['scheduled-start'] && !!ev['open-run-found'] && ev.action === 'queued',
      'C4 the event carries all three declared fields', JSON.stringify(Object.keys(ev)));
    assert(lines, ev['open-run-found']['run-id'] === 'run-2' && ev['open-run-found'].state === 'open',
      'C4 open-run-found NAMES which run was found', JSON.stringify(ev['open-run-found']));
    assert(lines, ev['scheduled-start'].goal === 'goal-open' && ev['scheduled-start']['queue-id'] === qOpen.queue_id,
      'C4 scheduled-start names the gated start', JSON.stringify(ev['scheduled-start']));
    assert(lines, String(ev['open-run-found'].register).endsWith(path.join('goal-open', 'runs.csv')),
      'C3 the answer was read from <goal>/runs.csv', String(ev['open-run-found'].register));

    // ── C2 + C3 — no open run, but run FOLDERS exist: starts normally ───────────────────────────
    // A rule keyed on a folder's existence queues here. This one must start: two run folders are on
    // disk and every register row reads `closed`.
    makeGoal(wsRoot, {
      goal: 'goal-closed',
      runsCsv: 'run-id,type,state,opened,closed\nrun-1,fresh,closed,t0,t1\nrun-2,fresh,closed,t2,t3\n',
      runFolders: ['run-1', 'run-2'],
    });
    registerRunStart(ctx, { jobId: 'start-closed', goal: 'goal-closed' });
    const qClosed = enqueueDue(ctx, 'start-closed', { workflow: WORKFLOW });
    const rClosed = await ctx.ticker.tick(new Date());
    assert(lines, queuedActionFor(rClosed, qClosed.queue_id) === null,
      'C2 a scheduled start with NO open run is not queued');
    assert(lines, firedRowsFor(ctx, qClosed.queue_id).length === 1,
      'C2 it STARTED — exactly one jobs_log row was created (the control: this rule does not queue everything)');
    assert(lines, !queueRowStillThere(ctx, qClosed.queue_id),
      'C3 two run FOLDERS on disk did not make it queue — only the register\'s state column decides');

    // ── C5a — register absent ───────────────────────────────────────────────────────────────────
    makeGoal(wsRoot, { goal: 'goal-noreg', runsCsv: null, runFolders: ['run-1'] });
    registerRunStart(ctx, { jobId: 'start-noreg', goal: 'goal-noreg' });
    const qNoreg = enqueueDue(ctx, 'start-noreg', { workflow: WORKFLOW });
    const rNoreg = await ctx.ticker.tick(new Date());
    const aNoreg = queuedActionFor(rNoreg, qNoreg.queue_id);
    assert(lines, aNoreg !== null && aNoreg.reason === 'register-unreadable',
      'C5 an ABSENT register queues (fail-closed)', JSON.stringify(aNoreg && aNoreg.reason));
    assert(lines, firedRowsFor(ctx, qNoreg.queue_id).length === 0,
      'C5 an absent register does NOT silently start the run');

    // ── C5b — register present but carries no `state` column ────────────────────────────────────
    makeGoal(wsRoot, { goal: 'goal-nostate', runsCsv: 'run-id,type,opened\nrun-1,fresh,t0\n' });
    registerRunStart(ctx, { jobId: 'start-nostate', goal: 'goal-nostate' });
    const qNostate = enqueueDue(ctx, 'start-nostate', { workflow: WORKFLOW });
    const rNostate = await ctx.ticker.tick(new Date());
    const aNostate = queuedActionFor(rNostate, qNostate.queue_id);
    assert(lines, aNostate !== null && aNostate.reason === 'register-unreadable',
      'C5 a register with no state column queues', JSON.stringify(aNostate && aNostate.reason));
    assert(lines, firedRowsFor(ctx, qNostate.queue_id).length === 0,
      'C5 a register with no state column does NOT start the run');

    // ── C5c — a state value that is neither open nor closed ────────────────────────────────────
    makeGoal(wsRoot, { goal: 'goal-junkstate', runsCsv: 'run-id,type,state\nrun-1,fresh, open\n' });
    registerRunStart(ctx, { jobId: 'start-junkstate', goal: 'goal-junkstate' });
    const qJunk = enqueueDue(ctx, 'start-junkstate', { workflow: WORKFLOW });
    const rJunk = await ctx.ticker.tick(new Date());
    const aJunk = queuedActionFor(rJunk, qJunk.queue_id);
    assert(lines, aJunk !== null && aJunk.reason === 'open-run-state-unrecognized',
      'C5 a state that is neither "open" nor "closed" queues — not provably closed',
      JSON.stringify(aJunk && aJunk.reason));
    assert(lines, firedRowsFor(ctx, qJunk.queue_id).length === 0,
      'C5 an unparseable state does NOT start the run');

    // ── C6 — two open rows: refused, both named, no pick ───────────────────────────────────────
    makeGoal(wsRoot, {
      goal: 'goal-two',
      runsCsv: 'run-id,type,state\nrun-1,fresh,open\nrun-2,fresh,open\n',
    });
    registerRunStart(ctx, { jobId: 'start-two', goal: 'goal-two' });
    const qTwo = enqueueDue(ctx, 'start-two', { workflow: WORKFLOW });
    const rTwo = await ctx.ticker.tick(new Date());
    const aTwo = queuedActionFor(rTwo, qTwo.queue_id);
    assert(lines, aTwo !== null && aTwo.reason === 'open-run-ambiguous',
      'C6 two open rows queue', JSON.stringify(aTwo && aTwo.reason));
    assert(lines,
      Array.isArray(aTwo.event['open-run-found']['run-id'])
      && aTwo.event['open-run-found']['run-id'].join(',') === 'run-1,run-2'
      && aTwo.event['open-run-found'].count === 2,
      'C6 both open runs are NAMED and no pick is made',
      JSON.stringify(aTwo.event['open-run-found']));
    assert(lines, firedRowsFor(ctx, qTwo.queue_id).length === 0, 'C6 it did not start');

    // ── C7 — a homed job that is NOT a run start fires while the run is open ────────────────────
    registerHomedTool(ctx, { jobId: 'watcher-open', goal: 'goal-open' });
    const qTool = enqueueDue(ctx, 'watcher-open', { tool: 'a-watcher' });
    const rTool = await ctx.ticker.tick(new Date());
    assert(lines, queuedActionFor(rTool, qTool.queue_id) === null,
      'C7 a fire-tool job homed at the SAME goal with the SAME open run is not gated');
    assert(lines, firedRowsFor(ctx, qTool.queue_id).length === 1,
      'C7 it FIRED — the gate does not stop the watchers and self-heal jobs that must run WHILE a run is open (C4 bound)');

    // ── C8 — the gate's own failure is CONTAINED, and it fails CLOSED ───────────────────────────
    // `dispatch()` has no try around the gate, so an exception here would abandon the whole tick.
    // Driven by injecting a register reader that throws — the one input a caller can supply, and
    // the only way to reach the branch without breaking the module on purpose.
    const thrower = () => { throw new Error('register reader exploded'); };
    const gateJob = { action_type: 'start-workflow', goal_name: 'goal-open', seat_name: 'entry' };
    const gateRow = { queue_id: 999, job_id: 'start-open', trigger_kind: 'scheduled', run_at: 'now' };
    let contained;
    try {
      contained = oneLiveRunDecision({ job: gateJob, queueRow: gateRow, resolveRoot: () => wsRoot, readRegister: thrower });
    } catch (err) {
      contained = { threw: err.message };
    }
    assert(lines, contained && contained.action === 'queued' && contained.reason === 'gate-error',
      'C8 an error inside the gate QUEUES and is not rethrown — a throw would abandon the whole tick',
      JSON.stringify(contained && (contained.reason || contained.threw)));
    assert(lines, contained.event['open-run-found'].reason.includes('register reader exploded'),
      'C8 the failure is not silent — the error rides the event into the tick log',
      String(contained.event['open-run-found'].reason).slice(0, 80));

    lines.push(`CHECKS: ${passed}/${passed} passed`);
    lines.push('ONE_LIVE_RUN_OK: true');
  } finally {
    delete process.env.RBTV_IGNITE_WORKSPACE_ROOT;
    teardown(ctx);
  }
}

capture('probe-one-live-run', run);
