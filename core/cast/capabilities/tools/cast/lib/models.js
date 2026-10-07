'use strict';

// cast — `cast models`: the models of the installation that holds the current folder.
//   cast models list [--selected | --supported | --catalog] [--json]
//   cast models add HARNESS MODEL [--dry-run] [--json]
//   cast models remove HARNESS MODEL [--force] [--dry-run] [--json]
// `list` only reads. `add` and `remove` change one file, the installation's model catalog
// (lib/model-catalog.js reads and writes it); every result names the installation and that file.

const fs = require('fs');
const path = require('path');
const { ROWS } = require('../supported-models');

const { agentsFolder } = require('./agent');
const { EFFORT_RULE, effortMap, resolveEffort } = require('./core');
const { installationRoot } = require('./installation');
const { CATALOG_REL, COLUMNS, CatalogError, SHIPPED_CATALOG, loadSelection, notSupported, saveSelection, supportedRow } = require('./model-catalog');
const { isAvailable, readJson } = require('./route');

const USAGE = [
  'cast models list [--selected | --supported | --catalog] [--json]',
  'cast models add HARNESS MODEL [--dry-run] [--json]',
  'cast models remove HARNESS MODEL [--force] [--dry-run] [--json]',
];
const VERBS = ['list', 'add', 'remove'];
const VIEWS = ['selected', 'supported', 'catalog'];
const JSON_USAGE = 'Pass the NUMBER (integer 1-5) as <effort>, not the word — example: '
  + 'cast opencode glm-5.3 2 -p "hello". rungs are labels only; each model\'s effort_numbers maps '
  + 'a word to the number that selects it. A model with mode api runs through cast api.';
// Where Ignite keeps the Dreamer's model, the one user of a model outside an agent.json.
const IGNITE_CONFIG_REL = path.join('.rbtv', 'config', 'ignite', 'config.json');

// --- refusals and the two lines every result starts with ---------------------------------------

// A refusal ends the command at exit 2: text on standard error, or under --json one value on
// standard output, `{error, message, next}`.
function refuse(json, code, lines, next, closing = 'Nothing changed.') {
  if (json) {
    process.stdout.write(`${JSON.stringify({ error: code, message: lines.join('\n'), next })}\n`);
  } else {
    process.stderr.write(`cast: refused: ${[...lines, closing, next].join('\n')}\n`);
  }
  return process.exit(2);
}

// The installation of the current folder and its model catalog in force.
function context(json, closing) {
  const root = installationRoot(process.cwd());
  try { return loadSelection(root); } catch (e) {
    if (!(e instanceof CatalogError)) throw e;
    const file = root ? path.join(root, CATALOG_REL) : SHIPPED_CATALOG;
    return refuse(json, 'catalog-unreadable', [e.message], `correct ${file}, then run the same command again`, closing);
  }
}

// How an installation that reads the shipped model catalog gets one of its own.
const ownFileComesFrom = (root) => `The installation's own file is created by the first cast models remove, or by copying ${SHIPPED_CATALOG} to ${path.join(root, CATALOG_REL)}.`;

function headLines(selection) {
  const shipped = `${selection.file} (shipped with cast: every supported model is selected)`;
  if (!selection.root) return [`installation: none above ${process.cwd()}`, `model catalog: ${shipped}`];
  return [`installation: ${selection.root}`,
    ...(selection.shipped ? [`model catalog: ${shipped}`, ownFileComesFrom(selection.root)]
      : [`model catalog: ${selection.file}`])];
}

const ownFile = (selection) => (selection.shipped ? null : selection.file);
const isRow = (harness, model) => (r) => r.harness === harness && r.model === model;
const publicRow = (row) => Object.fromEntries(COLUMNS.map((c) => [c, row[c]]));

// --- list --------------------------------------------------------------------------------------

// A supported model's effort ladder in the shape lib/core.js walks: a cli row's rungs, an api
// row's own reasoning modes.
function ladder(row) {
  const rungs = row.mode === 'api' ? row.depths : row.rungs;
  return rungs.length ? { rungs } : { inert: true };
}

// word -> the SMALLEST number that selects it, read off resolveEffort itself.
function effortNumbers(row) {
  const effort = { ...ladder(row), flag: () => [] };
  const numbers = {};
  for (let n = 1; n <= 5; n += 1) {
    const { word } = resolveEffort({ effort }, n);
    if (word && !(word in numbers)) numbers[word] = n;
  }
  return numbers;
}

// Every supported model, cli and api, with whether the installation selects it: by rule while it
// has no model catalog of its own, else by a row of that file.
function supportedModels(selection) {
  return ROWS.map((row) => ({
    harness: row.harness,
    model: row.model,
    mode: row.mode,
    rungs: (ladder(row).rungs || []).slice(),
    effort_numbers: effortNumbers(row),
    selected: selection.shipped || selection.rows.some(isRow(row.harness, row.model)),
  }));
}

const orphans = (selection) => selection.rows.filter((r) => !supportedRow(r.harness, r.model));

function table(header, rows) {
  const width = header.map((h, i) => Math.max(h.length, ...rows.map((r) => r[i].length)));
  return [header, ...rows].map((r) => `  ${r.map((cell, i) => cell.padEnd(width[i])).join('  ').trimEnd()}`);
}

function listModels(selection, view, json) {
  const all = supportedModels(selection);
  const models = view === 'selected' ? all.filter((m) => m.selected) : all;
  if (json) {
    return { installation: selection.root, selection: ownFile(selection), view, models, usage: JSON_USAGE };
  }
  const byName = new Map(ROWS.map((row) => [`${row.harness} ${row.model}`, row]));
  const cells = (m) => [m.harness, m.model, ...(view === 'supported' ? [m.selected ? 'yes' : 'no'] : []),
    effortMap(ladder(byName.get(`${m.harness} ${m.model}`)))];
  const lines = [...headLines(selection), ''];
  if (models.length) {
    lines.push(...table(['harness', 'model', ...(view === 'supported' ? ['selected'] : []), 'effort'], models.map(cells)), '');
  }
  lines.push(`${all.filter((m) => m.selected).length} of ${all.length} supported models are selected.`);
  const strays = orphans(selection);
  if (strays.length) {
    lines.push(`${strays.length} row${strays.length === 1 ? '' : 's'} of the model catalog name a model this copy of cast does not support: cast models list --catalog`);
  }
  lines.push(EFFORT_RULE);
  if (models.some((m) => m.mode === 'api')) lines.push('A model of harness api runs through cast api MODEL EFFORT, not as a harness launch.');
  if (view !== 'supported' && all.some((m) => !m.selected)) lines.push('The models not selected: cast models list --supported');
  return lines;
}

// Every row of the model catalog in force, a row with no supported model included: the owner
// filling the file needs to see a row cast route is ignoring.
function listCatalog(selection, json) {
  const rows = selection.rows.map((c) => {
    const spec = supportedRow(c.harness, c.model);
    return { ...publicRow(c), launchable: spec ? 'yes' : 'no', available: spec ? String(isAvailable(spec, selection.root)) : '-' };
  });
  if (json) return { installation: selection.root, source: selection.file, rows };
  const cols = [...COLUMNS, 'launchable', 'available'];
  return [...headLines(selection), '', ...table(cols, rows.map((r) => cols.map((c) => (r[c] === '' ? '-' : r[c]))))];
}

// --- add ---------------------------------------------------------------------------------------

const USE_NOTE = {
  route: 'launchable, and cast route may name it',
  panel: 'launchable, listed for panels, never named by cast route',
  off: 'launchable, never named by cast route: edit the use column to route it',
};

// The short name of a supported model given by that name or by the harness's own id; a name cast
// does not support comes back as typed.
function shortModel(harness, model) {
  const row = ROWS.find((r) => r.harness === harness && (r.model === model || r.id === model));
  return row ? row.model : model;
}

function needInstallation(selection, json) {
  if (selection.root) return;
  refuse(json, 'no-installation', [`no rbtv installation above ${process.cwd()} (no .rbtv/config/install.json)`,
    'the selected models belong to an installation; outside one, every supported model is selected'],
  'rbtv configure --harness claude --guidance none --target FOLDER');
}

function addModel(selection, harness, model, { dryRun, json }) {
  needInstallation(selection, json);
  if (!supportedRow(harness, model)) {
    const no = notSupported(harness, model);
    refuse(json, no.code, no.lines.map((l) => l.replace(/^refused: /, '')), no.next);
  }
  const result = { installation: selection.root, selection: ownFile(selection), harness, model, changed: false, added: [], dry_run: dryRun };
  const done = (lines) => (json ? result : [...headLines(selection), '', ...lines]);
  if (selection.shipped) {
    return done([`already selected: '${harness} ${model}'`,
      'No model catalog was saved: while this installation has none of its own, every supported model is selected.',
      ownFileComesFrom(selection.root)]);
  }
  if (selection.rows.some(isRow(harness, model))) return done([`already selected: '${harness} ${model}'`, 'Nothing changed.']);

  const shipped = loadSelection(null);
  const rows = shipped.rows.filter(isRow(harness, model));
  if (!rows.length) {
    refuse(json, 'no-shipped-row', [`the shipped model catalog ${shipped.file} has no row for '${harness} ${model}'`,
      'that is a defect in rbtv: it holds a row for every supported model'],
    `write the row by hand in ${selection.file}`);
  }
  // Written under the installation's own header, which may hold fewer columns in another order.
  const added = rows.map((row) => selection.header.map((c) => row[c]).join(','));
  if (!dryRun) saveSelection(selection.root, [...selection.lines, ...added], selection.eol);
  Object.assign(result, { changed: !dryRun, added: rows.map(publicRow) });
  const lines = [`${dryRun ? 'would select' : 'selected'}: '${harness} ${model}', ${added.length} row${added.length === 1 ? '' : 's'} ${dryRun ? 'to add' : 'added'}`];
  rows.forEach((row, i) => {
    const use = selection.header.includes('use') && row.use ? row.use : 'route';
    lines.push(`  ${added[i]}`, `      use=${use}: ${USE_NOTE[use]}`);
  });
  lines.push(dryRun ? 'Nothing changed: this was a dry run.' : `launch it: cast ${harness === 'api' ? `api ${model} 1` : `${harness} ${model} 1`} -p "reply with exactly: ok"${harness === 'api' ? ' --output-folder out/' : ''}`);
  return done(lines);
}

// --- remove ------------------------------------------------------------------------------------

// Who in the installation still launches `harness model`: its agents, and the Dreamer when it is
// on. `unread` names what could not be read to tell.
function usersOf(root, harness, model) {
  const users = [];
  const unread = [];
  const names = (value) => value && value.harness === harness && shortModel(harness, String(value.model)) === model;
  const folder = agentsFolder(root);
  for (const name of fs.existsSync(folder) ? fs.readdirSync(folder).sort() : []) {
    const file = path.join(folder, name, 'agent.json');
    if (!fs.existsSync(file)) continue;
    const record = readJson(file);
    if (!record) unread.push(`${file} cannot be read`);
    else if (names(record)) users.push({ kind: 'agent', name, file });
  }
  const file = path.join(root, IGNITE_CONFIG_REL);
  if (fs.existsSync(file)) {
    const config = readJson(file);
    if (!config) unread.push(`${file} cannot be read`);
    else if (config.dreamer && config.dreamer.enabled === true) {
      if (!config.dreamer.model) unread.push(`the Dreamer is on and ${file} names no dreamer.model`);
      else if (names(config.dreamer.model)) users.push({ kind: 'dreamer', name: 'the Dreamer', file });
    }
  }
  return { users, unread };
}

const userLine = (user) => (user.kind === 'agent' ? `agent ${user.name} (${user.file})` : `${user.name} (${user.file}, dreamer.model)`);

function removeModel(selection, harness, model, { force, dryRun, json }) {
  needInstallation(selection, json);
  const file = path.join(selection.root, CATALOG_REL);
  const rows = selection.rows.filter(isRow(harness, model));
  const result = { installation: selection.root, selection: file, harness, model, changed: false, removed: [],
    copied_shipped: false, users: [], not_checked: [], dry_run: dryRun };
  if (!rows.length) {
    Object.assign(result, { selection: ownFile(selection) });
    return json ? result : [...headLines(selection), '', `not selected: '${harness} ${model}'`,
      ...(supportedRow(harness, model) ? [] : ['It is not a model cast supports either: cast models list --supported']), 'Nothing changed.'];
  }
  const { users, unread } = usersOf(selection.root, harness, model);
  if (users.length && !force) {
    refuse(json, 'in-use', [`'${harness} ${model}' is still used in ${selection.root}`, ...users.map((u) => `  ${userLine(u)}`),
      'give each another model first (an agent: rbtv agent configure AGENT --model MODEL), or remove it anyway with --force'],
    `cast models remove ${harness} ${model} --force`);
  }
  const gone = new Set(rows.map((row) => row._line - 1));
  if (!dryRun) saveSelection(selection.root, selection.lines.filter((_, i) => !gone.has(i)), selection.eol);
  const notChecked = [...unread, `agents kept outside ${agentsFolder(selection.root)}`,
    'settings of a component that name a model, such as a file in an agent\'s config folder'];
  Object.assign(result, { changed: !dryRun, removed: rows.map(publicRow), copied_shipped: selection.shipped, users, not_checked: notChecked });
  if (json) return result;
  const lines = [`installation: ${selection.root}`, `model catalog: ${file}`, ''];
  if (selection.shipped) {
    lines.push(`${dryRun ? 'would copy' : 'copied'} the model catalog shipped with cast to that file first: every other supported model stays selected.`);
  }
  lines.push(`${dryRun ? 'would unselect' : 'unselected'}: '${harness} ${model}', ${rows.length} row${rows.length === 1 ? '' : 's'} ${dryRun ? 'to remove' : 'removed'}`,
    ...rows.map((row) => `  ${selection.lines[row._line - 1]}`));
  if (users.length) lines.push(`still naming it, so ${dryRun ? 'these would be' : 'these are now'} refused at launch:`, ...users.map((u) => `  ${userLine(u)}`));
  lines.push('not checked:', ...notChecked.map((n) => `  ${n}`),
    dryRun ? 'Nothing changed: this was a dry run.' : `select it again: cast models add ${harness} ${model}`);
  return lines;
}

// --- the words of `cast models` ----------------------------------------------------------------

function modelsArgs(args) {
  const json = args.includes('--json');
  const bad = (what, why, closing) => refuse(json, 'invalid-arguments', [what, why], 'cast models -h', closing);
  const verb = args[0];
  if (verb === undefined || verb.startsWith('-')) bad('cast models needs a verb', `choose from ${VERBS.join(', ')}`);
  if (!VERBS.includes(verb)) bad(`unknown verb 'models ${verb}'`, `choose from ${VERBS.join(', ')}`);
  const closing = verb === 'list' ? 'Nothing was listed.' : 'Nothing changed.';
  const flags = verb === 'list' ? ['--json', ...VIEWS.map((v) => `--${v}`)]
    : ['--json', '--dry-run', ...(verb === 'remove' ? ['--force'] : [])];
  const given = new Set();
  const named = [];
  for (const a of args.slice(1)) {
    if (!a.startsWith('-')) named.push(a);
    else if (flags.includes(a)) given.add(a);
    else bad(`'${a}' is not a cast models ${verb} option`, `cast models ${verb} takes ${flags.join(', ')}`, closing);
  }
  if (verb === 'list') {
    if (named.length) bad(`cast models list takes no name, got '${named[0]}'`, 'it lists every model of one view', closing);
    const views = VIEWS.filter((v) => given.has(`--${v}`));
    if (views.length > 1) bad(`${views.map((v) => `--${v}`).join(' and ')} are different lists`, 'pass one of them', closing);
    return { verb, json, view: views[0] || 'selected', closing };
  }
  if (named.length !== 2) {
    bad(`cast models ${verb} takes a harness and a model, got ${named.length} name${named.length === 1 ? '' : 's'}`,
      `as in a launch: cast models ${verb} claude haiku-4-5`, closing);
  }
  return { verb, json, harness: named[0], model: shortModel(named[0], named[1]),
    dryRun: given.has('--dry-run'), force: given.has('--force'), closing };
}

function runModels(args) {
  const asked = modelsArgs(args);
  const selection = context(asked.json, asked.closing);
  let out;
  if (asked.verb === 'add') out = addModel(selection, asked.harness, asked.model, asked);
  else if (asked.verb === 'remove') out = removeModel(selection, asked.harness, asked.model, asked);
  else out = asked.view === 'catalog' ? listCatalog(selection, asked.json) : listModels(selection, asked.view, asked.json);
  process.stdout.write(asked.json ? `${JSON.stringify(out)}\n` : `${out.join('\n')}\n`);
  process.exit(0);
}

module.exports = { USAGE, ownFileComesFrom, runModels };
