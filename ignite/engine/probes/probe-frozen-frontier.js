#!/usr/bin/env node
'use strict';

// probe-frozen-frontier — LE-13's ONE-TOKEN GUARD (2026-08-19), replayed against the recorded
// meet-transcript-summarizer 08-19 freeze (see the seat's own completion report for that replay's
// output — a real-data replay does not belong in a committed fixture).
//
// THE MEASURED DEFECT (root-cause-archaeology-2026-08-19.md §1.7): `seedGoal`'s empty-frontier
// guard read `readyRows.length || moving` — "did coord return ZERO rows" — while the actual freeze
// shape is "coord returned rows and ruled NONE of them READY". `readyRows.length` is truthy on ANY
// non-empty answer, so a goal where coord ruled every row BLOCKED/HELD/SKEW (never an empty `[]`)
// walked straight past the guard as healthy. The fix is one token: `ready.size` (the already-in-
// scope FILTERED READY map) in place of `readyRows.length`.
//
// THE DISCRIMINATING PAIR, and why it is the point: a probe that only asserts the frozen case would
// pass on code that alarms unconditionally. Both fixtures are ONE real seat that coord (the real
// `team-kit/coord.py`, not a stub) rules on for real:
//   FROZEN  — the seat's `after` names a dependency that never checked out. coord answers ONE row,
//             verdict BLOCKED, zero READY. Taskforce has a pending seat, nothing built/queued/live.
//             `frozen` must be non-null.
//   CONTROL — the SAME seat with NO `after` at all. coord answers ONE row, verdict READY. `frozen`
//             must be null — not because nothing is pending, but because there IS a ready seat.
//
// The RED arm proves the fixture is not vacuous: run the FROZEN case through the code AS IT STOOD
// before the fix (mutated in memory, exact anchor matched) and confirm it stays silent — the
// measured defect, reproduced on a controlled fixture rather than only on the incident replay.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const Module = require('node:module');

const HERE = __dirname;
const IGNITE_SRC = path.join(HERE, '..', '..');
const OUT_PATH = path.join(HERE, 'probe-frozen-frontier.out');
const SEEDING_PATH = path.join(HERE, '..', 'seeding.js');

const { createEngine } = require('../index');

const lines = [];
const failures = [];
function say(s) { lines.push(s); }
function check(claim, ok, detail) {
  say(`${ok ? 'ok  ' : 'FAIL'}  ${claim}${ok ? '' : ` — ${detail}`}`);
  if (!ok) failures.push(claim);
}

// A minimal, real, coord-readable goal package: one seat, optionally blocked on a dependency that
// never checks out. `hasAfter` is the ONLY variable between the two fixtures.
function fixture(hasAfter) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-frozen-frontier-'));
  const ws = path.join(root, 'ws');
  const goalFolder = path.join(ws, '.rbtv', 'goals', 'fx');
  fs.mkdirSync(path.join(goalFolder, 'seats', 'onlyseat'), { recursive: true });
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n`
    + `tf,onlyseat,${hasAfter ? 'missing-dep' : ''},bash,probe-frozen,high,35,\n`);
  fs.writeFileSync(path.join(goalFolder, 'seats', 'onlyseat', 'seat.md'),
    '---\nseat: onlyseat\nharness: bash\nmodel: probe-frozen\n---\n\nbody\n');
  return { root, ws, goalFolder };
}

// A real engine over the fixture workspace, a throwaway store, and an always-live lease — the same
// composition `probe-seed-gates.js#goalLiveArms` uses, so the D9 goal-live gate never masks the
// LE-13 result this probe is isolating.
function runFixture(hasAfter) {
  const { root, ws, goalFolder } = fixture(hasAfter);
  try {
    const yaml = require(path.join(IGNITE_SRC, 'node_modules', 'js-yaml'));
    const cfg = yaml.load(fs.readFileSync(path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml'), 'utf8'));
    cfg.spawn = { ...(cfg.spawn || {}), data_root: path.join(root, 'data'), carrier: 'setsid' };
    cfg.default_workdir_root = path.join(root, 'work');
    fs.mkdirSync(cfg.default_workdir_root, { recursive: true });
    const configPath = path.join(root, 'spawn-profiles.yaml');
    fs.writeFileSync(configPath, yaml.dump(cfg));

    const dbPath = path.join(ws, '.rbtv', 'heart', 'heart.db');
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });

    const { deriveLease } = require(path.join(IGNITE_SRC, 'server', 'lease', 'lease.js'));
    const liveLease = (a) => deriveLease({ ...a, tmuxProbe: () => ({ sessions: a.goal, panes: '' }) });

    const engine = createEngine({ dbPath, spawnConfigPath: configPath, userManager: false });
    try {
      return engine.seedGoal({ goalFolder, goal: 'fx', readLease: liveLease });
    } finally {
      engine.close();
    }
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

say('── the discriminating pair, driven through the REAL patched seedGoal ─────────────────────');
const frozenPickup = runFixture(true);
check('FROZEN fixture (coord rules the one seat BLOCKED, zero READY): `frozen` is non-null',
  Boolean(frozenPickup.frozen) && frozenPickup.frozen.kind === 'seeding-empty'
  && frozenPickup.frozen.seats.includes('onlyseat'),
  JSON.stringify(frozenPickup.frozen));
say(`  frozen: ${JSON.stringify(frozenPickup.frozen)}`);

const controlPickup = runFixture(false);
check('CONTROL fixture (coord rules the one seat READY): `frozen` is null — a ready seat is not a freeze',
  controlPickup.frozen === null,
  JSON.stringify(controlPickup.frozen));
say(`  frozen: ${JSON.stringify(controlPickup.frozen)}`);
say('');

// ── THE RED ARM — the SAME frozen fixture, driven through the PRE-FIX guard ───────────────────
say('── the red arm — the frozen fixture, through the code as it stood before the one-token fix ──');
const src = fs.readFileSync(SEEDING_PATH, 'utf8');
const ANCHOR = "const pendingUnseeded = (ready.size || moving) ? [] : seats.filter((s) => states[s] !== 'done');";
check('the mutation anchor is present — the red arm is measuring the real call site',
  src.includes(ANCHOR));
const PRE_FIX = "const pendingUnseeded = (readyRows.length || moving) ? [] : seats.filter((s) => states[s] !== 'done');";
const mut = new Module(SEEDING_PATH, null);
mut.filename = SEEDING_PATH;
mut.paths = Module._nodeModulePaths(path.dirname(SEEDING_PATH));
mut._compile(src.replace(ANCHOR, PRE_FIX), SEEDING_PATH);

function runFixtureWithSeedGoal(hasAfter, seedGoalFn) {
  const { root, ws, goalFolder } = fixture(hasAfter);
  try {
    const dbPath = path.join(ws, '.rbtv', 'heart', 'heart.db');
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    const { openHeartStore } = require('../../server/heart/heart-store');
    const heartStore = openHeartStore({ dbPath });
    try {
      return seedGoalFn({ heartStore, goalFolder, goal: 'fx' });
    } finally {
      heartStore.close();
    }
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}
// A bare store (no workspaceRoot threaded) skips the D9 goal-live gate entirely (seeding.js's own
// documented fallback: "absent ... seeding proceeds as before") — exactly what isolates the LE-13
// guard here without needing the full engine composition a second time.
const redPickup = runFixtureWithSeedGoal(true, mut.exports.seedGoal);
check('WITHOUT the fix, the SAME frozen fixture stays SILENT — the measured defect, on a controlled fixture',
  redPickup.frozen === null, JSON.stringify(redPickup.frozen));
say(`  pre-fix frozen: ${JSON.stringify(redPickup.frozen)}`);
const redControl = runFixtureWithSeedGoal(false, mut.exports.seedGoal);
check('CONTROL — the pre-fix guard still leaves a genuinely-ready fixture unfrozen (this fixture never distinguished either way)',
  redControl.frozen === null, JSON.stringify(redControl.frozen));

const verdict = failures.length ? 'FAIL' : 'PASS';
say('');
say(`SUMMARY: ${lines.filter((l) => l.startsWith('ok')).length}/${lines.filter((l) => /^(ok|FAIL)/.test(l)).length} passed`);
say(`VERDICT: ${verdict}`);
const out = lines.join('\n') + '\n';
fs.writeFileSync(OUT_PATH, out);
process.stdout.write(out);
process.exit(failures.length ? 1 : 0);
