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

// The same harness pointed at `seeding.js` instead, for L9. It needs the extra step because
// `index.js:37` DESTRUCTURES `seedGoal` at module load — recompiling `seeding.js` alone would leave
// `createEngine` closed over the real one — so the mutant is placed in `require.cache` under
// seeding's own resolved path and `index.js` is evicted, which makes the next `require` re-bind
// `seedGoal` to the mutant. Deliberately boring, and both cache entries are restored in `finally`
// so no arm after this one runs against a mutated build. `lane-watch.js` is NOT touched: the pass
// reaches the store through `engine.seedGoal`, so mutating seeding alone is the honest edit.
const SEEDING_PATH = require.resolve('../seeding');
const ENGINE_INDEX_PATH = require.resolve('../index');
const SEEDING_SRC = fs.readFileSync(SEEDING_PATH, 'utf8');
function withMutantSeeding(from, to, fn) {
  if (!SEEDING_SRC.includes(from)) {
    throw new Error(`mutation anchor ABSENT in seeding.js — the arm would measure nothing: ${from}`);
  }
  const savedSeeding = require.cache[SEEDING_PATH];
  const savedIndex = require.cache[ENGINE_INDEX_PATH];
  const m = new Module(SEEDING_PATH, null);
  m.filename = SEEDING_PATH;
  m.paths = Module._nodeModulePaths(path.dirname(SEEDING_PATH));
  m._compile(SEEDING_SRC.replace(from, to), SEEDING_PATH);
  m.loaded = true;
  require.cache[SEEDING_PATH] = m;
  delete require.cache[ENGINE_INDEX_PATH];
  try {
    return fn(require('../index').createEngine);
  } finally {
    require.cache[SEEDING_PATH] = savedSeeding;
    require.cache[ENGINE_INDEX_PATH] = savedIndex;
  }
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
// 7.787: `profiles:` is `launch-specs:`, keyed by (harness, model). The `bash -c` shim keeps
// the argv agreeing with the key (`profiles.js#validateSpecKey` refuses a disagreement at
// LOAD) while running exactly what it ran before; the goal's seats declare the matching cast.
cfg['launch-specs'] = { bash: {} };
cfg['launch-specs'].bash['probe-lane'] = {
  exec: { argv: ['bash', '-c', 'exec sleep 1', '--model', 'probe-lane'], prompt: 'stdin' },
  headed: { tui: { argv: ['true'] } },
  session_ref: { source: 'cwd-implicit' },
  // ABSOLUTE, and pointed at THIS fixture's goals root. A workspace-relative `.rbtv/goals` resolves
  // against the runner's cwd (the ignite source), so every seat launch would refuse
  // `E_WORKDIR_ESCAPE` and the probe would measure a spawn that never happened.
  workdir_root: goalsRoot,
  caps: { memory_max: '64M', cpu_quota: '10%', runtime_max: '5m', tasks_max: 16 },
  sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
};
// ⚠ THE CAST TWIN IS GONE AT 7.787. `probe-lane-cast` existed because `probe-lane`'s argv pinned
// no model, so no seat could be cast TO it — a cast was DERIVED from a spec's own `--model` pin.
// `launch-specs:` is keyed by the pair, so every spec is castable by construction and the twin has
// nothing left to be a twin of.
const configPath = path.join(tmp, 'spawn-profiles.yaml');
fs.writeFileSync(configPath, yaml.dump(cfg));

const daemonStorePath = path.join(dataRoot, 'heart.db');
const isoNow = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');

// Two seats, `bravo` after `alpha` — the wave that makes "did it skip the finished one" answerable.
// NO `execution-mode` file: absent means `autonomous` (ratified default), which is the state a
// daemon-run goal is in, and it keeps the foreground carrier out of this probe entirely.
// `cast` writes the seat's harness+model into its DESCRIPTOR frontmatter — the surface the launch
// reads (`spawn.js#seatDeclaresValue`), and since `#d-abolish-profile-names` the ONLY surface that
// decides what a seat runs. ⚠ DEFAULT ON since 7.787, and the flip is the ruling: an UNCAST seat is
// a NAMED REFUSAL at both doors, so a fixture that declared none could no longer be adopted at all
// and every downstream arm would measure the refusal instead of its own subject. `uncast-goal`
// below is the one deliberate exception, and it exists to measure exactly that refusal.
function makeGoal(name, { cast = { harness: 'bash', model: 'probe-lane' } } = {}) {
  const dir = path.join(goalsRoot, name);
  for (const s of ['alpha', 'bravo']) fs.mkdirSync(path.join(dir, 'seats', s), { recursive: true });
  fs.mkdirSync(path.join(dir, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'taskforce.csv'), `taskforce-id,seat,after\ntf-${name},alpha,\ntf-${name},bravo,alpha\n`);
  const castLines = cast ? `harness: ${cast.harness}\nmodel: ${cast.model}\n` : '';
  for (const s of ['alpha', 'bravo']) {
    fs.writeFileSync(path.join(dir, 'seats', s, 'seat.md'), `---\nseat: ${s}\n${castLines}---\n\nbody\n`);
  }
  return dir;
}

const switchGoal = makeGoal('switch-goal');     // the end-to-end: daemon first, console after
const consoleGoal = makeGoal('console-goal');   // THE CONTROL: assigned to the console lane
const lockedGoal = makeGoal('locked-goal');     // assigned daemon, but a console runner is attached
const heldGoal = makeGoal('held-goal');         // assigned daemon, one seat OPEN in the other lane
// The two 7.787 fixtures: a goal whose seats are UNCAST (refused at both doors), and a goal whose
// marker still carries the RETIRED two-token grammar (does not parse as `daemon`, reads console).
const uncastGoal = makeGoal('uncast-goal', { cast: null });
const legacyGoal = makeGoal('legacy-marker-goal');
const hiGoal = makeGoal('human-interactive-goal');
// The F1 fixture: an INTERACTIVE goal whose first seat declares `human-interactive:`. In the
// attached lane that seat is carried in the terminal; in this one there is no terminal at all —
// and since 7.626 that is fine, because the goal's channel is the owner surface and the seat's
// declared `fallback:` is what executes there.
fs.writeFileSync(path.join(hiGoal, 'execution-mode'), 'interactive\n');
fs.writeFileSync(path.join(hiGoal, 'seats', 'alpha', 'seat.md'),
  '---\nseat: alpha\nharness: bash\nmodel: probe-lane\nhuman-interactive: yes\nfallback: block-and-queue\n---\n\nbody\n');
// THE 7.626 RESIDUAL: the same shape with NO `fallback:` — a `component-lint --check
// interactive-fallback` violation that reached dispatch. It is the ONE case the pass must still
// be loud about, and it needs its own goal because the arm-declared case must stay quiet in the
// same run for the pair to discriminate.
// The PAUSE fixture: assigned to the daemon and then PAUSED by prefixing the marker. Its own goal
// because the pause must be measured while other goals ARE being adopted in the same pass — a
// "not adopted" that holds when nothing is adopted measures nothing.
const pausedGoal = makeGoal('paused-goal');
// The NARROWING fixture (2026-08-12, D19): every seat declares a cast, so no launch of this goal
// can ever read the marker's fallback token. Its whole point is to be the OTHER answer to the
// question `no-profile-goal` asks — same bare `daemon` marker, opposite verdict — because a
// refusal measured alone cannot tell an unconditional gate from a conditional one.
const castGoal = makeGoal('cast-goal');
const armlessGoal = makeGoal('armless-goal');
fs.writeFileSync(path.join(armlessGoal, 'execution-mode'), 'interactive\n');
fs.writeFileSync(path.join(armlessGoal, 'seats', 'alpha', 'seat.md'),
  '---\nseat: alpha\nharness: bash\nmodel: probe-lane\nhuman-interactive: yes\n---\n\nbody\n');

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

  // ── L0 · THE `taskforce.csv` READER ─────────────────────────────────────────────────────────
  //
  // THE DEFECT: `seeding.js#readCsv` split every line on a bare comma, so a QUOTED multi-predecessor
  // `after` cell became several fields and every column to its right shifted. Measured against the
  // REAL Python writer — `team-kit/materialize-seats.py#_render_csv_line` (`csv.writer`,
  // QUOTE_MINIMAL), loaded by path in a subprocess — never a hand-written fixture line.
  say('L0 — the taskforce reader, pinned to the REAL Python writer');
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
  // ⚠ THE CELL GRAMMAR IS NO LONGER READ IN JAVASCRIPT, so its arms are DELETED rather than
  // rewritten (`one-readiness-predicate.md` § Deletions). What stood here — L0b's cross-language
  // pin against `coord.py#parse_after_member`, L0c's pre-fix oracle, L0d's loud skip of a guard and
  // an alternate — pinned a MIRROR, and there is no mirror left to pin: `coordinate ready-seats`
  // answers the DAG and `seeding.js` answers only "has this store already fired this seat".
  // The CSV read above STAYS: reading `taskforce.csv` correctly is still seeding's job, and the
  // naive split it replaced shifted five columns on a six-predecessor row.

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
  const tolerant = readsAs('  Daemon   \n');
  check('L1 only `daemon` opens it — trimmed and case-insensitive, exactly as `execution-mode` is read',
    tolerant.lane === 'daemon' && tolerant.legacy === false, JSON.stringify(tolerant));
  // ⚑ THE MARKER IS ONE WORD (`#d-abolish-profile-names` sub-ruling 3). The retired second token
  // named a fallback launch profile; a marker still carrying one does NOT parse as `daemon`, so it
  // reads `console` under the standing fail-closed rule — and is REPORTED `legacy`, because a goal
  // silently demoted to the console is the "quietly stopped" failure this whole surface exists to
  // prevent. Both halves are asserted: the fail-closed verdict AND the report that makes it visible.
  const legacyRead = readsAs('daemon probe-lane\n');
  check('L1 a two-token marker (the RETIRED `daemon <profile>` grammar) reads CONSOLE and is REPORTED legacy',
    legacyRead.lane === 'console' && legacyRead.legacy === true && legacyRead.raw === 'daemon probe-lane',
    JSON.stringify(legacyRead));
  check('L1 a bare `daemon` marker parses and is NOT legacy — the pair discriminates',
    readsAs('daemon\n').lane === 'daemon' && readsAs('daemon\n').legacy === false);
  // ⚑ THE PAUSE MARKER, and it needs NO reader change — which is the arm. A pause is written by
  // PREFIXING the assignment (`paused daemon <profile>`), so the FIRST token stops being `daemon`
  // and the fail-closed default catches it: the goal reads `console`, the daemon does not adopt
  // it, and the profile it will return to is preserved verbatim in the marker for the resume to
  // put back. Pinned here because the pause verb DEPENDS on this reader behaviour — a reader that
  // grew tolerant of a leading word would silently un-pause every paused goal on the tree.
  const paused = readsAs('paused daemon\n');
  check('L1 a PAUSED marker (`paused daemon`) reads as the CONSOLE lane — the pause verb '
    + 'rides the fail-closed default rather than a new word in this reader',
    paused.lane === 'console' && paused.present === true && paused.raw === 'paused daemon',
    JSON.stringify(paused));
  fs.unlinkSync(lanePath(grammar));

  // ── L2 · THE CLI IS THE WRITER, AND IT WORKS DAEMON-DOWN ────────────────────────────────────
  say('');
  say('L2 — `rbtv goal lane` writes the marker, with no daemon in the picture');
  const refused = laneCli(['uncast-goal', '--set', 'daemon'], { expectRefusal: true });
  check('L2 `--set daemon` is REFUSED when a SEAT of that goal declares NO CAST — there is nothing '
    + 'left to launch it on, and the refusal is at the door rather than a journal warning at '
    + '03:00. It NAMES the seats that forced it',
    refused.ok === false && /no harness\+model cast/.test(refused.out) && /alpha/.test(refused.out)
      && !fs.existsSync(lanePath(uncastGoal)),
    refused.out.trim().split('\n').pop());
  // ⚑ THE OTHER ANSWER, in the same run and through the same door (narrowing of D19, 2026-08-12).
  // Only the seats' descriptors differ. Without this arm the one above is green whether the gate
  // is conditional or unconditional — which is exactly how the flag came to be demanded on a goal
  // where all 17 seats were cast and no launch ever read the value.
  laneCli(['cast-goal', '--set', 'daemon']);
  check('L2 …and on a FULLY CAST goal the same command SUCCEEDS — the marker is a bare `daemon`, '
    + 'one word, which both readers resolve identically',
    fs.readFileSync(lanePath(castGoal), 'utf8') === 'daemon\n'
      && laneWatch.readLane(castGoal).lane === 'daemon' && laneWatch.readLane(castGoal).legacy === false,
    `${JSON.stringify(fs.readFileSync(lanePath(castGoal), 'utf8'))} ${JSON.stringify(laneWatch.readLane(castGoal))}`);
  // ⚑ THE DOOR CHECK (review F2), RE-POINTED. A `--profile` typo used to be accepted here: the
  // marker was written, the daemon adopted the goal, `seedTaskforce` registered a job row per
  // seat, and only then did the enqueue refuse — leaving orphan rows and a goal that threw every
  // cadence forever. `#d-abolish-profile-names` removed the flag, so the typo it guarded is
  // unspellable; what remains at this door is the UNCAST refusal above, which writes nothing for
  // the same reason. Asserted here as the flag's ABSENCE, because a flag quietly coming back is
  // exactly what nothing else would notice.
  const deadFlag = laneCli(['cast-goal', '--set', 'daemon', '--profile', 'probe-lane'], { expectRefusal: true });
  check('L2 `--profile` is GONE from the door — the retired flag is an argparse refusal, not a '
    + 'silently ignored argument',
    deadFlag.ok === false && /unrecognized arguments/.test(deadFlag.out),
    deadFlag.out.trim().split('\n').pop());

  laneCli(['switch-goal', '--set', 'daemon']);
  laneCli(['locked-goal', '--set', 'daemon']);
  laneCli(['held-goal', '--set', 'daemon']);
  laneCli(['human-interactive-goal', '--set', 'daemon']);
  laneCli(['armless-goal', '--set', 'daemon']);
  laneCli(['console-goal', '--set', 'console']);
  // Assigned to the daemon by the CLI, then PAUSED by prefixing its marker — the pause is a
  // prefix, so the assignment (and the profile) survives it verbatim.
  laneCli(['paused-goal', '--set', 'daemon']);
  goalCli('pause', ['paused-goal']);
  check('L2 `rbtv-goal pause` stashes the assignment behind a `paused ` PREFIX — the marker it '
    + 'returns to is kept verbatim, and the DAEMON\'s reader resolves the result to `console` '
    + 'with no word of its own (two languages, one grammar, cross-checked)',
    fs.readFileSync(lanePath(pausedGoal), 'utf8').trim() === 'paused daemon'
      && laneWatch.readLane(pausedGoal).lane === 'console',
    JSON.stringify(laneWatch.readLane(pausedGoal)));
  // The two BROKEN markers only reachable by hand, since the door refuses both spellings.
  // The two markers only reachable by hand, since the door refuses both. `legacy-marker-goal`
  // carries the RETIRED two-token grammar; `uncast-goal` is properly assigned but has no cast.
  fs.writeFileSync(lanePath(legacyGoal), 'daemon probe-lane\n');
  fs.writeFileSync(lanePath(uncastGoal), 'daemon\n');
  check('L2 the write is ATOMIC — a temp file is renamed into place and nothing is left beside it',
    !fs.existsSync(path.join(switchGoal, `${laneWatch.LANE_FILE}.tmp`))
      && fs.readFileSync(lanePath(switchGoal), 'utf8') === 'daemon\n');
  check('L2 the CLI\'s writes are what the DAEMON\'s reader sees — two languages, one grammar, cross-checked',
    laneWatch.readLane(switchGoal).lane === 'daemon'
      && laneWatch.readLane(switchGoal).legacy === false
      && laneWatch.readLane(consoleGoal).lane === 'console',
    `switch=${JSON.stringify(laneWatch.readLane(switchGoal))} console=${JSON.stringify(laneWatch.readLane(consoleGoal))}`);
  const shown = JSON.parse(laneCli(['switch-goal', '--json']).out);
  check('L2 …and the read-only form reports the same answer as the engine\'s reader (orientation parity)',
    shown.lane === 'daemon' && shown.legacy_marker === false && shown.assigned === true,
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
    const goalStore = openHeartStore({ dbPath: path.join(heldGoal, 'heart.db') });
    goalStore.registerJob({
      jobId: 'seat-alpha',
      actionType: 'launch-agent',
      function: 'attached-lane seat alpha',
      argsSchema: JSON.stringify({ required: {}, optional: { workdir: 'string' } }),
      description: 'a seat the CONSOLE lane is running right now',
      createdAt: isoNow(), updatedAt: isoNow(),
    });
    goalStore.recordExecutionStart({
      jobId: 'seat-alpha', actionType: 'launch-agent',
      args: JSON.stringify({}), enqueuedBy: 'attached-execution',
      sessionMode: 'headless', firedTick: 1, firedAt: new Date(),
      sessionId: 'ffffffff-1111-2222-3333-444444444444',
      workdir: path.join(heldGoal, 'seats', 'alpha'),
    });
    goalStore.close();
    const goalEngine = createEngine({
      dbPath: path.join(heldGoal, 'heart.db'), spawnConfigPath: configPath, userManager: false,
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
      dbPath: daemonStorePath, spawnConfigPath: configPath, userManager: false,
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
      const s = openHeartStore({ dbPath: daemonStorePath });
      const d = s.dump();
      s.close();
      return !JSON.stringify([d.jobs, d.queue, d.jobs_log]).includes('console-goal');
    })());
  // ⚑ THE PAUSED GOAL — the same two facts as the console control, for a goal that IS assigned to
  // the daemon and is merely held. It must be skipped for the ordinary not-assigned reason and
  // leave no trace in the store, or a pause would be a pause in name only.
  // ⚠ `paused daemon` IS ALSO A TWO-TOKEN-ish MARKER, and the reader tells the two cases apart by
  // the FIRST token: `paused` is not `daemon`, so it is not a legacy marker, it is a pause. That
  // distinction is asserted here — a reader that lumped them together would shout a repair command
  // at every paused goal on the tree.
  check('L5 a PAUSED goal (`paused daemon`) is NOT adopted — skipped for the ordinary not-assigned '
    + 'reason (NOT the legacy-marker one), with the assignment it returns to still in its marker',
    !adoptedNames.includes('paused-goal')
      && pass1.skipped.some((s) => s.goal === 'paused-goal' && s.reason === 'not-assigned-to-the-daemon')
      && fs.readFileSync(lanePath(pausedGoal), 'utf8').trim() === 'paused daemon',
    JSON.stringify(pass1.skipped.filter((s) => s.goal === 'paused-goal')));
  check('L5 …and NOTHING of the paused goal reached the daemon\'s store either',
    (() => {
      const s = openHeartStore({ dbPath: daemonStorePath });
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
  const badSkip = pass1.skipped.find((s) => s.goal === 'legacy-marker-goal');
  check('L5b a marker still carrying the RETIRED two-token grammar is SKIPPED, typed, and NOTHING '
    + 'is registered — it does not parse as `daemon`, so the goal reads CONSOLE and the pass writes '
    + 'no job rows for it (the harm the ordering has always prevented)',
    Boolean(badSkip) && badSkip.reason === 'legacy-two-token-marker'
      && (() => {
        const s = openHeartStore({ dbPath: daemonStorePath });
        const d = s.dump(); s.close();
        return !JSON.stringify([d.jobs, d.queue, d.jobs_log]).includes('legacy-marker-goal');
      })(),
    JSON.stringify(badSkip || 'not skipped at all'));
  check('L5b …and it says so ONCE, naming the retired grammar and the one-command repair — a goal '
    + 'silently demoted to the console is the failure this line exists to prevent',
    log1.some((m) => m.goal === 'legacy-marker-goal' && m.level === 'warn'
      && /RETIRED two-token grammar/.test(m.message || '') && /--set daemon/.test(m.fix || '')),
    JSON.stringify(log1.filter((m) => m.goal === 'legacy-marker-goal').map((m) => m.level)));
  const noProfSkip = pass1.skipped.find((s) => s.goal === 'uncast-goal');
  check('L5b a properly assigned goal whose seats declare NO CAST is SKIPPED with its own reason, '
    + 'and the line NAMES the seats that forced it — since `#d-abolish-profile-names` there is no '
    + 'fallback left to launch them on, so seeding would only queue rows that refuse at spawn',
    Boolean(noProfSkip) && noProfSkip.reason === 'uncast-seats'
      && log1.some((m) => m.goal === 'uncast-goal' && m.level === 'warn'
        && /NO cast/.test(m.message || '')
        && Array.isArray(m.seats) && m.seats.includes('alpha')
        && /rbtv-bindings set/.test(m.fix || '')),
    JSON.stringify(noProfSkip || 'not skipped at all'));
  // ⚑ THE SAME BARE MARKER, THE OPPOSITE VERDICT — the pair is the measurement. A refusal observed
  // alone cannot tell an unconditional gate from a conditional one, which is exactly how the old
  // `--profile` demand came to fire on goals where every seat was cast. `uncast-goal` and
  // `cast-goal` differ in ONE byte-level fact: whether their seat descriptors declare a cast.
  const castPickup = pass1.adopted.find((a) => a.goal === 'cast-goal');
  check('L5b …while a FULLY CAST goal with the SAME bare `daemon` marker is ADOPTED and seeded — '
    + 'and the log line carries NO profile at all, because nothing names one any more',
    Boolean(castPickup)
      && log1.some((m) => m.goal === 'cast-goal' && /goal seeded/.test(m.message || '')
        && !('profile' in m)),
    JSON.stringify(log1.filter((m) => m.goal === 'cast-goal').map((m) => `${m.message}:${m.profile}`)));

  // ── L5c · THE FAILURE IS BOUNDED, and un-bounds itself when the marker changes ───────────────
  {
    const log2 = [];
    const engine = createEngine({
      dbPath: daemonStorePath, spawnConfigPath: configPath, userManager: false,
    });
    try { laneWatch.runLaneWatch({ goalsRoot, engine, logger: collectingLogger(log2) }); } finally { engine.close(); }
    const lvls = log2.filter((m) => m.goal === 'legacy-marker-goal').map((m) => m.level);
    check('L5c the SECOND pass over the same broken marker drops to debug — at a 10 s cadence the '
      + 'loud version is ~8,600 identical lines a day for a condition only a human can change',
      lvls.length > 0 && !lvls.includes('warn'), JSON.stringify(lvls));

    const log3 = [];
    fs.writeFileSync(lanePath(legacyGoal), 'daemon probe-laneY\n');  // somebody EDITED it, still two tokens
    const engine3 = createEngine({
      dbPath: daemonStorePath, spawnConfigPath: configPath, userManager: false,
    });
    try { laneWatch.runLaneWatch({ goalsRoot, engine: engine3, logger: collectingLogger(log3) }); } finally { engine3.close(); }
    check('L5c …and it is LOUD again the moment the marker text changes — quiet must never mean '
      + 'forgotten, so the memo is keyed on the marker, not on the goal',
      log3.some((m) => m.goal === 'legacy-marker-goal' && m.level === 'warn'),
      JSON.stringify(log3.filter((m) => m.goal === 'legacy-marker-goal').map((m) => m.level)));
    fs.writeFileSync(lanePath(legacyGoal), 'daemon probe-lane\n');
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
      dbPath: daemonStorePath, spawnConfigPath: configPath, userManager: false,
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
    const s = openHeartStore({ dbPath: daemonStorePath });
    const rows = s.dump().jobs_log.filter((r) => r.job_id === alphaJobId);
    check('L6 the daemon REALLY dispatched alpha — enqueued by the watch, fired by the daemon\'s tick',
      rows.length === 1, rows.map((r) => `${r.job_id}=${r.status}`).join(' ') || 'no execution row');
    // The synthesized half, disclosed: a `sleep` child files no completion report, so the turn is
    // ended through the store's own door — the execution itself is the daemon's, not the probe's.
    if (rows.length === 1) {
      s.endTurnAndCloseSession(rows[0].exec_id, { turnStatus: 'done', sessionStatus: 'closed', endedAt: new Date() });
    }
    s.close();
    // …AND ALPHA CHECKS OUT. Since § D1 (`one-readiness-predicate.md`) the turn status above is a
    // fact about a PROCESS and advances no edge: `coordinate ready-seats` reads the seat's own
    // check-out disposition, and a session that ended without one is UNDECLARED. A `sleep` child
    // cannot run the check-out verb, so the row it would have written is synthesized here — same
    // file, same columns (`coord.py SESSIONS_COLS`), same disposition the seat would declare.
    fs.writeFileSync(path.join(switchGoal, 'sessions.csv'),
      'session-id,seat,harness,native-session-id,workdir,recorded,started,ended,pid,pid-starttime,'
      + 'tty,disposition,disposition-writer,execution,checkin,model\n'
      + `${rows[0] ? rows[0].session_id : 'sid-alpha'},alpha,claude,,,,${isoNow()},${isoNow()},,,,done,seat,,,\n`);
  }
  {
    const engine = createEngine({
      dbPath: daemonStorePath, spawnConfigPath: configPath, userManager: false,
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
      dbPath: daemonStorePath, spawnConfigPath: configPath, userManager: false,
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
      '  return { lane: CONSOLE, present: true, legacy, raw: text };',
      '  return { lane: DAEMON, present: true, legacy, raw: text };');
    const mutRoot = path.join(tmp, 'm1');
    fs.cpSync(goalsRoot, mutRoot, { recursive: true });
    const engine = createEngine({
      dbPath: path.join(tmp, 'm1.db'), spawnConfigPath: configPath, userManager: false,
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
      dbPath: path.join(tmp, 'm2.db'), spawnConfigPath: configPath, userManager: false,
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
      '    if (uncast.length) {',
      '    if (false) {');
    const mutRoot = path.join(tmp, 'm4');
    fs.cpSync(goalsRoot, mutRoot, { recursive: true });
    const dbPath = path.join(tmp, 'm4.db');
    const engine = createEngine({
      dbPath, spawnConfigPath: configPath, userManager: false,
    });
    try { mutant({ goalsRoot: mutRoot, engine }); } finally { engine.close(); }
    const s = openHeartStore({ dbPath });
    const d = s.dump(); s.close();
    check('L8 M4 the uncast guard REMOVED -> the unlaunchable goal leaves orphan job rows in the '
      + 'daemon store (L5b RED), which is exactly the harm the ordering fixes',
      JSON.stringify(d.jobs).includes('uncast-goal'),
      `job ids: ${(d.jobs || []).map((j) => j.job_id).filter((i) => /uncast/.test(i)).join(', ') || 'none'}`);
  }

  // M5 · THE UNCAST BRANCH SILENCED — review F3: this branch shipped unmeasured, and a mutation
  // of it left the probe green. Retargeted at 7.787 onto the branch that replaced it.
  {
    const mutant = mutantWatch(
      "      skipped.push({ goal, reason: 'uncast-seats', seats: uncast });",
      "      skipped.push({ goal, reason: 'uncast-seats', seats: uncast }); continue;");
    const mutRoot = path.join(tmp, 'm5');
    fs.cpSync(goalsRoot, mutRoot, { recursive: true });
    const log = [];
    const engine = createEngine({
      dbPath: path.join(tmp, 'm5.db'), spawnConfigPath: configPath, userManager: false,
    });
    try { mutant({ goalsRoot: mutRoot, engine, logger: collectingLogger(log) }); } finally { engine.close(); }
    check('L8 M5 the uncast branch skips SILENTLY -> the operator loses the only line that says '
      + 'why the goal never starts (L5b RED)',
      !log.some((m) => m.goal === 'uncast-goal' && /NO cast/.test(m.message || '')),
      `lines for that goal: ${log.filter((m) => m.goal === 'uncast-goal').length}`);
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
      dbPath: path.join(tmp, 'm6.db'), spawnConfigPath: configPath, userManager: false,
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
      '---\nseat: alpha\nharness: bash\nmodel: probe-lane\nhuman-interactive: yes\nfallback: block-and-queue\n---\n\nbody\n');
    laneCli(['m7-arm-goal', '--set', 'daemon']);
    const log = [];
    const engine = createEngine({
      dbPath: path.join(tmp, 'm7.db'), spawnConfigPath: configPath, userManager: false,
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
      dbPath: path.join(tmp, 'm7-control.db'), spawnConfigPath: configPath, userManager: false,
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

  // M8 · THE LEGACY-MARKER REPORT REMOVED (7.787). The branch it replaces (`fallbackProfileFor`,
  // the D19 narrowing's derivation) is deleted with the fallback itself. What took its place is the
  // one line that keeps a goal from vanishing quietly: a marker written under the retired grammar
  // reads CONSOLE, and if that is not REPORTED the goal looks exactly like one somebody parked on
  // purpose. Mutating the report away must therefore leave the goal un-adopted AND unexplained.
  {
    const mutant = mutantWatch(
      "        skipped.push({ goal, reason: 'legacy-two-token-marker', raw });",
      "        skipped.push({ goal, reason: 'not-assigned-to-the-daemon' });");
    const mutRoot = path.join(tmp, 'm8');
    fs.cpSync(goalsRoot, mutRoot, { recursive: true });
    const log = [];
    const engine = createEngine({
      dbPath: path.join(tmp, 'm8.db'), spawnConfigPath: configPath, userManager: false,
    });
    let pass;
    try { pass = mutant({ goalsRoot: mutRoot, engine, logger: collectingLogger(log) }); } finally { engine.close(); }
    check('L8 M8 the legacy-marker REPORT removed -> a goal written under the retired grammar is '
      + 'indistinguishable from one deliberately assigned to the console (L5b RED): same skip '
      + 'reason, and nothing on the line says a human has to rewrite the marker',
      !pass.skipped.some((s) => s.goal === 'legacy-marker-goal' && s.reason === 'legacy-two-token-marker'),
      JSON.stringify(pass.skipped.filter((s) => s.goal === 'legacy-marker-goal')) || 'not skipped');
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

  // ── L9 · THE SEAT IS ENQUEUED WITH ITS INSTRUCTIONS ─────────────────────────────────────────
  //
  // THE DEFECT `d34277c6` CLOSED, which nothing here measured: `enqueueEligible` submitted
  // `{profile, workdir}` and NO PROMPT, so `spawn.js#ensurePromptFile` wrote 0 bytes, systemd
  // connected an empty file as stdin, and the harness refused — "Error: Input must be provided
  // either through stdin or as a prompt argument when using --print", exit 1, on execs 26274 and
  // 26358. The seeding pass had never successfully launched a seat, and every arm above stayed
  // green throughout, because every one of them stops at "a row was enqueued".
  //
  // ⚠ WHY THIS IS NOT AN ARGV ASSERTION, and cannot be. The prompt NEVER APPEARS IN ARGV:
  // `ticker.js:654` reads `args.prompt ?? null`, `spawn.js:233-241` sees `profile.exec.prompt ===
  // 'stdin'` and routes to `ensurePromptFile` (:141-147), which writes the bytes 0600 and hands
  // systemd `StandardInput=file:`. The composed command line carries no prompt operand at all —
  // correctly so. The two surfaces that CAN witness the defect are the ENQUEUED ROW'S `args.prompt`
  // and that file's bytes; this arm measures the first, at the door the defect lived behind.
  //
  // ⚠ ITS OWN FRESH GOAL AND ITS OWN FRESH STORE. Every goal above has been advanced by a prior
  // arm — flipped lanes, released locks, completed turns — and a row enqueued eight arms ago says
  // nothing about what THIS pass composed.
  say('');
  say('L9 — the enqueued row carries the seat\'s BOOT PROMPT, and it is coord\'s own bytes');
  const promptGoal = makeGoal('prompt-goal');
  laneCli(['prompt-goal', '--set', 'daemon']);
  const L9_JOB = 'seat-prompt-goal-alpha';
  const L9_ANCHOR = 'args: JSON.stringify({ workdir: seatDir, prompt }),';
  // THE EXPECTATION IS COMPUTED, NEVER TYPED: `coordinate boot-prompt` is the ONE composer
  // (`seeding.js#seatBootPrompt` shells exactly this), so a hand-written string here would be a
  // second composer and the arm would pass on drift between them.
  // ⚠ W1 (adv, C4) — `--lane daemon`, because THIS GOAL IS ON THE DAEMON LANE (set two lines
  // above) and the prompt now differs by lane. Without the flag this expectation would be the
  // CONSOLE bytes and the identity check below would red on a correct pass — the failure mode a
  // computed expectation exists to avoid, reintroduced by computing the wrong thing.
  const coordArgv = (...extra) => [path.join(IGNITE_SRC, 'team-kit', 'coord.py'),
    '--package', promptGoal, 'boot-prompt', 'alpha', ...extra];
  const expectedPrompt = execFileSync(requirePythonCmd(), coordArgv('--lane', 'daemon'),
    { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  check('L9 coord composes a NON-EMPTY boot prompt for this seat — the arm\'s own premise, asserted '
    + 'before anything is compared against it',
    expectedPrompt.trim().length > 0, `${expectedPrompt.length} bytes`);
  // ── W1 (adv, C4) · THE LANE ACTUALLY CHANGES THE BYTES, and in the ruled direction ───────────
  // Two seat-facing facts, asserted against the CONSOLE composition as the control, so neither
  // can pass by the flag being ignored: the daemon prompt must NOT order a check-in the seat has
  // no pane to perform, and it MUST still order the check-out that is the sole producer of
  // `incomplete`. A single "they differ" check would pass on any difference at all.
  const consolePrompt = execFileSync(requirePythonCmd(), coordArgv(),
    { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  check('L9/C4 the CONSOLE prompt orders a check-in — the control, without which "the daemon '
    + 'prompt has no check-in" is true of any two strings',
    /check in as/.test(consolePrompt), `console: ${consolePrompt.length} bytes`);
  check('L9/C4 …and the DAEMON prompt does NOT order one, while still ordering the CHECK-OUT that '
    + 'is the only producer of an honest `incomplete`',
    !/check in as/.test(expectedPrompt) && /DO NOT run `checkin`/.test(expectedPrompt)
      && /checkout --incomplete/.test(expectedPrompt),
    `daemon: ${expectedPrompt.length} bytes · checkin-order=${/check in as/.test(expectedPrompt)}`);

  function l9Pass(createEngineFn, dbPath, root) {
    const engine = createEngineFn({
      dbPath, spawnConfigPath: configPath, userManager: false,
    });
    let pass;
    try { pass = laneWatch.runLaneWatch({ goalsRoot: root, engine }); } finally { engine.close(); }
    const s = openHeartStore({ dbPath });
    const row = s.dump().queue.find((r) => r.job_id === L9_JOB);
    s.close();
    return { pass, row, pickup: pass.adopted.find((a) => a.goal === 'prompt-goal') };
  }

  const l9 = l9Pass(createEngine, path.join(tmp, 'l9.db'), goalsRoot);
  // NON-VACUITY, BOTH HALVES, BEFORE `args` IS EVER READ. Without these, "the goal was never
  // adopted" and "no row was enqueued" would both reach the prompt checks as `undefined` and
  // could be spun as "nothing wrong with the prompt".
  check('L9 the pass ADOPTED the goal and enqueued a NON-EMPTY seat list — the premise the two '
    + 'checks below rest on, so an empty store can never read as a healthy prompt',
    !!l9.pickup && Array.isArray(l9.pickup.enqueued) && l9.pickup.enqueued.length > 0,
    l9.pickup ? `enqueued: ${(l9.pickup.enqueued || []).join(', ') || 'none'}` : 'goal NOT adopted');
  check(`L9 …and the row for \`${L9_JOB}\` EXISTS in the queue`, !!l9.row,
    l9.row ? `queue_id=${l9.row.queue_id}` : 'no row');
  const l9args = l9.row ? JSON.parse(l9.row.args) : {};
  check('L9 the enqueued row carries a NON-EMPTY string `prompt` — the key `d34277c6` added, and '
    + 'the ONLY surface the launch reads it from',
    typeof l9args.prompt === 'string' && l9args.prompt.length > 0,
    `prompt: ${typeof l9args.prompt}${typeof l9args.prompt === 'string' ? ` ${l9args.prompt.length} bytes` : ''}`
    + ` · keys: ${Object.keys(l9args).join(', ') || 'none'}`);
  check('L9 …and those bytes are IDENTICAL to what `coordinate boot-prompt alpha` prints — '
    + 'non-empty alone would pass on a placeholder, a truncation, or another seat\'s prompt',
    l9args.prompt === expectedPrompt,
    l9args.prompt === expectedPrompt ? `${expectedPrompt.length} bytes, byte-for-byte`
      : `enqueued ${JSON.stringify(String(l9args.prompt).slice(0, 60))}… vs coord `
        + `${JSON.stringify(expectedPrompt.slice(0, 60))}…`);

  // M9 · THE HISTORICAL DEFECT, put back. `765c9fac:seeding.js:503` — the line immediately before
  // the fix — enqueued the row WITHOUT `prompt`, so this mutation restores the pre-`d34277c6`
  // enqueue for any goal whose boot prompt composes. (The historical line also carried `profile`;
  // that argument was abolished at 7.787, so the mutant drops only the key this arm is about —
  // which is what keeps it a PROMPT mutation rather than a second, unrelated schema change.) The whole pre-fix
  // FILE was the other candidate and was rejected on measurement: `e5dff4b8` landed 78 further
  // lines in `seeding.js` AFTER the fix, so checking the old file out would revert that too and
  // redden this arm for a reason that is not the defect.
  {
    const mutRoot = path.join(tmp, 'm9');
    fs.cpSync(goalsRoot, mutRoot, { recursive: true });
    const m9 = withMutantSeeding(L9_ANCHOR, 'args: JSON.stringify({ workdir: seatDir }),',
      (mutantCreateEngine) => l9Pass(mutantCreateEngine, path.join(tmp, 'm9.db'), mutRoot));
    const m9args = m9.row ? JSON.parse(m9.row.args) : {};
    // THE MUTANT'S OWN NON-VACUITY: it must still adopt and still enqueue, or the arm below would
    // go red because nothing ran rather than because the prompt went missing.
    check('L9 M9 CONTROL: the mutant still adopts the goal and still enqueues the seat — so the '
      + 'red below is a MISSING PROMPT and not a pass that did nothing',
      !!m9.pickup && (m9.pickup.enqueued || []).length > 0 && !!m9.row,
      m9.pickup ? `enqueued: ${(m9.pickup.enqueued || []).join(', ') || 'none'} · row: ${!!m9.row}` : 'not adopted');
    check('L9 M9 the prompt key REMOVED from the enqueue (the pre-`d34277c6` line, verbatim) -> '
      + 'BOTH prompt checks above go RED — the 0-byte-stdin defect, reproduced',
      !(typeof m9args.prompt === 'string' && m9args.prompt.length > 0) && m9args.prompt !== expectedPrompt,
      `mutant args keys: ${Object.keys(m9args).join(', ') || 'none'}`);
  }
  // AND THE BUILD IS UNMUTATED AGAIN — the cache restore is asserted, not trusted, because every
  // arm that runs after a `require.cache` swap depends on it having been undone.
  check('L9 M9 the require-cache swap was UNDONE: the live build still carries the prompt key',
    require('../seeding') === require.cache[SEEDING_PATH].exports
      && fs.readFileSync(SEEDING_PATH, 'utf8').includes(L9_ANCHOR),
    'seeding.js restored');

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
      + '(behaviour unchanged, 7.626 owns the fix). And the seat it enqueues carries ITS BOOT '
      + 'PROMPT — coord\'s own bytes, not a placeholder — which is the one thing every arm above '
      + 'this one was blind to while no real seat had ever launched. Every mutation red (the count '
      + 'is deliberately not a literal here: it read "Six" through three further mutations).');
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
