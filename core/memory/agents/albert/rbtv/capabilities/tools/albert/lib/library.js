'use strict';

const fs = require('node:fs');
const path = require('node:path');

const RELATIVE = '../../../../../../../capabilities/tools/memory/lib/index.js';
const REPO_FROM_INSTALLER = 6;
const SHIM = 'rbtv-shim -> ';

function exists(file) {
  try { return fs.statSync(file).isFile(); } catch { return false; }
}

function shimTarget(file) {
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch { return null; }
  for (const line of text.split(/\r?\n/)) {
    const at = line.indexOf(SHIM);
    if (at === -1) continue;
    const target = line.slice(at + SHIM.length).trim();
    return target || null;
  }
  return null;
}

function commandFile(name) {
  for (const dir of (process.env.PATH || '').split(path.delimiter)) {
    if (!dir) continue;
    const file = path.join(dir, name);
    try {
      if (!fs.existsSync(file)) continue;
      const real = fs.realpathSync(file);
      return shimTarget(real) || real;
    } catch { /* next */ }
  }
  return null;
}

function candidates() {
  const list = [path.resolve(__dirname, RELATIVE)];
  if (process.env.ALBERT_MEMORY_LIB) list.push(path.resolve(process.env.ALBERT_MEMORY_LIB));
  const memoryBin = commandFile('memory');
  if (memoryBin) list.push(path.join(path.dirname(memoryBin), 'lib', 'index.js'));
  const installer = commandFile('rbtv');
  if (installer) {
    const repo = path.resolve(installer, ...Array(REPO_FROM_INSTALLER).fill('..'));
    list.push(path.join(repo, 'core', 'memory', 'capabilities', 'tools', 'memory', 'lib', 'index.js'));
  }
  return list;
}

function loadLibrary() {
  const tried = [];
  for (const file of candidates()) {
    tried.push(file);
    if (!exists(file)) continue;
    const lib = require(file);
    if (typeof lib.validateProposalResult !== 'function' || typeof lib.publishProposal !== 'function') continue;
    lib.libraryFile = file;
    return lib;
  }
  const error = new Error('memory library not found; put ~/.rbtv/bin on PATH so the memory command from rbtv agent add albert is found, or set ALBERT_MEMORY_LIB to the library file');
  error.tried = tried;
  throw error;
}

module.exports = { loadLibrary, candidates, commandFile };
