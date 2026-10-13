'use strict';

const fs = require('node:fs');
const path = require('node:path');
const store = require('./store.js');

const HOUR = 60 * 60 * 1000;
const WATCH_MS = 48 * HOUR;

function today() {
  return new Date().toISOString().slice(0, 10);
}

function readText(file) {
  try { return fs.readFileSync(file, 'utf8'); } catch { return null; }
}

function agentDirs(installation) {
  const root = path.join(installation, '.rbtv', 'agents');
  if (!fs.existsSync(root)) return [];
  return fs.readdirSync(root, { withFileTypes: true }).filter((entry) => entry.isDirectory()).map((entry) => entry.name);
}

function inboxCandidates(installation, home) {
  const text = readText(path.join(installation, '.rbtv', 'memory', 'inbox.md'));
  if (!text) return [];
  const lines = text.split(/\r?\n/).filter((line) => /^- .+ \(\d{4}-\d{2}-\d{2} · .+\)$/.test(line));
  if (!home) return lines;
  const covered = new Set();
  for (const receipt of store.readReceipts(home)) {
    if (receipt.outcome !== 'published' && receipt.outcome !== 'migrated') continue;
    for (const item of receipt.items || []) {
      for (const source of item.sources || []) if (typeof source === 'string') covered.add(source);
    }
  }
  return lines.filter((line) => !covered.has(line));
}

function watchOuts(installation) {
  const found = [];
  for (const slug of agentDirs(installation)) {
    const text = readText(path.join(installation, '.rbtv', 'agents', slug, '_artifacts', 'board.md'));
    if (!text) continue;
    const lines = text.split(/\r?\n/);
    let section = '';
    for (const line of lines) {
      if (line.startsWith('## ')) section = line.slice(3);
      else if (section === 'Watch-outs' && line.trim()) found.push(`${slug}:${line}`);
    }
  }
  return found;
}

function expiries(installation, date) {
  const found = [];
  function walk(dir) {
    if (!fs.existsSync(dir)) return;
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith('.md')) {
        const text = readText(full) || '';
        for (const match of text.matchAll(/\buntil (\d{4}-\d{2}-\d{2})/g)) {
          if (match[1] < date) found.push(path.relative(installation, full));
        }
      }
    }
  }
  walk(path.join(installation, '.rbtv', 'memory'));
  walk(path.join(installation, '.rbtv', 'agents'));
  return found;
}

function maintenanceDue(home, installation, now) {
  const row = store.readJson(store.maintenanceFile(home), null);
  if (row && Number.isFinite(row.dueAt) && row.dueAt <= now) return ['due'];
  const facts = path.join(installation, '.rbtv', 'memory', 'knowledge');
  if (!fs.existsSync(facts)) return [];
  for (const name of fs.readdirSync(facts)) {
    if (!name.endsWith('.md')) continue;
    const lines = (readText(path.join(facts, name)) || '').split(/\r?\n/).filter((line) => line.trim());
    if (lines.length >= 100) return [name];
  }
  return [];
}

function pendingBatches(home) {
  const consumed = new Set(store.readConsumed(home).batches);
  return store.listEvidence(home).filter((name) => !consumed.has(name));
}

function work(home, installation, now = Date.now()) {
  const date = new Date(now).toISOString().slice(0, 10);
  const reasons = [];
  if (inboxCandidates(installation, home).length) reasons.push('inbox');
  if (watchOuts(installation).length) reasons.push('watch-out');
  if (expiries(installation, date).length) reasons.push('expiry');
  if (maintenanceDue(home, installation, now).length) reasons.push('maintenance');
  if (pendingBatches(home).length) reasons.push('evidence');
  return reasons;
}

function check(home, installation, now = Date.now()) {
  const reasons = work(home, installation, now);
  store.writeLiveness(home, now);
  if (!reasons.length) return { new: false };
  return { new: true, details: { reasons } };
}

function watchdog(home, now = Date.now()) {
  const last = store.readLiveness(home).lastSuccessAt;
  if (last == null || now - last > WATCH_MS) {
    return { new: true, details: { reason: 'no successful check or apply within 48 hours', lastSuccessAt: last } };
  }
  return { new: false };
}

function seedLiveness(home, at) {
  const parsed = Number(at);
  if (!Number.isFinite(parsed)) throw new Error('liveness --at requires epoch milliseconds');
  store.writeLiveness(home, parsed);
  return { seeded: true, lastSuccessAt: parsed };
}

module.exports = { check, watchdog, seedLiveness, work, today, WATCH_MS };
