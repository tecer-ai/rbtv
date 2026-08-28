'use strict';

// planning/queue-request.js — the planning workflow's catalog constants and the
// pipeline-seat DIVERGENCE ALARM. It is no longer a daemon pass and no longer a hook:
// `runQueueRequestPass` and the Path A mint door it wrapped were deleted on 2026-08-28,
// because their admission key (`role: planning` in `goal.md` frontmatter) had no producer
// and the pass fired 0 times in 592,458 journal lines. The five pipeline seats are minted
// AT BIRTH by the creation route (`goal_creation_request.py#create`), never on a cadence.
// The file keeps its name because `supervisor/lane-watch.js` requires `buildUnbuiltSeats`
// from this path and `planning/exposure.csv` exposes it by that path.
//
// What lives here now:
//   · the `plan-console` workflow's module/component/workflow names, stated once;
//   · `planningManifestSeats()` — the manifest column that IS the seat-id source of truth,
//     deep-equalled against `pipeline-seats.json` by the selftest below and by probe leg M;
//   · the re-export face of `./unbuilt-seats` (unbuilt-seat repair and the goal-local lane).

const fs = require('node:fs');
const path = require('node:path');
const { pipelineMinted, PLANNING_SEATS } = require('./door');
const unbuilt = require('./unbuilt-seats');

const PLANNING_MODULE = 'meta';
const PLANNING_COMPONENT = 'planning';
const PLANNING_WORKFLOW = 'plan-console';

class Refusal extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

// The workflow manifest is the SOURCE OF TRUTH for the planning seat ids —
// `materialize-seats.py --workflow W` resolves exactly `<component>/workflows/<W>/<W>.csv`
// and writes that file's `Seat/workflow` column onto taskforce.csv. `planning/door.js`'s
// `pipeline-seats.json` mirrors that column and is read by `argv.py`, which is what
// `path_a.py` uncasts and mints from. Divergence is not a load error: it silently mints a
// seat set the manifest cannot produce. Probe leg M byte-compares the two.
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

module.exports = {
  PLANNING_MODULE, PLANNING_COMPONENT, PLANNING_WORKFLOW, PLANNING_SEATS,
  PLANNING_MANIFEST_REL,
  Refusal, planningManifestPath, planningManifestSeats, pipelineMinted,
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
  assert.strictEqual(pipelineMinted([]), false);
  assert.strictEqual(pipelineMinted(PLANNING_SEATS.map((seat) => ({ seat }))), true);
  assert.strictEqual(pipelineMinted(PLANNING_SEATS.slice(0, 4).map((seat) => ({ seat }))), false);
  assert.deepStrictEqual(
    planningManifestSeats(path.join(__dirname, '..', '..', PLANNING_MODULE)),
    PLANNING_SEATS.slice(),
    'pipeline-seats.json has diverged from the plan-console manifest — `argv.py` would '
    + 'uncast and mint a seat set the manifest cannot produce',
  );
  console.log('queue-request selftest OK');
}
