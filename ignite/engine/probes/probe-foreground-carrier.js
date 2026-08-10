#!/usr/bin/env node
'use strict';

// probe-foreground-carrier — console-run wave B, item B1.
//
// WHAT IT GUARDS, clause by clause of the design's own acceptance sketch:
//
//   B1a  THE ENGINE NEVER DETACHES A HUMAN-INTERACTIVE SEAT. Measured at the ROW the fire wrote:
//        a foreground seat's `jobs_log` row carries `enqueued_by = attached-foreground` and
//        `session_mode = headed`; a detached seat of the SAME RUN carries `attached-execution`.
//        Those two words are written by two different code paths, so one row cannot be mistaken
//        for the other.
//   B1b  BOTH GATES, EACH MEASURED WITH THE OTHER HELD OPEN (ruling 5 / D14). Closing the goal's
//        execution mode alone must send the very same seat down the DETACHED path — which is the
//        mutation that proves B1a is measuring the gate and not the seat's name.
//   B1c  THE COMMAND IS THE PROFILE'S `headed.tui`, plus the descriptor. Asserted against the
//        profile's own argv, and the seat.md injection asserted present for a claude profile and
//        absent for a seat with no descriptor.
//   B1d  A PROFILE WITH NO `headed.tui` REFUSES, with a positive control in the same run.
//   B1e  THE CRASH EDGE, DONE RATHER THAN APPROXIMATED: a real `rbtv run` subprocess is SIGKILLed
//        while a foreground seat holds it, and the re-run must (1) reconcile that row, (2) REFUSE
//        to advance past the seat rather than silently re-firing it, and (3) run it again — once —
//        when, and only when, an explicit `--relaunch` grant is typed.
//   B1f  THE GRANT IS SPENT AND CANNOT RE-RUN FINISHED WORK.
//
// ⚠ A PROBE CANNOT OWN A REAL TTY, and this one does not pretend to. Two substitutions, both
// disclosed: the library-level arms inject `spawnForeground` (the real carriage stays the DEFAULT,
// and B1c asserts the argv the real one would have received); the subprocess arms use a profile
// whose `headed.tui` is `sleep`/`true`, which needs no terminal. What is NOT proven here is that a
// harness TUI behaves correctly on an inherited tty — that is the B2 dogfood's, with a person at
// the keyboard.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn: spawnProc, spawnSync } = require('node:child_process');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const OUT_PATH = path.join(__dirname, 'probe-foreground-carrier.out');
const COMMITTED_CONFIG = path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml');
const RBTV_BIN = path.resolve(IGNITE_SRC, '..', 'core', 'capabilities', 'rbtv-cli', 'tool', 'rbtv');

const start = Date.now();
const lines = [];
const failures = [];
const say = (s) => lines.push(s);
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}

const attached = require('../attached-execution');
const { openHeartStore } = require('../../server/heart/heart-store');
const { loadConfig } = require('../../server/spawn/config');

// ── fixture ───────────────────────────────────────────────────────────────────────────────────
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-foreground-carrier-'));
const workspace = path.join(tmp, 'workspace');
const dataRoot = path.join(tmp, 'data');
fs.mkdirSync(dataRoot, { recursive: true });

const yaml = require(path.join(IGNITE_SRC, 'node_modules', 'js-yaml'));
const cfg = yaml.load(fs.readFileSync(COMMITTED_CONFIG, 'utf8'));
cfg.spawn = { ...(cfg.spawn || {}), data_root: dataRoot, carrier: 'setsid' };
cfg.default_workdir_root = path.join(tmp, 'work');
fs.mkdirSync(cfg.default_workdir_root, { recursive: true });

const CONTAINMENT = {
  caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
  sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
};
// The run profile. `exec` is what a DETACHED seat runs; `headed.tui` is what the FOREGROUND
// carrier runs — two different templates in one profile, which is the whole point of B1c.
cfg.profiles['probe-fg'] = {
  exec: { argv: ['sleep', '1'], prompt: 'stdin' },
  headed: { tui: { argv: ['true'] } },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  ...CONTAINMENT,
};
// Same, but the foreground seat blocks long enough to be killed while it holds the run.
cfg.profiles['probe-fg-slow'] = {
  exec: { argv: ['sleep', '1'], prompt: 'stdin' },
  headed: { tui: { argv: ['sleep', '20.7'] } },   // the fractional second makes the pkill exact
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  ...CONTAINMENT,
};
// A CLAUDE-harness profile, used ONLY through an injected carriage: `harnessOf` reads
// `exec.argv[0]`, so this is what makes the descriptor injection reachable. Nothing in this probe
// ever executes it.
cfg.profiles['probe-fg-claude'] = {
  exec: { argv: ['claude', '-p'], prompt: 'stdin' },
  headed: { tui: { argv: ['claude'] } },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  ...CONTAINMENT,
};
// The control for B1d: a profile that can carry a headless child and NOT a human.
cfg.profiles['probe-fg-headless-only'] = {
  exec: { argv: ['sleep', '1'], prompt: 'stdin' },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  ...CONTAINMENT,
};
const configPath = path.join(tmp, 'spawn-profiles.yaml');
fs.writeFileSync(configPath, yaml.dump(cfg));
const spawnConfig = loadConfig(configPath);

// alpha is held (human-interactive), bravo follows it and is not — so the run must use BOTH
// carriages, and one row can be read against the other inside one store.
function makeGoal(name, { executionMode = 'interactive', humanInteractive = ['alpha'] } = {}) {
  const dir = path.join(workspace, '.rbtv', 'goals', name);
  for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(dir, 'seats', s), { recursive: true });
  // The package's coordination dir: the cage binds it, so a detached seat without one dies at
  // `bwrap: Can't find source path …/coordination` — and the DETACHED half of every arm below is
  // the control the foreground half is read against, so it has to actually run.
  fs.mkdirSync(path.join(dir, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'taskforce.csv'), [
    'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id',
    'tf-fg,alpha,,claude,claude-opus-5,medium,50,m1',
    'tf-fg,bravo,alpha,claude,claude-opus-5,medium,50,m1',
    '',
  ].join('\n'));
  for (const s of ['alpha', 'bravo']) {
    fs.writeFileSync(path.join(dir, 'seats', s, 'seat.md'),
      `---\nseat: ${s}\n${humanInteractive.includes(s) ? 'human-interactive: yes\nfallback: block-and-queue\n' : ''}---\n\nbody\n`);
  }
  fs.writeFileSync(path.join(dir, 'execution-mode'), `${executionMode}\n`);
  return dir;
}

function rowsFor(storePath, seat) {
  const store = openHeartStore({ dbPath: storePath });
  try {
    return store.dump().jobs_log.filter((r) => r.job_id === attached.jobIdFor(seat));
  } finally { store.close(); }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  say('probe-foreground-carrier — console-run wave B item B1');
  say(`fixture: ${tmp}`);
  say('');

  // ── B1a · the two carriages, in ONE run, read off the rows they wrote ───────────────────────
  say('B1a — a held seat is CARRIED IN THE TERMINAL; its neighbour in the same run is DETACHED');

  const heldCalls = [];
  const fakeCarriage = (argv, cwd) => { heldCalls.push({ argv, cwd }); return { status: 0 }; };

  const goal = makeGoal('fg-goal');
  const result = await attached.executeAttached({
    goalFolder: goal,
    profile: 'probe-fg',
    spawnConfigPath: configPath,
    tickIntervalMs: 200,
    maxTicks: 40,
    spawnForeground: fakeCarriage,
  });

  check('B1a the run reached a terminal verdict', result.outcome === 'complete', `outcome=${result.outcome}`);
  check('B1a the foreground carrier fired exactly ONCE, for the held seat, in that seat\'s folder',
    heldCalls.length === 1 && heldCalls[0].cwd === path.join(goal, 'seats', 'alpha'),
    JSON.stringify(heldCalls));

  const storePath = path.join(goal, 'heart.db');
  const alphaRows = rowsFor(storePath, 'alpha');
  const bravoRows = rowsFor(storePath, 'bravo');
  check('B1a the HELD seat has exactly one execution and it was NEVER detached',
    alphaRows.length === 1
      && alphaRows[0].enqueued_by === attached.FOREGROUND_ENQUEUER
      && alphaRows[0].session_mode === 'headed'
      && alphaRows[0].status === 'done',
    alphaRows.map((r) => `${r.enqueued_by}/${r.session_mode}/${r.status}`).join(' '));
  check('B1a POSITIVE CONTROL: its neighbour in the SAME run went down the detached path',
    bravoRows.length === 1 && bravoRows[0].enqueued_by === 'attached-execution'
      && bravoRows[0].session_mode === 'headless',
    bravoRows.map((r) => `${r.enqueued_by}/${r.session_mode}/${r.status}`).join(' '));
  check('B1a the held seat still BLOCKS its dependents — the wave math is unchanged',
    result.seats.join() === 'alpha,bravo' && result.foreground.map((f) => f.seat).join() === 'alpha',
    JSON.stringify(result.foreground));

  // …and the BAR ITSELF, at the point the engine could detach one. The run above cannot reach it —
  // the carrier fires first, so a held seat is never `ready` when the enqueue pass looks — which is
  // exactly why the invariant is measured HERE rather than inferred from the run: an ordering is a
  // policy, and this is the structural bar under it. Both calls run against the SAME store, the
  // held one first, so the control proves the seat was enqueueable all along.
  const barGoal = makeGoal('fg-goal-bar');
  const barStore = openHeartStore({ dbPath: path.join(barGoal, 'heart.db'), profiles: spawnConfig.profiles });
  const barRows = attached.seedTaskforce(barStore, barGoal, { profile: 'probe-fg' });
  const heldBar = attached.enqueueEligible(barStore, barRows,
    { profile: 'probe-fg', goalFolder: barGoal, isHeld: attached.heldSeatPredicate(barGoal) });
  const queuedAfterBar = barStore.listQueue().map((q) => q.job_id);
  const freeBar = attached.enqueueEligible(barStore, barRows, { profile: 'probe-fg', goalFolder: barGoal });
  check('B1a the enqueue pass REFUSES to queue a held seat — the bar, measured where it stands',
    heldBar.length === 0 && queuedAfterBar.length === 0,
    `enqueued=${JSON.stringify(heldBar)} queue=${JSON.stringify(queuedAfterBar)}`);
  check('B1a POSITIVE CONTROL: the same pass without the bar queues that very seat',
    freeBar.join() === 'alpha', JSON.stringify(freeBar));
  barStore.close();

  // ── B1b · the mutation: close ONE gate and the SAME seat detaches ───────────────────────────
  say('');
  say('B1b — each gate closed ALONE sends the very same seat down the detached path');

  const modeOffCalls = [];
  const goalAuto = makeGoal('fg-goal-autonomous', { executionMode: 'autonomous' });
  await attached.executeAttached({
    goalFolder: goalAuto,
    profile: 'probe-fg',
    spawnConfigPath: configPath,
    tickIntervalMs: 200,
    maxTicks: 40,
    spawnForeground: (argv, cwd) => { modeOffCalls.push({ argv, cwd }); return { status: 0 }; },
  });
  const autoAlpha = rowsFor(path.join(goalAuto, 'heart.db'), 'alpha');
  check('B1b GATE B closed alone (seat flag untouched): the carrier never fires, the seat detaches',
    modeOffCalls.length === 0 && autoAlpha.length === 1 && autoAlpha[0].enqueued_by === 'attached-execution',
    `carrier calls=${modeOffCalls.length}, enqueued_by=${autoAlpha[0] && autoAlpha[0].enqueued_by}`);

  const flagOffCalls = [];
  const goalNoFlag = makeGoal('fg-goal-noflag', { humanInteractive: [] });
  await attached.executeAttached({
    goalFolder: goalNoFlag,
    profile: 'probe-fg',
    spawnConfigPath: configPath,
    tickIntervalMs: 200,
    maxTicks: 40,
    spawnForeground: (argv, cwd) => { flagOffCalls.push({ argv, cwd }); return { status: 0 }; },
  });
  const noFlagAlpha = rowsFor(path.join(goalNoFlag, 'heart.db'), 'alpha');
  check('B1b GATE A closed alone (goal still interactive): the carrier never fires, the seat detaches',
    flagOffCalls.length === 0 && noFlagAlpha.length === 1 && noFlagAlpha[0].enqueued_by === 'attached-execution',
    `carrier calls=${flagOffCalls.length}, enqueued_by=${noFlagAlpha[0] && noFlagAlpha[0].enqueued_by}`);
  check('B1b the predicate is the CHAT BRIDGE\'s reader, not a second one — a QUOTED value reads false',
    (() => {
      const quoted = makeGoal('fg-goal-quoted', { humanInteractive: [] });
      fs.writeFileSync(path.join(quoted, 'seats', 'alpha', 'seat.md'),
        '---\nseat: alpha\nhuman-interactive: "yes"\n---\n\nbody\n');
      return attached.heldSeatPredicate(quoted)('alpha') === false;
    })(),
    'bus-ferry regex-matches the RAW frontmatter line; wave A canon-checks emission to the bare boolean');

  // ── B1c · the command comes from `headed.tui`, and the descriptor rides it ──────────────────
  say('');
  say('B1c — the launched command is the profile\'s OWN headed template, plus the seat descriptor');

  check('B1c the foreground argv IS the profile\'s headed.tui argv (not a filtered `exec:`)',
    heldCalls[0].argv.join(' ') === 'true'
      && spawnConfig.profiles['probe-fg'].exec.argv.join(' ') === 'sleep 1',
    `argv=${JSON.stringify(heldCalls[0].argv)}`);

  const claudeGoal = makeGoal('fg-goal-claude');
  const claudeStore = openHeartStore({ dbPath: path.join(claudeGoal, 'heart.db') });
  attached.seedTaskforce(claudeStore, claudeGoal, { profile: 'probe-fg-claude' });
  let claudeArgv = null;
  attached.runForegroundSeat({
    heartStore: claudeStore,
    seat: 'alpha',
    goalFolder: claudeGoal,
    profileName: 'probe-fg-claude',
    profile: spawnConfig.profiles['probe-fg-claude'],
    tick: 1,
    now: new Date(),
    spawnForeground: (argv) => { claudeArgv = argv; return { status: 0 }; },
  });
  const seatMd = path.join(claudeGoal, 'seats', 'alpha', 'seat.md');
  check('B1c a claude seat receives seat.md through --append-system-prompt-file',
    claudeArgv.join(' ') === `claude --append-system-prompt-file ${seatMd}`,
    JSON.stringify(claudeArgv));
  // …and the CONDITION is the file, not the harness alone: an absent descriptor must not put a
  // flag on the line that makes claude run nothing at all (measured, 2.1.224).
  fs.unlinkSync(seatMd);
  let noDescArgv = null;
  attached.runForegroundSeat({
    heartStore: claudeStore,
    seat: 'bravo',
    goalFolder: claudeGoal,
    profileName: 'probe-fg-claude',
    profile: spawnConfig.profiles['probe-fg-claude'],
    tick: 1,
    now: new Date(),
    spawnForeground: (argv) => { noDescArgv = argv; return { status: 0 }; },
  });
  fs.unlinkSync(path.join(claudeGoal, 'seats', 'bravo', 'seat.md'));
  let noFileArgv = null;
  attached.runForegroundSeat({
    heartStore: claudeStore,
    seat: 'bravo',
    goalFolder: claudeGoal,
    profileName: 'probe-fg-claude',
    profile: spawnConfig.profiles['probe-fg-claude'],
    tick: 1,
    now: new Date(),
    spawnForeground: (argv) => { noFileArgv = argv; return { status: 0 }; },
  });
  check('B1c NO descriptor on disk ⇒ NO flag on the line (the flag would make claude run nothing)',
    noFileArgv.join(' ') === 'claude' && /append-system-prompt-file/.test(noDescArgv.join(' ')),
    `withFile=${JSON.stringify(noDescArgv)} withoutFile=${JSON.stringify(noFileArgv)}`);
  claudeStore.close();

  // ── B1d · a profile that cannot carry a human REFUSES ───────────────────────────────────────
  say('');
  say('B1d — no `headed.tui` block ⇒ a refusal that names the seat and the profile');

  const refuseGoal = makeGoal('fg-goal-refuse');
  const refuseStore = openHeartStore({ dbPath: path.join(refuseGoal, 'heart.db') });
  attached.seedTaskforce(refuseStore, refuseGoal, { profile: 'probe-fg-headless-only' });
  let refusal = null;
  try {
    attached.runForegroundSeat({
      heartStore: refuseStore, seat: 'alpha', goalFolder: refuseGoal,
      profileName: 'probe-fg-headless-only', profile: spawnConfig.profiles['probe-fg-headless-only'],
      tick: 1, now: new Date(), spawnForeground: () => ({ status: 0 }),
    });
  } catch (err) { refusal = err.message; }
  check('B1d it refuses, naming the seat, the profile and the headed block',
    Boolean(refusal) && /alpha/.test(refusal) && /probe-fg-headless-only/.test(refusal) && /headed\.tui/.test(refusal),
    String(refusal).split('\n')[0]);
  let controlThrew = null;
  try {
    attached.runForegroundSeat({
      heartStore: refuseStore, seat: 'bravo', goalFolder: refuseGoal,
      profileName: 'probe-fg', profile: spawnConfig.profiles['probe-fg'],
      tick: 1, now: new Date(), spawnForeground: () => ({ status: 0 }),
    });
  } catch (err) { controlThrew = err.message; }
  check('B1d POSITIVE CONTROL: the same call with a headed profile does NOT refuse',
    controlThrew === null, String(controlThrew));
  refuseStore.close();

  // ── B1e · the crash edge, done for real ─────────────────────────────────────────────────────
  say('');
  say('B1e — SIGKILL while a foreground seat holds the run, then re-run (the design\'s hardest edge)');

  const killGoal = makeGoal('fg-goal-kill');
  const killStore = path.join(killGoal, 'heart.db');
  // ⚠ `detached: true` + a signal to the PROCESS GROUP, not to the pid. `rbtv` is a wrapper that
  // execs the delegate, which in turn holds the foreground child: a SIGKILL aimed at the wrapper's
  // pid alone leaves the real runner ALIVE and still writing to this store, and the arms below then
  // measure a race between it and the re-run instead of a resume. (That is also the honest shape of
  // the event being simulated — closing a terminal signals the whole foreground group.)
  const victim = spawnProc(RBTV_BIN,
    ['run', killGoal, '--profile', 'probe-fg-slow', '--config', configPath, '--tick-ms', '300'],
    { stdio: 'ignore', detached: true });

  let midRow = null;
  for (let i = 0; i < 40 && !midRow; i += 1) {
    await sleep(250);
    if (!fs.existsSync(killStore)) continue;
    const rows = rowsFor(killStore, 'alpha');
    if (rows.length) midRow = rows[0];
  }
  check('B1e the foreground seat was LIVE when the kill landed — the row exists and is not terminal',
    Boolean(midRow) && midRow.enqueued_by === attached.FOREGROUND_ENQUEUER
      && !['done', 'failed', 'blocked', 'killed'].includes(midRow.status),
    midRow ? `${midRow.enqueued_by}/${midRow.status}` : 'no row appeared — the carrier never fired');
  try { process.kill(-victim.pid, 'SIGKILL'); } catch { victim.kill('SIGKILL'); }
  await new Promise((resolve) => victim.on('exit', resolve));
  await sleep(300);
  // The orphaned foreground child outlives a SIGKILL aimed at the runner alone (a real Ctrl-C
  // signals the whole foreground process group and takes it with it). Disclosed in the contract;
  // reaped here so the probe leaves nothing behind.
  spawnSync('pkill', ['-f', 'sleep 20.7']);

  // The status verb must not tell an operator that a dead seat is being worked on.
  const stKilled = attached.statusAttached({ goalFolder: killGoal });
  check('B1e --status names the interrupted seat instead of leaving it reading as in-flight',
    stKilled.interrupted.join() === 'alpha' && stKilled.live.includes('alpha'),
    `interrupted=${JSON.stringify(stKilled.interrupted)} live=${JSON.stringify(stKilled.live)}`);

  const runCli = (args) => {
    const res = spawnSync(RBTV_BIN, args, { encoding: 'utf8', timeout: 120000 });
    let json = null;
    try { json = JSON.parse(res.stdout || ''); } catch { /* reported by the caller's check */ }
    return { status: res.status, json, stdout: res.stdout || '', stderr: res.stderr || '' };
  };

  const afterKill = runCli(['run', killGoal, '--profile', 'probe-fg', '--config', configPath, '--max-ticks', '3', '--json']);
  check('B1e the re-run RECONCILES the interrupted row instead of inheriting a ghost',
    afterKill.json && afterKill.json.reconciled.includes(attached.jobIdFor('alpha')),
    afterKill.json ? JSON.stringify(afterKill.json.reconciled) : afterKill.stderr.split('\n')[0]);
  check('B1e it REFUSES to advance past the seat — exit 1, naming it — and NEVER re-fires it blindly',
    afterKill.status === 1 && afterKill.json && afterKill.json.outcome === 'seat-failed'
      && afterKill.json.unfinished.join() === 'alpha'
      && afterKill.json.foreground.length === 0,
    afterKill.json ? `exit ${afterKill.status}, outcome ${afterKill.json.outcome}` : `exit ${afterKill.status}`);
  const afterKillRows = rowsFor(killStore, 'alpha');
  check('B1e the interrupted attempt is ENDED, not erased — one row, failed',
    afterKillRows.length === 1 && afterKillRows[0].status === 'failed',
    afterKillRows.map((r) => r.status).join());

  const granted = runCli(['run', killGoal, '--profile', 'probe-fg', '--config', configPath,
    '--relaunch', 'alpha', '--tick-ms', '300', '--max-ticks', '40', '--json']);
  check('B1e an EXPLICIT --relaunch runs the seat again, and the run then completes',
    granted.status === 0 && granted.json && granted.json.outcome === 'complete'
      && granted.json.foreground.map((f) => f.seat).join() === 'alpha',
    granted.json ? `exit ${granted.status}, outcome ${granted.json.outcome}` : `exit ${granted.status}: ${granted.stderr.split('\n')[0]}`);
  const grantedRows = rowsFor(killStore, 'alpha');
  check('B1e the grant fired ONCE: two rows for the seat — the failed attempt and the good one',
    grantedRows.length === 2 && grantedRows.filter((r) => r.status === 'done').length === 1
      && grantedRows.filter((r) => r.status === 'failed').length === 1,
    grantedRows.map((r) => r.status).join());

  check('B1e …and once the grant has run it, nothing is interrupted any more',
    attached.statusAttached({ goalFolder: killGoal }).interrupted.length === 0);

  // ── B1f · the grant's own bounds, measured at the view it changes ───────────────────────────
  say('');
  say('B1f — a grant re-opens a DEAD seat and can never re-open a FINISHED one');

  const view = openHeartStore({ dbPath: killStore });
  try {
    const rows = [{ seat: 'alpha', after: '' }, { seat: 'bravo', after: 'alpha' }];
    const plain = attached.executionsByJob(view);
    const withGrant = attached.executionsByJob(view, new Set(['alpha', 'bravo']));
    check('B1f a FINISHED seat is not re-opened by naming it in a grant',
      Boolean(withGrant.get(attached.jobIdFor('alpha')))
        && Boolean(withGrant.get(attached.jobIdFor('bravo')))
        && attached.seatState(rows[0], withGrant, new Set()) === 'done',
      'alpha finished on the relaunch, bravo finished behind it — neither is hidden');
    // …and the same call on a store where the seat is DEAD does re-open it. Measured on the
    // failed-only view built from this store's own first attempt.
    const deadOnly = new Map([[attached.jobIdFor('alpha'), plain.get(attached.jobIdFor('alpha')).filter((r) => r.status === 'failed')]]);
    check('B1f POSITIVE CONTROL: with only the failed attempt on record the seat reads `live`…',
      attached.seatState(rows[0], deadOnly, new Set()) === 'live');
    deadOnly.delete(attached.jobIdFor('alpha'));
    check('B1f …and the grant\'s view — its history hidden, nothing rewritten — reads `ready`',
      attached.seatState(rows[0], deadOnly, new Set()) === 'ready');
  } finally { view.close(); }

  // The reconciliation is SCOPED to the foreground marker: a detached row left non-terminal is the
  // ticker's crash sweep's business, and ending it here would race that sweep.
  const scopeStore = openHeartStore({ dbPath: path.join(tmp, 'scope.db'), profiles: spawnConfig.profiles });
  scopeStore.registerJob({ jobId: 'seat-fg', actionType: 'launch-agent', function: 'x', argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: {} }), description: 'x', createdAt: '2026-08-10T00:00:00Z', updatedAt: '2026-08-10T00:00:00Z' });
  scopeStore.registerJob({ jobId: 'seat-detached', actionType: 'launch-agent', function: 'x', argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: {} }), description: 'x', createdAt: '2026-08-10T00:00:00Z', updatedAt: '2026-08-10T00:00:00Z' });
  for (const [jobId, by] of [['seat-fg', attached.FOREGROUND_ENQUEUER], ['seat-detached', 'attached-execution']]) {
    scopeStore.recordExecutionStart({
      jobId, actionType: 'launch-agent', args: '{}', enqueuedBy: by,
      sessionMode: by === attached.FOREGROUND_ENQUEUER ? 'headed' : 'headless',
      firedTick: 1, firedAt: new Date(),
    });
  }
  const reconciled = attached.reconcileForegroundOrphans(scopeStore);
  const scopeRows = scopeStore.dump().jobs_log;
  check('B1f the reconciliation ends ONLY foreground rows — a detached orphan is left to the ticker',
    reconciled.join() === 'seat-fg'
      && scopeRows.find((r) => r.job_id === 'seat-fg').status === 'failed'
      && scopeRows.find((r) => r.job_id === 'seat-detached').status === 'launching',
    scopeRows.map((r) => `${r.job_id}=${r.status}`).join(' '));
  scopeStore.close();

  fs.rmSync(tmp, { recursive: true, force: true });
}

main().then(() => {
  const exitCode = failures.length ? 1 : 0;
  say('');
  say(exitCode
    ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
    : 'RESULT: PASS — a held seat is carried in the terminal and never detached, both gates decide it, '
      + 'the command is the profile\'s own headed template, and an interrupted seat is reconciled, refused, '
      + 'and re-run only on an explicit grant.');
  say('');
  say('NOT PROVEN HERE, deliberately: nothing about a harness TUI on an inherited tty — the carriage is');
  say('substituted (an injected function, or `sleep`/`true` as the headed command). That is B2\'s, with a');
  say('person at the keyboard. Nothing about model binding either: the shipped claude profiles pin no');
  say('--model in `headed.tui`, which is a config gap filed rather than fixed here.');
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
