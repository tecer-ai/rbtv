'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { admitLaunch } = require('./launch');
const { writeConfigShims, realStoreOnBinds } = require('./shims');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'envelope-shims-'));
const workspace = path.join(root, 'ws');
const home = path.join(root, 'home');
const rbtvRepo = path.join(root, 'rbtv');
const goalId = 'g1';
const goalDir = path.join(workspace, '.rbtv', 'goals', goalId);

function mkdirp(p) { fs.mkdirSync(p, { recursive: true }); }
function touch(p, body) {
  mkdirp(path.dirname(p));
  fs.writeFileSync(p, body == null ? '' : body);
}

mkdirp(path.join(goalDir, 'scratch'));
mkdirp(path.join(goalDir, 'coordination'));
mkdirp(path.join(workspace, '.rbtv', 'mirror', 'x'));
mkdirp(path.join(home, '.cache'));
mkdirp(path.join(home, '.config', 'tool'));
mkdirp(path.join(rbtvRepo, 'ignite', 'envelope'));
touch(path.join(home, '.claude.json'), '{"token":"harness-secret"}\n');
touch(path.join(workspace, '3-resources', 'tools', 'stools', 'config.yaml'), 'token: stools-secret\n');
touch(path.join(rbtvRepo, 'ignite', 'envelope', 'spawn-profiles.yaml'));

const base = {
  workspaceRoot: workspace,
  goalId,
  goalDir,
  home,
  tmpdir: os.tmpdir(),
  rbtvRepo,
};

function run() {
  const written = writeConfigShims(base);
  const claude = written.files.find((f) => f.harness === 'claude' && f.source.endsWith('.claude.json'));
  const stools = written.files.find((f) => f.tool === 'stools');
  assert.ok(claude, 'harness shim written');
  assert.ok(stools, 'stools shim written');
  assert.equal(fs.readFileSync(claude.dest, 'utf8'), '{"token":"harness-secret"}\n');
  assert.equal(fs.readFileSync(stools.dest, 'utf8'), 'token: stools-secret\n');

  const admitted = admitLaunch(base);
  assert.equal(admitted.spawn, true, 'planning envelope admits');
  const leaked = realStoreOnBinds(admitted.binds, written.sources);
  assert.deepEqual(leaked, [], `real stores on binds: ${leaked.join(',')}`);
  const claudeOnBinds = (admitted.binds || []).some((b) => path.resolve(b.path) === path.resolve(claude.source));
  const stoolsOnBinds = (admitted.binds || []).some((b) => path.resolve(b.path) === path.resolve(stools.source));
  assert.equal(claudeOnBinds, false, 'real ~/.claude.json not on bind list');
  assert.equal(stoolsOnBinds, false, 'real stools config.yaml not on bind list');

  console.log('PASS shims');
  console.log(`harness dest=${claude.dest}`);
  console.log(`stools dest=${stools.dest}`);
  console.log(`binds-exclude-real-stores leaked=${leaked.length}`);
}

run();
