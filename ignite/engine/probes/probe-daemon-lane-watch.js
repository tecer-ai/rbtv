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
// SEVEN MUTATION ARMS (L8) run the real pass against a single-string mutation of `lane-watch.js`,
// compiled in memory (no file is written into the source tree), and REQUIRE it to go red:
//   · the assignment is ignored     -> the daemon seeds a CONSOLE goal
//   · the run lock is ignored       -> the daemon seeds a goal a console runner is attached to
//   · the watch call is removed     -> the call-site arm reds (the "nothing picks a goal up" state)
//   · the unknown-profile guard off -> an unrunnable goal leaves ORPHAN job rows in the store
//   · the no-profile branch silent  -> the only line saying why a goal never starts disappears
//   · the human-interactive report off -> the seat is dispatched headless with nothing said
//   · the seat's fallback ARM not read -> the report degrades to the pre-7.626 one
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
const { requirePythonCmd } = require('../../lib/python-cmd');

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
const badGoal = makeGoal('bad-profile-goal');   // assigned daemon with a profile the config lacks
const noProfGoal = makeGoal('no-profile-goal'); // assigned daemon by hand, naming no profile at all
const hiGoal = makeGoal('human-interactive-goal');
// The F1 fixture: an INTERACTIVE goal whose first seat declares `human-interactive:`. In the
// attached lane that seat is carried in the terminal; in this one there is no terminal at all —
// and since 7.626 that is fine, because the goal's channel is the owner surface and the seat's
// declared `fallback:` is what executes there.
fs.writeFileSync(path.join(hiGoal, 'execution-mode'), 'interactive\n');
fs.writeFileSync(path.join(hiGoal, 'seats', 'alpha', 'seat.md'),
  '---\nseat: alpha\nhuman-interactive: yes\nfallback: block-and-queue\n---\n\nbody\n');
// THE 7.626 RESIDUAL: the same shape with NO `fallback:` — a `component-lint --check
// interactive-fallback` violation that reached dispatch. It is the ONE case the pass must still
// be loud about, and it needs its own goal because the arm-declared case must stay quiet in the
// same run for the pair to discriminate.
// The PAUSE fixture: assigned to the daemon and then PAUSED by prefixing the marker. Its own goal
// because the pause must be measured while other goals ARE being adopted in the same pass — a
// "not adopted" that holds when nothing is adopted measures nothing.
const pausedGoal = makeGoal('paused-goal');
const armlessGoal = makeGoal('armless-goal');
fs.writeFileSync(path.join(armlessGoal, 'execution-mode'), 'interactive\n');
fs.writeFileSync(path.join(armlessGoal, 'seats', 'alpha', 'seat.md'),
  '---\nseat: alpha\nhuman-interactive: yes\n---\n\nbody\n');

const GOAL_CLI = path.join(IGNITE_SRC, 'capabilities', 'goals-tree', 'tool', 'goal_cli.py');
// The CLI is the WRITER of the marker file, and it must work with no daemon anywhere — which is
// the whole reason the trigger is a file. Run it as the operator does: a subprocess, no engine.
function laneCli(args, { expectRefusal = false } = {}) {
  try {
    // RBTV_IGNITE_CONFIG_PATH points the CLI's profile-name check at THIS fixture's config — the
    // same override the daemon honours. Without it the door would validate `probe-lane` against
    // the shipped config, where it does not exist, and every write here would refuse.
    const out = execFileSync(requirePythonCmd(), [GOAL_CLI, '--root', goalsRoot, 'lane', ...args],
      { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, RBTV_IGNITE_CONFIG_PATH: configPath } });
    return { ok: true, out };
  } catch (err) {
    if (!expectRefusal) throw new Error(`rbtv-goal lane ${args.join(' ')} failed: ${err.stderr || err.message}`);
    return { ok: false, out: String(err.stdout || '') + String(err.stderr || '') };
  }
}
// The lane verb's SIBLINGS (`pause` / `resume`) — same CLI, not under `lane`. Separate helper
// rather than a parameter on the one above, because that one's whole shape is "the lane verb".
function goalCli(verb, args) {
  return execFileSync(requirePythonCmd(), [GOAL_CLI, '--root', goalsRoot, verb, ...args],
    { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, RBTV_IGNITE_CONFIG_PATH: configPath } });
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

  // ── L0 · THE `taskforce.csv` READER AND THE `after` CELL GRAMMAR ────────────────────────────
  //
  // THE DEFECT: `seeding.js#readCsv` split every line on a bare comma, and `seatState` read the
  // WHOLE `after` cell as ONE seat name. Both halves are measured here, against the REAL Python
  // writer and the REAL Python grammar — no hand-written fixture line, no re-stated regex.
  //
  //   the writer   `team-kit/materialize-seats.py#_render_csv_line` (`csv.writer`, QUOTE_MINIMAL)
  //   the grammar  `team-kit/coord.py#parse_after_member` — THE authority, of which the JS side is
  //                a mirror. Both are loaded by path in a subprocess, exactly as
  //                `goal_cli.py#after_member_grammar` reaches the grammar: imported, never copied.
  say('L0 — the taskforce reader and the `after` cell grammar, pinned to their Python originals');
  const seeding = require('../seeding');
  const TEAM_KIT = path.join(IGNITE_SRC, 'team-kit');
  function pythonJson(body) {
    const script = path.join(tmp, `l0-${Math.random().toString(36).slice(2)}.py`);
    fs.writeFileSync(script, body);
    return JSON.parse(execFileSync(requirePythonCmd(), [script], { encoding: 'utf8', cwd: TEAM_KIT }));
  }
  const LOADER = 'import importlib.util,sys,json\n'
    + 'sys.dont_write_bytecode=True\n'
    + 'sys.path.insert(0, ".")\n'
    + 'def load(name, fname):\n'
    + '    spec = importlib.util.spec_from_file_location(name, fname)\n'
    + '    mod = importlib.util.module_from_spec(spec)\n'
    + '    spec.loader.exec_module(mod)\n'
    + '    return mod\n';

  // L0a — THE QUOTED MULTI-PREDECESSOR CELL. The row is rendered by the writer itself, so the
  // quoting under test is the quoting production emits and not this probe's idea of it.
  const SIX = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'];
  const rendered = pythonJson(LOADER
    + 'ms = load("ms", "materialize-seats.py")\n'
    + `print(json.dumps(ms._render_csv_line(["tf-l0", "check-assembler", "${SIX.join(',')}", `
    + '"claude", "opus", "high", "", "m-1"])))\n');
  check('L0a the REAL writer QUOTES a multi-predecessor `after` cell — the shape the reader must survive',
    rendered.includes(`"${SIX.join(',')}"`), rendered);
  const l0Dir = path.join(tmp, 'l0');
  fs.mkdirSync(l0Dir, { recursive: true });
  const l0Csv = path.join(l0Dir, 'taskforce.csv');
  fs.writeFileSync(l0Csv,
    'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n'
    + `${rendered}\n`
    + 'tf-l0,solo,p1,claude,opus,high,,m-1\n');
  const l0Rows = seeding.readCsv(l0Csv);
  const assembler = l0Rows.find((r) => r.seat === 'check-assembler');
  check('L0a the reader parses that row WITHOUT SHIFTING: the quoted cell is ONE field and every '
    + 'column to its right keeps its own value (before the fix, `harness` read `p2`)',
    Boolean(assembler) && assembler.after === SIX.join(',') && assembler.harness === 'claude'
      && assembler.model === 'opus' && assembler.effort === 'high'
      && assembler['milestone-id'] === 'm-1',
    JSON.stringify(assembler));
  check('L0a …and the cell grammar reads SIX predecessors from it, not one seat named "p1,p2,…"',
    seeding.afterMembers(assembler.after).map((m) => m.name).join('|') === SIX.join('|'),
    JSON.stringify(seeding.afterMembers(assembler.after).map((m) => m.name)));

  // L0b — THE CROSS-LANGUAGE PIN. Two languages, ONE grammar, compared term by term over the whole
  // token table — guards, an alternate, a guard value CARRYING a `|` (the ordering property), a
  // malformed guard, a double bracket group. A divergence on ANY of them is red: the JS side is a
  // mirror, and a mirror that drifts is the two-readings defect 7.424 closed inside Python.
  const TOKENS = ['a', ' a ', 'a[k=v]', 'a[k=x|y]', 'a|b', 'a[g=y]|b', 'a[nokey]', 'a[k=]',
    'a[k=v][j=w]', 'a[=v]', '', 'plan-dag-structurer[planning-mode=full]'];
  const theirs = pythonJson(LOADER
    + 'c = load("_c", "coord.py")\n'
    + `print(json.dumps([list(c.parse_after_member(t)) for t in ${JSON.stringify(TOKENS)}]))\n`);
  const mine = TOKENS.map((t) => {
    const m = seeding.parseAfterMember(t);
    return [m.name, m.key, m.value, m.unsupported];
  });
  check('L0b the JS member grammar answers EXACTLY what `coord.py#parse_after_member` answers, on '
    + 'every token — including `a[k=x|y]`, whose `|` is inside a guard and is NOT an alternate '
    + '(brackets neutralised BEFORE the alternate test, coord\'s own load-bearing order)',
    JSON.stringify(mine) === JSON.stringify(theirs),
    `js=${JSON.stringify(mine)} py=${JSON.stringify(theirs)}`);

  // L0c — NOTHING CHANGES FOR A SINGLE BARE MEMBER. The oracle is the PRE-FIX line itself,
  // `after && !isDone(after)`, run over the same inputs: the fix is allowed to release seats that
  // were wrongly parked, and is NOT allowed to answer differently on the cells that already worked.
  {
    // The list carries a GUARDED and an ALTERNATE single-member cell on purpose: both are
    // `waiting` under the old predicate (neither string is in `done`) and must stay `waiting`
    // under the new one. Without them the oracle only ever saw cells the fix could not change,
    // so it could not discriminate a fix that wrongly RELEASED a guard from one that did not.
    const bare = ['', 'alpha', 'bravo', 'never-finished',
      'alpha[planning-mode=full]', 'alpha|bravo'];
    const doneSet = new Set(['alpha']);
    const oldState = (afterCell) => {
      const after = (afterCell || '').trim();
      if (after && !doneSet.has(after)) return 'waiting';
      return 'ready';
    };
    const diverged = bare.filter((cell) => seeding.seatState(
      { seat: 'x', after: cell }, new Map(), new Set(), { done: doneSet }) !== oldState(cell));
    check('L0c a SINGLE-member (or empty) `after` cell answers byte-identically to the pre-fix '
      + 'predicate — including a guarded and an alternate cell, which stay `waiting` under both',
      diverged.length === 0, `diverged on: ${JSON.stringify(diverged)}`);

    // THE SHORT-CIRCUIT ABOVE THE `after` READ. A queued seat answers `queued` without the cell
    // ever being consulted — so the cell here is one the after-walk would park on, and a
    // `queued` answer is only reachable through the early return.
    check('L0c a QUEUED seat answers `queued` from the job id alone — the `after` cell (an '
      + 'unevaluable guard here) is never reached',
      seeding.seatState({ seat: 'q', after: 'never-finished[g=v]' }, new Map(),
        new Set([seeding.jobIdFor('q')]), { done: doneSet }) === 'queued');

    // L0d — THE LOUD SKIP. A guard and an alternate are members this lane has no evaluator for
    // (coord discharges a guard against `coordination/guard-values.csv`; `edge-runner-job.py`
    // against the predecessor's validated output — neither surface is on the daemon lane). They
    // hold the seat, and — the part that is NEW — they SAY SO.
    const guarded = { seat: 'g', after: 'alpha[planning-mode=full]' };
    const alternate = { seat: 'o', after: 'alpha|bravo' };
    check('L0d a GUARDED member leaves the seat `waiting` even though its predecessor IS done — a '
      + 'guard never auto-satisfies, which is coord\'s own fail-safe direction',
      seeding.seatState(guarded, new Map(), new Set(), { done: doneSet }) === 'waiting');
    check('L0d an ALTERNATE does the same — `coord.py` calls it `<unsupported-alternate>` and blocks',
      seeding.seatState(alternate, new Map(), new Set(), { done: doneSet }) === 'waiting');
    check('L0d …and BOTH are NAMED, never silently parked: `unevaluableAfter` hands the operator '
      + 'the exact member that is holding the seat',
      seeding.unevaluableAfter(guarded).join() === 'alpha[planning-mode=full]'
        && seeding.unevaluableAfter(alternate).join() === 'alpha|bravo',
      JSON.stringify([seeding.unevaluableAfter(guarded), seeding.unevaluableAfter(alternate)]));
    check('L0d a MULTI-member bare cell is AND-joined — every predecessor, not the first',
      seeding.seatState({ seat: 'm', after: 'alpha,bravo' }, new Map(), new Set(), { done: doneSet }) === 'waiting'
        && seeding.seatState({ seat: 'm', after: 'alpha,alpha' }, new Map(), new Set(), { done: doneSet }) === 'ready');
  }
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
  // ⚑ THE PAUSE MARKER, and it needs NO reader change — which is the arm. A pause is written by
  // PREFIXING the assignment (`paused daemon <profile>`), so the FIRST token stops being `daemon`
  // and the fail-closed default catches it: the goal reads `console`, the daemon does not adopt
  // it, and the profile it will return to is preserved verbatim in the marker for the resume to
  // put back. Pinned here because the pause verb DEPENDS on this reader behaviour — a reader that
  // grew tolerant of a leading word would silently un-pause every paused goal on the tree.
  const paused = readsAs('paused daemon probe-lane\n');
  check('L1 a PAUSED marker (`paused daemon <profile>`) reads as the CONSOLE lane — the pause verb '
    + 'rides the fail-closed default rather than a new word in this reader',
    paused.lane === 'console' && paused.profile === null && paused.present === true
      && paused.raw === 'paused daemon probe-lane',
    JSON.stringify(paused));
  fs.unlinkSync(lanePath(grammar));

  // ── L2 · THE CLI IS THE WRITER, AND IT WORKS DAEMON-DOWN ────────────────────────────────────
  say('');
  say('L2 — `rbtv goal lane` writes the marker, with no daemon in the picture');
  const refused = laneCli(['switch-goal', '--set', 'daemon'], { expectRefusal: true });
  check('L2 `--set daemon` WITHOUT `--profile` is REFUSED — a goal handed to the daemon that names no '
    + 'launch profile cannot run, and the refusal is at the door rather than a journal warning at 03:00',
    refused.ok === false && /--profile/.test(refused.out) && !fs.existsSync(lanePath(switchGoal)),
    refused.out.trim().split('\n').pop());
  // ⚑ THE DOOR CHECK (review F2). A `--profile` typo used to be accepted here: the marker was
  // written, the daemon adopted the goal, `seedTaskforce` registered a job row per seat, and only
  // then did `enqueue` refuse `E_UNKNOWN_PROFILE` — leaving orphan rows and a goal that threw
  // every cadence forever. The name is now checked against the SHARED CONFIG at the door.
  const badName = laneCli(['switch-goal', '--set', 'daemon', '--profile', 'probe-laneX'], { expectRefusal: true });
  check('L2 `--profile <not-in-the-shared-config>` is REFUSED at the door, naming the valid set — a '
    + 'typo cannot reach the daemon at all, and nothing is written',
    badName.ok === false && /probe-lane/.test(badName.out) && !fs.existsSync(lanePath(switchGoal)),
    badName.out.trim().split('\n').pop());

  laneCli(['switch-goal', '--set', 'daemon', '--profile', 'probe-lane']);
  laneCli(['locked-goal', '--set', 'daemon', '--profile', 'probe-lane']);
  laneCli(['held-goal', '--set', 'daemon', '--profile', 'probe-lane']);
  laneCli(['human-interactive-goal', '--set', 'daemon', '--profile', 'probe-lane']);
  laneCli(['armless-goal', '--set', 'daemon', '--profile', 'probe-lane']);
  laneCli(['console-goal', '--set', 'console']);
  // Assigned to the daemon by the CLI, then PAUSED by prefixing its marker — the pause is a
  // prefix, so the assignment (and the profile) survives it verbatim.
  laneCli(['paused-goal', '--set', 'daemon', '--profile', 'probe-lane']);
  goalCli('pause', ['paused-goal']);
  check('L2 `rbtv-goal pause` stashes the assignment behind a `paused ` PREFIX — the profile it '
    + 'returns to is kept verbatim, and the DAEMON\'s reader resolves the result to `console` '
    + 'with no word of its own (two languages, one grammar, cross-checked)',
    fs.readFileSync(lanePath(pausedGoal), 'utf8').trim() === 'paused daemon probe-lane'
      && laneWatch.readLane(pausedGoal).lane === 'console',
    JSON.stringify(laneWatch.readLane(pausedGoal)));
  // The two BROKEN markers only reachable by hand, since the door refuses both spellings.
  fs.writeFileSync(lanePath(badGoal), 'daemon probe-laneX\n');
  fs.writeFileSync(lanePath(noProfGoal), 'daemon\n');
  check('L2 the write is ATOMIC — a temp file is renamed into place and nothing is left beside it',
    !fs.existsSync(path.join(switchGoal, `${laneWatch.LANE_FILE}.tmp`))
      && fs.readFileSync(lanePath(switchGoal), 'utf8') === 'daemon probe-lane\n');
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
      // ⚑ THE LIVE-SESSION CAP IS RAISED FOR THIS FIXTURE, and it has to be. The default is 2, so
      // one tick dispatches the first two queued seats and leaves the rest — which made L6's
      // "the daemon REALLY dispatched alpha" a claim about QUEUE ORDER: adding one more goal to the
      // tree (7.626's armless fixture) starved `switch-goal` and reddened four unrelated arms. The
      // cap is not what any arm here measures.
      tickerConfig: { max_live_agent_sessions: 16 },
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
  // ⚑ THE PAUSED GOAL — the same two facts as the console control, for a goal that IS assigned to
  // the daemon and is merely held. It must be skipped for the ordinary not-assigned reason and
  // leave no trace in the store, or a pause would be a pause in name only.
  check('L5 a PAUSED goal (`paused daemon <profile>`) is NOT adopted — skipped for the ordinary '
    + 'not-assigned reason, with the profile it returns to still written in its marker',
    !adoptedNames.includes('paused-goal')
      && pass1.skipped.some((s) => s.goal === 'paused-goal' && s.reason === 'not-assigned-to-the-daemon')
      && fs.readFileSync(lanePath(pausedGoal), 'utf8').trim() === 'paused daemon probe-lane',
    JSON.stringify(pass1.skipped.filter((s) => s.goal === 'paused-goal')));
  check('L5 …and NOTHING of the paused goal reached the daemon\'s store either',
    (() => {
      const s = openHeartStore({ dbPath: daemonStorePath, profiles: cfg.profiles });
      const d = s.dump();
      s.close();
      return !JSON.stringify([d.jobs, d.queue, d.jobs_log]).includes('paused-goal');
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

  // ── L5b · THE TWO BROKEN MARKERS, and what they cost (review F2/F3) ─────────────────────────
  const badSkip = pass1.skipped.find((s) => s.goal === 'bad-profile-goal');
  check('L5b a marker naming a profile the shared config does not carry is SKIPPED, typed, and '
    + 'NOTHING is registered — the guard runs BEFORE seedTaskforce, so no orphan job rows survive '
    + 'a marker that can never run',
    Boolean(badSkip) && badSkip.reason === 'unknown-profile'
      && (() => {
        const s = openHeartStore({ dbPath: daemonStorePath, profiles: cfg.profiles });
        const d = s.dump(); s.close();
        return !JSON.stringify([d.jobs, d.queue, d.jobs_log]).includes('bad-profile-goal');
      })(),
    JSON.stringify(badSkip || 'not skipped at all'));
  check('L5b …and it says so ONCE, with the fix and the known set on the line an operator reads',
    log1.some((m) => m.goal === 'bad-profile-goal' && m.level === 'warn'
      && /shared config does not carry/.test(m.message || '')
      && Array.isArray(m.known) && m.known.includes('probe-lane') && /rbtv goal lane/.test(m.fix || '')),
    JSON.stringify(log1.filter((m) => m.goal === 'bad-profile-goal').map((m) => m.level)));
  const noProfSkip = pass1.skipped.find((s) => s.goal === 'no-profile-goal');
  check('L5b a `daemon` marker naming NO profile is SKIPPED with its own reason and its own fix hint '
    + '(the branch a mutation used to survive because nothing measured it)',
    Boolean(noProfSkip) && noProfSkip.reason === 'no-profile-in-the-assignment'
      && log1.some((m) => m.goal === 'no-profile-goal' && m.level === 'warn'
        && /NO launch profile/.test(m.message || '')
        && /--set daemon --profile/.test(m.fix || '')),
    JSON.stringify(noProfSkip || 'not skipped at all'));

  // ── L5c · THE FAILURE IS BOUNDED, and un-bounds itself when the marker changes ───────────────
  {
    const log2 = [];
    const engine = createEngine({
      dbPath: daemonStorePath, profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    try { laneWatch.runLaneWatch({ goalsRoot, engine, logger: collectingLogger(log2) }); } finally { engine.close(); }
    const lvls = log2.filter((m) => m.goal === 'bad-profile-goal').map((m) => m.level);
    check('L5c the SECOND pass over the same broken marker drops to debug — at a 10 s cadence the '
      + 'loud version is ~8,600 identical lines a day for a condition only a human can change',
      lvls.length > 0 && !lvls.includes('warn'), JSON.stringify(lvls));

    const log3 = [];
    fs.writeFileSync(lanePath(badGoal), 'daemon probe-laneY\n');    // somebody EDITED it, still wrong
    const engine3 = createEngine({
      dbPath: daemonStorePath, profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    try { laneWatch.runLaneWatch({ goalsRoot, engine: engine3, logger: collectingLogger(log3) }); } finally { engine3.close(); }
    check('L5c …and it is LOUD again the moment the marker text changes — quiet must never mean '
      + 'forgotten, so the memo is keyed on the marker, not on the goal',
      log3.some((m) => m.goal === 'bad-profile-goal' && m.level === 'warn'),
      JSON.stringify(log3.filter((m) => m.goal === 'bad-profile-goal').map((m) => m.level)));
    fs.writeFileSync(lanePath(badGoal), 'daemon probe-laneX\n');
  }

  // ── L5d · THE HUMAN-INTERACTIVE SEAT IS DISPATCHED, AND ITS ARM IS REPORTED (7.626) ──────────
  //
  // The BEHAVIOUR is the owner's ruled default and is unchanged: the daemon dispatches the seat
  // headless, where the attached lane carries it in a terminal. What 7.626 changed is that the
  // seat's declared `fallback:` now EXECUTES — at the ferry, on the goal channel — so the pass no
  // longer warns about a step-over. It reports WHICH ARM each dispatched seat runs under (the one
  // thing an operator cannot derive from the seat list), and warns only for the seat that declared
  // none.
  const hiPickup = pass1.adopted.find((a) => a.goal === 'human-interactive-goal');
  const armlessPickup = pass1.adopted.find((a) => a.goal === 'armless-goal');
  check('L5d the daemon DOES dispatch the human-interactive seat — unchanged, and ruled: there is no '
    + 'terminal here and #d-s19 says there need not be one (the goal channel is the owner surface)',
    Boolean(hiPickup) && hiPickup.enqueued.includes('alpha'),
    hiPickup ? JSON.stringify(hiPickup.enqueued) : 'goal not adopted');
  check('L5d …and its declared ARM rides the pass\'s own return — `alpha: block-and-queue`, read '
    + 'through the ferry\'s OWN frontmatter reader, never a second parser',
    Boolean(hiPickup) && hiPickup.humanInteractiveDispatched
      && hiPickup.humanInteractiveDispatched.alpha === 'block-and-queue',
    hiPickup ? JSON.stringify(hiPickup.humanInteractiveDispatched || null) : 'goal not adopted');
  check('L5d …and a DECLARED arm is QUIET: no warn for that goal, because nothing is being stepped '
    + 'over any more — the arm executes at the ferry',
    !log1.some((m) => m.goal === 'human-interactive-goal' && m.level === 'warn'),
    JSON.stringify(log1.filter((m) => m.goal === 'human-interactive-goal').map((m) => m.level)));
  check('L5d THE RESIDUAL, and the PAIR that makes the quiet above meaningful: a flagged seat with '
    + 'NO `fallback:` IS warned about, named to `component-lint`, in the SAME pass',
    Boolean(armlessPickup) && armlessPickup.enqueued.includes('alpha')
      && armlessPickup.humanInteractiveDispatched
      && armlessPickup.humanInteractiveDispatched.alpha === null
      && log1.some((m) => m.goal === 'armless-goal' && m.level === 'warn'
        && /NO declared `fallback:`/.test(m.message || '') && /component-lint/.test(m.message || '')),
    JSON.stringify(log1.filter((m) => m.goal === 'armless-goal').map((m) => `${m.level}`)));
  check('L5d CONTROL: an AUTONOMOUS goal\'s seats are never reported as human-interactive — the '
    + 'report tracks the two gates, not the mere presence of the pass',
    !Object.hasOwn(pass1.adopted.find((a) => a.goal === 'switch-goal') || {}, 'humanInteractiveDispatched'));

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
      "    return { lane: CONSOLE, profile: null, present: true, raw: text };",
      "    return { lane: DAEMON, profile: 'probe-lane', present: true, raw: text };");
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

  // M4 · THE UNKNOWN-PROFILE GUARD REMOVED — the state review F2 measured: `seedTaskforce` registers
  // a job row per seat, `enqueue` then refuses, and the store keeps orphan rows for a goal that can
  // never run. The arm reads the STORE, not the skip list, because the harm is what was written.
  {
    const mutant = mutantWatch(
      '    if (!Object.hasOwn(known, profile)) {',
      '    if (false) {');
    const mutRoot = path.join(tmp, 'm4');
    fs.cpSync(goalsRoot, mutRoot, { recursive: true });
    const dbPath = path.join(tmp, 'm4.db');
    const engine = createEngine({
      dbPath, profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    try { mutant({ goalsRoot: mutRoot, engine }); } finally { engine.close(); }
    const s = openHeartStore({ dbPath, profiles: cfg.profiles });
    const d = s.dump(); s.close();
    check('L8 M4 unknown-profile guard REMOVED -> the unrunnable goal leaves orphan job rows in the '
      + 'daemon store (L5b RED), which is exactly the harm the ordering fixes',
      JSON.stringify(d.jobs).includes('bad-profile-goal'),
      `job ids: ${(d.jobs || []).map((j) => j.job_id).filter((i) => /bad-profile/.test(i)).join(', ') || 'none'}`);
  }

  // M5 · THE NO-PROFILE BRANCH REMOVED — review F3: this branch shipped unmeasured, and a mutation
  // of it left the probe green.
  {
    const mutant = mutantWatch(
      "      skipped.push({ goal, reason: 'no-profile-in-the-assignment' });",
      "      skipped.push({ goal, reason: 'no-profile-in-the-assignment' }); continue;");
    const mutRoot = path.join(tmp, 'm5');
    fs.cpSync(goalsRoot, mutRoot, { recursive: true });
    const log = [];
    const engine = createEngine({
      dbPath: path.join(tmp, 'm5.db'), profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    try { mutant({ goalsRoot: mutRoot, engine, logger: collectingLogger(log) }); } finally { engine.close(); }
    check('L8 M5 the no-profile branch skips SILENTLY -> the operator loses the only line that says '
      + 'why the goal never starts (L5b RED)',
      !log.some((m) => m.goal === 'no-profile-goal' && /NO launch profile/.test(m.message || '')),
      `lines for that goal: ${log.filter((m) => m.goal === 'no-profile-goal').length}`);
  }

  // M6 · THE HUMAN-INTERACTIVE REPORT REMOVED — the silence review F1 named, still reproduced
  // after 7.626 turned the report from a warn into an arm map.
  {
    const mutant = mutantWatch(
      '        if (!isHeld(seat)) continue;',
      '        if (true) continue;');
    const mutRoot = path.join(tmp, 'm6');
    fs.cpSync(goalsRoot, mutRoot, { recursive: true });
    // heldSeatPredicate resolves the workspace root from the goal folder's own depth, so the copy
    // is placed at the SAME depth the real tree has — otherwise the mutant would look green for
    // the wrong reason (an unresolvable descriptor rather than a removed report).
    const log = [];
    const engine = createEngine({
      dbPath: path.join(tmp, 'm6.db'), profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    let pass;
    try { pass = mutant({ goalsRoot, engine, logger: collectingLogger(log) }); } finally { engine.close(); }
    const hi = pass.adopted.find((a) => a.goal === 'human-interactive-goal');
    check('L8 M6 the human-interactive report REMOVED -> the daemon dispatches the seat with nothing '
      + 'said (L5d RED) — the silence, reproduced',
      Boolean(hi) && !hi.humanInteractiveDispatched
        && !log.some((m) => m.goal === 'armless-goal' && m.level === 'warn'),
      hi ? JSON.stringify(hi.humanInteractiveDispatched || null) : 'goal not adopted');
  }

  // M7 · THE ARM IS NOT READ (7.626) — the report survives but every seat reads UNDECLARED, so the
  // arm-bearing goal loses its arm AND acquires the residual warn that belongs to the other one.
  // It is the discriminator between "the pass reports human-interactive seats" (M6's claim) and
  // "the pass reports WHICH ARM each one runs under" (this row's).
  {
    const mutant = mutantWatch(
      '        const arm = seatFallback(goalFolder, seat);',
      '        const arm = null;');
    // ⚑ ITS OWN FRESH GOAL, and that is not tidiness. By this point the real passes have DISPATCHED
    // the shared fixture's human-interactive seat, so its execution-record row holds it `foreign` in
    // any other store — the mutant would enqueue nothing, report nothing, and the arm would go green
    // against a pass that never ran. A goal nothing has touched is the only honest input here.
    const m7Goal = makeGoal('m7-arm-goal');
    fs.writeFileSync(path.join(m7Goal, 'execution-mode'), 'interactive\n');
    fs.writeFileSync(path.join(m7Goal, 'seats', 'alpha', 'seat.md'),
      '---\nseat: alpha\nhuman-interactive: yes\nfallback: block-and-queue\n---\n\nbody\n');
    laneCli(['m7-arm-goal', '--set', 'daemon', '--profile', 'probe-lane']);
    const log = [];
    const engine = createEngine({
      dbPath: path.join(tmp, 'm7.db'), profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    let pass;
    try { pass = mutant({ goalsRoot, engine, logger: collectingLogger(log) }); } finally { engine.close(); }
    const hi = pass.adopted.find((a) => a.goal === 'm7-arm-goal');
    check('L8 M7 the ARM is never read -> a `block-and-queue` seat reports NO arm and is warned about '
      + 'as if it declared none (L5d RED) — the report degrades to the pre-7.626 one',
      Boolean(hi) && hi.enqueued.includes('alpha')
        && hi.humanInteractiveDispatched && hi.humanInteractiveDispatched.alpha === null
        && log.some((m) => m.goal === 'm7-arm-goal' && m.level === 'warn'),
      hi ? JSON.stringify(hi.humanInteractiveDispatched || null) : 'goal not adopted');
    // THE CONTROL, in the same block: the UNMUTATED pass over the SAME fresh goal reports the arm
    // and stays quiet — so the red above is the mutation and not the fixture.
    const clog = [];
    const cengine = createEngine({
      dbPath: path.join(tmp, 'm7-control.db'), profiles: cfg.profiles, spawnConfigPath: configPath, userManager: false,
    });
    let cpass;
    try { cpass = laneWatch.runLaneWatch({ goalsRoot, engine: cengine, logger: collectingLogger(clog) }); } finally { cengine.close(); }
    const chi = cpass.adopted.find((a) => a.goal === 'm7-arm-goal');
    check('L8 M7 CONTROL: the UNMUTATED pass over that same untouched goal reports `block-and-queue` '
      + 'and warns about nothing',
      Boolean(chi) && chi.humanInteractiveDispatched
        && chi.humanInteractiveDispatched.alpha === 'block-and-queue'
        && !clog.some((m) => m.goal === 'm7-arm-goal' && m.level === 'warn'),
      chi ? JSON.stringify(chi.humanInteractiveDispatched || null) : 'goal not adopted');
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
      + 'end to end with nothing re-run. It refuses an unknown profile at BOTH doors and registers '
      + 'nothing for one; its failure lines are bounded per marker and go loud again the moment the '
      + 'marker changes; and it REPORTS the human-interactive seat it knowingly dispatches headless '
      + '(behaviour unchanged, 7.626 owns the fix). Six mutations red.');
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
