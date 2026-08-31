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
mkdirp(path.join(workspace, '.rbtv', 'runtime', 'ignite'));
// The WAL sidecars are part of the fixture on purpose: they are what makes the DIRECTORY, and not
// `heart.db` alone, the thing the cage has to open.
touch(path.join(workspace, '.rbtv', 'runtime', 'ignite', 'heart.db'));
touch(path.join(workspace, '.rbtv', 'runtime', 'ignite', 'heart.db-wal'));
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
touch(path.join(goalDir, 'state.csv'));
touch(path.join(goalDir, 'taskforce.csv'));
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

// The bind the cage actually applies to a path: input order is output order and the LAST entry
// covering a path decides what that path IS (`cage.js`'s reading, and bwrap's own).
function innermostAccess(result, abs) {
  const real = fs.realpathSync(abs);
  let access = null;
  for (const b of result.binds) {
    if (real === b.path || real.startsWith(`${b.path}${path.sep}`)) access = b.access;
  }
  return access;
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
  assert.equal(innermostAccess(plan, path.join(workspace, '.rbtv', 'mirror')), 'ro', 'mirror root stays ro with no plan grant');
  assert.ok(hasBind(plan, path.join(home, '.cache'), 'rw'), 'benign cache rw');
  assert.ok(hasBind(plan, path.join(home, '.config', 'tool'), 'rw'), 'benign config child rw');
  assert.ok(!hasBind(plan, path.join(home, '.config', 'opencode'), 'rw'), 'opencode not an extra rw opening');
  assert.ok(hasBind(plan, path.join(goalDir, 'taskforce.csv'), 'ro'), 'daemon-owned file ro');
  // ⚠ AND `sessions.csv` / `state.csv` ARE NOT — inverted 2026-08-27, the `coordination` fix one
  // file in. They are records the seat's OWN protocol writes (`checkin`, `checkout`,
  // `advance-state`), and the file-level ro bind made the kit's atomic writer (tmp + `os.replace`)
  // fail EBUSY: `rename(2)` onto a bind MOUNTPOINT is unconditionally busy. Positively on the
  // innermost cover, for the reason the `coordination` pair states: an absent ro row also reads
  // green when the path stopped being bound at all.
  assert.ok(!hasBind(plan, path.join(goalDir, 'sessions.csv'), 'ro'), 'sessions.csv NOT ro — the seat stamps its own check-in (D3)');
  assert.equal(innermostAccess(plan, path.join(goalDir, 'sessions.csv')), 'rw', 'sessions.csv is WRITABLE');
  assert.equal(innermostAccess(plan, path.join(goalDir, 'state.csv')), 'rw', 'state.csv is WRITABLE');
  // …and `seat.md` STAYS ro: a wall-control surface, not a record (D3 item 3).
  assert.equal(innermostAccess(plan, path.join(goalDir, 'seats', 's1', 'seat.md')), 'ro', 'seat.md stays READ-ONLY');
  assert.ok(hasBind(plan, path.join(goalDir, 'seats'), 'ro'), 'seats dir ro');
  // ⚠ THE BUS IS WRITABLE, and this row is the assertion that keeps it so. `coordination` was in
  // `daemon-owned-records.yaml#directories` and its ro bind made `coordinate checkin` / `send` die
  // EROFS for every caged seat (2026-08-27) — the protocol's own acts, forbidden by the cage.
  assert.ok(!hasBind(plan, path.join(goalDir, 'coordination'), 'ro'), 'coordination dir NOT ro — the bus is the protocol\'s own surface (D3)');
  // …and POSITIVELY: the innermost bind covering it is the rw goal-folder one. Absence of an ro row
  // alone would also read green if the path stopped being bound at all, which is the same EROFS.
  assert.equal(innermostAccess(plan, path.join(goalDir, 'coordination')), 'rw', 'coordination dir is WRITABLE');
  // ⚠ THE ENDING STORE IS WRITABLE — the same class one directory out. `heart.db` is the ONE
  // ending store and the SEAT is its own ending's author (spec-state-store §4.1 Row A), but
  // family 5 binds `{workspace}` ro, so `coordinate checkout` refused `attempt to write a
  // readonly database` for every caged seat (measured live 2026-08-27). Asserted POSITIVELY on
  // the innermost cover, not as the absence of an ro row: absence also reads green when the path
  // is simply not bound, which is the same unwritable store.
  // The DIRECTORY, because sqlite WAL writes `heart.db-wal`/`-shm` beside the db.
  const endingStore = path.join(workspace, '.rbtv', 'runtime', 'ignite');
  assert.equal(innermostAccess(plan, endingStore), 'rw', 'ending-store dir is WRITABLE');
  assert.equal(innermostAccess(plan, path.join(endingStore, 'heart.db-wal')), 'rw', 'the WAL sidecar path is inside the rw opening');
  assert.ok(hasBind(plan, endingStore, 'rw'), 'ending-store dir has its own rw bind (family 8)');
  assert.ok(!plan.binds.some((b) => b.path === fs.realpathSync(path.join(workspace, '.rbtv', 'config', '.env'))));
  const fam = familiesOf(plan);
  assert.ok(fam.has('goal-folder') && fam.has('named-repos') && fam.has('project-folder'));
  assert.ok(fam.has('scratch-temp') && fam.has('vault-wide-read'));
  assert.ok(fam.has('rbtv-repo') && fam.has('benign-cache-config-temp'));
  assert.ok(fam.has('ending-store'), 'family 8 emitted');
  assert.ok(fam.has('mirror'), 'family 9 (mirror) emitted');

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
  assert.ok(pf.has('rbtv-repo'), 'planning-zero-fill-in: rbtv-repo');
  assert.ok(pf.has('mirror'), 'planning-zero-fill-in: mirror family present, no plan grant into it');
  assert.ok(pf.has('benign-cache-config-temp'), 'planning-zero-fill-in: benign-cache-config-temp');
  assert.ok(!pf.has('named-repos'), 'planning-zero-fill-in: no named-repos');
  assert.ok(!pf.has('project-folder'), 'planning-zero-fill-in: no project-folder');
  assert.ok(!hasBind(planning, repoA, 'rw'), 'planning-zero-fill-in: named repo excluded');
  assert.ok(!hasBind(planning, project, 'rw'), 'planning-zero-fill-in: project folder excluded');
  assert.equal(innermostAccess(planning, path.join(workspace, '.rbtv', 'mirror')), 'ro', 'planning-zero-fill-in: no rw grant, mirror stays ro');
  console.log('PASS planning-zero-fill-in');

  // THE MIRROR CARVE (fix-mirror-family-split, 2026-08-30) — a plan's rw grant landing under
  // `{mirror}` now compiles; the mirror ROOT stays ro. `projectFolder` is the vehicle here since
  // it is one of the three the plan-reviewer measured refusing before this fix (the others,
  // `namedRepos` and `extraPaths:rw`, exercise the same `authorizedCarve` clause).
  const mirrorProduct = path.join(workspace, '.rbtv', 'mirror', 'office', 'meeting-summarizer');
  mkdirp(mirrorProduct);
  const mirrorGrant = compile({
    ...base,
    projectFolder: path.join('.rbtv', 'mirror', 'office', 'meeting-summarizer'),
  });
  assert.equal(mirrorGrant.ok, true, `mirror rw grant refused: ${JSON.stringify(mirrorGrant.refuse)}`);
  assert.equal(innermostAccess(mirrorGrant, mirrorProduct), 'rw', 'plan rw path under mirror compiles rw');
  assert.equal(innermostAccess(mirrorGrant, path.join(workspace, '.rbtv', 'mirror')), 'ro', 'mirror root stays ro alongside the narrow rw carve');
  console.log('PASS mirror-carve-admitted');

  // THE RBTV REPO CARVE — `ignite-engine-loop` M1, register filing `G-leader-0828-1951`. These two
  // arms REPLACE `rbtv-repo-still-refuses` / `extraPaths-rw-under-rbtv-repo-refuses`, which asserted
  // the opposite until the plan bound at 5dc32b91 settled the rbtv read-only floor as a GAP. Both
  // halves are asserted together on purpose: an arm that only proves the door opens does not prove
  // the wall still exists, and this pair is the compile-layer half of that same reading.
  const repoProduct = path.join(rbtvRepo, 'ignite', 'envelope');
  const repoSibling = path.join(rbtvRepo, 'core');
  mkdirp(repoProduct);
  mkdirp(repoSibling);
  const repoGrant = compile({
    ...base,
    projectFolder: repoProduct,
  });
  assert.equal(repoGrant.ok, true, `plan rw path inside the rbtv repo refused: ${JSON.stringify(repoGrant.refuse)}`);
  assert.equal(innermostAccess(repoGrant, repoProduct), 'rw', 'declared rw path inside the rbtv repo compiles rw');
  assert.equal(innermostAccess(repoGrant, rbtvRepo), 'ro', 'rbtv repo root stays ro alongside the narrow rw carve');
  // THE FENCE, read off the same bind list: a SIBLING the plan did not declare inherits the repo
  // root's `ro` and gets no rw bind of its own. Nothing declares itself — that is the whole reason
  // the carve is narrow — so this is the arm that would redden if the rule keyed on the family
  // alone without a declared narrow.
  assert.equal(innermostAccess(repoGrant, repoSibling), 'ro', 'an UNDECLARED path inside the rbtv repo stays ro');
  console.log('PASS rbtv-repo-declared-carve-admitted');

  const extraMirror = path.join(workspace, '.rbtv', 'mirror', 'x');
  const extraGrant = compile({
    ...base,
    extraPaths: [{ path: extraMirror, access: 'rw' }],
  });
  assert.equal(extraGrant.ok, true, `extraPaths rw under mirror refused: ${JSON.stringify(extraGrant.refuse)}`);
  assert.equal(innermostAccess(extraGrant, extraMirror), 'rw', 'extraPaths rw under mirror compiles rw');
  console.log('PASS extraPaths-rw-under-mirror');

  // The `extraPaths` vehicle through the same carve — this is the one `composeCageFor` fills from a
  // seat's `rw-paths:`, so it is the arm that stands closest to a real caged build seat.
  const extraRepo = compile({
    ...base,
    extraPaths: [{ path: repoProduct, access: 'rw' }],
  });
  assert.equal(extraRepo.ok, true, `extraPaths rw inside the rbtv repo refused: ${JSON.stringify(extraRepo.refuse)}`);
  assert.equal(innermostAccess(extraRepo, repoProduct), 'rw', 'extraPaths rw inside the rbtv repo compiles rw');
  assert.equal(innermostAccess(extraRepo, repoSibling), 'ro', 'extraPaths carve leaves undeclared siblings ro');
  console.log('PASS extraPaths-rw-under-rbtv-repo-admitted');

  const planningExtra = compilePlanning({
    ...base,
    extraPaths: [{ path: extraMirror, access: 'rw' }],
  });
  assert.equal(planningExtra.ok, true, `compilePlanning dropped seat extraPaths: ${JSON.stringify(planningExtra.refuse)}`);
  assert.equal(innermostAccess(planningExtra, extraMirror), 'rw', 'compilePlanning keeps seat extraPaths');
  assert.ok(!hasBind(planningExtra, repoA, 'rw'), 'compilePlanning still zeros namedRepos');
  console.log('PASS compilePlanning-keeps-seat-extraPaths');
  console.log('PASS compiler');
}

run();
