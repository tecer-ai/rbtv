'use strict';

// The teambuild CORPUS READER — the ONE enumerator over the component databases.
//
// PARITY CONSTRAINT (registry `concepts/teambuild.md`, d-teambuild-discovery):
// there is exactly ONE implementation of this browse. The console's disconnected
// scaffolding browse, and any future panel client, RIDE THIS MODULE — they do not
// get a second reader. A second enumerator anywhere is the defect this constraint
// exists to prevent, not a variant.
//
// BLURB SOURCE — existing fields only, no new field anywhere:
//   catalog rows (prompts.csv / tasks.csv / seats.csv)  → the `description` COLUMN
//   cognitive-unit files, workflows, components, modules → frontmatter `description`
// A component that carries no description reads `(no description)`. Inventing one
// would make the browse's own output indistinguishable from the corpus's content.
//
// WHAT REFUSES (the red arm). A catalog that is ABSENT is simply not listed — a
// component need not carry every database. A catalog that is PRESENT but MALFORMED
// refuses loudly and stops the whole listing: no header, no `description` column,
// or no id column. Reading a malformed catalog positionally is how every field
// comes back as the value of whatever sat at that index.

const fs = require('fs');
const path = require('path');

// kind -> {file, id column}. The id is read BY NAME and a missing name is missing —
// never silently the first column's value.
const CATALOGS = {
  agents: { file: 'prompts.csv', id: 'prompt-id' },
  tasks: { file: 'tasks.csv', id: 'task-id' },
  seats: { file: 'seats.csv', id: 'seat-id' },
};

const KINDS = ['agents', 'units', 'seats', 'tasks', 'workflows'];

const NO_BLURB = '(no description)';

function fail(code, message) {
  const e = new Error(message);
  e.rbtvCode = code;
  throw e;
}

// ---------------------------------------------------------------- substrate

// Minimal RFC4180 field splitting. Deliberately NOT required from
// ignite/server/seat-identity/csv.js: `core` is always installed and `ignite` is
// not, so a require across that boundary would break this browse on any workspace
// without the runtime layer. Measured on the real corpus 2026-08-06: 162 mirror
// CSVs, zero lines with an unbalanced quote — no field spans a newline, so a
// line-at-a-time split is correct here.
function splitRow(line) {
  const out = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"') {
        if (line[i + 1] === '"') { field += '"'; i += 1; } else quoted = false;
      } else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { out.push(field); field = ''; } else field += ch;
  }
  out.push(field);
  return out;
}

function readCatalog(file, idColumn) {
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/).filter((l) => l.length);
  if (!lines.length) fail('BAD_CATALOG', `${file} is empty — a catalog with no header declares no schema`);
  const header = splitRow(lines[0]).map((h) => h.trim());
  for (const need of [idColumn, 'description']) {
    if (!header.includes(need)) {
      fail('BAD_CATALOG', `${file} has no \`${need}\` column — header is: ${header.join(', ')}`);
    }
  }
  return lines.slice(1).map((line) => {
    const f = splitRow(line);
    const row = {};
    header.forEach((h, i) => { row[h] = f[i] === undefined ? '' : f[i]; });
    return row;
  });
}

// Frontmatter scalars. Only enough YAML to read `id` and `description`, including
// the folded continuation form these files actually use (341 of 2015 corpus files
// carry one, measured 2026-08-06) — a first-line-only read would truncate every one
// of them mid-sentence.
function frontmatter(file) {
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch { return {}; }
  if (!text.startsWith('---')) return {};
  const bodyStart = text.indexOf('\n') + 1;
  const end = text.indexOf('\n---', bodyStart - 1);
  if (end < 0) return {};
  const lines = text.slice(bodyStart, end).split('\n');
  const out = {};
  for (let i = 0; i < lines.length; i += 1) {
    const m = /^([A-Za-z0-9_/. -]+):[ \t]*(.*)$/.exec(lines[i]);
    if (!m) continue;
    let value = m[2];
    while (i + 1 < lines.length && /^[ \t]+\S/.test(lines[i + 1])) {
      value = value ? `${value} ${lines[i + 1].trim()}` : lines[i + 1].trim();
      i += 1;
    }
    // Trimmed AFTER unquoting too: a quoted scalar can carry its own trailing
    // space inside the quotes, which one file in the corpus does.
    out[m[1].trim()] = unquote(value.trim()).trim();
  }
  return out;
}

// A quoted YAML scalar also DOUBLES its own quote character to escape it. Dropping
// the outer pair without undoing that leaves `it''s` in the blurb — 15 of the 2015
// corpus files carry one, found by diffing this reader against PyYAML over the
// whole corpus rather than by reading the code.
function unquote(s) {
  const q = s[0];
  if (s.length > 1 && (q === '"' || q === "'") && s.endsWith(q)) {
    return s.slice(1, -1).split(q + q).join(q);
  }
  return s;
}

function dirs(p) {
  try {
    return fs.readdirSync(p, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name).sort();
  } catch { return []; }
}

// ---------------------------------------------------------------- the corpus

// The mirror root: `--root` wins, else the nearest `.rbtv/mirror` walking up from
// `start`. The walk is an INFERENCE about where the caller stands, so its failure
// names every directory it looked in rather than reporting an empty corpus.
function resolveRoot(explicit, start) {
  if (explicit) {
    if (!fs.existsSync(explicit)) fail('NO_MIRROR', `no mirror at ${explicit}`);
    return path.resolve(explicit);
  }
  const looked = [];
  let dir = path.resolve(start || process.cwd());
  for (;;) {
    const candidate = path.join(dir, '.rbtv', 'mirror');
    looked.push(candidate);
    if (fs.existsSync(candidate)) return candidate;
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  fail('NO_MIRROR', `no .rbtv/mirror found walking up from ${path.resolve(start || process.cwd())}\n`
    + `       looked in: ${looked.join('\n                  ')}`);
  return null;
}

// A component is any directory under a module directory. Its databases are read
// only where the file exists — absence is not an error, malformation is.
function components(root) {
  const out = [];
  for (const mod of dirs(root)) {
    for (const comp of dirs(path.join(root, mod))) {
      out.push({ module: mod, component: comp, dir: path.join(root, mod, comp) });
    }
  }
  return out;
}

// Every entry is {kind, id, blurb, module, component, path, ...extra}. `blurb` is
// always the existing description field, never a synthesised one.
function entries(root, kind) {
  const out = [];
  for (const c of components(root)) {
    if (kind === 'units') out.push(...units(c));
    else if (kind === 'workflows') out.push(...workflows(c));
    else out.push(...catalogRows(c, kind));
  }
  return out;
}

function catalogRows(c, kind) {
  const spec = CATALOGS[kind];
  const file = path.join(c.dir, spec.file);
  if (!fs.existsSync(file)) return [];
  return readCatalog(file, spec.id).map((row) => ({
    kind,
    id: row[spec.id],
    blurb: row.description || NO_BLURB,
    module: c.module,
    component: c.component,
    path: file,
    // The agent card's second half: the prompt row's staffing recommendations
    // (`concepts/agent-card.md`) — hints the staffer carries into the binding,
    // never a binding. Absent in older catalogs; absent means absent.
    staffing: kind === 'agents' ? (row['staffing-recommendations'] || '') : '',
    executor: kind === 'seats' ? (row.executor || '') : '',
  }));
}

// Cognitive units live at <component>/{prompts,tasks}/cognitive-units/<kind>/*.md.
// The unit kind is the DIRECTORY NAME as authored — reported verbatim, matched
// tolerantly (the two mirror shapes on this box disagree on plural vs singular:
// `roles/` and `persona/` both occur).
function units(c) {
  const out = [];
  for (const half of ['prompts', 'tasks']) {
    const base = path.join(c.dir, half, 'cognitive-units');
    for (const unitKind of dirs(base)) {
      const kdir = path.join(base, unitKind);
      for (const f of fs.readdirSync(kdir).filter((n) => n.endsWith('.md')).sort()) {
        const fm = frontmatter(path.join(kdir, f));
        out.push({
          kind: 'units',
          unit_kind: unitKind,
          id: fm.id || path.basename(f, '.md'),
          blurb: fm.description || NO_BLURB,
          module: c.module,
          component: c.component,
          path: path.join(kdir, f),
        });
      }
    }
  }
  return out;
}

// A workflow's blurb is its ENTRY POINT's frontmatter description. Its manifest CSV
// carries no description column by design — it orders seats, it does not describe
// the workflow — so reading the blurb from there would be reading a column that is
// not there.
function workflows(c) {
  const base = path.join(c.dir, 'workflows');
  return dirs(base).map((name) => ({
    kind: 'workflows',
    id: name,
    blurb: frontmatter(path.join(base, name, 'workflow.md')).description || NO_BLURB,
    module: c.module,
    component: c.component,
    path: path.join(base, name),
  }));
}

// `roles` matches `role`, `persona` matches `personas`. Both mirror shapes on this
// box are authored, neither is wrong, and a filter that only knew one would report
// a real unit kind as absent.
function kindMatches(query, dirName) {
  const norm = (s) => s.toLowerCase().replace(/s$/, '');
  return norm(query) === norm(dirName);
}

module.exports = { KINDS, NO_BLURB, resolveRoot, components, entries, kindMatches, frontmatter, splitRow, readCatalog };
