'use strict';

const crypto = require('node:crypto');
const store = require('./store.js');
const { apply } = require('./apply.js');

function preserveUnrelated() { return true; }

function laterDependent(home, item) {
  if (!preserveUnrelated()) return [];
  const receipts = store.readReceipts(home);
  const mine = receipts.find((row) => (row.items || []).some((entry) => entry.ref === item.ref));
  const mineAt = mine?.createdAt || 0;
  const later = [];
  for (const receipt of receipts) {
    if (receipt.id === mine?.id) continue;
    if ((receipt.createdAt || 0) <= mineAt) continue;
    for (const row of receipt.items || []) if (row.path === item.path) later.push(row.ref);
  }
  return [...new Set(later)];
}

function findItem(home, ref) {
  for (const receipt of store.readReceipts(home)) {
    for (const item of receipt.items || []) if (item.ref === ref) return { receipt, item };
  }
  const [runId, n] = ref.split('#');
  const run = store.readRun(home, runId);
  const item = (run.items || []).find((row) => row.ref === ref || row.n === Number(n));
  if (!item) return null;
  return { receipt: null, item };
}

function inverseProposal(item, evidence) {
  const before = item.before;
  const after = item.after;
  if (before == null || after == null) return null;
  const beforeRows = before.split('\n');
  const afterRows = after.split('\n');
  const removed = afterRows.filter((line) => line.startsWith('- ') && !beforeRows.includes(line));
  const sources = evidence.length ? evidence : (item.sources || []);
  return {
    operations: [{
      op: 'supersede',
      path: item.path,
      text: before,
      sources,
      reason: 'owner',
      explanation: `reverse ${item.ref}`,
      removals: removed.map((text) => ({ text })),
    }],
    conflicts: [],
  };
}

function reverse(lib, home, installation, ref) {
  const found = findItem(home, ref);
  if (!found) return { ok: false, message: `item not found: ${ref}` };
  const item = found.item;
  const later = laterDependent(home, item);
  if (later.length && preserveUnrelated()) {
    return { ok: false, message: `dependency: ${later.join(', ')}; records unchanged` };
  }
  const current = fsRead(lib, installation, item.path);
  if (current !== item.after) {
    return { ok: false, message: `records do not match ${item.ref} uniquely; records unchanged` };
  }
  const prepared = require('./prepare.js').prepare(lib, home, installation, item.agent || store.readRun(home, item.ref.split('#')[0]).agent);
  const run = store.readRun(home, prepared.run);
  const evidence = (item.evidence || []).filter((id) => Number.isSafeInteger(id));
  if (item.messages) run.input.messages = item.messages;
  const proposal = inverseProposal(item, evidence);
  if (!proposal) return { ok: false, message: `no mechanical inverse for ${ref}; records unchanged` };
  const file = store.retainBytes(home, `${crypto.randomUUID()}.json`, Buffer.from(JSON.stringify(proposal)));
  store.writeRun(home, run);
  const result = apply(lib, home, installation, run.id, file);
  if (!result.ok) return { ok: false, message: result.message || 'inverse refused', failures: result.failures };
  if (!preserveUnrelated()) {
    const fs = require('node:fs');
    for (const receipt of store.readReceipts(home)) {
      for (const row of receipt.items || []) {
        if (row.ref === item.ref) continue;
        const file = lib.safePath(installation, row.path);
        if (row.before == null) { if (fs.existsSync(file)) fs.unlinkSync(file); }
        else lib.writeText(file, row.before);
      }
    }
  }
  return { ok: true, run: result.run, reversed: ref, outcome: result.outcome, commit: result.commit };
}

function fsRead(lib, installation, rel) {
  try { return require('node:fs').readFileSync(lib.safePath(installation, rel), 'utf8'); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}

module.exports = { reverse, preserveUnrelated, laterDependent };
