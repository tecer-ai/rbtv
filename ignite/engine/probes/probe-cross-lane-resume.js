#!/usr/bin/env node
'use strict';

// probe-cross-lane-resume — console-run wave B, item B3 (owner asked 2026-08-10).
//
// THE QUESTION: a goal run partially in the ATTACHED lane and then picked up by the DAEMON lane —
// and the reverse. Does create-only seeding from the goal folder hold across the two per-lane
// `heart.db` stores? And what becomes of a human-interactive seat on the daemon side, where there
// is no terminal for it to reach?
//
// ⚠⚠ THE ANSWER THIS PROBE MEASURES IS A NEGATIVE ONE, and it is filed rather than dressed up:
// **cross-lane resume does not hold today.** Create-only seeding is create-only WITHIN A STORE, and
// the two lanes keep two disjoint stores (CMP-2 § Two store kinds) with no lane-independent
// execution record in the goal folder between them. Each direction below is measured, and the one
// that cannot be run in a daemon-less fixture says exactly where it stops rather than being faked.
//
// WHAT IS SUBSTITUTED, disclosed up front (`bars.md` 10):
//   · No daemon runs here. Direction 1's daemon-side pickup is measured STRUCTURALLY — at the one
//     function that seeds a taskforce, and at its call sites — because the behavioural half needs a
//     live daemon, a gateway and an ARMED `coordination/edge-fastpath.json`, none of which a probe
//     may stand up. That boundary is REPORTED, not papered over.
//   · Direction 2's daemon-side history is SYNTHESIZED into the daemon store under the ATTACHED
//     lane's own job-id spelling (`seat-<name>`) — the most generous assumption available, since
//     the daemon's seat sessions are not keyed by seat name at all. The finding survives the
//     generosity, which is the point of granting it.

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
  check('D1 …and since S-18 the ENGINE reads it too — the refusal below is that read',
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

  const daemonStore = openHeartStore({ dbPath: daemonStorePath, profiles: cfg.profiles });
  const daemonKnows = daemonStore.dump().jobs_log.filter((r) => /^seat-/.test(r.job_id));
  check('D1 the DAEMON lane\'s store knows NOTHING of what the attached lane did',
    daemonKnows.length === 0,
    `${daemonKnows.length} seat row(s) in ${daemonStorePath}`);

  // The structural half, through the enumerator rather than a guess: what could seed a daemon
  // store from this goal's taskforce? Exactly one function does that seeding, and its only
  // non-probe call site is the attached lane's own boot.
  const seeders = filesMatching(/seedTaskforce\s*\(/);
  check('D1 ONE function seeds a taskforce, and ONLY the attached lane calls it',
    seeders.join() === 'engine/attached-execution.js', seeders.join(', ') || 'none');
  finding('D1 the daemon lane has NO path that seeds a goal\'s taskforce into its own store, so a '
    + 'goal half-run attached cannot be "picked up" by the daemon at all — the pickup is not '
    + 'degraded, it is absent. What the daemon lane advances is a QUEUE (armed edge-fastpath rows, '
    + 'the goal-watcher), never a taskforce.');
  say('MEASURED REFUSAL — D1\'s behavioural half stops HERE, and this is exactly where: exercising a');
  say('  daemon-side pickup needs a live daemon unit, its gateway, and an ARMED');
  say('  <goal>/coordination/edge-fastpath.json. A probe may stand up none of the three (arming is');
  say('  per-package and deliberately unreachable from an env var or a flag — edge-runner-job.py).');
  say('  So the claim above is made at the seeding function, which is where the pickup would have to');
  say('  happen, and no behavioural claim about the daemon lane is made from this fixture.');

  // ── D2 · DAEMON first, then the attached lane ───────────────────────────────────────────────
  say('');
  say('D2 — a seat already finished on the DAEMON side, then the goal is run ATTACHED');

  // Synthesized under the ATTACHED lane's OWN job-id spelling — the most generous assumption
  // available. If create-only seeding were going to carry across lanes anywhere, it would be here.
  daemonStore.registerJob({
    jobId: attached.jobIdFor('alpha'),
    actionType: 'launch-agent',
    function: 'daemon-side seat alpha',
    argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { workdir: 'string' } }),
    description: 'a seat the DAEMON lane finished',
    createdAt: isoNow(),
    updatedAt: isoNow(),
  });
  const daemonExec = daemonStore.recordExecutionStart({
    jobId: attached.jobIdFor('alpha'),
    actionType: 'launch-agent',
    args: JSON.stringify({ profile: 'probe-lane' }),
    enqueuedBy: 'daemon',
    sessionMode: 'headless',
    firedTick: 1,
    firedAt: new Date(),
  });
  daemonStore.endTurnAndCloseSession(daemonExec.exec_id, { turnStatus: 'done', sessionStatus: 'closed', endedAt: new Date() });
  check('D2 the daemon store now records alpha as DONE (synthesized, and disclosed as such)',
    daemonStore.dump().jobs_log.some((r) => r.job_id === attached.jobIdFor('alpha') && r.status === 'done'));
  daemonStore.close();

  // A SECOND goal folder, never run attached, so the attached lane meets a seat the daemon
  // "already finished" and nothing else.
  const freshGoal = path.join(workspace, '.rbtv', 'goals', 'lane-goal-2');
  for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(freshGoal, 'seats', s), { recursive: true });
  fs.mkdirSync(path.join(freshGoal, 'coordination'), { recursive: true });
  fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(freshGoal, 'taskforce.csv'));
  for (const s of ['alpha', 'bravo']) {
    fs.copyFileSync(path.join(goalFolder, 'seats', s, 'seat.md'), path.join(freshGoal, 'seats', s, 'seat.md'));
  }
  fs.writeFileSync(path.join(freshGoal, 'execution-mode'), 'interactive\n');

  const reran = [];
  await attached.executeAttached({
    goalFolder: freshGoal,
    profile: 'probe-lane',
    spawnConfigPath: configPath,
    tickIntervalMs: 200,
    maxTicks: 1,
    spawnForeground: (argv, cwd) => { reran.push(cwd); return { status: 0 }; },
  });
  check('D2 the attached lane RE-RUNS a seat the daemon lane already finished',
    reran.length === 1 && reran[0] === path.join(freshGoal, 'seats', 'alpha'),
    JSON.stringify(reran));
  finding('D2 create-only seeding protects against a REPLAY WITHIN ONE STORE and gives no '
    + 'cross-lane protection whatever: the attached lane re-seeded and re-ran a seat the daemon '
    + 'store recorded as done, under the most generous key-matching assumption available. Two lanes '
    + 'over one goal folder can each run the same seat once. NOT a defect in either lane — neither '
    + 'was ever given a shared record to read — and the fix is a ruling, not a patch: either a '
    + 'lane-independent execution record in the goal folder, or an explicit refusal when a goal '
    + 'carries evidence of the other lane.');

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

  // ── D4 · THE S-18 REFUSAL (owner ruling decisions.md#d-s18-cross-lane-refusal) ───────────────
  //
  // D2 measured the harm; this measures the v1 answer to it. The whole difficulty is that the
  // evidence is NOT "the goal has a launch trace" — an attached run's own detached seats write the
  // same rows (D1). The deciding fact is the JOIN: a trace row for a seat of this taskforce whose
  // `session-id` no execution in THIS goal's store owns. So the arms below are a discriminating
  // pair over exactly that fact, plus the false-positive control that matters most in practice.
  say('');
  say('D4 — a lane REFUSES a goal carrying execution evidence its own store has no record of');

  const foreignGoal = path.join(workspace, '.rbtv', 'goals', 'lane-goal-3');
  for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(foreignGoal, 'seats', s), { recursive: true });
  fs.mkdirSync(path.join(foreignGoal, 'coordination'), { recursive: true });
  fs.copyFileSync(path.join(goalFolder, 'taskforce.csv'), path.join(foreignGoal, 'taskforce.csv'));
  for (const s of ['alpha', 'bravo']) {
    fs.copyFileSync(path.join(goalFolder, 'seats', s, 'seat.md'), path.join(foreignGoal, 'seats', s, 'seat.md'));
  }
  fs.writeFileSync(path.join(foreignGoal, 'execution-mode'), 'interactive\n');
  // The header comes from the SCHEMA OWNER (coord.py SESSIONS_COLS), never spelled here — the same
  // contract the two writers follow. A fixture that invents the header would prove nothing about a
  // real trace.
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

  const attempt = async (goal) => {
    try { await attached.executeAttached({ goalFolder: goal, profile: 'probe-lane', spawnConfigPath: configPath, tickIntervalMs: 200, maxTicks: 1, spawnForeground: () => ({ status: 0 }) }); return null; }
    catch (err) { return err.message; }
  };

  const refusal = await attempt(foreignGoal);
  check('D4 `rbtv run` REFUSES a goal carrying a launched session its own store never recorded',
    Boolean(refusal) && /REFUSING TO RUN/.test(refusal) && refusal.includes(FOREIGN_SESSION) && /seat alpha/.test(refusal),
    (refusal || 'NO REFUSAL').split('\n').slice(0, 2).join(' / '));
  check('D4 …and it refuses BEFORE touching the goal: no heart store created, no run lock left behind',
    !fs.existsSync(path.join(foreignGoal, 'heart.db')) && !fs.existsSync(path.join(foreignGoal, attached.RUN_LOCK)),
    fs.readdirSync(foreignGoal).join(' '));
  check('D4 orientation is READ-ONLY and never refuses — `--status` still answers on that same goal',
    (() => {
      const st = attached.statusAttached({ goalFolder: foreignGoal });
      return st.everRun === false && st.seats.length === 2 && !fs.existsSync(path.join(foreignGoal, 'heart.db'));
    })(), 'a goal you cannot run is exactly the goal you most need to orient on');

  // THE DISCRIMINATING HALF. Nothing about the goal changes except the ONE fact the guard decides
  // on: the goal's own store gains an execution carrying that session id. If the refusal were
  // firing on "there is a trace" (or on the seat, or on the file), this would still refuse.
  const ownStore = openHeartStore({ dbPath: path.join(foreignGoal, 'heart.db'), profiles: cfg.profiles });
  ownStore.registerJob({
    jobId: attached.jobIdFor('alpha'), actionType: 'launch-agent',
    args: undefined, argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { workdir: 'string' } }),
    function: 'seat alpha', description: 'seat alpha', createdAt: isoNow(), updatedAt: isoNow(),
  });
  ownStore.recordExecutionStart({
    jobId: attached.jobIdFor('alpha'), actionType: 'launch-agent',
    args: JSON.stringify({ profile: 'probe-lane' }), enqueuedBy: attached.FOREGROUND_ENQUEUER,
    sessionMode: 'headed', firedTick: 1, firedAt: new Date(), sessionId: FOREIGN_SESSION,
  });
  ownStore.close();
  check('D4 MUTATION OF THE DECIDING FACT: give THIS store an execution for that session id and the '
    + 'very same goal runs — the guard reads the JOIN, not the file',
    (await attempt(foreignGoal)) === null,
    `evidence = a trace row this store cannot account for, and nothing else`);

  // THE STORE-EXISTS REFUSAL PATH, and the F4 property that makes it safe: the guard reads the
  // store READ-ONLY, so refusing leaves `heart.db` BYTE-IDENTICAL. Going through `openHeartStore`
  // here would have set WAL pragmas and run migrations — mutating a store as the price of declining
  // to run it, and doing so before the run lock, i.e. behind a live runner's back.
  //
  // ⚠ BYTE-IDENTITY ALONE IS NOT DISCRIMINATING and this arm was rewritten when a mutation proved
  // it: `openHeartStore` on an ALREADY-CURRENT store also leaves the bytes and the mtime untouched,
  // so the check passed with the migrating reader in place. The property that actually differs is
  // WHETHER A MIGRATION CAN RUN, so the fixture is made to LOOK OUTDATED — `user_version = 0`,
  // which `migrate()` stamps forward to its baseline the moment a read-write store opens it.
  const { DatabaseSync } = require('node:sqlite');
  const liveStore = path.join(foreignGoal, 'heart.db');
  const sha = (p) => require('node:crypto').createHash('sha256').update(fs.readFileSync(p)).digest('hex');
  const userVersion = () => {
    const d = new DatabaseSync(liveStore, { readOnly: true });
    try { return Number(d.prepare('PRAGMA user_version').get().user_version || 0); } finally { d.close(); }
  };
  const rw = new DatabaseSync(liveStore);
  rw.exec('PRAGMA user_version = 0;');
  rw.close();
  const before = sha(liveStore);
  fs.appendFileSync(foreignTrace, `${cell({
    'session-id': '99999999-8888-7777-6666-555555555555', seat: 'bravo', harness: 'claude',
    workdir: path.join(foreignGoal, 'seats', 'bravo'), started: isoNow(),
  })}\n`);
  const secondRefusal = await attempt(foreignGoal);
  check('D4 the refusal fires with a store PRESENT too — and the guard\'s read CANNOT MIGRATE it '
    + '(an out-of-date store is left out of date, and the bytes are identical)',
    Boolean(secondRefusal) && /REFUSING TO RUN/.test(secondRefusal)
      && /99999999/.test(secondRefusal) && userVersion() === 0 && sha(liveStore) === before,
    `user_version 0 -> ${userVersion()} · sha256 ${before.slice(0, 12)} -> ${sha(liveStore).slice(0, 12)}`);
  // The sidecars a WAL reader must create, REPORTED because they are the accepted price of the
  // read-only handle and nothing else in the tree would tell you they appear.
  say(`  (measured: a refusal leaves ${fs.readdirSync(foreignGoal).filter((f) => f.startsWith('heart.db-')).join(' ') || 'no'} sidecar(s) beside the store — see ourSessionIds)`);

  // F5: the store is GONE and the trace is not. Blaming "another lane" there is both false and
  // unactionable — this is `rm heart.db` on a goal this lane itself ran.
  fs.rmSync(liveStore, { force: true });
  const goneRefusal = await attempt(foreignGoal);
  check('D4 an ABSENT store gets its own message: what is true, and what the operator can do',
    Boolean(goneRefusal) && /NO heart store at all/.test(goneRefusal)
      && /restore the goal's heart.db/.test(goneRefusal) && !/ANOTHER LANE/.test(goneRefusal),
    (goneRefusal || 'NO REFUSAL').split('\n')[0].slice(0, 110));

  // THE FALSE-POSITIVE CONTROL, and the one that decides whether this guard is shippable: a goal
  // the attached lane ran itself carries TWO trace rows (D1) — one per carriage — and neither is
  // evidence of another lane. A guard that refused here would brick every resume.
  check('D4 CONTROL: the attached lane RE-RUNS its own goal — its own two rows are not evidence',
    (await attempt(goalFolder)) === null,
    'both carriages\' rows join to executions in this goal\'s own store');

  finding('D4 the refusal\'s DAEMON half is VACUOUSLY HELD, not built, and that is measured rather '
    + 'than assumed: D1 shows ONE function seeds a goal\'s taskforce (`seedTaskforce`) and its only '
    + 'non-probe caller is the attached lane\'s own boot, so there is no daemon-side path that could '
    + 'pick up a goal and re-run its seats — the direction the guard would protect does not exist to '
    + 'be guarded. Building a symmetric refusal on the daemon side today would be dead code. It '
    + 'becomes live the moment anything under `server/` seeds a taskforce; the Phase-6 '
    + 'lane-independent execution record retires the question for both lanes at once.');

  fs.rmSync(tmp, { recursive: true, force: true });
}

main().then(() => {
  const exitCode = failures.length ? 1 : 0;
  say('');
  say(exitCode
    ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
    : `RESULT: PASS — every arm measured what it claims; the three FINDINGS above are the probe's `
      + `deliverable, and they are negative: cross-lane resume does not hold, in either direction.`);
  say(`FINDINGS: ${findings.length} (a PASS here means "measured", never "cross-lane resume works")`);
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
