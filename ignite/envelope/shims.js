'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const SHIM_DIRNAME = 'config-shims';

const HARNESS_STORES = {
  claude: (home) => [path.join(home, '.claude'), path.join(home, '.claude.json')],
  codex: (home) => [path.join(home, '.codex')],
  opencode: (home) => [
    path.join(home, '.config', 'opencode'),
    path.join(home, '.local', 'share', 'opencode'),
  ],
};

const TOOL_CONFIGS = {
  stools: (...roots) => roots.map((r) => path.join(r, '3-resources', 'tools', 'stools', 'config.yaml')),
  gtools: (...roots) => roots.map((r) => path.join(r, '3-resources', 'tools', 'gtools', 'config.yaml')),
};

function copyInto(src, dest) {
  const st = fs.statSync(src);
  if (st.isDirectory()) {
    fs.cpSync(src, dest, { recursive: true, dereference: true });
    return;
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
}

function firstExisting(cands) {
  for (const p of cands) {
    if (p && fs.existsSync(p)) return p;
  }
  return null;
}

function writeConfigShims(input) {
  const goalDir = input.goalDir;
  if (!goalDir) return { dir: null, files: [], sources: [] };
  const home = input.home || os.homedir();
  const workspaceRoot = input.workspaceRoot || null;
  const dir = path.join(goalDir, 'scratch', SHIM_DIRNAME);
  fs.mkdirSync(dir, { recursive: true });
  const files = [];
  const sources = [];

  for (const [harness, pathsOf] of Object.entries(HARNESS_STORES)) {
    for (const src of pathsOf(home)) {
      if (!fs.existsSync(src)) continue;
      sources.push(src);
      const dest = path.join(dir, 'harness', harness, path.basename(src));
      copyInto(src, dest);
      files.push({ kind: 'harness', harness, source: src, dest });
    }
  }

  const searchRoots = [workspaceRoot, input.rbtvRepo].filter(Boolean);
  for (const [tool, pathsOf] of Object.entries(TOOL_CONFIGS)) {
    const src = firstExisting(pathsOf(...searchRoots));
    if (!src) continue;
    sources.push(src);
    const dest = path.join(dir, 'tools', tool, 'config.yaml');
    copyInto(src, dest);
    files.push({ kind: 'tool', tool, source: src, dest });
  }

  return { dir, files, sources };
}

function realStoreOnBinds(binds, sources) {
  const listed = new Set((binds || []).map((b) => path.resolve(b.path)));
  return (sources || []).filter((s) => listed.has(path.resolve(s)));
}

module.exports = {
  SHIM_DIRNAME,
  HARNESS_STORES,
  TOOL_CONFIGS,
  writeConfigShims,
  realStoreOnBinds,
};
