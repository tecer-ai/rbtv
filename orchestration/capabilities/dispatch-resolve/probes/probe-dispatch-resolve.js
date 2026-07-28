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
// Run:  node orchestration/capabilities/dispatch-resolve/probes/probe-dispatch-resolve.js
// Exit: 0 = all checks passed, 1 = at least one failed.

const path = require('node:path');
const yaml = (() => { try { return require('js-yaml'); } catch { return null; } })();
const fs = require('node:fs');

const lane = require('..');
const profiles = require('../../../../ignite/launch-profiles');

const CONFIG = path.resolve(__dirname, '../../../../ignite/config/spawn-profiles.yaml');

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
    detail = `${e.code || e.name}: ${e.message.split('\n')[0].slice(0, 120)}`;
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

// ── 0 · PRECONDITIONS — the probe's own premises, asserted not assumed ────────────────────────
// A guard that denies `claude-seat` proves nothing if `claude-seat` does not declare SeatBinds, and
// a load that "succeeds thanks to the stub" proves nothing if the bare load also succeeds. Both are
// asserted here, at the instant this probe runs (`bars.md` 11 third half — a control proves its
// precondition WHEN it runs, never for the run that follows).

check('P1', 'the committed config exists at the path this lane reads', () => {
  if (!fs.existsSync(CONFIG)) throw new Error(`absent: ${CONFIG}`);
  return CONFIG;
});

check('P2', 'BARE load REFUSES (so the stub is load-bearing, not decorative)', () =>
  expectRefusal('E_CONFIG_LOAD', () => profiles.loadConfig(CONFIG)));

check('P3', 'claude-seat REALLY declares sandbox.SeatBinds (else check 1 is vacuous)', () => {
  const raw = fs.readFileSync(CONFIG, 'utf8');
  if (!yaml) {
    if (!/SeatBinds/.test(raw)) throw new Error('no SeatBinds key anywhere in the config');
    return 'SeatBinds present (textual assert — js-yaml unavailable)';
  }
  const d = yaml.load(raw);
  const binds = d.profiles['claude-seat'].sandbox.SeatBinds;
  if (binds === undefined) throw new Error('claude-seat declares NO SeatBinds — check 1 is vacuous');
  return `claude-seat.sandbox.SeatBinds = ${JSON.stringify(binds)}`;
});

// The stub is what makes the whole file loadable to this consumer. Everything below needs it.
const config = lane.loadProfiles(CONFIG);

check('P4', 'WITH the stub the whole file loads (all 6 profiles)', () => {
  const n = Object.keys(config.profiles).length;
  if (n !== 6) throw new Error(`expected 6 profiles, got ${n}`);
  return `${n} profiles loaded`;
});

// ── 1 · THE DENY-LIST — the leader's binding acceptance bar ───────────────────────────────────

check('1-RED', 'resolving claude-seat is REFUSED (the deny-list FIRES)', () =>
  expectRefusal(lane.E_SEATBINDS_PROFILE, () => lane.assertNoSeatBinds(config, 'claude-seat')));

check('1-GREEN', 'a profile WITHOUT SeatBinds passes the deny-list (it is not blanket-refusing)', () => {
  lane.assertNoSeatBinds(config, 'claude-sonnet-tools');
  return 'claude-sonnet-tools admitted';
});

check('1-RED-via-entry', 'the deny-list fires through the ENTRY POINT too, not only the bound', () =>
  expectRefusal(lane.E_SEATBINDS_PROFILE, () =>
    lane.preflightDispatch(config, 'claude-seat', { addDir: '/tmp', effort: 'high' })));

// ── 2 · THE CONFINEMENT SPLIT (row G1) — homed in the pre-flight per ruling #1486 ──────────────

check('2a-RED', 'a dispatch with NO work-target is REFUSED', () =>
  expectRefusal(lane.E_ADD_DIR_ABSENT, () =>
    lane.preflightDispatch(config, 'claude-sonnet-tools', { effort: 'high' })));

check('2b-RED', 'a RELATIVE work-target is REFUSED', () =>
  expectRefusal(lane.E_ADD_DIR_RELATIVE, () =>
    lane.preflightDispatch(config, 'claude-sonnet-tools', { addDir: 'relative/path', effort: 'high' })));

check('2-GREEN', 'an ABSOLUTE work-target passes the bound (it is not blanket-refusing)', () => {
  lane.assertWorkTarget('/home/henri');
  return '/home/henri admitted';
});

// ── 3 · THE PINNED-FLAG PRE-FLIGHT — criterion 3's leg, against the LIVE binary ────────────────

check('3-GREEN', 'claude-sonnet-tools pre-flights CLEAN against the live installed claude', () => {
  const r = lane.preflightDispatch(config, 'claude-sonnet-tools', {
    addDir: '/home/henri', effort: 'high',
  });
  if (r.preflight.missing.length) throw new Error(`missing flags: ${r.preflight.missing}`);
  return `checked ${JSON.stringify(r.preflight.checked)} missing []`;
});

check('3-RED', 'a pinned flag absent from live --help goes RED (the green discriminates)', () =>
  expectRefusal('E_PINNED_FLAG_ABSENT', () =>
    profiles.preflightPinnedFlags({ binary: 'claude', argv: ['claude', '-p', '--this-flag-does-not-exist'] })));

// ── 4 · EFFORT REACHES THE HARNESS IN ITS OWN DIALECT — criterion 4 ───────────────────────────

check('4', 'abstract effort is translated per-profile, never hand-written', () => {
  const c = lane.preflightDispatch(config, 'claude-sonnet-tools', { addDir: '/home/henri', effort: 'high' });
  const hasEffort = c.argv.includes('--effort') && c.argv[c.argv.indexOf('--effort') + 1] === 'high';
  if (!hasEffort) throw new Error(`claude dialect not applied: ${JSON.stringify(c.argv)}`);
  // The SAME abstract level renders differently for a different dialect — that IS the translation.
  const x = profiles.resolveProfile(config, 'codex-git-write', { slots: { workdir: '/tmp' }, effort: 'high' });
  const codexRendered = x.argv.join(' ');
  if (!codexRendered.includes('model_reasoning_effort=high')) {
    throw new Error(`codex dialect not applied: ${codexRendered}`);
  }
  return "abstract 'high' -> claude '--effort high' AND codex '-c model_reasoning_effort=high'";
});

check('4-RED', 'an effort level outside the closed vocabulary is REFUSED', () =>
  expectRefusal('E_UNKNOWN_EFFORT', () =>
    profiles.resolveProfile(config, 'claude-sonnet-tools', { slots: {}, effort: 'turbo' })));

// ── 5 · NO RAW FLAGS — the conductor cannot smuggle argv past the profile ──────────────────────

check('5-RED', 'a slot the profile does not declare is REFUSED (no raw-flag smuggling)', () =>
  expectRefusal('E_RAW_FLAG', () =>
    profiles.resolveProfile(config, 'claude-sonnet-tools', { slots: { workdir: '/tmp' }, effort: 'high' })));

// ── 6 · END-TO-END — the manifest mapping is USABLE, not merely recorded ──────────────────────
//
// `bars.md` 10: verify at the artifact the CONSUMER reads. Checks 1-5 drive the lane with profile
// names this probe supplies; that proves the lane, not the migration. THIS check reads the
// `launch_profile` mapping OFF DISK from each package manifest and drives the whole path with it —
// which is the only version of criterion 2 that can fail if the mapping is wrong.

const EXPECTED_COVERAGE = { 'claude-code-cli': 'sonnet', opencode: 'sakana' };

check('6', 'every recorded launch_profile resolves + pre-flights end-to-end', () => {
  if (!yaml) throw new Error('js-yaml unavailable — cannot read manifests');
  const modelsDir = path.resolve(__dirname, '../../../models');
  const found = [];
  for (const pkg of fs.readdirSync(modelsDir)) {
    const mf = path.join(modelsDir, pkg, 'manifest.yaml');
    if (!fs.existsSync(mf)) continue;
    const d = yaml.load(fs.readFileSync(mf, 'utf8'));
    for (const v of d.variants || []) {
      if (!v.launch_profile) continue;
      // ⚠ EFFORT IS PASSED ONLY WHERE THE PROFILE DECLARES A DIAL — and the dial-less case is
      // asserted LOUD below (check 6-EFFORT-GAP), never worked around here. The resolver's own
      // refusal says a dial-less harness "must declare 'effort: { inert: true }' so the slot is
      // STATED inert rather than silently absent"; a lane that quietly dropped the effort would
      // defeat that design — the same shape as a stub defeating the SeatBinds guard.
      const hasDial = Boolean(config.profiles[v.launch_profile].effort);
      let note = hasDial ? '' : ' (NO effort dial)';
      try {
        const r = lane.preflightDispatch(config, v.launch_profile, {
          addDir: '/home/henri', ...(hasDial ? { effort: 'high' } : {}),
        });
        if (!r.argv.length) throw new Error(`${pkg}:${v.variant} resolved an empty argv`);
        if (r.preflight.missing.length) {
          throw new Error(`${pkg}:${v.variant} pre-flight missing ${r.preflight.missing}`);
        }
        note += ' PRE-FLIGHT GREEN';
      } catch (e) {
        // ⚠ A binary whose `--help` cannot be READ is NOT a clean bill of health, and this lane
        // fails closed on it — see check 6-PREFLIGHT-GAP for the measured cause. Recorded here
        // rather than swallowed: the mapping resolves, the pre-flight cannot look.
        if (e.code !== 'E_PREFLIGHT_UNAVAILABLE') throw e;
        note += ' PRE-FLIGHT UNAVAILABLE (see 6-PREFLIGHT-GAP)';
      }
      found.push(`${pkg}:${v.variant} -> ${v.launch_profile}${note}`);
    }
  }
  if (!found.length) throw new Error('NO launch_profile recorded anywhere — check is vacuous');
  return found.join(' | ');
});

// ⚠ A LIVE PROFILE DEFECT, ASSERTED RATHER THAN WORKED AROUND (finding, task 7.54).
// Routing sets `effort = f(boundedness)` for EVERY dispatch, so the conductor always holds one.
// `opencode-sakana` declares no effort table and does NOT declare `effort: { inert: true }`, so the
// resolver refuses the pair outright. ⇒ of the 2 covered pairs, only `claude-code-cli:sonnet` can
// complete a resolver-backed dispatch that carries an effort. The fix is one line in
// `ignite/config/spawn-profiles.yaml` — THE LIVE DAEMON'S ARMED CONFIG, whose edit is the leader's
// call, not this row's. This check FAILS THE DAY IT IS FIXED, which is the intent: it is the
// tripwire that tells the next reader the gap closed.
check('6-EFFORT-GAP', 'the opencode-sakana effort gap is still open (tripwire — flip when fixed)', () =>
  expectRefusal('E_UNKNOWN_EFFORT', () =>
    lane.preflightDispatch(config, 'opencode-sakana', { addDir: '/home/henri', effort: 'high' })));

// ⚠ A SECOND LIVE GAP, in 7.42's pre-flight rather than in a profile — MEASURED, not inferred:
//   opencode run --help  ->  exit 0, 0 bytes on stdout, 3053 bytes on STDERR
//   claude --help / codex exec --help  ->  stdout (16036 / 3681 bytes)
// `readHelp` (launch-profiles/preflight.js:67) merges stderr ONLY in its CATCH branch, i.e. only
// when the binary exits NON-ZERO. On a clean exit `execFileSync` returns STDOUT ALONE, so a CLI
// that prints help to stderr and exits 0 reads as empty and raises E_PREFLIGHT_UNAVAILABLE. The
// module's own comment says "both streams are captured" — true only on the error path, and the
// "exit non-zero" qualifier is doing silent load-bearing work.
// ⇒ THE ERROR'S STATED CAUSE ("some CLIs render help only to a TTY") POINTS AT THE WRONG THING and
// would send the next debugger after a TTY. `ignite/launch-profiles/` is not this row's write
// surface, so this is FILED, never fixed here. Failing closed is correct meanwhile: an unreadable
// --help must not read as a clean bill of health.
check('6-PREFLIGHT-GAP', 'the opencode pre-flight gap is still open (tripwire — flip when fixed)', () =>
  expectRefusal('E_PREFLIGHT_UNAVAILABLE', () =>
    lane.preflightDispatch(config, 'opencode-sakana', { addDir: '/home/henri' })));

check('6-COUNTS', 'covered-vs-elected counts are as MEASURED (criterion 2 reports them)', () => {
  if (!yaml) throw new Error('js-yaml unavailable');
  const modelsDir = path.resolve(__dirname, '../../../models');
  // CLI packages only — API workers and the Agent-tool carrier are out by the row's construction.
  const CLI = ['claude-code-cli', 'codex-cli', 'kimi-code-cli', 'opencode'];
  let elected = 0; let covered = 0;
  for (const pkg of CLI) {
    const d = yaml.load(fs.readFileSync(path.join(modelsDir, pkg, 'manifest.yaml'), 'utf8'));
    for (const v of d.variants || []) {
      elected += 1;
      if (v.launch_profile) covered += 1;
    }
  }
  if (elected !== 11) throw new Error(`expected 11 elected CLI pairs, counted ${elected}`);
  if (covered !== 2) throw new Error(`expected 2 covered pairs, counted ${covered}`);
  // The uncovered pairs MUST still have a manual — their invocation knowledge is their only home
  // until 7.86 lands, and deleting it is what this row was ruled NOT to do.
  for (const pkg of CLI) {
    if (!fs.existsSync(path.join(modelsDir, pkg, 'manual.md'))) {
      throw new Error(`${pkg}/manual.md is MISSING — the uncovered pairs lost their only home`);
    }
  }
  return `covered ${covered} / elected ${elected}; all 4 CLI package manuals intact`;
});

// ── report ────────────────────────────────────────────────────────────────────────────────────

console.log('probe-dispatch-resolve — task 7.54\n');
for (const r of results) {
  console.log(`  ${r.ok ? 'PASS' : 'FAIL'}  ${r.id.padEnd(14)} ${r.what}`);
  if (r.detail) console.log(`        ${r.detail}`);
}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
