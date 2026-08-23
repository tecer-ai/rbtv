'use strict';

// The drill substrate — levels 0, 1 and 2.
//
// ⚠ STAND-IN PENDING CMP-5. The registry (`concepts/rbtv-cli.md`) specifies this
// drill over `module.md` (level 0/1), per-component `component.md` description
// lines (level 1), and exposure-manifest rows carrying an `rbtv-cli` column
// (level 2). `module.md` (level 0/1) is STILL not read — level 0/1's module
// listing stays the install-manifest stand-in below.
//
// What IS now read (owner-ruled 2026-08-24, option a — cli-drill seat): component
// FOLDERS. Since 2026-08-22 some components moved their manifest one level down
// (`component.md` + `exposure.csv` beside the parts they declare, e.g.
// `ignite/team-kit/`, `ignite/work-on-ignite/` — component-anatomy.md §1: "a
// directory at depth 2 holding exposure.csv IS the component"). `componentFolders()`
// below enumerates those directly, and `component.md`'s frontmatter + a component's
// own `exposure.csv` rows are what level 2 delivers for them — the settled CMP-5
// shape, read straight off disk rather than through a manifest that never learns
// about them. What is still NOT read: `module.md` (level 0/1), and the `rbtv-cli`
// column is read as data (which parts a component exposes as verbs) without any
// dispatch machinery around it.
//
// So this module reads the substrate that IS live — the install manifest, the
// capability-folder shape, and now component folders — and every function below is
// a stand-in for a CMP-5 reader, NOT the settled schema. When CMP-5 lands, this
// file is the one that changes; nothing above it should need to.

const fs = require('fs');
const path = require('path');

// The repo root, resolved from this file's own position: tool/lib -> tool ->
// rbtv-cli -> capabilities -> core -> <rbtv root>. `RBTV_ROOT` overrides it, the
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
  : path.resolve(__dirname, '..', '..', '..', '..', '..');
const MANIFEST = path.join(RBTV_ROOT, 'admin', 'install', 'module-manifest.json');

// Manifest keys that carry a per-component inventory. `tools` nests its rows one
// level deeper (`{description, source_dir, entries:[...]}`) and is unwrapped below.
const COMPONENT_KEYS = ['skills', 'commands', 'rules', 'subagents', 'tools'];

function readManifest() {
  let raw;
  try {
    raw = fs.readFileSync(MANIFEST, 'utf8');
  } catch (err) {
    const e = new Error(`cannot read the module manifest at ${MANIFEST}: ${err.message}`);
    e.rbtvCode = 'NO_MANIFEST';
    throw e;
  }
  try {
    return JSON.parse(raw);
  } catch (err) {
    const e = new Error(`the module manifest is not valid JSON (${MANIFEST}): ${err.message}`);
    e.rbtvCode = 'BAD_MANIFEST';
    throw e;
  }
}

// Level 0 — the installed modules. `cross_module_agents` is bookkeeping, not a module.
function modules() {
  const m = readManifest();
  return Object.keys(m)
    .filter((k) => k !== 'cross_module_agents')
    .sort()
    .map((name) => ({
      name,
      description: m[name].description || '',
      always_installed: Boolean(m[name].always_installed),
    }));
}

function moduleExists(name) {
  return modules().some((m) => m.name === name);
}

// A capability is a folder `<module>/capabilities/<name>/` holding `<name>.md`
// (its entry point) and, by convention, `tool/` with the runnable surface. This is
// the settled CLI placement shape (rbtv/CLAUDE.md § CLI Tool Placement) and is the
// closest live thing to CMP-5's exposure rows — hence its use here.
function capabilities(moduleName) {
  const dir = path.join(RBTV_ROOT, moduleName, 'capabilities');
  let names;
  try {
    names = fs.readdirSync(dir, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name)
      .sort();
  } catch {
    return [];
  }
  return names.map((name) => {
    const entryPoint = path.join(dir, name, `${name}.md`);
    return {
      kind: 'capability',
      name,
      description: firstDescriptionLine(entryPoint) || `capability ${name}`,
      entry_point: fs.existsSync(entryPoint) ? rel(entryPoint) : null,
      tools: toolsOf(path.join(dir, name)),
    };
  });
}

// A capability's runnable entry points: executables directly under `tool*/`.
// Directories and non-executable files (READMEs, importable modules) are not
// entry points — only what a caller can actually invoke.
function toolsOf(capabilityDir) {
  const out = [];
  let sub;
  try {
    sub = fs.readdirSync(capabilityDir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const d of sub) {
    if (!d.isDirectory() || !d.name.startsWith('tool')) continue;
    const toolDir = path.join(capabilityDir, d.name);
    for (const f of fs.readdirSync(toolDir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (!f.isFile()) continue;
      const p = path.join(toolDir, f.name);
      try {
        fs.accessSync(p, fs.constants.X_OK);
      } catch {
        continue;
      }
      out.push({ name: f.name, path: rel(p) });
    }
  }
  return out;
}

// Level 1 — a module's components. Manifest rows plus capability folders plus
// component folders; the manifest never lists capabilities (the installer does not
// install them) or component-level manifests (nothing installs those either), so no
// one source alone is the module's inventory.
function components(moduleName) {
  const mod = readManifest()[moduleName];
  if (!mod) return null;
  const out = [];

  for (const key of COMPONENT_KEYS) {
    const block = mod[key];
    if (!block) continue;
    const rows = Array.isArray(block) ? block : Array.isArray(block.entries) ? block.entries : [];
    for (const row of rows) {
      const source = row.source_template || row.source || row.package || null;
      out.push({
        kind: key.replace(/s$/, ''),
        name: componentName(row, key),
        description: row.description || '',
        entry_point: source,
        tools: [],
      });
    }
  }

  out.push(...capabilities(moduleName));
  out.push(...componentFolders(moduleName));
  out.sort((a, b) => a.kind.localeCompare(b.kind) || a.name.localeCompare(b.name));
  return out;
}

// Component folders — a direct child of a MODULE folder carrying `component.md`
// OR `exposure.csv` IS a component (component-anatomy.md §1; team-kit/exposure.csv's
// own header note). `node_modules`, dot-directories and `probes` are never
// components — the first is a dependency tree, the second is bookkeeping, the third
// is test fixtures, per the seat ruling that added this reader.
const COMPONENT_FOLDER_SKIP = new Set(['node_modules', 'probes']);

function componentFolders(moduleName) {
  const modDir = path.join(RBTV_ROOT, moduleName);
  let entries;
  try {
    entries = fs.readdirSync(modDir, { withFileTypes: true });
  } catch {
    return [];
  }
  const out = [];
  for (const d of entries) {
    if (!d.isDirectory()) continue;
    if (d.name.startsWith('.') || COMPONENT_FOLDER_SKIP.has(d.name)) continue;
    const dir = path.join(modDir, d.name);
    const componentMdAbs = path.join(dir, 'component.md');
    const exposureCsvAbs = path.join(dir, 'exposure.csv');
    const hasComponentMd = fs.existsSync(componentMdAbs);
    const hasExposureCsv = fs.existsSync(exposureCsvAbs);
    if (!hasComponentMd && !hasExposureCsv) continue;
    out.push(componentFolderDescriptor(d.name, dir, hasComponentMd, hasExposureCsv));
  }
  return out;
}

// Description priority, exactly the seat ruling's order: component.md frontmatter
// `description:` -> the folder's own `<name>.md` description line -> the first
// non-comment manifest row carrying a description -> "(component)".
function componentFolderDescriptor(name, dir, hasComponentMd, hasExposureCsv) {
  const componentMdAbs = hasComponentMd ? path.join(dir, 'component.md') : null;
  const exposureCsvAbs = hasExposureCsv ? path.join(dir, 'exposure.csv') : null;
  const rows = exposureCsvAbs ? parseExposureCsv(exposureCsvAbs) : [];

  const fromComponentMd = componentMdAbs ? frontmatterField(componentMdAbs, 'description') : null;
  const fromOwnDoc = firstDescriptionLine(path.join(dir, `${name}.md`));
  const fromFirstRow = (rows.find((r) => r.description) || {}).description || null;
  const description = fromComponentMd || fromOwnDoc || fromFirstRow || '(component)';

  return {
    kind: 'component',
    name,
    description,
    entry_point: componentMdAbs ? rel(componentMdAbs) : null,
    tools: [],
    exposure_rows: rows,
    exposure_path: exposureCsvAbs ? rel(exposureCsvAbs) : null,
    has_component_md: hasComponentMd,
  };
}

// Minimal frontmatter field read — the same `---\nkey: value\n---` block every
// other rbtv-authored file already carries. Values are never quoted in this repo's
// frontmatter, so no quote-stripping is attempted beyond a defensive trim.
function frontmatterField(absPath, key) {
  let text;
  try {
    text = fs.readFileSync(absPath, 'utf8');
  } catch {
    return null;
  }
  const block = text.match(/^---\n([\s\S]*?)\n---/);
  if (!block) return null;
  const line = block[1].split('\n').find((l) => l.startsWith(`${key}:`));
  if (!line) return null;
  return line.slice(line.indexOf(':') + 1).trim() || null;
}

// A component.md's DELIVERABLE body never includes its own frontmatter block — the
// frontmatter is addressing metadata (the level-1 blurb), the body is what level 2
// prints (registry: "component entry point" § definition — the agent-facing
// orientation text, distinct from the manifest fact the frontmatter carries).
function stripFrontmatter(text) {
  if (!text) return text;
  const m = text.match(/^---\n[\s\S]*?\n---\n?/);
  return m ? text.slice(m[0].length).replace(/^\n+/, '') : text;
}

// A component's own exposure.csv — same 7-column schema as the module-root
// manifest (concepts/exposure-manifest.md), read with a quoted-field-aware line
// parser (a naive split corrupts any description carrying a comma inside quotes,
// which team-kit's and work-on-ignite's both do).
function parseExposureCsv(absPath) {
  let text;
  try {
    text = fs.readFileSync(absPath, 'utf8');
  } catch {
    return [];
  }
  const dataLines = text.split('\n').filter((l) => l.trim() && !l.trim().startsWith('#'));
  if (!dataLines.length) return [];
  const header = splitCsvLine(dataLines[0]);
  const rows = [];
  for (const line of dataLines.slice(1)) {
    const cells = splitCsvLine(line);
    if (!cells.length || !cells.some((c) => c)) continue;
    const row = {};
    header.forEach((h, i) => { row[h] = cells[i] || ''; });
    rows.push(row);
  }
  return rows;
}

function splitCsvLine(line) {
  const out = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') { cur += '"'; i += 1; } else if (ch === '"') inQuotes = false;
      else cur += ch;
    } else if (ch === '"') inQuotes = true;
    else if (ch === ',') { out.push(cur); cur = ''; } else cur += ch;
  }
  out.push(cur);
  return out;
}

// The name an agent types. Installed components are addressed by their INSTALLED
// name (what `.claude/` actually carries), with the `rbtv-` prefix stripped so the
// module scope is not repeated in every token: `rbtv core commit`, not
// `rbtv core rbtv-commit`.
function componentName(row, key) {
  if (row.name) return row.name;
  if (row.target) {
    const base = path.basename(row.target, '.md');
    const dir = path.basename(path.dirname(row.target));
    const raw = base === 'SKILL' ? dir : base;
    return raw.replace(/^rbtv-/, '');
  }
  if (row.source_template || row.source) {
    return path.basename(row.source_template || row.source, '.md');
  }
  return `<unnamed ${key} row>`;
}

// ALL matches, never the first. One name can legitimately carry two facets — in
// `core`, `safe-move` is BOTH a skill (the loader installed into `.claude/`) and a
// tool (the package it loads). Returning the first match would deliver one facet
// and silently hide the other, and which one you got would depend on manifest key
// order. Level 2 delivers every facet instead.
function findComponents(moduleName, componentName_) {
  const list = components(moduleName);
  if (!list) return [];
  return list.filter((c) => c.name === componentName_);
}

// Rules ride the drill's results (registry: "entering a module or component
// delivers that scope's rules in the tool result, module/component granularity").
// Delivered as NAMES + PATHS inline and BODIES under --rules: `core` alone carries
// 11 rules, and unconditionally inlining them would make the cheap scan step the
// most expensive output the CLI produces. Divergence stated in rbtv-cli.md.
function rulesOf(moduleName) {
  const mod = readManifest()[moduleName];
  if (!mod || !Array.isArray(mod.rules)) return [];
  return mod.rules.map((r) => ({
    name: componentName(r, 'rules'),
    description: r.description || '',
    path: r.source || r.source_template || null,
  }));
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

function firstDescriptionLine(absPath) {
  let text;
  try {
    text = fs.readFileSync(absPath, 'utf8');
  } catch {
    return null;
  }
  for (const line of text.split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#') || t.startsWith('---')) continue;
    return t.replace(/[*_`]/g, '');
  }
  return null;
}

function rel(abs) {
  return path.relative(RBTV_ROOT, abs).split(path.sep).join('/');
}

module.exports = {
  RBTV_ROOT,
  MANIFEST,
  modules,
  moduleExists,
  components,
  capabilities,
  componentFolders,
  findComponents,
  rulesOf,
  readBody,
  stripFrontmatter,
  rel,
};
