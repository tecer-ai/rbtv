'use strict';

// cast — `cast doctor`: what this machine can launch, read from cast's own data only.
//
// Three checks: which harness programs are on PATH, which selected models have their provider's
// login present, and whether the installation's model catalog still holds the values rbtv ships.
// Local files and the environment only: no network call, no other program started.
// Accounts, saved logins and usage limits belong to `rbtv providers`, which the report points to.

const fs = require('fs');
const { ROWS } = require('../supported-models');
const { providers: PROVIDERS } = require('../providers.json');
const { HARNESSES, fail } = require('./core');
const { installationRoot } = require('./installation');
const { CatalogError, loadSelection } = require('./model-catalog');
const { catalogDrift, ownFileComesFrom } = require('./models');
const { expandHome, loginFoundIn, readJson, unavailableReason } = require('./route');
const { findOnPath } = require('./win-exec');

const NEXT = ['rbtv providers list', 'rbtv providers usage'];

// The words of `cast doctor`: --json and nothing else. Every other word is refused, so a mistyped
// command never prints a report that looks like an answer to it.
function doctorArgs(args) {
  const refuse = (what, why) => fail(`refused: ${what}\n${why}\nNothing was checked.\ncast doctor -h`);
  let json = false;
  for (const a of args) {
    if (a === '--json') json = true;
    else if (a.startsWith('-')) refuse(`'${a}' is not a cast doctor option`, 'cast doctor takes --json only');
    else refuse(`cast doctor takes no name, got '${a}'`, 'it checks every harness and every selected model; it takes --json only');
  }
  return { json };
}

// The models the login check covers: every supported model the installation selects, cli and
// api. While the installation has no model catalog of its own, that is every supported model.
// `problem` is set, and no model is checked, when its model catalog cannot be read.
function selectedModels(root) {
  let selection;
  try { selection = loadSelection(root); } catch (e) {
    if (!(e instanceof CatalogError)) throw e;
    return { selection: null, rows: [], unsupported: 0, drift: 0, problem: e.message };
  }
  const selects = (row) => selection.rows.some((r) => r.harness === row.harness && r.model === row.model);
  return {
    selection: selection.shipped ? null : selection.file,
    rows: selection.shipped ? ROWS : ROWS.filter(selects),
    unsupported: selection.rows.filter((r) => !ROWS.some((row) => row.harness === r.harness && row.model === r.model)).length,
    // cells of the installation's own file that differ from the shipped model catalog
    drift: selection.shipped ? 0 : catalogDrift(selection).changes.length,
    problem: null,
  };
}

// A provider whose login is a set of files (providers.json `saved_login.files`): what is missing
// from them, or null when every file, and every named entry inside one, is there.
function savedLoginGap(provider) {
  for (const file of Object.values(provider.saved_login.files)) {
    const at = expandHome(file.path);
    if (!fs.existsSync(at)) return `no login file ${file.path}`;
    if (file.key) {
      const data = readJson(at);
      if (!data || !Object.prototype.hasOwnProperty.call(data, file.key)) return `${file.path} holds no '${file.key}' entry`;
    }
  }
  return null;
}

// One model's login: the presence test `cast route` uses, and for a provider with login files,
// those files too. `via` says where it was found and `reason` what is absent; neither carries a
// value.
function loginState(row, root) {
  let via = loginFoundIn(row, root);
  let reason = via === null ? unavailableReason(row) : null;
  const provider = PROVIDERS[row.provider];
  if (reason === null && provider.saved_login) {
    reason = savedLoginGap(provider);
    via = reason === null ? `login files: ${Object.values(provider.saved_login.files).map((f) => f.path).join(', ')}` : null;
  }
  return { harness: row.harness, model: row.model, provider: row.provider, login: reason === null, via, reason };
}

function runDoctor(args) {
  const { json } = doctorArgs(args);
  const root = installationRoot(process.cwd());
  const harnesses = Object.fromEntries(HARNESSES.map((name) => [name, findOnPath(name)]));
  const { selection, rows, unsupported, drift, problem } = selectedModels(root);
  const models = rows.map((row) => loginState(row, root));
  if (json) {
    process.stdout.write(`${JSON.stringify({ installation: root, selection, catalog_problem: problem, catalog_drift: drift, harnesses, models, next: NEXT })}\n`);
    process.exit(0);
  }
  const pad = (values) => Math.max(0, ...values.map((v) => v.length));
  const hw = pad([...HARNESSES, ...models.map((m) => m.harness)]);
  const mw = pad(models.map((m) => m.model));
  const lines = ['cast doctor — can this machine launch the selected models? Local files only; nothing is started.', '',
    root ? `installation: ${root}` : `installation: none above ${process.cwd()} (no environment file is read)`,
    `model catalog: ${selection || 'the one shipped with cast (every supported model is selected)'}`,
    ...(root && !selection && !problem ? [ownFileComesFrom(root)] : []),
    '', 'harnesses'];
  for (const name of HARNESSES) lines.push(`  ${name.padEnd(hw)}  ${harnesses[name] || 'MISSING'}`);
  lines.push('', 'selected models');
  if (problem) lines.push(`  none checked: ${problem}`);
  for (const m of models) {
    lines.push(`  ${m.login ? '✓' : '·'} ${m.harness.padEnd(hw)}  ${m.model.padEnd(mw)}  ${m.login ? m.via : `no login: ${m.reason}`}`);
  }
  if (!problem) lines.push(`  ${models.filter((m) => m.login).length} of ${models.length} selected models have a login present.`);
  if (unsupported) {
    lines.push(`  ${unsupported} row${unsupported === 1 ? '' : 's'} of the model catalog name a model this copy of cast does not support: cast models list --catalog`);
  }
  if (drift) {
    lines.push(`  ${drift} cell${drift === 1 ? '' : 's'} of the model catalog differ${drift === 1 ? 's' : ''} from the one shipped with cast: cast models update --dry-run`);
  }
  lines.push('', `Accounts and usage: ${NEXT.join(' · ')}`);
  process.stdout.write(`${lines.join('\n')}\n`);
  process.exit(0);
}

module.exports = { doctorArgs, runDoctor };
