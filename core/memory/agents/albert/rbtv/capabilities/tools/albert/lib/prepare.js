'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const store = require('./store.js');

function hash(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

function readBatch(file) {
  const raw = fs.readFileSync(file, 'utf8');
  let body;
  try { body = JSON.parse(raw); } catch { throw new Error(`evidence batch is not JSON: ${path.basename(file)}`); }
  for (const key of ['sourceKind', 'sourceAgent', 'sourceCursor', 'ceiling', 'contentHash', 'rows']) {
    if (body[key] == null) throw new Error(`evidence batch missing ${key}: ${path.basename(file)}`);
  }
  if (!Array.isArray(body.rows)) throw new Error(`evidence batch rows must be an array: ${path.basename(file)}`);
  const digest = hash(JSON.stringify(body.rows));
  if (digest !== body.contentHash) throw new Error(`evidence batch contentHash mismatch: ${path.basename(file)}`);
  return body;
}

function sourceId(batch) {
  return `${batch.sourceKind}:${batch.sourceAgent}:${batch.sourceCursor}`;
}

function prepare(lib, home, installation, agent) {
  const now = Date.now();
  const id = crypto.randomUUID();
  const date = new Date(now).toISOString().slice(0, 10);
  const release = lib.acquireMemoryLock(installation);
  let run;
  try {
    const files = lib.snapshot(installation, [{ slug: agent }]);
    const plain = Object.fromEntries(files);
    const hashes = Object.fromEntries([...files].map(([name, text]) => [name, hash(text)]));
    const consumed = new Set(store.readConsumed(home).batches);
    const batches = [];
    const messages = [];
    const excluded = [];
    const sources = [];
    for (const name of store.listEvidence(home)) {
      if (consumed.has(name)) continue;
      const batch = readBatch(path.join(store.evidenceDir(home), name));
      batches.push(name);
      const positions = [];
      for (const row of batch.rows) {
        if (!row || row.id == null || typeof row.author !== 'string') throw new Error(`evidence row needs id and author in ${name}`);
        positions.push(String(row.id));
        const item = {
          nativeId: row.id,
          text: String(row.text || ''),
          thread: row.thread || null,
          conversation_key: row.conversationKey || `${batch.sourceAgent}:${row.id}`,
          author: row.author,
        };
        if (row.author === 'owner' && Number.isSafeInteger(row.id)) {
          messages.push({ rowid: row.id, ...item });
        } else excluded.push(item);
      }
      sources.push({
        source: sourceId(batch),
        sourceKind: batch.sourceKind,
        sourceAgent: batch.sourceAgent,
        sourceCursor: batch.sourceCursor,
        ceiling: batch.ceiling,
        positions,
        batch: name,
      });
    }
    const inbox = plain['.rbtv/memory/inbox.md'] || '';
    const inboxLines = inbox.split(/\r?\n/).filter((line) => line.startsWith('- ') && (line.includes(` · ${agent}`) || line.includes(` · ${agent}/`)));
    if (inboxLines.length) {
      sources.push({
        source: `inbox:${agent}`,
        sourceKind: 'inbox',
        sourceAgent: agent,
        sourceCursor: 'inbox',
        ceiling: hash(inboxLines.join('\n')),
        positions: inboxLines,
        batch: null,
      });
    }
    run = {
      id,
      agent,
      createdAt: now,
      phase: 'prepared',
      date,
      files: plain,
      hashes,
      sources,
      batches,
      excluded,
      input: {
        agent,
        date,
        cursor: 0,
        ceiling: messages.reduce((max, row) => Math.max(max, row.rowid), 0),
        messages,
        reportedConflicts: [],
        files: plain,
      },
      intended: null,
      commit: null,
      receiptId: null,
    };
    store.writeRun(home, run);
  } finally { release(); }
  return { run: run.id, input: { ...run.input, excluded: run.excluded, sources: run.sources } };
}

module.exports = { prepare, hash };
