'use strict';

// engine/queue-request.js — daemon hook for the Path A planning-seat mint
// (spec-planning-door §1 / §2.1). The IE-2 splice door is gone: no planningMode,
// no passesMinted, no materializeArgv, no per-milestone queue-request drain.
//
// Unbuilt-seat repair lives in `./unbuilt-seats` (lane-watch still requires
// `buildUnbuiltSeats` from this module).

const fs = require('node:fs');
const path = require('node:path');
const {
  runPlanningMintPass, isPlanningGoal, pipelineMinted, planningMintArgv, PLANNING_SEATS,
} = require('../planning/door');
const unbuilt = require('./unbuilt-seats');

const PLANNING_MODULE = 'meta';
const PLANNING_COMPONENT = 'planning';
const PLANNING_WORKFLOW = 'plan-console';
const PLANNING_CODE = 'plan';
const MATERIALIZE_PY = path.join(__dirname, '..', 'team-kit', 'materialize-seats.py');
const SUBPROCESS_TIMEOUT_MS = 120000;

class Refusal extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

function resolveCatalogRoot(goalsRoot) {
  const workspace = path.resolve(goalsRoot, '..', '..');
  const book = path.join(workspace, 'rbtv.json');
  if (!fs.existsSync(book)) {
    throw new Refusal('queue-request-workspace-book-absent',
      `${book} — the book that records \`rbtv_path\` — does not exist, so this is not a workspace `
      + 'and there is no component catalog to materialize a planning pass from');
  }
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(book, 'utf8'));
  } catch (err) {
    throw new Refusal('queue-request-workspace-book-unreadable',
      `${book} is not readable JSON — ${err.message}`);
  }
  if (!String((parsed && parsed.rbtv_path) || '').trim()) {
    throw new Refusal('queue-request-workspace-book-no-rbtv-path',
      `${book} carries no \`rbtv_path\` — the one field that proves this tree is an rbtv workspace`);
  }
  let repoRoot = String(parsed.rbtv_path).trim();
  if (!path.isAbsolute(repoRoot)) repoRoot = path.resolve(workspace, repoRoot);
  const catalogRoot = path.join(repoRoot, PLANNING_MODULE);
  if (!fs.existsSync(catalogRoot)) {
    throw new Refusal('queue-request-catalog-root-absent',
      `${catalogRoot}: the component catalog root is absent — the '${PLANNING_WORKFLOW}' workflow `
      + 'is read from there and nothing can be materialized without it');
  }
  const sheet = path.join(workspace, '.rbtv', 'config', 'modules', PLANNING_MODULE,
    PLANNING_COMPONENT, 'bindings', `${PLANNING_CODE}.json`);
  if (!fs.existsSync(sheet)) {
    throw new Refusal('queue-request-bindings-sheet-absent',
      `${sheet}: the planning workflow's casting sheet is absent — which harness, model and effort `
      + 'each seat runs on has no honest guess (`#d-abolish-profile-names`)');
  }
  return { workspace, catalogRoot, sheet };
}

// The workflow manifest is the SOURCE OF TRUTH for the planning seat ids —
// `materialize-seats.py --workflow W` resolves exactly `<component>/workflows/<W>/<W>.csv`
// and writes that file's `Seat/workflow` column onto taskforce.csv. `planning/door.js`
// decides already-minted by comparing `pipeline-seats.json` against those same rows, so the
// json is only ever a mirror of this column. Divergence is not a load error: it makes every
// planning goal read unminted forever. Probe leg M byte-compares the two.
const PLANNING_MANIFEST_REL = path.join(
  PLANNING_COMPONENT, 'workflows', PLANNING_WORKFLOW, `${PLANNING_WORKFLOW}.csv`,
);

function planningManifestPath(catalogRoot) {
  return path.join(catalogRoot, PLANNING_MANIFEST_REL);
}

// Read the manifest's first column. Later columns are RFC-quoted and may contain commas;
// the id column never is, so the text before the first comma is the whole cell.
function planningManifestSeats(catalogRoot) {
  const file = planningManifestPath(catalogRoot);
  let text;
  try {
    text = fs.readFileSync(file, 'utf8');
  } catch (err) {
    throw new Refusal('queue-request-planning-manifest-unreadable',
      `${file}: the '${PLANNING_WORKFLOW}' workflow manifest — the source of truth for the `
      + `planning seat ids — is unreadable: ${err.message}`);
  }
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (!lines.length) {
    throw new Refusal('queue-request-planning-manifest-empty', `${file} carries no rows`);
  }
  return lines.slice(1).map((l) => l.slice(0, l.indexOf(',') < 0 ? l.length : l.indexOf(',')).trim());
}

function runQueueRequestPass({ goalsRoot, engine = null, logger = null, mint = null }) { // eslint-disable-line no-unused-vars
  return runPlanningMintPass({
    goalsRoot,
    resolveCatalog: resolveCatalogRoot,
    logger,
    mint,
  });
}

module.exports = {
  PLANNING_MODULE, PLANNING_COMPONENT, PLANNING_WORKFLOW, PLANNING_CODE, PLANNING_SEATS,
  PLANNING_MANIFEST_REL, MATERIALIZE_PY, SUBPROCESS_TIMEOUT_MS,
  Refusal, resolveCatalogRoot, planningManifestPath, planningManifestSeats,
  isPlanningGoal, pipelineMinted, planningMintArgv, runQueueRequestPass,
  sheetForSeat: unbuilt.sheetForSeat,
  materializeUnbuiltSeatArgv: unbuilt.materializeUnbuiltSeatArgv,
  buildUnbuiltSeats: unbuilt.buildUnbuiltSeats,
  goalLocalSeatDir: unbuilt.goalLocalSeatDir,
  goalLocalLint: unbuilt.goalLocalLint,
  goalLocalArgv: unbuilt.goalLocalArgv,
  buildGoalLocalSeats: unbuilt.buildGoalLocalSeats,
  GOAL_LOCAL_SOURCE: unbuilt.GOAL_LOCAL_SOURCE,
  GOAL_LOCAL_REUSE: unbuilt.GOAL_LOCAL_REUSE,
  GOAL_LOCAL_SHEET: unbuilt.GOAL_LOCAL_SHEET,
};

if (require.main === module) {
  const assert = require('node:assert');
  const argv = planningMintArgv({
    goalFolder: '/g', catalogRoot: '/c', sheet: '/s.json',
  });
  assert(argv.includes('--package') && argv.includes('/g'));
  assert(argv.includes('--workflow') && argv.includes(PLANNING_WORKFLOW));
  assert(!argv.includes('--nested'));
  assert(!argv.includes('--milestone-id'));
  assert(!argv.includes('full') && !argv.includes('collapsed'));
  assert(argv.includes('--force-partial') && argv.includes('--json'));
  assert.strictEqual(pipelineMinted([]), false);
  assert.strictEqual(pipelineMinted(PLANNING_SEATS.map((seat) => ({ seat }))), true);
  assert.strictEqual(pipelineMinted(PLANNING_SEATS.slice(0, 4).map((seat) => ({ seat }))), false);
  assert.deepStrictEqual(
    planningManifestSeats(path.join(__dirname, '..', '..', PLANNING_MODULE)),
    PLANNING_SEATS.slice(),
    'pipeline-seats.json has diverged from the plan-console manifest — the door would re-mint forever',
  );
  console.log('queue-request selftest OK');
}
