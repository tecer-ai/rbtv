'use strict';

// -- THE SHARED ROUTING TABLE, from the daemon's side [spec-recovery §3, C-10] ------------------
//
// `ignite/supervisor/models.csv` is one file with two readers, and that is the point of moving it
// here. `cast route` asks it "which model runs a job of this class"; this module asks it "which
// models may this lane try INSTEAD, now that its own provider is transiently down". Two copies of
// that roster would be a daemon rerouting onto a model `cast` cannot launch — the same drift the
// route/catalog join exists to prevent, one level up.
//
// ⚠ THE OTHER READER IS `core/sub-agents/tool/lib/route.js` (`CSV_LOCAL`). Move this path and that
// constant in the SAME edit. The FILE is what is shared; the parse is not — route.js joins against
// `catalog.js` and ranks by class, questions this module deliberately does not ask.
//
// ⚠ THE MODE COLUMN IS `mode`, NOT `carrier`. A landed defect (launch-profiles memory 69760b69)
// was exactly this: a join filtered `r.carrier === 'cli'` and matched zero rows, hourly, for a
// day. The columns are read by NAME off the header row for that reason.

const fs = require('node:fs');
const path = require('node:path');

const TABLE_FILENAME = 'models.csv';
const DEFAULT_TABLE_PATH = path.join(__dirname, TABLE_FILENAME);

class RoutingTableError extends Error {
  constructor(message) {
    super(message);
    this.name = 'RoutingTableError';
    this.code = 'E_ROUTING_TABLE';
  }
}

function tablePath(override) {
  return path.resolve(override || DEFAULT_TABLE_PATH);
}

// Header-driven, so a column added or reordered upstream cannot silently shift a cell.
function readTable(tableFile) {
  const file = tablePath(tableFile);
  let text;
  try {
    text = fs.readFileSync(file, 'utf8');
  } catch (err) {
    throw new RoutingTableError(`the shared routing table is unreadable at ${file}: ${err.code || err.message}`);
  }
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  if (!lines.length) throw new RoutingTableError(`the shared routing table at ${file} is empty`);
  const header = lines[0].split(',').map((c) => c.trim());
  const rows = lines.slice(1).map((line, i) => {
    const cells = line.split(',');
    const row = { _line: i + 2 };
    header.forEach((c, idx) => { row[c] = (cells[idx] === undefined ? '' : cells[idx]).trim(); });
    return row;
  });
  return { file, header, rows };
}

const labelOf = (r) => `${r.harness}/${r.model}`;

// -- ELIGIBLE ALTERNATES ------------------------------------------------------------------------
//
// Eligible = the table says this row is a routing answer (`use=route`) and `cast` can launch it as
// a real process (`mode=cli`). NOT eligible: the lane's own pin (rerouting onto the model that
// just failed is not a reroute), anything already tried in THIS launch attempt (one pass, never
// two [spec-recovery §3]), and `use=panel` / `use=off` rows, which the owner has already said are
// not route verdicts.
//
// Order is the TABLE's order, which is the owner's ranking. No re-ranking here: a second opinion
// about which model is better is exactly what `cast route` owns.
function eligibleAlternates({ harness, model, tried = [] } = {}, { tableFile } = {}) {
  const skip = new Set([`${harness}/${model}`, ...tried]);
  return readTable(tableFile).rows
    .filter((r) => r.mode === 'cli' && r.use === 'route')
    .filter((r) => !skip.has(labelOf(r)))
    // A multi-level table can carry the same (harness, model) twice; a lane tries a MODEL once.
    .filter((r, i, all) => all.findIndex((x) => labelOf(x) === labelOf(r)) === i)
    .map((r) => ({ harness: r.harness, model: r.model, label: labelOf(r) }));
}

module.exports = {
  TABLE_FILENAME,
  DEFAULT_TABLE_PATH,
  RoutingTableError,
  tablePath,
  readTable,
  eligibleAlternates,
};
