'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const store = require('./store.js');
const { git, commitForRun } = require('./git.js');
const { noteConflicts } = require('./report.js');

let writes = 0;
function fault(point) {
  if (process.env.ALBERT_FAULT !== point) return;
  if (point === 'during-write' && ++writes < 2) return;
  const error = new Error(`fault ${point}`);
  error.code = 'fault';
  throw error;
}

function readFile(file) {
  try { return fs.readFileSync(file); } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

function stalePath(lib, installation, run) {
  for (const [rel, text] of Object.entries(run.files)) {
    const current = readFile(lib.safePath(installation, rel));
    const now = current == null ? null : current.toString('utf8');
    if (now !== text) return rel;
  }
  return null;
}

function advanceAfterCommit(home, run) {
  const cursors = store.readCursors(home);
  for (const source of run.sources) {
    cursors[source.source] = {
      sourceAgent: source.sourceAgent,
      sourceCursor: source.sourceCursor,
      ceiling: source.ceiling,
      positions: source.positions,
      run: run.id,
    };
  }
  store.writeCursors(home, cursors);
  const consumed = store.readConsumed(home);
  consumed.batches = [...new Set([...consumed.batches, ...run.batches])];
  store.writeConsumed(home, consumed);
}

function coveredText(run) {
  return run.sources.map((source) => `${source.source}@${source.ceiling}`).join('\n') || 'none';
}

function itemsFrom(run, operations) {
  return operations.map((op, index) => ({
    n: index + 1,
    ref: `${run.id}#${index + 1}`,
    agent: run.agent,
    path: op.path,
    before: Object.prototype.hasOwnProperty.call(run.files, op.path) ? run.files[op.path] : null,
    after: op.text,
    sources: op.sources,
    explanation: op.explanation,
    messages: run.input.messages,
  }));
}

function writeReceipt(home, run, outcome, commit, items) {
  const receipt = {
    id: run.receiptId || crypto.randomUUID(),
    createdAt: Date.now(),
    outcome,
    runId: run.id,
    commit: commit || null,
    sources: run.sources.map((source) => ({
      source: source.source,
      sourceKind: source.sourceKind,
      sourceAgent: source.sourceAgent,
      sourceCursor: source.sourceCursor,
      ceiling: source.ceiling,
      positions: source.positions,
    })),
    items,
  };
  const file = store.appendReceipt(home, receipt);
  run.receiptId = receipt.id;
  run.phase = 'receipt';
  store.writeRun(home, run);
  fault('after-receipt');
  return { receipt, file };
}

function finish(home, run, commit) {
  if (!run.receiptId) {
    const existing = store.readReceipts(home).find((row) => row.runId === run.id);
    if (existing) run.receiptId = existing.id;
  }
  if (run.phase !== 'done') {
    if (!run.receiptId) writeReceipt(home, run, commit ? 'published' : 'no-change', commit, run.items || []);
    advanceAfterCommit(home, run);
    run.phase = 'done';
    run.commit = commit || run.commit;
    store.writeRun(home, run);
  }
  store.writeLiveness(home, Date.now());
  return { ok: true, run: run.id, outcome: commit ? 'published' : 'no-change', commit: commit || null, receipt: run.receiptId };
}

function recover(lib, home, installation, run) {
  const conflicts = [];
  const intended = run.intended || { files: {} };
  const same = (current, text) => {
    if (current == null && (text == null)) return true;
    if (current == null || text == null) return false;
    return current.equals(Buffer.from(text, 'utf8'));
  };
  for (const [rel, written] of Object.entries(intended.files || {})) {
    const file = lib.safePath(installation, rel);
    const current = readFile(file);
    if (same(current, written)) {
      const original = run.files[rel];
      if (original == null) fs.unlinkSync(file);
      else lib.writeText(file, original);
    } else if (same(current, Object.prototype.hasOwnProperty.call(run.files, rel) ? run.files[rel] : null)) {
      continue;
    } else conflicts.push(rel);
  }
  if (conflicts.length) {
    return { ok: false, recovered: false, conflicts, message: `later bytes preserved: ${conflicts.join(', ')}` };
  }
  run.phase = 'prepared';
  run.intended = null;
  store.writeRun(home, run);
  return { ok: true, recovered: true, run: run.id };
}

function printFailures(failures) {
  const lines = [];
  failures.forEach((row, index) => {
    lines.push(`failure ${index + 1}`);
    lines.push(`path: ${row.path || '(proposal)'}`);
    lines.push(`operation: ${row.operation || '(proposal)'}`);
    lines.push(`requirement: ${row.requirement}`);
    lines.push(`expected: ${row.expected}`);
    lines.push(`reason: ${row.reason}`);
  });
  return lines.join('\n');
}

function refuseProposal(home, run, raw, failures) {
  const kept = store.retainBytes(home, `${run.id}.bin`, Buffer.from(raw));
  return { ok: false, retained: kept, failures, message: printFailures(failures) };
}

function apply(lib, home, installation, runId, proposalPath) {
  const run = store.readRun(home, runId);
  const found = commitForRun(installation, run.id);
  if (found || run.phase === 'published' || run.phase === 'receipt' || run.phase === 'done') {
    return finish(home, run, found || run.commit);
  }
  if (run.phase === 'writing') return recover(lib, home, installation, run);
  const raw = fs.readFileSync(proposalPath, 'utf8');
  const validated = lib.validateProposalResult(run.input, raw, installation);
  if (!validated.ok) return refuseProposal(home, run, raw, validated.failures);
  if (validated.conflicts?.length) noteConflicts(home, validated.conflicts);
  const operations = validated.operations || [];
  if (!operations.length) {
    const stale = stalePath(lib, installation, run);
    if (stale) {
      return { ok: false, message: `stale snapshot at ${stale}; run a fresh prepare` };
    }
    run.items = [];
    const noted = writeReceipt(home, run, 'no-change', null, []);
    advanceAfterCommit(home, run);
    run.phase = 'done';
    store.writeRun(home, run);
    store.writeLiveness(home, Date.now());
    return { ok: true, run: run.id, outcome: 'no-change', commit: null, receipt: noted.receipt.id };
  }
  let checked = false;
  let publish;
  try {
    publish = lib.publishProposal(run.input, raw, installation, {
    write(file, text) {
      if (!checked) {
        checked = true;
        const stale = stalePath(lib, installation, run);
        if (stale) throw Object.assign(new Error(`stale snapshot at ${stale}; run a fresh prepare`), { code: 'stale' });
        run.intended = { files: Object.fromEntries(operations.map((op) => [op.path, op.text])) };
        run.items = itemsFrom(run, operations);
        run.phase = 'writing';
        store.writeRun(home, run);
      }
      lib.writeText(file, text);
      fault('during-write');
    },
    gitCommit(workspace, args, input) {
      if (args[0] === 'commit') {
        input = `Albert ${run.id}\n\ncovered\n${coveredText(run)}\n`;
      }
      return git(workspace, args, input);
    },
    });
  } catch (error) {
    if (error.code === 'fault') throw error;
    if (error.code === 'stale' || /fresh prepare/.test(error.message)) return { ok: false, message: error.message };
    throw error;
  }
  fault('after-commit');
  run.phase = 'published';
  run.commit = publish.commit || null;
  store.writeRun(home, run);
  return finish(home, run, run.commit);
}

module.exports = { apply, stalePath, advanceAfterCommit, printFailures };
