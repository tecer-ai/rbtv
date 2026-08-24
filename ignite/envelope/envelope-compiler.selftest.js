'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { compile, compilePlanning } = require('./compiler');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'envelope-compiler-'));
const workspace = path.join(root, 'ws');
const home = path.join(root, 'home');
const rbtvRepo = path.join(root, 'rbtv');
const goalId = 'g1';
const goalDir = path.join(workspace, '.rbtv', 'goals', goalId);
const repoA = path.join(workspace, 'repo-a');
const project = path.join(workspace, '1-projects', 'demo');

function mkdirp(p) { fs.mkdirSync(p, { recursive: true }); }
function touch(p, body) {
  mkdirp(path.dirname(p));
  fs.writeFileSync(p, body == null ? '' : body);
}

mkdirp(path.join(goalDir, 'scratch'));
mkdirp(path.join(goalDir, 'coordination'));
mkdirp(path.join(goalDir, 'seats', 's1'));
mkdirp(path.join(goalDir, 'planning'));
mkdirp(path.join(workspace, '.rbtv', 'goals', 'other', 'scratch'));
mkdirp(path.join(workspace, '.rbtv', 'heart'));
mkdirp(path.join(workspace, '.rbtv', 'mirror', 'x'));
mkdirp(path.join(workspace, '.rbtv', 'config'));
mkdirp(path.join(workspace, '.user', 'config', 'env'));
mkdirp(path.join(workspace, '4-archives'));
mkdirp(path.join(repoA, '.git'));
mkdirp(project);
mkdirp(path.join(home, '.cache'));
mkdirp(path.join(home, '.config', 'tool'));
mkdirp(path.join(home, '.config', 'opencode'));
mkdirp(path.join(rbtvRepo, 'ignite', 'envelope'));
touch(path.join(goalDir, 'sessions.csv'));
touch(path.join(goalDir, 'seats', 's1', 'seat.md'));
touch(path.join(workspace, '.rbtv', 'config', '.env'), 'FOO=1\n');
touch(path.join(workspace, '.rbtv', 'config', 'sender-token.env'), 'T=1\n');
touch(path.join(workspace, '.rbtv', 'config', 'private.json'), '{}\n');
touch(path.join(rbtvRepo, 'ignite', 'envelope', 'spawn-profiles.yaml'));

const base = {
  workspaceRoot: workspace,
  goalId,
  home,
  tmpdir: os.tmpdir(),
  rbtvRepo,
  mirror: path.join(workspace, '.rbtv', 'mirror'),
};

function familiesOf(result) {
  return new Set(result.binds.map((b) => b.family).filter(Boolean));
}

function hasBind(result, abs, access) {
  const real = fs.realpathSync(abs);
  return result.binds.some((b) => b.path === real && b.access === access);
}

function run() {
  const plan = compile({
    ...base,
    namedRepos: ['repo-a'],
    projectFolder: '1-projects/demo',
    credentialNames: ['FOO'],
    extraPaths: [],
  });
  assert.equal(plan.ok, true, `plan fixture refused: ${JSON.stringify(plan.refuse)}`);
  assert.equal(plan.posture, 'caged-worker');
  assert.deepEqual(plan.credentialNames, ['FOO']);
  assert.ok(hasBind(plan, goalDir, 'rw'), 'goal folder rw');
  assert.ok(hasBind(plan, repoA, 'rw'), 'named repo rw');
  assert.ok(hasBind(plan, project, 'rw'), 'project folder rw');
  assert.ok(hasBind(plan, path.join(goalDir, 'scratch'), 'rw'), 'scratch rw');
  assert.ok(hasBind(plan, workspace, 'ro'), 'vault-wide ro');
  assert.ok(hasBind(plan, rbtvRepo, 'ro'), 'rbtv repo ro');
  assert.ok(hasBind(plan, path.join(workspace, '.rbtv', 'mirror'), 'ro'), 'mirror ro');
  assert.ok(hasBind(plan, path.join(home, '.cache'), 'rw'), 'benign cache rw');
  assert.ok(hasBind(plan, path.join(home, '.config', 'tool'), 'rw'), 'benign config child rw');
  assert.ok(!hasBind(plan, path.join(home, '.config', 'opencode'), 'rw'), 'opencode not an extra rw opening');
  assert.ok(hasBind(plan, path.join(goalDir, 'sessions.csv'), 'ro'), 'daemon-owned file ro');
  assert.ok(hasBind(plan, path.join(goalDir, 'seats'), 'ro'), 'seats dir ro');
  assert.ok(hasBind(plan, path.join(goalDir, 'coordination'), 'ro'), 'coordination dir ro');
  assert.ok(!plan.binds.some((b) => b.path === fs.realpathSync(path.join(workspace, '.rbtv', 'config', '.env'))));
  const fam = familiesOf(plan);
  assert.ok(fam.has('goal-folder') && fam.has('named-repos') && fam.has('project-folder'));
  assert.ok(fam.has('scratch-temp') && fam.has('vault-wide-read'));
  assert.ok(fam.has('rbtv-and-mirror') && fam.has('benign-cache-config-temp'));

  const clash = compile({
    ...base,
    namedRepos: ['repo-a'],
    extraPaths: [{ path: 'repo-a', access: 'ro' }],
  });
  assert.equal(clash.ok, false, 'conflict fixture must refuse');
  assert.equal(clash.refuse.kind, 'conflict');
  assert.ok(clash.refuse.pair && clash.refuse.pair.length === 2, 'conflict pair present');
  assert.ok(clash.refuse.pair.some((p) => p.access === 'rw') && clash.refuse.pair.some((p) => p.access === 'ro'));

  const missing = compile({
    ...base,
    namedRepos: ['no-such-repo'],
  });
  assert.equal(missing.ok, false, 'unresolved fixture must refuse');
  assert.equal(missing.refuse.kind, 'unresolved');
  assert.ok(String(missing.refuse.path).includes('no-such-repo'));
  assert.equal(missing.refuse.source, 'named-repo');

  const planning = compilePlanning(base);
  assert.equal(planning.ok, true, `planning envelope refused: ${JSON.stringify(planning.refuse)}`);
  assert.equal(planning.posture, 'caged-worker');
  assert.deepEqual(planning.credentialNames, []);
  const pf = familiesOf(planning);
  assert.ok(pf.has('goal-folder'), 'planning-zero-fill-in: goal-folder');
  assert.ok(pf.has('scratch-temp'), 'planning-zero-fill-in: scratch-temp');
  assert.ok(pf.has('vault-wide-read'), 'planning-zero-fill-in: vault-wide-read');
  assert.ok(pf.has('rbtv-and-mirror'), 'planning-zero-fill-in: rbtv-and-mirror');
  assert.ok(pf.has('benign-cache-config-temp'), 'planning-zero-fill-in: benign-cache-config-temp');
  assert.ok(!pf.has('named-repos'), 'planning-zero-fill-in: no named-repos');
  assert.ok(!pf.has('project-folder'), 'planning-zero-fill-in: no project-folder');
  assert.ok(!hasBind(planning, repoA, 'rw'), 'planning-zero-fill-in: named repo excluded');
  assert.ok(!hasBind(planning, project, 'rw'), 'planning-zero-fill-in: project folder excluded');
  console.log('PASS planning-zero-fill-in');
  console.log('PASS compiler');
}

run();
