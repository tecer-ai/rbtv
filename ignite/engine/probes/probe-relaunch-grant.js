#!/usr/bin/env node
'use strict';

// probe-relaunch-grant — CAN A SEAT THAT FAILED ON THE DAEMON LANE EVER BE RETRIED?
//
// THE MEASURED DEFECT, live on `.rbtv/goals/forge-reference-seat-id-naming`, seat `forg-intake`:
// `execution-lane` = `daemon claude-fable`, `executions.csv` carries one row `outcome=failed`, and
// `coordinate ready-seats` says READY (root seat, no predecessors — the DAG gate was green all
// along). The seat still never ran again. The eligibility engine ALREADY honoured a relaunch grant
// — `recordView` drops a granted seat from `foreign`/`notFinished`/`blocked`, `executionsByJob`
// hides this store's memory of the failed attempt — but the grant's only SOURCE was an in-memory
// `Set` built from `rbtv-execution --relaunch` argv, and `lane-watch.js` calls
// `seedGoal({goalFolder, goal, profile})` with no relaunch key, ever. The daemon lane had no way to
// receive one.
//
// ⚠ THE HOLD IS **NOT** THE `foreign` ARM, and this fixture is built on the shape that was actually
// measured rather than the one that reads plausible. The daemon store DOES carry that session id
// with status `failed`, so `recordView`'s `ours` set contains it and the foreign classification is
// SKIPPED. What holds the seat is `seatHasRun(byJob.get('seat-<goal>-<seat>'))` — `failed` is in
// `ALL_TURN_STATUSES` — so `seatState` answers `live`, and `live` is not `ready`. The grant
// therefore releases the seat through the `executionsByJob` arm, and every leg below reproduces
// THAT: a `failed` jobs_log row in the pass's own store PLUS the matching `executions.csv` row.
//
// WHAT IS SUBSTITUTED, disclosed up front:
//   · no daemon PROCESS — the daemon-lane legs call `engine.seedGoal({goalFolder, goal, profile})`,
//     which is byte-for-byte the call `lane-watch.js#runLaneWatch` makes, against a store placed at
//     a daemon data root (which is what makes a lane the daemon's, `execution-record.laneOf`).
//   · the harness — the profile's `exec.argv` is `sleep`, as in probe-cross-lane-resume.
//   · leg 6's unlaunchable pass breaks `PATH` around ONE call so the boot-prompt subprocess fails
//     synchronously (ENOENT). Every descriptor-shaped break was tried first and every one of them
//     turns the seat UNBUILT at `ready-seats` too, so the seat would never reach the boot-prompt
//     gate at all and the arm would pass for the wrong reason.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const OUT_PATH = path.join(__dirname, 'probe-relaunch-grant.out');

const start = Date.now();
const lines = [];
const failures = [];
const say = (s) => lines.push(s);
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}
const findings = [];
function finding(s) { findings.push(s); lines.push(`FINDING  ${s}`); }

const attached = require('../attached-execution');
const record = require('../execution-record');
const seeding = require('../seeding');
const grantsApi = require('../relaunch-grants');
const { createEngine } = require('../index');
const { openHeartStore } = require('../../server/heart/heart-store');

// ── fixture ───────────────────────────────────────────────────────────────────────────────────
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-relaunch-grant-'));
const workspace = path.join(tmp, 'workspace');
const dataRoot = path.join(tmp, 'data');            // the DAEMON lane's state root
fs.mkdirSync(dataRoot, { recursive: true });

const yaml = require(path.join(IGNITE_SRC, 'node_modules', 'js-yaml'));
const cfg = yaml.load(fs.readFileSync(path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml'), 'utf8'));
cfg.spawn = { ...(cfg.spawn || {}), data_root: dataRoot, carrier: 'setsid' };
cfg.default_workdir_root = path.join(tmp, 'work');
fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
cfg.profiles['probe-relaunch'] = {
  exec: { argv: ['sleep', '1'], prompt: 'stdin' },
  headed: { tui: { argv: ['true'] } },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
  sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
};
const configPath = path.join(tmp, 'spawn-profiles.yaml');
fs.writeFileSync(configPath, yaml.dump(cfg));

const PROFILE = 'probe-relaunch';
const SEAT = 'alpha';
const daemonStorePath = path.join(dataRoot, 'heart.db');
const isoNow = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
let sid = 0;
const nextSession = () => `00000000-0000-4000-8000-${String(++sid).padStart(12, '0')}`;

function makeGoal(name) {
  const goalFolder = path.join(workspace, '.rbtv', 'goals', name);
  fs.mkdirSync(path.join(goalFolder, 'seats', SEAT), { recursive: true });
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'), `taskforce-id,seat,after\ntf-g,${SEAT},\n`);
  fs.writeFileSync(path.join(goalFolder, 'seats', SEAT, 'seat.md'), `---\nseat: ${SEAT}\n---\n\nbody\n`);
  return goalFolder;
}

// THE ACCEPTANCE CASE'S SHAPE, in both halves — the store row AND the record row, joined by one
// session id. The join is what makes `recordView` call the row OURS (so `foreign` is skipped) and
// the store row is what makes `seatHasRun` answer `live`.
function synthTerminalAttempt(store, goalFolder, { jobId, outcome, storeStatus }) {
  const sessionId = nextSession();
  store.registerJob({
    jobId,
    actionType: 'launch-agent',
    function: `attached-execution seat ${SEAT}`,
    argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { workdir: 'string', prompt: 'string' } }),
    description: `seat ${SEAT}`,
    createdAt: isoNow(),
    updatedAt: isoNow(),
  });
  const exec = store.recordExecutionStart({
    jobId,
    actionType: 'launch-agent',
    args: JSON.stringify({ profile: PROFILE }),
    enqueuedBy: 'daemon',
    sessionMode: 'headless',
    firedTick: 1,
    firedAt: new Date(),
    sessionId,
    workdir: path.join(goalFolder, 'seats', SEAT),
  });
  store.endTurnAndCloseSession(exec.exec_id, {
    turnStatus: storeStatus, sessionStatus: storeStatus === 'done' ? 'closed' : 'crashed', endedAt: new Date(),
  });
  record.openExecution({ goalFolder, seat: SEAT, sessionId, lane: 'daemon', startedAt: isoNow() });
  record.closeExecution({ goalFolder, sessionId, outcome, endedAt: isoNow() });
  return sessionId;
}

// ONE daemon-lane seeding pass, through the exact call `lane-watch.js` makes — no relaunch key.
function daemonPass(goalFolder, goal) {
  const logs = [];
  // ⚠ THE LOGGER GOES ON THE ENGINE, NOT ON THE CALL. `engine.seedGoal` takes only
  // `{goalFolder, goal, profile, isHeld}` and passes ITS OWN logger down — a logger handed to the
  // call is silently dropped, and an arm reading that empty array would be measuring nothing.
  const engine = createEngine({
    dbPath: daemonStorePath, profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    logger: (m) => logs.push(m),
  });
  let pickup;
  try {
    pickup = engine.seedGoal({ goalFolder, goal, profile: PROFILE });
  } finally {
    engine.close();
  }
  return { pickup, logs };
}

function withDaemonStore(fn) {
  const store = openHeartStore({ dbPath: daemonStorePath, profiles: cfg.profiles });
  try { return fn(store); } finally { store.close(); }
}

const jobRows = (store, jobId) => store.dump().jobs_log.filter((r) => r.job_id === jobId);

async function main() {
  say('probe-relaunch-grant — the relaunch grant reaches BOTH lanes from ONE home');
  say(`fixture: ${tmp}`);
  say('');

  // ── LEG 1 · CONTROL — no grant file, and the seat stays held ─────────────────────────────────
  say('LEG 1 — CONTROL: the acceptance shape with NO grant');
  const g1 = makeGoal('grant-control');
  const job1 = seeding.jobIdFor(SEAT, 'grant-control');
  withDaemonStore((s) => synthTerminalAttempt(s, g1, { jobId: job1, outcome: 'failed', storeStatus: 'failed' }));

  check('LEG 1 the fixture IS the measured shape: coord says READY and the store carries a `failed` row',
    seeding.readySeats(g1).ready.has(SEAT)
      && withDaemonStore((s) => jobRows(s, job1).map((r) => r.status).join()) === 'failed',
    `ready=${[...seeding.readySeats(g1).ready.keys()].join()} · record=${record.readExecutionRecord(g1).rows.map((r) => `${r.seat}=${r.outcome}`).join()}`);
  check('LEG 1 …and the hold is the STORE-HISTORY arm, not `foreign` — the session id IS ours',
    !withDaemonStore((s) => seeding.recordView(s, g1).foreign.has(SEAT)),
    `foreign=${withDaemonStore((s) => [...seeding.recordView(s, g1).foreign.keys()].join()) || 'none'}`);

  const c1 = daemonPass(g1, 'grant-control');
  check('LEG 1 with no grant the daemon lane does NOT enqueue the failed seat',
    c1.pickup.enqueued.length === 0, `enqueued ${JSON.stringify(c1.pickup.enqueued)} · states ${JSON.stringify(c1.pickup.states)}`);
  // The hold must be VISIBLE. This bar is satisfied by task 7.776's visibility fix, which landed in
  // `seeding.js` concurrently with this build: the skip used to be a bare `continue` with no log
  // line and nothing in the return, which is how the live goal sat still for 18 hours looking
  // healthy. If this arm ever goes red, that report is what was lost.
  const heldReported = c1.logs.some((m) => m.seat === SEAT && /NOT enqueued|held/.test(m.message || ''))
    || Boolean(c1.pickup.heldByStore && c1.pickup.heldByStore[SEAT]);
  check('LEG 1 …and the hold is REPORTED — a silent skip is the defect that hid this for 18 hours',
    heldReported, c1.logs.filter((m) => m.seat === SEAT).map((m) => m.message).join(' | ') || 'nothing logged');

  // ── LEG 2 · THE DAEMON ARM — the grant file, and the call lane-watch actually makes ──────────
  say('');
  say('LEG 2 — DAEMON ARM: write the grant, seed with NO relaunch key');
  const g2 = makeGoal('grant-daemon');
  const job2 = seeding.jobIdFor(SEAT, 'grant-daemon');
  withDaemonStore((s) => synthTerminalAttempt(s, g2, { jobId: job2, outcome: 'failed', storeStatus: 'failed' }));
  const before2 = daemonPass(g2, 'grant-daemon');
  check('LEG 2 CONTROL half: the same goal, ungranted, enqueues nothing',
    before2.pickup.enqueued.length === 0, JSON.stringify(before2.pickup.enqueued));

  grantsApi.grantRelaunch(g2, SEAT);
  check('LEG 2 the grant file is the CONTRACT SHAPE — one bare seat name per line, no header',
    fs.readFileSync(path.join(g2, grantsApi.GRANT_FILE), 'utf8') === `${SEAT}\n`,
    JSON.stringify(fs.readFileSync(path.join(g2, grantsApi.GRANT_FILE), 'utf8')));

  const granted2 = daemonPass(g2, 'grant-daemon');
  check('LEG 2 the DAEMON LANE enqueues the seat off the file alone — `seedGoal` was passed no relaunch key',
    granted2.pickup.enqueued.includes(SEAT),
    `enqueued ${JSON.stringify(granted2.pickup.enqueued)} · states ${JSON.stringify(granted2.pickup.states)}`);

  // ── LEG 3 · THE SPEND — one grant buys one attempt ───────────────────────────────────────────
  say('');
  say('LEG 3 — SPEND: the grant is consumed by the pass that used it');
  check('LEG 3 the grant file no longer names the seat',
    !grantsApi.readGrants(g2).has(SEAT),
    `on disk: ${JSON.stringify(fs.existsSync(path.join(g2, grantsApi.GRANT_FILE)) ? fs.readFileSync(path.join(g2, grantsApi.GRANT_FILE), 'utf8') : '(no file)')}`);
  // …and BEHAVIOURALLY. The queue row this pass wrote would hold the seat on its own, so it is
  // removed first: without that, a second pass declines for a reason that has nothing to do with
  // the grant and the arm would pass whether or not the grant was ever spent.
  withDaemonStore((s) => {
    for (const q of s.listQueue()) if (q.job_id === job2) s.removeQueueRow({ queueId: q.queue_id });
  });
  const second2 = daemonPass(g2, 'grant-daemon');
  check('LEG 3 …and a SECOND pass does not enqueue it again, with the queue row cleared out of the way',
    second2.pickup.enqueued.length === 0,
    `enqueued ${JSON.stringify(second2.pickup.enqueued)} · queue drained first`);

  // ── LEG 4 · THE CONSOLE ARM — same fixture, same verdict, through `executeAttached` ──────────
  say('');
  say('LEG 4 — CONSOLE ARM: the other lane answers identically, from the same file');
  const g4 = makeGoal('grant-console');
  const job4 = seeding.jobIdFor(SEAT);            // attached lane: `seat-<name>`, no goal namespace
  const consoleStorePath = path.join(g4, 'heart.db');
  {
    const store = openHeartStore({ dbPath: consoleStorePath, profiles: cfg.profiles });
    try { synthTerminalAttempt(store, g4, { jobId: job4, outcome: 'failed', storeStatus: 'failed' }); }
    finally { store.close(); }
  }
  const runConsole = async () => {
    const out = await attached.executeAttached({
      goalFolder: g4, profile: PROFILE, spawnConfigPath: configPath, tickIntervalMs: 200, maxTicks: 1,
    });
    const store = openHeartStore({ dbPath: consoleStorePath, profiles: cfg.profiles });
    try { return { out, rows: jobRows(store, job4).length }; } finally { store.close(); }
  };
  const consoleControl = await runConsole();
  check('LEG 4 CONTROL: ungranted, the console lane fires nothing new either',
    consoleControl.rows === 1, `${consoleControl.rows} execution row(s) · outcome=${consoleControl.out.outcome}`);
  grantsApi.grantRelaunch(g4, SEAT);
  const consoleGranted = await runConsole();
  check('LEG 4 the CONSOLE lane reads the SAME file and fires the seat — one predicate, both lanes',
    consoleGranted.rows === 2, `${consoleGranted.rows} execution row(s) · outcome=${consoleGranted.out.outcome}`);
  check('LEG 4 …and it spends the grant on the same terms the daemon does',
    !grantsApi.readGrants(g4).has(SEAT), JSON.stringify([...grantsApi.readGrants(g4)]));

  // ── LEG 5 · FINISHED IS NEVER OVERRIDABLE ────────────────────────────────────────────────────
  say('');
  say('LEG 5 — a grant can never re-open a seat the RECORD calls done');
  const g5 = makeGoal('grant-finished');
  const job5 = seeding.jobIdFor(SEAT, 'grant-finished');
  // The cross-lane `done` shape: the record says done and THIS store has no row at all, so the
  // record's word is the only thing protecting the seat. (A store `done` row protects it a second
  // time — measured separately by probe-cross-lane-resume — and would make this arm undiscriminating
  // by covering for the record.)
  {
    const s5 = nextSession();
    record.openExecution({ goalFolder: g5, seat: SEAT, sessionId: s5, lane: 'daemon', startedAt: isoNow() });
    record.closeExecution({ goalFolder: g5, sessionId: s5, outcome: 'done', endedAt: isoNow() });
  }
  grantsApi.grantRelaunch(g5, SEAT);
  const finishedPass = daemonPass(g5, 'grant-finished');
  check('LEG 5 a granted seat whose last record row is `done` is NOT enqueued',
    finishedPass.pickup.enqueued.length === 0 && finishedPass.pickup.skippedAsFinished.includes(SEAT),
    `enqueued ${JSON.stringify(finishedPass.pickup.enqueued)} · skippedAsFinished ${JSON.stringify(finishedPass.pickup.skippedAsFinished)}`);
  check('LEG 5 …and the grant is NOT spent — an authorization nothing consumed must still stand',
    grantsApi.readGrants(g5).has(SEAT), JSON.stringify([...grantsApi.readGrants(g5)]));
  check('LEG 5 …with no job row registered for it either — nothing was written off a grant that fired nothing',
    withDaemonStore((s) => jobRows(s, job5).length) === 0);

  // ── LEG 6 · AN UNSPENT GRANT SURVIVES AN UNLAUNCHABLE PASS ───────────────────────────────────
  say('');
  say('LEG 6 — the boot prompt cannot be composed: the seat is not enqueued AND the grant survives');
  const g6 = makeGoal('grant-unlaunchable');
  const job6 = seeding.jobIdFor(SEAT, 'grant-unlaunchable');
  withDaemonStore((s) => synthTerminalAttempt(s, g6, { jobId: job6, outcome: 'failed', storeStatus: 'failed' }));
  grantsApi.grantRelaunch(g6, SEAT);
  {
    // Coord's two answers are taken WITH the environment intact; only the boot-prompt call below
    // meets the broken PATH, which is the ordering `enqueueEligible` itself has (readiness is the
    // caller's, the boot prompt is per-launch).
    const { ready, rows: readyRows } = seeding.readySeats(g6);
    const rows = seeding.readTaskforce(g6);
    const store = openHeartStore({ dbPath: daemonStorePath, profiles: cfg.profiles });
    const view = seeding.recordView(store, g6);
    const savedPath = process.env.PATH;
    let enqueued;
    try {
      process.env.PATH = path.join(tmp, 'no-interpreter-here');   // execFileSync -> ENOENT, synchronously
      enqueued = seeding.enqueueEligible(store, rows, {
        profile: PROFILE, goalFolder: g6, goal: 'grant-unlaunchable', logger: null, view, ready, readyRows,
      });
    } finally {
      process.env.PATH = savedPath;
      store.close();
    }
    check('LEG 6 the seat is NOT enqueued when its boot prompt cannot be composed',
      enqueued.length === 0, JSON.stringify(enqueued));
    check('LEG 6 …and its one-shot grant is STILL ON DISK — it survives to the pass that can launch it',
      grantsApi.readGrants(g6).has(SEAT), JSON.stringify([...grantsApi.readGrants(g6)]));
  }
  // …and the pass that CAN launch it does, off that same surviving grant.
  const recovered = daemonPass(g6, 'grant-unlaunchable');
  check('LEG 6 …and the next healthy pass spends it',
    recovered.pickup.enqueued.includes(SEAT) && !grantsApi.readGrants(g6).has(SEAT),
    `enqueued ${JSON.stringify(recovered.pickup.enqueued)} · grants ${JSON.stringify([...grantsApi.readGrants(g6)])}`);

  // ── LEG 7 · FAIL-CLOSED — an unreadable grant file is NOT a grant ────────────────────────────
  say('');
  say('LEG 7 — an unreadable grant file yields NO grant, and never throws');
  const g7 = makeGoal('grant-unreadable');
  const job7 = seeding.jobIdFor(SEAT, 'grant-unreadable');
  withDaemonStore((s) => synthTerminalAttempt(s, g7, { jobId: job7, outcome: 'failed', storeStatus: 'failed' }));
  grantsApi.grantRelaunch(g7, SEAT);
  fs.chmodSync(path.join(g7, grantsApi.GRANT_FILE), 0o000);
  let readThrew = null;
  let readBack = null;
  try { readBack = grantsApi.readGrants(g7); } catch (err) { readThrew = err.message; }
  check('LEG 7 `readGrants` yields an EMPTY set and does not throw',
    readThrew === null && readBack && readBack.size === 0,
    readThrew ? `threw: ${readThrew}` : `size ${readBack && readBack.size}`);
  const unreadablePass = daemonPass(g7, 'grant-unreadable');
  check('LEG 7 …so the pass holds the seat exactly as it would with no file at all — an I/O error '
    + 'can never synthesize an authorization',
    unreadablePass.pickup.enqueued.length === 0, JSON.stringify(unreadablePass.pickup.enqueued));
  fs.chmodSync(path.join(g7, grantsApi.GRANT_FILE), 0o644);

  // ── LEG 8 · THE REMEDY HINT IS REACHABLE ON `blocked` (the folded-in defect) ─────────────────
  //
  // The hint was gated on `outcome === 'seat-failed'`, and a CROSS-LANE failed seat produces
  // `blocked` instead: the record holds it, so `evaluateExit` counts it STUCK rather than failed.
  // The operator read "BLOCKED — nothing can advance" with no signal that a relaunch is the fix.
  // Measured through the CLI BINARY, because the defect was in the CLI's print gating and nothing
  // below it could see the difference.
  say('');
  say('LEG 8 — the CLI names the remedy on a BLOCKED verdict too, and only for grantable seats');
  const g8 = makeGoal('grant-hint');
  {
    const s8 = nextSession();                      // another lane's failure: no store row of ours
    record.openExecution({ goalFolder: g8, seat: SEAT, sessionId: s8, lane: 'daemon', startedAt: isoNow() });
    record.closeExecution({ goalFolder: g8, sessionId: s8, outcome: 'failed', endedAt: isoNow() });
  }
  const cli = require('node:child_process').spawnSync(process.execPath,
    [path.join(IGNITE_SRC, 'capabilities', 'attached-execution', 'tool', 'rbtv-execution'),
      g8, '--profile', PROFILE, '--config', configPath, '--max-ticks', '1', '--tick-ms', '200'],
    { encoding: 'utf8' });
  const cliOut = String(cli.stdout || '');
  check('LEG 8 the run reports BLOCKED (the verdict a cross-lane failed seat produces)',
    /BLOCKED — nothing can advance/.test(cliOut), cliOut.trim().split('\n').slice(-4).join(' / '));
  check('LEG 8 …AND names the relaunch remedy, which it never did on this verdict before',
    /--relaunch alpha/.test(cliOut), cliOut.trim().split('\n').slice(-4).join(' / '));

  // TRUTHFULNESS: a seat merely WAITING on an unmet `after` is not grantable, and must not be
  // named. Two seats, the second following the first; the first is held by another lane's failure
  // and the second is simply waiting.
  const g8b = path.join(workspace, '.rbtv', 'goals', 'grant-hint-truth');
  for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(g8b, 'seats', s), { recursive: true });
  fs.mkdirSync(path.join(g8b, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(g8b, 'taskforce.csv'), 'taskforce-id,seat,after\ntf-g,alpha,\ntf-g,bravo,alpha\n');
  for (const s of ['alpha', 'bravo']) fs.writeFileSync(path.join(g8b, 'seats', s, 'seat.md'), `---\nseat: ${s}\n---\n\nbody\n`);
  {
    const sb = nextSession();
    record.openExecution({ goalFolder: g8b, seat: 'alpha', sessionId: sb, lane: 'daemon', startedAt: isoNow() });
    record.closeExecution({ goalFolder: g8b, sessionId: sb, outcome: 'failed', endedAt: isoNow() });
  }
  const truth = await attached.executeAttached({
    goalFolder: g8b, profile: PROFILE, spawnConfigPath: configPath, tickIntervalMs: 200, maxTicks: 1,
  });
  check('LEG 8 the remedy is TRUTHFUL — only the seat a grant could release is named, never the one '
    + 'merely waiting on it',
    truth.outcome === 'blocked' && truth.unfinished.includes('bravo')
      && truth.grantable.join() === 'alpha',
    `unfinished ${JSON.stringify(truth.unfinished)} · grantable ${JSON.stringify(truth.grantable)}`);

  finding('`lane-watch.js` is UNTOUCHED by this build, and that is the structural claim: the grant is '
    + 'sourced INSIDE `recordView`/`enqueueEligible`, so every caller of `seedGoal` — including ones '
    + 'not yet written — gets it. Threading a parameter would have created a second place that '
    + 'decides whether a grant applies, which is exactly how the gap being closed here was born.');

  fs.rmSync(tmp, { recursive: true, force: true });
}

main().then(() => {
  const exitCode = failures.length ? 1 : 0;
  say('');
  say(exitCode
    ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
    : 'RESULT: PASS — a failed seat on the DAEMON lane is retryable off `<goal>/relaunch-grants`, '
      + 'the CONSOLE lane answers from the same file, the grant is spent exactly once, survives a '
      + 'pass that could not launch, can never re-open a finished seat, and an unreadable file is no '
      + 'grant at all.');
  say(`FINDINGS: ${findings.length}`);
  say(`WALL_MS ${Date.now() - start}`);
  say(`EXIT ${exitCode}`);
  fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n');
  console.log(lines.join('\n'));
  process.exit(exitCode);
}).catch((err) => {
  say(`FAIL probe threw: ${err.stack || err.message}`);
  say('EXIT 1');
  fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n');
  console.log(lines.join('\n'));
  process.exit(1);
});
