'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { compile, compilePlanning } = require('./compiler');
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

function admitLaunch(raw) {
  const compiled = consumeLaunch(raw);
  if (!compiled.ok) return { spawn: false, refuse: compiled.refuse };
  return {
    spawn: true,
    binds: compiled.binds,
    credentialNames: compiled.credentialNames || [],
  };
}

function bindsToSpec(binds) {
  return binds.map((b) => ({
    verb: b.access === 'rw' ? 'bind' : 'ro-bind',
    path: b.path,
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
