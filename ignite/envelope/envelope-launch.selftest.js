'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { admitLaunch, consumeLaunch, isStaffUncaged } = require('./launch');
const { loadCentralStore, resolveCredentials, injectDeclaredEnv } = require('./credentials');
const { stampLaunchRefused } = require('./stamp');
const { conflictBind } = require('../server/spawn/seat-grants');

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

  const { openHeartStore, closeHeartStore } = require('../server/heart/heart-store');
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

  assert.equal(isStaffUncaged({ seat: 'leader' }), true);
  assert.equal(isStaffUncaged({ seat: 'worker' }), false);
  assert.ok(conflictBind([
    { path: repoA, access: 'rw', source: 'a' },
    { path: repoA, access: 'ro', source: 'b' },
  ]));
  const planning = consumeLaunch({ ...base, fillIns: null });
  assert.equal(planning.ok, true, JSON.stringify(planning.refuse));
}

run();
