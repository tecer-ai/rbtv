#!/usr/bin/env node
'use strict';

// probe-dispatch-resolve — task 7.54's acceptance instrument.
//
// ⚠⚠ EVERY REFUSAL IS PROVEN IN BOTH DIRECTIONS, AND THAT IS THE POINT OF THIS FILE, not a
// flourish. `bars.md` 11 second half: a negative needs a positive control IN THE SAME RUN, and the
// control needs its own proof that it fires — "it passed everywhere" and "it cannot fail anywhere"
// print the same thing. The leader's binding addition on this row says it in the row's own terms:
// "a deny-list demonstrated only in the green direction is the guard it replaced, wearing a
// different name."
//
// So each bound below is exercised RED (the refusal fires) AND GREEN (an input that must pass,
// does). A bound with only one direction is not reported as proven.
//
// ══════════════════════════════════════════════════════════════════════════════════════════════
// ⚠ REPOINTED 2026-08-10 — THE LANE LEGS NOW RUN AGAINST A FIXTURE, THE LIVE LEGS ARE MEASUREMENTS.
//
// This probe used to name four LIVE profiles — `claude-seat`, `claude-sonnet-tools`,
// `codex-git-write`, `opencode-sakana` — and assert the roster was 6. `r-seats-only-architecture`
// (owner, 2026-08-06) retired all four and re-rostered the file to 14 profiles, so 11 of 19 checks
// failed at their PRECONDITIONS with `E_UNKNOWN_PROFILE` before any bound was exercised. A probe
// whose preconditions fail reports the same red for "the guard broke" and "the config moved" — its
// verdict carried no information at all, and it stayed that way through unrelated edits.
//
// The fix follows the sibling `probe-extra-dir-slot.js` exactly: the LANE'S OWN BOUNDS (the
// deny-list, the confinement split, effort translation, the raw-flag refusal, the pinned-flag
// pre-flight) are mechanism, and mechanism is proven on a fixture this file owns — a roster change
// can never strand them again. What genuinely IS a statement about the live tree stays live, as
// the three `LIVE-*` measurements at the bottom.
// ══════════════════════════════════════════════════════════════════════════════════════════════
//
// Run:  node orchestration/capabilities/dispatch-resolve/probes/probe-dispatch-resolve.js
//       (direct, like its sibling — `ignite/deploy/probe-suite.js` enumerates `ignite/` only, so
//        an orchestration-module probe is outside its reach.)
// Exit: 0 = all checks passed, 1 = at least one failed.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { createRequire } = require('node:module');

const lane = require('..');
const profiles = require('../../../../ignite/launch-profiles');

const CONFIG = path.resolve(__dirname, '../../../../ignite/config/spawn-profiles.yaml');
const MODELS_DIR = path.resolve(__dirname, '../../../models');

// js-yaml is `ignite/`'s dependency, installed in `ignite/node_modules` — a bare require from THIS
// folder walks up from `orchestration/` and misses it, which silently degraded three checks to
// "js-yaml unavailable" on any box without a root-level install. Resolve it the way the resolver
// this lane already depends on resolves it, so the probe and its subject share one copy.
const yaml = (() => {
  try { return require('js-yaml'); } catch { /* fall through */ }
  try { return createRequire(require.resolve('../../../../ignite/launch-profiles'))('js-yaml'); }
  catch { return null; }
})();

let pass = 0;
let fail = 0;
const results = [];

function check(id, what, fn) {
  let ok = false;
  let detail = '';
  try {
    detail = fn() || '';
    ok = true;
  } catch (e) {
    ok = false;
    detail = `${e.code || e.name}: ${e.message.split('\n')[0].slice(0, 160)}`;
  }
  results.push({ id, what, ok, detail });
  if (ok) pass += 1; else fail += 1;
}

function expectRefusal(code, fn) {
  try {
    fn();
  } catch (e) {
    if (e.code === code) return `REFUSED with ${code} — as required`;
    throw new Error(`expected ${code}, got ${e.code || e.name}: ${e.message.slice(0, 90)}`);
  }
  throw new Error(`NO REFUSAL — expected ${code}. The guard did not fire.`);
}

// ── the fixture ───────────────────────────────────────────────────────────────────────────────
// FOUR profiles, one per shape the lane's bounds need, and nothing else:
//   fx-seat     declares `sandbox.SeatBinds`   -> the deny-list's RED, and the reason the bare
//               load refuses (so the stub is provably load-bearing)
//   fx-claude   a plain claude profile with an effort dial -> the deny-list's GREEN, the
//               confinement split, the live pinned-flag pre-flight, the claude effort dialect
//   fx-codex    the SECOND dialect — the same abstract level rendering differently is what makes
//               "translated, never hand-written" a claim rather than a coincidence
//   fx-no-dial  no effort block at all -> the G-270 refusal of a dial-less pair
// `claude` is the binary on the two claude rows deliberately: the pinned-flag pre-flight shells
// out to the LIVE `claude --help`, which is a real property of this box and not fixture-able.
const FIXTURE_YAML = `
default_workdir_root: /tmp
caps:
  runtime_max: "1h"
profiles:
  fx-seat:
    exec:
      argv: ["claude", "-p"]
      prompt: stdin
    sandbox:
      SeatBinds: ["bind:{seatDir}"]
    session_ref: { source: assigned }
    workdir_root: /tmp
  fx-claude:
    exec:
      argv: ["claude", "-p", "--model", "claude-sonnet-5", "--output-format", "stream-json", "--verbose"]
      prompt: stdin
    effort:
      dialect: effort
      values: { low: low, medium: medium, high: high, max: max }
      argv: ["--effort", "{effort}"]
    session_ref: { source: assigned }
    workdir_root: /tmp
  fx-codex:
    exec:
      argv: ["codex", "exec", "--cd", "{workdir}"]
      prompt: stdin
    effort:
      dialect: thinking
      values: { low: low, medium: medium, high: high, max: high }
      argv: ["-c", "model_reasoning_effort={effort}"]
    session_ref: { source: assigned }
    workdir_root: /tmp
  fx-no-dial:
    exec:
      argv: ["claude", "-p"]
      prompt: stdin
    session_ref: { source: assigned }
    workdir_root: /tmp
`;

const fixturePath = path.join(
  fs.mkdtempSync(path.join(os.tmpdir(), 'probe-dispatch-resolve-')),
  'fixture-profiles.yaml',
);
fs.writeFileSync(fixturePath, FIXTURE_YAML, 'utf8');

// ── 0 · PRECONDITIONS — the probe's own premises, asserted not assumed ────────────────────────
// A guard that denies `fx-seat` proves nothing if `fx-seat` does not declare SeatBinds, and a load
// that "succeeds thanks to the stub" proves nothing if the bare load also succeeds. Both are
// asserted here, at the instant this probe runs (`bars.md` 11 third half — a control proves its
// precondition WHEN it runs, never for the run that follows).

check('P1', 'the committed config exists at the path this lane reads', () => {
  if (!fs.existsSync(CONFIG)) throw new Error(`absent: ${CONFIG}`);
  return CONFIG;
});

check('P2', 'BARE load of the fixture REFUSES (so the stub is load-bearing, not decorative)', () =>
  expectRefusal('E_CONFIG_LOAD', () => profiles.loadConfig(fixturePath)));

check('P3', 'fx-seat REALLY declares sandbox.SeatBinds (else the deny-list check is vacuous)', () => {
  const raw = fs.readFileSync(fixturePath, 'utf8');
  if (!/SeatBinds/.test(raw)) throw new Error('no SeatBinds key anywhere in the fixture');
  return 'fx-seat.sandbox.SeatBinds declared in the fixture this probe wrote';
});

// The stub is what makes the whole file loadable to this consumer. Everything below needs it.
const config = lane.loadProfiles(fixturePath);

check('P4', 'WITH the stub the whole fixture loads (all 4 profiles)', () => {
  const names = Object.keys(config.profiles);
  // The literal is safe HERE and was not safe before: this file writes the fixture six lines up,
  // so the count can only drift in the same edit that changes it.
  if (names.length !== 4) throw new Error(`expected 4 fixture profiles, got ${names.length}`);
  return names.join(', ');
});

// ── 1 · THE DENY-LIST — the leader's binding acceptance bar ───────────────────────────────────

check('1-RED', 'resolving fx-seat is REFUSED (the deny-list FIRES)', () =>
  expectRefusal(lane.E_SEATBINDS_PROFILE, () => lane.assertNoSeatBinds(config, 'fx-seat')));

check('1-GREEN', 'a profile WITHOUT SeatBinds passes the deny-list (it is not blanket-refusing)', () => {
  // ⚠ NOT a vacuous green, and the distinction is what the old version lost: `assertNoSeatBinds`
  // RETURNS SILENTLY for an unknown profile name, so the retired `claude-sonnet-tools` kept
  // "passing" this check for days after it stopped existing. The fixture profile is asserted
  // present first, so a green here means admitted, never absent.
  if (!config.profiles['fx-claude']) throw new Error('fx-claude absent — the green would be vacuous');
  lane.assertNoSeatBinds(config, 'fx-claude');
  return 'fx-claude present AND admitted';
});

check('1-RED-via-entry', 'the deny-list fires through the ENTRY POINT too, not only the bound', () =>
  expectRefusal(lane.E_SEATBINDS_PROFILE, () =>
    lane.preflightDispatch(config, 'fx-seat', { addDir: '/tmp', effort: 'high' })));

// ── 2 · THE CONFINEMENT SPLIT (row G1) — homed in the pre-flight per ruling #1486 ──────────────

check('2a-RED', 'a dispatch with NO work-target is REFUSED', () =>
  expectRefusal(lane.E_ADD_DIR_ABSENT, () =>
    lane.preflightDispatch(config, 'fx-claude', { effort: 'high' })));

check('2b-RED', 'a RELATIVE work-target is REFUSED', () =>
  expectRefusal(lane.E_ADD_DIR_RELATIVE, () =>
    lane.preflightDispatch(config, 'fx-claude', { addDir: 'relative/path', effort: 'high' })));

check('2-GREEN', 'an ABSOLUTE work-target passes the bound (it is not blanket-refusing)', () => {
  const target = path.resolve(os.tmpdir());
  lane.assertWorkTarget(target);
  return `${target} admitted`;
});

// ── 3 · THE PINNED-FLAG PRE-FLIGHT — criterion 3's leg, against the LIVE binary ────────────────

check('3-GREEN', 'fx-claude pre-flights CLEAN against the live installed claude', () => {
  const r = lane.preflightDispatch(config, 'fx-claude', {
    addDir: path.resolve(os.tmpdir()), effort: 'high',
  });
  if (r.preflight.missing.length) throw new Error(`missing flags: ${r.preflight.missing}`);
  return `checked ${JSON.stringify(r.preflight.checked)} missing []`;
});

check('3-RED', 'a pinned flag absent from live --help goes RED (the green discriminates)', () =>
  expectRefusal('E_PINNED_FLAG_ABSENT', () =>
    profiles.preflightPinnedFlags({ binary: 'claude', argv: ['claude', '-p', '--this-flag-does-not-exist'] })));

// ── 4 · EFFORT REACHES THE HARNESS IN ITS OWN DIALECT — criterion 4 ───────────────────────────

check('4', 'abstract effort is translated per-profile, never hand-written', () => {
  const c = lane.preflightDispatch(config, 'fx-claude', { addDir: path.resolve(os.tmpdir()), effort: 'high' });
  const hasEffort = c.argv.includes('--effort') && c.argv[c.argv.indexOf('--effort') + 1] === 'high';
  if (!hasEffort) throw new Error(`claude dialect not applied: ${JSON.stringify(c.argv)}`);
  // The SAME abstract level renders differently for a different dialect — that IS the translation.
  const x = profiles.resolveProfile(config, 'fx-codex', { slots: { workdir: '/tmp' }, effort: 'high' });
  const codexRendered = x.argv.join(' ');
  if (!codexRendered.includes('model_reasoning_effort=high')) {
    throw new Error(`codex dialect not applied: ${codexRendered}`);
  }
  return "abstract 'high' -> claude '--effort high' AND codex '-c model_reasoning_effort=high'";
});

check('4-RED', 'an effort level outside the closed vocabulary is REFUSED', () =>
  expectRefusal('E_UNKNOWN_EFFORT', () =>
    profiles.resolveProfile(config, 'fx-claude', { slots: {}, effort: 'turbo' })));

check('4-NO-DIAL', 'a profile with NO effort table refuses the pair rather than dropping it (G-270)', () =>
  // Was `6-EFFORT-GAP`, a tripwire on the live `opencode-sakana`. The GUARD is what this row owns
  // and the guard is mechanism, so it is proven on a dial-less fixture instead. A live profile that
  // forgets `effort: { inert: true }` is a CONFIG defect, and LIVE-2 below is where config defects
  // are now measured.
  expectRefusal('E_UNKNOWN_EFFORT', () =>
    lane.preflightDispatch(config, 'fx-no-dial', { addDir: path.resolve(os.tmpdir()), effort: 'high' })));

// ── 5 · NO RAW FLAGS — the conductor cannot smuggle argv past the profile ──────────────────────

check('5-RED', 'a slot the profile does not declare is REFUSED (no raw-flag smuggling)', () =>
  expectRefusal('E_RAW_FLAG', () =>
    profiles.resolveProfile(config, 'fx-claude', { slots: { workdir: '/tmp' }, effort: 'high' })));

// ── 6 · THE STDERR-HELP DEFECT IN 7.42's PRE-FLIGHT — reproduced, not narrated ─────────────────
//
// MEASURED (2026-07-28, against the real `opencode run --help`): exit 0, 0 bytes on stdout, 3053
// bytes on STDERR. `readHelp` (`ignite/launch-profiles/preflight.js`) merges stderr ONLY in its
// CATCH branch, i.e. only when the binary exits NON-ZERO — on a clean exit `execFileSync` returns
// STDOUT ALONE, so a CLI that prints help to stderr and exits 0 reads as empty and raises
// E_PREFLIGHT_UNAVAILABLE. The module's own comment says "both streams are captured": true only on
// the error path, and the "exit non-zero" qualifier is doing silent load-bearing work. The error's
// STATED cause ("some CLIs render help only to a TTY") points at the wrong thing and would send the
// next debugger after a TTY.
//
// ⚠ THE TRIPWIRE USED TO NEED `opencode` INSTALLED, which made a code-level defect look like a
// property of whichever box ran the probe. `node` reproduces it exactly and is already required to
// run this file. `ignite/launch-profiles/` is not this row's write surface, so the defect is still
// FILED, never fixed here — failing closed meanwhile is correct: an unreadable --help must not read
// as a clean bill of health.
const STDERR_HELP = ['-e', "process.stderr.write('--fx-pinned-flag\\n')"];
const STDOUT_HELP = ['-e', "process.stdout.write('--fx-pinned-flag\\n')"];
const HELP_PROBE = { name: 'fx-stderr-help', binary: 'node', argv: ['node', '--fx-pinned-flag'] };

check('6-STDERR-HELP-GAP', 'help on STDERR at exit 0 still reads as unavailable (tripwire — flip when fixed)', () =>
  expectRefusal('E_PREFLIGHT_UNAVAILABLE', () =>
    profiles.preflightPinnedFlags(HELP_PROBE, { helpArgs: STDERR_HELP })));

check('6-STDERR-HELP-GREEN', 'the SAME help on STDOUT is read fine (the red is the stream, not the flag)', () => {
  const r = profiles.preflightPinnedFlags(HELP_PROBE, { helpArgs: STDOUT_HELP });
  if (r.missing.length) throw new Error(`missing ${r.missing} — the control does not discriminate`);
  return `checked ${JSON.stringify(r.checked)} missing [] — only the STREAM differs from the red above`;
});

// ── LIVE · WHAT IS ACTUALLY TRUE OF THE SHIPPED TREE RIGHT NOW ────────────────────────────────
//
// Three measurements, deliberately roster-COUNT-independent: they assert relationships, never a
// number a ruling can change overnight. Two of them are tripwires over LIVE DEFECTS this row does
// not own and must not paper over — each flips the day the defect closes.

check('LIVE-1', 'the shipped config still loads through this consumer\'s stub', () => {
  const shipped = lane.loadProfiles(CONFIG);
  const n = Object.keys(shipped.profiles).length;
  if (n === 0) throw new Error('no profiles loaded — every check below would be vacuous');
  return `${n} shipped profiles loaded`;
});

// ⚠ LIVE DEFECT #1, ASSERTED RATHER THAN WORKED AROUND.
// `r-seats-only-architecture` (2026-08-06) moved SeatBinds from ONE profile (`claude-seat`) to the
// ONE SHARED `cage:` block every profile inherits. The conductor's deny-list refuses any profile
// declaring `sandbox.SeatBinds` — correctly, since this consumer loads them through a
// non-interpreting stub — so it now refuses ALL of them: the dispatch-resolve lane can resolve
// ZERO live profiles. The deny-list is not wrong; its premise (seat profiles are the exception) is.
// The fix is an architecture call — teach this lane the cage vocabulary, or give the conductor a
// cage-free profile family — and is NOT this row's to make. This check FAILS THE DAY IT IS FIXED.
check('LIVE-2', 'EVERY shipped profile is deny-listed, so the lane resolves none (tripwire — flip when fixed)', () => {
  const shipped = lane.loadProfiles(CONFIG);
  const names = Object.keys(shipped.profiles);
  const resolvable = names.filter((n) => {
    try { lane.assertNoSeatBinds(shipped, n); return true; } catch { return false; }
  });
  if (resolvable.length) {
    throw new Error(`${resolvable.length}/${names.length} shipped profiles are now resolvable ` +
      `(${resolvable.join(', ')}) — restore a real end-to-end leg here and in LIVE-3`);
  }
  return `0/${names.length} resolvable; all carry the shared cage's SeatBinds`;
});

// ⚠ LIVE DEFECT #2, same treatment. Task 7.86 repointed every recorded `launch_profile` at a
// conductor-lane `cli-*` twin it was to author; `r-seats-only-architecture` then retired that whole
// family. The twins were never authored, so the manifest -> profile mapping is 100% DANGLING: every
// recorded value names a profile the shipped config does not have. The sibling probe
// (`probe-extra-dir-slot.js` check 4-GAP) measures the same absence from the config side; this is
// the manifest side of one fact. Replaces the old `6` / `6-COUNTS` pair, whose hardcoded
// "2 covered / 11 elected" literals were stale the day 7.86 landed.
check('LIVE-3', 'every recorded launch_profile is DANGLING (tripwire — flip when the profiles land)', () => {
  if (!yaml) throw new Error('js-yaml unresolvable from here AND from ignite/ — cannot read manifests');
  const shipped = lane.loadProfiles(CONFIG);
  const recorded = [];
  for (const pkg of fs.readdirSync(MODELS_DIR)) {
    const mf = path.join(MODELS_DIR, pkg, 'manifest.yaml');
    if (!fs.existsSync(mf)) continue;
    const d = yaml.load(fs.readFileSync(mf, 'utf8'));
    for (const v of d.variants || []) {
      if (v.launch_profile) recorded.push({ pair: `${pkg}:${v.variant}`, profile: v.launch_profile });
    }
  }
  if (!recorded.length) throw new Error('NO launch_profile recorded anywhere — the check is vacuous');
  const present = recorded.filter((r) => Boolean(shipped.profiles[r.profile]));
  if (present.length) {
    throw new Error(`${present.length}/${recorded.length} mappings now RESOLVE ` +
      `(${present.map((r) => `${r.pair}->${r.profile}`).join(', ')}) — replace this tripwire with an ` +
      'end-to-end resolve+pre-flight leg over the mappings that landed');
  }
  return `${recorded.length} recorded mappings, 0 present in the shipped roster ` +
    `(all name retired/unauthored cli-* twins, e.g. ${recorded[0].pair} -> ${recorded[0].profile})`;
});

check('LIVE-4', 'the uncovered pairs keep their invocation manual (their only home until 7.86 lands)', () => {
  // Unchanged in intent from the old `6-COUNTS` tail, minus the literals: the manuals are what this
  // row was ruled NOT to delete, and that bound holds whatever the roster count is.
  const CLI = ['claude-code-cli', 'codex-cli', 'kimi-code-cli', 'opencode'];
  for (const pkg of CLI) {
    if (!fs.existsSync(path.join(MODELS_DIR, pkg, 'manual.md'))) {
      throw new Error(`${pkg}/manual.md is MISSING — the uncovered pairs lost their only home`);
    }
  }
  return `all ${CLI.length} CLI package manuals intact`;
});

// ── report ────────────────────────────────────────────────────────────────────────────────────

console.log('probe-dispatch-resolve — task 7.54\n');
for (const r of results) {
  console.log(`  ${r.ok ? 'PASS' : 'FAIL'}  ${r.id.padEnd(20)} ${r.what}`);
  if (r.detail) console.log(`        ${r.detail}`);
}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
