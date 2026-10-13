'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { readMemory, workspaceFiles, workspacePaths, workspaceMatches, agentBaselinePath } = require('./records.js');
const { boardPath, renderBoardView } = require('./board.js');
const { loadLearned } = require('./rules.js');

function prepareMemory({ installation, agentHome = null, cwd = null }) {
  if (typeof installation !== 'string' || !installation.trim()) {
    throw new Error('preparation requires an explicit installation root');
  }
  const root = path.resolve(installation);
  const warnings = [];
  const memory = [];
  const identity = { installation: root, agentHome: agentHome ? path.resolve(agentHome) : null, master: false };
  const add = (file, kind) => {
    const loaded = readMemory(file, kind, warnings);
    memory.push({ path: file, text: loaded.text, source: loaded.source });
    return loaded;
  };
  add(path.join(root, '.rbtv', 'memory', 'profile.md'), 'profile');
  add(path.join(root, '.rbtv', 'memory', '_artifacts', 'index.md'), 'index');
  add(path.join(root, '.rbtv', 'memory', 'inbox.md'), 'inbox');
  if (agentHome) {
    const home = path.resolve(agentHome);
    const learned = agentBaselinePath(home);
    const board = boardPath(home);
    if (!fs.existsSync(learned) && !fs.existsSync(board)) {
      warnings.push(`Memory alert: ${home} has no personal records; it is not master.`);
      identity.master = false;
    }
    add(learned, 'learned');
    const loaded = add(board, 'board');
    let view = loaded.text;
    try { view = renderBoardView(loaded.text, board); }
    catch { warnings.push(`Memory alert: ${board} could not be rendered as a view.`); }
    identity.board = board;
    identity.view = view;
    for (const file of loadLearned(root, home)) {
      if (!memory.some((row) => row.path === file.path)) memory.push({ ...file, source: 'working' });
    }
  }
  if (cwd) {
    try {
      for (const file of workspaceFiles(path.join(root, '.rbtv', 'memory', 'workspaces'))) {
        const loaded = readMemory(file, 'workspace', warnings);
        let paths = loaded.paths;
        if (!paths) {
          try { paths = workspacePaths(fs.readFileSync(file, 'utf8')); } catch { continue; }
        }
        if (workspaceMatches(root, cwd, paths)) memory.push({ path: file, text: loaded.text, source: loaded.source });
      }
    } catch {
      warnings.push(`Memory alert: cannot list workspace notes under ${root}.`);
    }
  }
  return { bundle: memory, identity, warnings };
}

module.exports = { prepareMemory };
