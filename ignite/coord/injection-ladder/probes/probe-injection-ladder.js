'use strict';

// Probe for the ONE per-harness injection ladder (task 7.45, CMP-9).
//
// Self-contained: requires only this module and node builtins — NO daemon, no heart store, no
// config file. That is not convenience, it is the assertion: CMP-9 dropped the `uses → server`
// edge, and a probe that needed the daemon to exercise the ladder would disprove the property the
// module exists to have.
//
// ⚠ EVERY LEG BELOW WAS MUTATION-TESTED — see the `.out` capture and README § Probe. A leg that
// cannot go red proves nothing (`bars.md` 11), and the specific shape to avoid on THIS module is
// `p-green-harness-over-a-broken-mechanism`: handing the ladder the rung it is supposed to select.
// So no leg passes a rung in. Legs 4–6 are the ones that would go green under a table with no
// per-harness differences at all, which is why they carry the self-check comments they do.

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const ladder = require('..');

const lines = [];
const start = Date.now();
function ok(msg) { lines.push(`PASS ${msg}`); }
function note(msg) { lines.push(`     ${msg}`); }

function expectThrow(label, fn, code) {
  let err = null;
  try { fn(); } catch (e) { err = e; }
  assert.ok(err, `${label}: expected a throw, nothing was raised`);
  assert.strictEqual(err.name, 'LadderError', `${label}: expected a typed LadderError, got ${err.name}: ${err.message}`);
  assert.strictEqual(err.code, code, `${label}: expected ${code}, got ${err.code}`);
  return err;
}

function main() {
  // ── 1 · the closed vocabulary, and its ORDER ───────────────────────────────────────────────
  assert.deepStrictEqual(ladder.RUNGS, ['headless', 'hooks', 'keystroke']);
  ok('1  RUNGS is the ladder order headless -> hooks -> keystroke (CMP-9 § layout)');
  assert.deepStrictEqual(ladder.KNOWN_HARNESSES.slice().sort(), ['claude', 'codex', 'kimi', 'opencode']);
  ok(`1b harness vocabulary is closed: ${ladder.KNOWN_HARNESSES.join('|')}`);

  // ── 2 · harness identification from the profile's OWN argv[0] (D23) ─────────────────────────
  for (const [argv0, want] of [['claude', 'claude'], ['codex', 'codex'], ['opencode', 'opencode'],
    ['kimi', 'kimi'],
    ['sleep', null], ['bash', null], ['claude-code', null], [undefined, null]]) {
    assert.strictEqual(ladder.harnessFromBinary(argv0), want, `harnessFromBinary(${argv0})`);
  }
  assert.strictEqual(ladder.harnessOf({ exec: { argv: ['codex', 'exec'] } }), 'codex');
  assert.strictEqual(ladder.harnessOf({ exec: { argv: ['sleep', '3600'] } }), null);
  assert.strictEqual(ladder.harnessOf(null), null);
  assert.strictEqual(ladder.harnessOf({}), null);
  ok('2  harnessOf/harnessFromBinary: the four harnesses resolve; sleep/bash/absent/null -> null');

  // ── 3 · an unknown harness is a TYPED refusal, never a guess and never a TypeError ──────────
  // `kimi` was this leg's stand-in until 2026-08-07, when it gained a MEASURED row and stopped
  // being unknown. The leg asserts a PROPERTY (an unnamed harness is refused, never guessed), so it
  // needs a name that is genuinely absent from the table — not the one that just joined it.
  const e3 = expectThrow('unknown harness', () => ladder.resolveRung('aider', { phase: 'launch' }), 'E_UNKNOWN_HARNESS');
  assert.ok(/does not guess/.test(e3.message), 'unknown-harness refusal must say it does not guess');
  expectThrow('unknown rung', () => ladder.rungFor('claude', 'telepathy'), 'E_UNKNOWN_RUNG');
  ok('3  unknown harness -> E_UNKNOWN_HARNESS; unknown rung -> E_UNKNOWN_RUNG (both typed)');

  // ── 4 · the WALK at phase launch — the caller names NO rung ─────────────────────────────────
  for (const h of ['claude', 'codex', 'opencode', 'kimi']) {
    const r = ladder.resolveRung(h, { phase: 'launch' });
    assert.strictEqual(r.rung, 'headless', `${h} at launch should take the top rung`);
  }
  ok('4  launch phase: all three harnesses take the TOP rung (headless) when nothing bars it');

  // ── 5 · THE DISCRIMINATING LEG — two harnesses, same request, DIFFERENT answers ─────────────
  // This is the leg that fails if the table has no real per-harness content. `opencode run` is
  // ONE-SHOT (G-13, live-verified): the seat executes its prompt and exits, so a caller that must
  // reach the session again cannot have it. claude/codex resume by session id and can.
  const claudeAgain = ladder.resolveRung('claude', { phase: 'launch', needResumable: true });
  assert.strictEqual(claudeAgain.rung, 'headless');
  const codexAgain = ladder.resolveRung('codex', { phase: 'launch', needResumable: true });
  assert.strictEqual(codexAgain.rung, 'headless');
  const e5 = expectThrow(
    'opencode must refuse a re-reachable launch',
    () => ladder.resolveRung('opencode', { phase: 'launch', needResumable: true }),
    'E_NO_RUNG_AVAILABLE',
  );
  // The refusal must name EVERY rung it passed and why — a bare "no" would leave the caller to
  // re-derive the reason, which is how the opencode one-shot fact got re-learned three times.
  assert.deepStrictEqual(e5.details.skipped.map((s) => s.rung), ['headless', 'hooks', 'keystroke']);
  assert.ok(/reached again/.test(e5.details.skipped[0].why), 'the headless skip must cite re-reachability');
  ok('5  SAME request, DIFFERENT answers: claude/codex -> headless; opencode -> typed refusal (G-13 one-shot)');
  note(`5  opencode refusal names all three rungs: ${e5.details.skipped.map((s) => `${s.rung}(${s.why})`).join(' | ')}`);

  // ── 5b · the near-miss this walk was WRITTEN WRONG for once ─────────────────────────────────
  // A `resumable === false` test (instead of `!== true`) falls through opencode's one-shot rung
  // onto `hooks` and returns it confidently — and hooks cannot reach a live session at all.
  // Asserting the refusal rather than "not headless" is what makes that mutation visible.
  assert.throws(
    () => ladder.resolveRung('opencode', { phase: 'launch', needResumable: true }),
    (e) => e.code === 'E_NO_RUNG_AVAILABLE',
    'opencode+needResumable must REFUSE, never silently fall through to hooks',
  );
  ok('5b opencode+needResumable REFUSES rather than falling through to a rung that cannot deliver');

  // ── 6 · phase discriminates: inject reaches a LIVE session, so only keystroke applies ───────
  for (const h of ladder.KNOWN_HARNESSES) {
    const r = ladder.resolveRung(h, { phase: 'inject' });
    assert.strictEqual(r.rung, 'keystroke', `${h} at inject phase must reach the last-resort rung`);
    assert.deepStrictEqual(r.skipped.map((s) => s.rung), ['headless', 'hooks'],
      `${h}: the walk must PASS the launch-only rungs, not skip the ladder`);
  }
  ok('6  inject phase: the walk passes headless+hooks (launch-only) and lands on keystroke');

  // ── 6b · assert the PHASE TABLE ITSELF, and the REASON a rung is passed ─────────────────────
  // Added after this probe's own mutation sweep found a hole: making keystroke launch-eligible
  // left all other legs green, because every launch case already resolves at a HIGHER rung, so
  // nothing ever observed the change. The launch-only / inject-only property was load-bearing and
  // asserted nowhere. A rung's phase set is a fact, so it is asserted as a fact.
  assert.deepStrictEqual(ladder.RUNG_PHASES.headless, ['launch']);
  assert.deepStrictEqual(ladder.RUNG_PHASES.hooks, ['launch']);
  assert.deepStrictEqual(ladder.RUNG_PHASES.keystroke, ['inject'],
    'keystroke is inject-ONLY: it needs a live TUI to type into, which is why it is the last resort');
  // The behavioural half of the same fact: with both launch rungs barred, the walk must REFUSE —
  // it must NOT reach keystroke, because you cannot type into a session that does not exist yet.
  const e6b = expectThrow(
    'keystroke must not be reachable at launch',
    () => ladder.resolveRung('claude', { phase: 'launch', hostSupports: { headless: false, hooks: false } }),
    'E_NO_RUNG_AVAILABLE',
  );
  assert.ok(/inject-only/.test(e6b.details.skipped[2].why),
    'the keystroke skip at launch must cite inject-only, not a host or resumability reason');
  ok('6b RUNG_PHASES asserted directly, and keystroke is UNREACHABLE at launch even with both rungs above it barred');

  // ── 7 · host capability removes a rung (fail closed at the bottom) ──────────────────────────
  const noExec = ladder.resolveRung('claude', { phase: 'launch', hostSupports: { headless: false } });
  assert.strictEqual(noExec.rung, 'hooks');
  expectThrow(
    'no rung left',
    () => ladder.resolveRung('claude', { phase: 'inject', hostSupports: { keystroke: false } }),
    'E_NO_RUNG_AVAILABLE',
  );
  ok('7  hostSupports removes a rung; exhausting the ladder is E_NO_RUNG_AVAILABLE, never a fallback');

  // ── 8 · the hooks rung WRITES NOTHING (CMP-9 § Interface) ───────────────────────────────────
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ladder-probe-'));
  const before = fs.readdirSync(dir);
  const plan = ladder.hooksConfigFor('claude', { sessionDir: dir, editablePaths: ['/tmp/x'] });
  const after = fs.readdirSync(dir);
  assert.deepStrictEqual(after, before, 'hooksConfigFor must perform NO I/O — it returns a descriptor');
  assert.strictEqual(after.length, 0, 'the session dir must still be empty after hooksConfigFor');
  assert.strictEqual(plan.files.length, 1);
  assert.strictEqual(plan.result.enforceable, true);
  // and the same call for the harness whose config is NOT enforceable
  assert.strictEqual(ladder.hooksConfigFor('codex', { sessionDir: dir }).result.enforceable, false);
  assert.strictEqual(ladder.hooksConfigFor('opencode', { sessionDir: dir }).result.enforceable, false);
  // null harness: no dirs, no files, no I/O
  const nullPlan = ladder.hooksConfigFor(null, { sessionDir: dir });
  assert.deepStrictEqual([nullPlan.dirs.length, nullPlan.files.length], [0, 0]);
  assert.deepStrictEqual(fs.readdirSync(dir), []);
  fs.rmSync(dir, { recursive: true, force: true });
  ok('8  hooksConfigFor returns a DESCRIPTOR and touches the filesystem zero times, for all 4 cases');

  // ── 8b · A HARNESS WITH NO MEASURED HOOKS RUNG PLANS NOTHING — AND PLANS NOTHING OF ANOTHER
  //          HARNESS'S. Until 2026-08-07 this function ended in a bare fallthrough that ASSUMED
  //          opencode, so the first harness added to the table would have had `opencode.json`
  //          planned into its seat dir — and opencode strict-validates that file, so the
  //          contamination is a startup kill wherever it lands. The guard is the DECLARED rung, so
  //          it is asserted through the declaration and against the neighbour it would have leaked.
  const kimiPlan = ladder.hooksConfigFor('kimi', { sessionDir: '/tmp/kimi-seat', editablePaths: ['/tmp/kimi-seat'] });
  assert.strictEqual(ladder.rungFor('kimi', 'hooks').available, false,
    'kimi declares no measured hooks rung — that declaration is what makes 8b meaningful');
  assert.deepStrictEqual([kimiPlan.dirs.length, kimiPlan.files.length], [0, 0],
    `a hooks-less harness must plan no files, planned: ${kimiPlan.files.map((f) => f.path).join(', ')}`);
  assert.strictEqual(kimiPlan.result.written, null);
  assert.strictEqual(kimiPlan.harness, 'kimi', 'the descriptor must still name its own harness');
  // The neighbour it would have leaked from still plans its own two files — so 8b is a real
  // discrimination, not a function that stopped planning for everyone.
  const ocPlan = ladder.hooksConfigFor('opencode', { sessionDir: '/tmp/oc-seat' });
  assert.deepStrictEqual(ocPlan.files.map((f) => path.basename(f.path)).sort(),
    ['.ignite-sandbox-note.txt', 'opencode.json']);
  ok('8b a hooks-less harness (kimi) plans ZERO files and never inherits opencode\'s — while opencode still plans both of its own');

  // ── 9 · the module reaches nothing under server/ (the dropped `uses -> server` edge) ────────
  const own = ['index.js', 'ladder.js', 'errors.js'];
  for (const f of own) {
    const src = fs.readFileSync(path.join(__dirname, '..', f), 'utf8');
    const bad = src.match(/require\(['"][^'"]*server\/[^'"]*['"]\)/g);
    assert.strictEqual(bad, null, `${f} requires something under server/: ${bad && bad.join(', ')}`);
  }
  ok(`9  no module file requires anything under server/ (checked ${own.join(', ')}) — CMP-9's dropped edge holds`);
}

const outPath = path.join(__dirname, 'probe-injection-ladder.out');
const header = [
  'probe: probe-injection-ladder',
  `started: ${new Date().toISOString()}`,
  'command: node injection-ladder/probes/probe-injection-ladder.js',
];
let status = 'PASS';
let exit = 0;
try {
  main();
} catch (err) {
  status = 'FAIL';
  exit = 1;
  lines.push(`error: ${err.code || err.name}: ${err.message}`);
}
const legs = lines.filter((l) => l.startsWith('PASS ')).length;
fs.writeFileSync(
  outPath,
  header.concat(lines, [
    `legs_passed: ${legs}`,
    `status: ${status}`,
    `exit: ${exit}`,
    `wall_ms: ${Date.now() - start}`,
    `ended: ${new Date().toISOString()}`,
  ]).join('\n') + '\n',
  'utf8',
);
process.stdout.write(`${status} — ${legs} legs — ${outPath}\n`);
process.exit(exit);
