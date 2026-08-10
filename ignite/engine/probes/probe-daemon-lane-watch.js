#!/usr/bin/env node
'use strict';

// probe-daemon-lane-watch — THE DAEMON LANE'S GOAL-PICKUP TRIGGER, end to end
// (owner ruling decisions.md#d-daemon-lane-button; discharges the follow-on
// decisions.md#d-s23-single-execution-record-now named and deliberately did not invent, and the
// migrate task "Wire the daemon lane's goal-pickup TRIGGER").
//
// THE QUESTION, in the owner's own framing: a goal starts in the DAEMON lane and finishes in the
// CONSOLE one, and the thing that decides which lane runs it is a file a CLI writes. Does the
// daemon actually pick a goal up by itself now? Does it leave the goals it was not given alone?
// Does it stay off a goal somebody is attached to right now? And does the flip mid-goal work in
// the direction the owner asked for — start in daemon, finish in console, with nothing re-run?
//
// WHAT IS SUBSTITUTED, disclosed up front (`bars.md` 10):
//   · No daemon PROCESS runs here. The daemon-side half is exercised at the ENGINE the daemon
//     boots (`createEngine`, the same call `server/index.js` makes) against a store placed at a
//     DAEMON data root — which is exactly what makes a lane the daemon's
//     (`execution-record.laneOf`) — driven by the REAL `runLaneWatch` the daemon's loop calls.
//     That the loop calls it is a separate, structural arm (L7), because a behavioural arm cannot
//     see a loop that stopped calling the function it drives (review finding F1's lesson).
//   · One COMPLETION is synthesized: seat `alpha` is really enqueued by the watch and really
//     dispatched by the daemon's tick, but a `sleep` child files no completion report, so its turn
//     is ended through the store's own `endTurnAndCloseSession` and then published to the record by
//     the REAL writer (`engine.tick`). Nothing is ever hand-written into `executions.csv`.
//   · The seats' harness is `sleep 1` under the setsid carrier (no systemd user manager in a
//     probe), the same substitution `probe-cross-lane-resume.js` makes.
//
// THREE MUTATION ARMS (L8) run the real pass against a single-string mutation of `lane-watch.js`,
// compiled in memory (no file is written into the source tree), and REQUIRE it to go red:
//   · the assignment is ignored  -> the daemon seeds a CONSOLE goal
//   · the run lock is ignored    -> the daemon seeds a goal a console runner is attached to
//   · the watch call is removed  -> the call-site arm reds (the "nothing picks a goal up" state)
// Each anchor is asserted present before it is replaced, so a mutation that silently matched
// nothing can never pass for a mutation that was survived.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const Module = require('node:module');
const { execFileSync } = require('node:child_process');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const OUT_PATH = path.join(__dirname, 'probe-daemon-lane-watch.out');

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
const laneWatch = require('../lane-watch');
const { createEngine } = require('../index');
const { openHeartStore } = require('../../server/heart/heart-store');

// ── the mutation harness ──────────────────────────────────────────────────────────────────────
// The module is recompiled IN MEMORY under its own real filename, so its relative `require`s
// resolve exactly as the original's do and nothing is written beside the source. The anchor is
// asserted present first: a mutation that matched nothing is a green arm measuring nothing.
const LANE_WATCH_PATH = path.join(IGNITE_SRC, 'engine', 'lane-watch.js');
const LANE_WATCH_SRC = fs.readFileSync(LANE_WATCH_PATH, 'utf8');
function mutantWatch(from, to) {
  if (!LANE_WATCH_SRC.includes(from)) {
    throw new Error(`mutation anchor ABSENT in lane-watch.js — the arm would measure nothing: ${from}`);
  }
  const m = new Module(LANE_WATCH_PATH, null);
  m.filename = LANE_WATCH_PATH;
  m.paths = Module._nodeModulePaths(path.dirname(LANE_WATCH_PATH));
  m._compile(LANE_WATCH_SRC.replace(from, to), LANE_WATCH_PATH);
  return m.exports.runLaneWatch;
}

// ── fixture ───────────────────────────────────────────────────────────────────────────────────
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-lane-watch-'));
const workspace = path.join(tmp, 'workspace');
const goalsRoot = path.join(workspace, '.rbtv', 'goals');
const dataRoot = path.join(tmp, 'data');                  // the DAEMON lane's state root
fs.mkdirSync(dataRoot, { recursive: true });
fs.mkdirSync(goalsRoot, { recursive: true });

const yaml = require(path.join(IGNITE_SRC, 'node_modules', 'js-yaml'));
const cfg = yaml.load(fs.readFileSync(path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml'), 'utf8'));
cfg.spawn = { ...(cfg.spawn || {}), data_root: dataRoot, carrier: 'setsid' };
cfg.default_workdir_root = path.join(tmp, 'work');
fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
cfg.profiles['probe-lane'] = {
  exec: { argv: ['sleep', '1'], prompt: 'stdin' },
  headed: { tui: { argv: ['true'] } },
  session_ref: { source: 'cwd-implicit' },
  // ABSOLUTE, and pointed at THIS fixture's goals root. A workspace-relative `.rbtv/goals` resolves
  // against the runner's cwd (the ignite source), so every seat launch would refuse
  // `E_WORKDIR_ESCAPE` and the probe would measure a spawn that never happened.
  workdir_root: goalsRoot,
  caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
  sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
};
const configPath = path.join(tmp, 'spawn-profiles.yaml');
fs.writeFileSync(configPath, yaml.dump(cfg));

const daemonStorePath = path.join(dataRoot, 'heart.db');
const isoNow = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');

// Two seats, `bravo` after `alpha` — the wave that makes "did it skip the finished one" answerable.
// NO `execution-mode` file: absent means `autonomous` (ratified default), which is the state a
// daemon-run goal is in, and it keeps the foreground carrier out of this probe entirely.
function makeGoal(name) {
  const dir = path.join(goalsRoot, name);
  for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(dir, 'seats', s), { recursive: true });
  fs.mkdirSync(path.join(dir, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'taskforce.csv'), `taskforce-id,seat,after\ntf-${name},alpha,\ntf-${name},bravo,alpha\n`);
  for (const s of ['alpha', 'bravo']) {
    fs.writeFileSync(path.join(dir, 'seats', s, 'seat.md'), `---\nseat: ${s}\n---\n\nbody\n`);
  }
  return dir;
}

const switchGoal = makeGoal('switch-goal');     // the end-to-end: daemon first, console after
const consoleGoal = makeGoal('console-goal');   // THE CONTROL: assigned to the console lane
const lockedGoal = makeGoal('locked-goal');     // assigned daemon, but a console runner is attached
const heldGoal = makeGoal('held-goal');         // assigned daemon, one seat OPEN in the other lane

const GOAL_CLI = path.join(IGNITE_SRC, 'capabilities', 'goals-tree', 'tool', 'goal_cli.py');
// The CLI is the WRITER of the marker file, and it must work with no daemon anywhere — which is
// the whole reason the trigger is a file. Run it as the operator does: a subprocess, no engine.
function laneCli(args, { expectRefusal = false } = {}) {
  try {
    const out = execFileSync('python3', [GOAL_CLI, '--root', goalsRoot, 'lane', ...args],
      { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    return { ok: true, out };
  } catch (err) {
    if (!expectRefusal) throw new Error(`rbtv-goal lane ${args.join(' ')} failed: ${err.stderr || err.message}`);
    return { ok: false, out: String(err.stdout || '') + String(err.stderr || '') };
  }
}

// A logger that keeps every line, so an arm can assert what the daemon would have REPORTED and not
// only what it did — `heldByOtherLane` is a fact an operator reads, so it is measured where they
// would read it.
function collectingLogger(sink) {
  return (m) => sink.push(m);
}

async function main() {
  say('probe-daemon-lane-watch — the daemon lane\'s goal-pickup trigger (d-daemon-lane-button)');
  say(`fixture: ${tmp}`);
  say('');

  // ── L1 · THE READER'S GRAMMAR ───────────────────────────────────────────────────────────────
  say('L1 — the lane marker\'s grammar: absent, junk and `console` are ONE answer');
  const lanePath = (dir) => path.join(dir, laneWatch.LANE_FILE);
  const grammar = path.join(goalsRoot, 'switch-goal');
  const readsAs = (text) => {
    if (text === null) { try { fs.unlinkSync(lanePath(grammar)); } catch { /* already absent */ } }
    else fs.writeFileSync(lanePath(grammar), text);
    return laneWatch.readLane(grammar);
  };
  check('L1 an ABSENT marker reads as the CONSOLE lane — the daemon adopts only what it was GIVEN',
    readsAs(null).lane === 'console');
  check('L1 …and so does a junk word, an empty file and `console` itself: one answer, three inputs',
    ['nonsense\n', '\n', 'console\n'].every((t) => readsAs(t).lane === 'console'));
  const tolerant = readsAs('  Daemon   probe-lane \n');
  check('L1 only `daemon` opens it — trimmed and case-insensitive, exactly as `execution-mode` is read',
    tolerant.lane === 'daemon' && tolerant.profile === 'probe-lane', JSON.stringify(tolerant));
  check('L1 a `daemon` marker with NO profile parses, and carries none — the pass warns rather than guessing',
    readsAs('daemon\n').lane === 'daemon' && readsAs('daemon\n').profile === null);
  fs.unlinkSync(lanePath(grammar));

  // ── L2 · THE CLI IS THE WRITER, AND IT WORKS DAEMON-DOWN ────────────────────────────────────
  say('');
  say('L2 — `rbtv goal lane` writes the marker, with no daemon in the picture');
  const refused = laneCli(['switch-goal', '--set', 'daemon'], { expectRefusal: true });
  check('L2 `--set daemon` WITHOUT `--profile` is REFUSED — a goal handed to the daemon that names no '
    + 'launch profile cannot run, and the refusal is at the door rather than a journal warning at 03:00',
    refused.ok === false && /--profile/.test(refused.out) && !fs.existsSync(lanePath(switchGoal)),
    refused.out.trim().split('\n').pop());
  laneCli(['switch-goal', '--set', 'daemon', '--profile', 'probe-lane']);
  laneCli(['locked-goal', '--set', 'daemon', '--profile', 'probe-lane']);
  laneCli(['held-goal', '--set', 'daemon', '--profile', 'probe-lane']);
  laneCli(['console-goal', '--set', 'console']);
  check('L2 the CLI\'s writes are what the DAEMON\'s reader sees — two languages, one grammar, cross-checked',
    laneWatch.readLane(switchGoal).lane === 'daemon'
      && laneWatch.readLane(switchGoal).profile === 'probe-lane'
      && laneWatch.readLane(consoleGoal).lane === 'console',
    `switch=${JSON.stringify(laneWatch.readLane(switchGoal))} console=${JSON.stringify(laneWatch.readLane(consoleGoal))}`);
  const shown = JSON.parse(laneCli(['switch-goal', '--json']).out);
  check('L2 …and the read-only form reports the same answer as the engine\'s reader (orientation parity)',
    shown.lane === 'daemon' && shown.profile === 'probe-lane' && shown.assigned === true,
    JSON.stringify(shown));

  // ── L3 · THE RUN LOCK — a live console run owns the goal ─────────────────────────────────────
  // Written with THIS process's pid and start time, so the lock is genuinely LIVE (the same two
  // fields `acquireRunLock` writes and `runnerAlive` tests). Nothing is faked about its liveness.
  const lockPath = path.join(lockedGoal, attached.RUN_LOCK);
  const selfStart = fs.readFileSync(`/proc/${process.pid}/stat`, 'utf8');
  fs.writeFileSync(lockPath, `${process.pid} ${selfStart.slice(selfStart.lastIndexOf(')') + 2).split(' ')[19]}\n`);
  check('L3 the fixture\'s run lock is genuinely LIVE by the lock\'s own liveness test',
    laneWatch.consoleRunIsLive(lockedGoal) === true);

  // ── L4 · A SEAT HELD BY THE OTHER LANE ──────────────────────────────────────────────────────
  // An OPEN row published into `held-goal`'s record by a GOAL-rooted store — i.e. the attached
  // lane's own writer, through `engine.tick`. Nothing is hand-written into `executions.csv`.
  {
    const goalStore = openHeartStore({ dbPath: path.join(heldGoal, 'heart.db'), profiles: cfg.profiles });
    goalStore.registerJob({
      jobId: 'seat-alpha',
      actionType: 'launch-agent',
      function: 'attached-lane seat alpha',
      argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { workdir: 'string' } }),
      description: 'a seat the CONSOLE lane is running right now',
      createdAt: isoNow(), updatedAt: isoNow(),
    });
    goalStore.recordExecutionStart({
      jobId: 'seat-alpha', actionType: 'launch-agent',
      args: JSON.stringify({ profile: 'probe-lane' }), enqueuedBy: 'attached-execution',
      sessionMode: 'headless', firedTick: 1, firedAt: new Date(),
      sessionId: 'ffffffff-1111-2222-3333-444444444444',
      workdir: path.join(heldGoal, 'seats', 'alpha'),
    });
    goalStore.close();
    const goalEngine = createEngine({
      dbPath: path.join(heldGoal, 'heart.db'), profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    try { await goalEngine.tick(); } finally { goalEngine.close(); }
  }
  // ⚠ The row reads `failed`, not open, and that is the ticker's crash sweep doing its job: a
  // synthesized execution has no live process, so the lane that wrote it ends it on its own next
  // pass. Either way it is a row the other lane did NOT finish, which is exactly what holds the
  // seat (`seeding.js` § `foreign` — open OR terminal-non-`done`), so the arm asserts that and not
  // an emptiness the sweep is entitled to remove.
  check('L4 the other lane\'s NOT-DONE row reached the record through its own writer',
    record.readExecutionRecord(heldGoal).rows.some((r) => r.seat === 'alpha' && r.outcome !== 'done'),
    record.readExecutionRecord(heldGoal).rows.map((r) => `${r.seat}=${r.outcome || 'open'}/${r.lane}`).join(' ') || 'empty');

  // ── L5 · THE WATCH PASS ─────────────────────────────────────────────────────────────────────
  say('');
  say('L5 — ONE watch pass over the goals tree: which goals does the daemon pick up?');
  const log1 = [];
  let pass1;
  {
    const engine = createEngine({
      dbPath: daemonStorePath, profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
      logger: collectingLogger(log1),
    });
    try {
      pass1 = laneWatch.runLaneWatch({ goalsRoot, engine, logger: collectingLogger(log1) });
      await engine.tick();          // …and the daemon's own tick DISPATCHES what the pass enqueued
    } finally { engine.close(); }
  }
  const adoptedNames = pass1.adopted.map((a) => a.goal).sort();
  check('L5 the daemon ADOPTS the goal assigned to it — the trigger that did not exist before',
    adoptedNames.includes('switch-goal'), adoptedNames.join(', ') || 'none');
  check('L5 THE CONTROL: it leaves the CONSOLE-assigned goal alone — not adopted, and skipped BY NAME',
    !adoptedNames.includes('console-goal')
      && pass1.skipped.some((s) => s.goal === 'console-goal' && s.reason === 'not-assigned-to-the-daemon'),
    JSON.stringify(pass1.skipped.filter((s) => s.goal === 'console-goal')));
  check('L5 …and NOTHING of that goal reached the daemon\'s store — no job, no queue row, no execution',
    (() => {
      const s = openHeartStore({ dbPath: daemonStorePath, profiles: cfg.profiles });
      const d = s.dump();
      s.close();
      return !JSON.stringify([d.jobs, d.queue, d.jobs_log]).includes('console-goal');
    })());
  check('L5 a goal a CONSOLE RUNNER IS ATTACHED TO is not seeded against — the lock is read, never taken',
    !adoptedNames.includes('locked-goal')
      && pass1.skipped.some((s) => s.goal === 'locked-goal' && s.reason === 'console-run-live'),
    JSON.stringify(pass1.skipped.filter((s) => s.goal === 'locked-goal')));
  const heldPickup = pass1.adopted.find((a) => a.goal === 'held-goal');
  check('L5 a seat OPEN in the other lane is HELD, not dispatched a second time',
    Boolean(heldPickup) && Object.keys(heldPickup.heldByOtherLane).includes('alpha')
      && !heldPickup.enqueued.includes('alpha'),
    heldPickup ? JSON.stringify(heldPickup.heldByOtherLane) : 'goal not adopted at all');
  check('L5 …and the daemon REPORTS it — `heldByOtherLane` rides the log line an operator reads '
    + '(the migrate trigger task\'s own requirement)',
    log1.some((m) => /lane watch: daemon-assigned goal seeded/.test(m.message || '')
      && m.goal === 'held-goal' && m.heldByOtherLane && m.heldByOtherLane.alpha),
    JSON.stringify(log1.filter((m) => m.goal === 'held-goal').map((m) => m.message)));

  // The PAIR for the lock arm: the same goal, the same pass, the lock gone. Without this, "not
  // seeded" could just as well mean "this watch seeds nothing".
  fs.unlinkSync(lockPath);
  {
    const engine = createEngine({
      dbPath: daemonStorePath, profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    let pass2;
    try { pass2 = laneWatch.runLaneWatch({ goalsRoot, engine }); } finally { engine.close(); }
    check('L5 PAIR: with the console runner gone, the SAME goal is adopted on the next pass — so '
      + '"not seeded" above was the lock, not an inert watch',
      pass2.adopted.map((a) => a.goal).includes('locked-goal'),
      pass2.adopted.map((a) => a.goal).join(', ') || 'none');
  }

  // ── L6 · THE SWITCH, END TO END: start in the daemon, finish in the console ─────────────────
  say('');
  say('L6 — the owner\'s own story: a goal STARTS in the daemon lane and FINISHES in the console one');
  const alphaJobId = 'seat-switch-goal-alpha';
  {
    const s = openHeartStore({ dbPath: daemonStorePath, profiles: cfg.profiles });
    const rows = s.dump().jobs_log.filter((r) => r.job_id === alphaJobId);
    check('L6 the daemon REALLY dispatched alpha — enqueued by the watch, fired by the daemon\'s tick',
      rows.length === 1, rows.map((r) => `${r.job_id}=${r.status}`).join(' ') || 'no execution row');
    // The synthesized half, disclosed: a `sleep` child files no completion report, so the turn is
    // ended through the store's own door — the execution itself is the daemon's, not the probe's.
    if (rows.length === 1) {
      s.endTurnAndCloseSession(rows[0].exec_id, { turnStatus: 'done', sessionStatus: 'closed', endedAt: new Date() });
    }
    s.close();
  }
  {
    const engine = createEngine({
      dbPath: daemonStorePath, profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    try { await engine.tick(); } finally { engine.close(); }
  }
  check('L6 the DAEMON\'s own tick published that outcome into the goal folder\'s execution record',
    record.readExecutionRecord(switchGoal).rows.some((r) => r.seat === 'alpha' && r.lane === 'daemon' && r.outcome === 'done'),
    record.readExecutionRecord(switchGoal).rows.map((r) => `${r.seat}=${r.outcome || 'open'}/${r.lane}`).join(' ') || 'empty');

  // ⚑ THE FLIP — one CLI call, mid-goal. This is the act the ruling calls the button.
  laneCli(['switch-goal', '--set', 'console']);
  check('L6 the owner FLIPS the goal to the console lane mid-goal — one CLI call, daemon untouched',
    laneWatch.readLane(switchGoal).lane === 'console');
  {
    const engine = createEngine({
      dbPath: daemonStorePath, profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    let pass3;
    try { pass3 = laneWatch.runLaneWatch({ goalsRoot, engine }); } finally { engine.close(); }
    check('L6 …and the daemon LETS GO of it on the very next pass — flipped, therefore skipped',
      !pass3.adopted.map((a) => a.goal).includes('switch-goal')
        && pass3.skipped.some((s) => s.goal === 'switch-goal' && s.reason === 'not-assigned-to-the-daemon'),
      JSON.stringify(pass3.skipped.filter((s) => s.goal === 'switch-goal')));
  }

  await attached.executeAttached({
    goalFolder: switchGoal,
    profile: 'probe-lane',
    spawnConfigPath: configPath,
    tickIntervalMs: 200,
    maxTicks: 2,
  });
  {
    const s = openHeartStore({ dbPath: path.join(switchGoal, 'heart.db') });
    const rows = s.dump().jobs_log;
    s.close();
    check('L6 `rbtv run` PICKS THE GOAL UP and re-runs NOTHING the daemon finished — alpha is never fired here',
      !rows.some((r) => r.job_id === attached.jobIdFor('alpha')),
      rows.map((r) => `${r.job_id}=${r.status}`).join(' ') || 'empty');
    check('L6 …and it runs the NEXT seat: bravo, whose `after` the daemon\'s alpha satisfied ACROSS THE LANES',
      rows.some((r) => r.job_id === attached.jobIdFor('bravo')),
      rows.map((r) => `${r.job_id}=${r.status}`).join(' ') || 'empty');
  }
  finding('L6 THE REVERSE DIRECTION\'S HONEST BOUND (console -> daemon): it is the SAME two mechanisms '
    + 'measured in the same file rather than a second path — the record makes the daemon skip what the '
    + 'console finished (`probe-cross-lane-resume.js` D1, attached-then-daemon, still green), and this '
    + 'probe\'s L5 shows the watch adopting a goal on the pass after its marker says `daemon`. What no '
    + 'arm here covers: flipping a goal to `daemon` while a console run is STILL ATTACHED. The lock '
    + 'holds the daemon off for as long as that runner lives (L5), so the pickup is DEFERRED to the '
    + 'pass after the console run exits, never concurrent — which is the intended behaviour, not a race.');

  // ── L7 · THE CALL SITE — the daemon\'s loop is what fires this ───────────────────────────────
  say('');
  say('L7 — the loop calls it: a behavioural arm cannot see a daemon that stopped calling the pass');
  // ⚠ COMMENT LINES ARE STRIPPED FIRST, exactly as the sibling `engine.tick` arm strips them: the
  // call site's own explanatory comment NAMES the function, so a pattern matched against prose
  // would report the call present in a file that had stopped making it.
  const daemonCodeRaw = fs.readFileSync(path.join(IGNITE_SRC, 'server', 'index.js'), 'utf8');
  const stripComments = (src) => src.split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  const daemonCode = stripComments(daemonCodeRaw);
  const callsWatch = (src) => /laneWatchPass\(\)/.test(src) && /runLaneWatch\(\{/.test(src);
  check('L7 `server/index.js` RUNS THE WATCH PASS — at boot and on every interval tick',
    callsWatch(daemonCode) && (daemonCode.match(/laneWatchPass\(\);/g) || []).length >= 2,
    `laneWatchPass() call sites: ${(daemonCode.match(/laneWatchPass\(\);/g) || []).length}`);
  check('L7 …and it runs BEFORE the tick, so a seat the pass enqueues is dispatched by that same tick',
    daemonCode.indexOf('laneWatchPass();') < daemonCode.indexOf('const tickResult = await engine.tick();'),
    `watch@${daemonCode.indexOf('laneWatchPass();')} tick@${daemonCode.indexOf('const tickResult = await engine.tick();')}`);

  // ── L8 · MUTATIONS — each guard is proven to be the thing doing the work ─────────────────────
  say('');
  say('L8 — mutations: every green arm above is re-run against a broken build and required to RED');

  // M1 · THE ASSIGNMENT IS IGNORED. The reader answers `daemon` for everything, so the pass should
  // seed the CONSOLE-assigned goal — the exact harm the fail-closed default exists to prevent.
  {
    const mutant = mutantWatch(
      "    return { lane: CONSOLE, profile: null, present: true };",
      "    return { lane: DAEMON, profile: 'probe-lane', present: true };");
    const mutRoot = path.join(tmp, 'm1');
    fs.cpSync(goalsRoot, mutRoot, { recursive: true });
    const engine = createEngine({
      dbPath: path.join(tmp, 'm1.db'), profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    let pass;
    try { pass = mutant({ goalsRoot: mutRoot, engine }); } finally { engine.close(); }
    check('L8 M1 assignment IGNORED -> the daemon seeds a CONSOLE goal (the L5 control goes RED)',
      pass.adopted.map((a) => a.goal).includes('console-goal'),
      `mutant adopted: ${pass.adopted.map((a) => a.goal).join(', ') || 'none'}`);
  }

  // M2 · THE RUN LOCK IS IGNORED. A live console runner no longer holds the daemon off, so the
  // collision arm goes red.
  {
    const mutant = mutantWatch(
      '  return runnerAlive(Number(pidRaw), startRaw);',
      '  return false;');
    const mutRoot = path.join(tmp, 'm2');
    fs.cpSync(goalsRoot, mutRoot, { recursive: true });
    const relocked = path.join(mutRoot, 'locked-goal', attached.RUN_LOCK);
    fs.writeFileSync(relocked, `${process.pid} ${selfStart.slice(selfStart.lastIndexOf(')') + 2).split(' ')[19]}\n`);
    const engine = createEngine({
      dbPath: path.join(tmp, 'm2.db'), profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    let pass;
    try { pass = mutant({ goalsRoot: mutRoot, engine }); } finally { engine.close(); }
    check('L8 M2 run lock IGNORED -> the daemon seeds a goal a LIVE console runner is attached to (L5 RED)',
      pass.adopted.map((a) => a.goal).includes('locked-goal'),
      `mutant adopted: ${pass.adopted.map((a) => a.goal).join(', ') || 'none'}`);
  }

  // M3 · THE WATCH IS NEVER CALLED — the state this whole build ends, mutated back into place. The
  // arm under test is L7's, so the mutation is applied to the daemon's SOURCE TEXT and L7's own
  // predicate is re-run against it.
  {
    const disabled = stripComments(daemonCodeRaw.split('\n').filter((l) => !/^\s*laneWatchPass\(\);/.test(l)).join('\n'));
    check('L8 M3 the watch call REMOVED from the daemon loop -> the call-site arm goes RED (the '
      + '"daemon adopts nothing by itself" state this build closed)',
      !callsWatch(disabled) || (disabled.match(/laneWatchPass\(\);/g) || []).length < 2,
      `remaining call sites: ${(disabled.match(/laneWatchPass\(\);/g) || []).length}`);
  }

  fs.rmSync(tmp, { recursive: true, force: true });
}

main().then(() => {
  const exitCode = failures.length ? 1 : 0;
  say('');
  say(exitCode
    ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
    : 'RESULT: PASS — the daemon lane HAS a goal-pickup trigger: a per-goal marker file a CLI writes, '
      + 'watched once a cadence, seeding through `engine.seedGoal` and nothing else. It adopts only '
      + 'goals explicitly assigned to it, stays off a goal a console runner is attached to, holds a '
      + 'seat the other lane has open, and the owner\'s start-in-daemon-finish-in-console flip works '
      + 'end to end with nothing re-run. Three mutations red.');
  say(`FINDINGS: ${findings.length} (a PASS means "measured" — read the findings for the open bounds)`);
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
