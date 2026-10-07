'use strict';

// cast — the fallback of a launch: the second harness and model a launch runs when the first
// fails to start.
//
// The model catalog names it, in a row's `fallback-harness` and `fallback-model` cells
// (lib/model-catalog.js). A launch falls back once, and only on a start failure: the harness
// could not be started, or it exited with a failure inside the start window. A failure after the
// window may follow work the agent already did, and a second run would repeat that work, so the
// launch ends with that failure. The fallback's own failure is final: its row's fallback is not
// read.

const { lookupModel, resolveEffort, shortName } = require('./core');
const { installationRoot } = require('./installation');
const { loadSelection } = require('./model-catalog');

// Measured 2026-10-07: a model the harness cannot reach ends claude, codex and opencode with
// exit 1 in 2.4 to 3.2 seconds.
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

// The fallback of `harness model` in the installation that holds `from`, at the effort the launch
// asked for (a dial number, or the model's own rung word): null when the model catalog names
// none, {problem} when it names one that cannot be launched, else the launch values.
function fallbackOf(harness, model, effort, from) {
  let own;
  let named;
  let found;
  try {
    own = lookupModel(harness, model, from);
    const short = shortName(harness, own.modelId);
    const row = loadSelection(installationRoot(from)).rows.find((r) => r.harness === harness && r.model === short);
    if (!row || !row['fallback-harness']) return null;
    named = { harness: row['fallback-harness'], model: row['fallback-model'] };
    found = lookupModel(named.harness, named.model, from);
  } catch (e) {
    return { problem: e.message.split('\n')[0] };
  }
  const number = dial(own.spec, effort);
  const resolved = resolveEffort(found.spec, number);
  return { ...named, modelId: found.modelId, effort: number, effortWord: resolved.word, effortArgv: resolved.argv };
}

module.exports = { START_WINDOW_MS, startFailure, dial, fallbackOf };
