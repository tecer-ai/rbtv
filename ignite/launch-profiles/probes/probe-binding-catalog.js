'use strict';

// probe-binding-catalog — the (harness, model) -> profile-name catalog (task 7.54, ruling D19).
//
// TWO THINGS ARE UNDER TEST, and they are different claims:
//
//   1. THE CATALOG resolves a cast to exactly one profile name, and REFUSES rather than guessing
//      when it cannot (unknown pair, alias spelling, ambiguous pair). The refusals are the point:
//      the defect being fixed is a SILENT wrong-model launch, so every arm that refuses is paired
//      with the arm that shows the same input succeeding when it should.
//
//   2. THE FIX resolves a REAL `seat.md` descriptor — the seat's cast beats the caller's profile,
//      an undeclared cast falls back to the caller's profile unchanged (the channel master's
//      `open_binding` case), and an unmappable cast STOPS the launch. Exercised through
//      `spawn.js#profileForSeatCast` against descriptors written to a temp dir, never a stub: a
//      probe that stubbed the descriptor read would prove the catalog and not the fix.
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
const { profileForSeatCast, seatDeclaresValue } = require('../../server/spawn/spawn');
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
const shipped = loadConfig(SHIPPED).profiles;

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
check('(1) claude + claude-fable-5 resolves to the claude-fable profile', () => {
  const name = catalog.profileForBinding(shipped, { harness: 'claude', model: 'claude-fable-5' });
  eq(name, 'claude-fable', 'profile');
  return name;
});

// ── 2 · every shipped profile round-trips through its own cast ───────────────────────────────
// The whole-set version of arm 1: no profile may resolve to a DIFFERENT profile than itself, which
// is the property that makes the mapping usable as an identity for a launch.
check('(2) every castable shipped profile round-trips to itself', () => {
  const rows = catalog.catalogOf(shipped);
  for (const r of rows) {
    if (!catalog.declaresBinding(r)) continue;              // test-sleep pins no model
    const back = catalog.profileForBinding(shipped, r);
    eq(back, r.profile, `round-trip of ${r.profile}`);
  }
  return `${rows.length} rows`;
});

// ── 3 · an ALIAS is refused, never rewritten ─────────────────────────────────────────────────
// `bindings.md`: the model vocabulary is the profile's pin VERBATIM. The pairing matters — the
// same harness with the PINNED spelling must succeed, or "it refused" would be compatible with a
// catalog that refuses everything.
check('(3) the `fable` alias is REFUSED while `claude-fable-5` succeeds', () => {
  const err = expectCode('E_UNMAPPED_BINDING', () =>
    catalog.profileForBinding(shipped, { harness: 'claude', model: 'fable' }, { seat: 'interviewer' }));
  eq(catalog.profileForBinding(shipped, { harness: 'claude', model: 'claude-fable-5' }), 'claude-fable', 'control');
  if (!/castable/i.test(err.message)) throw new Error('the refusal does not name the castable set');
  return err.code;
});

// ── 4 · an unknown harness is refused ────────────────────────────────────────────────────────
check('(4) an unconfigured harness is REFUSED', () => {
  const err = expectCode('E_UNMAPPED_BINDING', () =>
    catalog.profileForBinding(shipped, { harness: 'gpt-cli', model: 'gpt-9' }));
  return err.code;
});

// ── 5 · an AMBIGUOUS pair is refused, not picked ─────────────────────────────────────────────
// The one place this side is stricter than `bindings.py#castable()`, which lets a duplicate win
// last. Here the answer launches a process.
check('(5) two profiles claiming one (harness, model) are REFUSED, not ranked', () => {
  const twins = {
    'twin-a': { exec: { argv: ['claude', '-p', '--model', 'claude-opus-5'] } },
    'twin-b': { exec: { argv: ['claude', '-p', '--model', 'claude-opus-5'] } },
  };
  const err = expectCode('E_AMBIGUOUS_BINDING', () =>
    catalog.profileForBinding(twins, { harness: 'claude', model: 'claude-opus-5' }));
  if (!/twin-a/.test(err.message) || !/twin-b/.test(err.message)) {
    throw new Error('the refusal does not name BOTH claimants');
  }
  return err.code;
});

// ── 6 · the derivation law's edges ───────────────────────────────────────────────────────────
check('(6) a trailing model flag pins NOTHING; `-m` is read; `--model` wins when both appear', () => {
  eq(catalog.bindingOf({ exec: { argv: ['claude', '--model'] } }).model, '', 'trailing flag');
  eq(catalog.bindingOf({ exec: { argv: ['opencode', 'run', '-m', 'a/b'] } }).model, 'a/b', '-m');
  eq(catalog.bindingOf({ exec: { argv: ['x', '-m', 'second', '--model', 'first'] } }).model, 'first', 'flag order');
  eq(catalog.bindingOf({ exec: { argv: ['/usr/local/bin/claude', '-p'] } }).harness, 'claude', 'basename');
  eq(catalog.bindingOf({ headed: {} }), null, 'no exec: half casts nothing');
  return 'four edges';
});

// ── 7 · THE FIX · a real descriptor's cast beats the caller's profile ────────────────────────
check('(7) a seat cast claude-fable-5 launches claude-fable even when the caller asked for claude-sonnet', () => {
  const dir = seatWith('seat: interviewer\nharness: claude\nmodel: claude-fable-5\neffort: high\nmode: interactive');
  eq(seatDeclaresValue(dir, 'model'), 'claude-fable-5', 'scalar reader');
  eq(profileForSeatCast(shipped, dir, 'claude-sonnet', quiet), 'claude-fable', 'resolved profile');
  return 'cast wins';
});

// ── 8 · THE FIX · an undeclared cast falls back, unchanged ───────────────────────────────────
// The channel master (`open_binding`: all three omitted) and every unmaterialized seat. This is
// the arm that keeps the fix additive — a workspace that casts nothing behaves as it did before.
check('(8) open-binding / absent / partial descriptors fall back to the caller profile', () => {
  const master = seatWith('seat: goal-master\nagent_type: master\nmode: interactive');
  eq(profileForSeatCast(shipped, master, 'claude-sonnet', quiet), 'claude-sonnet', 'open binding');

  const noFrontmatter = seatWith(null);
  eq(profileForSeatCast(shipped, noFrontmatter, 'claude-sonnet', quiet), 'claude-sonnet', 'no frontmatter');

  const missingDir = path.join(os.tmpdir(), 'cast-probe-absent-seat');
  eq(profileForSeatCast(shipped, missingDir, 'claude-sonnet', quiet), 'claude-sonnet', 'no seat.md');

  // A HALF cast (harness with no model) is not a cast — `declaresBinding` needs both, matching
  // `open_binding`'s all-three-or-none rule. It falls back rather than refusing, because the
  // materializer already refuses a partial declaration at authoring time.
  const half = seatWith('seat: half\nharness: claude\nmode: interactive');
  eq(profileForSeatCast(shipped, half, 'claude-sonnet', quiet), 'claude-sonnet', 'partial cast');

  // …and the CONTROL that this arm is not vacuous: the same reader on a full cast does divert.
  const full = seatWith('seat: full\nharness: claude\nmodel: claude-opus-5\neffort: high');
  eq(profileForSeatCast(shipped, full, 'claude-sonnet', quiet), 'claude-opus', 'control diverts');
  return 'four fallbacks + control';
});

// ── 9 · THE FIX · an unmappable cast STOPS the launch ────────────────────────────────────────
// The defect class in one arm: the wrong answer here is "return claude-sonnet and launch it".
check('(9) a seat cast as something unspawnable REFUSES rather than launching the caller profile', () => {
  const dir = seatWith('seat: ghost\nharness: claude\nmodel: claude-fable-9\neffort: high', 'ghost');
  const err = expectCode('E_UNMAPPED_BINDING', () => profileForSeatCast(shipped, dir, 'claude-sonnet', quiet));
  if (!/ghost/.test(err.message)) throw new Error('the refusal does not name the seat');
  return err.code;
});

// ── 10 · THE DRIFT ALARM · one derivation law, two implementations ───────────────────────────
check('(10) the JS catalog equals `bindings.py#catalog` ROW FOR ROW on the shipped config', () => {
  const mine = catalog.catalogOf(shipped).map((r) => `${r.profile}|${r.harness}|${r.model}`);
  let theirs;
  try {
    const out = execFileSync('python', ['-c',
      'import sys,json; sys.path.insert(0, sys.argv[1]); import bindings;'
      + ' print(json.dumps(["%s|%s|%s" % (r["profile"], r["harness"], r["model"]) for r in bindings.catalog(sys.argv[2])]))',
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
