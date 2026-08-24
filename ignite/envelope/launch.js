'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { compile, compilePlanning } = require('./compiler');
const { writeConfigShims } = require('./shims');
const { reasonFrom } = require('../server/spawn/seat-grants');

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

function admitLaunch(raw) {
  ensureGoalScratch(raw.goalDir);
  const shims = writeConfigShims({
    goalDir: raw.goalDir,
    home: raw.home || os.homedir(),
    workspaceRoot: raw.workspaceRoot,
    rbtvRepo: raw.rbtvRepo,
  });
  const compiled = consumeLaunch(raw);
  if (!compiled.ok) return { spawn: false, refuse: compiled.refuse };
  return {
    spawn: true,
    binds: compiled.binds,
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
  admitLaunch,
  bindsToSpec,
  reasonFrom,
};
