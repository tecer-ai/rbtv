#!/usr/bin/env node
'use strict';

// probe-cross-lane-resume — console-run wave B, item B3 (owner asked 2026-08-10).
//
// THE QUESTION: a goal run partially in the ATTACHED lane and then picked up by the DAEMON lane —
// and the reverse. Does create-only seeding from the goal folder hold across the two per-lane
// `heart.db` stores? And what becomes of a human-interactive seat on the daemon side, where there
// is no terminal for it to reach?
//
// ⚠⚠ WHAT THIS PROBE MEASURED UNTIL 2026-08-10 WAS A NEGATIVE: cross-lane resume did not hold, in
// either direction, because create-only seeding is create-only WITHIN A STORE and the two lanes
// keep two disjoint stores (CMP-2 § Two store kinds). The owner then ruled the fix BUILT
// (`decisions.md#d-s23-single-execution-record-now`): ONE goal-folder-resident execution record —
// `<goal>/executions.csv` — that both lanes publish to and read before seeding. So the arms below
// are REPURPOSED, and the flip is the acceptance:
//
//   · D1/D2 flip from measuring the DOUBLE RUN to measuring correct CROSS-LANE RESUME, both
//     directions, behaviourally.
//   · D4 flips from measuring the v1 REFUSAL (`assertNoCrossLaneEvidence`, which declined the
//     crossover) to measuring that the crossover is RESUMED. The function it measured is DELETED
//     with this build, so those arms could not have survived unchanged.
//
// WHAT IS SUBSTITUTED, disclosed up front (`bars.md` 10):
//   · No daemon PROCESS runs here. Both daemon-side halves are exercised at the ENGINE the daemon
//     boots (`createEngine` — the same call `runtime/index.js` makes) against a store placed at a
//     DAEMON data root, which is exactly what makes a lane the daemon's (`execution-record.laneOf`).
//     What a live daemon adds on top is its unit, its gateway and its arming; none of the three
//     touches the seeding or record decisions measured here. The TRIGGER that fires the pickup on a
//     live daemon is a separate build (#d-daemon-lane-button) with its own probe beside this one —
//     what remains substituted here is the daemon PROCESS, reported at D1.
//   · Direction 2's daemon-side history is SYNTHESIZED into the daemon store and then published
//     through the REAL writer (`publishToRecord`), never hand-written into the record file: the arm
//     is only worth something if the daemon's own path is what wrote it.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const OUT_PATH = path.join(__dirname, 'probe-cross-lane-resume.out');

const start = Date.now();
const lines = [];
const failures = [];
const say = (s) => lines.push(s);
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}
// A measured fact that is not a pass/fail bar: the finding this probe exists to file.
const findings = [];
function finding(s) { findings.push(s); lines.push(`FINDING  ${s}`); }

const { awaitExit } = require('../../runtime/probes/await-exit');
const attached = require('../attached-execution');
const record = require('../../supervisor/execution-record');
const { createEngine } = require('../../runtime/engine');
const { openHeartStore } = require('../../state-store/heart/heart-store');
const { requirePythonCmd } = require('../../runtime/python-cmd');
// D9 (seed-gates, 2026-08-19): the goal-live injection — the real `deriveLease` over a fixture
// tmux reading whose one session IS the goal's room, so fixture goals seed as live ones do.
const { deriveLease } = require('../../runtime/lease/lease');
const fixtureLiveLease = ({ workspaceRoot, goal }) => deriveLease({ workspaceRoot, goal, tmuxProbe: () => ({ sessions: goal, panes: '' }) });

// Every .js/.py under the module, minus vendored code — the enumerator a structural claim must go
// through, because a hand-glob's wrong answer and right answer are the same empty result.
function sourceFiles() {
  const out = [];
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (e.name === 'node_modules' || e.name.startsWith('.')) continue;
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (/\.(js|py)$/.test(e.name)) out.push(p);
    }
  };
  walk(IGNITE_SRC);
  return out;
}
const SOURCES = sourceFiles();
const rel = (p) => path.relative(IGNITE_SRC, p);
function filesMatching(re, { includeProbes = false } = {}) {
  return SOURCES
    .filter((p) => includeProbes || !/probes?[/\\]/.test(rel(p)))
    .filter((p) => re.test(fs.readFileSync(p, 'utf8')))
    .map(rel)
    .sort();
}

// ── fixture ───────────────────────────────────────────────────────────────────────────────────
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-cross-lane-'));
const workspace = path.join(tmp, 'workspace');
const dataRoot = path.join(tmp, 'data');           // the DAEMON lane's state root
fs.mkdirSync(dataRoot, { recursive: true });

const yaml = require(path.join(IGNITE_SRC, 'node_modules', 'js-yaml'));
const cfg = yaml.load(fs.readFileSync(path.join(IGNITE_SRC, 'envelope', 'spawn-profiles.yaml'), 'utf8'));
cfg.spawn = { ...(cfg.spawn || {}), data_root: dataRoot, carrier: 'setsid' };
cfg.default_workdir_root = path.join(tmp, 'work');
fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
// 7.787: `profiles:` is `launch-specs:`, keyed by (harness, model). The `bash -c` shim keeps
// the argv agreeing with the key (`profiles.js#validateSpecKey` refuses a disagreement at
// LOAD) while running exactly what it ran before; the goal's seats declare the matching cast.
cfg['launch-specs'] = { bash: {} };
cfg['launch-specs'].bash['probe-lane'] = {
  exec: { argv: ['bash', '-c', 'exec sleep 1', '--model', 'probe-lane'], prompt: 'stdin' },
  headed: { tui: { argv: ['true'] } },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
  sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
};
const configPath = path.join(tmp, 'spawn-profiles.yaml');
fs.writeFileSync(configPath, yaml.dump(cfg));

// ⚠ THE CAGE'S MIRROR ROOT MUST EXIST BEFORE ANY SEAT LAUNCHES. `envelope/compiler.js` resolves
// `<workspace>/.rbtv/mirror` into every launch plan, and `composeCageFor` refuses an unresolved
// bind source outright (`LaunchRefused: unresolved …/.rbtv/mirror`) — so on a fixture without it
// EVERY detached launch lands `failed` with no carrier and no session id, which reads like a
// broken engine and is a missing directory. The envelope's own selftests create the same folder
// (`envelope-launch.selftest.js`); these fixtures predate that requirement.
fs.mkdirSync(path.join(workspace, '.rbtv', 'mirror'), { recursive: true });

const goalFolder = path.join(workspace, '.rbtv', 'goals', 'lane-goal');
for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(goalFolder, 'seats', s), { recursive: true });
fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
  'taskforce-id,seat,after\ntf-lane,alpha,\ntf-lane,bravo,alpha\n');
fs.writeFileSync(path.join(goalFolder, 'seats', 'alpha', 'seat.md'),
  '---\nseat: alpha\nharness: bash\nmodel: probe-lane\nhuman-interactive: yes\nfallback: block-and-queue\n---\n\nbody\n');
fs.writeFileSync(path.join(goalFolder, 'seats', 'bravo', 'seat.md'), '---\nseat: bravo\nharness: bash\nmodel: probe-lane\n---\n\nbody\n');
fs.writeFileSync(path.join(goalFolder, 'execution-mode'), 'interactive\n');

const goalStorePath = path.join(goalFolder, 'heart.db');
const daemonStorePath = path.join(dataRoot, 'heart.db');
const isoNow = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');

// ── THE SEAT'S OWN CHECK-OUT, AS A FIXTURE ACT ────────────────────────────────────────────────
//
// ⚠ WHY IT IS NEEDED HERE. Since `build/one-readiness-predicate.md` § D1 the ONE readiness
// evaluator is `coord.ready_seat_rows`, and it satisfies an `after` member on a predecessor's
// `done` CHECK-OUT and on nothing else — not a store turn, not an exit code, and not the execution
// record. The carrier stamps `exited` on purpose ("`done` is the seat reporting its own work
// finished, which no exit code can assert"), so substituting the carriage means substituting the
// occupant's check-out too, or the fixture models a seat that finished and an edge that cannot
// move. `coord.py session_close` would write exactly these three cells for a seat that declared
// itself done; `seat` is the only writer the enum admits for that value.
// The launch TRACE's header, from the SCHEMA OWNER (`coord.py SESSIONS_COLS`) and never spelled
// here. Hoisted to module scope because BOTH synthesized lanes need it since W2: a fixture that
// writes only the execution record now models a lane that ran a seat which never checked out, and
// `--status`/`recordView` correctly answer "not done" for it.
const HEADER = require('node:child_process').execFileSync(requirePythonCmd(),
  ['-c', 'import sys; sys.path.insert(0, sys.argv[1]); import coord; print(",".join(coord.SESSIONS_COLS))',
    path.join(IGNITE_SRC, 'coord')], { encoding: 'utf8' }).trim();
const HEADER_COLS = HEADER.split(',');
const cell = (m) => HEADER_COLS.map((c) => m[c] || '').join(',');

// ⚠ A SYNTHESIZED LANE MUST WRITE **BOTH** HALVES SINCE W2, and this helper is why. The execution
// record's `outcome` column is a PROCESS vocabulary now, so nothing in it can say the WORK is done;
// done-ness is the seat's own CHECK-OUT, which `coord.py ready-seats --json` reports as a
// `disposition` and `seeding.js#recordView` reads. A fixture that stopped at the record row was
// modelling a real state — a seat whose process ended and which never checked out — but not the one
// its arm claimed.
// ⚠ AND SINCE THE STATE-STORE MIGRATION IT MUST ALSO STAMP THE ENDING STORE, which is where
// done-ness now lives (spec-state-store §4.1: the check-out is a `seat_endings` write, and
// `sessions.csv` stopped being a work-state writer). The store is opened AT ITS HOME —
// `<workspace>/.rbtv/runtime/ignite/heart.db`, derived from the goal folder — because that home is
// exactly what makes this probe's subject true: both lanes read ONE ending store, so a seat the
// attached lane finished is finished to the daemon lane as well. A fixture that stamped the lane's
// own `heart.db` would be modelling the per-goal store §1.1 forbids.
const stateStore = require('../../state-store');
function stampDone(goal, seat) {
  const workspaceRoot = path.resolve(goal, '..', '..', '..');
  stateStore.bind(stateStore.openEndingStoreFor(workspaceRoot)).stampSeatDeclare({
    goal: path.basename(goal),
    seat,
    ending: 'done',
    evidence_pointer: `probe-cross-lane:${seat}`,
    replace: true,
  });
}

// …and its opposite, for the arms that model a seat the other lane could NOT finish: a terminal
// `failed` (the leader attempt already spent), which §2.6 makes un-launchable. A NON-terminal
// `failed` is deliberately not used here — that one IS relaunchable, because it is the recovery
// ladder's own state and not a hold.
function stampFailedTerminal(goal, seat) {
  const api = stateStore.bind(stateStore.openEndingStoreFor(path.resolve(goal, '..', '..', '..')));
  const gid = path.basename(goal);
  api.stampSystem({
    goal: gid,
    seat,
    ending: 'failed',
    reason_class: 'crash',
    evidence_pointer: `probe-cross-lane:${seat} observed dead`,
    replace: true,
  });
  api.setLeaderAttemptUsed({ goal: gid, seat });
}

function attestCheckout(goal, seat, sessionId) {
  fs.writeFileSync(path.join(goal, 'sessions.csv'), `${HEADER}\n${cell({
    'session-id': sessionId, seat, harness: 'claude', workdir: path.join(goal, 'seats', seat),
    started: isoNow(), ended: isoNow(), disposition: 'done', 'disposition-writer': 'seat',
  })}\n`);
  stampDone(goal, seat);
}

const { splitRow, quoteField } = require('../../runtime/seat-identity/csv');
function checkOutDone(goal, seat) {
  const csvPath = path.join(goal, 'sessions.csv');
  const lines = fs.readFileSync(csvPath, 'utf8').split('\n');
  const header = splitRow(lines[0]).map((h) => h.trim());
  const at = (n) => header.indexOf(n);
  for (let i = lines.length - 1; i >= 1; i -= 1) {       // the LAST open row: the live sitting
    if (!lines[i].length) continue;
    const cells = splitRow(lines[i]);
    while (cells.length < header.length) cells.push('');
    if ((cells[at('seat')] || '').trim() !== seat || (cells[at('ended')] || '').trim()) continue;
    cells[at('ended')] = isoNow();
    cells[at('disposition')] = 'done';
    cells[at('disposition-writer')] = 'seat';
    lines[i] = header.map((_, c) => quoteField(cells[c])).join(',');
    fs.writeFileSync(csvPath, lines.join('\n'), 'utf8');
    stampDone(goal, seat);
    return true;
  }
  return false;
}

async function main() {
  say('probe-cross-lane-resume — console-run wave B item B3');
  say(`fixture: ${tmp}`);
  say('');

  // ── D1 · ATTACHED first, then the daemon lane ──────────────────────────────────────────────
  say('D1 — a goal advanced in the ATTACHED lane, offered to the DAEMON lane');

  // ⚠ TWO TICKS, NOT ONE, and the second is structural rather than slack: coord's frontier is read
  // ONCE PER PASS, before the carriage runs, so `bravo` cannot be in the pass that carries `alpha`
  // — its predecessor's check-out did not exist when that pass asked. The re-seed is a pull; one
  // extra pass is what an advance costs (§ Why the re-seed stays the driver).
  await attached.executeAttached({
    goalFolder,
    profile: 'probe-lane',
    spawnConfigPath: configPath,
    tickIntervalMs: 200,
    maxTicks: 2,
    // alpha is held; it runs in "the terminal" — and the occupant checks out, which is the only
    // thing that releases bravo.
    spawnForeground: (argv, cwd) => {
      checkOutDone(path.resolve(cwd, '..', '..'), path.basename(cwd));
      return { status: 0 };
    },
  });
  const goalStore = openHeartStore({ dbPath: goalStorePath });
  const goalRows = goalStore.dump().jobs_log;
  goalStore.close();
  check('D1 the attached lane really advanced the goal — alpha is done in the GOAL\'s store',
    goalRows.some((r) => r.job_id === attached.jobIdFor('alpha') && r.status === 'done'),
    goalRows.map((r) => `${r.job_id}=${r.status}`).join(' '));

  // ⚠ THE GOAL FOLDER DOES CARRY A LANE-INDEPENDENT RECORD, and this arm was written expecting the
  // opposite: `sessions.csv`, the launch trace the spawn path guarantees a header for (7.449). So a
  // shared record EXISTS — and since S-20 the engine both WRITES to it (the foreground carrier) and
  // READS it (the D4 refusal below).
  const trace = path.join(goalFolder, 'sessions.csv');
  const traceRows = fs.existsSync(trace) ? fs.readFileSync(trace, 'utf8').trim().split('\n') : [];
  check('D1 the goal folder DOES carry a lane-independent trace — `sessions.csv`, written at launch',
    traceRows.length > 1, `${Math.max(0, traceRows.length - 1)} row(s)`);
  // ⚑ THE PATTERN IS A QUOTED PATH, not the bare word: a match on prose would fire on the sentences
  // that merely NAME the trace. The control proves the pattern finds a real reader where one exists.
  // D3 (2026-08-19): `supervisor/spawn/spawn.js` no longer quotes `'sessions.csv'`. The quoted
  // mentions were the file-level ro-carve and `assertGroundTruthUnwritable` — the anti-forgery
  // rule D3 retired. The at-dispatch writer remains; it addresses the file via
  // `dispatchSeat.sessionsCsv`, never a quoted basename. The attached carrier still quotes the
  // path because it opens the file by name.
  const TRACE_READ = /['"]sessions\.csv['"]/;      // quotes only — a backticked mention is prose
  const traceReadersAnywhere = filesMatching(TRACE_READ);
  check('D1 …and the ATTACHED carrier writes and reads the quoted path',
    traceReadersAnywhere.includes('operator/attached-execution.js')
      && !traceReadersAnywhere.includes('supervisor/spawn/spawn.js'),
    `quoted-path readers: ${traceReadersAnywhere.join(', ')}`);
  const spawnSrc = fs.readFileSync(path.join(IGNITE_SRC, 'supervisor', 'spawn', 'spawn.js'), 'utf8');
  check('D1 …and the DAEMON spawn path still writes the at-dispatch row via sessionsCsv (D3: no file-level carve)',
    /sessionsCsv/.test(spawnSrc) && /appendRowEnsuringHeader/.test(spawnSrc) && !TRACE_READ.test(spawnSrc),
    'spawn.js must keep the writer and must not re-introduce a quoted sessions.csv carve');
  // S-20 (owner ruling #d-s20-foreground-seat-writes-session-row) FLIPPED THIS ARM, and the flip is
  // the acceptance: a terminal-carried seat IS a launched session, so BOTH carriages of one run now
  // appear in the one trace. The pre-ruling finding (D1b, "the carrier leaves no row") is retired,
  // not merely edited — the traceless-package case it filed no longer exists.
  const tracedSeats = traceRows.slice(1).join('\n');
  check('D1 BOTH carriages of the run leave a trace row — the foreground seat and the detached one',
    /alpha/.test(tracedSeats) && /bravo/.test(tracedSeats),
    traceRows.slice(1).map((r) => r.split(',').slice(0, 3).join(',')).join(' | ') || 'empty');

  {
    const daemonStore = openHeartStore({ dbPath: daemonStorePath });
    const daemonKnows = daemonStore.dump().jobs_log.filter((r) => /^seat-/.test(r.job_id));
    check('D1 the DAEMON lane\'s store knows NOTHING of what the attached lane did — two stores, still',
      daemonKnows.length === 0,
      `${daemonKnows.length} seat row(s) in ${daemonStorePath}`);
    daemonStore.close();   // the in-process E_SECOND_WRITER guard: one handle on this file at a time
  }

  // THE RECORD ITSELF — the file this build is. Written by the attached lane's own run above; the
  // probe hand-writes nothing into it.
  const recordRows = record.readExecutionRecord(goalFolder).rows;
  check('D1 the goal folder carries the EXECUTION RECORD, written by the lane that ran the seats',
    recordRows.length > 0 && recordRows.every((r) => r.lane === 'attached'),
    recordRows.map((r) => `${r.seat}=${r.outcome || 'open'}/${r.lane}`).join(' ') || 'empty');
  // ⚠ THIS ARM USED TO CLAIM "alpha is DONE in the record", off `finishedSeats`. IT CANNOT, AND
  // SAYING SO IS THE POINT OF W2: the `outcome` column is a PROCESS vocabulary (`clean|crashed|
  // killed`), so the most it can attest is that a lane RAN this seat and watched it end — a `clean`
  // exit is equally true of a seat that fail-blocked. Done-ness is the seat's own check-out
  // disposition, on `coord.py ready-seats --json`. What the record still answers is precisely what
  // the cross-lane guarantee spends: has ANY lane already run this seat to termination. So the arm
  // measures THAT, under the function's honest name, and the done-ness claim is not restated
  // somewhere weaker — it is made where it now lives, at the `--status` arm in D4 below, which
  // reads coord's disposition.
  check('D1 the record shows a lane RAN alpha to termination — the cross-lane fact that used to '
    + 'live only in this lane\'s heart.db',
    record.ranSeats(goalFolder).has('alpha'),
    `ran: ${[...record.ranSeats(goalFolder)].join(', ') || 'none'}`);

  // THE PICKUP, BEHAVIOURALLY — the half that could only be measured structurally before, and the
  // reason it can be measured now: seeding stopped being attached-lane machinery (engine/seeding.js)
  // and the engine BOTH lanes boot exposes it. The store below sits at the DAEMON data root, which
  // is what makes this the daemon's lane rather than a second attached run.
  const daemonEngine = createEngine({
    dbPath: daemonStorePath, spawnConfigPath: configPath, userManager: false,
  });
  let pickup;
  try {
    pickup = daemonEngine.seedGoal({ goalFolder, goal: 'lane-goal', profile: 'probe-lane', readLease: fixtureLiveLease });
  } finally {
    daemonEngine.close();
  }
  check('D1 the DAEMON lane can SEED A GOAL FOLDER — the path that did not exist at all before',
    pickup.seats.join() === 'alpha,bravo', JSON.stringify(pickup.seats));
  check('D1 …and it SKIPS the seat the attached lane finished — read from the RECORD, not from a store',
    pickup.skippedAsFinished.includes('alpha') && !pickup.enqueued.includes('alpha'),
    `skipped ${JSON.stringify(pickup.skippedAsFinished)} · enqueued ${JSON.stringify(pickup.enqueued)}`);
  say('MEASURED BOUND — what a live daemon adds that this fixture does not: its LOOP. The TRIGGER is');
  say('  no longer part of that bound: `engine.seedGoal` HAS a caller under server/ since');
  say('  #d-daemon-lane-button — `supervisor/lane-watch.js#runLaneWatch`, fired by the daemon loop before');
  say('  every tick, seeding the goals whose `execution-lane` marker reads `daemon`. That pass, its');
  say('  call site and the owner\'s mid-goal flip are measured next door in probe-daemon-lane-watch.js;');
  say('  what this fixture still substitutes is only the daemon PROCESS (unit, gateway, cadence).');

  // ── D2 · DAEMON first, then the attached lane ───────────────────────────────────────────────
  say('');
  say('D2 — a seat already finished on the DAEMON side, then the goal is run ATTACHED');

  // A SECOND goal folder, never run attached, so the attached lane meets a seat the daemon
  // "already finished" and nothing else.
  const freshGoal = path.join(workspace, '.rbtv', 'goals', 'lane-goal-2');
  for (const s2 of ['alpha', 'bravo']) fs.mkdirSync(path.join(freshGoal, 'seats', s2), { recursive: true });
  fs.mkdirSync(path.join(freshGoal, 'coordination'), { recursive: true });
  fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(freshGoal, 'taskforce.csv'));
  for (const s2 of ['alpha', 'bravo']) {
    fs.copyFileSync(path.join(goalFolder, 'seats', s2, 'seat.md'), path.join(freshGoal, 'seats', s2, 'seat.md'));
  }
  fs.writeFileSync(path.join(freshGoal, 'execution-mode'), 'interactive\n');

  // The daemon's own history for that goal, SYNTHESIZED — job id in the daemon's namespaced
  // spelling (`seat-<goal>-<seat>`, which is what a store holding every goal must use), workdir at
  // the seat's real home, which is the column the record derives goal+seat from in both lanes.
  const DAEMON_SESSION = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';
  {
    const daemonStore = openHeartStore({ dbPath: daemonStorePath });
    const daemonJobId = `seat-lane-goal-2-alpha`;
    daemonStore.registerJob({
      jobId: daemonJobId,
      actionType: 'launch-agent',
      function: 'daemon-side seat alpha',
      argsSchema: JSON.stringify({ required: {}, optional: { workdir: 'string' } }),
      description: 'a seat the DAEMON lane finished',
      createdAt: isoNow(),
      updatedAt: isoNow(),
    });
    const daemonExec = daemonStore.recordExecutionStart({
      jobId: daemonJobId,
      actionType: 'launch-agent',
      args: JSON.stringify({}),
      enqueuedBy: 'daemon',
      sessionMode: 'headless',
      firedTick: 1,
      firedAt: new Date(),
      sessionId: DAEMON_SESSION,
      workdir: path.join(freshGoal, 'seats', 'alpha'),
    });
    daemonStore.endTurnAndCloseSession(daemonExec.exec_id, { turnStatus: 'done', sessionStatus: 'closed', endedAt: new Date() });
    check('D2 the daemon store records alpha as DONE (synthesized, and disclosed as such)',
      daemonStore.dump().jobs_log.some((r) => r.job_id === daemonJobId && r.status === 'done'));

    daemonStore.close();
  }

  // …and now the DAEMON'S OWN CALLER publishes it. ⚠ THIS ARM USED TO CALL `publishToRecord`
  // DIRECTLY, and that is exactly why review finding F1 shipped: measuring the FUNCTION proves
  // nothing about whether anything CALLS it, and the daemon's loop was calling the raw
  // `ticker.tick()`. So the arm now goes through the same two things the daemon does — the engine
  // façade's `tick()`, and the assertion that `runtime/index.js` is what calls it.
  {
    const daemonEngine = createEngine({
      dbPath: daemonStorePath, spawnConfigPath: configPath, userManager: false,
    });
    try {
      await daemonEngine.tick();
    } finally {
      daemonEngine.close();
    }
  }
  // …and the seat's own CHECK-OUT, which is the other half of what a daemon lane leaves behind and
  // the ONLY surface that can say the WORK finished since W2 (see `attestCheckout`). Written AFTER
  // the publish so the arm above still measures the record's own writer and nothing else.
  attestCheckout(freshGoal, 'alpha', DAEMON_SESSION);
  // ⚠ WHAT IT PUBLISHES IS THE CLOSE, NOT A WORD. Row D of spec-state-store emptied the outcome
  // column, so this arm read `outcome === record.CLEAN` against a constant that no longer exists —
  // `undefined`, which no cell can equal. The publish's observable is the row: this lane's name on
  // it and an `ended` stamp, with the work word deliberately absent.
  check('D2 the DAEMON LANE\'S OWN TICK publishes that close into the GOAL FOLDER\'s record',
    record.readExecutionRecord(freshGoal).rows.some((r) => r.seat === 'alpha' && r.lane === 'daemon'
      && (r.ended || '').trim() && !(r.outcome || '').trim()),
    record.readExecutionRecord(freshGoal).rows.map((r) => `${r.seat}=${(r.ended || '').trim() ? 'ended' : 'open'}/${r.lane}`).join(' ') || 'empty');

  // THE CALLER ARM (review F1). The behavioural arm above drives `engine.tick`; this one asserts
  // that the DAEMON drives `engine.tick` too. Both are needed: the first cannot see a loop that
  // reaches past the façade, and this one cannot see a façade that stopped publishing.
  // ⚠ COMMENT LINES ARE STRIPPED FIRST. The fix's own warning line NAMES `ticker.tick()` — a
  // pattern that matched prose would fire on the sentence forbidding the thing it looks for, and
  // this arm went red on exactly that before the strip was added.
  const daemonCode = fs.readFileSync(path.join(IGNITE_SRC, 'runtime', 'index.js'), 'utf8')
    .split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n');
  const bare = (daemonCode.match(/[^.\w]ticker\.tick\(/g) || []).length;
  check('D2 the DAEMON LOOP calls `engine.tick()` — never the raw ticker, which publishes nothing',
    /engine\.tick\(\)/.test(daemonCode) && bare === 0,
    `engine.tick: ${(daemonCode.match(/engine\.tick\(\)/g) || []).length} · bare ticker.tick: ${bare}`);

  const reran = [];
  await attached.executeAttached({
    goalFolder: freshGoal,
    profile: 'probe-lane',
    spawnConfigPath: configPath,
    tickIntervalMs: 200,
    maxTicks: 1,
    spawnForeground: (argv, cwd) => { reran.push(cwd); return { status: 0 }; },
  });
  // THE FLIP. This arm asserted the double run until the record landed; it now asserts the resume.
  check('D2 the attached lane does NOT re-run a seat the DAEMON lane finished — it reads the record',
    reran.length === 0, `foreground launches: ${JSON.stringify(reran)}`);
  check('D2 …and it is a RESUME, not a refusal: the goal advanced, bravo was enqueued here',
    attached.statusAttached({ goalFolder: freshGoal }).done.includes('alpha'),
    JSON.stringify(attached.statusAttached({ goalFolder: freshGoal }).seats.map((x) => `${x.seat}=${x.state}`)));

  // THE DISCRIMINATING MUTATION: nothing about this goal changes except the ONE fact the decision
  // rests on — alpha's ROW. Take it out and the very same fixture re-runs the seat, so the skip
  // above is the record's content, not the file's existence, not the seat's name, not the trace.
  // ⚠ THE MUTATION IS ON THE `ended` CELL AND NO LONGER ON A WORD. It used to blank
  // `record.CLEAN` in the outcome column — and Row D deleted that constant, so the regex was
  // `,undefined$`: it matched NOTHING, the F3 mutant was byte-identical to its control, and the
  // arm passed while measuring nothing at all. Re-opening a row is now what it always meant
  // structurally: clear the close stamp, which is the cell the readers key on.
  const reopenAlphaRow = (rp) => {
    const lines = fs.readFileSync(rp, 'utf8').split('\n');
    const header = lines[0].split(',').map((h) => h.trim());
    const at = header.indexOf('ended');
    const out = lines.map((l, i) => {
      if (i === 0 || !/^alpha,/.test(l)) return l;
      const cells = l.split(',');
      cells[at] = '';
      return cells.join(',');
    });
    if (out.join('\n') === lines.join('\n')) throw new Error('reopenAlphaRow mutated nothing');
    fs.writeFileSync(rp, out.join('\n'));
  };
  // ⚠ A MUTANT DROPS THE CHECK-OUT BY DEFAULT SINCE W2, AND WITHOUT THAT EVERY ARM BELOW IS
  // UNREACHABLE. `freshGoal` now carries both halves a finished daemon-lane seat leaves — the record
  // row AND the `done` disposition on `sessions.csv` — because done-ness moved to the check-out.
  // Every mutant below models a seat whose WORK is NOT finished (crashed, still open, or with its
  // record row erased), and such a seat did not check out `done`; leaving the copied attestation in
  // place makes coord answer `DONE` for it, so nothing can ever be dispatched and each arm reports
  // `[]` no matter what the engine decides. Copying a fixture is copying its every fact.
  // ⚠ AND THE CHECK-OUT IS NOW TWO FACTS, SO COPYING IT IS TWO ACTS. Since spec-state-store §4.1
  // the ending lives in the store, keyed by GOAL NAME — and a mutant is a NEW goal name, so
  // `cpSync` carries the `sessions.csv` row and leaves the ending behind. A mutant that kept its
  // check-out on paper and lost it in the store is not the fixture arm (a) claims; it is a seat
  // that never ended, which re-runs for a reason the arm is not about.
  const mutantOf = (name, edit, { keepCheckout = false } = {}) => {
    const dir = path.join(workspace, '.rbtv', 'goals', name);
    fs.cpSync(freshGoal, dir, { recursive: true });
    for (const f of fs.readdirSync(dir)) if (f.startsWith('heart.db')) fs.rmSync(path.join(dir, f), { force: true });
    if (!keepCheckout) fs.rmSync(path.join(dir, 'sessions.csv'), { force: true });
    if (keepCheckout) stampDone(dir, 'alpha');
    edit(record.recordPath(dir));
    return dir;
  };
  const runOn = async (dir) => {
    const fired = [];
    const out = await attached.executeAttached({
      goalFolder: dir, profile: 'probe-lane', spawnConfigPath: configPath, tickIntervalMs: 200,
      maxTicks: 1, spawnForeground: (argv, cwd) => { fired.push(cwd); return { status: 0 }; },
    });
    return { fired, out };
  };

  const dropAlphaRow = (rp) => {
    const keep = fs.readFileSync(rp, 'utf8').split('\n').filter((l) => !/^alpha,/.test(l));
    fs.writeFileSync(rp, keep.join('\n'));
  };
  // ⚠ THE SINGLE MUTATION THAT USED TO SIT HERE IS NOW A **PAIR**, AND THE FIRST HALF IS THE W2
  // REPOINT ITSELF. The arm read "delete alpha's ROW from the record and the same goal re-runs the
  // seat — the decision is the recorded row and nothing else". That sentence is false since W2 and
  // its falseness is the whole change: the record's `outcome` column is a PROCESS vocabulary, so
  // nothing in it can say the WORK finished, and the seat's own CHECK-OUT decides. Erasing the
  // record row alone therefore must NOT re-run the seat — and had this stayed one arm, the honest
  // new behaviour would have read as a regression.
  const goneRecordOnly = mutantOf('lane-goal-2m-rec', dropAlphaRow, { keepCheckout: true });
  const goneRecordOnlyRun = await runOn(goneRecordOnly);
  check('D2 MUTATION (a): with alpha\'s record ROW deleted but its CHECK-OUT intact the seat is '
    + 'STILL not re-run — done-ness is the seat\'s own disposition since W2, not a cell in this file',
    goneRecordOnlyRun.fired.length === 0, JSON.stringify(goneRecordOnlyRun.fired));
  // …and the non-vacuity half: with NEITHER half of the evidence the very same fixture DOES re-run
  // the seat, so arm (a) is a hold and not a fixture that could never dispatch anything.
  const gone = mutantOf('lane-goal-2m', dropAlphaRow);
  const goneRun = await runOn(gone);
  check('D2 MUTATION (b): with the record row AND the check-out both gone the same goal re-runs the '
    + 'seat — so (a) measured a hold, not a fixture that can never dispatch',
    goneRun.fired.length === 1 && goneRun.fired[0] === path.join(gone, 'seats', 'alpha'),
    JSON.stringify(goneRun.fired));

  // ── F3 · AN OPEN FOREIGN ROW IS A SEAT SOMEBODY ELSE IS RUNNING RIGHT NOW ───────────────────
  // Blank the OUTCOME and the row goes back to what it was between dispatch and completion. The
  // seat must NOT be dispatched here — that was the double-dispatch review finding F3 — and the run
  // must not spin on it either.
  const openGoal = mutantOf('lane-goal-2o', reopenAlphaRow, { keepCheckout: true });
  const openRun = await runOn(openGoal);
  check('F3 an OPEN row from another lane HOLDS the seat — it is never dispatched a second time',
    openRun.fired.length === 0, `foreground launches ${JSON.stringify(openRun.fired)}`);
  check('F3 …and the run RETURNS rather than spinning on a seat only the other lane can advance',
    openRun.out.outcome === 'blocked' && openRun.out.unfinished.includes('alpha'),
    `outcome=${openRun.out.outcome} unfinished=${JSON.stringify(openRun.out.unfinished)}`);
  check('F3 …and `--status` says so in the shared vocabulary: the seat reads `live`, not `ready`',
    attached.statusAttached({ goalFolder: openGoal }).live.includes('alpha')
      && !attached.statusAttached({ goalFolder: openGoal }).ready.includes('alpha'),
    JSON.stringify(attached.statusAttached({ goalFolder: openGoal }).seats.map((x) => `${x.seat}=${x.state}`)));
  // ── F6 · A FOREIGN `crashed` OUTCOME IS HELD TOO, exactly like a local one ────────
  // ⚠ AND THE FAILURE IS STAMPED IN THE STORE, NOT SPELLED IN THE COLUMN (§4.4): death-truth is
  // `failed` plus an evidence pointer, and it is TERMINAL here (the leader attempt spent) because
  // that is the state that holds. The old mutant wrote `record.CRASHED` into the outcome cell — a
  // constant Row D deleted, so it wrote `undefined` and the arm held for no reason at all.
  const failedGoal = mutantOf('lane-goal-2f', () => {});
  stampFailedTerminal(failedGoal, 'alpha');
  const failedRun = await runOn(failedGoal);
  check('F6 a seat that FAILED in the other lane is held here, not silently re-run — exactly as a '
    + 'LOCAL failure is held on this lane',
    failedRun.fired.length === 0, `foreground launches ${JSON.stringify(failedRun.fired)}`);
  // ── F2 · ADOPTION: a goal that ran BEFORE this record existed publishes its history ──────────
  //
  // The state every goal on disk was in the day this landed: a store full of outcomes, no record.
  // Delete the record from the goal D1 ran IN PLACE (so its workdirs really are its own), run the
  // verb again, and the run must publish its own store's history — which is what makes the OTHER
  // lane able to skip those seats. The daemon assertion is the discriminating half: without the
  // publish inside `engine.tick`, the record stays empty and the daemon enqueues a finished seat.
  fs.rmSync(record.recordPath(goalFolder), { force: true });
  await runOn(goalFolder);
  check('F2 ADOPTION: a goal whose record was deleted has its store\'s history published by the run',
    record.ranSeats(goalFolder).has('alpha'),
    `record ${record.readExecutionRecord(goalFolder).rows.map((r) => `${r.seat}=${r.outcome || 'open'}`).join(' ') || 'empty'}`);
  {
    const daemonEngine = createEngine({
      dbPath: daemonStorePath, spawnConfigPath: configPath, userManager: false,
    });
    let pick;
    try { pick = daemonEngine.seedGoal({ goalFolder, goal: 'lane-goal', profile: 'probe-lane', readLease: fixtureLiveLease }); }
    finally { daemonEngine.close(); }
    check('F2 …and THAT is what the other lane reads: the daemon skips alpha off the republished record',
      pick.skippedAsFinished.includes('alpha') && !pick.enqueued.includes('alpha'),
      `skipped ${JSON.stringify(pick.skippedAsFinished)} · enqueued ${JSON.stringify(pick.enqueued)}`);
  }

  finding('D2 cross-lane resume HOLDS in the daemon->attached direction: the daemon\'s own publish '
    + 'writes the outcome into <goal>/executions.csv, and the attached lane skips the seat without '
    + 'refusing the goal. The former finding — "two lanes over one goal folder can each run the same '
    + 'seat once" — is RETIRED by the mutation pair above, which shows the skip tracking exactly the '
    + 'recorded outcome.');

  // ── D5 · THE RECORD SURVIVES TWO WRITERS (review finding F4) ────────────────────────────────
  //
  // The first version of this file did its close as an UNLOCKED read-modify-write. Measured in
  // review: 300 appends racing 300 closes lost 336 of 601 rows — WHOLE ROWS, nothing malformed for
  // a reader to notice — and the record's own reader (`ranSeats`, spelled `finishedSeats` then)
  // transiently read EMPTY mid-rewrite, which is the one wrong answer that re-runs a seat another
  // lane already ran. Two lanes over one goal is what this record is FOR,
  // so that interleaving is the normal case. This arm is that experiment, kept.
  //
  // TWO REAL PROCESSES, not two loops in one: the losing interleaving is between processes, and an
  // in-process race would prove nothing about a lock whose whole job is to be seen by another pid.
  say('');
  say('D5 — 300 appends racing 300 closes, from two separate processes');

  const raceGoal = path.join(workspace, '.rbtv', 'goals', 'lane-goal-race');
  fs.mkdirSync(raceGoal, { recursive: true });
  const N = 300;
  const child = (body) => require('node:child_process').spawn(process.execPath,
    ['-e', `const record=require(${JSON.stringify(path.join(IGNITE_SRC, 'supervisor', 'execution-record.js'))});const G=${JSON.stringify(raceGoal)};const N=${N};${body}`],
    { stdio: 'ignore' });

  // The reader takes NO lock — that is the point of the atomic replace — and it must never see the
  // row count go backwards, nor a stamped-outcome count go backwards.
  let minRows = 0; let regressed = false; let sawEmptyAfterRows = false;
  const poll = setInterval(() => {
    const rows = record.readExecutionRecord(raceGoal).rows.length;
    if (rows < minRows) regressed = true;
    if (minRows > 0 && rows === 0) sawEmptyAfterRows = true;
    minRows = Math.max(minRows, rows);
  }, 1);

  const appender = child('for(let i=0;i<N;i++)record.openExecution({goalFolder:G,seat:"s"+i,sessionId:"sid-"+i,lane:"attached",startedAt:"t"});');
  const closer = child('let i=0;const t=Date.now();while(i<N){if(record.closeExecution({goalFolder:G,sessionId:"sid-"+i,outcome:"",endedAt:"t"}).closed){i++;continue;}if(Date.now()-t>60000)break;}');
  await Promise.all([appender, closer].map(awaitExit));
  clearInterval(poll);

  const raceRows = record.readExecutionRecord(raceGoal).rows;
  // The close stamp is `ended`; the outcome cell is blank on every closed row since Row D, so
  // counting it counted zero and this arm reported a lost race that never happened.
  const stamped = raceRows.filter((r) => (r.ended || '').trim());
  const malformed = raceRows.filter((r) => !r.seat || !r['session-id']);
  check(`D5 all ${N} appended rows SURVIVED the race — not one lost`,
    raceRows.length === N, `${raceRows.length}/${N} rows · ${malformed.length} malformed`);
  check(`D5 all ${N} closes landed`, stamped.length === N, `${stamped.length}/${N} closed`);
  check('D5 an UNLOCKED reader never saw the file go backwards or empty',
    !regressed && !sawEmptyAfterRows, `regressed=${regressed} empty-after-rows=${sawEmptyAfterRows}`);
  check('D5 no lock file survives the writers',
    !fs.existsSync(record.recordPath(raceGoal) + '.lock'),
    fs.readdirSync(raceGoal).join(' '));

  // ── D3 · the human-interactive seat on the daemon side ──────────────────────────────────────
  say('');
  say('D3 — the same held seat, in the lane with no terminal');

  check('D3 the seat IS held in the attached lane — so anything below is about the LANE, not the seat',
    attached.heldSeatPredicate(freshGoal)('alpha') === true);

  // ⚑ THE STRUCTURAL CLAIM WAS RE-SCOPED (owner ruling `#d-d3-dedupe-rescope`, 2026-08-10). It read
  // "NOTHING under server/ asks whether a seat is human-interactive" — and that stopped being the
  // thing worth protecting the moment the warm path landed a LEGITIMATE reader there
  // (`live-sessions.js` gate 1, live-session-design §1). Worse, the claim was satisfiable by the
  // exact defect it should have caught: the warm path first satisfied it by carrying its OWN copy
  // of the predicate, the pre-a6bb05d regex, blind to `"yes"` and to a trailing comment — a second
  // parser of one file, which is the drift PRIN-11 exists to prevent. So the arm now measures the
  // two things that actually protect the architecture, each with the mutation that turns it red.
  //
  // Half 1 — ONE IMPLEMENTATION. A parser of this flag is a regex literal over it, and `/^human-`
  // is that signature: it excludes prose quoting the field name (`goal_cli.py`'s writer comment
  // does exactly that) and catches any re-introduced copy. MUTATION: put the old regex back in
  // `live-sessions.js` → this check goes red on a second entry.
  const flagParsers = filesMatching(/\/\^human-interactive:/);
  check('D3 exactly ONE implementation of the human-interactive predicate, and it is the ferry\'s '
    + '(PRIN-11 — two parsers of one file is a system whose halves disagree about the same seat)',
    flagParsers.length === 1 && flagParsers[0] === 'chat/bus-ferry.js',
    `parsers: ${flagParsers.join(', ') || 'none'}`);

  // Half 2 — NO DISPATCH-PATH READER. The one server/ file that names the flag decides WARMTH, not
  // dispatch: an ineligible seat takes the cold path unchanged, so nothing about WHERE or WHETHER a
  // seat runs turns on it. The dispatch door itself does not know the word, and the warm gate reads
  // THROUGH the ferry — a lazy require, so the daemon still holds no load-time dependency on the
  // relocatable bridge subtree.
  const serverReaders = filesMatching(/human-interactive/).filter((f) => f.startsWith('server/'));
  const anyReaders = filesMatching(/human-interactive/);
  const liveSrc = fs.readFileSync(path.join(IGNITE_SRC, 'supervisor', 'spawn', 'live-sessions.js'), 'utf8');
  const doorSrc = fs.readFileSync(path.join(IGNITE_SRC, 'supervisor', 'spawn', 'spawn.js'), 'utf8');
  check('D3 the DISPATCH DOOR never asks — the only server/ reader is the warm-path eligibility '
    + 'gate, and it reads THROUGH the ferry instead of parsing the seat itself',
    serverReaders.length === 1 && serverReaders[0] === 'supervisor/spawn/live-sessions.js'
      && !/human-interactive/.test(doorSrc)
      && /require\('\.\.\/\.\.\/bridges\/chat\/bus-ferry'\)/.test(liveSrc)
      && anyReaders.includes('chat/bus-ferry.js')
      && anyReaders.includes('operator/attached-execution.js'),
    `server/: ${serverReaders.join(', ') || 'none'} · elsewhere: ${anyReaders.join(', ')}`);

  // ⚑ THIS ARM WAS NEGATIVE AND IS NOW POSITIVE — the finding it recorded was RULED and BUILT
  // (task 7.626, `#d-s19-fallback-rides-goal-channels`). It used to assert that the ferry did not
  // know the word `fallback` at all, which was the measurement that filed the gap. Inverting it
  // rather than deleting it keeps the same file answering the same question: WHERE does a held
  // seat's declared arm get executed. The answer is: in this module, on the goal-channel surface.
  const ferry = fs.readFileSync(path.join(IGNITE_SRC, 'chat', 'bus-ferry.js'), 'utf8');
  // ⚠ AND THE `park` RUNG IS NO LONGER PART OF THE CLAIM — it was DELETED by ruling
  // [D24, T2-R17, D-7-ruling, T2-R14] (`chat(bus-ferry): the park is deleted — every `to: owner`
  // row travels`), which is why the third conjunct here is now its ABSENCE. The three park rungs
  // swallowed owner-bound rows: nothing posted, cursor advanced, no retry, no queue. The reader
  // and the three declared arms still live in this one module, which is all this arm was ever
  // about; what it may no longer assert is that a gate parks a question.
  check('D3 the module that IMPLEMENTS the two gates also owns the seat\'s declared `fallback:` '
    + 'reader and its arms (7.626) — and NO gate-park reason survives it [D24]',
    /function seatFallback\(/.test(ferry)
      && ['park', 'default-and-disclose', 'block-and-queue'].every((a) => ferry.includes(`'${a}'`))
      && !/'fallback-park'/.test(ferry),
    'reader+arms present, gate park absent — see bus-ferry.js § THE SEAT\'S FALLBACK ARM');
  const watch = fs.readFileSync(path.join(IGNITE_SRC, 'supervisor', 'lane-watch.js'), 'utf8');
  check('D3 …and the DAEMON lane reads it through THAT module\'s reader — no second parser of a seat '
    + 'descriptor anywhere on the path',
    /require\('\.\.\/bridges\/chat\/bus-ferry'\)/.test(watch) && /seatFallback\(goalFolder, seat\)/.test(watch),
    'lane-watch.js imports seatFallback from bus-ferry.js');
  finding('D3 RESOLVED (7.626, ruling #d-s19-fallback-rides-goal-channels). The daemon lane still '
    + 'dispatches a human-interactive seat as an ordinary detached child — no server/ reader decides '
    + 'DISPATCH on the flag, and none needs to: the ruled owner surface is the goal\'s Slack channel '
    + 'with a thread per agent, so the arm executes AT THE FERRY. `park` parks the ask on the ferry\'s '
    + 'own gate ladder (`gate: fallback-park`); `default-and-disclose` and `block-and-queue` are '
    + 'delivered into the seat\'s thread and MARKED, so the owner can tell an FYI from a question; a '
    + 'seat with no declared arm keeps its pre-7.626 behaviour and lane-watch warns, naming '
    + '`component-lint --check interactive-fallback`. The bound left standing and disclosed: '
    + '`block-and-queue` does not hold the DAG — the wait is the seat\'s own procedure plus the '
    + 'existing revival leg (the owner\'s reply mints a session at the asking seat\'s home).');

  // ── D4 · THE CROSSOVER, RESUMED (owner ruling decisions.md#d-s23-single-execution-record-now)
  //
  // This section measured the v1 REFUSAL: a lane declining a goal that carried execution evidence
  // its own store could not account for. That guard is DELETED with this build — the record answers
  // the question the guard could only decline — so the arms are repurposed onto the answer:
  // a goal carrying another lane's evidence RUNS, and re-runs nothing that lane finished.
  say('');
  say('D4 — a goal carrying ANOTHER LANE\'s evidence is RESUMED, not refused');

  const foreignGoal = path.join(workspace, '.rbtv', 'goals', 'lane-goal-3');
  for (const s2 of ['alpha', 'bravo']) fs.mkdirSync(path.join(foreignGoal, 'seats', s2), { recursive: true });
  fs.mkdirSync(path.join(foreignGoal, 'coordination'), { recursive: true });
  fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(foreignGoal, 'taskforce.csv'));
  for (const s2 of ['alpha', 'bravo']) {
    fs.copyFileSync(path.join(goalFolder, 'seats', s2, 'seat.md'), path.join(foreignGoal, 'seats', s2, 'seat.md'));
  }
  fs.writeFileSync(path.join(foreignGoal, 'execution-mode'), 'interactive\n');
  // The launch TRACE the old guard refused on — header from the SCHEMA OWNER (coord.py
  // SESSIONS_COLS), never spelled here. It is written for two reasons: the trace is still the
  // lifecycle accounting both lanes keep, and the LAST arm below measures what it now does NOT do.
  const FOREIGN_SESSION = '11111111-2222-3333-4444-555555555555';
  // ⚠ THE ROW IS CLOSED WITH A `done` DISPOSITION, and since W2 it must be. The seat this arm calls
  // finished is finished BECAUSE IT SAID SO — an open trace row plus a record outcome models a lane
  // that launched a seat which never checked out, which is a real state and not this one.
  attestCheckout(foreignGoal, 'alpha', FOREIGN_SESSION);
  // …and the other lane's OUTCOME, in the shared record, keyed by that same session id.
  record.openExecution({ goalFolder: foreignGoal, seat: 'alpha', sessionId: FOREIGN_SESSION, lane: 'daemon', startedAt: isoNow() });
  record.closeExecution({ goalFolder: foreignGoal, sessionId: FOREIGN_SESSION, outcome: '', endedAt: isoNow() });

  const foreignRuns = [];
  const attempt = async (goal, sink = null) => {
    try {
      await attached.executeAttached({
        goalFolder: goal, profile: 'probe-lane', spawnConfigPath: configPath, tickIntervalMs: 200,
        maxTicks: 1, spawnForeground: (argv, cwd) => { if (sink) sink.push(cwd); return { status: 0 }; },
      });
      return null;
    } catch (err) { return err.message; }
  };

  const refusal = await attempt(foreignGoal, foreignRuns);
  check('D4 `rbtv run` RUNS a goal carrying another lane\'s launched session — the v1 refusal is gone',
    refusal === null, refusal ? refusal.split('\n')[0].slice(0, 120) : 'ran');
  check('D4 …and it re-ran NOTHING that lane finished: alpha is done, and this lane never launched it',
    foreignRuns.length === 0 && attached.statusAttached({ goalFolder: foreignGoal }).done.includes('alpha'),
    `foreground launches ${JSON.stringify(foreignRuns)}`);
  check('D4 orientation is READ-ONLY and still never refuses — and it now answers `done` for a seat '
    + 'THIS lane never ran, off the other lane\'s two files and no store of its own',
    (() => {
      const fresh = path.join(workspace, '.rbtv', 'goals', 'lane-goal-4');
      fs.mkdirSync(path.join(fresh, 'seats', 'alpha'), { recursive: true });
      fs.mkdirSync(path.join(fresh, 'seats', 'bravo'), { recursive: true });
      fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(fresh, 'taskforce.csv'));
      for (const s2 of ['alpha', 'bravo']) fs.copyFileSync(path.join(goalFolder, 'seats', s2, 'seat.md'), path.join(fresh, 'seats', s2, 'seat.md'));
      const FRESH_SESSION = 'ffffffff-0000-0000-0000-000000000001';
      record.openExecution({ goalFolder: fresh, seat: 'alpha', sessionId: FRESH_SESSION, lane: 'daemon', startedAt: isoNow() });
      record.closeExecution({ goalFolder: fresh, sessionId: FRESH_SESSION, outcome: '', endedAt: isoNow() });
      // …AND THE TRACE ROW THAT LANE'S SEAT LEFT, CHECKED OUT `done`. The record answers "did this
      // seat FINISH" and coord answers "is bravo READY", and since § D1 they are DIFFERENT
      // QUESTIONS asked of DIFFERENT FILES — a fixture writing only the record models a lane that
      // ran a seat which never checked out, for which `bravo` correctly never becomes ready. Both
      // halves are written here because the daemon lane writes both.
      fs.writeFileSync(path.join(fresh, 'sessions.csv'), `${HEADER}\n${cell({
        'session-id': FRESH_SESSION, seat: 'alpha', harness: 'claude',
        workdir: path.join(fresh, 'seats', 'alpha'), started: isoNow(), ended: isoNow(),
        disposition: 'done', 'disposition-writer': 'seat',
      })}\n`);
      // …and the third half the daemon lane leaves: the ENDING, in the one store both lanes read
      // (§1.1). It is what makes this arm's claim true — the orientation answers `done` for a seat
      // this lane never ran, with no store of ITS OWN in the goal folder.
      stampDone(fresh, 'alpha');
      const st = attached.statusAttached({ goalFolder: fresh });
      return st.everRun === false && st.done.join() === 'alpha' && st.ready.join() === 'bravo'
        && !fs.existsSync(path.join(fresh, 'heart.db'));
    })(), 'a goal this lane has no store for still reports what the other lane finished');

  // THE FALSE-POSITIVE CONTROL, unchanged in intent and still the one that decides shippability: a
  // goal the attached lane ran ITSELF must resume without re-running its own finished seats.
  const ownRerun = [];
  check('D4 CONTROL: the attached lane re-runs its own goal and re-fires nothing',
    (await attempt(goalFolder, ownRerun)) === null && ownRerun.length === 0,
    `foreground launches ${JSON.stringify(ownRerun)}`);

  // THE BOUND THE RETIRED GUARD USED TO COVER, measured rather than asserted: a seat run BY HAND
  // writes a `sessions.csv` row and NO record row. The guard refused the whole goal over it; the
  // record does not see it at all, so the seat IS re-run.
  const handGoal = path.join(workspace, '.rbtv', 'goals', 'lane-goal-5');
  for (const s2 of ['alpha', 'bravo']) fs.mkdirSync(path.join(handGoal, 'seats', s2), { recursive: true });
  fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(handGoal, 'taskforce.csv'));
  for (const s2 of ['alpha', 'bravo']) fs.copyFileSync(path.join(goalFolder, 'seats', s2, 'seat.md'), path.join(handGoal, 'seats', s2, 'seat.md'));
  fs.writeFileSync(path.join(handGoal, 'execution-mode'), 'interactive\n');
  fs.writeFileSync(path.join(handGoal, 'sessions.csv'), `${HEADER}\n${cell({
    'session-id': '22222222-3333-4444-5555-666666666666', seat: 'alpha', harness: 'claude',
    workdir: path.join(handGoal, 'seats', 'alpha'), started: isoNow(),
  })}\n`);
  const handRuns = [];
  const handRefusal = await attempt(handGoal, handRuns);
  check('D4 BOUND: a trace row with NO record row does not stop a re-run (and does not refuse either)',
    handRefusal === null && handRuns.length === 1,
    `refusal ${handRefusal ? 'yes' : 'no'} · launches ${JSON.stringify(handRuns)}`);

  finding('D4 the crossover is now RESUMED in both directions rather than refused, and the record is '
    + 'the deciding fact in each (D1 attached->daemon: the daemon\'s seeding skips the finished seat; '
    + 'D2 daemon->attached: the attached lane skips it, and blanking the outcome cell re-runs it). '
    + 'The one case the retired v1 guard covered and the record does not: work executed with NO '
    + 'record row — a hand-run tmux sitting — is invisible and will be re-run. Closing such a seat '
    + 'is one outcome row in <goal>/executions.csv, which is the same act every lane performs.');

  finding('D4 THE DAEMON HALF IS NOW WHOLE: `engine.seedGoal` is built and proven here (D1), and since '
    + 'owner ruling #d-daemon-lane-button it HAS a caller under server/ — the daemon loop runs '
    + '`supervisor/lane-watch.js#runLaneWatch` before every tick, which seeds each goal whose '
    + '`execution-lane` marker reads `daemon` (absent means console; the daemon adopts only what it '
    + 'was explicitly given, and stays off a goal a console runner is attached to). This finding used '
    + 'to read "nothing under server/ CALLS it yet"; that is retired, and the trigger\'s own arms — '
    + 'including the owner\'s start-in-daemon-finish-in-console flip and three red mutations — live in '
    + 'probe-daemon-lane-watch.js beside this file.');

  fs.rmSync(tmp, { recursive: true, force: true });
}

main().then(() => {
  const exitCode = failures.length ? 1 : 0;
  say('');
  say(exitCode
    ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
    : `RESULT: PASS — every arm measured what it claims. Since #d-s23-single-execution-record-now `
      + `the headline is POSITIVE: cross-lane resume HOLDS in both directions, off `
      + `<goal>/executions.csv, and the v1 refusal it replaces is retired. The FINDINGS below carry `
      + `what is still open — the fallback gap (D3) and the one case the retired guard covered that `
      + `the record does not. The daemon's pickup TRIGGER is no longer among them: it landed with `
      + `#d-daemon-lane-button and is measured in probe-daemon-lane-watch.js.`);
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
