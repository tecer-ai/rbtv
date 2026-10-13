'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { withMemoryLock, safeWritePath } = require('./lock.js');
const { failure, refusalError } = require('./failures.js');

function collectionPath(workspace) {
  return path.join(workspace, '.rbtv', 'memory', 'commitments.md');
}

function parseCollection(text) {
  const items = [];
  const blocks = String(text || '').split(/\n## /).slice(1);
  for (const block of blocks) {
    const [title, ...rest] = block.split('\n');
    const fields = {};
    const changes = [];
    for (const line of rest) {
      const field = line.match(/^- ([a-z_]+): (.*)$/);
      if (field) fields[field[1]] = field[2];
      else if (line.startsWith('  - ')) changes.push(line.slice(4));
    }
    items.push({ id: title.trim(), ...fields, changes });
  }
  return items;
}

function render(items) {
  const lines = ['# Commitments', ''];
  for (const item of items) {
    lines.push(`## ${item.id}`);
    for (const key of ['debtor', 'creditor', 'action', 'status', 'recorded_at', 'due_at', 'sources']) {
      if (item[key]) lines.push(`- ${key}: ${item[key]}`);
    }
    if (item.changes?.length) {
      lines.push('- changes:');
      for (const change of item.changes) lines.push(`  - ${change}`);
    }
    lines.push('');
  }
  return `${lines.join('\n').trim()}\n`;
}

function load(workspace) {
  const file = collectionPath(workspace);
  try { return { file, items: parseCollection(fs.readFileSync(file, 'utf8')) }; }
  catch (error) {
    if (error.code === 'ENOENT') return { file, items: [] };
    throw error;
  }
}

function save(workspace, file, items) {
  safeWritePath(workspace, file);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, render(items), 'utf8');
}

function requireFields(input, names) {
  const failures = [];
  for (const name of names) {
    if (typeof input[name] !== 'string' || !input[name].trim()) {
      failures.push(failure({
        path: '.rbtv/memory/commitments.md', operation: 'commitment',
        requirement: `${name} is missing`, expected: `non-empty ${name}`, reason: `commitment requires ${name}`,
      }));
    }
  }
  if (failures.length) throw refusalError(failures);
}

function createCommitment(workspace, input, now = Date.now()) {
  requireFields(input, ['debtor', 'creditor', 'action', 'sources']);
  return withMemoryLock(workspace, () => {
    const { file, items } = load(workspace);
    const id = input.id || randomUUID();
    if (items.some((item) => item.id === id)) {
      throw refusalError([failure({
        path: '.rbtv/memory/commitments.md', operation: 'commitment',
        requirement: 'id already exists', expected: 'a new id', reason: `commitment id already exists: ${id}`,
      })]);
    }
    items.push({
      id, debtor: input.debtor.trim(), creditor: input.creditor.trim(), action: input.action.trim(),
      status: 'open', recorded_at: new Date(now).toISOString(), due_at: input.due_at || '',
      sources: input.sources.trim(), changes: [],
    });
    save(workspace, file, items);
    return { path: file, id, status: 'open' };
  });
}

function annotateCommitment(workspace, id, note, now = Date.now()) {
  return withMemoryLock(workspace, () => {
    const { file, items } = load(workspace);
    const item = items.find((row) => row.id === id);
    if (!item) throw refusalError([failure({ path: '.rbtv/memory/commitments.md', operation: 'commitment', requirement: 'id not found', expected: 'an existing commitment id', reason: `commitment not found: ${id}` })]);
    item.changes = [...(item.changes || []), `${new Date(now).toISOString()} annotation: ${note}`];
    save(workspace, file, items);
    return { path: file, id, status: item.status, annotated: true };
  });
}

function setCommitmentStatus(workspace, id, status, { statement, artifact, actor, now = Date.now() }) {
  if (!['done', 'cancelled'].includes(status)) {
    throw refusalError([failure({ path: '.rbtv/memory/commitments.md', operation: 'commitment', requirement: 'status not allowed', expected: 'done or cancelled', reason: 'commitment status must be done or cancelled' })]);
  }
  const explicit = typeof statement === 'string' && statement.trim();
  const checkable = typeof artifact === 'string' && artifact.trim();
  if (!explicit && !checkable) {
    return annotateCommitment(workspace, id, `agent report from ${actor || 'agent'} is not completion`, now);
  }
  return withMemoryLock(workspace, () => {
    const { file, items } = load(workspace);
    const item = items.find((row) => row.id === id);
    if (!item) throw refusalError([failure({ path: '.rbtv/memory/commitments.md', operation: 'commitment', requirement: 'id not found', expected: 'an existing commitment id', reason: `commitment not found: ${id}` })]);
    const prior = item.status;
    item.changes = [...(item.changes || []), `${new Date(now).toISOString()} ${prior} -> ${status} sources ${item.sources}`];
    item.status = status;
    if (explicit) item.sources = `${item.sources}; ${statement.trim()}`;
    if (checkable) item.sources = `${item.sources}; artifact ${artifact.trim()}`;
    save(workspace, file, items);
    return { path: file, id, status, prior };
  });
}

function missDueDate(workspace, id, now = Date.now()) {
  return withMemoryLock(workspace, () => {
    const { file, items } = load(workspace);
    const item = items.find((row) => row.id === id);
    if (!item) throw refusalError([failure({ path: '.rbtv/memory/commitments.md', operation: 'commitment', requirement: 'id not found', expected: 'an existing commitment id', reason: `commitment not found: ${id}` })]);
    const before = JSON.stringify(item);
    const after = JSON.stringify(parseCollection(render(items)).find((row) => row.id === id));
    if (before !== after) throw new Error('due date changed the commitment');
    return { path: file, id, status: item.status, changed: false, now };
  });
}

module.exports = { collectionPath, createCommitment, annotateCommitment, setCommitmentStatus, missDueDate, parseCollection };
