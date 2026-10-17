'use strict';

// API
// DEFAULT_HISTORY_WINDOW — recent messages included in every turn prompt
// historyPath(home, key) → runtime/ignite/conversations/<safe>/history.md under home.
//   safe replaces : * ? " < > | \\ in the key with '-'. A raw-key folder is renamed on first access.
// listAll(store, key) — store history for one conversation, oldest first
// writeHistory(home, store, key) — regenerate that conversation's history.md from the store. An owner
//   message's heading carries its provenance — service, id, account, conversation and sender with its
//   trust (a claimed sender stays marked claimed) — whenever the stored message carries it; a Slack
//   message stored without provenance keeps the plain timestamp wording. The heading keeps the
//   timestamp `ignite status --task --message` takes.

const fs = require('node:fs');
const path = require('node:path');
const { ignitePaths, resolveIgniteRuntime } = require('./config.js');

const DEFAULT_HISTORY_WINDOW = 20;
const FULL_HISTORY_LIMIT = 100_000;
const FORBIDDEN = /[:*?"<>|\\]/g;

function conversationDir(key) {
  return String(key).replace(FORBIDDEN, '-');
}

function historyPath(home, key) {
  resolveIgniteRuntime(home);
  const name = conversationDir(key);
  const dir = path.join(ignitePaths(home).conversations, name);
  if (name !== key && !fs.existsSync(dir)) {
    const legacy = path.join(ignitePaths(home).conversations, key);
    let legacyExists = false;
    try { legacyExists = fs.existsSync(legacy); } catch { legacyExists = false; }
    if (legacyExists) fs.renameSync(legacy, dir);
  }
  return path.join(dir, 'history.md');
}

function listAll(store, key) {
  return store.listHistory(key, FULL_HISTORY_LIMIT);
}

// One provenance rendering for every connector's owner messages: the neutral sender line the
// prompt uses, in the history heading. Rows without stored provenance keep their older wording.
function provenanceTag(row) {
  const meta = row.metadata || {};
  const connector = meta.connector || row.connector;
  if (!connector) return ` (Slack timestamp ${row.ts})`;
  const account = meta.account ?? null;
  const sender = meta.claimed || meta.from || null;
  if (!account && !sender) return connector === 'slack' ? ` (Slack timestamp ${row.ts})` : ` (${connector} id ${row.ts})`;
  const trust = meta.trusted ? 'trusted' : 'claimed';
  const conversation = meta.conversation || row.channel || null;
  const parts = [`${connector} id ${row.ts}`];
  if (account != null) parts.push(`account ${account}`);
  if (conversation != null) parts.push(`conversation ${conversation}`);
  parts.push(`sender ${trust} ${sender}`);
  return ` (${parts.join(' ')})`;
}

function writeHistory(home, store, key) {
  const rows = listAll(store, key);
  const lines = [`# ${key}`, ''];
  if (rows.length === FULL_HISTORY_LIMIT) {
    lines.push(`(file holds the newest ${FULL_HISTORY_LIMIT} messages; the store has the rest)`, '');
  }
  for (const row of rows) {
    const ts = row.role === 'owner' && row.ts ? provenanceTag(row) : '';
    lines.push(`## ${row.created_at} ${row.role}${ts}`, row.text || '', '');
  }
  const file = historyPath(home, key);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${lines.join('\n')}\n`);
  return file;
}

module.exports = { DEFAULT_HISTORY_WINDOW, FULL_HISTORY_LIMIT, historyPath, listAll, writeHistory };
