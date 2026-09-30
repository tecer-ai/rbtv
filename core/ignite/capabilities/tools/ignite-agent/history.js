'use strict';

// API
// DEFAULT_HISTORY_WINDOW — recent messages included in every turn prompt
// historyPath(home, key) → conversations/<safe>/history.md under home.
//   safe replaces : * ? " < > | \\ in the key with '-'. A raw-key folder is renamed on first access.
// listAll(store, key) — store history for one conversation, oldest first
// writeHistory(home, store, key) — regenerate that conversation's history.md from the store

const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_HISTORY_WINDOW = 20;
const FULL_HISTORY_LIMIT = 100_000;
const FORBIDDEN = /[:*?"<>|\\]/g;

function conversationDir(key) {
  return String(key).replace(FORBIDDEN, '-');
}

function historyPath(home, key) {
  const name = conversationDir(key);
  const dir = path.join(home, 'conversations', name);
  if (name !== key && !fs.existsSync(dir)) {
    const legacy = path.join(home, 'conversations', key);
    let legacyExists = false;
    try { legacyExists = fs.existsSync(legacy); } catch { legacyExists = false; }
    if (legacyExists) fs.renameSync(legacy, dir);
  }
  return path.join(dir, 'history.md');
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
