#!/usr/bin/env node
'use strict';

// probe-engine-library — core-build task 7.44's own probe.
//
// WHAT IT PROVES, criterion by criterion:
//
//   C1  the engine core is importable AS A LIBRARY — no daemon process, no gateway, no HTTP — and
//       the DAEMON consumes the same library (asserted at the daemon's own source, not inferred).
//   C2  an attached execution with NO daemon executes a MULTI-SEAT workflow with PARALLEL WAVES and the
//       stall ladder live.
//   C3  kill it mid-run, re-run, and it RESUMES from run-folder state at the correct step.
//   C4  the attached engine's store lands in the GOAL FOLDER and never opens the daemon's
//       {state_root}/heart.db (owner ruling decisions.md#d-attached-run-store-and-seats).
//   SEAM the Windows-degraded lane cannot fall through to a POSIX construct — it is REFUSED, with
//       an error naming all four degraded sites and task 7.84.
//
// ⚠⚠ WHAT THIS PROBE DOES **NOT** PROVE, said here rather than left for a reader to discover
// (`bars.md` 10 — a green obtained in a fixture is a claim about the harness):
//
//   · IT PROVES NOTHING ABOUT WINDOWS. This box is CAGED (bwrap + systemd + tmux all present).
//     The seam checks force the branch with RBTV_IGNITE_SUBSTRATE and assert the REFUSAL. That the
//     refusal fires is a fact about this code; how a degraded BODY behaves is task 7.84's, and
//     nothing here may be read as evidence about it.
//   · THE SEATS IT LAUNCHES ARE `sleep`, NOT HARNESSES. The wave/resume/exit mechanics are
//     exercised against the REAL ticker, the REAL spawn path and a REAL store; the WORK is a
//     throwaway profile. The committed profiles (the 14-profile r-seats-only-architecture roster) are still loaded through the daemon's own
//     config module, so the pinned-and-named property is exercised against the real file.
//
// ⚠ EVERY NEGATIVE HERE CARRIES A POSITIVE CONTROL IN THE SAME RUN (`bars.md` 11 second half):
// each refusal check is paired with a case that must NOT refuse. A refusal that fires
// unconditionally and a refusal that works print the same thing without its control.
//
// ⚠ KNOWN CAPABLE OF A TRANSIENT FALSE-RED UNDER VPS LOAD. Several arms race REAL subprocesses
// against fixed sleeps (250 ms / 300 ms) and hard timeouts (5 s / 20 s / 120 s): C3/C3c's
// kill-and-recover, and C5's `rbtv run` subprocess, which lands `outcome seat-failed` when a
// loaded box eats the margin. Measured red 2026-08-11 at VPS HEAD 8ae0978a, and again that day at
// a74af8f7 (C5) — then GREEN on 3 consecutive re-runs with no code change. Diagnosis:
// environment/timing, not code. Widening any of those budgets is an owner call, not a fix.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { awaitExit } = require('./await-exit');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const OUT_PATH = path.join(__dirname, 'probe-engine-library.out');
const COMMITTED_CONFIG = path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml');

const lines = [];
let passed = 0;
let failed = 0;

function check(name, ok, detail = '') {
  if (ok) { passed += 1; lines.push(`ok    ${name}${detail ? `  — ${detail}` : ''}`); }
  else { failed += 1; lines.push(`FAIL  ${name}${detail ? `  — ${detail}` : ''}`); }
  return ok;
}

function say(s) { lines.push(s); }

// Run `fn` and report whether it threw, and with what. Used by every refusal check AND by its
// control, so both sides are measured the same way.
function attempt(fn) {
  try { const value = fn(); return { threw: false, value }; }
  catch (err) { return { threw: true, err }; }
}

async function attemptAsync(fn) {
  try { const value = await fn(); return { threw: false, value }; }
  catch (err) { return { threw: true, err }; }
}

// ── fixture ───────────────────────────────────────────────────────────────────────────────────
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-engine-library-'));
const workspace = path.join(tmp, 'workspace');
const dataRoot = path.join(tmp, 'data');
// 7.607 E3: GOAL-DIRECT. The attached engine's folder predicate is `.rbtv/goals/<goal>/` now;
// a `runs/run-1` fixture would be refused by the very predicate this probe exercises.
const goalFolder = path.join(workspace, '.rbtv', 'goals', 'probe-goal');
fs.mkdirSync(goalFolder, { recursive: true });
fs.mkdirSync(dataRoot, { recursive: true });

const SEATS = ['alpha', 'bravo', 'charlie'];

// ⚠ A GOAL FOLDER, NOT THREE EMPTY SEAT DIRECTORIES — and the missing half hid for exactly the
// reason the seat folders themselves once did (see C5's note below). `config/spawn-profiles.yaml`
// § SeatBinds carries two sources with NO `-try` suffix — `ro-bind:{seatDir}/seat.md` and
// `bind:{goalDir}/coordination` — and bwrap fails the WHOLE namespace on a missing bind source. So
// every seat this fixture fired died at `bwrap: Can't find source path .../seat.md`, `sleep 1`
// never ran, and C5 returned `max-ticks` (exit 0) or `seat-failed` (exit 1) purely on whether the
// tick bound landed before the exit-condition pass saw the wreckage — a coin flip, not a check:
// 3 red in 6 consecutive hand runs, and 7 red across the 49 retained scheduled runs of
// 2026-08-09..11. Every other arm stayed green throughout, which is why this sat: they measure
// what was ENQUEUED and what the wave decision RELEASED, neither of which needs a seat to survive
// its cage.
//
// `seat.md` is written by the SHIPPED materializer, not by a literal here: it is the same call the
// ticker makes for a job-born seat, so the fixture's descriptor cannot drift from the real one.
const { parseSeatPath, materializeSeatFolder } = require(path.join(IGNITE_SRC, 'server', 'seat-identity', 'seat-folder.js'));
// ⚠ AND THE DESCRIPTOR IS CAST (7.787). `materializeSeatFolder` writes the minimal job-born shape,
// which declares no harness+model — and since `#d-abolish-profile-names` an UNCAST seat is a NAMED
// refusal at every door, so a fixture left that way measures the refusal instead of its subject.
// The cast is appended to the frontmatter the materializer wrote, which is exactly where
// `materialize-seats.py --repass` puts it on a real seat. `castSeats: false` keeps the ONE goal
// that means to be uncast (C5b's negative twin) uncast.
function makeGoalFolder(dir, { castSeats = true } = {}) {
  fs.mkdirSync(path.join(dir, 'coordination'), { recursive: true });
  for (const s of SEATS) {
    materializeSeatFolder(parseSeatPath(path.join(dir, 'seats', s)), { jobId: 'probe-engine-library fixture' });
    if (!castSeats) continue;
    const md = path.join(dir, 'seats', s, 'seat.md');
    fs.writeFileSync(md, fs.readFileSync(md, 'utf8')
      .replace(/^---\n/, '---\nharness: bash\nmodel: probe-seat\n'));
  }
}
makeGoalFolder(goalFolder);

// taskforce.csv in the goals tree's own shape (goal_cli.py write_csv). `after` is the WAVE
// structure: alpha and bravo have none (wave 1), charlie follows alpha (wave 2).
fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'), [
  'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id',
  'tf-probe,alpha,,claude,claude-opus-5,medium,50,m1',
  'tf-probe,bravo,,claude,claude-opus-5,medium,50,m1',
  'tf-probe,charlie,alpha,claude,claude-opus-5,medium,50,m1',
  '',
].join('\n'));

// The throwaway config is the COMMITTED one plus one harmless profile, so the real profiles
// are still loaded through the daemon's own config module (the route that clears G-211) while the
// work a "seat" does is `sleep`.
const yaml = require(path.join(IGNITE_SRC, 'node_modules', 'js-yaml'));
const cfg = yaml.load(fs.readFileSync(COMMITTED_CONFIG, 'utf8'));
// 7.787: the committed roster is `launch-specs:`' (harness, model) KEYS, flattened to
// `<harness>/<model>` by the loader. Collected as pairs here so the C1 check below asks the loader
// for exactly what the document declares — a harness-name-only list would pass on a config that
// lost every model under it.
const committedSpecKeys = Object.entries(cfg['launch-specs'] || {})
  .flatMap(([h, models]) => Object.keys(models || {}).map((m) => `${h}/${m}`));
cfg.spawn = { ...(cfg.spawn || {}), data_root: dataRoot, carrier: 'setsid' };
cfg.default_workdir_root = path.join(tmp, 'work');
fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
// Shaped on the committed `test-sleep` profile — `prompt: stdin` is the ONLY headless carriage
// the shared validator accepts (caller free text never becomes argv, batch-08 item 4). The one
// difference is `workdir_root`, which must cover a SEAT folder: seats live under `.rbtv/goals`,
// which is exactly where the committed `claude-seat` profile points its own root.
// 7.787: `profiles:` is `launch-specs:`, keyed by (harness, model). The `bash -c` shim keeps
// the argv agreeing with the key (`profiles.js#validateSpecKey` refuses a disagreement at
// LOAD) while running exactly what it ran before; the goal's seats declare the matching cast.
// ⚠ MERGED, NOT REPLACED — the committed specs stay, because C1 below asserts they all load
// through the daemon's own config module. Assigning a fresh object here wiped the roster and made
// that check assert over nothing.
cfg['launch-specs'] = { ...(cfg['launch-specs'] || {}), bash: { ...((cfg['launch-specs'] || {}).bash || {}) } };
cfg['launch-specs'].bash['probe-seat'] = {
  exec: { argv: ['bash', '-c', 'exec sleep 1', '--model', 'probe-seat'], prompt: 'stdin' },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  // Declared because the shared validator REQUIRES them of every profile — a profile that
  // declares no containment is refused rather than waved through. They are not enforced under the
  // `setsid` carrier this fixture selects, and this probe claims nothing about containment.
  caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
  sandbox: {
    ProtectSystem: 'strict',
    ReadWritePaths: ['{workdir}'],
    PrivateTmp: true,
    NoNewPrivileges: true,
  },
};
// ⚠ THE TWIN IS GONE AT 7.787, AND ITS REASON WENT WITH IT. `probe-seat-cast` existed because
// `probe-seat` pinned no model and therefore could not be CAST to — a seat with no cast fell back
// to it under D3(a), and C5's fully-cast arm needed something a seat COULD be cast to. Both halves
// are abolished: every spec is keyed by its (harness, model), so `probe-seat` is castable by
// construction, and there is no fallback for the other case to exercise.
const configPath = path.join(tmp, 'spawn-profiles.yaml');
fs.writeFileSync(configPath, yaml.dump(cfg));

const storePath = path.join(goalFolder, 'heart.db');
const daemonStorePath = path.join(dataRoot, 'heart.db');

async function main() {
  say('probe-engine-library — core-build task 7.44');
  say(`fixture: ${tmp}`);
  say('');

  // ── C1 · the engine is a LIBRARY ───────────────────────────────────────────────────────────
  say('C1 — the engine core is importable as a library, and the daemon consumes the SAME one');

  // Loaded in a CHILD process with a clean require cache, so the answer is about the engine's own
  // closure and not about whatever this probe already required.
  const graph = JSON.parse(execFileSync(process.execPath, ['-e', `
    require(${JSON.stringify(path.join(IGNITE_SRC, 'engine'))});
    const loaded = Object.keys(require.cache).map((p) => p.replace(${JSON.stringify(IGNITE_SRC + path.sep)}, ''));
    const builtins = (process.moduleLoadList || []).filter((m) => m.startsWith('NativeModule'));
    console.log(JSON.stringify({ loaded, builtins }));
  `], { encoding: 'utf8' }));

  const gatewayFiles = graph.loaded.filter((f) => f.startsWith('gateway' + path.sep));
  check('C1 the engine loads NO gateway module', gatewayFiles.length === 0,
    gatewayFiles.length ? gatewayFiles.join(', ') : 'zero gateway files in the require closure');

  const apiFiles = graph.loaded.filter((f) => f.includes(`internal-api${path.sep}`));
  check('C1 the engine loads NO internal-api module', apiFiles.length === 0,
    apiFiles.length ? apiFiles.join(', ') : 'zero internal-api files in the require closure');

  const httpLoaded = graph.builtins.some((m) => /NativeModule (node:)?(http|https)$/.test(m));
  check('C1 the engine loads NO http/https builtin', !httpLoaded,
    httpLoaded ? 'http was loaded' : 'neither http nor https in the native module load list');

  // The control that makes the three checks above mean something. It requires the GATEWAY module
  // — not `server/index.js`, which is an ENTRY POINT: requiring it calls main() and tries to boot
  // a daemon, which is both wrong here and dangerous on a box running one. The point of the
  // control is only that the measurement is not blind, and the gateway module answers that
  // exactly: if the same instrument reports zero gateway files even when a gateway IS loaded,
  // then the three absences above are worthless.
  const controlGraph = JSON.parse(execFileSync(process.execPath, ['-e', `
    require(${JSON.stringify(path.join(IGNITE_SRC, 'gateway', 'gateway.js'))});
    const loaded = Object.keys(require.cache).map((p) => p.replace(${JSON.stringify(IGNITE_SRC + path.sep)}, ''));
    const builtins = (process.moduleLoadList || []).filter((m) => m.startsWith('NativeModule'));
    console.log(JSON.stringify({ loaded, builtins }));
  `], { encoding: 'utf8' }));
  const controlGateway = controlGraph.loaded.filter((f) => f.startsWith('gateway' + path.sep));
  const controlHttp = controlGraph.builtins.some((m) => /NativeModule (node:)?http$/.test(m));
  check('C1 POSITIVE CONTROL: the same instrument DOES see a gateway when one is loaded',
    controlGateway.length > 0,
    controlGateway.length ? `${controlGateway.length} gateway file(s) — so the empty results above are real absences`
      : 'the instrument found no gateway even when requiring the gateway: the checks above prove NOTHING');
  check('C1 POSITIVE CONTROL: the same instrument DOES see http when one is loaded',
    controlHttp,
    controlHttp ? 'http appears in the native module load list for the gateway'
      : 'the instrument cannot see http at all, so "no http" above proves NOTHING');

  check('C1 the daemon consumes the engine library (asserted at its source)',
    /require\(['"]\.\.\/engine['"]\)/.test(fs.readFileSync(path.join(IGNITE_SRC, 'server', 'index.js'), 'utf8')),
    "server/index.js requires '../engine'");

  const { createEngine } = require(path.join(IGNITE_SRC, 'engine'));
  const { loadConfig } = require(path.join(IGNITE_SRC, 'server', 'spawn', 'config'));
  const spawnConfig = loadConfig(configPath);
  check('C1 every committed launch spec loads through the daemon\'s own config module, keyed by '
    + 'its (harness, model) pair',
    committedSpecKeys.length > 0 && committedSpecKeys.every((k) => spawnConfig.launchSpecs[k]),
    `pinned + keyed: ${committedSpecKeys.join(', ')}`);

  const noDb = attempt(() => createEngine({ spawnConfigPath: configPath }));
  check('C1 createEngine REFUSES without a dbPath (it never guesses which store it owns)',
    noDb.threw && /dbPath/.test(noDb.err.message), noDb.threw ? noDb.err.message.split('\n')[0] : 'it did not refuse');

  // ── C4 · two store kinds ───────────────────────────────────────────────────────────────────
  say('');
  say('C4 — the store lands in the GOAL FOLDER, and the daemon\'s store is never opened');

  const attached = require(path.join(IGNITE_SRC, 'engine', 'attached-execution.js'));

  const badFolder = attempt(() => attached.resolveGoalFolder(tmp));
  check('C4 a path that is not a goal folder is REFUSED',
    badFolder.threw && /goal folder/.test(badFolder.err.message),
    badFolder.threw ? 'refused' : 'it accepted a non-goal-folder path');
  const goodFolder = attempt(() => attached.resolveGoalFolder(goalFolder));
  check('C4 POSITIVE CONTROL: a real goal folder is ACCEPTED',
    !goodFolder.threw && goodFolder.value === goalFolder,
    goodFolder.threw ? goodFolder.err.message : goodFolder.value);

  const sameStore = attempt(() => attached.assertNotTheDaemonStore(daemonStorePath, spawnConfig));
  check('C4 a store path EQUAL to the daemon\'s is REFUSED',
    sameStore.threw && /never opens/.test(sameStore.err.message),
    sameStore.threw ? 'refused' : 'it accepted the daemon\'s own store path');
  const otherStore = attempt(() => attached.assertNotTheDaemonStore(storePath, spawnConfig));
  check('C4 POSITIVE CONTROL: the goal-folder store is ACCEPTED',
    !otherStore.threw, otherStore.threw ? otherStore.err.message : storePath);

  // The COMMITTED value, not only the fixture's — the guard must be measured against the real
  // per-machine state root this box actually configures, or it only ever guarded a temp dir.
  const committed = yaml.load(fs.readFileSync(COMMITTED_CONFIG, 'utf8'));
  const committedRoot = committed.spawn && committed.spawn.data_root;
  const committedStore = committedRoot ? path.resolve(committedRoot, 'heart.db') : null;
  const againstCommitted = committedStore
    ? attempt(() => attached.assertNotTheDaemonStore(committedStore, committed))
    : { threw: false };
  check('C4 the guard REFUSES the COMMITTED per-machine store path too, not just the fixture\'s',
    Boolean(committedStore) && againstCommitted.threw,
    committedStore ? `${committedStore} refused` : 'the committed config declares no spawn.data_root');

  // ── SEAM · the Windows-degraded lane cannot fall through ───────────────────────────────────
  say('');
  say('SEAM — the Windows-degraded lane REFUSES rather than running POSIX constructs');

  const substrate = require(path.join(IGNITE_SRC, 'engine', 'substrate.js'));
  check('SEAM this box detects as posix', substrate.detectSubstrate({}, 'linux') === 'posix');
  check('SEAM a win32 platform detects as windows', substrate.detectSubstrate({}, 'win32') === 'windows');

  const forced = attempt(() => substrate.assertSubstrateSupported({ RBTV_IGNITE_SUBSTRATE: 'windows' }, 'linux'));
  check('SEAM a forced windows substrate is REFUSED',
    forced.threw && forced.err.code === substrate.E_SUBSTRATE_UNSUPPORTED,
    forced.threw ? `code ${forced.err.code}` : 'it did NOT refuse — the lane would fall through to POSIX');
  const notForced = attempt(() => substrate.assertSubstrateSupported({}, 'linux'));
  check('SEAM POSITIVE CONTROL: a posix substrate is NOT refused',
    !notForced.threw && notForced.value === 'posix',
    notForced.threw ? notForced.err.message.split('\n')[0] : 'posix passed');

  const msg = forced.threw ? forced.err.message : '';
  for (const site of ['carrier', 'tree-kill', 'filesystem-wall', 'seat-room']) {
    check(`SEAM the refusal NAMES the '${site}' site`, msg.includes(site));
  }
  check('SEAM the refusal names the row that owns the branch bodies (7.84)', /7\.84/.test(msg));
  check('SEAM the refusal names the owner ruling', /d-windows-degraded-attached-lane/.test(msg));
  check('SEAM the refusal says the deferral is DELIBERATE',
    /DELIBERATE DEFERRAL/.test(msg),
    '"deliberately deferred" and "nobody thought about Windows" must not render identically');

  const bogus = attempt(() => substrate.detectSubstrate({ RBTV_IGNITE_SUBSTRATE: 'darwin-ish' }, 'linux'));
  check('SEAM an unknown substrate value is REFUSED, never silently treated as posix', bogus.threw);

  const seamOnRun = await attemptAsync(() => attached.executeAttached({
    goalFolder, profile: 'probe-seat', spawnConfigPath: configPath, maxTicks: 1,
  }));
  const hadEnv = 'RBTV_IGNITE_SUBSTRATE' in process.env;
  process.env.RBTV_IGNITE_SUBSTRATE = 'windows';
  const seamBlocked = await attemptAsync(() => attached.executeAttached({
    goalFolder, profile: 'probe-seat', spawnConfigPath: configPath, maxTicks: 1,
  }));
  if (!hadEnv) delete process.env.RBTV_IGNITE_SUBSTRATE;
  check('SEAM executeAttached itself refuses on a non-POSIX host, BEFORE opening any store',
    seamBlocked.threw && seamBlocked.err.code === substrate.E_SUBSTRATE_UNSUPPORTED,
    seamBlocked.threw ? `code ${seamBlocked.err.code}` : 'the run proceeded on a windows substrate');
  // ⚠ THIS CONTROL WAS WEAK WHEN FIRST WRITTEN AND THE PROBE CAUGHT IT ON ITSELF. It asked only
  // that the posix call not throw E_SUBSTRATE_UNSUPPORTED — so it PASSED while the run was in
  // fact dying of an unrelated bug (a malformed args_schema), reporting a healthy control over a
  // broken run. That is `bars.md` 11's MISGRADING shape: it ran, and its result was read wrong.
  // It now demands the posix run actually SUCCEED, which is the only thing that makes the refusal
  // above evidence about the SUBSTRATE rather than evidence that everything throws.
  check('SEAM POSITIVE CONTROL: the same call on this posix box SUCCEEDS (not merely "throws differently")',
    !seamOnRun.threw && Boolean(seamOnRun.value) && seamOnRun.value.host === 'posix',
    seamOnRun.threw ? `it threw: ${String(seamOnRun.err.message).split('\n')[0]}` : `outcome ${seamOnRun.value.outcome}, host ${seamOnRun.value.host}`);

  // ── C2 · a multi-seat run with parallel waves, and no daemon anywhere ───────────────────────
  say('');
  say('C2 — a multi-seat workflow, parallel waves, the stall ladder live, NO daemon');

  check('C2 the store landed in the GOAL FOLDER', fs.existsSync(storePath), storePath);
  check('C2 no store was created at the daemon\'s data root', !fs.existsSync(daemonStorePath),
    `${daemonStorePath} absent`);

  const { openHeartStore } = require(path.join(IGNITE_SRC, 'server', 'heart', 'heart-store'));
  const inspect = openHeartStore({ dbPath: storePath, profiles: spawnConfig.profiles });
  const all = inspect.dump();
  const firedJobs = new Set(all.jobs_log.map((r) => r.job_id));

  check('C2 all three seats were registered as jobs',
    SEATS.every((s) => all.jobs.some((j) => j.job_id === `seat-${s}`)),
    all.jobs.map((j) => j.job_id).join(', '));

  check('C2 WAVE 1 fired IN PARALLEL — both dependency-free seats, from ONE tick',
    firedJobs.has('seat-alpha') && firedJobs.has('seat-bravo'),
    `fired: ${[...firedJobs].join(', ') || 'none'}`);
  check('C2 WAVE 2 did NOT fire — charlie waits on alpha (`after`), which has not finished',
    !firedJobs.has('seat-charlie'),
    'the wave structure is the taskforce\'s `after` column, honoured');


  // The stall ladder is not a separate build: it rides in with createTicker. Assert it is LIVE in
  // THIS engine's config rather than that the constant exists somewhere.
  const tickerSrc = fs.readFileSync(path.join(IGNITE_SRC, 'server', 'ticker', 'ticker.js'), 'utf8');
  check('C2 the stall ladder is the ticker\'s, and the attached lane gets the ticker',
    /stall_warn_ticks/.test(tickerSrc) && /stall_halt_ticks/.test(tickerSrc)
      && all.ticks.length > 0,
    `${all.ticks.length} tick(s) recorded by the attached engine, with no daemon running`);

  // ── C2/C3 · the exit conditions, read from the store ────────────────────────────────────────
  say('');
  say('C3 — the exit conditions, and RESUME from run-folder state');

  const rows = [{ seat: 'alpha', after: '' }, { seat: 'bravo', after: '' }, { seat: 'charlie', after: 'alpha' }];

  // ⚠ THE LIVE TURN IS PINNED, NOT HOPED FOR (task 7.629, the C3 half). This arm used to evaluate
  // the exit predicate against whatever the C2 run happened to have left running — and what it left
  // running is a `sleep 1` child racing every line between the run's return and this call. It went
  // red whenever the box was busy enough for the sleep to win (measured red 2/8 under load at the
  // commit before the execution record, and more often after it, because ANY work added to the run
  // lengthens that gap). The property under test is `evaluateExit`'s, not the sleep's: so a live
  // turn is CREATED here, on the real fixture store, and removed again immediately — the predicate
  // still runs against a real store with a real non-terminal row, and the arm can no longer be
  // decided by a timer. (C3c's own race is the same family and is fixed separately by 7.629.)
  inspect.registerJob({
    jobId: 'probe-live-pin', actionType: 'launch-agent',
    argsSchema: JSON.stringify({ required: {}, optional: {} }),
    function: 'a turn pinned live for the exit predicate', description: 'C3 pin',
    createdAt: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    updatedAt: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
  });
  const pinned = inspect.recordExecutionStart({
    jobId: 'probe-live-pin', actionType: 'launch-agent',
    args: JSON.stringify({}), enqueuedBy: 'probe',
    sessionMode: 'headless', firedTick: 1, firedAt: new Date(),
  });
  const midRun = attached.evaluateExit(inspect, rows);
  check('C3 with turns still live the run does NOT exit', !midRun.done,
    `live=${midRun.live}`);
  // Unpinned before anything else reads this store, so no later arm inherits a live row.
  inspect.endTurnAndCloseSession(pinned.exec_id, {
    turnStatus: 'failed', sessionStatus: 'crashed', endedAt: new Date(), reason: 'C3 pin released',
  });
  check('C3 …and the pin is RELEASED — no later arm inherits a live turn from this one',
    attached.evaluateExit(inspect, rows).done !== false
      || !inspect.listExecutionsByStatus('launching').some((r) => r.job_id === 'probe-live-pin'),
    'the pinned row is terminal again');

  const stamp = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  inspect.recordMessage({
    type: 'ask', sender: 'alpha', thread: 'probe', corpus: 'a worker question', createdAt: stamp(),
  });
  const onAsk = attached.evaluateExit(inspect, rows);
  check('C3 ANY worker question ends the attached execution and returns it to the caller',
    onAsk.done && onAsk.reason === 'question' && onAsk.asks.length === 1,
    onAsk.done ? `reason=${onAsk.reason}, ${onAsk.asks.length} ask(s)` : 'the run did not return on a question');

  // ⚠ REWRITTEN, console-run B1. The old control passed the ask's own id back in a `seenAskIds`
  // set — and NOTHING in the run loop ever put an id in that set, so the control proved a property
  // the product did not have: a run resumed after ANY ask ever recorded handed back exit 3 at its
  // first tick, on a question that may have been answered while it was down. The correlation is now
  // the ANSWER, which is what actually closes a question, and it is the status verb's own pairing.
  inspect.recordMessage({
    type: 'answer', sender: 'owner', thread: 'probe', corpus: 'here is your answer', createdAt: stamp(),
  });
  const afterAnswer = attached.evaluateExit(inspect, rows);
  check('C3 an ANSWERED question does not end the run again',
    !(afterAnswer.done && afterAnswer.reason === 'question'),
    'else a resumed run would exit immediately, forever, on a question already answered');
  // …and a SECOND, still-open question on the same thread does stop it — so the arm above is
  // measuring the pairing and not "any answer anywhere silences everything".
  inspect.recordMessage({
    type: 'ask', sender: 'alpha', thread: 'probe', corpus: 'a second, unanswered question', createdAt: stamp(),
  });
  const secondAsk = attached.evaluateExit(inspect, rows);
  check('C3 a SECOND unanswered ask on the same thread still ends the run',
    secondAsk.done && secondAsk.reason === 'question'
      && secondAsk.asks.length === 1 && /second/.test(secondAsk.asks[0].corpus),
    JSON.stringify(secondAsk.asks || []));
  inspect.recordMessage({
    type: 'answer', sender: 'owner', thread: 'probe', corpus: 'answered too', createdAt: stamp(),
  });
  inspect.close();

  // ⚠⚠ THE TWO CHECKS ABOVE WERE THE ONLY EVIDENCE FOR WAVES AND THEY WERE BLIND. A mutation run
  // that DELETED the `after` gate entirely still passed them: `max_live_agent_sessions` is 2, so
  // charlie could not have fired in that tick whatever the gate did. The check could not tell
  // "the dependency held charlie back" from "the session cap held charlie back" — `bars.md` 11's
  // first shape, a check that cannot fail, hiding inside a green.
  //
  // So the wave decision is now measured WHERE IT IS MADE: `enqueueEligible` returns the seats it
  // releases, against a store whose state this probe sets deliberately. Nothing here depends on
  // the cap, on timing, or on what a tick happened to dispatch.
  say('');
  say('C2b — the WAVE DECISION itself, measured at the point it is made (not at what fired)');

  const waveDir = path.join(workspace, '.rbtv', 'goals', 'wave-goal');
  // The seat DESCRIPTORS, from the shipped materializer as above — `coordinate ready-seats` calls a
  // seat with no descriptor UNBUILT and offers it to nobody, and this fixture's whole subject is
  // which seats get offered.
  makeGoalFolder(waveDir);
  fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(waveDir, 'taskforce.csv'));
  const waveStore = openHeartStore({ dbPath: path.join(waveDir, 'heart.db'), profiles: spawnConfig.profiles });
  const waveRows = attached.seedTaskforce(waveStore, waveDir, { profile: 'probe-seat' });
  // ⚠ THE FRONTIER IS COORD'S SINCE § D1 (`one-readiness-predicate.md`): `enqueueEligible` no
  // longer evaluates the `after` column at all — it takes the READY set and subtracts what this
  // store has already registered, queued or fired. So every pass below hands it a FRESHLY READ
  // frontier, and what these arms measure is the STORE half: the no-double-fire guard.
  const { readySeats } = require('../seeding');
  const frontier = () => { const r = readySeats(waveDir); return { ready: r.ready, readyRows: r.rows }; };
  // The seat's own CHECK-OUT — the only thing that advances an edge now. `sessions.csv` is the
  // surface `coord.py#session_disposition` reads, and the shape is its own `SESSIONS_COLS`.
  const SESSIONS_HEADER = 'session-id,seat,harness,native-session-id,workdir,recorded,started,ended,'
    + 'pid,pid-starttime,tty,disposition,disposition-writer,execution,checkin,model\n';
  function checkOut(dir, seat, disposition) {
    const f = path.join(dir, 'sessions.csv');
    if (!fs.existsSync(f)) fs.writeFileSync(f, SESSIONS_HEADER);
    fs.appendFileSync(f, `sid-${seat},${seat},claude,,,,2026-08-11T10:00Z,2026-08-11T10:05Z,,,,`
      + `${disposition},${disposition ? 'seat' : ''},,,\n`);
  }

  const wave1 = attached.enqueueEligible(waveStore, waveRows, { profile: 'probe-seat', goalFolder: waveDir, ...frontier() });
  check('C2b WAVE 1 releases BOTH dependency-free seats and NOTHING else',
    wave1.length === 2 && wave1.includes('alpha') && wave1.includes('bravo'),
    `released: [${wave1.join(', ')}]`);
  check('C2b charlie is HELD by its `after`, and this cannot be confused with the session cap',
    !wave1.includes('charlie'),
    'the cap dispatches; the `after` column decides eligibility, and this reads eligibility');

  const wave1Again = attached.enqueueEligible(waveStore, waveRows, { profile: 'probe-seat', goalFolder: waveDir, ...frontier() });
  check('C2b a second pass releases NOTHING — an already-queued seat is never double-enqueued',
    wave1Again.length === 0, `released: [${wave1Again.join(', ')}]`);

  // Advance the store BY HAND to the state a finished alpha produces, so the wave-2 release is
  // observed for the one reason under test.
  waveStore.dump().queue.forEach((q) => {
    if (q.job_id === 'seat-alpha' || q.job_id === 'seat-bravo') waveStore.removeQueueRow({ queueId: q.queue_id });
  });
  const nowIso = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const alphaExec = waveStore.recordExecutionStart({
    jobId: 'seat-alpha', actionType: 'launch-agent', args: '{}', enqueuedBy: 'probe',
    sessionMode: 'headless', firedTick: 1, firedAt: nowIso,
  });
  const wave2Blocked = attached.enqueueEligible(waveStore, waveRows, { profile: 'probe-seat', goalFolder: waveDir, ...frontier() });
  check('C2b POSITIVE CONTROL: with alpha merely RUNNING, charlie is STILL held',
    !wave2Blocked.includes('charlie'),
    '`after` means finished, not started — else wave 2 would race wave 1');

  waveStore.updateExecutionStatus(alphaExec.exec_id, { status: 'done', endedAt: nowIso });
  // …AND alpha CHECKS OUT. The turn status above is a fact about a PROCESS and advances nothing
  // since § D1; the check-out beside it is the seat's own declaration, and it is what moves the
  // edge. The pair is deliberate: with the turn alone, charlie stays held (arm below).
  const heldWithoutCheckout = attached.enqueueEligible(waveStore, waveRows, { profile: 'probe-seat', goalFolder: waveDir, ...frontier() });
  check('C2b a DONE TURN alone does not release charlie — an exit code is not a check-out',
    !heldWithoutCheckout.includes('charlie'),
    `released: [${heldWithoutCheckout.join(', ')}]`);
  checkOut(waveDir, 'alpha', 'done');
  const wave2 = attached.enqueueEligible(waveStore, waveRows, { profile: 'probe-seat', goalFolder: waveDir, ...frontier() });
  check('C2b WAVE 2 releases charlie ONCE alpha is done, and only charlie',
    wave2.length === 1 && wave2[0] === 'charlie',
    `released: [${wave2.join(', ')}]`);

  // ── C3b · RESUME, isolated from the "already queued" guard ────────────────────────────────
  //
  // ⚠ THIS CHECK ALSO HAD TO BE REWRITTEN, for the same family of reason as C2b. The first
  // version asked only that a repeat pass release nothing — and a mutant that DELETED the
  // has-already-run guard entirely still passed it, because by then every seat was sitting in the
  // QUEUE and the queued-guard caught them all. Two guards, one observation: the check could not
  // say which one was doing the work, so it certified a guard that was gone.
  //
  // The state below is built so ONLY the has-already-run guard can produce the answer: the queue
  // is EMPTIED first, and both wave-1 seats are given real execution rows. A seat that has run and
  // is not queued must still not be released — that is exactly what makes a re-run a resume.
  for (const q of waveStore.dump().queue) waveStore.removeQueueRow({ queueId: q.queue_id });
  const bravoExec = waveStore.recordExecutionStart({
    jobId: 'seat-bravo', actionType: 'launch-agent', args: '{}', enqueuedBy: 'probe',
    sessionMode: 'headless', firedTick: 1, firedAt: nowIso,
  });
  waveStore.updateExecutionStatus(bravoExec.exec_id, { status: 'done', endedAt: nowIso });
  check('C3b the queue is EMPTY, so the queued-guard cannot answer for the has-run guard',
    waveStore.listQueue().length === 0, 'the two guards are now separable');

  const dupes = attached.enqueueEligible(waveStore, waveRows, { profile: 'probe-seat', goalFolder: waveDir, ...frontier() });
  check('C3b RESUME: seats that already RAN are NOT re-enqueued, even with an empty queue',
    !dupes.includes('alpha') && !dupes.includes('bravo'),
    dupes.length ? `released [${dupes.join(', ')}]` : 'released nothing');
  check('C3b POSITIVE CONTROL: a seat that has NOT run is still released from the same call',
    dupes.includes('charlie'),
    'else "nothing was re-enqueued" would also be true of a call that releases nothing at all');
  waveStore.close();

  // RESUME: a second boot must re-enqueue NOTHING that already ran. This is criterion 3's whole
  // mechanism — the state is in the goal folder, so re-running the verb continues rather than
  // restarts.
  const second = await attemptAsync(() => attached.executeAttached({
    goalFolder, profile: 'probe-seat', spawnConfigPath: configPath, maxTicks: 1,
  }));
  check('C3 a SECOND run of the same folder boots without error (resume, not replay)',
    !second.threw, second.threw ? second.err.message.split('\n')[0] : `outcome ${second.value.outcome}`);
  if (!second.threw) {
    check('C3 the second run RESUMED at the tick the first left, not at tick 1',
      second.value.resumedAtTick >= 1,
      `resumed at tick ${second.value.resumedAtTick}, now ${second.value.tick}`);
  }

  const after2 = openHeartStore({ dbPath: storePath, profiles: spawnConfig.profiles });
  const execsPerJob = {};
  for (const r of after2.dump().jobs_log) execsPerJob[r.job_id] = (execsPerJob[r.job_id] || 0) + 1;
  after2.close();
  check('C3 no seat was fired twice by the resume',
    Object.values(execsPerJob).every((n) => n === 1),
    Object.entries(execsPerJob).map(([k, v]) => `${k}=${v}`).join(', ') || 'nothing fired');

  // ── C5 · the CONSUMER surface, exercised as a real subprocess ──────────────────────────────
  //
  // Everything above calls the library directly. `bars.md` 10: verify at the artifact the CONSUMER
  // reads, in the environment it runs in. The consumer is `rbtv run`, and a route that resolves,
  // a delegate that is executable, and an engine path that actually resolves from the tool's own
  // location are three separate things a library-level green says nothing about. The path bug in
  // this very tool (one `..` too many) was invisible to every check above and fell out of running
  // it once.
  say('');
  say('C5 — the `rbtv run` verb itself, as a real subprocess');

  const RBTV_BIN = path.resolve(IGNITE_SRC, '..', 'core', 'capabilities', 'rbtv-cli', 'tool', 'rbtv');
  const runCli = (args) => {
    const res = require('node:child_process').spawnSync(RBTV_BIN, args, { encoding: 'utf8', timeout: 120000 });
    return { status: res.status, stdout: res.stdout || '', stderr: res.stderr || '' };
  };

  check('C5 the rbtv delegate is present AND executable (a permission bit is invisible to a content check)',
    (() => { try { fs.accessSync(path.join(IGNITE_SRC, 'capabilities', 'attached-execution', 'tool', 'rbtv-execution'), fs.constants.X_OK); return true; } catch { return false; } })(),
    'asserted with X_OK, never inferred from the file existing — `bars.md` 9');

  const helpRes = runCli(['run', '--help']);
  check('C5 `rbtv run --help` resolves through the CLI and exits 0',
    helpRes.status === 0 && /goal-folder/.test(helpRes.stdout),
    `exit ${helpRes.status}`);

  const cliDir = path.join(workspace, '.rbtv', 'goals', 'cli-goal');
  // ⚠ THE WHOLE GOAL FOLDER, and it is not decoration. A seat's workdir is its own folder; without
  // one every fire of this fixture REFUSED at the workdir guard and the rows landed `failed`. That
  // was invisible while `--max-ticks 1` returned first and reported `max-ticks` over the wreckage
  // — the outcome word said "the bound was reached", never "every seat failed". Console-run B1's
  // `seat-failed` verdict returns before the bound and made it visible. The SAME defect then sat
  // one layer deeper for weeks — the folders existed, the CAGE's `seat.md` and `coordination`
  // sources did not — and `makeGoalFolder` is where that half is fixed; it is what makes this arm
  // measure a real advance instead of a coin flip between the two outcome words.
  makeGoalFolder(cliDir);
  fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(cliDir, 'taskforce.csv'));
  const cliRes = runCli(['run', cliDir, '--config', configPath, '--max-ticks', '1', '--json']);
  let cliJson = null;
  try { cliJson = JSON.parse(cliRes.stdout); } catch { /* reported by the check below */ }
  check('C5 a REAL `rbtv run` advances the run and emits a machine-readable result',
    cliRes.status === 0 && cliJson && cliJson.host === 'posix',
    cliJson ? `exit ${cliRes.status}, outcome ${cliJson.outcome}` : `exit ${cliRes.status}: ${cliRes.stderr.split('\n')[0]}`);
  check('C5 the store it created is IN THE GOAL FOLDER, reached through the CLI',
    fs.existsSync(path.join(cliDir, 'heart.db')),
    path.join(cliDir, 'heart.db'));

  // ── C5b · AN UNCAST SEAT IS A NAMED REFUSAL (`#d-abolish-profile-names` sub-ruling 3) ───────
  //
  // ⚠ THE SUBJECT SURVIVED TWO RULINGS AND THIS IS THE THIRD SHAPE. It first asserted that
  // `--profile` was demanded UNCONDITIONALLY; the D19 narrowing made it conditional on a seat
  // that would read it; 7.787 removed the flag and the fallback entirely, so the condition is now
  // the refusal itself. The two-goal pairing is what carries the intent through all three: a
  // one-sided arm cannot tell "refuses everything" from "refuses the right thing".
  //
  // The two goals differ in ONE byte-level fact and nothing else: whether their `seat.md` files
  // declare a cast. `cli-goal`'s seats are the ones `materializeSeatFolder` writes — descriptor,
  // no `harness:`/`model:` — so they are UNCAST and the verb must refuse, naming them.
  // `cast-goal`'s seats are the same folders with a cast appended, so the run proceeds.
  // C5b's UNCAST twin gets its OWN FRESH goal — `cliDir` has already been advanced by C5 above,
  // so its store carries rows and the run would be held by those before the cast gate is reached.
  const uncastDir = path.join(workspace, '.rbtv', 'goals', 'uncast-goal');
  makeGoalFolder(uncastDir, { castSeats: false });
  fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(uncastDir, 'taskforce.csv'));
  const noProfile = runCli(['run', uncastDir, '--config', configPath, '--max-ticks', '1']);
  check('C5b `rbtv run` on a goal whose seats declare NO cast REFUSES, and NAMES them',
    noProfile.status === 1 && /no harness\+model cast/.test(noProfile.stderr)
      && SEATS.every((s) => noProfile.stderr.includes(s)),
    `exit ${noProfile.status}: ${noProfile.stderr.split('\n')[0].slice(0, 160)}`);

  const castDir = path.join(workspace, '.rbtv', 'goals', 'cast-goal');
  makeGoalFolder(castDir);
  fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(castDir, 'taskforce.csv'));
  for (const s of SEATS) {
    const md = path.join(castDir, 'seats', s, 'seat.md');
    // Into the FRONTMATTER, where `spawn.js#seatDeclaresValue` reads it — appending to the body
    // would leave the seats uncast and the arm would pass for the wrong reason.
    fs.writeFileSync(md, fs.readFileSync(md, 'utf8')
      .replace(/^---\n/, '---\nharness: bash\nmodel: probe-seat\n'));
  }
  const castRes = runCli(['run', castDir, '--config', configPath, '--max-ticks', '1']);
  check('C5b …and a FULLY CAST goal is not refused — the run proceeds and opens the store',
    !/no harness\+model cast/.test(castRes.stderr) && fs.existsSync(path.join(castDir, 'heart.db')),
    `exit ${castRes.status}: ${(castRes.stderr.split('\n').find((l) => /profile/.test(l)) || 'no profile line').slice(0, 160)}`);

  // ── C3c · KILLED MID-RUN, then re-run — criterion 3's literal words ────────────────────────
  //
  // Criterion 3 says "kill the terminal mid-run, re-run the verb, and the run RESUMES from
  // run-folder state at the correct step (PROVEN BY DOING IT)". Every resume check above re-enters
  // the function; none of them kills a process. A run that dies by SIGKILL never runs a shutdown
  // path, never closes its store, and leaves whatever WAL state it left — which is the whole
  // question, and the only way to ask it is to do it.
  say('');
  say('C3c — SIGKILLed mid-run, then re-run (criterion 3, done rather than approximated)');

  const killDir = path.join(workspace, '.rbtv', 'goals', 'kill-goal');
  makeGoalFolder(killDir);
  fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(killDir, 'taskforce.csv'));

  const { spawn: spawnProc, spawnSync } = require('node:child_process');
  // ⚠ `detached: true`, and the signal below goes to the PROCESS GROUP. `rbtv` is a wrapper that
  // spawns the delegate: a SIGKILL aimed at the wrapper's pid alone leaves the REAL runner alive,
  // so what this section used to measure as "a resume" was a SECOND RUNNER starting on a goal the
  // first still held. Found by console-run B1's run lock, which refused it out loud.
  const victim = spawnProc(RBTV_BIN,
    ['run', killDir, '--config', configPath, '--tick-ms', '500'],
    { stdio: 'ignore', detached: true });

  // Wait until the run has actually STARTED something — killing before the first tick would prove
  // only that an empty store reopens. ⚠ POLL ON THE TICK ROW, not only on the execution rows
  // (task 7.629): execution rows are written DURING a tick, so a SIGKILL landing between the fire
  // and the tick-row COMMIT leaves `getLastTick()` at 0 and the resume check below reads
  // "resumed at tick 0 -> 1" — a red that measured the probe's own race, not the engine. The
  // resume assertion needs `resumedAtTick >= 1`, i.e. a committed row in `ticks`, so that is what
  // the kill waits for. Same bound as before; if it expires without a tick row the check below
  // goes RED on its own precondition instead of mis-blaming the resume.
  const killStore = path.join(killDir, 'heart.db');
  let firedBeforeKill = 0;
  let tickBeforeKill = 0;
  for (let i = 0; i < 60 && !(firedBeforeKill > 0 && tickBeforeKill >= 1); i += 1) {
    spawnSync(process.execPath, ['-e', 'setTimeout(()=>{},250)'], { timeout: 5000 });
    if (fs.existsSync(killStore)) {
      const peek = spawnSync(process.execPath, ['-e', `
        const { openHeartStore } = require(${JSON.stringify(path.join(IGNITE_SRC, 'server', 'heart', 'heart-store'))});
        const s = openHeartStore({ dbPath: ${JSON.stringify(killStore)} });
        const d = s.dump();
        process.stdout.write(JSON.stringify({
          fired: d.jobs_log.length,
          tick: d.ticks.length ? d.ticks[d.ticks.length - 1].tick : 0,
        })); s.close();
      `], { encoding: 'utf8', timeout: 20000 });
      try {
        const seen = JSON.parse(peek.stdout);
        firedBeforeKill = seen.fired;
        tickBeforeKill = seen.tick;
      } catch { /* store mid-write or not yet readable — the loop retries */ }
    }
  }

  try { process.kill(-victim.pid, 'SIGKILL'); } catch { victim.kill('SIGKILL'); }
  const { code: killCode, signal: killSignal } = await awaitExit(victim);
  const killedCleanly = killSignal === 'SIGKILL' || killCode !== 0;
  await new Promise((r) => setTimeout(r, 300));

  check('C3c the attached run was KILLED mid-run, with work already fired AND a tick committed',
    killedCleanly && firedBeforeKill > 0 && tickBeforeKill >= 1,
    `${firedBeforeKill} execution row(s) and last committed tick ${tickBeforeKill} when SIGKILL landed`);

  const afterKill = runCli(['run', killDir, '--config', configPath, '--max-ticks', '1', '--json']);
  let resumeJson = null;
  try { resumeJson = JSON.parse(afterKill.stdout); } catch { /* reported below */ }
  check('C3c re-running the verb after the kill RESUMES — it does not restart at tick 1',
    Boolean(resumeJson) && resumeJson.resumedAtTick >= 1,
    resumeJson ? `resumed at tick ${resumeJson.resumedAtTick} -> ${resumeJson.tick}`
      : `no result: ${afterKill.stderr.split('\n')[0]}`);

  const postKill = spawnSync(process.execPath, ['-e', `
    const { openHeartStore } = require(${JSON.stringify(path.join(IGNITE_SRC, 'server', 'heart', 'heart-store'))});
    const s = openHeartStore({ dbPath: ${JSON.stringify(killStore)} });
    const counts = {};
    for (const r of s.dump().jobs_log) counts[r.job_id] = (counts[r.job_id] || 0) + 1;
    process.stdout.write(JSON.stringify(counts)); s.close();
  `], { encoding: 'utf8', timeout: 20000 });
  const counts = JSON.parse(postKill.stdout || '{}');
  check('C3c no seat was fired twice across the kill — the resume continued, it did not replay',
    Object.values(counts).every((n) => n === 1) && Object.keys(counts).length > 0,
    Object.entries(counts).map(([k, v]) => `${k}=${v}`).join(', ') || 'nothing fired');

  // ⚠ THE ARM THAT STOOD HERE IS UNSPELLABLE (7.787): it passed `--profile <not-in-the-config>`
  // and required "unknown launch profile". `#d-abolish-profile-names` deleted the flag, so the
  // typo it guarded cannot be typed. What replaces it is the same class of refusal one surface
  // down — a seat cast to a pair NO launch spec carries — planted here so the verb is still
  // proven to refuse rather than compose a launch out of something it cannot resolve.
  const ghostDir = path.join(workspace, '.rbtv', 'goals', 'ghost-cast-goal');
  makeGoalFolder(ghostDir);
  fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(ghostDir, 'taskforce.csv'));
  for (const s of SEATS) {
    const md = path.join(ghostDir, 'seats', s, 'seat.md');
    fs.writeFileSync(md, fs.readFileSync(md, 'utf8').replace(/^model: .*$/m, 'model: no-such-model-9'));
  }
  const cliUnknownCast = runCli(['run', ghostDir, '--config', configPath, '--max-ticks', '1']);
  // ⚠ THE CLAIM IS ABSENCE OF A LAUNCH, ASSERTED ON THE RECORD — not on message text. A refusal
  // that printed the right words while still starting a session would be the defect; a refusal
  // whose wording moves would redden a text match for nothing. So the arm reads the goal's own
  // execution record: NO seat finished, and the run did not report success.
  const ghostRecord = (() => {
    const f = path.join(ghostDir, 'executions.csv');
    if (!fs.existsSync(f)) return [];
    return fs.readFileSync(f, 'utf8').trim().split('\n').slice(1).filter(Boolean);
  })();
  // ⚠ THE TEST IS "ANY STAMPED OUTCOME", NOT A WORD (W2). It read `/,done,|,done$/`, and after the
  // outcome column narrowed to the process vocabulary `clean|crashed|killed` that pattern could
  // never match — so the arm would have reported `done=0` for a goal that ran every seat, and
  // passed forever. The claim here is ABSENCE OF A LAUNCH, and the record's own way of saying a
  // launch ended is a non-empty last cell, whatever the word in it.
  const ghostDone = ghostRecord.filter((r) => /,[a-z]+$/.test(r.trim()));
  check('C5 a cast NO launch spec carries is refused, and NOTHING of that goal ran — the verb never '
    + 'composes a launch out of a pair it cannot resolve',
    cliUnknownCast.status !== 0 && ghostDone.length === 0,
    `exit ${cliUnknownCast.status} · record rows=${ghostRecord.length} stamped=${ghostDone.length}`);

  // ── verdict ────────────────────────────────────────────────────────────────────────────────
  say('');
  say(`${passed} passed, ${failed} failed, ${passed + failed}/${passed + failed} checks run`);
  say('');
  say('NOT PROVEN HERE, deliberately: anything about Windows (this box is caged — the seam checks');
  say('force the branch and assert the REFUSAL, which says nothing about a degraded body); and the');
  say('seats launched are `sleep`, not harnesses — the wave/resume/exit mechanics are real, the');
  say('WORK is a fixture.');
}

main()
  .then(() => {
    const text = lines.join('\n') + '\n';
    process.stdout.write(text);
    fs.writeFileSync(OUT_PATH, text);
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch { /* fixture cleanup is best-effort */ }
    process.exit(failed ? 1 : 0);
  })
  .catch((err) => {
    lines.push(`FAIL  probe crashed: ${err.stack || err.message}`);
    const text = lines.join('\n') + '\n';
    process.stdout.write(text);
    fs.writeFileSync(OUT_PATH, text);
    process.exit(1);
  });
