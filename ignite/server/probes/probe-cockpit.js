'use strict';

// probe-cockpit — task 7.36's boot cockpit (settle ledger R6/R15), exercised in two layers.
//
// LAYER 1 (pure, no tmux server needed): the composition — the naming guard, the goal-room
// collision refusal, the lazy master pane's ABSENCE of a command, the explicit --package, and the
// run-folder ranking.
//
// LAYER 2 (live, under a THROWAWAY session name): the cockpit is really created; the master pane
// really holds NO harness process, read from /proc; teamview is really running; the identity
// marker is really set; a second call is really idempotent.
//
// ⚠ IT NEVER TOUCHES A GOAL ROOM. Every tmux command carries an explicit `-t` (run bar G-172: on
// this box a bare tmux command resolves against the CLIENT's pane, which is the owner's parked
// door). The throwaway session name is unique per run, and the probe asserts the live session
// inventory is byte-identical before and after — so "I cleaned up" is measured, not promised.
//
// ⚠ THE HARNESS DETECTOR IS PROVEN ABLE TO FAIL. The criterion demands the no-harness fact be
// "proven by process listing, not by the launch config", and a detector that only ever sees clean
// panes proves nothing about itself (p-green-harness-over-a-broken-mechanism). So the probe spawns
// a CONTROL pane running a process named `claude` and asserts the SAME detector flags it. A pass
// on the master pane means something only because the control fails.
//
// Capture truncated at module load, BEFORE any work (D51 evidence-husk hazard). The process exit
// code is the truth; the footer is a hint. The check DENOMINATOR is declared before the first
// check runs, and the run asserts it reached that total — a truncated run reads greener than a
// complete one (G-121), so completeness is asserted rather than assumed.

require('../../deploy/probe-self-isolate').selfIsolateTmux(); // solo-run tmux isolation (task 7.630) — no-op under the runner
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cockpit.out');
fs.writeFileSync(outPath, '');

const {
  COCKPIT_SESSION, COCKPIT_MARKER,
  E_COCKPIT_NAME_COLLISION, E_COCKPIT_TEAMVIEW_UNRESOLVED,
  resolveCockpitPackage, composeCockpitSpawn, ensureCockpit,
} = require('../cockpit');

// Declared BEFORE anything runs. A run that ends with a different tally is INCOMPLETE, whatever
// its failures say.
//
// 38 = 12 (layer 1) + 13 (layer 1b) + 13 (layer 2). The live layer's skip branch emits exactly 13
// too, so a tmux-less box reaches the same denominator rather than silently shrinking it.
// (7.607 E3: layer 1b went 10 -> 13 — the three run-folder RANKING arms were replaced by six
// LEASE-ranking arms, and the count moving is how this assertion reported the change.)
//
// ⚠ THIS NUMBER WAS WRONG ON THE FIRST RUN (declared 24, ran 34) AND THE ASSERTION IS WHAT SAID
// SO: every check passed and the probe still exited 1. Recorded because it is the argument for
// the assertion existing — a probe that only counted its failures would have reported a clean
// green over an author who had lost track of his own coverage.
const EXPECTED_CHECKS = 38;

const checks = [];
let skipped = 0;
function out(...args) {
  const line = args.join(' ');
  fs.appendFileSync(outPath, line + '\n');
  console.log(line);
}
function check(name, pass, detail = '') {
  checks.push({ name, pass: Boolean(pass) });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`);
}
function skip(name, why) {
  skipped += 1;
  checks.push({ name, pass: true });
  out(`SKIP  ${name}  — ${why}`);
}

const UNIQUE = `${process.pid}-${Date.now()}`;
const THROWAWAY = `rbtv-cockpitprobe-${UNIQUE}`;
const HARNESS_NAMES = new Set(['claude', 'codex', 'opencode', 'kimi']);

function tmux(args, { allowFail = false } = {}) {
  try {
    return execFileSync('tmux', args, { encoding: 'utf8', timeout: 10000 }).trim();
  } catch (err) {
    if (allowFail) return null;
    throw err;
  }
}

function tmuxAvailable() {
  try {
    execFileSync('tmux', ['-V'], { encoding: 'utf8', timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

function sessionNames() {
  const outp = tmux(['list-sessions', '-F', '#{session_name}'], { allowFail: true });
  return outp ? outp.split('\n').map((s) => s.trim()).filter(Boolean).sort() : [];
}

// ── the harness detector ───────────────────────────────────────────────────────────────────────
//
// Walks the pane's process TREE from /proc and returns every harness-looking comm it finds. It
// reads the RUNNING PROCESSES, never a config, a profile, or the argv we composed — which is the
// whole point of the criterion.
function procChildren(pid) {
  try {
    const kids = fs.readFileSync(`/proc/${pid}/task/${pid}/children`, 'utf8');
    return kids.split(/\s+/).filter(Boolean).map(Number);
  } catch {
    return [];
  }
}
function procComm(pid) {
  try {
    return fs.readFileSync(`/proc/${pid}/comm`, 'utf8').trim();
  } catch {
    return null;
  }
}
function harnessesInTree(rootPid) {
  const found = [];
  const seen = new Set();
  const stack = [Number(rootPid)];
  while (stack.length) {
    const pid = stack.pop();
    if (!pid || seen.has(pid)) continue;
    seen.add(pid);
    const comm = procComm(pid);
    if (comm && HARNESS_NAMES.has(comm)) found.push({ pid, comm });
    stack.push(...procChildren(pid));
  }
  return found;
}

// ── layer 1: the composition, pure ─────────────────────────────────────────────────────────────
function layerCompose() {
  out('── LAYER 1: composition (no tmux server involved) ──');

  const composed = composeCockpitSpawn({
    sessionName: 'rbtv-cockpit',
    masterDir: '/tmp/master-here',
    teamviewArgv: ['teamview'],
    packageDir: '/tmp/.rbtv/goals/some-goal',
  });

  // THE LAZY PANE. `new-session` must carry NO command — the absence IS the feature. If a command
  // ever appears after the flags, the master pane stops being lazy and this check catches it.
  const ns = composed.newSessionArgv;
  check('master pane is LAZY: new-session argv carries no command and no `--`',
    !ns.includes('--') && ns[ns.length - 2] === '-F',
    `argv=${JSON.stringify(ns)}`);
  check('master pane opens at the requested cwd',
    ns[ns.indexOf('-c') + 1] === '/tmp/master-here');
  check('session is created detached (-d), never stealing an attached client',
    ns.includes('-d'));

  // THE EXPLICIT --package (leader ruling 2026-07-27 ~23:25). Without it teamview exits 2 from a
  // cockpit and the pane dies.
  const tvIdx = composed.splitArgv.indexOf('--');
  const tvCmd = composed.splitArgv.slice(tvIdx + 1);
  check('teamview is invoked with an EXPLICIT --package',
    tvCmd.includes('--package') && tvCmd[tvCmd.indexOf('--package') + 1] === '/tmp/.rbtv/goals/some-goal',
    `cmd=${JSON.stringify(tvCmd)}`);
  check('teamview pane command is passed as a VECTOR after `--` (no shell parses it)',
    tvIdx > 0 && tvCmd.length >= 3);
  check('teamview pane is added detached so the MASTER pane stays active for the owner',
    composed.splitArgv.includes('-d'));
  check('teamview split targets the cockpit window EXPLICITLY (-t), never a default target',
    composed.splitArgv[composed.splitArgv.indexOf('-t') + 1] === 'rbtv-cockpit:cockpit');

  // The identity marker.
  check('the session is stamped with the machine-readable identity marker',
    composed.markArgv.includes(COCKPIT_MARKER) && composed.markArgv.includes('-t'));

  // No --package resolvable: the flag must be OMITTED, not passed empty (an empty --package would
  // make teamview refuse and the pane die).
  const noPkg = composeCockpitSpawn({
    masterDir: '/tmp/m', teamviewArgv: ['teamview'], packageDir: null,
  });
  check('with no run folder resolvable, --package is OMITTED rather than passed empty',
    !noPkg.splitArgv.includes('--package'));

  // THE NAMING GUARD, through spawn/tmux.js's own assertTmuxName.
  let guarded = false;
  try {
    composeCockpitSpawn({ sessionName: 'rbtv:cockpit', masterDir: '/tmp/m', teamviewArgv: ['teamview'] });
  } catch (err) {
    guarded = /separator/.test(err.message);
  }
  check('a session name carrying a tmux target separator is REFUSED', guarded);

  check('the reserved cockpit name itself passes the guard and is distinctly prefixed',
    COCKPIT_SESSION === 'rbtv-cockpit' && !/[:.\s]/.test(COCKPIT_SESSION));

  // teamview unresolved -> a typed refusal, never a pane launched with an empty command.
  let typed = null;
  try {
    composeCockpitSpawn({ masterDir: '/tmp/m', teamviewArgv: [] });
  } catch (err) { typed = err.code; }
  check('an unresolvable teamview produces a TYPED refusal, not an empty pane command',
    typed === E_COCKPIT_TEAMVIEW_UNRESOLVED, `code=${typed}`);
}

// ── layer 1b: the collision refusal and the package ranking ────────────────────────────────────
function layerPolicy() {
  out('');
  out('── LAYER 1b: goal-room collision + LEASE-ranked package resolution ──');

  // THE DISTINCTNESS CRITERION, enforced. ensureCockpit is fail-soft, so the refusal surfaces as a
  // NAMED reason rather than a throw — and the check asserts the NAME, because "did not spawn" is
  // also satisfied by a cockpit that failed for an unrelated reason.
  const calls = [];
  const res = ensureCockpit({
    workspaceRoot: '/tmp/ws',
    installed: true,
    goalRoom: 'rbtv-cockpit',
    sessionName: 'rbtv-cockpit',
    env: { PATH: '' , RBTV_IGNITE_COCKPIT_TEAMVIEW: '/bin/true' },
    runTmux: (argv) => { calls.push(argv); return ''; },
    logger: () => {},
  });
  check('a goal room sharing the cockpit name REFUSES the spawn with a named code',
    res.spawned === false && res.reason === E_COCKPIT_NAME_COLLISION, `reason=${res.reason}`);
  check('the refused collision executed NO tmux command at all', calls.length === 0,
    `calls=${calls.length}`);

  // The off switch.
  const offCalls = [];
  const off = ensureCockpit({
    workspaceRoot: '/tmp/ws', env: { RBTV_IGNITE_COCKPIT: 'off' },
    runTmux: (argv) => { offCalls.push(argv); return ''; }, logger: () => {},
  });
  check('RBTV_IGNITE_COCKPIT=off disables the cockpit and runs no tmux command',
    off.spawned === false && off.reason === 'disabled' && offCalls.length === 0);

  // ⚠ THE INSTALLED GATE — added because the feature LEAKED. A cockpit outlives its daemon by
  // design, so without this every throwaway probe daemon left a persistent session on the box
  // (measured: a probe-suite run stranded an `rbtv-cockpit`). The check asserts the NAMED reason,
  // because "did not spawn" is also satisfied by a cockpit that failed for an unrelated cause.
  const uninstCalls = [];
  const uninst = ensureCockpit({
    workspaceRoot: '/tmp/ws', installed: false,
    env: { PATH: '', RBTV_IGNITE_COCKPIT_TEAMVIEW: '/bin/true' },
    runTmux: (argv) => { uninstCalls.push(argv); return ''; }, logger: () => {},
  });
  check('an UNINSTALLED workspace spawns no cockpit, by name, and runs no tmux command',
    uninst.spawned === false && uninst.reason === 'workspace-not-installed' && uninstCalls.length === 0,
    `reason=${uninst.reason} calls=${uninstCalls.length}`);

  // FAIL-SOFT: a tmux that refuses everything must not throw out of ensureCockpit.
  let threw = false;
  let soft;
  try {
    soft = ensureCockpit({
      workspaceRoot: '/tmp/ws',
      installed: true,
      env: { PATH: '', RBTV_IGNITE_COCKPIT_TEAMVIEW: '/bin/true' },
      runTmux: () => { throw new Error('tmux: no server'); },
      logger: () => {},
    });
  } catch { threw = true; }
  check('a failing tmux is reported and swallowed — ensureCockpit NEVER throws at the daemon',
    !threw && soft && soft.spawned === false && Boolean(soft.error), `reason=${soft && soft.reason}`);

  // ── 7.607 E3 — WHICH GOAL THE COCKPIT RENDERS, on fabricated trees under tmpdir ──────────────
  //
  // The run-folder ranking arms are GONE with their subject (`runs/run-N` and the register). What
  // replaces them is the three-rung order in `resolveCockpitPackage`: override > LIVE LEASE >
  // most-recent snapshot. `readLease` is injected, so the lease arms measure the RANKING and never
  // tmux — the lease's own derivation has its own probe.
  const ws = fs.mkdtempSync(path.join(os.tmpdir(), 'cockpit-pkg-'));
  const mk = (goal, snapshot, ageMs) => {
    const p = path.join(ws, '.rbtv', 'goals', goal);
    fs.mkdirSync(p, { recursive: true });
    if (snapshot) {
      const f = path.join(p, 'state.json');
      fs.writeFileSync(f, '{}');
      const t = new Date(Date.now() - ageMs);
      fs.utimesSync(f, t, t);
    }
    return p;
  };
  const stale = mk('goal-a', true, 60_000);
  const newest = mk('goal-b', true, 1_000);
  mk('goal-c', false, 0);

  // A lease reader that says "executing" for exactly the named goals, and answers a readable
  // "not executing" for every other — the shape `deriveLease` returns.
  const leaseOf = (...liveGoals) => ({ workspaceRoot, goal }) => {
    const goalDir = path.join(workspaceRoot, '.rbtv', 'goals', goal);
    const live = liveGoals.includes(goal);
    return { ok: true, live, goal, goalDir, seats: [], evidence: {},
             rooms: live ? [{ room: goal, packageDir: goalDir, panePids: [], seats: [] }] : [] };
  };

  // RUNG 3 first, so the LEASE arm below is attributable: with NOTHING executing, the newest
  // snapshot wins — and that is a DIFFERENT goal from the one the lease arm picks, which is what
  // makes the lease arm's result evidence rather than a coincidence.
  check('nothing executing: the most recent SNAPSHOT is rendered (the goal that just finished)',
    resolveCockpitPackage(ws, { env: {} , readLease: leaseOf() }) === newest,
    `picked=${resolveCockpitPackage(ws, { env: {}, readLease: leaseOf() })}`);

  check('⚠ THE LIVE LEASE OUTRANKS THE SNAPSHOT: the EXECUTING goal is rendered even though its '
    + 'snapshot is 60s older than another goal\'s — "which workspace is live" is asked of the '
    + 'lease, never of an mtime (design-lock item 1, inventory #12)',
    resolveCockpitPackage(ws, { env: {}, readLease: leaseOf('goal-a') }) === stale,
    `picked=${resolveCockpitPackage(ws, { env: {}, readLease: leaseOf('goal-a') })}, stale=${stale}`);

  check('a goal with NO snapshot at all still wins when it holds the lease — the lease is '
    + 'evidence of execution and a snapshot is not',
    resolveCockpitPackage(ws, { env: {}, readLease: leaseOf('goal-c') })
      === path.join(ws, '.rbtv', 'goals', 'goal-c'));

  check('two live leases (which the design forbids): the FIRST BY NAME is taken deterministically '
    + '— a view that refuses to render is worse than one rendering a checkable choice',
    resolveCockpitPackage(ws, { env: {}, readLease: leaseOf('goal-b', 'goal-a') }) === stale);

  check('an UNREADABLE lease falls through to the snapshot rather than blanking the view — the '
    + 'posture on ignorance for a VIEW is to show the last thing known',
    resolveCockpitPackage(ws, { env: {}, readLease: () => ({ ok: false, reason: 'tmux unreadable' }) })
      === newest);

  // A goal WITH a snapshot outranks a bare folder, whatever the mtimes say.
  const ws3 = fs.mkdtempSync(path.join(os.tmpdir(), 'cockpit-pkg3-'));
  const withSnap = path.join(ws3, '.rbtv', 'goals', 'g-snap');
  fs.mkdirSync(withSnap, { recursive: true });
  const sf = path.join(withSnap, 'state.json');
  fs.writeFileSync(sf, '{}');
  const old = new Date(Date.now() - 600_000);
  fs.utimesSync(sf, old, old);
  const bare = path.join(ws3, '.rbtv', 'goals', 'g-bare');
  fs.mkdirSync(bare, { recursive: true });
  check('a goal WITH a snapshot outranks a freshly-touched folder without one',
    resolveCockpitPackage(ws3, { env: {}, readLease: leaseOf() }) === withSnap);

  check('the env override pins the package and short-circuits resolution — the lease is never asked',
    resolveCockpitPackage(ws, { env: { RBTV_IGNITE_COCKPIT_PACKAGE: '/pinned/goal-x' },
      readLease: () => { throw new Error('the override must short-circuit before any lease read'); } })
      === '/pinned/goal-x');

  check('a workspace with no goals resolves to null rather than guessing',
    resolveCockpitPackage(fs.mkdtempSync(path.join(os.tmpdir(), 'cockpit-empty-')),
      { env: {}, readLease: leaseOf() }) === null);

  for (const d of [ws, ws3]) { try { fs.rmSync(d, { recursive: true, force: true }); } catch { /* tmp */ } }
}

// ── layer 2: live, under a throwaway session ───────────────────────────────────────────────────
function layerLive(before) {
  out('');
  out('── LAYER 2: live cockpit under a throwaway session ──');

  const ws = fs.mkdtempSync(path.join(os.tmpdir(), 'cockpit-live-'));
  const pkg = path.join(ws, '.rbtv', 'goals', 'g', 'runs', 'run-1');
  fs.mkdirSync(pkg, { recursive: true });
  fs.writeFileSync(path.join(pkg, 'state.json'), '{}');

  // A stand-in teamview: a long-running process, so the pane behaves like the real dashboard
  // without this probe depending on teamview's own resolution. The REAL teamview's survival with
  // an explicit --package is proven separately (see the module header's measured note).
  const fakeTv = path.join(ws, 'teamview-standin');
  fs.writeFileSync(fakeTv, '#!/bin/sh\nwhile :; do sleep 5; done\n', { mode: 0o755 });

  try {
    const res = ensureCockpit({
      workspaceRoot: ws,
      installed: true,
      sessionName: THROWAWAY,
      env: { RBTV_IGNITE_COCKPIT_TEAMVIEW: fakeTv, PATH: process.env.PATH },
      logger: () => {},
    });
    check('the cockpit session is really created', res.spawned === true, `reason=${res.reason || ''}`);
    check('the cockpit exists under its EXACT name', sessionNames().includes(THROWAWAY));

    // THE IDENTITY MARKER, read back from the live server.
    const marker = tmux(['show-options', '-v', '-t', `${THROWAWAY}:`, COCKPIT_MARKER], { allowFail: true });
    check('the identity marker is readable from the live session', marker === '1', `marker=${marker}`);

    // Panes, by explicit target.
    const panes = tmux(['list-panes', '-t', `${THROWAWAY}:cockpit`, '-F',
      '#{pane_index} #{pane_id} #{pane_pid} #{pane_current_path} #{pane_active}']).split('\n');
    check('the cockpit window holds exactly TWO panes (master + teamview)', panes.length === 2,
      `panes=${panes.length}`);

    const master = panes.map((l) => l.split(' ')).find((f) => f[0] === '0');
    const tvPane = panes.map((l) => l.split(' ')).find((f) => f[0] === '1');

    check('the MASTER pane is the active one, so attaching lands where the owner types',
      master && master[4] === '1');
    check('the master pane sits at the requested cwd', master && master[3] === ws,
      `cwd=${master && master[3]}`);

    // ⚠ THE CRITERION'S OWN CHECK: read the PROCESS TREE, never the launch config.
    const masterHarnesses = harnessesInTree(master[2]);
    check('the master pane holds NO harness process (read from /proc, not from the config)',
      masterHarnesses.length === 0,
      `pane_pid=${master[2]} comm=${procComm(master[2])} found=${JSON.stringify(masterHarnesses)}`);

    // The teamview pane really runs the command it was given.
    const tvAlive = procComm(tvPane[2]) !== null;
    check('the teamview pane is alive and running its command', tvAlive,
      `pane_pid=${tvPane[2]} comm=${procComm(tvPane[2])}`);

    // ⚠ THE DISCRIMINATOR. A control pane running a process named `claude` must be FLAGGED by the
    // same detector. Without this, "no harness found" could mean the detector is broken.
    const fakeHarnessDir = path.join(ws, 'bin');
    fs.mkdirSync(fakeHarnessDir, { recursive: true });
    const fakeClaude = path.join(fakeHarnessDir, 'claude');
    fs.writeFileSync(fakeClaude, '#!/bin/sh\nwhile :; do sleep 5; done\n', { mode: 0o755 });
    tmux(['new-window', '-d', '-t', `${THROWAWAY}:`, '-n', 'control', '-c', ws, '--', fakeClaude]);
    const ctlPanes = tmux(['list-panes', '-t', `${THROWAWAY}:control`, '-F', '#{pane_pid}']).split('\n');
    // Give the exec a moment to become the pane's process.
    execFileSync('sleep', ['1']);
    const ctlFound = harnessesInTree(ctlPanes[0].trim());
    check('CONTROL: the same detector FLAGS a pane that does run a harness-named process',
      ctlFound.length > 0, `found=${JSON.stringify(ctlFound)}`);

    // IDEMPOTENCE: a second boot must leave the cockpit exactly as it is.
    const again = ensureCockpit({
      workspaceRoot: ws, installed: true, sessionName: THROWAWAY,
      env: { RBTV_IGNITE_COCKPIT_TEAMVIEW: fakeTv, PATH: process.env.PATH },
      logger: () => {},
    });
    check('a second boot does NOT respawn the cockpit', again.spawned === false
      && again.reason === 'already-present', `reason=${again.reason}`);
    const panesAfter = tmux(['list-panes', '-t', `${THROWAWAY}:cockpit`, '-F', '#{pane_id}']).split('\n');
    check('the second boot left the existing panes untouched (same pane ids)',
      panesAfter.join(',') === panes.map((l) => l.split(' ')[1]).join(','),
      `${panesAfter.join(',')}`);
  } finally {
    tmux(['kill-session', '-t', THROWAWAY], { allowFail: true });
    try { fs.rmSync(ws, { recursive: true, force: true }); } catch { /* tmp */ }
  }

  // "I cleaned up" is MEASURED. And the live goal room must be exactly as it was.
  const after = sessionNames();
  check('the throwaway session is gone', !after.includes(THROWAWAY));
  check('every pre-existing tmux session is untouched (inventory identical)',
    after.join('|') === before.join('|'), `before=${before.join(',')} after=${after.join(',')}`);
}

try {
  layerCompose();
  layerPolicy();
  if (tmuxAvailable()) {
    const before = sessionNames();
    layerLive(before);
  } else {
    for (let i = 0; i < 13; i += 1) skip(`live layer check ${i + 1}`, 'no tmux on this box');
  }
} catch (err) {
  out('ERROR:', err.message, err.stack);
  checks.push({ name: 'unhandled error', pass: false });
}

const failed = checks.filter((c) => !c.pass);
// COMPLETENESS, asserted rather than assumed: a run that did not reach its declared denominator is
// INCOMPLETE and exits non-zero even with zero failures (G-121 — a truncated run reads greener
// than a complete one).
const complete = checks.length === EXPECTED_CHECKS;
out('');
out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed (expected ${EXPECTED_CHECKS})`);
if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
out(`SKIPPED_COUNT: ${skipped}`);
out(`SUITE-COMPLETE: ${complete}`);
out(`COCKPIT_OK: ${failed.length === 0 && complete}`);
out(`EXIT: ${failed.length === 0 && complete ? 0 : 1}`);
out(`WALL_MS: ${Date.now() - start}`);
process.exitCode = (failed.length === 0 && complete) ? 0 : 1;
