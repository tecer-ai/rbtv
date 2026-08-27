'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { compile, compilePlanning } = require('./compiler');
const { covers, realpathOrNull } = require('./paths');
const { writeConfigShims } = require('./shims');
const { reasonFrom } = require('../supervisor/spawn/seat-grants');

const STAFF = new Set(['leader', 'goal-master', 'channel-master']);
const FILL_IN_NAME = 'envelope.json';

class LaunchRefused extends Error {
  constructor(refuse) {
    super(reasonFrom(refuse));
    this.name = 'LaunchRefused';
    this.code = 'E_LAUNCH_REFUSED';
    this.refuse = refuse;
  }
}

function isStaffUncaged(seatPath) {
  const name = seatPath && seatPath.seat;
  return typeof name === 'string' && STAFF.has(name);
}

function loadFillIns(goalDir) {
  if (!goalDir) return null;
  const p = path.join(goalDir, FILL_IN_NAME);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function consumeLaunch(raw) {
  const workspaceRoot = raw.workspaceRoot;
  const goalId = raw.goalId;
  const rbtvRepo = raw.rbtvRepo || path.resolve(__dirname, '../..');
  const fill = raw.fillIns !== undefined ? raw.fillIns : loadFillIns(raw.goalDir);
  const input = {
    workspaceRoot,
    goalId,
    rbtvRepo,
    home: raw.home || os.homedir(),
    tmpdir: raw.tmpdir || os.tmpdir(),
    namedRepos: (fill && fill.namedRepos) || [],
    projectFolder: (fill && fill.projectFolder) || null,
    credentialNames: (fill && fill.credentialNames) || [],
    extraPaths: (fill && extraPathsOf(fill)) || [],
  };
  return fill ? compile(input) : compilePlanning(input);
}

function extraPathsOf(fill) {
  return fill.extraPaths || [];
}

// ⚠ THE GOAL SCRATCH FOLDER IS MATERIALIZED HERE, BEFORE THE COMPILE — ORDER IS LOAD-BEARING.
// Template family 4 (`scratch-temp`) bakes `{workspace}/.rbtv/goals/{goal}/scratch`, and the
// compiler resolves every baked family path or refuses `unresolved`. Nothing else on the launch
// path creates that folder, so a compile-first order refused EVERY first launch of every goal
// with `E_LAUNCH_REFUSED unresolved …/scratch`. Scratch is a launch-time daemon artifact — the
// same launch step that writes the §8 config shims into it is the step that creates it.
function ensureGoalScratch(goalDir) {
  if (!goalDir) return null;
  const dir = path.join(goalDir, 'scratch');
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

// ⚠ THE ENDING STORE DIRECTORY IS MATERIALIZED HERE TOO, AND FOR THE SAME REASON — the compiler
// resolves every baked family path or refuses `unresolved`, and family 8 bakes
// `{workspace}/.rbtv/runtime/ignite`. On a workspace whose daemon has never written an ending
// (a fresh install, a probe fixture) the folder does not exist yet, and a compile-first order
// would refuse the launch instead of opening the store. `ending_store.py#ending_store_op` mkdirs
// the same parent on its own side; this is the launch-side half, so the bind source is there
// BEFORE bwrap is handed the flag.
function ensureEndingStore(workspaceRoot) {
  if (!workspaceRoot) return null;
  const dir = path.join(workspaceRoot, '.rbtv', 'runtime', 'ignite');
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

// ⚠ THE OWN-SEAT RW PUNCH — spec-envelope §5, and the one bind the COMPILER cannot make.
// `{goal}/seats` is a daemon-owned DIRECTORY: the compiler binds the whole tree `ro` so a worker
// cannot write a peer's folder. But §5's directory row carries an exception in its own heading —
// "the dir and everything under it, EXCEPT a worker's need to write its own seat folder" — and
// `daemon-owned-records.yaml` records it as `own-seat-folder-rw: true`. The compiler is per-GOAL
// and plan-time: it never learns WHICH seat is launching, so it cannot spell `{self}`. Launch can,
// and this is the step the compiler's creation entry names ("launch punches `{self}`").
// Without it a seat spawns, passes caps-at-kernel, and then cannot write the one directory it
// exists to fill — `probe-tmux-seat-live` died exactly there, on its own `a4-report.txt`.
//
// THE PUNCH IS EXACTLY ONE FOLDER, NEVER A LEVEL WIDER. `{goal}/seats` itself stays ro; only a
// path whose PARENT is the launching goal's own `seats/` is punched, so a seatDir from another
// goal, a nested path, or a service seat's `goalDir == seatDir` home punches nothing.
//
// ORDER IS THE MECHANISM, and the sort is how it is kept: bwrap applies mounts in argv order and
// the deepest-applied mount wins, so the list must read `{goal}` rw → `{goal}/seats` ro →
// `{seatDir}` rw → `{seatDir}/seat.md` ro. Appending the punch at the END instead would remount
// the seat folder OVER the daemon-owned `seat.md` ro carve inside it and hand the worker a
// writable `seat.md` — the one file §5 keeps read-only inside an otherwise RW own folder. Sorting
// by path (the compiler's own comparator) puts every parent before its children and holds that.
function ownSeatPunch(binds, raw) {
  const seatDir = raw && raw.seatDir;
  if (!seatDir) return { binds };
  const resolved = realpathOrNull(seatDir);
  // The compiler refuses a baked path that does not resolve; a seat folder that does not resolve
  // is the same defect one layer out, and a silent skip would launch the seat read-only instead.
  if (!resolved) return { refuse: { kind: 'unresolved', path: path.normalize(seatDir), source: 'own-seat', origin: 'own-seat' } };
  const goalDir = raw.goalDir ? realpathOrNull(raw.goalDir) : null;
  if (!goalDir) return { binds };
  if (path.dirname(resolved) !== path.join(goalDir, 'seats')) return { binds };
  if (binds.some((b) => b.path === resolved)) return { binds };
  // Nothing to punch BACK through unless something covering it is ro — on a bind list where the
  // seats tree is already rw the punch would be a no-op line of argv, not a grant.
  if (!binds.some((b) => b.access === 'ro' && b.path !== resolved && covers(b.path, resolved))) return { binds };
  const punched = [...binds, {
    path: resolved,
    access: 'rw',
    family: 'goal-folder',
    origin: 'own-seat',
    source: 'own-seat-punch',
  }];
  punched.sort((a, b) => a.path.localeCompare(b.path));
  return { binds: punched };
}

function admitLaunch(raw) {
  ensureGoalScratch(raw.goalDir);
  ensureEndingStore(raw.workspaceRoot);
  const shims = writeConfigShims({
    goalDir: raw.goalDir,
    home: raw.home || os.homedir(),
    workspaceRoot: raw.workspaceRoot,
    rbtvRepo: raw.rbtvRepo,
  });
  const compiled = consumeLaunch(raw);
  if (!compiled.ok) return { spawn: false, refuse: compiled.refuse };
  const punched = ownSeatPunch(compiled.binds, raw);
  if (punched.refuse) return { spawn: false, refuse: punched.refuse };
  return {
    spawn: true,
    binds: punched.binds,
    credentialNames: compiled.credentialNames || [],
    shims,
  };
}

// `family` and `origin` ride along with the verb. They are not decoration: `cage.js#lastCovering`
// asks `compiler.js#authorizedCarve` whether a covering pair at different access is a conflict,
// and that question is unanswerable from a path and a verb alone — a `/tmp` opening is a carve
// because it came from a TEMP FAMILY, not because of how it is spelled. Dropping them here is
// what made a workspace legal to the compiler illegal to the mask composer.
// `specToBwrapFlags` reads only `verb`/`path`/`punchThrough`, so the extra fields cost no argv.
function bindsToSpec(binds) {
  return binds.map((b) => ({
    verb: b.access === 'rw' ? 'bind' : 'ro-bind',
    path: b.path,
    access: b.access,
    family: b.family,
    origin: b.origin,
  }));
}

module.exports = {
  STAFF,
  FILL_IN_NAME,
  LaunchRefused,
  isStaffUncaged,
  loadFillIns,
  consumeLaunch,
  ensureEndingStore,
  ownSeatPunch,
  admitLaunch,
  bindsToSpec,
  reasonFrom,
};
