'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { admitLaunch, consumeLaunch, isStaffUncaged, loadFillIns } = require('./launch');
const { loadCentralStore, resolveCredentials, injectDeclaredEnv } = require('./credentials');
const { stampLaunchRefused } = require('./stamp');
const { conflictBind } = require('../supervisor/spawn/seat-grants');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'envelope-launch-'));
const workspace = path.join(root, 'ws');
const home = path.join(root, 'home');
const rbtvRepo = path.join(root, 'rbtv');
const goalId = 'g1';
const goalDir = path.join(workspace, '.rbtv', 'goals', goalId);
const repoA = path.join(workspace, 'repo-a');

function mkdirp(p) { fs.mkdirSync(p, { recursive: true }); }
function touch(p, body) {
  mkdirp(path.dirname(p));
  fs.writeFileSync(p, body == null ? '' : body);
}

mkdirp(path.join(goalDir, 'scratch'));
mkdirp(path.join(goalDir, 'coordination'));
mkdirp(path.join(goalDir, 'seats', 's1'));
mkdirp(path.join(workspace, '.rbtv', 'mirror', 'x'));
mkdirp(path.join(workspace, '.rbtv', 'config'));
mkdirp(path.join(repoA, '.git'));
mkdirp(path.join(home, '.cache'));
mkdirp(path.join(home, '.config', 'tool'));
mkdirp(path.join(rbtvRepo, 'ignite', 'envelope'));
touch(path.join(goalDir, 'sessions.csv'));
touch(path.join(rbtvRepo, 'ignite', 'envelope', 'spawn-profiles.yaml'));
touch(path.join(workspace, '.rbtv', 'config', '.env'), 'DECLARED=secret\nUNDECLARED=nope\nEMPTY=\n');

const base = {
  workspaceRoot: workspace,
  goalId,
  goalDir,
  home,
  tmpdir: os.tmpdir(),
  rbtvRepo,
};

function run() {
  touch(path.join(goalDir, 'envelope.json'), JSON.stringify({
    namedRepos: ['repo-a'],
    extraPaths: [{ path: 'repo-a', access: 'ro' }],
    credentialNames: ['DECLARED'],
  }));
  const clash = admitLaunch(base);
  assert.equal(clash.spawn, false, 'conflicting-bind must not spawn');
  assert.equal(clash.refuse.kind, 'conflict');

  const { openHeartStore, closeHeartStore } = require('../state-store/heart/heart-store');
  const dbPath = path.join(root, 'heart.db');
  const heart = openHeartStore({ dbPath });
  try {
    const row = stampLaunchRefused({
      heartStore: heart,
      goal: goalId,
      seat: 's1',
      refuse: clash.refuse,
    });
    assert.equal(row.ending, 'failed');
    assert.equal(row.reason_class, 'launch-refused');
    const fixture = path.join(root, 'stamp-fixture.txt');
    fs.writeFileSync(fixture, `failed: ${row.reason_class}\n${row.evidence_pointer}\n`);
    const grepped = fs.readFileSync(fixture, 'utf8');
    assert.match(grepped, /launch-refused/);
    process.stdout.write(`stamp fixture: ${grepped.split('\n')[0]}\n`);
  } finally {
    heart.close();
    closeHeartStore();
  }
  console.log('PASS refusal');

  const store = loadCentralStore(workspace);
  const injected = injectDeclaredEnv(['DECLARED'], store);
  assert.equal(injected.DECLARED, 'secret');
  assert.equal(injected.UNDECLARED, undefined);
  const missing = resolveCredentials(['NO_SUCH'], store);
  assert.equal(missing.ok, false);
  const empty = resolveCredentials(['EMPTY'], store);
  assert.equal(empty.ok, false);
  const ok = resolveCredentials(['DECLARED'], store);
  assert.equal(ok.ok, true);
  console.log('PASS injection');

  const missingLaunch = admitLaunch({ ...base, fillIns: { credentialNames: ['NO_SUCH'] } });
  assert.equal(missingLaunch.spawn, false, 'declared-but-absent key must refuse launch');
  assert.equal(missingLaunch.refuse.kind, 'missing-credential');
  assert.deepEqual(missingLaunch.refuse.missing, ['NO_SUCH']);
  const emptyLaunch = admitLaunch({ ...base, fillIns: { credentialNames: ['EMPTY'] } });
  assert.equal(emptyLaunch.spawn, false, 'declared empty store value must refuse launch');
  assert.equal(emptyLaunch.refuse.kind, 'missing-credential');
  const okLaunch = admitLaunch({ ...base, fillIns: { credentialNames: ['DECLARED'] } });
  assert.equal(okLaunch.spawn, true, `present key refused: ${JSON.stringify(okLaunch.refuse)}`);
  assert.deepEqual(okLaunch.credentialNames, ['DECLARED']);
  const noneLaunch = admitLaunch({ ...base, fillIns: null });
  assert.equal(noneLaunch.spawn, true, `zero names refused: ${JSON.stringify(noneLaunch.refuse)}`);
  assert.deepEqual(noneLaunch.credentialNames, []);
  console.log('PASS missing-credential-refuses');

  assert.equal(isStaffUncaged({ seat: 'leader' }), true);
  assert.equal(isStaffUncaged({ seat: 'worker' }), false);
  assert.ok(conflictBind([
    { path: repoA, access: 'rw', source: 'a' },
    { path: repoA, access: 'ro', source: 'b' },
  ]));
  const planning = consumeLaunch({ ...base, fillIns: null });
  assert.equal(planning.ok, true, JSON.stringify(planning.refuse));

  const grantDir = path.join(workspace, '.rbtv', 'mirror', 'x');
  const withGrant = admitLaunch({
    ...base,
    fillIns: null,
    extraPaths: [{ path: grantDir, access: 'rw' }],
  });
  assert.equal(withGrant.spawn, true, `seat extraPaths refused: ${JSON.stringify(withGrant.refuse)}`);
  assert.ok(
    (withGrant.binds || []).some((b) => b.access === 'rw' && path.resolve(b.path) === path.resolve(grantDir)),
    'admitLaunch composes raw extraPaths as an rw bind when there is no envelope.json',
  );
  const repoWrite = admitLaunch({
    ...base,
    fillIns: null,
    extraPaths: [{ path: path.join(rbtvRepo, 'ignite', 'envelope'), access: 'rw' }],
  });
  assert.equal(repoWrite.spawn, false, 'rbtv-repo extraPaths must refuse, not silently grant');
  assert.equal(repoWrite.refuse.kind, 'conflict');
  console.log('PASS seat-extraPaths-composed');

  // owner-flagged-birth-writes-no-envelope: a Path-B-born goal (marked by
  // `planning/bound-plan.json`, `path_b.py#BOUND_PLAN_NAME`) with no envelope.json warns loudly
  // once; any other goal shape (no such marker) falls back silently, exactly as before.
  const bornGoalDir = path.join(root, 'born-goal');
  mkdirp(path.join(bornGoalDir, 'planning'));
  touch(path.join(bornGoalDir, 'planning', 'bound-plan.json'), '{}');
  const origError = console.error;
  let warned = '';
  console.error = (msg) => { warned += msg; };
  const bornFill = loadFillIns(bornGoalDir);
  console.error = origError;
  assert.equal(bornFill, null);
  assert.match(warned, /Path-B-born goal has no envelope\.json/);

  const planningGoalDir = path.join(root, 'planning-goal');
  mkdirp(planningGoalDir);
  let silent = '';
  console.error = (msg) => { silent += msg; };
  const otherFill = loadFillIns(planningGoalDir);
  console.error = origError;
  assert.equal(otherFill, null);
  assert.equal(silent, '', 'a goal with no bound-plan.json must stay silent');
  console.log('PASS path-b-born-warns-once');
}

run();
