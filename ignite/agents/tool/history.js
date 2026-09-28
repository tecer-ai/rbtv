'use strict';

// API
// DEFAULT_HISTORY_WINDOW — recent messages included in every turn prompt
// historyPath(home, key) → <home>/conversations/<key>/history.md
// listAll(store, key) — store history for one conversation, oldest first
// writeHistory(home, store, key) — regenerate that conversation's history.md from the store

const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_HISTORY_WINDOW = 20;
const FULL_HISTORY_LIMIT = 100_000;

function historyPath(home, key) {
  return path.join(home, 'conversations', key, 'history.md');
}

function listAll(store, key) {
  return store.listHistory(key, FULL_HISTORY_LIMIT);
}

function writeHistory(home, store, key) {
  const rows = listAll(store, key);
  const lines = [`# ${key}`, ''];
  if (rows.length === FULL_HISTORY_LIMIT) {
    lines.push(`(file holds the newest ${FULL_HISTORY_LIMIT} messages; the store has the rest)`, '');
  }
  for (const row of rows) {
    lines.push(`## ${row.created_at} ${row.role}`, row.text || '', '');
  }
  const file = historyPath(home, key);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${lines.join('\n')}\n`);
  return file;
}

module.exports = { DEFAULT_HISTORY_WINDOW, FULL_HISTORY_LIMIT, historyPath, listAll, writeHistory };
