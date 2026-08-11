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

const { awaitExit } = require('./await-exit');
const attached = require('../attached-execution');
// The chat bridge's own gate readers — held BESIDE `heldSeatPredicate` so B1b can measure that the
// two answer alike rather than asserting it (7.626 review F3).
const ferry = require('../../bridges/chat/bus-ferry');
const { openHeartStore } = require('../../server/heart/heart-store');
const { requirePythonCmd } = require('../../lib/python-cmd');
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
// Holds the foreground seat long enough for a SECOND runner to try the same goal.
cfg.profiles['probe-fg-hold'] = {
  exec: { argv: ['sleep', '1'], prompt: 'stdin' },
  headed: { tui: { argv: ['sleep', '6'] } },
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

// B1j's fixture: N held seats with NO dependencies between them, so they are ALL ready in the SAME
// wave. `makeGoal` above deliberately chains bravo behind alpha (that chain is what B1a reads one
// carriage against the other with); a wave is the other shape, and 7.619 is only expressible on it.
function makeWaveGoal(name, seats) {
  const dir = path.join(workspace, '.rbtv', 'goals', name);
  fs.mkdirSync(path.join(dir, 'coordination'), { recursive: true });
  const rows = ['taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id'];
  for (const s of seats) {
    fs.mkdirSync(path.join(dir, 'seats', s), { recursive: true });
    rows.push(`tf-wave,${s},,claude,claude-opus-5,medium,50,m1`);
    fs.writeFileSync(path.join(dir, 'seats', s, 'seat.md'),
      `---\nseat: ${s}\nhuman-interactive: yes\nfallback: block-and-queue\n---\n\nbody\n`);
  }
  rows.push('');
  fs.writeFileSync(path.join(dir, 'taskforce.csv'), rows.join('\n'));
  fs.writeFileSync(path.join(dir, 'execution-mode'), 'interactive\n');
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
  // ⚑ THIS ARM USED TO PIN A DEFECT AS CANON, and the 7.626 review (F3) took it out. It asserted
  // that a QUOTED `human-interactive: "yes"` read FALSE, on the argument that the materializer emits
  // the bare boolean so the spelling cannot occur. It can: `component-lint` validates a descriptor
  // with `yaml.safe_load`, for which `"yes"` and `yes # comment` are TRUE, and STANDING seats are
  // hand-authored (`.rbtv/goals/_channel-master/seat.md`). The result was a lint-green seat this
  // predicate read false — silently detached instead of carried, with nothing reporting the
  // disagreement. `seatIsHumanInteractive` now strips quotes and trailing comments like its two
  // siblings, and the sameness claim is measured the honest way: the two readers AGREE, on the
  // spelling that used to split them.
  check('B1b the predicate is the CHAT BRIDGE\'s reader, not a second one — the two agree on a QUOTED value, and on a trailing-comment one, exactly as the linter reads them',
    (() => {
      const quoted = makeGoal('fg-goal-quoted', { humanInteractive: [] });
      fs.writeFileSync(path.join(quoted, 'seats', 'alpha', 'seat.md'),
        '---\nseat: alpha\nhuman-interactive: "yes"\n---\n\nbody\n');
      fs.mkdirSync(path.join(quoted, 'seats', 'bravo'), { recursive: true });
      fs.writeFileSync(path.join(quoted, 'seats', 'bravo', 'seat.md'),
        '---\nseat: bravo\nhuman-interactive: yes # ratified 2026-08-09\n---\n\nbody\n');
      const held = attached.heldSeatPredicate(quoted);
      return held('alpha') === true && held('bravo') === true
        && ferry.seatIsHumanInteractive(quoted, 'alpha') === true
        && ferry.seatIsHumanInteractive(quoted, 'bravo') === true
        // …and the reader is still STRICT where strictness is the point: a seat declaring `no`, and
        // one declaring nothing, stay false. Without this the arm would pass against a reader that
        // returned true for everything.
        && ferry.seatIsHumanInteractive(quoted, 'charlie') === false;
    })(),
    'both spellings are TRUE to yaml.safe_load, so both must be true here — the divergence was the defect (7.626 review F3)');

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
  await awaitExit(victim);
  await sleep(300);
  // The orphaned foreground child outlives a SIGKILL aimed at the runner alone (a real Ctrl-C
  // signals the whole foreground process group and takes it with it). Disclosed in the contract;
  // reaped here so the probe leaves nothing behind.
  spawnSync('pkill', ['-f', 'sleep 20.7']);

  check('B1e the killed runner left its lock behind — the STALE path is what the re-run must handle',
    fs.existsSync(path.join(killGoal, attached.RUN_LOCK)),
    'a runner killed outright cannot clear its own lock; only staleness detection can');

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
  check('B1e the stale lock did NOT brick the goal, and no lock is left behind',
    !fs.existsSync(path.join(killGoal, attached.RUN_LOCK)),
    'the crashed runner\'s lock was cleared by liveness, and both re-runs released their own');

  // ── B1g · ONE RUNNER PER GOAL (review finding 1) ────────────────────────────────────────────
  say('');
  say('B1g — a SECOND runner on a goal a first one holds must refuse, not reconcile');

  const holdGoal = makeGoal('fg-goal-hold');
  const holder = spawnProc(RBTV_BIN,
    ['run', holdGoal, '--profile', 'probe-fg-hold', '--config', configPath, '--tick-ms', '300', '--json'],
    { stdio: 'ignore', detached: true });
  const holderExit = awaitExit(holder);

  let holderRow = null;
  for (let i = 0; i < 40 && !holderRow; i += 1) {
    await sleep(200);
    if (!fs.existsSync(path.join(holdGoal, 'heart.db'))) continue;
    const rows = rowsFor(path.join(holdGoal, 'heart.db'), 'alpha');
    if (rows.length) holderRow = rows[0];
  }
  check('B1g runner A is holding a foreground seat (its row is live) and holds the lock',
    Boolean(holderRow) && !['done', 'failed'].includes(holderRow.status)
      && fs.existsSync(path.join(holdGoal, attached.RUN_LOCK)),
    holderRow ? `${holderRow.status}` : 'A never reached the carrier');

  const intruder = spawnSync(RBTV_BIN,
    ['run', holdGoal, '--profile', 'probe-fg', '--config', configPath, '--max-ticks', '1', '--json'],
    { encoding: 'utf8', timeout: 60000 });
  check('B1g runner B REFUSES, loudly, naming the live runner\'s pid — it does not reconcile',
    intruder.status === 1 && /another attached run is live on this goal \(pid \d+\)/.test(intruder.stderr || ''),
    `exit ${intruder.status}: ${(intruder.stderr || intruder.stdout || '').split('\n')[0].slice(0, 120)}`);
  const rowAfterIntruder = rowsFor(path.join(holdGoal, 'heart.db'), 'alpha')[0];
  check('B1g …and A\'s LIVE row is untouched — B did not end a seat a human is sitting in',
    rowAfterIntruder && rowAfterIntruder.status === holderRow.status
      && rowAfterIntruder.exec_id === holderRow.exec_id,
    `${holderRow.status} -> ${rowAfterIntruder && rowAfterIntruder.status}`);

  const { code: holderCode } = await holderExit;
  const holderRows = rowsFor(path.join(holdGoal, 'heart.db'), 'alpha');
  check('B1g runner A then completes NORMALLY — the refusal cost it nothing',
    holderCode === 0 && holderRows.length === 1 && holderRows[0].status === 'done'
      && !fs.existsSync(path.join(holdGoal, attached.RUN_LOCK)),
    `A exited ${holderCode}, alpha=${holderRows.map((r) => r.status).join()}, lock cleared=${!fs.existsSync(path.join(holdGoal, attached.RUN_LOCK))}`);

  // A lock naming a pid that no longer exists must never brick a goal — measured at the function,
  // with a live pid as the control so the arm cannot pass by refusing everything.
  const staleGoal = makeGoal('fg-goal-stale');
  fs.writeFileSync(path.join(staleGoal, attached.RUN_LOCK), '2147483646 999999999\n');
  let staleTaken = null;
  try { staleTaken = attached.acquireRunLock(staleGoal); } catch (err) { staleTaken = err.message; }
  check('B1g a lock naming a DEAD pid is cleared and taken — a crash never bricks the goal',
    staleTaken && staleTaken.release, String(staleTaken).slice(0, 120));
  if (staleTaken && staleTaken.release) staleTaken.release();
  check('B1g POSITIVE CONTROL: a lock naming a LIVE pid refuses',
    (() => {
      fs.writeFileSync(path.join(staleGoal, attached.RUN_LOCK), `${process.pid} ${''}\n`);
      try { attached.acquireRunLock(staleGoal); return false; } catch (err) { return /is live on this goal/.test(err.message); }
    })());
  fs.unlinkSync(path.join(staleGoal, attached.RUN_LOCK));

  // The silent-overwrite half: a foreign writer ends our row while the human works.
  const overwriteGoal = makeGoal('fg-goal-overwrite');
  const owStore = openHeartStore({ dbPath: path.join(overwriteGoal, 'heart.db'), profiles: spawnConfig.profiles });
  attached.seedTaskforce(owStore, overwriteGoal, { profile: 'probe-fg' });
  const owResult = attached.runForegroundSeat({
    heartStore: owStore, seat: 'alpha', goalFolder: overwriteGoal,
    profileName: 'probe-fg', profile: spawnConfig.profiles['probe-fg'],
    tick: 1, now: new Date(),
    // Stands in for the other writer: the row is ended `failed` WHILE the session runs.
    spawnForeground: () => {
      const live = owStore.dump().jobs_log.find((r) => r.job_id === attached.jobIdFor('alpha'));
      owStore.endTurnAndCloseSession(live.exec_id, { turnStatus: 'failed', sessionStatus: 'crashed', endedAt: new Date() });
      return { status: 0 };
    },
  });
  const owRow = owStore.dump().jobs_log.find((r) => r.job_id === attached.jobIdFor('alpha'));
  owStore.close();
  check('B1g a row already ended by another writer is NOT silently overwritten — it is surfaced',
    owResult.foreignTerminal === 'failed' && owResult.status === 'failed' && owRow.status === 'failed',
    `carrier reported ${JSON.stringify({ foreignTerminal: owResult.foreignTerminal, status: owResult.status })}, row=${owRow.status}`);

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

  // ── B1h · S-20 — a terminal-carried seat IS a launched session, and leaves the row ───────────
  //
  // Owner ruling `decisions.md#d-s20-foreground-seat-writes-session-row`. The row is the daemon
  // spawn path's schema (`coord.py SESSIONS_COLS`), written by the carrier in the dispatching act
  // and keyed by the SAME session id its `jobs_log` row carries — which is the join that makes it
  // identifiable as foreground without inventing a column.
  say('');
  say('B1h — the foreground carrier writes the goal\'s sessions.csv row (S-20)');

  const { readCsv: readTrace } = require('../../server/seat-identity/csv');
  const fgTrace = readTrace(path.join(goal, 'sessions.csv'));
  const alphaTraceRows = fgTrace.rows.filter((r) => r.seat === 'alpha');
  const alphaExec = rowsFor(storePath, 'alpha')[0];
  check('B1h the held seat has EXACTLY ONE trace row, and it joins its own execution by session id',
    alphaTraceRows.length === 1 && alphaTraceRows[0]['session-id'] === alphaExec.session_id
      && alphaExec.enqueued_by === attached.FOREGROUND_ENQUEUER,
    `trace session-id=${alphaTraceRows[0] && alphaTraceRows[0]['session-id']} · jobs_log session_id=${alphaExec.session_id}`);
  check('B1h the row is schema-conformant — every cell is a column of the file\'s OWN header',
    fgTrace.header.includes('session-id') && fgTrace.header.includes('pid-starttime')
      && alphaTraceRows[0].workdir === path.join(goal, 'seats', 'alpha')
      && alphaTraceRows[0].harness === ''    // `probe-fg` runs `sleep`/`true`: no harness to name
      && /^\d{4}-\d{2}-\d{2}T/.test(alphaTraceRows[0].started),
    `header=${fgTrace.header.join('|')}`);
  // The IDENTITY PAIR is the RUNNER's — the coord.py `pane_identity` rule: the seat's processes are
  // all descendants of `rbtv run`, and the gate matches a registered pid against the caller's
  // ancestry. `tty` is the numeric tty_nr and is only non-zero when the run really has a terminal,
  // which a probe does not — so it is REPORTED here, never asserted (a probe cannot own a tty).
  check('B1h the row carries the RUNNER\'s identity pair (its descendants are the seat\'s processes)',
    alphaTraceRows[0].pid === String(process.pid) && alphaTraceRows[0]['pid-starttime'].length > 0,
    `pid=${alphaTraceRows[0].pid} starttime=${alphaTraceRows[0]['pid-starttime']} tty=${alphaTraceRows[0].tty || '(none — this probe has no terminal)'}`);
  check('B1h POSITIVE CONTROL: the detached sibling\'s row is there too, written by the daemon door',
    fgTrace.rows.filter((r) => r.seat === 'bravo').length === 1,
    fgTrace.rows.map((r) => `${r.seat}:${r['session-id'].slice(0, 8)}`).join(' '));

  // THE CASE THE RULING EXISTS FOR: a package whose seats are ALL carried in the terminal. Before
  // S-20 it was traceless — no launch ever went through the daemon door — and the edge-runner's
  // check-out fast path refuses a traceless package wholesale. The header itself must be born here,
  // from the schema owner, since nothing else has written the file.
  const allFg = makeGoal('fg-goal-all-foreground', { humanInteractive: ['alpha', 'bravo'] });
  await attached.executeAttached({
    goalFolder: allFg,
    profile: 'probe-fg',
    spawnConfigPath: configPath,
    tickIntervalMs: 200,
    maxTicks: 40,
    spawnForeground: () => ({ status: 0 }),
  });
  const allTrace = readTrace(path.join(allFg, 'sessions.csv'));
  check('B1h an ALL-FOREGROUND package is no longer traceless — the file is born with the owner\'s header',
    allTrace.exists && allTrace.header[0] === 'session-id' && allTrace.header.length >= 14
      && allTrace.rows.map((r) => r.seat).sort().join() === 'alpha,bravo',
    `${allTrace.rows.length} row(s): ${allTrace.rows.map((r) => r.seat).join(' ')}`);

  // …AND THE ROW HAS A CLOSER (review F2). A console-lane seat can never reach `coord.py
  // session_close` (`checkIdentity` refuses it E_GOAL_NOT_LIVE — there is no tmux room on this
  // lane), so a row nobody closes leaves every FINISHED foreground seat reading as an open sitting
  // for the rest of the goal's life. Measured THROUGH THE REAL READERS, in python, because the
  // claim is about what `goal-state-job` and `coord` say — not about a cell this probe can inspect.
  check('B1h every foreground row is CLOSED — `ended` stamped, disposition `exited` by the `kit`',
    allTrace.rows.every((r) => r.ended && r.disposition === 'exited' && r['disposition-writer'] === 'kit'),
    allTrace.rows.map((r) => `${r.seat}:${r.ended || 'OPEN'}/${r.disposition || '-'}`).join(' '));

  const askPython = (src) => spawnSync(requirePythonCmd(), ['-c', src], { encoding: 'utf8', cwd: IGNITE_SRC });
  const readersSay = askPython(`
import sys, pathlib, importlib.util
sys.path.insert(0, 'team-kit')
import coord
def load(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
gs = load('gsj', 'jobs/goal-state-job.py')
pkg = pathlib.Path(${JSON.stringify(allFg)})
print('OPEN=' + ','.join(sorted(gs.open_session_seats(coord, pkg))))
print('DISP=' + ','.join('%s:%s' % (s, coord.session_disposition(pkg, s)) for s in ('alpha', 'bravo')))
`);
  const readerOut = `${readersSay.stdout || ''}${readersSay.stderr || ''}`.trim();
  check('B1h goal-state-job\'s `open_session_seats` no longer lists the FINISHED seats (the F2 harm)',
    /OPEN=\s*$/m.test(readerOut) || /OPEN=$/m.test(readerOut.split('\n')[0]),
    readerOut.split('\n')[0] || 'python said nothing');
  // F3, measured rather than assumed: gate 3's PURPOSE is that the trace can ANSWER disposition.
  // It now does — and the answer is `exited`, which every reader treats as NOT-done. That is the
  // truth on this lane: no seat declared its own check-out, because it cannot.
  check('B1h …and `coord.session_disposition` now RESOLVES for a foreground seat (was None)',
    /DISP=alpha:exited,bravo:exited/.test(readerOut),
    readerOut.split('\n')[1] || 'python said nothing');

  // ── B1i · S-21 — every `headed.tui` pins its profile's model ─────────────────────────────────
  //
  // Owner ruling `decisions.md#d-s21-headed-tui-pins-model`. Measured against the COMMITTED config
  // (not a fixture): a profile that pins its model in `exec` and not in `headed.tui` is a profile
  // whose name means one model detached and the harness default in a terminal.
  say('');
  say('B1i — the shipped headed.tui blocks pin the profile\'s model (S-21)');

  const shipped = loadConfig(COMMITTED_CONFIG).profiles;
  const headedProfiles = Object.entries(shipped).filter(([, p]) => p.headed && p.headed.tui);
  const MODEL_FLAGS = ['--model', '-m'];
  const unpinned = headedProfiles.filter(([, p]) => {
    const tui = p.headed.tui.argv;
    const i = tui.findIndex((a) => MODEL_FLAGS.includes(a));
    if (i < 0 || !tui[i + 1]) return true;
    // …and it must be the profile's OWN model — the value its detached template pins. A pin that
    // names a DIFFERENT model would satisfy "carries a model flag" and be worse than none.
    const exec = (p.exec && p.exec.argv) || [];
    const j = exec.findIndex((a) => MODEL_FLAGS.includes(a));
    return j < 0 ? false : exec[j + 1] !== tui[i + 1];
  });
  check('B1i EVERY shipped profile with a headed.tui pins its own model there',
    headedProfiles.length >= 11 && unpinned.length === 0,
    `${headedProfiles.length} headed profile(s); unpinned/mismatched: ${unpinned.map(([n]) => n).join(', ') || 'none'}`);

  // …and the pin survives COMPOSITION, on the real carrier path with a SHIPPED profile — the argv a
  // foreground seat would actually receive, not the config line it came from.
  const pinGoal = makeGoal('fg-goal-model-pin');
  const pinStore = openHeartStore({ dbPath: path.join(pinGoal, 'heart.db'), profiles: shipped });
  attached.seedTaskforce(pinStore, pinGoal, { profile: 'claude-fable' });
  let pinArgv = null;
  attached.runForegroundSeat({
    heartStore: pinStore, seat: 'alpha', goalFolder: pinGoal,
    profileName: 'claude-fable', profile: shipped['claude-fable'],
    tick: 1, now: new Date(),
    spawnForeground: (argv) => { pinArgv = argv; return { status: 0 }; },
  });
  pinStore.close();
  check('B1i composeArgv gives the carrier the pinned model — measured on a SHIPPED profile',
    pinArgv.slice(0, 3).join(' ') === 'claude --model claude-fable-5'
      && pinArgv.includes('--append-system-prompt-file'),
    JSON.stringify(pinArgv));

  // ── B1j · 7.619 — consecutive held seats carry BACK-TO-BACK, not one per tick ────────────────
  //
  // Three held seats with no dependency between them are all ready in ONE wave. The old shape
  // carried one per pass and slept `intervalMs` between them, so the measurable signature is the
  // TICK COUNT: 3 carriages across 3 ticks, with (N-1) intervals of blank terminal in between.
  // The interval is set deliberately large relative to the work so the two shapes cannot be
  // confused by timing noise — restoring the sleep reds this arm on the tick count alone.
  say('');
  say('B1j — three held seats ready in one wave are carried back-to-back in ONE pass (7.619)');

  const waveSeats = ['w-one', 'w-two', 'w-three'];
  const wave = makeWaveGoal('fg-goal-wave', waveSeats);
  const waveIntervalMs = 2000;
  const waveStart = Date.now();
  const waveResult = await attached.executeAttached({
    goalFolder: wave,
    profile: 'probe-fg',
    spawnConfigPath: configPath,
    tickIntervalMs: waveIntervalMs,
    maxTicks: 10,
    spawnForeground: () => ({ status: 0 }),
  });
  const waveMs = Date.now() - waveStart;
  check('B1j all three held seats were carried in ONE tick — no inter-seat interval sleep',
    waveResult.foreground.length === 3 && waveResult.ticks === 1,
    `carried=${waveResult.foreground.length} ticks=${waveResult.ticks} wall=${waveMs}ms interval=${waveIntervalMs}ms`);
  check('B1j …and the gap it removes is real: the run finished inside ONE interval',
    waveMs < waveIntervalMs,
    `wall=${waveMs}ms < ${waveIntervalMs}ms (the old shape paid ${(waveSeats.length - 1) * waveIntervalMs}ms of blank terminal here)`);
  check('B1j every carried seat is on record exactly once — the drain never re-carries one',
    waveSeats.every((s) => rowsFor(path.join(wave, 'heart.db'), s).length === 1)
      && waveResult.outcome === 'complete',
    `outcome=${waveResult.outcome}`);

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
