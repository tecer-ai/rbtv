'use strict';

const fs = require('node:fs');
const path = require('node:path');
const store = require('./store.js');

function occasionNow(now = Date.now()) {
  const date = new Date(now);
  const utc = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const day = utc.getUTCDay() || 7;
  utc.setUTCDate(utc.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(utc.getUTCFullYear(), 0, 1));
  const week = Math.ceil((((utc - yearStart) / 86400000) + 1) / 7);
  return `${utc.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

function conflictId(text) {
  return require('node:crypto').createHash('sha256').update(text).digest('hex').slice(0, 12);
}

function knownConflicts(home) {
  return store.readJson(path.join(store.runtime(home), 'conflicts.json'), { items: [] });
}

function reportText(occasion, applied, approvals, conflicts) {
  const lines = [`Weekly report ${occasion}`, '', 'Applied'];
  if (!applied.length) lines.push('(none)');
  for (const item of applied) {
    lines.push(`${item.ref}`);
    lines.push(`path: ${item.path}`);
    lines.push('before:');
    lines.push(item.before == null ? '(new file)' : item.before);
    lines.push('after:');
    lines.push(item.after == null ? '(removed)' : item.after);
    lines.push(`sources: ${(item.sources || []).join(', ') || '(none)'}`);
    lines.push('');
  }
  lines.push('Pending global-rule approvals');
  if (!approvals.length) lines.push('(none)');
  for (const row of approvals) lines.push(`${row.id} ${row.text}`);
  lines.push('', 'Unresolved conflicts');
  if (!conflicts.length) lines.push('(none)');
  for (const row of conflicts) lines.push(`${row.id} ${row.repeated ? 'unchanged' : 'new'} ${row.text}`);
  return lines.join('\n');
}

function uncoveredItems(home, acknowledged) {
  const covered = new Set(acknowledged);
  const items = [];
  for (const receipt of store.readReceipts(home)) {
    if (receipt.outcome !== 'published' && receipt.outcome !== 'migrated') continue;
    for (const item of receipt.items || []) {
      if (!covered.has(item.ref)) items.push(item);
    }
  }
  return items;
}

function freezeReport(home, occasion) {
  const dir = store.reportsDir(home);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${occasion}.json`);
  if (fs.existsSync(file)) return store.readJson(file, null);
  const acked = store.readJson(path.join(store.runtime(home), 'acked-items.json'), { refs: [] });
  const conflicts = knownConflicts(home);
  const approvals = conflicts.items.filter((row) => row.kind === 'approval');
  const pending = conflicts.items.filter((row) => row.kind !== 'approval').map((row) => ({
    ...row,
    repeated: acked.conflicts?.includes(row.id) || false,
  }));
  const applied = uncoveredItems(home, acked.refs || []);
  const payload = {
    occasion,
    identity: occasion,
    items: applied.map((item) => item.ref),
    approvals: approvals.map((row) => row.id),
    conflicts: pending.map((row) => row.id),
    text: reportText(occasion, applied, approvals, pending),
    acked: false,
  };
  const tmp = `${file}.${process.pid}.tmp`;
  const fd = fs.openSync(tmp, 'w', 0o600);
  try {
    fs.writeFileSync(fd, `${JSON.stringify(payload, null, 2)}\n`);
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
  try {
    fs.linkSync(tmp, file);
  } catch (error) {
    fs.unlinkSync(tmp);
    if (error.code === 'EEXIST') return store.readJson(file, null);
    throw error;
  }
  fs.unlinkSync(tmp);
  return payload;
}

function report(home, occasion) {
  const id = occasion || occasionNow();
  const payload = freezeReport(home, id);
  return { occasion: id, text: payload.text, items: payload.items, acked: payload.acked, identity: payload.identity };
}

function reportAck(home, occasion) {
  const id = occasion || occasionNow();
  const file = path.join(store.reportsDir(home), `${id}.json`);
  const payload = store.readJson(file, null);
  if (!payload) throw new Error(`no frozen report for ${id}; run report first`);
  payload.acked = true;
  store.writeJson(file, payload);
  const acked = store.readJson(path.join(store.runtime(home), 'acked-items.json'), { refs: [], conflicts: [] });
  acked.refs = [...new Set([...(acked.refs || []), ...payload.items])];
  acked.conflicts = [...new Set([...(acked.conflicts || []), ...payload.conflicts])];
  acked.occasions = [...new Set([...(acked.occasions || []), id])];
  store.writeJson(path.join(store.runtime(home), 'acked-items.json'), acked);
  return { occasion: id, acked: true, items: payload.items, identity: payload.identity };
}

function noteConflicts(home, conflicts) {
  const current = knownConflicts(home);
  const seen = new Map(current.items.map((row) => [row.id, row]));
  for (const text of conflicts) {
    const id = conflictId(text);
    if (seen.has(id)) continue;
    seen.set(id, { id, text, kind: text.startsWith('Pending global rule:') ? 'approval' : 'conflict' });
  }
  store.writeJson(path.join(store.runtime(home), 'conflicts.json'), { items: [...seen.values()] });
}

module.exports = { report, reportAck, noteConflicts, occasionNow, freezeReport };
