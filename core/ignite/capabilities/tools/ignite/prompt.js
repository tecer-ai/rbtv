'use strict';

// API
// composeTurn({ board, work, inputs, recent, stored, historyPath, resultPath, nonce, rehydrate })
//   → turn message. Standing instructions are not copied here; turn-loop passes
//   <home>/agent.md as systemPromptFile on the cast request. This file does not read CLAUDE.md.
// readTurnMemory(home, cwd, store?, now?) → board, memory sections and owner alerts

const fs = require('node:fs');
const path = require('node:path');
const { boardPath, refreshBoard, renderBoard } = require('./board.js');
const { workspaceFromHome, workspacePaths, workspaceMatches, workspaceFiles, readMemory } = require('./memory.js');

const CONTRACT = [
  'Write JSON to RESULT_FILE and nowhere else. Do not post to Slack.',
  'Shape: {"nonce":"<NONCE>","disposition":"completed|continue|waiting_owner|waiting_workers|stopped",',
  '"summary":"…","nextStep":"…","workers":[{"ref":"…","kind":"…"}],"outputs":["<path>"],',
  '"replies":[{"text":"…","audio":false,"files":["<path>"]}]}',
  'disposition continue requires a non-empty nextStep. Echo NONCE exactly.',
].join(' ');

function readBoard(home, store = null, now = Date.now(), alerts = []) {
  const loaded = readMemory(boardPath(home), 'board', alerts);
  if (!store || !loaded.source) return loaded.text;
  try {
    if (loaded.source === 'working') refreshBoard(home, store, now);
    return renderBoard(loaded.text, store, now);
  } catch {
    alerts.push(`Memory alert: ${boardPath(home)} refresh failed; using the checked board without refreshed timers or flags.`);
    return `(board refresh failed)\n${loaded.text}`;
  }
}

function readTurnMemory(home, cwd = home, store = null, now = Date.now()) {
  const alerts = [];
  const board = readBoard(home, store, now, alerts);
  const memory = [];
  const workspace = workspaceFromHome(home);
  const add = (file, kind) => memory.push({ path: file, text: readMemory(file, kind, alerts).text });
  if (workspace) add(path.join(workspace, '.rbtv', 'memory', 'profile.md'), 'profile');
  add(path.join(home, 'memory', 'learned.md'), 'learned');
  if (!workspace) {
    const text = '[MISSING MEMORY: installation root unavailable; profile, index and inbox could not be loaded.]';
    memory.push({ path: '.rbtv/memory', text });
    alerts.push(`Memory alert: cannot resolve installation root from agent home ${home}.`);
    return { board, memory, alerts };
  }
  const root = path.join(workspace, '.rbtv', 'memory');
  add(path.join(root, '_artifacts', 'index.md'), 'index');
  add(path.join(root, 'inbox.md'), 'inbox');
  try {
    for (const file of workspaceFiles(path.join(root, 'workspaces'))) {
      const loaded = readMemory(file, 'workspace', alerts);
      let paths = loaded.paths;
      // If both copies fail, readable current paths can still select a missing
      // note. Never inject unscoped private notes when the paths are unknown.
      if (!paths) {
        try { paths = workspacePaths(fs.readFileSync(file, 'utf8')); } catch { continue; }
      }
      if (workspaceMatches(workspace, cwd, paths)) memory.push({ path: file, text: loaded.text });
    }
  } catch {
    alerts.push(`Memory alert: cannot list ${path.join(root, 'workspaces')}; workspace notes unavailable.`);
  }
  return { board, memory, alerts };
}

function linesOf(rows) {
  return rows.map((row) => `[${row.role}] ${row.text}`);
}

function composeTurn({ board, memory = [], work, inputs, recent, stored, historyPath, resultPath, nonce, rehydrate }) {
  const body = [
    'Turn input for this conversation only.',
    `NONCE: ${nonce}`,
    `RESULT_FILE: ${resultPath}`,
    `HISTORY_FILE: ${historyPath}`,
    CONTRACT,
    ...memory.flatMap((item) => [`Memory (${item.path}):`, item.text]),
    'Board:',
    board,
    'Work:',
    JSON.stringify({
      summary: work?.summary ?? null,
      nextStep: work?.next_step ?? null,
      workers: work?.workers ?? [],
      outputs: work?.outputs ?? [],
    }),
    'Triggering input:',
    ...inputs.map((input) => {
      const files = input.files?.length ? `\nattachments: ${input.files.join(', ')}` : '';
      const missing = input.missingFiles
        ? `\n${input.missingFiles} attached file(s) could not be downloaded; tell the owner.` : '';
      return `[${input.role}] ${input.text}${files}${missing}`;
    }),
    'Recent messages of this conversation:',
    ...(recent.length ? linesOf(recent) : ['(none)']),
  ];
  if (rehydrate) {
    body.push(
      'Stored thread context of this conversation (new harness session; do not assume a native transcript):',
      ...(stored.length ? linesOf(stored) : ['(none)']),
      'Continue from the work state above. HISTORY_FILE is the full on-disk history.',
    );
  }
  return `${body.join('\n')}\n`;
}

module.exports = { composeTurn, readBoard, readTurnMemory, CONTRACT };
