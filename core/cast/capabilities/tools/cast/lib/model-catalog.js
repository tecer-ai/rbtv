'use strict';

// cast — the model catalog: reading it, writing it, and the launch check that reads it.
//
// Three files decide what a launch may name:
//   supported-models.js   what this copy of cast can launch: harness-native id, effort ladder,
//                         provider. Code.
//   models.csv, beside it the shipped model catalog: the routing columns rbtv proposes, with at
//                         least one row for every supported model.
//   <installation>/.rbtv/config/cast/models.csv
//                         the installation's model catalog. A row SELECTS its harness+model for
//                         that installation and carries its routing columns. While the file is
//                         absent the shipped model catalog is in force and every supported model
//                         is selected.
// A model that is selected and supported is launchable. A row with no supported twin is an orphan:
// never launchable, and `cast route` warns about it.
//
// The installation's file gates every launch in the installation, the daemon's included, so it is
// read strictly: cells by header name, and an unknown column, a missing mode, harness or model
// column, or a malformed row refuses with the file and the line. A skipped row would silently
// unselect a model.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { ROWS } = require('../supported-models');

const { installationRoot } = require('./installation');

const CATALOG_NAME = 'models.csv';
const SHIPPED_CATALOG = path.join(__dirname, '..', CATALOG_NAME);
const CATALOG_REL = path.join('.rbtv', 'config', 'cast', CATALOG_NAME);
const SUPPORTED_FILE = path.join(__dirname, '..', 'supported-models.js');

const COLUMNS = ['mode', 'harness', 'model', 'efforts', 'image', 'level',
  'reasoning', 'coding', 'cost', 'use', 'quality-override', 'price-override'];
// A row is nothing without these three; every other column may be absent and then reads blank.
const REQUIRED_COLUMNS = ['mode', 'harness', 'model'];

// --- reading -----------------------------------------------------------------------------------

class CatalogError extends Error {}

function unreadable(file, line, why) {
  return new CatalogError(`cannot read the model catalog ${file}${line ? ` line ${line}` : ''}: ${why}`);
}

// ponytail: split(',') — the model catalog has no quoted fields and no embedded commas; a cell
// count that differs from the header's is refused, which is also what a decimal comma produces.
// Returns the file's own line ending, its lines as written (for the writer), its header (the
// column names in the file's order) and its rows.
function parseCatalog(text, file) {
  const firstBreak = text.indexOf('\n');
  const eol = firstBreak > 0 && text[firstBreak - 1] === '\r' ? '\r\n' : '\n';
  const lines = text.split('\n').map((l) => l.replace(/\r$/, ''));
  if (lines[lines.length - 1] === '') lines.pop();
  let header = null;
  const rows = [];
  lines.forEach((line, i) => {
    if (line.trim() === '') return;
    const cells = line.split(',').map((s) => s.trim());
    if (!header) {
      const unknown = cells.find((c) => !COLUMNS.includes(c));
      if (unknown !== undefined) throw unreadable(file, i + 1, `unknown column '${unknown}' (the columns are ${COLUMNS.join(', ')})`);
      const twice = cells.find((c, idx) => cells.indexOf(c) !== idx);
      if (twice !== undefined) throw unreadable(file, i + 1, `column '${twice}' appears twice`);
      const missing = REQUIRED_COLUMNS.find((c) => !cells.includes(c));
      if (missing) throw unreadable(file, i + 1, `no '${missing}' column`);
      header = cells;
      return;
    }
    if (cells.length !== header.length) {
      throw unreadable(file, i + 1, `${cells.length} cells where the header has ${header.length}`);
    }
    const row = { _line: i + 1 };
    for (const c of COLUMNS) row[c] = '';
    header.forEach((c, idx) => { row[c] = cells[idx]; });
    const blank = REQUIRED_COLUMNS.find((c) => row[c] === '');
    if (blank) throw unreadable(file, i + 1, `blank ${blank}`);
    rows.push(row);
  });
  if (!header) throw unreadable(file, null, 'the file is empty');
  return { eol, lines, header, rows };
}

// The installation's own model catalog, or null while it has none (or there is no installation).
function ownCatalog(root) {
  const file = root ? path.join(root, CATALOG_REL) : null;
  return file && fs.existsSync(file) ? file : null;
}

// The model catalog in force for an installation root (null = no installation): its own file when
// present, else the shipped one. Throws a CatalogError naming the file and the line.
function loadSelection(root) {
  const own = ownCatalog(root);
  const file = own || SHIPPED_CATALOG;
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch (e) { throw unreadable(file, null, e.message); }
  const { eol, lines, header, rows } = parseCatalog(text, file);
  // A file the installation does not have yet is written with this machine's line ending.
  return { root, file, shipped: !own, eol: own ? eol : os.EOL, lines, header, rows };
}

// --- writing -----------------------------------------------------------------------------------

// Replaces the installation's model catalog in one step: the lines go to a temporary file beside
// it, which is then renamed over it, so a reader never sees a half-written table. `eol` is the
// line ending loadSelection reported.
function saveSelection(root, lines, eol) {
  const file = path.join(root, CATALOG_REL);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.${process.pid}.tmp`;
  try {
    fs.writeFileSync(temporary, lines.map((l) => `${l}${eol}`).join(''), 'utf8');
    fs.renameSync(temporary, file);
  } catch (e) {
    fs.rmSync(temporary, { force: true });
    throw e;
  }
  return file;
}

// --- the join and the launch check -------------------------------------------------------------

// The supported twin of a harness+model, by the short model name; undefined for an orphan.
function supportedRow(harness, model) {
  return ROWS.find((r) => r.harness === harness && r.model === model);
}

// naive scoring: longest common prefix length, +100 if either string contains the other
function suggest(input, candidates) {
  let best = null;
  let bestScore = -1;
  for (const c of candidates) {
    let i = 0;
    while (i < input.length && i < c.length && input[i] === c[i]) i++;
    let score = i;
    if (c.includes(input) || input.includes(c)) score += 100;
    if (score > bestScore) {
      bestScore = score;
      best = c;
    }
  }
  return best;
}

// A refusal: `message` is the whole text, `code` names the case and `next` is its one next command.
function refusal(code, lines, next) {
  return Object.assign(new Error([...lines, 'Nothing changed.', next].join('\n')), { code, lines, next });
}

// The refusal for a harness+model that is neither supported nor selected: it names the closest
// supported model of that harness, by its name or by the harness's own id for it.
function notSupported(harness, model) {
  const near = ROWS.filter((r) => r.harness === harness);
  const guess = suggest(model, near.flatMap((r) => [r.model, r.id]));
  return refusal('not-supported', [`refused: '${harness} ${model}' is not a model cast supports`,
    ...(near.length ? [`did you mean '${near.find((r) => r.model === guess || r.id === guess).model}'?`] : [])],
  'cast models list --supported');
}

// The launch check: returns when `harness model` is launchable in the installation that holds
// `from`, else throws a refusal. While the installation has no model catalog of its own, every
// supported model is selected and nothing is read.
function gate(harness, model, from) {
  const root = installationRoot(from);
  const file = ownCatalog(root);
  const supported = supportedRow(harness, model);
  let selected = !!supported;
  if (file) {
    let selection;
    try { selection = loadSelection(root); } catch (e) {
      if (!(e instanceof CatalogError)) throw e;
      throw refusal('catalog-unreadable', [`refused: ${e.message}`], 'cast models list --catalog');
    }
    selected = selection.rows.some((r) => r.harness === harness && r.model === model);
  }
  if (!supported && !selected) throw notSupported(harness, model);
  if (!supported) {
    throw refusal('orphan', [`refused: '${harness} ${model}' is selected in ${file} but this copy of cast does not support it (${SUPPORTED_FILE})`,
      'the daemon runs its own deployed copy of rbtv: deploy a commit that supports it'], `cast models remove ${harness} ${model}`);
  }
  if (!selected) {
    throw refusal('not-selected', [`refused: '${harness} ${model}' is not selected in ${root}`, `model catalog: ${file}`],
      `cast models add ${harness} ${model}`);
  }
}

module.exports = {
  CATALOG_REL, SHIPPED_CATALOG, COLUMNS, CatalogError,
  parseCatalog, loadSelection, saveSelection, supportedRow, suggest, notSupported, gate,
};
