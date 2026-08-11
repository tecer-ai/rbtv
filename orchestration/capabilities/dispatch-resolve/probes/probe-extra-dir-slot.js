#!/usr/bin/env node
'use strict';

// probe-extra-dir-slot — task 7.87 criterion 4's acceptance instrument.
//
// THE CLAIM UNDER TEST: the conductor's enforced add-dir refusal now resolves the work-target
// THROUGH the declared `{extra_dir}` slot instead of leaving the flag hand-composed, and the G1
// confinement split (`cards/dispatch-wrapper.md:36`) is expressible end-to-end in a profile.
//
// ⚠ IT RUNS AGAINST A FIXTURE CONFIG, DELIBERATELY, AND THAT IS THE SAFETY BOUND — not a shortcut.
// `ignite/config/spawn-profiles.yaml` is the LIVE DAEMON'S ARMED CONFIG: writing `--add-dir
// {extra_dir}` into a shipped profile would change that profile's resolved argv for EVERY daemon
// spawn, which is exactly what task 7.42's byte-unchanged criterion (re-asserted at 7.87) forbids
// this row to do on its own authority. So the mechanism is proven on a fixture, and the shipped
// config is asserted UNTOUCHED by the same run (check 4).
//
// ⚠ EVERY LEG IS EXERCISED IN BOTH DIRECTIONS (`bars.md` 11): a slot that fills and a slot that is
// never injected print the same "green" unless the RED control fires. Check 2-RED reverts the
// injection in-process and asserts the resolution then FAILS — without it, check 2 cannot tell
// "the resolver filled the slot" from "the profile never needed one".
//
// Run:  node orchestration/capabilities/dispatch-resolve/probes/probe-extra-dir-slot.js
//       (direct, like its sibling probe-dispatch-resolve.js — `ignite/deploy/probe-suite.js`
//        enumerates `ignite/` only, so an orchestration-module probe is outside its reach.)
// Exit: 0 = all checks passed, 1 = at least one failed.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const lane = require('..');
const profiles = require('../../../../ignite/launch-profiles');
const resolve = require('../resolve');

const SHIPPED_CONFIG = path.resolve(__dirname, '../../../../ignite/config/spawn-profiles.yaml');
const WORK_TARGET = path.resolve(os.tmpdir());

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
    detail = `${e.code || e.name}: ${String(e.message).split('\n')[0].slice(0, 160)}`;
  }
  results.push({ id, what, ok, detail });
  if (ok) pass += 1; else fail += 1;
}

function expectRefusal(code, fn) {
  try {
    fn();
  } catch (e) {
    if (e.code === code) return `REFUSED with ${code} — as required`;
    throw new Error(`expected ${code}, got ${e.code || e.name}: ${String(e.message).slice(0, 110)}`);
  }
  throw new Error(`NO REFUSAL — expected ${code}. The guard did not fire.`);
}

// ── the fixture ───────────────────────────────────────────────────────────────────────────────
// `claude` is the binary because the pinned-flag pre-flight is part of what this proves: a
// profile-written `--add-dir` is scanned by `pinnedFlagsOf` and checked against the LIVE `--help`,
// which a hand-composed flag never was. `fx-split` declares the slot; `fx-no-split` is its
// negative twin — same shape, no `{extra_dir}` — so check 3 can show non-declaring profiles are
// untouched rather than merely asserting it.
const FIXTURE_YAML = `
default_workdir_root: /tmp
caps:
  runtime_max: "1h"
profiles:
  fx-split:
    exec:
      argv: ["claude", "-p", "--add-dir", "{extra_dir}"]
      prompt: stdin
    session_ref: { source: assigned }
    workdir_root: /tmp
  fx-no-split:
    exec:
      argv: ["claude", "-p"]
      prompt: stdin
    session_ref: { source: assigned }
    workdir_root: /tmp
`;

const fixturePath = path.join(
  fs.mkdtempSync(path.join(os.tmpdir(), 'probe-extra-dir-')),
  'fixture-profiles.yaml',
);
fs.writeFileSync(fixturePath, FIXTURE_YAML, 'utf8');
const config = lane.loadProfiles(fixturePath);

// ── 0 · PRECONDITIONS — the probe's own premises, asserted not assumed ────────────────────────

check('P1', '{extra_dir} is a DECLARED slot of the shared vocabulary (else every leg is vacuous)', () => {
  if (!profiles.CLOSED_SLOTS.has('{extra_dir}')) {
    throw new Error(`CLOSED_SLOTS = ${[...profiles.CLOSED_SLOTS].join(' ')} — {extra_dir} absent`);
  }
  return `CLOSED_SLOTS = ${[...profiles.CLOSED_SLOTS].join(' ')}`;
});

check('P2', 'the fixture profile really WRITES the add-dir flag (else check 2 proves nothing)', () => {
  const argv = config.profiles['fx-split'].exec.argv;
  if (!argv.includes('--add-dir') || !argv.includes('{extra_dir}')) {
    throw new Error(`fx-split argv does not carry the flag+slot pair: ${JSON.stringify(argv)}`);
  }
  return JSON.stringify(argv);
});

// ── 1 · THE DECLARATION PREDICATE — both directions ───────────────────────────────────────────

check('1', 'declaresExtraDir discriminates: true for fx-split, FALSE for fx-no-split', () => {
  if (!lane.declaresExtraDir(config.profiles['fx-split'])) throw new Error('fx-split read as NOT declaring');
  if (lane.declaresExtraDir(config.profiles['fx-no-split'])) throw new Error('fx-no-split read as DECLARING');
  return 'fx-split true / fx-no-split false';
});

// ── 2 · END-TO-END — the work-target reaches argv through the PROFILE'S OWN position ──────────

check('2', 'the declared slot is filled from addDir, in the position the profile wrote', () => {
  const r = lane.preflightDispatch(config, 'fx-split', { addDir: WORK_TARGET });
  const i = r.argv.indexOf('--add-dir');
  if (i < 0 || r.argv[i + 1] !== WORK_TARGET) {
    throw new Error(`work-target not in the profile's position: ${JSON.stringify(r.argv)}`);
  }
  if (r.addDirResolved !== true) throw new Error('addDirResolved is not true — the caller is told it still owes a flag');
  if (r.preflight.missing.length) throw new Error(`pre-flight missing ${r.preflight.missing}`);
  return `${JSON.stringify(r.argv)} | pre-flight checked ${JSON.stringify(r.preflight.checked)}`;
});

check('2-RED', 'REVERTING the injection breaks the resolution (check 2 discriminates)', () => {
  // The pre-7.87 behaviour, reproduced exactly: resolve with the caller's slots UNTOUCHED. The
  // declared position then has no value and the shared resolver refuses — which is the proof that
  // check 2's green comes from the injection and not from the profile happening to resolve anyway.
  return expectRefusal('E_MISSING_KEY', () =>
    profiles.resolveProfile(config, 'fx-split', { slots: {} }));
});

check('2-DOOR', 'a caller-supplied slots.extra_dir cannot route around the absolute-path bound', () => {
  // The relative value must never reach argv: `addDir` is the one door, and it overwrites.
  const r = lane.preflightDispatch(config, 'fx-split', {
    addDir: WORK_TARGET, slots: { extra_dir: 'relative/smuggled' },
  });
  if (r.argv.includes('relative/smuggled')) throw new Error(`smuggled value reached argv: ${JSON.stringify(r.argv)}`);
  // ...and the bound itself still fires when the door carries the relative value.
  expectRefusal(lane.E_ADD_DIR_RELATIVE, () =>
    lane.preflightDispatch(config, 'fx-split', { addDir: 'relative/smuggled' }));
  return 'slots.extra_dir overwritten by the validated addDir; E_ADD_DIR_RELATIVE still fires';
});

// ── 3 · STRICTLY OPT-IN — a non-declaring profile is UNCHANGED ────────────────────────────────

check('3', 'a profile declaring no {extra_dir} resolves byte-identically and reports it', () => {
  const r = lane.preflightDispatch(config, 'fx-no-split', { addDir: WORK_TARGET });
  const expected = config.profiles['fx-no-split'].exec.argv;
  if (JSON.stringify(r.argv) !== JSON.stringify(expected)) {
    throw new Error(`argv changed: ${JSON.stringify(r.argv)} != ${JSON.stringify(expected)}`);
  }
  if (r.addDirResolved !== false) throw new Error('addDirResolved is not false — caller would drop its hand-composed flag');
  return `${JSON.stringify(r.argv)} | addDirResolved false`;
});

check('3-RED', 'injecting the slot into a NON-declaring profile is refused (the opt-in is enforced)', () =>
  expectRefusal('E_RAW_FLAG', () =>
    profiles.resolveProfile(config, 'fx-no-split', { slots: { extra_dir: WORK_TARGET } })));

// ── 4 · THE SAFETY BOUND — the LIVE daemon config is untouched by this widening ────────────────

check('4', 'NO shipped profile declares {extra_dir}, so every daemon argv is byte-unchanged', () => {
  const shipped = lane.loadProfiles(SHIPPED_CONFIG);
  const names = Object.keys(shipped.profiles);
  if (names.length === 0) throw new Error('no profiles loaded — the check would be vacuous');
  const declaring = names.filter((n) => resolve.declaresExtraDir(shipped.profiles[n]));
  const textual = fs.readFileSync(SHIPPED_CONFIG, 'utf8').includes('{extra_dir}');
  if (declaring.length || textual) {
    throw new Error(`shipped config now declares {extra_dir} (${declaring.join(', ') || 'textual match'}) — ` +
      're-assert task 7.42 byte-unchanged-daemon-behaviour before flipping this check');
  }
  return `${names.length} shipped profiles, none declaring {extra_dir}`;
});

// ⚠ TRIPWIRE — FLIPS THE DAY A CONDUCTOR-LANE PROFILE IS AUTHORED. The `cli-*` family this split
// belongs on was retired by `r-seats-only-architecture` (2026-08-06) and never re-created; the
// manifest field that once pointed at it (`launch_profile`) was retired with the deny-list by the
// owner ruling of 2026-08-11. Until a cage-free conductor-lane profile exists, the split cannot be
// declared on a real profile without editing a LIVE daemon row. This check states that absence as a
// measurement rather than leaving it implied.
check('4-GAP', 'no conductor-lane cli-* profile exists (tripwire — flip when one is authored)', () => {
  const shipped = lane.loadProfiles(SHIPPED_CONFIG);
  const present = Object.keys(shipped.profiles).filter((n) => n.startsWith('cli-'));
  if (present.length) {
    throw new Error(`cli-* profiles now exist (${present.join(', ')}) — declare --add-dir {extra_dir} on them ` +
      'and replace this tripwire with a real end-to-end leg');
  }
  return 'no cli-* profile in the shipped config; the fixture is the only end-to-end surface today';
});

// ── report ────────────────────────────────────────────────────────────────────────────────────

console.log('probe-extra-dir-slot — task 7.87 criterion 4\n');
for (const r of results) {
  console.log(`  ${r.ok ? 'PASS' : 'FAIL'}  ${r.id.padEnd(8)} ${r.what}`);
  if (r.detail) console.log(`        ${r.detail}`);
}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
