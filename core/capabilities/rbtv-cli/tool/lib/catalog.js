'use strict';

// The drill substrate — levels 0, 1 and 2.
//
// ⚠ STAND-IN PENDING CMP-5. The registry (`concepts/rbtv-cli.md`) specifies this
// drill over `module.md` (level 0/1), per-component `component.md` description
// lines (level 1), and exposure-manifest rows carrying an `rbtv-cli` column
// (level 2). NONE of those exist: `find . -name component.md -o -name module.md`
// over the whole repo returns zero, and no exposure manifest carries that column.
// That is G-109 (CMP-5 designed-unbuilt), the same gap `rbtv-goal` hit.
//
// So this module reads the substrate that IS live — the install manifest and the
// capability-folder shape — and every function below is a stand-in for a CMP-5
// reader, NOT the settled schema. When CMP-5 lands, this file is the one that
// changes; nothing above it should need to.

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

// Level 1 — a module's components. Manifest rows plus capability folders; the
// manifest never lists capabilities (the installer does not install them), so
// neither source alone is the module's inventory.
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
  out.sort((a, b) => a.kind.localeCompare(b.kind) || a.name.localeCompare(b.name));
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

function findComponent(moduleName, componentName_) {
  const list = components(moduleName);
  if (!list) return null;
  return list.find((c) => c.name === componentName_) || null;
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
  findComponent,
  rulesOf,
  readBody,
  rel,
};
