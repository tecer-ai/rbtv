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
//   B1f  THE GRANT'S BOUNDS AT THE VIEW IT CHANGES: it hides a granted seat's history WHOLE —
//        finished rows included, since the loop re-fire (owner ruling 2026-08-12) moved the "must
//        not re-run completed work" guard to the grant's MINT — and the ungranted view of the same
//        store is the control.
//
// ⚠ A PROBE CANNOT OWN A REAL TTY, and this one does not pretend to. Two substitutions, both
// disclosed: the library-level arms inject `spawnForeground` (the real carriage stays the DEFAULT,
// and B1c asserts the argv the real one would have received); the subprocess arms use a profile
// whose `headed.tui` is `sleep`/`true`, which needs no terminal. What is NOT proven here is that a
// harness TUI behaves correctly on an inherited tty — that is the B2 dogfood's, with a person at
// the keyboard.
//
// ⚠ KNOWN CAPABLE OF A TRANSIENT FALSE-RED UNDER VPS LOAD. This probe races REAL subprocess
// spawns and kills against hard wall-clock margins — B1j asserts `waveMs < waveIntervalMs`
// (2000 ms) for three real subprocess dispatches inside one tick interval on a shared 4-core box.
// Measured red 2026-08-11 at VPS HEAD 8ae0978a; unreproducible, 48/48 green on re-run the same
// day. Diagnosis: environment/timing, not code. Widening the margin is an owner call, not a fix.

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
// COORD'S FRONTIER, the readiness answer every arm below is measured against since
// `build/one-readiness-predicate.md` § D1. The unit-level arms hand it in explicitly; the run-level
// ones get it from `executeAttached`, which asks once per pass.
const { readySeats } = require('../seeding');
// The chat bridge's own gate readers — held BESIDE `heldSeatPredicate` so B1b can measure that the
// two answer alike rather than asserting it (7.626 review F3).
const ferry = require('../../bridges/chat/bus-ferry');
const { openHeartStore, closeHeartStore } = require('../../server/heart/heart-store');
const { requirePythonCmd } = require('../../lib/python-cmd');
const { loadConfig } = require('../../server/spawn/config');

// ── fixture ───────────────────────────────────────────────────────────────────────────────────
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-foreground-carrier-'));
const workspace = path.join(tmp, 'workspace');
const dataRoot = path.join(tmp, 'data');
fs.mkdirSync(dataRoot, { recursive: true });

// ── THE SEAT'S OWN CHECK-OUT, AS A FIXTURE ACT ────────────────────────────────────────────────
//
// ⚠ WHY THIS EXISTS AT ALL, and it is the whole reason this probe was red. Since § D1 the ONE
// readiness evaluator is `coord.ready_seat_rows`, and it satisfies an `after` member on a
// predecessor's `done` CHECK-OUT and on nothing else — no store turn, no exit code. The carrier
// deliberately stamps `exited` ("`done` is the seat reporting its own work finished, which no exit
// code can assert"), so a terminal-carried seat advances NOTHING unless the OCCUPANT checks out.
// Substituting the carriage therefore means substituting the occupant's check-out too; every arm
// below that needs an edge to move does it here, and the arms that measure the CARRIER's own
// stamping (B1h) deliberately do not.
//
// Written as a standalone file so the in-process arms and the `headed.tui` SUBPROCESS arms share
// ONE implementation — the subprocess ones cannot be handed a JS function.
const CHECKOUT_JS = path.join(tmp, 'seat-checks-out-done.js');
fs.writeFileSync(CHECKOUT_JS, `'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { splitRow, quoteField } = require(${JSON.stringify(path.join(IGNITE_SRC, 'server', 'seat-identity', 'csv'))});

// Close this seat's OPEN sessions.csv row the way \`coord.py session_close\` would for a seat that
// declared its work finished: \`done\`, written by the \`seat\` (the only writer the enum admits for
// that value). The carrier's own closer then finds \`ended\` set and stands down — the
// "already closed by another writer" branch it documents.
// ⚠ LAST OPEN ROW, NOT THE FIRST. A relaunched seat has an earlier row from the attempt that died
// — closing THAT one would stamp \`done\` on a dead sitting while the live one still closes
// \`exited\`, and every disposition reader takes the LAST ended row.
function checkOutDone(goalFolder, seat) {
  const csvPath = path.join(goalFolder, 'sessions.csv');
  const lines = fs.readFileSync(csvPath, 'utf8').split('\\n');
  const header = splitRow(lines[0]).map((h) => h.trim());
  const at = (n) => header.indexOf(n);
  for (let i = lines.length - 1; i >= 1; i -= 1) {
    if (!lines[i].length) continue;
    const cells = splitRow(lines[i]);
    while (cells.length < header.length) cells.push('');
    if ((cells[at('seat')] || '').trim() !== seat) continue;
    if ((cells[at('ended')] || '').trim()) continue;
    cells[at('ended')] = new Date().toISOString().replace(/\\.\\d{3}Z$/, 'Z');
    cells[at('disposition')] = 'done';
    cells[at('disposition-writer')] = 'seat';
    lines[i] = header.map((_, c) => quoteField(cells[c])).join(',');
    fs.writeFileSync(csvPath, lines.join('\\n'), 'utf8');
    return true;
  }
  return false;
}
module.exports = { checkOutDone };
// As a \`headed.tui\` command the cwd IS the seat folder, so both operands are read off it.
if (require.main === module) {
  checkOutDone(path.resolve(process.cwd(), '..', '..'), path.basename(process.cwd()));
}
`);
const { checkOutDone } = require(CHECKOUT_JS);

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
// ⚠ ITS `headed.tui` IS THE CHECK-OUT SCRIPT, not `true`: the subprocess arms (B1e, B1g) drive a
// REAL `rbtv run` and cannot inject a carriage, so the profile's own command is the only place the
// occupant's check-out can be stood in for. See CHECKOUT_JS above for why an edge needs one.
// 7.787: `profiles:` is `launch-specs:`, keyed by (harness, model). Each argv gains a `--model`
// pin so it agrees with its key (`profiles.js#validateSpecKey` refuses a disagreement at LOAD);
// what each one RUNS is unchanged. `probe-fg-claude` keeps `claude` as argv[0] because that is
// exactly what makes `harnessOf` classify it — it is never executed.
cfg['launch-specs'] = { bash: {}, claude: {} };
cfg['launch-specs'].bash['probe-fg'] = {
  exec: { argv: ['bash', '-c', 'exec sleep 1', '--model', 'probe-fg'], prompt: 'stdin' },
  headed: { tui: { argv: ['node', CHECKOUT_JS] } },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  ...CONTAINMENT,
};
// Same, but the foreground seat blocks long enough to be killed while it holds the run.
cfg['launch-specs'].bash['probe-fg-slow'] = {
  exec: { argv: ['bash', '-c', 'exec sleep 1', '--model', 'probe-fg-slow'], prompt: 'stdin' },
  headed: { tui: { argv: ['sleep', '20.7'] } },   // longer than B1e's kill window, by a distinctive duration
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  ...CONTAINMENT,
};
// Holds the foreground seat long enough for a SECOND runner to try the same goal, then checks out
// so runner A's own run can finish (B1g's last arm).
cfg['launch-specs'].bash['probe-fg-hold'] = {
  exec: { argv: ['bash', '-c', 'exec sleep 1', '--model', 'probe-fg-hold'], prompt: 'stdin' },
  headed: { tui: { argv: ['sh', '-c', `sleep 6; exec node ${CHECKOUT_JS}`] } },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  ...CONTAINMENT,
};
// A CLAUDE-harness profile, used ONLY through an injected carriage: `harnessOf` reads
// `exec.argv[0]`, so this is what makes the descriptor injection reachable. Nothing in this probe
// ever executes it.
cfg['launch-specs'].claude['probe-fg-claude'] = {
  exec: { argv: ['claude', '-p', '--model', 'probe-fg-claude'], prompt: 'stdin' },
  headed: { tui: { argv: ['claude'] } },
  session_ref: { source: 'cwd-implicit' },
  workdir_root: '.rbtv/goals',
  ...CONTAINMENT,
};
// The control for B1d: a profile that can carry a headless child and NOT a human.
cfg['launch-specs'].bash['probe-fg-headless-only'] = {
  exec: { argv: ['bash', '-c', 'exec sleep 1', '--model', 'probe-fg-headless-only'], prompt: 'stdin' },
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
      `---\nseat: ${s}\nharness: bash\nmodel: probe-fg\n${humanInteractive.includes(s) ? 'human-interactive: yes\nfallback: block-and-queue\n' : ''}---\n\nbody\n`);
  }
  fs.writeFileSync(path.join(dir, 'execution-mode'), `${executionMode}\n`);
  return dir;
}

// Re-cast an already-materialized seat descriptor onto another of this fixture's launch specs.
// Since `#d-abolish-profile-names` the descriptor is the ONLY thing that decides what a seat runs,
// so this is how an arm selects a spec — there is no parameter left to pass one on.
function recast(seatDir, model, harness = 'bash') {
  const md = path.join(seatDir, 'seat.md');
  fs.writeFileSync(md, fs.readFileSync(md, 'utf8')
    .replace(/^harness: .*$/m, `harness: ${harness}`)
    .replace(/^model: .*$/m, `model: ${model}`));
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
      `---\nseat: ${s}\nharness: bash\nmodel: probe-fg\nhuman-interactive: yes\nfallback: block-and-queue\n---\n\nbody\n`);
  }
  rows.push('');
  fs.writeFileSync(path.join(dir, 'taskforce.csv'), rows.join('\n'));
  fs.writeFileSync(path.join(dir, 'execution-mode'), 'interactive\n');
  return dir;
}

// ⚠ FIXTURE HARDENING, not a product guard. The polling loops below open a FRESH store on a goal
// a concurrently-spawned `rbtv run` is writing every 300 ms, and `HeartStore`'s constructor runs
// WAL/schema/migrate BEFORE it sets `busy_timeout` — so the open can throw `database is locked`
// inside a window no timeout covers. Retried 3× narrowly (that string ONLY); anything else, and a
// lock that survives all three, still fails the probe loudly.
//
// The closeHeartStore() below is NOT housekeeping - without it the retry makes things WORSE,
// measured 2026-08-14. The constructor claims the process-wide single-writer slot
// (`singleton = this`, heart-store.js:579) BEFORE the migrate that throws, so a lock leaves a
// half-built store owning that slot; the next open then dies with `heart store writer already open
// in this process` and every later rowsFor in the run is poisoned. closeHeartStore() releases the
// orphaned slot - on the final rethrow too, so the probe reports the honest lock, not the shrapnel.
function rowsFor(storePath, seat) {
  for (let attempt = 1; ; attempt += 1) {
    let store;
    try {
      store = openHeartStore({ dbPath: storePath });
    } catch (err) {
      if (!/database is locked/i.test(err.message || '')) throw err;
      closeHeartStore();
      if (attempt >= 3) throw err;
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 150);
      continue;
    }
    try {
      return store.dump().jobs_log.filter((r) => r.job_id === attached.jobIdFor(seat));
    } finally { store.close(); }
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  say('probe-foreground-carrier — console-run wave B item B1');
  say(`fixture: ${tmp}`);
  say('');

  // ── B1a · the two carriages, in ONE run, read off the rows they wrote ───────────────────────
  say('B1a — a held seat is CARRIED IN THE TERMINAL; its neighbour in the same run is DETACHED');

  const heldCalls = [];
  // The injected carriage stands in for the human in the seat — INCLUDING the check-out they would
  // type. Without it `alpha` ends `exited`, which advances no edge (§ D1) and `bravo` never runs.
  const fakeCarriage = (argv, cwd) => {
    heldCalls.push({ argv, cwd });
    checkOutDone(path.resolve(cwd, '..', '..'), path.basename(cwd));
    return { status: 0 };
  };

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
  check('B1a the held seat GATES its dependent — bravo runs only behind alpha\'s check-out, and only alpha is carried',
    result.seats.join() === 'alpha,bravo' && result.foreground.map((f) => f.seat).join() === 'alpha'
      && result.ticks >= 2,
    `${JSON.stringify(result.foreground)} ticks=${result.ticks} (bravo cannot be in alpha's own pass — coord's frontier is read once per pass, BEFORE the carriage runs)`);

  // …and the BAR ITSELF, at the point the engine could detach one. The run above cannot reach it —
  // the carrier fires first, so a held seat is never `ready` when the enqueue pass looks — which is
  // exactly why the invariant is measured HERE rather than inferred from the run: an ordering is a
  // policy, and this is the structural bar under it. Both calls run against the SAME store, the
  // held one first, so the control proves the seat was enqueueable all along.
  const barGoal = makeGoal('fg-goal-bar');
  const barStore = openHeartStore({ dbPath: path.join(barGoal, 'heart.db') });
  const barRows = attached.seedTaskforce(barStore, barGoal, { profile: 'probe-fg' });
  // ⚠ COORD'S ANSWER IS HANDED IN, off the REAL fixture on disk — not a hand-typed map. Without it
  // `enqueueEligible` promotes nothing (the store may decline, never promote, § D1) and BOTH arms
  // below would pass for the wrong reason: the bar arm would be vacuous and its control would be
  // the thing that catches it, which is exactly the pairing that must not silently collapse.
  const { ready: barReady, rows: barReadyRows } = readySeats(barGoal);
  check('B1a coord offers `alpha` on the bar fixture — the precondition BOTH arms below rest on',
    Boolean(barReady) && barReady.has('alpha'),
    barReady ? `READY=${[...barReady.keys()].join()}` : 'coord refused to compute readiness');
  const heldBar = attached.enqueueEligible(barStore, barRows,
    { profile: 'probe-fg', goalFolder: barGoal, isHeld: attached.heldSeatPredicate(barGoal), ready: barReady, readyRows: barReadyRows });
  const queuedAfterBar = barStore.listQueue().map((q) => q.job_id);
  const freeBar = attached.enqueueEligible(barStore, barRows,
    { profile: 'probe-fg', goalFolder: barGoal, ready: barReady, readyRows: barReadyRows });
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
        '---\nseat: alpha\nharness: bash\nmodel: probe-fg\nhuman-interactive: "yes"\n---\n\nbody\n');
      fs.mkdirSync(path.join(quoted, 'seats', 'bravo'), { recursive: true });
      fs.writeFileSync(path.join(quoted, 'seats', 'bravo', 'seat.md'),
        '---\nseat: bravo\nharness: bash\nmodel: probe-fg\nhuman-interactive: yes # ratified 2026-08-09\n---\n\nbody\n');
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
    heldCalls[0].argv.join(' ') === `node ${CHECKOUT_JS}`
      && spawnConfig.launchSpecs['bash/probe-fg'].exec.argv.join(' ') === 'bash -c exec sleep 1 --model probe-fg',
    `argv=${JSON.stringify(heldCalls[0].argv)}`);

  const claudeGoal = makeGoal('fg-goal-claude');
  const claudeStore = openHeartStore({ dbPath: path.join(claudeGoal, 'heart.db') });
  attached.seedTaskforce(claudeStore, claudeGoal, {});
  // The cast selects the spec (7.787) — both seats onto the claude-harness one, because this
  // block's subject is the claude descriptor flag.
  for (const s of ['alpha', 'bravo']) recast(path.join(claudeGoal, 'seats', s), 'probe-fg-claude', 'claude');
  let claudeArgv = null;
  attached.runForegroundSeat({
    heartStore: claudeStore,
    seat: 'alpha',
    goalFolder: claudeGoal,
    launchSpecs: spawnConfig.launchSpecs,
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
  //
  // ⚠ THE NO-FILE CASE IS NO LONGER A FLAGLESS LAUNCH — IT IS A REFUSAL (7.787). The descriptor is
  // now the ONLY place a launch spec can be resolved from, so a seat with no `seat.md` cannot
  // launch at all and never reaches argv composition. The old failure mode (claude launched with a
  // flag pointing at nothing) is structurally unreachable, and this arm asserts THAT rather than
  // an argv that can no longer be produced. The flag's presence-when-the-file-exists half is
  // asserted above and is unchanged.
  let noDescArgv = null;
  attached.runForegroundSeat({
    heartStore: claudeStore,
    seat: 'bravo',
    goalFolder: claudeGoal,
    launchSpecs: spawnConfig.launchSpecs,
    tick: 1,
    now: new Date(),
    spawnForeground: (argv) => { noDescArgv = argv; return { status: 0 }; },
  });
  fs.unlinkSync(path.join(claudeGoal, 'seats', 'bravo', 'seat.md'));
  let noFileRefusal = null;
  try {
    attached.runForegroundSeat({
      heartStore: claudeStore,
      seat: 'bravo',
      goalFolder: claudeGoal,
      launchSpecs: spawnConfig.launchSpecs,
      tick: 1,
      now: new Date(),
      spawnForeground: (argv) => { noFileRefusal = `LAUNCHED ${argv.join(' ')}`; return { status: 0 }; },
    });
  } catch (err) { noFileRefusal = err.code; }
  check('B1c NO descriptor on disk ⇒ the launch is REFUSED (it can no longer reach argv at all), '
      + 'while a descriptor that IS there still carries the flag',
    noFileRefusal === 'E_UNCAST_SEAT' && /append-system-prompt-file/.test(noDescArgv.join(' ')),
    `withFile=${JSON.stringify(noDescArgv)} withoutFile=${noFileRefusal}`);
  claudeStore.close();

  // ── B1d · a profile that cannot carry a human REFUSES ───────────────────────────────────────
  say('');
  say('B1d — no `headed.tui` block ⇒ a refusal that names the seat and the profile');

  const refuseGoal = makeGoal('fg-goal-refuse');
  const refuseStore = openHeartStore({ dbPath: path.join(refuseGoal, 'heart.db') });
  // ⚠ THE CAST IS IN THE DESCRIPTOR NOW (7.787): `runForegroundSeat` reads the seat, not a
  // parameter, so which spec each arm exercises is decided by re-casting its seat.md. `alpha` gets
  // the headless-only spec (B1d's subject), `bravo` keeps the headed one (B1d's positive control).
  attached.seedTaskforce(refuseStore, refuseGoal, {});
  recast(path.join(refuseGoal, 'seats', 'alpha'), 'probe-fg-headless-only');
  let refusal = null;
  try {
    attached.runForegroundSeat({
      heartStore: refuseStore, seat: 'alpha', goalFolder: refuseGoal,
      launchSpecs: spawnConfig.launchSpecs,
      tick: 1, now: new Date(), spawnForeground: () => ({ status: 0 }),
    });
  } catch (err) { refusal = err.message; }
  check('B1d it refuses, naming the seat, the profile and the headed block',
    Boolean(refusal) && /alpha/.test(refusal) && /bash\/probe-fg-headless-only/.test(refusal) && /headed\.tui/.test(refusal),
    String(refusal).split('\n')[0]);
  let controlThrew = null;
  try {
    attached.runForegroundSeat({
      heartStore: refuseStore, seat: 'bravo', goalFolder: refuseGoal,
      launchSpecs: spawnConfig.launchSpecs,
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
  // ⚠ THE SEAT MUST STILL BE RUNNING WHEN THE KILL LANDS, and since 7.787 the ONLY way to say so is
  // the descriptor: this run used to carry `--profile probe-fg-slow` and the abolition dropped the
  // flag without recasting the seat, so alpha ran `probe-fg` — the INSTANT check-out — and every arm
  // below raced a seat that was already `done`. The 20.7 s sleep is not a margin, it is the fixture
  // CHOOSING the duration of the state these arms pin. Recast back to `probe-fg` before the re-runs.
  recast(path.join(killGoal, 'seats', 'alpha'), 'probe-fg-slow');
  // ⚠ `detached: true` + a signal to the PROCESS GROUP, not to the pid. `rbtv` is a wrapper that
  // execs the delegate, which in turn holds the foreground child: a SIGKILL aimed at the wrapper's
  // pid alone leaves the real runner ALIVE and still writing to this store, and the arms below then
  // measure a race between it and the re-run instead of a resume. (That is also the honest shape of
  // the event being simulated — closing a terminal signals the whole foreground group.)
  const victim = spawnProc(RBTV_BIN,
    ['run', killGoal, '--config', configPath, '--tick-ms', '300'],
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
  // NO reap is needed here, and that is a property of the kill above, not luck: the foreground
  // child is a plain `spawnSync` of the runner, so it INHERITS the runner's process group, and the
  // group kill above takes it with the runner. Measured 2026-08-13 — pre-kill the `sleep 20.7`
  // is alive with `pgid == victim.pid`, at +300 ms it is gone. This line used to be
  // `pkill -f 'sleep 20.7'`, which matched on command-line TEXT (the shape that self-kills operator
  // shells) and reaped nothing. If a future carriage detaches the child into its OWN group, capture
  // that pid at spawn and kill it — never re-introduce a pattern match.

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

  // The crash is over; the re-runs want the seat to FINISH, so alpha goes back to the check-out
  // spec (this is what the retired `--profile probe-fg` on both re-runs said).
  recast(path.join(killGoal, 'seats', 'alpha'), 'probe-fg');
  const afterKill = runCli(['run', killGoal, '--config', configPath, '--max-ticks', '3', '--json']);
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

  const granted = runCli(['run', killGoal, '--config', configPath,
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
  // Same abolition casualty as B1e: `--profile probe-fg-hold` went away without a recast, so A's
  // seat finished before B ever started and "A is still holding it" was a race. `probe-fg-hold`
  // sleeps 6 s and THEN checks out — long enough for B to be refused, and it still lets A complete.
  recast(path.join(holdGoal, 'seats', 'alpha'), 'probe-fg-hold');
  const holder = spawnProc(RBTV_BIN,
    ['run', holdGoal, '--config', configPath, '--tick-ms', '300', '--json'],
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
    ['run', holdGoal, '--config', configPath, '--max-ticks', '1', '--json'],
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
  const owStore = openHeartStore({ dbPath: path.join(overwriteGoal, 'heart.db') });
  attached.seedTaskforce(owStore, overwriteGoal, { profile: 'probe-fg' });
  const owResult = attached.runForegroundSeat({
    heartStore: owStore, seat: 'alpha', goalFolder: overwriteGoal,
    launchSpecs: spawnConfig.launchSpecs,
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
  say('B1f — a grant re-opens a DEAD seat, and since the loop re-fire a FINISHED one too');

  const view = openHeartStore({ dbPath: killStore });
  try {
    const rows = [{ seat: 'alpha', after: '' }, { seat: 'bravo', after: 'alpha' }];
    const plain = attached.executionsByJob(view);
    const withGrant = attached.executionsByJob(view, new Set(['alpha', 'bravo']));
    // This arm used to pin the OPPOSITE — "a grant can never re-open finished work". The loop
    // re-fire (owner ruling 2026-08-12, `concepts/loop.md`) moved that guard to the grant's MINT —
    // every writer of the grant is a deliberate act (the `--relaunch` CLI, the leader, the verdict
    // verb's `on-fail-relaunch` route) — so a granted seat's history is now hidden WHOLE, finished
    // rows included. LEG 5 of probe-relaunch-grant pins it on the daemon side (control + granted
    // pair against one attested check-out); this is the VIEW FUNCTION itself, on a store a real
    // killed-then-relaunched subprocess wrote. ⚠ The two OTHER citations this comment carried are
    // gone and were not replaced silently: `P5 of probe-block-and-queue-hold` died with that probe
    // (W2 deleted its subject), and probe-cross-lane-resume's F6 `done` half was removed in the
    // same change — since W2 that fixture's finishedness is a coord CHECK-OUT, which the engine's
    // own grant cannot lift, so restoring it would mean hand-minting into a schema coord owns.
    check('B1f a FINISHED seat IS re-opened by naming it in a grant — the loop re-fire, at the view',
      !withGrant.get(attached.jobIdFor('alpha'))
        && !withGrant.get(attached.jobIdFor('bravo'))
        && attached.seatState(rows[0], withGrant, new Set(), { ready: new Map([['alpha', []]]) }) === 'ready'
        // …and WITHOUT the grant the very same store reads `done`, so the grant is the only
        // difference between the two verdicts and this arm cannot pass on an empty view.
        && Boolean(plain.get(attached.jobIdFor('alpha')))
        && Boolean(plain.get(attached.jobIdFor('bravo')))
        && attached.seatState(rows[0], plain, new Set()) === 'done',
      `granted=${attached.seatState(rows[0], withGrant, new Set(), { ready: new Map([['alpha', []]]) })}`
        + ` · ungranted=${attached.seatState(rows[0], plain, new Set())}`);
    // …and the same call on a store where the seat is DEAD does re-open it. Measured on the
    // failed-only view built from this store's own first attempt.
    const deadOnly = new Map([[attached.jobIdFor('alpha'), plain.get(attached.jobIdFor('alpha')).filter((r) => r.status === 'failed')]]);
    check('B1f POSITIVE CONTROL: with only the failed attempt on record the seat reads `live`…',
      attached.seatState(rows[0], deadOnly, new Set()) === 'live');
    deadOnly.delete(attached.jobIdFor('alpha'));
    // ⚠ COORD'S TERM IS HANDED IN. `ready` is no longer derived from `after` here (§ D1), so this
    // arm's subject — the STORE half, "the grant hides the history and the seat is offerable again"
    // — is only reachable with the DAG half supplied. Its two neighbours above pin the other
    // direction: a store term (`done`, `live`) outranks coord's answer whatever it says.
    check('B1f …and the grant\'s view — its history hidden, nothing rewritten — reads `ready`',
      attached.seatState(rows[0], deadOnly, new Set(), { ready: new Map([['alpha', []]]) }) === 'ready'
        // …and WITHOUT coord's offer the very same view reads `waiting`: the store may decline, never promote.
        && attached.seatState(rows[0], deadOnly, new Set()) === 'waiting');
  } finally { view.close(); }

  // The reconciliation is SCOPED to the foreground marker: a detached row left non-terminal is the
  // ticker's crash sweep's business, and ending it here would race that sweep.
  const scopeStore = openHeartStore({ dbPath: path.join(tmp, 'scope.db') });
  scopeStore.registerJob({ jobId: 'seat-fg', actionType: 'launch-agent', function: 'x', argsSchema: JSON.stringify({ required: {}, optional: {} }), description: 'x', createdAt: '2026-08-10T00:00:00Z', updatedAt: '2026-08-10T00:00:00Z' });
  scopeStore.registerJob({ jobId: 'seat-detached', actionType: 'launch-agent', function: 'x', argsSchema: JSON.stringify({ required: {}, optional: {} }), description: 'x', createdAt: '2026-08-10T00:00:00Z', updatedAt: '2026-08-10T00:00:00Z' });
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
  // S-20 it was traceless — no launch ever went through the daemon door — and the reader of the day
  // (the edge-runner's check-out fast path, since retired) refused a traceless package wholesale.
  // The header itself must be born here, from the schema owner, since nothing else has written it.
  //
  // ⚠ A WAVE, NOT A CHAIN, AND THE SHAPE IS THE POINT: nothing here checks out, so the carrier's
  // own `exited` is the only disposition on either row — which is exactly what the two arms below
  // measure. A chained fixture could not reach the second seat at all, because `exited` advances no
  // edge (§ D1). The stall that produces is CORRECT and is measured at B1a; here it would only hide
  // the subject.
  const allFg = makeWaveGoal('fg-goal-all-foreground', ['alpha', 'bravo']);
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
  // for the rest of the goal's life. Measured THROUGH THE REAL READER, in python, because the
  // claim is about what `coord` says — not about a cell this probe can inspect.
  //
  // ⚠ THE OPEN-SITTING DERIVATION MOVED HERE when `jobs/goal-state-job.py` was deleted
  // (`build/one-readiness-predicate.md`, owner-ruled 2026-08-11 — it was a THIRD reader of the
  // readiness question). Nothing was reimplemented: that helper was twenty lines over
  // `sessions.csv` using COORD'S OWN primitives (`sessions_csv`, `read_csv_table`, `SESSIONS_COLS`,
  // `pad_row`), and those primitives are what run below. The parse stays coord's; only the wrapper
  // is gone. This is a PROBE computing an assertion, never production code deciding anything, so it
  // mints no second reader of the state it checks.
  check('B1h every foreground row is CLOSED — `ended` stamped, disposition `exited` by the `kit`',
    allTrace.rows.every((r) => r.ended && r.disposition === 'exited' && r['disposition-writer'] === 'kit'),
    allTrace.rows.map((r) => `${r.seat}:${r.ended || 'OPEN'}/${r.disposition || '-'}`).join(' '));

  const askPython = (src) => spawnSync(requirePythonCmd(), ['-c', src], { encoding: 'utf8', cwd: IGNITE_SRC });
  const readersSay = askPython(`
import sys, pathlib, importlib.util
sys.path.insert(0, 'team-kit')
import coord
def open_session_seats(pkg):
    path = coord.sessions_csv(pkg)
    if not path.exists():
        return set()
    header, rows = coord.read_csv_table(path, coord.SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    if not {'seat', 'ended'} <= set(idx):
        return set()
    out = set()
    for r in rows:
        coord.pad_row(r, header)
        seat = r[idx['seat']].strip()
        if seat and not r[idx['ended']].strip():
            out.add(seat)
    return out
pkg = pathlib.Path(${JSON.stringify(allFg)})
print('OPEN=' + ','.join(sorted(open_session_seats(pkg))))
print('DISP=' + ','.join('%s:%s' % (s, coord.session_disposition(pkg, s)) for s in ('alpha', 'bravo')))
`);
  const readerOut = `${readersSay.stdout || ''}${readersSay.stderr || ''}`.trim();
  check('B1h no FINISHED seat is left reading as an OPEN sitting in the trace (the F2 harm)',
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

  const shipped = loadConfig(COMMITTED_CONFIG).launchSpecs;
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
  const pinStore = openHeartStore({ dbPath: path.join(pinGoal, 'heart.db') });
  attached.seedTaskforce(pinStore, pinGoal, {});
  recast(path.join(pinGoal, 'seats', 'alpha'), 'claude-fable-5', 'claude');
  let pinArgv = null;
  attached.runForegroundSeat({
    heartStore: pinStore, seat: 'alpha', goalFolder: pinGoal,
    launchSpecs: shipped,
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
