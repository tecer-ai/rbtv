'use strict';

// probe-one-live-run — 7.607 E1: the one-live-execution gate RE-FOUNDED ON THE DERIVED LEASE.
//
// A scheduled start that finds the same goal EXECUTING is QUEUED, not started; and — the half that
// is new and that this whole epic exists for — a goal that is NOT executing has its start ADMITTED
// no matter what any stored register row says.
//
// EIGHT CHECK GROUPS, and the ones that carry the weight are the CONTROLS.
//
//   C1  a live ROOM      -> the row is NOT fired (no jobs_log row, the queue row survives) and the
//                           tick records `action: 'queued'`.
//   ⚠⚠ C2 THE RED-FIRST DEADLOCK ARM. The goal carries a `runs.csv` row reading `state=open` AND
//                           run folders on disk — 7.608's EXACT shape, the state that refused
//                           `d1-throwaway`'s start forever — and NO room. It must START. This
//                           check is red against the register-era gate by construction: that gate
//                           read the very row this one must ignore. It is also C1's control (a
//                           scheduler that queues everything passes C1 and is not this rule).
//   C3  the read site    -> proven by C1 and C2 DISAGREEING WITH THE REGISTER IN OPPOSITE
//                           DIRECTIONS: C1's goal has `state=closed` on disk and queues; C2's has
//                           `state=open` and starts. No reading of runs.csv produces both.
//   C4  event fields     -> the declared fields present; `live-lease` names WHICH room was found;
//                           the legacy `open-run-found` key still carries it (the notifier compat
//                           seam, `one-live-run.js` header).
//   C5  lease unreadable -> QUEUED, fail-closed. Ignorance never starts a run.
//   C6  workspace root unresolvable -> QUEUED, same posture, different cause.
//   C7  not a run start  -> a `fire-tool` job homed at the SAME goal with the SAME live room FIRES.
//                           The bound: the gate must not stop the watchers and self-heal jobs that
//                           exist precisely to run WHILE a goal executes.
//   C8  the gate throws  -> QUEUED and never rethrown; the error rides the event.
//
// ⚠ IT NEVER TOUCHES A REAL ROOM. The live scenarios run against an ISOLATED tmux server
// (`TMUX_TMPDIR` pointed at a scratch dir, `TMUX`/`TMUX_PANE` unset), created and killed inside
// this probe. The DEFAULT server's session inventory is asserted byte-identical before and after —
// the owner's `d1-throwaway` acceptance room is on this box and must not be observed or disturbed.
//
// Nothing about the rule's inputs is hand-fed on the C1/C2/C7 paths: the rooms are real tmux
// sessions, read by the real lease module, and the decision is reached inside a real `ticker.tick()`.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
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

// A real goal tree: goals.csv row + a runs.csv written verbatim. The register is written on
// PURPOSE in the scenarios below — it is the thing the gate must now be blind to, and a scenario
// that omitted it could not tell blindness from absence.
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

function defaultServerSessions() {
  try {
    return execFileSync('tmux', ['list-sessions', '-F', '#{session_name}'],
      { encoding: 'utf8', timeout: 10000, env: { ...process.env, TMUX: '', TMUX_PANE: '' } })
      .split('\n').map((s) => s.trim()).filter(Boolean).sort().join(',');
  } catch { return ''; }
}

async function run(lines) {
  const ctx = setup();
  ctx.store.config.workflows = { [WORKFLOW]: { argv: ['/bin/true'] } };
  ctx.store.config.tools = { 'a-watcher': { argv: ['/bin/true'] } };

  const wsRoot = path.join(ctx.tmp, 'ws');
  fs.mkdirSync(wsRoot, { recursive: true });
  process.env.RBTV_IGNITE_WORKSPACE_ROOT = wsRoot;

  const beforeSessions = defaultServerSessions();
  const tmuxScratch = fs.mkdtempSync(path.join(os.tmpdir(), 'rbtvolr-'));
  const savedEnv = { TMUX_TMPDIR: process.env.TMUX_TMPDIR, TMUX: process.env.TMUX, TMUX_PANE: process.env.TMUX_PANE };
  process.env.TMUX_TMPDIR = tmuxScratch;
  delete process.env.TMUX;
  delete process.env.TMUX_PANE;
  const itmux = (args, { allowFail = false } = {}) => {
    try { return execFileSync('tmux', args, { encoding: 'utf8', timeout: 10000 }).trim(); } catch (e) {
      if (allowFail) return null;
      throw e;
    }
  };

  // Unique per run so nothing can collide with a real goal name, here or on the default server.
  const U = `${process.pid}${Date.now() % 100000}`;
  const GOAL_LIVE = `zz-olr-live-${U}`;
  const GOAL_DEAD = `zz-olr-dead-${U}`;

  lines.push('--- gate description (the code\'s own output) ---');
  for (const l of describeGate().split('\n')) lines.push(`  ${l}`);
  lines.push('--- scenarios ---');

  try {
    // ── C1 + C4 — the goal is EXECUTING (a real room), while its register says `closed` ─────────
    makeGoal(wsRoot, {
      goal: GOAL_LIVE,
      runsCsv: 'run-id,type,state,opened,closed\nrun-1,fresh,closed,t0,t1\n',
      runFolders: ['run-1'],
    });
    // 7.607 E2b — the room name IS the goal name (design-lock item 2); the E1 transitional
    // `<goal>-run-N` spelling is deleted from the lease predicate, so a legacy-named room would
    // no longer match and this arm would measure a goal with NO room instead of a live one.
    // The `runs.csv` fixture above STAYS: it is this arm's DECOY — the register says `closed`
    // while the room is up, which is exactly what proves no stored status is being read.
    const room = GOAL_LIVE;
    itmux(['new-session', '-d', '-s', room]);

    registerRunStart(ctx, { jobId: 'start-live', goal: GOAL_LIVE });
    const qLive = enqueueDue(ctx, 'start-live', { workflow: WORKFLOW });
    const rLive = await ctx.ticker.tick(new Date());
    const aLive = queuedActionFor(rLive, qLive.queue_id);

    assert(lines, aLive !== null && aLive.reason === 'live-lease',
      'C1 a scheduled start against a LIVE ROOM records action "queued" with the LEASE reason',
      JSON.stringify(aLive && aLive.reason));
    assert(lines, firedRowsFor(ctx, qLive.queue_id).length === 0,
      'C1 it did NOT start — no jobs_log row exists for that queue row');
    assert(lines, queueRowStillThere(ctx, qLive.queue_id),
      'C1 the queued row is OBSERVABLE in the queue, not dropped on the floor (it drains when the room goes)');
    assert(lines, aLive.reason === 'live-lease' && aLive.reason !== 'open-run',
      'C1 the refusal vocabulary is LEASE-shaped — the register words are gone, not aliased');

    const ev = aLive.event;
    assert(lines, !!ev['scheduled-start'] && !!ev['live-lease'] && ev.action === 'queued',
      'C4 the event carries all three declared fields', JSON.stringify(Object.keys(ev)));
    assert(lines, ev['live-lease']['run-id'] === room && ev['live-lease'].state === 'live-lease',
      'C4 live-lease NAMES which room was found', JSON.stringify(ev['live-lease']));
    assert(lines, ev['open-run-found'] === ev['live-lease'],
      'C4 the legacy `open-run-found` key still carries it — the disclosed compat seam that keeps '
      + 'queued-run-notify.js (out of this stage\'s write surface) rendering');
    assert(lines, ev['scheduled-start'].goal === GOAL_LIVE && ev['scheduled-start']['queue-id'] === qLive.queue_id,
      'C4 scheduled-start names the gated start', JSON.stringify(ev['scheduled-start']));
    assert(lines, !/runs\.csv/.test(String(ev['live-lease'].register)),
      'C3 the answer did NOT come from a register — the evidence field names the ROOM PREDICATE',
      String(ev['live-lease'].register));

    // ── ⚠⚠ C2 — THE 7.608 DEADLOCK ARM. `state=open` on disk, run folders on disk, NO room ──────
    makeGoal(wsRoot, {
      goal: GOAL_DEAD,
      runsCsv: 'run-id,type,state,opened,closed\nrun-1,fresh,open,t0,\n',
      runFolders: ['run-1', 'run-2'],
    });
    registerRunStart(ctx, { jobId: 'start-dead', goal: GOAL_DEAD });
    const qDead = enqueueDue(ctx, 'start-dead', { workflow: WORKFLOW });
    const rDead = await ctx.ticker.tick(new Date());
    assert(lines, queuedActionFor(rDead, qDead.queue_id) === null,
      '⚠⚠ C2 THE DEADLOCK IS GONE: a goal whose runs.csv reads `state=open` and whose run folders '
      + 'exist, but which has NO ROOM, is NOT queued. This is the exact state that refused every '
      + 'start of a fresh planning goal forever (7.608)');
    assert(lines, firedRowsFor(ctx, qDead.queue_id).length === 1,
      '⚠⚠ C2 it STARTED — exactly one jobs_log row. Also C1\'s control: a scheduler that queues '
      + 'everything passes C1 and is not this rule');
    assert(lines, !queueRowStillThere(ctx, qDead.queue_id),
      'C3 neither the `state=open` row NOR the run folders on disk made it queue — with C1\'s '
      + '`state=closed` goal queueing, the two disagree with the register in OPPOSITE directions, '
      + 'so no reading of runs.csv produces both');

    // ── C7 — a homed job that is NOT a start fires while the goal executes ─────────────────────
    registerHomedTool(ctx, { jobId: 'watcher-live', goal: GOAL_LIVE });
    const qTool = enqueueDue(ctx, 'watcher-live', { tool: 'a-watcher' });
    const rTool = await ctx.ticker.tick(new Date());
    assert(lines, queuedActionFor(rTool, qTool.queue_id) === null,
      'C7 a fire-tool job homed at the SAME goal with the SAME live room is not gated');
    assert(lines, firedRowsFor(ctx, qTool.queue_id).length === 1,
      'C7 it FIRED — the gate does not stop the watchers and self-heal jobs that must run WHILE a goal executes');

    // ── C5 — the lease is UNREADABLE: fail CLOSED ─────────────────────────────────────────────
    // Injected through the module's one injection point, because a tmux that cannot be read is not
    // a state a probe may create on a shared box.
    const gateRow = { queue_id: 999, job_id: 'start-live', trigger_kind: 'scheduled', run_at: 'now' };
    const gateJob = { action_type: 'start-workflow', goal_name: GOAL_DEAD, seat_name: 'entry' };
    const unreadable = oneLiveRunDecision({
      job: gateJob, queueRow: gateRow, resolveRoot: () => wsRoot,
      readLease: () => ({ ok: false, reason: 'tmux is unreadable (simulated)' }),
    });
    assert(lines, unreadable.action === 'queued' && unreadable.reason === 'lease-unreadable',
      'C5 an UNREADABLE lease QUEUES (fail-closed) — ignorance is not "not executing"',
      JSON.stringify(unreadable.reason));
    assert(lines, String(unreadable.event['live-lease'].reason).includes('tmux is unreadable'),
      'C5 the cause rides the event, so the tick log says WHY it could not decide');

    // ── C6 — no workspace root ────────────────────────────────────────────────────────────────
    const noRoot = oneLiveRunDecision({ job: gateJob, queueRow: gateRow, resolveRoot: () => null });
    assert(lines, noRoot.action === 'queued' && noRoot.reason === 'workspace-root-unresolvable',
      'C6 an unresolvable workspace root QUEUES — same posture, distinct cause',
      JSON.stringify(noRoot.reason));

    // ── C8 — the gate's own failure is CONTAINED, and it fails CLOSED ──────────────────────────
    // `dispatch()` has no try around the gate, so an exception here would abandon the whole tick.
    const thrower = () => { throw new Error('lease reader exploded'); };
    let contained;
    try {
      contained = oneLiveRunDecision({ job: gateJob, queueRow: gateRow, resolveRoot: () => wsRoot, readLease: thrower });
    } catch (err) {
      contained = { threw: err.message };
    }
    assert(lines, contained && contained.action === 'queued' && contained.reason === 'gate-error',
      'C8 an error inside the gate QUEUES and is not rethrown — a throw would abandon the whole tick',
      JSON.stringify(contained && (contained.reason || contained.threw)));
    assert(lines, contained.event['live-lease'].reason.includes('lease reader exploded'),
      'C8 the failure is not silent — the error rides the event into the tick log',
      String(contained.event['live-lease'].reason).slice(0, 80));

    // ── C9 — the room goes away and the SAME goal now starts ──────────────────────────────────
    // The queued row from C1 is still due. Nothing on disk changes; only the room does.
    itmux(['kill-session', '-t', room], { allowFail: true });
    const rDrain = await ctx.ticker.tick(new Date());
    assert(lines, queuedActionFor(rDrain, qLive.queue_id) === null
      && firedRowsFor(ctx, qLive.queue_id).length === 1,
      '⚠ C9 THE QUEUED ROW DRAINS BY ITSELF once the room is gone — with every file on disk '
      + 'unchanged, including the `state=closed` register. The room, and only the room, decided');

    lines.push(`CHECKS: ${passed}/${passed} passed`);
    lines.push('ONE_LIVE_RUN_OK: true');
  } finally {
    itmux(['kill-server'], { allowFail: true });
    for (const [k, v] of Object.entries(savedEnv)) {
      if (v === undefined) delete process.env[k]; else process.env[k] = v;
    }
    fs.rmSync(tmuxScratch, { recursive: true, force: true });
    delete process.env.RBTV_IGNITE_WORKSPACE_ROOT;
    teardown(ctx);
  }
  if (defaultServerSessions() !== beforeSessions) {
    throw new Error('the DEFAULT tmux server\'s session inventory changed across this probe — '
      + `before=${beforeSessions} after=${defaultServerSessions()}`);
  }
  lines.push('DEFAULT_TMUX_SERVER_UNTOUCHED: true');
}

capture('probe-one-live-run', run);
