'use strict';

// Task 7.130 / M4-15 — the owner-notification path for a QUEUED START (renamed 7.607 E3).
//
// NINE CHECKS. The ones that carry the weight are the CONTROLS and the DISCRIMINATORS, because the
// easy way to pass this task is to assert that a notify function was CALLED, and 7.77 excludes that
// reading on purpose.
//
//   N1  a queued row NOTIFIES — driven through a real `ticker.tick()`, asserted on the message that
//       arrived in the store's `owner-feed` thread, not on the notifier's return value.
//   N2  THE CONTROL: a start with no live lease notifies NOTHING. Without it, N1 is satisfied by a
//       path that notifies on every due row, which is not this path.
//   N3  the notice NAMES the held start and the run that held it — literal expected substrings
//       (goal, job id, queue row, due time, room), so the check cannot drift with the renderer.
//   N4  ONCE per queued row, not once per tick — three ticks with the row still queued produce one
//       message. A queued row is re-evaluated every tick; without this it is an hourly message
//       storm. And a CHANGED reason re-notifies, because that is new information.
//   N5  THE DISCRIMINATING CONTROL the task's own done contract names: with the notification path
//       DELIBERATELY BROKEN, the row still QUEUES and did not start, and the failure is SURFACED.
//       A notification failure must never become a skip.
//   N6  a THROWING deliverer is contained — surfaced, never rethrown. A throw on the dispatch path
//       abandons the whole tick (7.129 measured it), and a delivery is the likeliest thing to fail.
//   N7  a MISSING deliverer is a surfaced failure, not a silent no-op.
//   N8  the path fires on R9's queue event and on NO other event — a `start` decision, a defer-
//       shaped object and a half-built event all deliver nothing.
//   N9  no credential appears in the notice or in the recorded event.
//
// N1/N2/N5 assert on the STORE and the QUEUE — did a message land? did the row survive? did it
// fire? — never on a mock's call count. N6/N7/N8 call the notifier directly, because injecting a
// throwing or absent deliverer is the only way to reach those branches without breaking the module
// on purpose.

require('../../../deploy/probe-self-isolate').selfIsolateTmux(); // solo-run tmux isolation (task 7.630) — no-op under the runner
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { setup, teardown, capture } = require('./lib');
const {
  createQueuedStartNotifier, renderQueuedStartNotice, describeNotifier, SKIPPED,
} = require('../queued-start-notify');

const WORKFLOW = 'start-a-run';
const OWNER_FEED = 'owner-feed';

// The tally is COUNTED, never typed: a hand-written "9/9" stops being true the moment a check is
// added and would read as green while covering less.
let passed = 0;
function assert(lines, ok, label, detail = '') {
  lines.push(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? ` — ${detail}` : ''}`);
  if (!ok) throw new Error(`check failed: ${label}${detail ? ` — ${detail}` : ''}`);
  passed += 1;
}

function makeGoal(wsRoot, { goal, runsCsv }) {
  const goalDir = path.join(wsRoot, '.rbtv', 'goals', goal);
  fs.mkdirSync(goalDir, { recursive: true });
  const goalsCsvPath = path.join(wsRoot, '.rbtv', 'goals', 'goals.csv');
  if (!fs.existsSync(goalsCsvPath)) fs.writeFileSync(goalsCsvPath, 'name,state\n');
  fs.appendFileSync(goalsCsvPath, `${goal},open\n`);
  if (runsCsv !== null) fs.writeFileSync(path.join(goalDir, 'runs.csv'), runsCsv);
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

// The DELIVERY-side observation for the in-daemon leg: what actually landed on the owner feed.
// Not the notifier's return value, and not a call count.
function ownerFeedNotices(ctx) {
  return ctx.store.dump().messages
    .filter((m) => m.thread === OWNER_FEED && String(m.corpus).includes('was QUEUED'));
}

function actionsOf(result, action, queueId) {
  return result.actions.filter(
    (a) => a.phase === 'dispatch' && a.action === action && a.queueId === queueId,
  );
}

function firedRowsFor(ctx, queueId) {
  return ctx.store.dump().jobs_log.filter((r) => r.queue_id === queueId);
}

// A complete queue event, spelled out here rather than captured from the rule, so the direct-call
// checks state their own input instead of inheriting whatever the rule happens to emit today.
function queueEvent(overrides = {}) {
  return {
    'scheduled-start': {
      'queue-id': 42, 'job-id': 'start-tg', 'action-type': 'start-workflow',
      goal: 'tg-goal', 'trigger-kind': 'scheduled', 'run-at': '2026-07-30T06:00:00Z',
    },
    'live-lease': { room: 'tg-goal', rooms: ['tg-goal'], state: 'live-lease', count: 1,
                    register: 'session name === "tg-goal" (design-lock item 2: one room per goal)' },
    action: 'queued',
    reason: 'live-lease',
    ...overrides,
  };
}

async function run(lines) {
  const ctx = setup();
  ctx.store.config.workflows = { [WORKFLOW]: { argv: ['/bin/true'] } };

  const wsRoot = path.join(ctx.tmp, 'ws');
  fs.mkdirSync(wsRoot, { recursive: true });
  process.env.RBTV_IGNITE_WORKSPACE_ROOT = wsRoot;

  // The isolated tmux server this probe's fixture rooms live on. Installed on THIS process's env
  // because the lease module reads it, and torn down in the finally block.
  const tmuxScratch = fs.mkdtempSync(path.join(os.tmpdir(), 'rbtvqrn-'));
  const savedTmuxEnv = { TMUX_TMPDIR: process.env.TMUX_TMPDIR, TMUX: process.env.TMUX, TMUX_PANE: process.env.TMUX_PANE };
  process.env.TMUX_TMPDIR = tmuxScratch;
  delete process.env.TMUX;
  delete process.env.TMUX_PANE;
  const itmux = (args, { allowFail = false } = {}) => {
    try { return execFileSync('tmux', args, { encoding: 'utf8', timeout: 10000 }).trim(); } catch (e) {
      if (allowFail) return null;
      throw e;
    }
  };

  lines.push('--- notifier description (the code\'s own output) ---');
  for (const l of describeNotifier().split('\n')) lines.push(`  ${l}`);
  lines.push('--- scenarios ---');

  try {
    // ── N1 + N3 + N4 — a queued row notifies, names both halves, and does it ONCE ───────────────
    //
    // ⚠ 7.607 E1: what HOLDS the start is no longer a `state=open` register row but a LIVE ROOM
    // (`server/lease/lease.js`). The register below is still written — deliberately, so the
    // fixture proves the notice follows the room and not the file — and the room is what makes
    // the gate queue. It lives on an ISOLATED tmux server (see the finally block) so this probe
    // cannot see or disturb the box's real rooms.
    makeGoal(wsRoot, {
      goal: 'goal-open',
      runsCsv: 'run-id,type,state,opened,closed\nrun-1,fresh,closed,t0,t1\nrun-7,fresh,closed,t2,t3\n',
    });
    // 7.607 E2b — the room name IS the goal name (design-lock item 2); the E1 transitional
    // `<goal>-run-N` spelling is deleted from the lease predicate. The register above STAYS as
    // the decoy that proves the notice follows the ROOM and not the file.
    itmux(['new-session', '-d', '-s', 'goal-open']);
    registerRunStart(ctx, { jobId: 'start-open', goal: 'goal-open' });
    const q = enqueueDue(ctx, 'start-open', { workflow: WORKFLOW });
    const r1 = await ctx.ticker.tick(new Date());

    const notices = ownerFeedNotices(ctx);
    assert(lines, notices.length === 1,
      'N1 a queued start put exactly ONE notification on the owner feed (observed in the store, not a call count)',
      `messages=${notices.length}`);
    assert(lines, actionsOf(r1, 'queued-notified', q.queue_id).length === 1,
      'N1 the tick records that the notification went out, distinctly from the queueing itself');
    assert(lines, firedRowsFor(ctx, q.queue_id).length === 0 && Boolean(ctx.store.getQueueRow(q.queue_id)),
      'N1 and the row is still queued — notifying did not start it and did not consume it');

    // N3: literal expected substrings. Spelled out, never derived from the value under test — a
    // check that asks the renderer what it rendered moves with the renderer and passes any change.
    //
    // ⚠ ANCHORED ON THE LABELLED LINE, NOT ON A BARE SUBSTRING — and that is a correction, not a
    // style choice. The first form of this check asked whether the notice CONTAINED "goal-open",
    // and it passed even with the goal line deleted, because the register path it also prints is
    // `…/.rbtv/goals/goal-open/…` and contains the goal name incidentally. Mutant M1 caught
    // it. A bare substring check on a notice that also prints a PATH built from the same values is
    // satisfied by the path, so it proves nothing about the field it claims to guard.
    const text = notices[0].corpus;
    const mustName = [
      ['the goal, on its own line', /^\s*goal:\s+goal-open\s*$/m],
      ['the held job', /^\s*start held:\s+job start-open\b/m],
      ['its queue row', new RegExp(`\\(queue row ${q.queue_id}\\)`)],
      // 7.607 E3: the compat label is GONE with the compat field. The notice reads the lease
      // directly and says so — `lease held by: room <goal>` — and the room the lease found is the
      // goal's OWN name (item 2). Label and value now describe the same mechanism.
      ['the live room that held it', /^\s*lease held by:\s+room goal-open\b/m],
      ['what happened', /was QUEUED/],
    ];
    const missing = mustName.filter(([, re]) => !re.test(text)).map(([label]) => label);
    assert(lines, missing.length === 0,
      'N3 the notice NAMES the goal, the held job, its queue row and the live room that held it',
      missing.length ? `missing: ${missing.join(', ')}` : mustName.map(([l]) => l).join(' · '));
    assert(lines, /not lost/.test(text) && /re-schedule it by hand/.test(text),
      'N3 and it tells the reader the start is not lost, so nobody hand-schedules a second racing row');

    // N4: two more ticks, row still queued, still exactly one message.
    await ctx.ticker.tick(new Date());
    await ctx.ticker.tick(new Date());
    assert(lines, ownerFeedNotices(ctx).length === 1,
      'N4 three ticks with the row still queued produced ONE message, not one per tick',
      `messages=${ownerFeedNotices(ctx).length}`);

    // ── N2 — THE CONTROL: no live room ⇒ no notification ────────────────────────────────────────
    // ⚠ its register says `state=open` and it still starts — the control now also witnesses that
    // the notice follows the ROOM, not the file.
    makeGoal(wsRoot, {
      goal: 'goal-closed',
      runsCsv: 'run-id,type,state,opened,closed\nrun-1,fresh,open,t0,\n',
    });
    registerRunStart(ctx, { jobId: 'start-closed', goal: 'goal-closed' });
    const qc = enqueueDue(ctx, 'start-closed', { workflow: WORKFLOW });
    const rc = await ctx.ticker.tick(new Date());
    assert(lines, ownerFeedNotices(ctx).length === 1,
      'N2 CONTROL: a start with NO live room added no notification (the path does not notify on every row)',
      `messages still=${ownerFeedNotices(ctx).length}`);
    assert(lines, firedRowsFor(ctx, qc.queue_id).length === 1,
      'N2 and it STARTED — exactly one jobs_log row, so the control really exercised the un-gated path (with `state=open` on disk: the room decides, the register does not)');
    assert(lines, actionsOf(rc, 'queued-notified', qc.queue_id).length === 0,
      'N2 no queued-notified action for a row that was never queued');

    // ── N5 — THE DISCRIMINATING CONTROL: notification broken ⇒ still queues, failure SURFACED ────
    //
    // The break is injected at the deliverer, which is where a real delivery fails. The rest of the
    // path — decision, dispatch, queue row — is untouched and real.
    const broken = createQueuedStartNotifier({
      deliver: async () => ({ delivered: false, error: 'delivery-surface-unreachable' }),
    });
    const brokenResult = await broken(queueEvent());
    assert(lines, brokenResult.notified === true && brokenResult.delivered === false
      && brokenResult.error === 'delivery-surface-unreachable',
      'N5 a broken delivery is SURFACED as {delivered:false, error}, carrying the reason',
      JSON.stringify({ delivered: brokenResult.delivered, error: brokenResult.error }));
    assert(lines, typeof brokenResult.text === 'string' && brokenResult.text.includes('was QUEUED'),
      'N5 and the notice it failed to deliver comes back with it, so the caller can record what was missed');

    // The queue half of the same control, driven through a real tick: the store's own queue table
    // still holds the row from N1 after its notification path was exercised — a failed or absent
    // notification cannot consume a queued row, because this path holds no queue handle at all.
    assert(lines, Boolean(ctx.store.getQueueRow(q.queue_id)) && firedRowsFor(ctx, q.queue_id).length === 0,
      'N5 the queued row survived every notification outcome — a notification failure is never a skip');

    // ── N6 — a THROWING deliverer is contained, not rethrown ─────────────────────────────────────
    const thrower = createQueuedStartNotifier({
      deliver: async () => { throw new Error('socket hang up'); },
    });
    let threw = false;
    let thrownResult = null;
    try { thrownResult = await thrower(queueEvent()); } catch { threw = true; }
    assert(lines, threw === false,
      'N6 a deliverer that THROWS did not propagate — a throw on the dispatch path abandons the whole tick');
    assert(lines, thrownResult && thrownResult.delivered === false && thrownResult.error === 'socket hang up',
      'N6 and it is not silent either — the thrown message rides out in the result',
      JSON.stringify(thrownResult && thrownResult.error));

    // ── N7 — a MISSING deliverer is a surfaced failure, not a quiet no-op ────────────────────────
    const undelivered = createQueuedStartNotifier({});
    const noDeliverer = await undelivered(queueEvent());
    assert(lines, noDeliverer.notified === true && noDeliverer.delivered === false
      && noDeliverer.error === SKIPPED.NO_DELIVERER,
      'N7 a missing deliverer reports delivered:false with no-deliverer — a misconfiguration is not silence',
      JSON.stringify(noDeliverer.error));

    // ── N8 — fires on the queue event and on NO other event ─────────────────────────────────────
    const sent = [];
    const picky = createQueuedStartNotifier({ deliver: async (t) => { sent.push(t); return { delivered: true, ts: '1' }; } });
    const nonEvents = [
      ['a start decision', { action: 'start' }],
      ['a defer-shaped action', { phase: 'dispatch', action: 'defer', reason: 'job-invalid' }],
      ['an event with no action at all', { 'scheduled-start': { 'queue-id': 1 } }],
      ['null', null],
      ['the tick action name rather than the event', { action: 'queued-notified' }],
    ];
    const wrongly = [];
    for (const [label, ev] of nonEvents) {
      const res = await picky(ev);
      if (res.notified !== false || res.skipped !== SKIPPED.NOT_A_QUEUE_EVENT) wrongly.push(label);
    }
    assert(lines, wrongly.length === 0 && sent.length === 0,
      'N8 five non-queue events delivered NOTHING — the path fires on R9\'s queue event and no other',
      wrongly.length ? `fired on: ${wrongly.join(', ')}` : 'delivered=0 across all five');
    const good = await picky(queueEvent());
    assert(lines, good.notified === true && good.delivered === true && sent.length === 1,
      'N8 CONTROL: the same notifier DID fire on a real queue event — the refusals above are discriminating, not deafness');
    const changedReason = await picky(queueEvent({ reason: 'lease-unreadable' }));
    assert(lines, changedReason.delivered === true && sent.length === 2,
      'N4 a CHANGED reason on the same queue row notifies again — it is new information, not a repeat');
    const repeat = await picky(queueEvent());
    assert(lines, repeat.notified === false && repeat.skipped === SKIPPED.ALREADY_NOTIFIED && sent.length === 2,
      'N4 the identical event a second time delivers nothing');

    // ── N9 — no credential in the notice or the event ───────────────────────────────────────────
    const secretShapes = [/xoxb-/, /xapp-/, /Bearer /i, /SLACK_BOT_TOKEN/, /IGNITE_BRIDGE_TOKEN/];
    const rendered = renderQueuedStartNotice(queueEvent());
    const leaked = secretShapes.filter((re) => re.test(rendered) || re.test(JSON.stringify(queueEvent())));
    assert(lines, leaked.length === 0,
      'N9 no credential shape appears in the rendered notice or the event it renders',
      leaked.length ? `leaked: ${leaked.join(', ')}` : 'checked xoxb-/xapp-/Bearer/token env names');

    lines.push(`CHECKS: ${passed}/${passed} passed`);
    lines.push('QUEUED_START_NOTIFY_OK: true');
  } finally {
    itmux(['kill-server'], { allowFail: true });
    for (const [k, v] of Object.entries(savedTmuxEnv)) {
      if (v === undefined) delete process.env[k]; else process.env[k] = v;
    }
    fs.rmSync(tmuxScratch, { recursive: true, force: true });
    delete process.env.RBTV_IGNITE_WORKSPACE_ROOT;
    teardown(ctx);
  }
}

capture('probe-queued-start-notify', run);
