'use strict';

// cast — the fallback of a launch: the models a launch runs, one after another, when its own
// model fails to start.
//
// The installation turns it on and says how to rank, in its defaults (lib/defaults.js, key
// `fallback`: off, price or quality). The candidates are the other models of the failed model's
// level in the model catalog that `cast route` may name and whose login is present, ranked as
// `cast route` ranks them. A launch tries them in that order while each one fails to start, and
// never leaves the level: when none starts, it stops and names the model it would take from the
// next level down.
//
// A start failure is the only trigger: the harness could not be started, or it exited with a
// failure inside the start window. A failure after the window may follow work the agent already
// did, and a second run would repeat that work, so the launch ends with that failure.

const { lookupModel, resolveEffort, shortName } = require('./core');
const { DefaultsError, loadDefaults } = require('./defaults');
const { installationRoot } = require('./installation');
const { CatalogError, loadSelection } = require('./model-catalog');
const { LEVELS, isAvailable, joinCatalog, pick } = require('./route');

// Measured 2026-10-07: a model the harness cannot reach ends claude, codex and opencode with
// exit 1 in 2.4 to 3.2 seconds. Measured 2026-10-08: a provider's spending limit ends opencode
// with exit 1 in about 4 seconds.
const START_WINDOW_MS = 15_000;

// `out` is how one attempt ended: `error` when the harness could not be started, else its exit
// `code`, the `signal` that ended it if one did, and `elapsedMs` since the attempt began.
function startFailure(out) {
  if (out.error) return true;
  return out.code !== 0 && !out.signal && out.elapsedMs < START_WINDOW_MS;
}

// The dial number (1-5) an effort stands for on its own model, so that another model's ladder can
// take it. A number is itself. A rung word is its place on the ladder, and the top rung is 5, so
// the highest effort stays the highest. A model with no dial gives no place: 3, the middle.
function dial(spec, effort) {
  if (Number.isInteger(effort)) return effort;
  const rungs = spec.effort && !spec.effort.inert ? spec.effort.rungs : [];
  const at = rungs.indexOf(effort);
  if (at === -1) return 3;
  return at === rungs.length - 1 ? 5 : at + 1;
}

// The models of one level a fallback may run, best first by `optimize`, without `skip`. A model
// listed at two levels has two rows and one place per level. A fallback does not know its task,
// so quality ranks on the two scores added.
function ranked(rows, level, optimize, root, skip) {
  const pool = rows.filter((r) => r.level === level && r.mode === 'cli' && r.use === 'route'
    && !(r.harness === skip.harness && r.model === skip.model) && isAvailable(r.spec, root));
  return pick(pool, optimize, 'both', [level], []);
}

// What a launch of `harness model` does when the model fails to start, in the installation that
// holds `from`, at the effort the launch asked for (a dial number, or the model's own rung word):
//   null       the installation's fallback is off, or the model catalog gives the model no level;
//   {problem}  the defaults or the model catalog cannot be read;
//   else       {level, optimize, candidates, below}: the launch values of each candidate in the
//              order to try them, and the best model of the next level down that holds one
//              (null when no level below does).
function fallbackPlan(harness, model, effort, from) {
  const root = installationRoot(from);
  let optimize;
  let rows;
  try {
    optimize = loadDefaults(root).fallback;
    if (optimize === 'off') return null;
    rows = joinCatalog(loadSelection(root).rows, []);
  } catch (e) {
    if (!(e instanceof DefaultsError) && !(e instanceof CatalogError)) throw e;
    return { problem: e.message };
  }
  const own = lookupModel(harness, model, from);
  const failed = { harness, model: shortName(harness, own.modelId) };
  // A model listed at two levels falls back inside the higher one.
  const level = LEVELS.find((l) => rows.some((r) => r.harness === failed.harness && r.model === failed.model && r.level === l));
  if (!level) return null;
  const number = dial(own.spec, effort);
  const launchValues = (row) => {
    const found = lookupModel(row.harness, row.model, from);
    const resolved = resolveEffort(found.spec, number);
    return { harness: row.harness, model: row.model, modelId: found.modelId, effort: number,
      effortWord: resolved.word, effortArgv: resolved.argv };
  };
  let below = null;
  for (const lower of LEVELS.slice(LEVELS.indexOf(level) + 1)) {
    const [best] = ranked(rows, lower, optimize, root, failed);
    if (best) { below = { level: lower, harness: best.harness, model: best.model }; break; }
  }
  return { level, optimize, candidates: ranked(rows, level, optimize, root, failed).map(launchValues), below };
}

const nameOf = (m) => `${m.harness} ${m.model}`;

// The words that close a launch whose level is used up: what was tried, and the model of the
// next level down, which is named and never launched.
function exhausted(plan, tried) {
  const lines = [`no model of level ${plan.level} started: tried ${tried.map(nameOf).join(', ')}`];
  lines.push(plan.below
    ? `the next model by ${plan.optimize} is one level down (${plan.below.level}) and was not launched: ${nameOf(plan.below)}`
    : `no level below ${plan.level} holds a model to launch`);
  return lines;
}

module.exports = { START_WINDOW_MS, startFailure, dial, fallbackPlan, exhausted, nameOf };
