#!/usr/bin/env node
'use strict';

// probe-engine-ending-store — DOES THE ENGINE HOLD THE ONE ENDING STORE?
//
// WHAT WAS BROKEN, AND WHY IT NEEDED ITS OWN PROBE. `supervisor/reconcile.js:796` reads
// `engine.endingStore` and NOTHING in the tree set it, so every production pass ran with `null`
// and took the absent arm of all seven of its gated branches: the leader's answers were never
// drained, the exhaustion exit could not stamp its `disarmed` row, and the recovery relaunch
// budget was never spent. That absence was invisible to every existing probe, because each one
// INJECTS `engine: { endingStore }` by hand into `reconcileGoal` — a fixture that supplies the
// very fact production was missing cannot see it missing. This probe therefore measures the
// COMPOSITION ROOT and nothing else: it calls the real `createEngine` and asks what came back.
//
// EVIDENCE CLASS: fixture, in-process, offline. A scratch workspace under the OS temp dir, the
// COMMITTED launch-profile config, `userManager: false`. It spawns no seat, opens no gateway,
// starts no daemon, touches no live store and writes nothing outside its temp dir.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const OUT_PATH = path.join(__dirname, 'probe-engine-ending-store.out');
const SPAWN_CONFIG = path.join(IGNITE_SRC, 'envelope', 'spawn-profiles.yaml');

const start = Date.now();
const lines = [];
let passed = 0;
let failed = 0;

function out(...l) { lines.push(...l); }
function check(name, ok, detail = '') {
  if (ok) { passed += 1; out(`ok    ${name}${detail ? `  — ${detail}` : ''}`); }
  else { failed += 1; out(`FAIL  ${name}${detail ? `  — ${detail}` : ''}`); }
  return ok;
}

// A fresh module registry per arm. `state-store/open.js` caches ONE handle per file per PROCESS
// and `runtime/engine.js` is a singleton require — without this, arm B would be answered by arm
// A's cached handle and the red mutations below could not be told apart from the green.
function freshEngine() {
  for (const key of Object.keys(require.cache)) {
    if (key.startsWith(IGNITE_SRC + path.sep)) delete require.cache[key];
  }
  return require('../engine').createEngine;
}

function scratchWorkspace(name) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), `engine-ending-${name}-`));
  fs.mkdirSync(path.join(root, '.rbtv', 'goals'), { recursive: true });
  fs.mkdirSync(path.join(root, '.rbtv', 'runtime', 'ignite'), { recursive: true });
  fs.mkdirSync(path.join(root, 'lane-state'), { recursive: true });
  return root;
}

function buildEngine(root, { logs }) {
  const createEngine = freshEngine();
  // The DAEMON's own shape: the lane store is a DIFFERENT FILE from the ending home, exactly as
  // `{data_root}/heart.db` is on the live box. An arm that passed the ending home as `dbPath`
  // could not tell the two bindings apart — the split section (h) of `probe-pause-resume` exists
  // for the same reason.
  process.env.RBTV_IGNITE_WORKSPACE_ROOT = root;
  return createEngine({
    dbPath: path.join(root, 'lane-state', 'heart.db'),
    spawnConfigPath: SPAWN_CONFIG,
    userManager: false,
    logger: (m) => logs.push(m),
  });
}

function main() {
  const prevWs = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  const { endingStorePath, openEndingStore, bind } = require('../../state-store');

  // ── A. THE ENGINE HOLDS THE ONE ENDING STORE, AND IT IS THE WORKSPACE'S HOME ────────────────
  const rootA = scratchWorkspace('a');
  const logsA = [];
  const engineA = buildEngine(rootA, { logs: logsA });
  const homeA = endingStorePath(rootA);

  check('A1: the composition root learns the workspace — `heartStore.config.workspaceRoot` is the scratch root',
    engineA.heartStore.config.workspaceRoot === rootA,
    `got=${engineA.heartStore.config.workspaceRoot}`);
  check('A2: `engine.endingStore` EXISTS — the key `reconcile.js:796` reads is on the returned engine',
    Boolean(engineA.endingStore), `typeof=${typeof engineA.endingStore}`);
  check('A3: it carries the writer half the exhaustion exit spends (stampSystem / insertAsk / incrementRecoveryRelaunch)',
    Boolean(engineA.endingStore)
      && typeof engineA.endingStore.stampSystem === 'function'
      && typeof engineA.endingStore.insertAsk === 'function'
      && typeof engineA.endingStore.incrementRecoveryRelaunch === 'function');
  check('A4: the ending home was CREATED at `<workspace>/.rbtv/runtime/ignite/heart.db` [spec-state-store 1.1]',
    fs.existsSync(homeA), homeA);
  check('A5: it is NOT the lane store — a writer bound to the caller\'s handle is the 919be192 defect',
    fs.existsSync(path.join(rootA, 'lane-state', 'heart.db'))
      && path.resolve(homeA) !== path.resolve(rootA, 'lane-state', 'heart.db'));
  check('A6: the boot was SILENT about the store — an error line here would mean the home was unopenable',
    logsA.filter((m) => m.level === 'error').length === 0,
    JSON.stringify(logsA.filter((m) => m.level === 'error')));

  // A ROW WRITTEN THROUGH THE ENGINE'S HANDLE IS READ BACK OUT OF THE FILE ITSELF, by a second,
  // independent handle. Proving the api answers its own writes would prove only that an object
  // remembers; the fact that matters is that the BYTES landed in the home every other reader binds.
  if (engineA.endingStore) {
    engineA.endingStore.stampSystem({
      goal: 'probe-goal', seat: 'probe-seat', ending: 'incomplete',
      diagnostic: 'attempt-counter exhaustion',
      evidence_pointer: path.join(rootA, 'evidence.json'),
      stamped_at: '2026-08-28T00:00:00Z',
      replace: true,
    });
    engineA.endingStore.writeGoalWord({
      goal: 'probe-goal', stored: 'paused', who_stamped: 'owner',
      evidence_pointer: 'probe', stamped_at: '2026-08-28T00:00:01Z',
    });
  }
  engineA.close();

  const reader = bind(openEndingStore(homeA));
  const readBack = reader.getCurrentEnding({ goal: 'probe-goal', seat: 'probe-seat' });
  const goalWord = reader.getGoalState('probe-goal');
  check('A7: `getCurrentEnding` against the FILE sees the row the engine wrote — disarmed, with the exit\'s own diagnostic',
    Boolean(readBack) && readBack.ending === 'incomplete' && Number(readBack.armed) === 0
      && readBack.diagnostic === 'attempt-counter exhaustion',
    JSON.stringify(readBack));
  check('A8: `getGoalState` against the same FILE sees the goal word the engine wrote — this is the file `laneIsPaused` binds',
    Boolean(goalWord) && goalWord.stored === 'paused', JSON.stringify(goalWord));
  check('A9: `close()` did NOT close the ending home — the handle is process-cached and shared with every lane pass',
    Boolean(readBack) && Boolean(goalWord));

  // ── B. AN UNOPENABLE HOME IS `null` + ONE ERROR LINE, AND THE ENGINE STILL CONSTRUCTS ──────
  const rootB = scratchWorkspace('b');
  // The home's PARENT is made a regular file, so `mkdirSync` inside `openEndingStore` throws
  // (ENOTDIR) before any handle exists. That is the real shape of an unopenable home.
  fs.rmSync(path.join(rootB, '.rbtv', 'runtime', 'ignite'), { recursive: true, force: true });
  fs.writeFileSync(path.join(rootB, '.rbtv', 'runtime', 'ignite'), 'not a directory\n');
  const logsB = [];
  let engineB = null;
  let threw = null;
  try { engineB = buildEngine(rootB, { logs: logsB }); } catch (err) { threw = err; }
  check('B1: the engine STILL CONSTRUCTS — a degraded recovery path, never a dead daemon',
    threw === null && Boolean(engineB), threw && threw.message);
  check('B2: `engine.endingStore` is `null` — today\'s behaviour exactly, and every consumer gates on it',
    Boolean(engineB) && engineB.endingStore === null, engineB && String(engineB.endingStore));
  const errorsB = logsB.filter((m) => m.level === 'error');
  check('B3: EXACTLY ONE error line, and it names what the daemon lost',
    errorsB.length === 1 && /ending store/i.test(errorsB[0].message)
      && /drain|budget|stamp/i.test(errorsB[0].message),
    JSON.stringify(errorsB.map((m) => m.message)));
  check('B4: the lane store still opened — the engine is otherwise whole',
    Boolean(engineB) && Boolean(engineB.heartStore) && Boolean(engineB.ticker));
  if (engineB) engineB.close();

  // ── C. NO WORKSPACE AT ALL IS THE SAME ANSWER, NOT A CRASH ─────────────────────────────────
  //
  // `resolveWorkspaceRoot` returns null when neither the db path nor the env names one. The
  // control matters: a `createEngine` that threw here would take down `rbtv run` on any box
  // without the env var.
  const rootC = scratchWorkspace('c');
  delete process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  const logsC = [];
  let engineC = null;
  let threwC = null;
  try {
    const createEngine = freshEngine();
    engineC = createEngine({
      dbPath: path.join(rootC, 'lane-state', 'heart.db'),
      spawnConfigPath: SPAWN_CONFIG,
      userManager: false,
      logger: (m) => logsC.push(m),
    });
  } catch (err) { threwC = err; }
  check('C1: with NO resolvable workspace the engine constructs, holds no ending store, and says so once',
    threwC === null && Boolean(engineC) && engineC.endingStore === null
      && logsC.filter((m) => m.level === 'error').length === 1,
    threwC ? threwC.message : `errors=${logsC.filter((m) => m.level === 'error').length}`);
  if (engineC) engineC.close();

  if (prevWs === undefined) delete process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  else process.env.RBTV_IGNITE_WORKSPACE_ROOT = prevWs;

  for (const r of [rootA, rootB, rootC]) {
    try { fs.rmSync(r, { recursive: true, force: true }); } catch { /* tmp */ }
  }
}

try {
  main();
} catch (err) {
  failed += 1;
  out(`PROBE FAULT: ${err && err.stack ? err.stack : err}`);
}

out('');
out(`PROBE probe-engine-ending-store EXIT=${failed ? 1 : 0} WALL_MS=${Date.now() - start} PASS=${failed === 0} CHECKS=${passed + failed}`);
const text = lines.join('\n') + '\n';
fs.writeFileSync(OUT_PATH, text);
process.stdout.write(text);
process.exit(failed ? 1 : 0);
