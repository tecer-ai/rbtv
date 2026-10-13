'use strict';

const fs = require('node:fs');
const path = require('node:path');

function runtime(home) {
  return path.join(path.resolve(home), 'runtime', 'albert');
}

function readJson(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (error) {
    if (error.code === 'ENOENT') return fallback;
    throw error;
  }
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const text = `${JSON.stringify(value, null, 2)}\n`;
  const tmp = `${file}.tmp`;
  const fd = fs.openSync(tmp, 'w', 0o600);
  try {
    fs.writeFileSync(fd, text);
    fs.fsyncSync(fd);
  } finally { fs.closeSync(fd); }
  fs.renameSync(tmp, file);
  return file;
}

function agentHome() {
  const home = process.env.RBTV_AGENT_HOME || process.cwd();
  if (!home) throw new Error('RBTV_AGENT_HOME is required');
  return path.resolve(home);
}

function livenessFile(home) { return path.join(runtime(home), 'liveness.json'); }
function cursorFile(home) { return path.join(runtime(home), 'cursors.json'); }
function consumedFile(home) { return path.join(runtime(home), 'consumed.json'); }
function maintenanceFile(home) { return path.join(runtime(home), 'maintenance.json'); }
function runsDir(home) { return path.join(runtime(home), 'runs'); }
function evidenceDir(home) { return path.join(runtime(home), 'evidence'); }
function receiptsDir(home) { return path.join(runtime(home), 'receipts'); }
function reportsDir(home) { return path.join(runtime(home), 'reports'); }
function diagnosticsDir(home) { return path.join(runtime(home), 'diagnostics'); }

function readLiveness(home) {
  return readJson(livenessFile(home), { lastSuccessAt: null });
}

function writeLiveness(home, at) {
  writeJson(livenessFile(home), { lastSuccessAt: at });
}

function readCursors(home) { return readJson(cursorFile(home), {}); }
function writeCursors(home, cursors) { writeJson(cursorFile(home), cursors); }

function readConsumed(home) { return readJson(consumedFile(home), { batches: [] }); }
function writeConsumed(home, consumed) { writeJson(consumedFile(home), consumed); }

function runFile(home, id) { return path.join(runsDir(home), id, 'run.json'); }
function readRun(home, id) {
  const run = readJson(runFile(home, id), null);
  if (!run) throw new Error(`prepared run not found: ${id}; run prepare`);
  return run;
}
function writeRun(home, run) { writeJson(runFile(home, run.id), run); }

function listEvidence(home) {
  const dir = evidenceDir(home);
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((name) => name.endsWith('.json')).sort();
}

function appendReceipt(home, receipt) {
  const dir = receiptsDir(home);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${receipt.id}.json`);
  if (fs.existsSync(file)) return file;
  const text = `${JSON.stringify(receipt, null, 2)}\n`;
  const fd = fs.openSync(file, 'wx', 0o600);
  try {
    fs.writeFileSync(fd, text);
    fs.fsyncSync(fd);
  } finally { fs.closeSync(fd); }
  return file;
}

function readReceipts(home) {
  const dir = receiptsDir(home);
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((name) => name.endsWith('.json')).sort()
    .map((name) => readJson(path.join(dir, name), null)).filter(Boolean);
}

function retainBytes(home, name, bytes) {
  const dir = diagnosticsDir(home);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, name);
  fs.writeFileSync(file, bytes, { mode: 0o600 });
  return file;
}

module.exports = {
  runtime, readJson, writeJson, agentHome, livenessFile, cursorFile, consumedFile, maintenanceFile,
  runsDir, evidenceDir, receiptsDir, reportsDir, diagnosticsDir, readLiveness, writeLiveness,
  readCursors, writeCursors, readConsumed, writeConsumed, runFile, readRun, writeRun, listEvidence,
  appendReceipt, readReceipts, retainBytes,
};
