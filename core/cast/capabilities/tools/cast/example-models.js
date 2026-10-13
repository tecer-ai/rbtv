'use strict';

// Example models for the test suites: a supported model picked by a property it has, never by
// its name, so that adding, replacing or removing a supported model edits no test. A suite states
// the property its arm depends on; when no supported model has it any more, `example` fails with
// that property, which names the arm that lost its subject.
//
// Each example is one row of supported-models.js joined with its row of the shipped models.csv:
//   harness, model, mode, id, rungs, provider   from supported-models.js
//   efforts, image, level, reasoning, coding, cost   the shipped cells, as written (strings)
// The installer's Python selftests read the same list through `node example-models.js`.

const { ROWS } = require('./supported-models');
const { loadSelection } = require('./lib/model-catalog');

const shipped = new Map(loadSelection(null).rows.map((r) => [`${r.harness}/${r.model}`, r]));
const EXAMPLES = ROWS.map((r) => ({ ...shipped.get(`${r.harness}/${r.model}`), ...r, rungs: r.rungs.slice() }));

// Every supported model with the property, in the order of supported-models.js.
function examples(has = () => true) {
  return EXAMPLES.filter(has);
}

// The first supported model with the property. `what` says the property in words, for the failure.
// `not` lists examples already taken, for an arm that needs two different models.
function example(what, has, not = []) {
  const found = EXAMPLES.find((m) => has(m) && !not.includes(m));
  if (!found) throw new Error(`no supported model is ${what}: the arm that asked has lost its subject`);
  return found;
}

module.exports = { example, examples };

if (require.main === module) process.stdout.write(`${JSON.stringify(EXAMPLES)}\n`);
