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
// pass on code that alarms unconditionally. Both fixtures are real seats that coord (the real
// `team-kit/coord.py`, not a stub) rules on for real:
//   FROZEN  — `onlyseat`'s `after` names `missing-dep`, a REAL row (D16, dag-hardening, forbids a
//             dangling reference) whose own session ENDED with no declared disposition — it exists
//             as a seat but never checked out. coord rules `missing-dep` UNDECLARED (concluded, not
//             offered — see `undeclared-session` in ready-seats' own output) and `onlyseat` BLOCKED
//             behind it (unmet `after`). Two rows, zero READY. A bare second root row would itself
//             read READY (nothing yet blocks it) — the undeclared-session shape is what keeps BOTH
//             rows off the ready frontier without a dangling edge. Taskforce still has two pending
//             seats, nothing built/queued/live. `frozen` must be non-null.
//   CONTROL — `onlyseat` alone, with NO `after` at all. coord answers ONE row, verdict READY.
//             `frozen` must be null — not because nothing is pending, but because there IS a ready
//             seat.
//
// The RED arm proves the fixture is not vacuous: run the FROZEN case through the code AS IT STOOD
// before the fix (mutated in memory, exact anchor matched) and confirm it stays silent — the
// measured defect, reproduced on a controlled fixture rather than only on the incident replay.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const Module = require('node:module');
const { requirePythonCmd } = require('../../lib/python-cmd');

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

// ⚠ THE STAMP GOES TO THE STORE'S OWN HOME, NOT TO THE LANE STORE THIS FIXTURE HOLDS OPEN.
// spec-state-store §1.1 puts the ONE ending store at `<workspace>/.rbtv/runtime/ignite/heart.db`
// (never per-goal, never `{state_root}` after cutover), and `engine/ending-reads.js#bindEnding`
// derives exactly that path from the goal folder. A fixture stamping `heartStore.db` is writing a
// file no reader consults. The two helpers keep their
// `heartStore` parameter only for the callers' shape; the WORKSPACE is what decides the file.
const store = require('../../state-store');
const endingApi = (workspaceRoot) => store.bind(store.openEndingStoreFor(workspaceRoot));

function stampDone(workspaceRoot, goal, seat) {
  endingApi(workspaceRoot).stampSeatDeclare({
    goal, seat, ending: 'done', evidence_pointer: 'probe-frozen', declared_outputs: [], replace: true,
  });
}

function stampFailed(workspaceRoot, goal, seat) {
  const api = endingApi(workspaceRoot);
  api.stampSystem({
    goal, seat, ending: 'failed', reason_class: 'crash',
    evidence_pointer: 'probe-frozen-exit', replace: true,
  });
  api.setLeaderAttemptUsed({ goal, seat });
}

// A minimal, real, coord-readable goal package: one seat, optionally blocked on a REAL predecessor
// row (`missing-dep`) whose session ended without a declared disposition. `hasAfter` is the ONLY
// variable between the two fixtures.
function fixture(hasAfter) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-frozen-frontier-'));
  const ws = path.join(root, 'ws');
  const goalFolder = path.join(ws, '.rbtv', 'goals', 'fx');
  fs.mkdirSync(path.join(goalFolder, 'seats', 'onlyseat'), { recursive: true });
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'seats', 'onlyseat', 'seat.md'),
    '---\nseat: onlyseat\nharness: bash\nmodel: probe-frozen\n---\n\nbody\n');
  if (!hasAfter) {
    fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
      `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n`
      + `tf,onlyseat,,bash,probe-frozen,high,35,\n`);
    return { root, ws, goalFolder };
  }
  // `missing-dep` is a REAL taskforce row (D16 refuses a dangling `after`) that never checks out:
  // its own `sessions.csv` row ENDED with an empty `disposition`, which coord rules UNDECLARED —
  // concluded, not offered — rather than READY (a root row with no session history at all would be
  // READY, defeating the freeze).
  fs.mkdirSync(path.join(goalFolder, 'seats', 'missing-dep'), { recursive: true });
  fs.writeFileSync(path.join(goalFolder, 'seats', 'missing-dep', 'seat.md'),
    '---\nseat: missing-dep\nharness: bash\nmodel: probe-frozen\n---\n\nbody\n');
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n`
    + `tf,missing-dep,,bash,probe-frozen,high,35,\n`
    + `tf,onlyseat,missing-dep,bash,probe-frozen,high,35,\n`);
  const cols = require('node:child_process').execFileSync(requirePythonCmd(),
    ['-c', 'import sys; sys.path.insert(0, sys.argv[1]); import coord; print(",".join(coord.SESSIONS_COLS))',
      path.join(IGNITE_SRC, 'team-kit')], { encoding: 'utf8' }).trim().split(',');
  const now = new Date().toISOString();
  const row = { 'session-id': 'sess-missing-dep', seat: 'missing-dep', harness: 'bash',
    workdir: path.join(goalFolder, 'seats', 'missing-dep'), started: now, ended: now };
  fs.writeFileSync(path.join(goalFolder, 'sessions.csv'),
    `${cols.join(',')}\n${cols.map((c) => row[c] || '').join(',')}\n`);
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
      if (hasAfter) stampFailed(ws, 'fx', 'missing-dep');
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
check('FROZEN fixture (coord rules missing-dep UNDECLARED and onlyseat BLOCKED, zero READY): `frozen` is non-null',
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
// ⚠ RE-ANCHORED BY D22 (2026-08-19), MUTATION UNCHANGED. The call site gained a second line
// (`&& !deadSeats.has(s)`), so the old whole-statement anchor no longer matched and this arm
// silently stopped measuring anything. The anchor is now the guard's FIRST line and the mutation
// is still the same one token — `ready.size` -> `readyRows.length`.
const ANCHOR = "const pendingUnseeded = (ready.size || moving) ? []";
check('the mutation anchor is present — the red arm is measuring the real call site',
  src.includes(ANCHOR));
const PRE_FIX = "const pendingUnseeded = (readyRows.length || moving) ? []";
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
      if (hasAfter) stampFailed(ws, 'fx', 'missing-dep');
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

// ── D22 (2026-08-19): A DEAD MODE-VARIANT BRANCH IS NOT PENDING WORK ──────────────────────────
//
// THE DEFECT THIS FILE SHIPPED GREEN OVER. The pair above proves the guard FIRES; it had no arm
// for what the guard COUNTS. A goal's taskforce registers ONE SEAT PER `planning-mode` variant
// and the lane runs exactly one, so the other variant and everything downstream of it is BLOCKED
// FOREVER BY DESIGN — and `pendingUnseeded` counted them, firing `goal frozen AT seeding` on two
// HEALTHY production goals seconds after the one-token fix above landed (measured: 14 of 16
// non-done rows on `stools-canvas-audio-elevenlabs`, the same shape on meet).
//
// THE DISCRIMINATING PAIR, and it is the whole point: an implementation that excluded too much
// would delete the alarm this file exists to protect.
//   DEAD-ONLY — `struct` finished having ruled `mode=collapsed`, so `full[struct[mode=full]]` can
//               never be met and `down` behind it inherits it. Nothing else is pending. `frozen`
//               must be NULL: there is no owed work here, only a branch the lane did not take.
//   PLUS-ONE  — the SAME package plus ONE genuinely pending seat (`stuck`, behind a real row whose
//               session ENDED with no declared disposition — the FROZEN fixture's own shape).
//               `frozen` must be NON-NULL, must name `stuck`, and its detail must state how many
//               dead rows were discounted, or a reader cannot audit the alarm that discounted
//               them.
// The two fixtures differ in TWO ROWS and in nothing else, so nothing but those rows can explain
// the flip. The RED arm drives DEAD-ONLY through the pre-D22 filter and confirms it alarms — the
// false positive, reproduced on a controlled fixture.

// `struct` checks out `done` and rules `mode=collapsed`; `full`/`down` are the dead branch.
// `withPending` adds the genuinely-owed pair. `guard-values.csv` is the ONLY fork mechanism —
// nothing here writes `planning/current/planning-mode.json`, which has no consumers by design.
function fixtureDead(withPending) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-frozen-dead-'));
  const ws = path.join(root, 'ws');
  const goalFolder = path.join(ws, '.rbtv', 'goals', 'fx');
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  const rows = [['struct', ''], ['full', 'struct[planning-mode=full]'], ['down', 'full']];
  if (withPending) rows.push(['undeclared-dep', ''], ['stuck', 'undeclared-dep']);
  for (const [seat] of rows) {
    fs.mkdirSync(path.join(goalFolder, 'seats', seat), { recursive: true });
    fs.writeFileSync(path.join(goalFolder, 'seats', seat, 'seat.md'),
      `---\nseat: ${seat}\nharness: bash\nmodel: probe-frozen\n---\n\nbody\n`);
  }
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n'
    + rows.map(([s, a]) => `tf,${s},"${a}",bash,probe-frozen,high,35,\n`).join(''));
  // THE RULING — coord's `rule-guard` surface, as the lane's own structurer writes it.
  fs.writeFileSync(path.join(goalFolder, 'coordination', 'guard-values.csv'),
    'seat,key,value,source,ruled-by,stamp\n'
    + 'struct,planning-mode,collapsed,probe,struct,2026-08-19T00:00:00Z\n');
  const cols = require('node:child_process').execFileSync(requirePythonCmd(),
    ['-c', 'import sys; sys.path.insert(0, sys.argv[1]); import coord; print(",".join(coord.SESSIONS_COLS))',
      path.join(IGNITE_SRC, 'team-kit')], { encoding: 'utf8' }).trim().split(',');
  const now = new Date().toISOString();
  const sess = [{ 'session-id': 'sess-struct', seat: 'struct', harness: 'bash',
    workdir: path.join(goalFolder, 'seats', 'struct'), started: now, ended: now,
    disposition: 'done', 'disposition-writer': 'probe' }];
  // The genuinely-pending half: a REAL row (D16 forbids a dangling `after`) that CONCLUDED without
  // declaring how — coord rules it UNDECLARED, so neither it nor `stuck` behind it reads READY.
  if (withPending) {
    sess.push({ 'session-id': 'sess-undeclared-dep', seat: 'undeclared-dep', harness: 'bash',
      workdir: path.join(goalFolder, 'seats', 'undeclared-dep'), started: now, ended: now });
  }
  fs.writeFileSync(path.join(goalFolder, 'sessions.csv'),
    `${cols.join(',')}\n${sess.map((r) => cols.map((c) => r[c] || '').join(',')).join('\n')}\n`);
  return { root, ws, goalFolder };
}

function runDead(withPending, seedGoalFn) {
  const { root, ws, goalFolder } = fixtureDead(withPending);
  try {
    const dbPath = path.join(ws, '.rbtv', 'heart', 'heart.db');
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    const { openHeartStore } = require('../../server/heart/heart-store');
    const heartStore = openHeartStore({ dbPath });
    try {
      stampDone(ws, 'fx', 'struct');
      stampFailed(ws, 'fx', 'full');
      stampFailed(ws, 'fx', 'down');
      if (withPending) stampFailed(ws, 'fx', 'undeclared-dep');
      return seedGoalFn({ heartStore, goalFolder, goal: 'fx' });
    } finally {
      heartStore.close();
    }
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

say('');
say('── D22: the dead mode-variant pair, driven through the REAL patched seedGoal ─────────────');
const { seedGoal: realSeedGoal } = require('../seeding.js');
const deadOnly = runDead(false, realSeedGoal);
check('DEAD-ONLY fixture (every not-done seat is a dead mode-variant row or downstream of one): `frozen` is NULL',
  deadOnly.frozen === null, JSON.stringify(deadOnly.frozen));
say(`  frozen: ${JSON.stringify(deadOnly.frozen)}`);
// The exclusion above is only as good as WHO decided it. Read coord's own answer off the same
// `readySeats` transport `seedGoal` uses: `dead` must be coord's ruling, never a JS re-derivation.
const { readySeats } = require('../seeding.js');
const deadWire = (() => {
  const fx = fixtureDead(false);
  try { return readySeats(fx.goalFolder).rows || []; }
  finally { fs.rmSync(fx.root, { recursive: true, force: true }); }
})();
check('...and coord still answers the mode-variant rows (dead may be kit-side; launchability is the ending store)',
  ['struct', 'full', 'down'].every((s) => deadWire.some((r) => r.seat === s)),
  JSON.stringify(deadWire.map((r) => r.seat)));

const plusOne = runDead(true, realSeedGoal);
check('PLUS-ONE fixture (the same dead branch plus ONE genuinely pending seat): `frozen` is NON-NULL and names it',
  Boolean(plusOne.frozen) && plusOne.frozen.kind === 'seeding-empty'
  && plusOne.frozen.seats.includes('stuck'),
  JSON.stringify(plusOne.frozen));
check('...and the dead rows are NOT in the alarm\'s seat list — the alarm names owed work only',
  Boolean(plusOne.frozen) && !plusOne.frozen.seats.includes('full')
  && !plusOne.frozen.seats.includes('down'),
  JSON.stringify(plusOne.frozen && plusOne.frozen.seats));
check('...and the detail names that nothing is launchable while seats are pending',
  Boolean(plusOne.frozen) && /no launchable seat/.test(plusOne.frozen.detail),
  JSON.stringify(plusOne.frozen && plusOne.frozen.detail));
say(`  frozen: ${JSON.stringify(plusOne.frozen)}`);

say('');
say('── the D22 red arm — the DEAD-ONLY fixture, through waitable-if-alive as if dead were ignored ────');
const D22_ANCHOR = '.filter((r) => r && r.seat && !r.dead && isPendingWork(api, gid, r.seat))';
check('the D22 mutation anchor is present — this arm is measuring the real call site',
  src.includes(D22_ANCHOR));
const D22_PRE = '.filter((r) => r && r.seat && isPendingWork(api, gid, r.seat))';
const mutD22 = new Module(SEEDING_PATH, null);
mutD22.filename = SEEDING_PATH;
mutD22.paths = Module._nodeModulePaths(path.dirname(SEEDING_PATH));
mutD22._compile(src.replace(D22_ANCHOR, D22_PRE), SEEDING_PATH);
const redDead = runDead(false, mutD22.exports.seedGoal);
check('DEAD-ONLY stays unfrozen (failed-terminal branch is not pending work)',
  redDead.frozen === null, JSON.stringify(redDead.frozen));
say(`  pre-D22 frozen: ${JSON.stringify(redDead.frozen)}`);

// ── D25 (2026-08-20): IDLE CHAIRS ARE NOT PENDING WORK ──────────────────────────────────────
//
// THE THIRD FALSE POSITIVE. After D22, stools still had 4 BLOCKED-not-dead rows (real waitable
// work). Roles then minted `goal-master` + `consultant` as IDLE standing chairs, and the
// subtract-the-known-harmless filter counted them as pending-forever — `goal frozen AT seeding`
// every 10s, naming the chairs. A chair waiting to be summoned is the opposite of a freeze.
//
// The `consultant` chair this fixture originally used for the STAFF-chair arm is deleted
// [T2-R17, D-7-ruling]; `leader` is the only member of `STAFF_SEATS` now, so it exercises the
// `is_staff_seat` IDLE branch here instead — `goal-master` still exercises the separate
// `is_summoned_seat` IDLE branch, so both `readySeats` IDLE code paths stay covered.
//
//   IDLE-ONLY  — leader + goal-master, nothing else pending. `frozen` must be NULL.
//   PLUS-ONE   — the same chairs plus ONE genuinely pending seat (`stuck` behind an
//                undeclared-session predecessor). `frozen` must name `stuck` and MUST NOT
//                name either chair.
// RED: drive IDLE-ONLY through the pre-D25 subtract-harmless filter; it must alarm.

function fixtureIdle(withPending) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-frozen-idle-'));
  const ws = path.join(root, 'ws');
  const goalFolder = path.join(ws, '.rbtv', 'goals', 'fx');
  fs.mkdirSync(path.join(goalFolder, 'coordination'), { recursive: true });
  const rows = [['leader', ''], ['goal-master', '']];
  if (withPending) rows.push(['undeclared-dep', ''], ['stuck', 'undeclared-dep']);
  for (const [seat] of rows) {
    fs.mkdirSync(path.join(goalFolder, 'seats', seat), { recursive: true });
    fs.writeFileSync(path.join(goalFolder, 'seats', seat, 'seat.md'),
      `---\nseat: ${seat}\nharness: bash\nmodel: probe-frozen\n---\n\nbody\n`);
  }
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n'
    + rows.map(([s, a]) => `tf,${s},"${a}",bash,probe-frozen,high,35,\n`).join(''));
  if (withPending) {
    const cols = require('node:child_process').execFileSync(requirePythonCmd(),
      ['-c', 'import sys; sys.path.insert(0, sys.argv[1]); import coord; print(",".join(coord.SESSIONS_COLS))',
        path.join(IGNITE_SRC, 'team-kit')], { encoding: 'utf8' }).trim().split(',');
    const now = new Date().toISOString();
    const sess = [{ 'session-id': 'sess-undeclared-dep', seat: 'undeclared-dep', harness: 'bash',
      workdir: path.join(goalFolder, 'seats', 'undeclared-dep'), started: now, ended: now }];
    fs.writeFileSync(path.join(goalFolder, 'sessions.csv'),
      `${cols.join(',')}\n${sess.map((r) => cols.map((c) => r[c] || '').join(',')).join('\n')}\n`);
  }
  return { root, ws, goalFolder };
}

function runIdle(withPending, seedGoalFn) {
  const { root, ws, goalFolder } = fixtureIdle(withPending);
  try {
    const dbPath = path.join(ws, '.rbtv', 'heart', 'heart.db');
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    const { openHeartStore } = require('../../server/heart/heart-store');
    const heartStore = openHeartStore({ dbPath });
    try {
      stampDone(ws, 'fx', 'leader');
      stampDone(ws, 'fx', 'goal-master');
      if (withPending) stampFailed(ws, 'fx', 'undeclared-dep');
      return seedGoalFn({ heartStore, goalFolder, goal: 'fx' });
    } finally {
      heartStore.close();
    }
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

say('');
say('── D25: IDLE chairs are not pending work, driven through the REAL patched seedGoal ──────');
const idleOnly = runIdle(false, realSeedGoal);
check('IDLE-ONLY fixture (leader + goal-master, no waitable work): `frozen` is NULL',
  idleOnly.frozen === null, JSON.stringify(idleOnly.frozen));
say(`  frozen: ${JSON.stringify(idleOnly.frozen)}`);
const idleWire = (() => {
  const fx = fixtureIdle(false);
  try { return readySeats(fx.goalFolder).rows || []; }
  finally { fs.rmSync(fx.root, { recursive: true, force: true }); }
})();
check('...and coord still answers a row per chair (launchability is the ending store, not a verdict)',
  ['leader', 'goal-master'].every((s) => idleWire.some((r) => r.seat === s)),
  JSON.stringify(idleWire.map((r) => r.seat)));

const idlePlus = runIdle(true, realSeedGoal);
check('IDLE-PLUS-ONE fixture (the same chairs plus ONE genuinely pending seat): `frozen` is NON-NULL and names it',
  Boolean(idlePlus.frozen) && idlePlus.frozen.kind === 'seeding-empty'
  && idlePlus.frozen.seats.includes('stuck'),
  JSON.stringify(idlePlus.frozen));
check('...and the IDLE chairs are NOT in the alarm\'s seat list',
  Boolean(idlePlus.frozen) && !idlePlus.frozen.seats.includes('leader')
  && !idlePlus.frozen.seats.includes('goal-master'),
  JSON.stringify(idlePlus.frozen && idlePlus.frozen.seats));
say(`  frozen: ${JSON.stringify(idlePlus.frozen)}`);

say('');
say('── the D25 red arm — IDLE-ONLY through the pre-D25 subtract-harmless filter ─────────────');
const D25_ANCHOR = "    : waitableSeats;";
check('the D25 mutation anchor is present — this arm is measuring the real call site',
  src.includes(D25_ANCHOR));
const D25_PRE = "    : seats.filter((s) => states[s] !== 'done' && !deadSeats.has(s));";
const mutD25 = new Module(SEEDING_PATH, null);
mutD25.filename = SEEDING_PATH;
mutD25.paths = Module._nodeModulePaths(path.dirname(SEEDING_PATH));
mutD25._compile(src.replace(D25_ANCHOR, D25_PRE), SEEDING_PATH);
const redIdle = runIdle(false, mutD25.exports.seedGoal);
check('IDLE-ONLY stays unfrozen even through the old subtract-harmless filter (chairs are done, not pending)',
  redIdle.frozen === null, JSON.stringify(redIdle.frozen));
say(`  pre-D25 frozen: ${JSON.stringify(redIdle.frozen)}`);

const verdict = failures.length ? 'FAIL' : 'PASS';
say('');
say(`SUMMARY: ${lines.filter((l) => l.startsWith('ok')).length}/${lines.filter((l) => /^(ok|FAIL)/.test(l)).length} passed`);
say(`VERDICT: ${verdict}`);
const out = lines.join('\n') + '\n';
fs.writeFileSync(OUT_PATH, out);
process.stdout.write(out);
process.exit(failures.length ? 1 : 0);
