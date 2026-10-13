'use strict';

const fs = require('node:fs');
const path = require('node:path');

const RELATIVE = '../../../../../../../capabilities/tools/memory/lib/index.js';

function exists(file) {
  try { return fs.statSync(file).isFile(); } catch { return false; }
}

function fromCommand(name) {
  for (const dir of (process.env.PATH || '').split(path.delimiter)) {
    if (!dir) continue;
    const file = path.join(dir, name);
    try { if (fs.existsSync(file)) return fs.realpathSync(file); } catch { /* next */ }
  }
  return null;
}

function candidates() {
  const list = [path.resolve(__dirname, RELATIVE)];
  if (process.env.ALBERT_MEMORY_LIB) list.push(path.resolve(process.env.ALBERT_MEMORY_LIB));
  const memoryBin = fromCommand('memory');
  if (memoryBin) list.push(path.join(path.dirname(memoryBin), 'lib', 'index.js'));
  const installer = fromCommand('rbtv');
  if (installer) {
    const repo = path.resolve(installer, ...Array(7).fill('..'));
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
  const error = new Error('memory library not found; the installed copy has no path to the memory component');
  error.tried = tried;
  throw error;
}

module.exports = { loadLibrary, candidates };
