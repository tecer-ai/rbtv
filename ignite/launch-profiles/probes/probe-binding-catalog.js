'use strict';

// probe-binding-catalog — the (harness, model) -> launch-spec table (7.54 · D19 · 7.787).
//
// TWO THINGS ARE UNDER TEST, and they are different claims:
//
//   1. THE TABLE resolves a cast to exactly one launch spec, and REFUSES rather than guessing when
//      it cannot (unknown pair, alias spelling). The refusals are the point: the defect being fixed
//      is a SILENT wrong-model launch, so every arm that refuses is paired with the arm that shows
//      the same input succeeding when it should.
//
//   2. THE FIX resolves a REAL `seat.md` descriptor — the seat's cast is the ONLY answer, an
//      UNCAST seat REFUSES (D2, 2026-08-11; made absolute by `#d-abolish-profile-names`, which
//      deleted the caller's profile parameter outright), and an unmappable cast STOPS the launch.
//      Exercised through `spawn.js#launchSpecForSeat` against descriptors written to a temp dir,
//      never a stub: a probe that stubbed the descriptor read would prove the table and not the fix.
//
// ⚠ THE AMBIGUITY ARM IS GONE (7.787) AND ITS ABSENCE IS CORRECT, not an omission. Two specs
// claiming one (harness, model) was expressible while `profiles:` was a flat name-keyed map; under
// `launch-specs: { <harness>: { <model>: … } }` it is a duplicate YAML key — unspellable rather
// than refused. Arm 5 now asserts the property that replaced it: the KEY and the argv must AGREE.
//
// ⚑ ARM 10 IS THE DRIFT ALARM, and it is the reason this file runs Python. `bindings.py#catalog`
// derives the SAME (harness, model) pairs from the SAME document for the AUTHORING side, and the
// two must agree or a cast the author was allowed to write is a cast the daemon cannot run. Both
// are run against the shipped config and compared ROW FOR ROW — order, harness and model — so a
// change to either derivation reds this probe instead of surfacing as an unlaunchable seat months
// later. A count-only comparison would pass on two catalogs that disagree about every row, so the
// rows themselves are asserted (never the length alone).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const catalog = require('../catalog');
const { launchSpecForSeat, seatDeclaresValue } = require('../../server/spawn/spawn');
const { loadConfig } = require('../../server/spawn/config');

const IGNITE_ROOT = path.resolve(__dirname, '..', '..');
const SHIPPED = path.join(IGNITE_ROOT, 'config', 'spawn-profiles.yaml');
const OUT = path.join(__dirname, 'probe-binding-catalog.out');

const lines = [];
const started = new Date();
let failed = null;
let skipped = 0;

function check(label, fn) {
  try {
    const detail = fn();
    lines.push(`PASS ${label}${detail ? ` -> ${detail}` : ''}`);
  } catch (err) {
    lines.push(`FAIL ${label} -> ${err.message}`);
    if (!failed) failed = err;
  }
}

function expectCode(code, fn) {
  try {
    fn();
  } catch (err) {
    if (err.code === code) return err;
    throw new Error(`expected ${code}, got ${err.code || err.message}`);
  }
  throw new Error(`expected ${code}, but the call SUCCEEDED`);
}

function eq(a, b, what) {
  if (a !== b) throw new Error(`${what}: expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`);
}

// The shipped config, loaded through the DAEMON adapter — it injects the SeatBinds validator the
// bare resolver refuses to run without, so this is the same profile set the daemon spawns from.
const shipped = loadConfig(SHIPPED).launchSpecs;

// A seat folder carrying exactly the frontmatter `materialize-seats.py` emits. The folder is
// NAMED for the seat, as it is in production (`.rbtv/goals/<goal>/seats/<seat>/`) — the refusal
// path identifies a seat by its folder, so a temp-named fixture would test a different thing.
function seatWith(frontmatter, seatName = 'aseat') {
  const dir = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'cast-probe-')), seatName);
  fs.mkdirSync(dir, { recursive: true });
  const body = frontmatter === null
    ? '# a seat with no descriptor frontmatter at all\n'
    : `---\n${frontmatter}\n---\n\n# seat\n`;
  fs.writeFileSync(path.join(dir, 'seat.md'), body);
  return dir;
}

const quiet = () => {};

// ── 1 · the shipped config resolves the motivating cast ──────────────────────────────────────
check('(1) claude + claude-fable-5 resolves to its own launch spec', () => {
  const { key, spec } = catalog.specForSeatCast(shipped, { harness: 'claude', model: 'claude-fable-5' }, quiet, 'aseat');
  eq(key, 'claude/claude-fable-5', 'spec key');
  eq(spec.exec.argv[3], 'claude-fable-5', 'the argv the key resolves to');
  return key;
});

// ── 2 · every shipped profile round-trips through its own cast ───────────────────────────────
// The whole-set version of arm 1: no profile may resolve to a DIFFERENT profile than itself, which
// is the property that makes the mapping usable as an identity for a launch.
check('(2) every shipped launch spec round-trips to itself', () => {
  const rows = catalog.catalogOf(shipped);
  for (const r of rows) {
    const { key } = catalog.specForSeatCast(shipped, r, quiet, 'aseat');
    eq(key, r.key, `round-trip of ${r.key}`);
  }
  if (!rows.length) throw new Error('the catalog is EMPTY — a round-trip that proves nothing');
  return `${rows.length} rows`;
});

// ── 3 · an ALIAS is refused, never rewritten ─────────────────────────────────────────────────
// `bindings.md`: the model vocabulary is the profile's pin VERBATIM. The pairing matters — the
// same harness with the PINNED spelling must succeed, or "it refused" would be compatible with a
// catalog that refuses everything.
check('(3) the `fable` alias is REFUSED while `claude-fable-5` succeeds', () => {
  const err = expectCode('E_UNMAPPED_BINDING', () =>
    catalog.specForSeatCast(shipped, { harness: 'claude', model: 'fable' }, quiet, 'interviewer'));
  eq(catalog.specForSeatCast(shipped, { harness: 'claude', model: 'claude-fable-5' }, quiet, 'x').key,
     'claude/claude-fable-5', 'control');
  if (!/castable/i.test(err.message)) throw new Error('the refusal does not name the castable set');
  return err.code;
});

// ── 4 · an unknown harness is refused ────────────────────────────────────────────────────────
check('(4) an unconfigured harness is REFUSED', () => {
  const err = expectCode('E_UNMAPPED_BINDING', () =>
    catalog.specForSeatCast(shipped, { harness: 'gpt-cli', model: 'gpt-9' }, quiet, 'aseat'));
  return err.code;
});

// ── 5 · THE KEY AND THE ARGV MUST AGREE — the guard that replaced the ambiguity refusal ──────
//
// `launch-specs:`' key is what every seat cast resolves through, so a spec filed under one model
// whose argv runs another is the same silent-wrong-model launch the ambiguity refusal guarded
// against, one level down. `profiles.js#validateSpecKey` refuses it at config LOAD; this arm plants
// exactly that disagreement, and PAIRS it with an agreeing spec so a validator that refused
// everything could not read green.
check('(5) a spec whose argv contradicts its KEY is refused at config LOAD', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'keyguard-'));
  const write = (model, argvModel) => {
    const f = path.join(dir, `${model}.yaml`);
    fs.writeFileSync(f, [
      `default_workdir_root: ${dir}`,
      'launch-specs:',
      '  claude:',
      `    ${model}:`,
      `      exec: { argv: ["claude", "-p", "--model", "${argvModel}"], prompt: stdin }`,
      '      session_ref: { source: cwd-implicit }',
      `      workdir_root: ${dir}`,
      '      caps: { memory_max: "64M" }',
      '',
    ].join('\n'));
    return f;
  };
  const err = expectCode('E_CONFIG_LOAD', () => loadConfig(write('claude-opus-5', 'claude-haiku-4-5')));
  if (!/claude-haiku-4-5/.test(err.message)) throw new Error('the refusal does not name what the argv RUNS');
  loadConfig(write('claude-sonnet-5', 'claude-sonnet-5'));      // CONTROL — agreement loads clean
  return `${err.code} — key says claude-opus-5, argv runs claude-haiku-4-5`;
});

// ── 6 · the key-guard's derivation edges ─────────────────────────────────────────────────────
// `bindingOf` no longer DERIVES a catalog (7.787 — the key does that). It is what
// `validateSpecKey` compares a key against, so its edges still decide whether arm 5's guard can be
// fooled, and they are still asserted here.
check('(6) a trailing model flag pins NOTHING; `-m` is read; `--model` wins when both appear', () => {
  eq(catalog.bindingOf({ exec: { argv: ['claude', '--model'] } }).model, '', 'trailing flag');
  eq(catalog.bindingOf({ exec: { argv: ['opencode', 'run', '-m', 'a/b'] } }).model, 'a/b', '-m');
  eq(catalog.bindingOf({ exec: { argv: ['x', '-m', 'second', '--model', 'first'] } }).model, 'first', 'flag order');
  eq(catalog.bindingOf({ exec: { argv: ['/usr/local/bin/claude', '-p'] } }).harness, 'claude', 'basename');
  eq(catalog.bindingOf({ headed: {} }), null, 'no exec: half is not checkable against a key');
  return 'four edges';
});

// ── 7 · THE FIX · a real descriptor's cast beats the caller's profile ────────────────────────
check('(7) a REAL descriptor cast claude-fable-5 resolves that spec, and nothing else can be asked for', () => {
  const dir = seatWith('seat: interviewer\nharness: claude\nmodel: claude-fable-5\neffort: high\nmode: interactive');
  eq(seatDeclaresValue(dir, 'model'), 'claude-fable-5', 'scalar reader');
  eq(launchSpecForSeat(shipped, dir, quiet).key, 'claude/claude-fable-5', 'resolved spec');
  // ⚑ THE ABOLITION, ASSERTED STRUCTURALLY. `launchSpecForSeat` takes no caller profile: there is
  // no parameter through which a transport could ask for a different one. A signature check is the
  // only way to assert an ABSENCE — an arm that passed a name would just be testing arity.
  if (launchSpecForSeat.length !== 3) {
    throw new Error(`launchSpecForSeat takes ${launchSpecForSeat.length} args — a caller-supplied `
      + 'profile parameter is back, which is what #d-abolish-profile-names deleted');
  }
  return 'the descriptor is the only input';
});

// ── 8 · THE FIX · an UNCAST seat refuses, with NOTHING left to fall back to ──────────────────
check('(8) an UNCAST seat REFUSES — there is no fallback anywhere any more', () => {
  // ⚑ THIS ARM WAS INVERTED 2026-08-11 (D2) AND NARROWED AGAIN 2026-08-12. It once asserted the
  // OPPOSITE — that an open, absent or partial descriptor falls back to the caller's profile — and
  // that fallback was the defect: it is how a transport's value came to decide what an agent ran.
  // D2 made it refuse EXCEPT where the caller's own profile pinned no model (D3(a)); 7.787 deleted
  // the caller's profile entirely, so that carve-out has no subject and the refusal is total. The
  // old expectations are preserved here in words because a reader meeting this check needs to know
  // it changed by ruling, twice, not by drift.
  const cases = [
    ['open binding', seatWith('seat: goal-master\nagent_type: master\nmode: interactive')],
    ['no frontmatter', seatWith(null)],
    ['no seat.md', path.join(os.tmpdir(), 'cast-probe-absent-seat')],
    // A HALF cast (harness, no model) is not a cast — `declaresBinding` needs both, matching
    // `open_binding`'s all-three-or-none rule. It refuses with the rest.
    ['partial cast', seatWith('seat: half\nharness: claude\nmode: interactive')],
  ];
  for (const [what, dir] of cases) {
    let code = null;
    try { launchSpecForSeat(shipped, dir, quiet); }
    catch (err) { code = err.code; }
    if (code !== 'E_UNCAST_SEAT') {
      throw new Error(`${what}: expected E_UNCAST_SEAT, got ${code || 'NO THROW — something was returned'}`);
    }
  }
  // …and the CONTROL that this arm is not vacuous: a FULL cast resolves. Without it, a resolver
  // that threw E_UNCAST_SEAT unconditionally would read green on every line above.
  const full = seatWith('seat: full\nharness: claude\nmodel: claude-opus-5\neffort: high');
  eq(launchSpecForSeat(shipped, full, quiet).key, 'claude/claude-opus-5', 'control resolves');
  // ⚑ AND THE RETIRED CARVE-OUT IS ASSERTED GONE. D3(a) let an uncast seat launch when the
  // CALLER's profile pinned no model — the `sleep`-based probe stand-ins. Those live in the
  // `jobs:` block now and `specForSeatCast` never reads it, so a model-less table refuses the same
  // uncast seat as the shipped one. Planted because a re-introduced carve-out would be silent.
  const modelless = {};
  let bareCode = null;
  try { catalog.specForSeatCast(modelless, { harness: '', model: '' }, quiet, 'bare'); }
  catch (err) { bareCode = err.code; }
  eq(bareCode, 'E_UNCAST_SEAT', 'a model-less table no longer lets an uncast seat through');
  return 'four refusals + control resolves + the D3(a) carve-out asserted GONE';
});

// ── 9 · THE FIX · an unmappable cast STOPS the launch ────────────────────────────────────────
// The defect class in one arm: the wrong answer here is "return claude-sonnet and launch it".
check('(9) a seat cast as something unspawnable REFUSES rather than launching the caller profile', () => {
  const dir = seatWith('seat: ghost\nharness: claude\nmodel: claude-fable-9\neffort: high', 'ghost');
  const err = expectCode('E_UNMAPPED_BINDING', () => launchSpecForSeat(shipped, dir, quiet));
  if (!/ghost/.test(err.message)) throw new Error('the refusal does not name the seat');
  return err.code;
});

// ── 10 · THE DRIFT ALARM · one derivation law, two implementations ───────────────────────────
check('(10) the JS catalog equals `bindings.py#catalog` ROW FOR ROW on the shipped config', () => {
  const mine = catalog.catalogOf(shipped).map((r) => `${r.key}|${r.harness}|${r.model}`);
  let theirs;
  try {
    const out = execFileSync('python', ['-c',
      'import sys,json; sys.path.insert(0, sys.argv[1]); import bindings;'
      + ' print(json.dumps(["%s|%s|%s" % (r["spec"], r["harness"], r["model"]) for r in bindings.catalog(sys.argv[2])]))',
      path.join(IGNITE_ROOT, 'capabilities', 'bindings', 'tool'), SHIPPED,
    ], { encoding: 'utf8', timeout: 60000 });
    theirs = JSON.parse(out.trim().split('\n').pop());
  } catch (err) {
    // A missing/broken python is a SKIP with its reason, never a silent pass: the alarm did not
    // ring because it was not armed, and those are different facts.
    skipped += 1;
    lines.push(`SKIP (10) parity vs bindings.py — could not run the Python side: ${err.message.split('\n')[0]}`);
    return null;
  }
  if (mine.length !== theirs.length) throw new Error(`row COUNT differs: js ${mine.length}, py ${theirs.length}`);
  for (let i = 0; i < mine.length; i++) {
    if (mine[i] !== theirs[i]) throw new Error(`row ${i} differs: js ${mine[i]} | py ${theirs[i]}`);
  }
  if (mine.length === 0) throw new Error('both catalogs are EMPTY — an agreement that proves nothing');
  return `${mine.length} rows identical`;
});

const ended = new Date();
const passCount = lines.filter((l) => l.startsWith('PASS')).length;
const body = [
  'probe: probe-binding-catalog',
  `started: ${started.toISOString()}`,
  'command: node deploy/probe-suite.js --only probe-binding-catalog',
  ...lines,
  `status: ${failed ? 'FAIL' : 'PASS'}`,
  `checks: ${lines.length} (${passCount} pass, ${lines.filter((l) => l.startsWith('FAIL')).length} fail)`,
  `SKIPPED_COUNT: ${skipped}`,
  `exit: ${failed ? 1 : 0}`,
  `wall_ms: ${ended - started}`,
  `ended: ${ended.toISOString()}`,
  '',
].join('\n');
fs.writeFileSync(OUT, body);
process.stdout.write(body);
// A truncated run must never read greener than a complete one (G-121).
process.exit(failed ? 1 : 0);
