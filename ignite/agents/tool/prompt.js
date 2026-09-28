'use strict';

// API
// composeTurn({ board, work, inputs, recent, stored, historyPath, resultPath, nonce, rehydrate })
//   → turn message. CLAUDE.md is not copied here; the harness reads it because cwd is the home.
// readBoard(home) → board.md text, or a visible missing/unreadable note

const fs = require('node:fs');
const path = require('node:path');

const CONTRACT = [
  'Write JSON to RESULT_FILE and nowhere else. Do not post to Slack.',
  'Shape: {"nonce":"<NONCE>","disposition":"completed|continue|waiting_owner|waiting_workers|stopped",',
  '"summary":"…","nextStep":"…","workers":[{"ref":"…","kind":"…"}],"outputs":["<path>"],',
  '"replies":[{"text":"…","audio":false,"files":["<path>"]}]}',
  'disposition continue requires a non-empty nextStep. Echo NONCE exactly.',
].join(' ');

function readBoard(home) {
  try {
    return fs.readFileSync(path.join(home, 'board.md'), 'utf8');
  } catch (error) {
    if (error.code === 'ENOENT') return '(no board)';
    return `(board unreadable: ${error.message})`;
  }
}

function linesOf(rows) {
  return rows.map((row) => `[${row.role}] ${row.text}`);
}

function composeTurn({ board, work, inputs, recent, stored, historyPath, resultPath, nonce, rehydrate }) {
  const body = [
    'Turn input for this conversation only.',
    `NONCE: ${nonce}`,
    `RESULT_FILE: ${resultPath}`,
    `HISTORY_FILE: ${historyPath}`,
    CONTRACT,
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
      return `[${input.role}] ${input.text}${files}`;
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

module.exports = { composeTurn, readBoard, CONTRACT };
