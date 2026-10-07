'use strict';

// cast — `cast models`: the models of the installation that holds the current folder.
//   cast models list [--selected | --supported | --catalog] [--json]
//   cast models add HARNESS MODEL [--dry-run] [--json]
//   cast models remove HARNESS MODEL [--force] [--dry-run] [--json]
//   cast models set HARNESS MODEL [--use V] [--quality-override V] [--price-override V] [--level L]
//   cast models update [HARNESS MODEL] [--dry-run] [--json]
//   cast models defaults [--route V] [--fallback V] [--dry-run] [--json]
// `list` only reads. `add`, `remove`, `set` and `update` change one file, the installation's model
// catalog (lib/model-catalog.js reads and writes it); `defaults` changes the installation's
// defaults (lib/defaults.js). Every result names the installation and the file.

const fs = require('fs');
const path = require('path');
const { ROWS } = require('../supported-models');

const { agentsFolder } = require('./agent');
const { EFFORT_RULE, effortMap, resolveEffort } = require('./core');
const { DefaultsError, VALUES: DEFAULT_VALUES, loadDefaults, saveDefaults } = require('./defaults');
const { installationRoot } = require('./installation');
const { CATALOG_REL, COLUMNS, CatalogError, OWN_COLUMNS, SHIPPED_CATALOG, SHIPPED_COLUMNS, editCells, loadSelection, notSupported, saveSelection, supportedRow } = require('./model-catalog');
const { isAvailable, readJson } = require('./route');

const USAGE = [
  'cast models list [--selected | --supported | --catalog] [--json]',
  'cast models add HARNESS MODEL [--dry-run] [--json]',
  'cast models remove HARNESS MODEL [--force] [--dry-run] [--json]',
  'cast models set HARNESS MODEL [--use route|panel|off] [--quality-override Y|N] [--price-override Y|N] [--level LEVEL] [--dry-run] [--json]',
  'cast models update [HARNESS MODEL] [--dry-run] [--json]',
  'cast models defaults [--route price|quality] [--fallback off|price|quality] [--dry-run] [--json]',
];
const VERBS = ['list', 'add', 'remove', 'set', 'update', 'defaults'];
// The options of each verb that take a value, with the values each accepts (null = any word).
const VALUED = {
  set: { '--use': ['route', 'panel', 'off'], '--quality-override': ['Y', 'N'], '--price-override': ['Y', 'N'], '--level': null },
  defaults: { '--route': DEFAULT_VALUES.route, '--fallback': DEFAULT_VALUES.fallback },
};
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
const ownFileComesFrom = (root) => `The installation's own file, ${path.join(root, CATALOG_REL)}, is created by the first cast models set or cast models remove.`;

function headLines(selection) {
  const shipped = `${selection.file} (shipped with cast: every supported model is selected)`;
  if (!selection.root) return [`installation: none above ${process.cwd()}`, `model catalog: ${shipped}`];
  return [`installation: ${selection.root}`,
    ...(selection.shipped ? [`model catalog: ${shipped}`, ownFileComesFrom(selection.root)]
      : [`model catalog: ${selection.file}`])];
}

// The installation's defaults as the line a list shows under its head lines, and as a value.
function defaultsOf(root) {
  try {
    const d = loadDefaults(root);
    const from = Object.keys(d.own).length ? d.file : "cast's own values";
    return { value: { route: d.route, fallback: d.fallback, file: Object.keys(d.own).length ? d.file : null },
      line: `defaults: cast route ranks by ${d.route}; fallback ${d.fallback === 'off' ? 'is off' : `ranks by ${d.fallback}`} (${from}; cast models defaults)` };
  } catch (e) {
    if (!(e instanceof DefaultsError)) throw e;
    return { value: { problem: e.message }, line: `defaults: ${e.message}` };
  }
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
  const defaults = defaultsOf(selection.root);
  if (json) {
    return { installation: selection.root, selection: ownFile(selection), defaults: defaults.value, view, models, usage: JSON_USAGE };
  }
  const byName = new Map(ROWS.map((row) => [`${row.harness} ${row.model}`, row]));
  const cells = (m) => [m.harness, m.model, ...(view === 'supported' ? [m.selected ? 'yes' : 'no'] : []),
    effortMap(ladder(byName.get(`${m.harness} ${m.model}`)))];
  const lines = [...headLines(selection), defaults.line, ''];
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
  const defaults = defaultsOf(selection.root);
  if (json) return { installation: selection.root, source: selection.file, defaults: defaults.value, rows };
  const cols = [...COLUMNS, 'launchable', 'available'];
  return [...headLines(selection), defaults.line, '', ...table(cols, rows.map((r) => cols.map((c) => (r[c] === '' ? '-' : r[c]))))];
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

// --- set ---------------------------------------------------------------------------------------

// The refusal for a verb that acts on a selected model when the installation has no row for it.
function needSelected(selection, harness, model, json) {
  const rows = selection.rows.filter(isRow(harness, model));
  if (rows.length) return rows;
  return refuse(json, 'not-selected', [`'${harness} ${model}' is not selected in ${selection.root}`,
    ...(supportedRow(harness, model) ? [] : ['It is not a model cast supports either: cast models list --supported'])],
  `cast models add ${harness} ${model}`);
}

// Writes the cells an installation owns: `use`, which holds for every level of a model, and the
// two overrides, which belong to one level.
function setModel(selection, harness, model, { values, dryRun, json }) {
  needInstallation(selection, json);
  const rows = needSelected(selection, harness, model, json);
  const file = path.join(selection.root, CATALOG_REL);
  const level = values['--level'];
  const overrides = ['--quality-override', '--price-override'].filter((f) => values[f] !== undefined);
  const next = `cast models set ${harness} ${model}`;
  if (values['--use'] === undefined && !overrides.length) {
    refuse(json, 'invalid-arguments', ['cast models set needs a value to set', 'give --use, --quality-override or --price-override'], `${next} --use off`);
  }
  const levels = rows.map((r) => r.level);
  if (level !== undefined && !overrides.length) {
    refuse(json, 'invalid-arguments', ['--level goes with an override', '--use holds for every level of a model'], `${next} --use ${values['--use']}`);
  }
  if (level !== undefined && !levels.includes(level)) {
    refuse(json, 'no-such-level', [`'${harness} ${model}' has no row at level ${level}`, `its level${levels.length === 1 ? ' is' : 's are'} ${levels.join(', ')}`],
      `${next} --level ${levels[0]} ${overrides.map((f) => `${f} ${values[f]}`).join(' ')}`);
  }
  if (overrides.length && rows.length > 1 && level === undefined) {
    refuse(json, 'level-needed', [`'${harness} ${model}' has rows at levels ${levels.join(' and ')}`, 'an override belongs to one level: name it with --level'],
      `${next} --level ${levels[0]} ${overrides.map((f) => `${f} ${values[f]}`).join(' ')}`);
  }
  const edits = [];
  if (values['--use'] !== undefined) for (const row of rows) edits.push({ row, column: 'use', value: values['--use'] });
  for (const flag of overrides) {
    edits.push({ row: level === undefined ? rows[0] : rows.find((r) => r.level === level), column: flag.slice(2), value: values[flag] });
  }
  const changes = edits.filter((e) => e.row[e.column] !== e.value);
  const set = changes.map((e) => ({ level: e.row.level, column: e.column, from: e.row[e.column], to: e.value }));
  const result = { installation: selection.root, selection: file, harness, model, changed: false, set, copied_shipped: false, dry_run: dryRun };
  const head = [`installation: ${selection.root}`, `model catalog: ${file}`, ''];
  if (!changes.length) {
    Object.assign(result, { selection: ownFile(selection) });
    return json ? result : [...headLines(selection), '', `already set: '${harness} ${model}' ${edits.map((e) => `${e.column}=${e.value}`).join(', ')}`, 'Nothing changed.'];
  }
  if (!dryRun) saveSelection(selection.root, editCells(selection, changes), selection.eol);
  Object.assign(result, { changed: !dryRun, copied_shipped: selection.shipped });
  if (json) return result;
  if (selection.shipped) {
    head.push(`${dryRun ? 'would copy' : 'copied'} the model catalog shipped with cast to that file first: every supported model stays selected.`);
  }
  return [...head, `${dryRun ? 'would set' : 'set'}: '${harness} ${model}'`,
    ...set.map((c) => `  level ${c.level || '-'}  ${c.column}  ${c.from || '-'} -> ${c.to}`),
    dryRun ? 'Nothing changed: this was a dry run.' : 'cast route and a fallback read the new values from their next call.'];
}

// --- update ------------------------------------------------------------------------------------

// Where the installation's model catalog differs from the shipped one in the cells rbtv proposes
// (SHIPPED_COLUMNS), for every model or for one. A row is compared with the shipped row of the
// same model and level; a model with one row here and one there is compared whatever the levels,
// so a changed level is a difference. `unmatched` names what update leaves alone.
function catalogDrift(selection, only = null) {
  const shipped = loadSelection(null);
  const columns = SHIPPED_COLUMNS.filter((c) => selection.header.includes(c));
  const changes = [];
  const unmatched = [];
  const names = [...new Set(selection.rows.map((r) => `${r.harness} ${r.model}`))];
  for (const name of names) {
    const [harness, model] = name.split(' ');
    if (only && !(only.harness === harness && only.model === model)) continue;
    const mine = selection.rows.filter(isRow(harness, model));
    const theirs = shipped.rows.filter(isRow(harness, model));
    if (!theirs.length) { unmatched.push(`'${name}': the shipped model catalog has no row for it`); continue; }
    const pairs = [];
    const left = theirs.slice();
    const alone = [];
    for (const row of mine) {
      const at = left.findIndex((t) => t.level === row.level);
      if (at === -1) alone.push(row);
      else pairs.push([row, left.splice(at, 1)[0]]);
    }
    if (alone.length === 1 && left.length === 1) pairs.push([alone.pop(), left.pop()]);
    if (alone.length || left.length) {
      unmatched.push(`'${name}': its levels here are ${mine.map((r) => r.level || '-').join(', ')} and the shipped ones are ${theirs.map((r) => r.level || '-').join(', ')}; update adds and removes no row`);
    }
    for (const [row, source] of pairs) {
      for (const column of columns) {
        if (row[column] !== source[column]) changes.push({ row, column, value: source[column] });
      }
    }
  }
  return { changes, unmatched, shipped: shipped.file };
}

function updateModels(selection, only, { dryRun, json }) {
  needInstallation(selection, json);
  if (only) needSelected(selection, only.harness, only.model, json);
  const result = { installation: selection.root, selection: ownFile(selection), changed: false, updated: [], not_updated: [], dry_run: dryRun };
  if (selection.shipped) {
    return json ? result : [...headLines(selection), '', 'Nothing to update: this installation reads the shipped model catalog itself.', 'Nothing changed.'];
  }
  const { changes, unmatched, shipped } = catalogDrift(selection, only);
  const updated = changes.map((c) => ({ harness: c.row.harness, model: c.row.model, level: c.row.level, column: c.column, from: c.row[c.column], to: c.value }));
  Object.assign(result, { updated, not_updated: unmatched });
  const kept = `never changed by update: ${OWN_COLUMNS.join(', ')}, and which models are selected`;
  if (!changes.length) {
    return json ? result : [...headLines(selection), '', `up to date with ${shipped}${only ? `: '${only.harness} ${only.model}'` : ''}`,
      ...unmatched.map((u) => `not compared: ${u}`), 'Nothing changed.'];
  }
  if (!dryRun) saveSelection(selection.root, editCells(selection, changes), selection.eol);
  result.changed = !dryRun;
  if (json) return result;
  const width = Math.max(...updated.map((u) => `${u.harness} ${u.model}`.length));
  return [...headLines(selection), '', `${dryRun ? 'would update' : 'updated'} ${updated.length} cell${updated.length === 1 ? '' : 's'} from ${shipped}`,
    ...updated.map((u) => `  ${`${u.harness} ${u.model}`.padEnd(width)}  level ${u.level || '-'}  ${u.column}  ${u.from || '-'} -> ${u.to || '-'}`),
    ...unmatched.map((u) => `not compared: ${u}`), kept,
    dryRun ? 'Nothing changed: this was a dry run.' : 'cast route and a fallback read the new values from their next call.'];
}

// --- defaults ----------------------------------------------------------------------------------

const DEFAULT_NOTES = {
  route: 'how cast route ranks when a call gives no --optimize',
  fallback: 'how a launch picks the model that replaces one that fails to start; off = it never does',
};

function runDefaults(root, { values, dryRun, json }) {
  let defaults;
  try { defaults = loadDefaults(root); } catch (e) {
    if (!(e instanceof DefaultsError)) throw e;
    return refuse(json, 'defaults-unreadable', [e.message], `correct that file, then run the same command again`);
  }
  const asked = Object.fromEntries(Object.keys(DEFAULT_VALUES).filter((k) => values[`--${k}`] !== undefined).map((k) => [k, values[`--${k}`]]));
  const keys = Object.keys(asked);
  if (keys.length && !root) {
    refuse(json, 'no-installation', [`no rbtv installation above ${process.cwd()} (no .rbtv/config/install.json)`,
      'the defaults belong to an installation; outside one, cast uses its own values'],
    'rbtv configure --harness claude --guidance none --target FOLDER');
  }
  const changed = keys.filter((k) => defaults[k] !== asked[k] || defaults.own[k] === undefined);
  const now = dryRun ? defaults : { ...defaults, ...asked };
  if (changed.length && !dryRun) saveDefaults(root, { ...defaults.own, ...asked });
  const written = fs.existsSync(defaults.file || '') || (changed.length > 0 && !dryRun);
  const result = { installation: root, file: defaults.file, route: now.route, fallback: now.fallback,
    changed: changed.length > 0 && !dryRun, dry_run: dryRun };
  if (json) return result;
  const lines = [root ? `installation: ${root}` : `installation: none above ${process.cwd()}`,
    root ? `defaults: ${defaults.file}${written ? '' : " (not written yet: cast's own values are in force)"}` : "defaults: cast's own values", ''];
  for (const key of Object.keys(DEFAULT_VALUES)) {
    lines.push(`  ${key.padEnd(8)}  ${now[key].padEnd(7)}  ${DEFAULT_NOTES[key]} (${DEFAULT_VALUES[key].join(' | ')})`);
  }
  if (keys.length) {
    lines.push('', !changed.length ? 'Nothing changed: already set.'
      : (dryRun ? `would set: ${changed.map((k) => `${k}=${asked[k]}`).join(', ')}\nNothing changed: this was a dry run.` : `set: ${changed.map((k) => `${k}=${asked[k]}`).join(', ')}`));
  } else lines.push('', 'change one: cast models defaults --fallback price');
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
  const valued = VALUED[verb] || {};
  const flags = verb === 'list' ? ['--json', ...VIEWS.map((v) => `--${v}`)]
    : ['--json', '--dry-run', ...(verb === 'remove' ? ['--force'] : []), ...Object.keys(valued)];
  const given = new Set();
  const values = {};
  const named = [];
  for (let i = 1; i < args.length; i += 1) {
    const a = args[i];
    if (!a.startsWith('-')) named.push(a);
    else if (a in valued) {
      const value = args[i + 1];
      const allowed = valued[a];
      if (value === undefined || value.startsWith('-') || (allowed && !allowed.includes(value))) {
        bad(`${a} takes ${allowed ? `one of ${allowed.join(', ')}` : 'a value'}, got ${value === undefined ? 'nothing' : `'${value}'`}`,
          `cast models ${verb} takes ${flags.join(', ')}`, closing);
      }
      values[a] = value;
      i += 1;
    } else if (flags.includes(a)) given.add(a);
    else bad(`'${a}' is not a cast models ${verb} option`, `cast models ${verb} takes ${flags.join(', ')}`, closing);
  }
  const common = { verb, json, values, dryRun: given.has('--dry-run'), force: given.has('--force'), closing };
  if (verb === 'list') {
    if (named.length) bad(`cast models list takes no name, got '${named[0]}'`, 'it lists every model of one view', closing);
    const views = VIEWS.filter((v) => given.has(`--${v}`));
    if (views.length > 1) bad(`${views.map((v) => `--${v}`).join(' and ')} are different lists`, 'pass one of them', closing);
    return { verb, json, view: views[0] || 'selected', closing };
  }
  if (verb === 'defaults') {
    if (named.length) bad(`cast models defaults takes no name, got '${named[0]}'`, 'the defaults hold for every model of the installation', closing);
    return common;
  }
  if (verb === 'update' && named.length === 0) return common;
  if (named.length !== 2) {
    bad(`cast models ${verb} takes a harness and a model, got ${named.length} name${named.length === 1 ? '' : 's'}`,
      verb === 'update' ? 'every model: cast models update; one model, as in a launch: cast models update claude haiku-4-5'
        : `as in a launch: cast models ${verb} claude haiku-4-5`, closing);
  }
  return { ...common, harness: named[0], model: shortModel(named[0], named[1]) };
}

function runModels(args) {
  const asked = modelsArgs(args);
  let out;
  if (asked.verb === 'defaults') out = runDefaults(installationRoot(process.cwd()), asked);
  else {
    const selection = context(asked.json, asked.closing);
    if (asked.verb === 'add') out = addModel(selection, asked.harness, asked.model, asked);
    else if (asked.verb === 'remove') out = removeModel(selection, asked.harness, asked.model, asked);
    else if (asked.verb === 'set') out = setModel(selection, asked.harness, asked.model, asked);
    else if (asked.verb === 'update') out = updateModels(selection, asked.harness ? { harness: asked.harness, model: asked.model } : null, asked);
    else out = asked.view === 'catalog' ? listCatalog(selection, asked.json) : listModels(selection, asked.view, asked.json);
  }
  process.stdout.write(asked.json ? `${JSON.stringify(out)}\n` : `${out.join('\n')}\n`);
  process.exit(0);
}

module.exports = { USAGE, ownFileComesFrom, catalogDrift, runModels };
