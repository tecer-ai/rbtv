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
//     boots (`createEngine` — the same call `server/index.js` makes) against a store placed at a
//     DAEMON data root, which is exactly what makes a lane the daemon's (`execution-record.laneOf`).
//     What a live daemon adds on top is its unit, its gateway and its arming; none of the three
//     touches the seeding or record decisions measured here. The TRIGGER bound is reported at D1.
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

const attached = require('../attached-execution');
const record = require('../execution-record');
const { createEngine } = require('../index');
const { openHeartStore } = require('../../server/heart/heart-store');

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
const cfg = yaml.load(fs.readFileSync(path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml'), 'utf8'));
cfg.spawn = { ...(cfg.spawn || {}), data_root: dataRoot, carrier: 'setsid' };
cfg.default_workdir_root = path.join(tmp, 'work');
fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
cfg.profiles['probe-lane'] = {
  exec: { argv: ['sleep', '1'], prompt: 'stdin' },
  headed: { tui: { argv: ['true'] } },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
  sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
};
const configPath = path.join(tmp, 'spawn-profiles.yaml');
fs.writeFileSync(configPath, yaml.dump(cfg));

const goalFolder = path.join(workspace, '.rbtv', 'goals', 'lane-goal');
for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(goalFolder, 'seats', s), { recursive: true });
fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
  'taskforce-id,seat,after\ntf-lane,alpha,\ntf-lane,bravo,alpha\n');
fs.writeFileSync(path.join(goalFolder, 'seats', 'alpha', 'seat.md'),
  '---\nseat: alpha\nhuman-interactive: yes\nfallback: block-and-queue\n---\n\nbody\n');
fs.writeFileSync(path.join(goalFolder, 'seats', 'bravo', 'seat.md'), '---\nseat: bravo\n---\n\nbody\n');
fs.writeFileSync(path.join(goalFolder, 'execution-mode'), 'interactive\n');

const goalStorePath = path.join(goalFolder, 'heart.db');
const daemonStorePath = path.join(dataRoot, 'heart.db');
const isoNow = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');

async function main() {
  say('probe-cross-lane-resume — console-run wave B item B3');
  say(`fixture: ${tmp}`);
  say('');

  // ── D1 · ATTACHED first, then the daemon lane ──────────────────────────────────────────────
  say('D1 — a goal advanced in the ATTACHED lane, offered to the DAEMON lane');

  await attached.executeAttached({
    goalFolder,
    profile: 'probe-lane',
    spawnConfigPath: configPath,
    tickIntervalMs: 200,
    maxTicks: 1,
    spawnForeground: () => ({ status: 0 }),     // alpha is held; it runs in "the terminal"
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
  const TRACE_READ = /['"]sessions\.csv['"]/;      // quotes only — a backticked mention is prose
  const traceReadersAnywhere = filesMatching(TRACE_READ);
  check('D1 …and the ENGINE both writes and reads it — the foreground carrier opens and closes a row',
    traceReadersAnywhere.includes('engine/attached-execution.js')
      && traceReadersAnywhere.includes('server/spawn/spawn.js'),
    `readers: ${traceReadersAnywhere.join(', ')}`);
  // S-20 (owner ruling #d-s20-foreground-seat-writes-session-row) FLIPPED THIS ARM, and the flip is
  // the acceptance: a terminal-carried seat IS a launched session, so BOTH carriages of one run now
  // appear in the one trace. The pre-ruling finding (D1b, "the carrier leaves no row") is retired,
  // not merely edited — the traceless-package case it filed no longer exists.
  const tracedSeats = traceRows.slice(1).join('\n');
  check('D1 BOTH carriages of the run leave a trace row — the foreground seat and the detached one',
    /alpha/.test(tracedSeats) && /bravo/.test(tracedSeats),
    traceRows.slice(1).map((r) => r.split(',').slice(0, 3).join(',')).join(' | ') || 'empty');

  {
    const daemonStore = openHeartStore({ dbPath: daemonStorePath, profiles: cfg.profiles });
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
  check('D1 alpha is DONE in the record — the answer that used to live only in this lane\'s heart.db',
    record.finishedSeats(goalFolder).has('alpha'),
    `finished: ${[...record.finishedSeats(goalFolder)].join(', ') || 'none'}`);

  // THE PICKUP, BEHAVIOURALLY — the half that could only be measured structurally before, and the
  // reason it can be measured now: seeding stopped being attached-lane machinery (engine/seeding.js)
  // and the engine BOTH lanes boot exposes it. The store below sits at the DAEMON data root, which
  // is what makes this the daemon's lane rather than a second attached run.
  const daemonEngine = createEngine({
    dbPath: daemonStorePath, profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
  });
  let pickup;
  try {
    pickup = daemonEngine.seedGoal({ goalFolder, goal: 'lane-goal', profile: 'probe-lane' });
  } finally {
    daemonEngine.close();
  }
  check('D1 the DAEMON lane can SEED A GOAL FOLDER — the path that did not exist at all before',
    pickup.seats.join() === 'alpha,bravo', JSON.stringify(pickup.seats));
  check('D1 …and it SKIPS the seat the attached lane finished — read from the RECORD, not from a store',
    pickup.skippedAsFinished.includes('alpha') && !pickup.enqueued.includes('alpha'),
    `skipped ${JSON.stringify(pickup.skippedAsFinished)} · enqueued ${JSON.stringify(pickup.enqueued)}`);
  say('MEASURED BOUND — what a live daemon adds that this fixture does not: THE TRIGGER. `seedGoal`');
  say('  is a function, and nothing under server/ calls it yet — which goals the daemon picks up by');
  say('  itself is an owner-facing arming question (per-package today, edge-fastpath), deliberately');
  say('  not invented by this build. The pickup PATH is measured here; the thing that fires it is a');
  say('  named follow-on (capabilities/attached-execution/attached-execution.md § the follow-on).');

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
    const daemonStore = openHeartStore({ dbPath: daemonStorePath, profiles: cfg.profiles });
    const daemonJobId = `seat-lane-goal-2-alpha`;
    daemonStore.registerJob({
      jobId: daemonJobId,
      actionType: 'launch-agent',
      function: 'daemon-side seat alpha',
      argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { workdir: 'string' } }),
      description: 'a seat the DAEMON lane finished',
      createdAt: isoNow(),
      updatedAt: isoNow(),
    });
    const daemonExec = daemonStore.recordExecutionStart({
      jobId: daemonJobId,
      actionType: 'launch-agent',
      args: JSON.stringify({ profile: 'probe-lane' }),
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

    // …and the DAEMON'S OWN WRITER publishes it — not the probe. This is the call `engine.tick()`
    // makes on every daemon cadence, run here directly because no daemon process is up.
    const published = record.publishToRecord(daemonStore);
    check('D2 the DAEMON lane publishes that outcome into the GOAL FOLDER\'s record',
      published.closed.includes('alpha=done')
        && record.readExecutionRecord(freshGoal).rows.some((r) => r.seat === 'alpha' && r.lane === 'daemon' && r.outcome === 'done'),
      JSON.stringify(published));
    daemonStore.close();
  }

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
  // rests on — alpha's OUTCOME cell. Blank it, and the very same fixture re-runs the seat. So the
  // skip above is the record's `done`, not the file's existence, not the seat's name, not the trace.
  const mutantGoal = path.join(workspace, '.rbtv', 'goals', 'lane-goal-2m');
  fs.cpSync(freshGoal, mutantGoal, { recursive: true });
  fs.rmSync(path.join(mutantGoal, 'heart.db'), { force: true });
  for (const f of fs.readdirSync(mutantGoal)) if (f.startsWith('heart.db-')) fs.rmSync(path.join(mutantGoal, f), { force: true });
  const rec = fs.readFileSync(record.recordPath(mutantGoal), 'utf8');
  fs.writeFileSync(record.recordPath(mutantGoal), rec.replace(/,done$/m, ','));
  const reranMutant = [];
  await attached.executeAttached({
    goalFolder: mutantGoal,
    profile: 'probe-lane',
    spawnConfigPath: configPath,
    tickIntervalMs: 200,
    maxTicks: 1,
    spawnForeground: (argv, cwd) => { reranMutant.push(cwd); return { status: 0 }; },
  });
  check('D2 MUTATION: blank alpha\'s OUTCOME in the record and the same goal re-runs it — the '
    + 'decision is the recorded outcome and nothing else',
    reranMutant.length === 1 && reranMutant[0] === path.join(mutantGoal, 'seats', 'alpha'),
    JSON.stringify(reranMutant));

  finding('D2 cross-lane resume HOLDS in the daemon->attached direction: the daemon\'s own publish '
    + 'writes the outcome into <goal>/executions.csv, and the attached lane skips the seat without '
    + 'refusing the goal. The former finding — "two lanes over one goal folder can each run the same '
    + 'seat once" — is RETIRED by the mutation pair above, which shows the skip tracking exactly the '
    + 'recorded outcome.');

  // ── D3 · the human-interactive seat on the daemon side ──────────────────────────────────────
  say('');
  say('D3 — the same held seat, in the lane with no terminal');

  check('D3 the seat IS held in the attached lane — so anything below is about the LANE, not the seat',
    attached.heldSeatPredicate(freshGoal)('alpha') === true);

  const serverReaders = filesMatching(/human-interactive/).filter((f) => f.startsWith('server/'));
  const anyReaders = filesMatching(/human-interactive/);
  check('D3 NOTHING under server/ — the dispatch and spawn path — asks whether a seat is human-interactive',
    serverReaders.length === 0 && anyReaders.includes('bridges/chat/bus-ferry.js')
      && anyReaders.includes('engine/attached-execution.js'),
    `server/: ${serverReaders.join(', ') || 'none'} · elsewhere: ${anyReaders.join(', ')}`);

  const ferry = fs.readFileSync(path.join(IGNITE_SRC, 'bridges', 'chat', 'bus-ferry.js'), 'utf8');
  check('D3 the module that IMPLEMENTS the two gates does not know the word `fallback` at all',
    !/fallback/.test(ferry),
    'so the `fallback:` a held seat is REQUIRED to declare is consumed by no runtime reader');
  finding('D3 a human-interactive seat dispatched by the DAEMON lane is spawned as an ordinary '
    + 'detached child: nothing on that path reads the flag, so there is no point at which its '
    + '`fallback:` (park | default-and-disclose | block-and-queue) could fire. The declaration is '
    + 'validated at materialization (goal_cli.py) and read at exactly two places — the chat bridge\'s '
    + 'message gate and, since B1, the attached engine\'s carrier. The daemon lane is not one of '
    + 'them. Filed for a ruling: either the daemon lane REFUSES to dispatch a held seat of an '
    + 'interactive goal, or something must execute the fallback it already requires them to declare.');

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
  const HEADER = require('node:child_process').execFileSync('python3',
    ['-c', 'import sys; sys.path.insert(0, sys.argv[1]); import coord; print(",".join(coord.SESSIONS_COLS))',
      path.join(IGNITE_SRC, 'team-kit')], { encoding: 'utf8' }).trim();
  const FOREIGN_SESSION = '11111111-2222-3333-4444-555555555555';
  const foreignTrace = path.join(foreignGoal, 'sessions.csv');
  const idx = HEADER.split(',');
  const cell = (m) => idx.map((c) => m[c] || '').join(',');
  fs.writeFileSync(foreignTrace, `${HEADER}\n${cell({
    'session-id': FOREIGN_SESSION, seat: 'alpha', harness: 'claude',
    workdir: path.join(foreignGoal, 'seats', 'alpha'), started: isoNow(),
  })}\n`);
  // …and the other lane's OUTCOME, in the shared record, keyed by that same session id.
  record.openExecution({ goalFolder: foreignGoal, seat: 'alpha', sessionId: FOREIGN_SESSION, lane: 'daemon', startedAt: isoNow() });
  record.closeExecution({ goalFolder: foreignGoal, sessionId: FOREIGN_SESSION, outcome: 'done', endedAt: isoNow() });

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
    + 'THIS lane never ran, off the record alone',
    (() => {
      const fresh = path.join(workspace, '.rbtv', 'goals', 'lane-goal-4');
      fs.mkdirSync(path.join(fresh, 'seats', 'alpha'), { recursive: true });
      fs.mkdirSync(path.join(fresh, 'seats', 'bravo'), { recursive: true });
      fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(fresh, 'taskforce.csv'));
      for (const s2 of ['alpha', 'bravo']) fs.copyFileSync(path.join(goalFolder, 'seats', s2, 'seat.md'), path.join(fresh, 'seats', s2, 'seat.md'));
      record.openExecution({ goalFolder: fresh, seat: 'alpha', sessionId: 'ffffffff-0000-0000-0000-000000000001', lane: 'daemon', startedAt: isoNow() });
      record.closeExecution({ goalFolder: fresh, sessionId: 'ffffffff-0000-0000-0000-000000000001', outcome: 'done', endedAt: isoNow() });
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

  finding('D4 THE MEASURED BOUND ON THE DAEMON HALF: `engine.seedGoal` is built and proven (D1), but '
    + 'nothing under server/ CALLS it yet — the daemon picks a goal up when something tells it to, '
    + 'and what tells it is an arming decision this build did not invent. Until that lands, the '
    + 'daemon lane WRITES the record on every tick (D2, publishToRecord) and can seed on demand, but '
    + 'does not adopt goal folders by itself.');

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
      + `what is still open — the daemon's pickup TRIGGER, the fallback gap (D3), and the one case `
      + `the retired guard covered that the record does not.`);
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
