'use strict';

// The drill substrate — levels 0, 1 and 2, read straight off the tree.
//
// A module is a folder at the repo root holding its own `<module>.json`; a
// component is a folder inside it holding its own `<component>.json`. Both records
// carry the description shown at levels 0 and 1. Level 2 delivers a component's
// orientation text (`capabilities/component.md`, when it has one) and its units,
// found by the folder each sits in: `skills/`, `rules/`, `commands/`, `agents/`,
// `hooks/`, `mcp-servers/`, `capabilities/tools/<tool>/`, `folder-instructions/`.
//
// This reader lists; it does not validate. The installer refuses a file that
// breaks its schema — here a unit's name and description are simply read.

const fs = require('fs');
const path = require('path');

// The repo root, resolved from this file's own position: tool/lib -> tool ->
// rbtv-cli -> meta -> <rbtv root>. `RBTV_ROOT` overrides it, the
// same env-override shape the rest of this family uses (RBTV_IGNITE_UNIT,
// IGNITE_GATEWAY_ADDR) — which is also what makes the tree probeable from a
// throwaway copy without editing the real one.
//
// The positional walk is an INFERENCE about where this file sits, and it is wrong
// the moment the tool is copied or the layout moves. So it is never trusted
// silently: every read through it fails into a typed, teaching refusal naming the
// root it resolved, and `doctor` prints that root as its own check.
const RBTV_ROOT = process.env.RBTV_ROOT
  ? path.resolve(process.env.RBTV_ROOT)
  : path.resolve(__dirname, '..', '..', '..', '..');

// A folder with `<name>/<name>.json` is a module (at the root) or a component
// (inside a module). `node_modules`, dot-directories and `probes` are never
// either: the first is a dependency tree, the second is bookkeeping, the third
// is test fixtures.
const SKIP = new Set(['node_modules', 'probes']);

function readJson(abs) {
  try {
    return JSON.parse(fs.readFileSync(abs, 'utf8'));
  } catch {
    return null;
  }
}

function recordFolders(parent) {
  let entries;
  try {
    entries = fs.readdirSync(parent, { withFileTypes: true });
  } catch (err) {
    const e = new Error(`cannot read the rbtv tree at ${parent}: ${err.message}`);
    e.rbtvCode = 'NO_TREE';
    throw e;
  }
  const out = [];
  for (const d of entries) {
    if (!d.isDirectory() || d.name.startsWith('.') || SKIP.has(d.name)) continue;
    const record = readJson(path.join(parent, d.name, `${d.name}.json`));
    if (record) out.push({ name: d.name, dir: path.join(parent, d.name), record });
  }
  return out;
}

// Level 0 — the modules ON THE TREE, read from disk rather than from an inventory
// file, so a module added or removed is visible the moment it exists.
//
// A tree with no module record anywhere is a resolved-root failure, not an empty
// repo, so it refuses by name — every verb passes through here, and "0 modules"
// silently answered would send a caller looking for a module that is really
// there.
function modules() {
  const out = recordFolders(RBTV_ROOT).map((m) => ({
    name: m.name,
    description: m.record.description || '',
    entry_point: rel(path.join(m.dir, `${m.name}.json`)),
  }));
  if (!out.length) {
    const e = new Error(`no directory under ${RBTV_ROOT} carries a <module>/<module>.json`);
    e.rbtvCode = 'NO_MODULES';
    throw e;
  }
  return out.sort((a, b) => a.name.localeCompare(b.name));
}

function moduleExists(name) {
  return modules().some((m) => m.name === name);
}

// Level 1 — a module's components.
function components(moduleName) {
  if (!moduleExists(moduleName)) return null;
  return componentFolders(moduleName);
}

function componentFolders(moduleName) {
  const out = recordFolders(path.join(RBTV_ROOT, moduleName)).map((c) => {
    const orientation = path.join(c.dir, 'capabilities', 'component.md');
    const hasOrientation = fs.existsSync(orientation);
    return {
      kind: 'component',
      name: c.name,
      description: c.record.description || '(component)',
      entry_point: hasOrientation ? rel(orientation) : null,
      units: unitsOf(c.dir),
    };
  });
  return out.sort((a, b) => a.name.localeCompare(b.name));
}

const FILE_UNITS = [
  ['skills', 'skill', '.md'],
  ['rules', 'rule', '.md'],
  ['commands', 'command', '.md'],
  ['agents', 'agent', '.md'],
  ['hooks', 'hook', '.json'],
  ['mcp-servers', 'mcp-server', '.json'],
];

// A component's units: what each exposure folder holds, with the description its
// own frontmatter or record carries.
function unitsOf(dir) {
  const out = [];
  for (const [folder, method, ext] of FILE_UNITS) {
    for (const file of listDir(path.join(dir, folder)).filter((f) => f.endsWith(ext))) {
      const abs = path.join(dir, folder, file);
      out.push({
        id: file.slice(0, -ext.length),
        method,
        description: ext === '.md' ? frontmatterField(abs, 'description') : (readJson(abs) || {}).description,
        entry: rel(abs),
      });
    }
  }
  for (const tool of listDir(path.join(dir, 'capabilities', 'tools'))) {
    const record = readJson(path.join(dir, 'capabilities', 'tools', tool, `${tool}.json`));
    if (!record) continue;
    out.push({
      id: tool,
      method: 'tool',
      description: record.description,
      entry: rel(path.resolve(dir, 'capabilities', 'tools', tool, record.entry || '')),
    });
  }
  for (const file of listDir(path.join(dir, 'folder-instructions')).filter((f) => f.endsWith('.md'))) {
    const abs = path.join(dir, 'folder-instructions', file);
    out.push({
      id: file.slice(0, -3),
      method: 'folder-instructions',
      description: `folder instructions for ${frontmatterField(abs, 'target') || '?'}`,
      entry: rel(abs),
    });
  }
  return out.map((u) => ({ ...u, description: u.description || '' }));
}

function listDir(abs) {
  try {
    return fs.readdirSync(abs).sort();
  } catch {
    return [];
  }
}

// Minimal frontmatter field read — the same `---\nkey: value\n---` block every
// other rbtv-authored file already carries. Some values ARE quoted (a
// `description:` containing a colon must be, or the YAML is invalid), so a
// matching pair of surrounding quotes is stripped: leaving it in printed a
// stray `"` at the head of two module blurbs.
function frontmatterField(absPath, key) {
  let text;
  try {
    text = fs.readFileSync(absPath, 'utf8');
  } catch {
    return null;
  }
  const block = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!block) return null;
  const line = block[1].split(/\r?\n/).find((l) => l.startsWith(`${key}:`));
  if (!line) return null;
  const value = line.slice(line.indexOf(':') + 1).trim();
  const unquoted = /^(["']).*\1$/.test(value) ? value.slice(1, -1) : value;
  return unquoted || null;
}

// A component's orientation text DELIVERABLE never includes its own frontmatter
// block: the body is what level 2 prints.
function stripFrontmatter(text) {
  if (!text) return text;
  const m = text.match(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/);
  return m ? text.slice(m[0].length).replace(/^(?:\r?\n)+/, '') : text;
}

// The component with this name, or null.
function findComponent(moduleName, componentName) {
  return (components(moduleName) || []).find((c) => c.name === componentName) || null;
}

// Rules ride the drill's results: delivered as NAMES + PATHS inline and BODIES
// under --rules, because unconditionally inlining them would make the cheap scan
// step the most expensive output the CLI produces.
function rulesOf(moduleName) {
  if (!moduleExists(moduleName)) return [];
  const out = [];
  for (const comp of componentFolders(moduleName)) {
    for (const unit of comp.units) {
      if (unit.method === 'rule') {
        out.push({ name: unit.id, description: unit.description, path: unit.entry });
      }
    }
  }
  return out;
}

// Level 2 delivers a body. Read at the point of need, never eagerly.
function readBody(relPath) {
  if (!relPath) return null;
  const abs = path.isAbsolute(relPath) ? relPath : path.join(RBTV_ROOT, relPath);
  try {
    return fs.readFileSync(abs, 'utf8');
  } catch {
    return null;
  }
}

function rel(abs) {
  return path.relative(RBTV_ROOT, abs).split(path.sep).join('/');
}

module.exports = {
  RBTV_ROOT,
  modules,
  moduleExists,
  components,
  componentFolders,
  findComponent,
  rulesOf,
  readBody,
  stripFrontmatter,
  rel,
};
