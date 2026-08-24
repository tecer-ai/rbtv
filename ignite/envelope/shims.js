'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const SHIM_DIRNAME = 'config-shims';

// ⚠ EVERY ENTRY IS A CONFIG *FILE*, NEVER A STORE DIRECTORY. Spec §8's shim carries "the config
// the tool reads", and a harness store is config files sitting inside a data tree: `~/.claude`
// holds 3.7 GB of transcripts beside its 3 KB `settings.json`, and `~/.local/share/opencode`
// holds a 6.4 GB session database beside its 1.5 KB `auth.json`. The first cut of this file
// copied the store trees and wrote ~11 GB into goal scratch on ONE launch, filling the disk.
// A store that grows a new config file is added here by name — never by widening to its parent.
const HARNESS_STORES = {
  claude: (home) => [
    path.join(home, '.claude.json'),
    path.join(home, '.claude', 'settings.json'),
    path.join(home, '.claude', '.credentials.json'),
  ],
  codex: (home) => [
    path.join(home, '.codex', 'config.toml'),
    path.join(home, '.codex', 'auth.json'),
  ],
  opencode: (home) => [
    path.join(home, '.config', 'opencode', 'opencode.jsonc'),
    path.join(home, '.config', 'opencode', 'opencode.json'),
    path.join(home, '.local', 'share', 'opencode', 'auth.json'),
    path.join(home, '.local', 'share', 'opencode', 'mcp-auth.json'),
  ],
};

const TOOL_CONFIGS = {
  stools: (...roots) => roots.map((r) => path.join(r, '3-resources', 'tools', 'stools', 'config.yaml')),
  gtools: (...roots) => roots.map((r) => path.join(r, '3-resources', 'tools', 'gtools', 'config.yaml')),
};

function copyFileInto(src, dest) {
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
      copyFileInto(src, dest);
      files.push({ kind: 'harness', harness, source: src, dest });
    }
  }

  const searchRoots = [workspaceRoot, input.rbtvRepo].filter(Boolean);
  for (const [tool, pathsOf] of Object.entries(TOOL_CONFIGS)) {
    const src = firstExisting(pathsOf(...searchRoots));
    if (!src) continue;
    sources.push(src);
    const dest = path.join(dir, 'tools', tool, 'config.yaml');
    copyFileInto(src, dest);
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
