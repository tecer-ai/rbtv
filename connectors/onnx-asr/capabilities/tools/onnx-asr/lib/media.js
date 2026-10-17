'use strict';

// In-process media adapter; one Python worker per installation/model configuration.
// Calls are serialized so simultaneous agents share one model and bounded CPU use.
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const workers = new Map();
const DEFAULT_MODEL = 'nemo-parakeet-tdt-0.6b-v3';
const TIMEOUT_MS = 300_000;

function configuration(workspace, model) {
  if (!workspace) throw new Error('onnx-asr requires an installation');
  const file = path.join(workspace, '.rbtv', 'config', 'onnx-asr', 'config.json');
  let config;
  try { config = JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (error) { throw new Error(`cannot read ${file}: ${error.message}`); }
  if (!config || typeof config !== 'object' || Array.isArray(config)) throw new Error(`${file}: expected an object`);
  for (const key of Object.keys(config)) {
    if (!['python', 'model_path', 'threads'].includes(key)) throw new Error(`${file}: unknown field ${key}`);
  }
  if (typeof config.model_path !== 'string' || !config.model_path.trim()) throw new Error(`${file}: model_path required`);
  if (config.python !== undefined && (typeof config.python !== 'string' || !config.python.trim())) throw new Error(`${file}: python must name an executable`);
  const threads = config.threads ?? 8;
  if (!Number.isInteger(threads) || threads < 1 || threads > 64) throw new Error(`${file}: threads must be between 1 and 64`);
  const python = config.python || 'python3';
  return { python: /[\\/]/.test(python) ? path.resolve(workspace, python) : python,
    model_path: path.resolve(workspace, config.model_path), threads, model: model || DEFAULT_MODEL };
}

class Resident {
  constructor(config, spawnImpl = spawn) {
    this.child = null;
    this.pending = null;
    this.tail = Promise.resolve();
    this.config = config;
    this.spawn = spawnImpl;
    this.closed = false;
  }

  start() {
    if (this.child) return;
    const child = this.spawn(this.config.python, ['-u', path.join(__dirname, 'worker.py'), JSON.stringify(this.config)],
      { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true,
        env: Object.fromEntries(Object.entries({ PATH: process.env.PATH, HOME: process.env.HOME,
          SystemRoot: process.env.SystemRoot, WINDIR: process.env.WINDIR, TEMP: process.env.TEMP,
          TMP: process.env.TMP, LANG: process.env.LANG, PYTHONUTF8: '1',
          HF_HUB_OFFLINE: '1', TRANSFORMERS_OFFLINE: '1' }).filter(([, value]) => value !== undefined)) });
    this.child = child;
    // Drain stderr without publishing paths, audio or model-library diagnostics into owner replies.
    child.stderr.on('data', () => {});
    child.stdin.on('error', (error) => this.fail(error, child));
    child.on('error', (error) => this.fail(new Error(`onnx-asr could not start: ${error.message}`), child));
    child.on('close', (code) => this.fail(new Error(`onnx-asr worker exited ${code}; check Python packages and model_path`), child));
    const lines = createInterface({ input: child.stdout });
    lines.on('line', (line) => {
      if (!this.pending || this.child !== child) return;
      try {
        const result = JSON.parse(line);
        if (result.error) throw new Error(`onnx-asr: ${result.error}`);
        if (typeof result.text !== 'string' || !result.text.trim()) throw new Error('onnx-asr returned no transcript');
        const pending = this.pending;
        this.pending = null;
        clearTimeout(pending.timer);
        pending.resolve(result);
      } catch (error) { this.fail(error, child); }
    });
  }

  fail(error, child = this.child) {
    if (child !== this.child) return;
    const pending = this.pending;
    this.pending = null;
    this.child = null;
    child?.kill();
    if (pending) { clearTimeout(pending.timer); pending.reject(error); }
  }

  transcribe(file) {
    const run = this.tail.then(() => new Promise((resolve, reject) => {
      if (this.closed) throw new Error('onnx-asr stopped');
      this.start();
      const timer = setTimeout(() => this.fail(new Error('onnx-asr transcription timed out')), TIMEOUT_MS);
      this.pending = { resolve, reject, timer };
      this.child.stdin.write(`${JSON.stringify({ file })}\n`);
    }));
    this.tail = run.catch(() => {});
    return run;
  }

  close() { this.closed = true; this.fail(new Error('onnx-asr stopped')); }
}

async function transcribe({ file, model, workspace }) {
  if (typeof file !== 'string' || !fs.statSync(file).isFile() || !fs.statSync(file).size) {
    throw new Error('onnx-asr requires a nonempty audio file');
  }
  const config = configuration(workspace, model);
  const key = JSON.stringify(config);
  if (!workers.has(key)) {
    // A changed selection releases the previous weights for this model directory.
    for (const [oldKey, worker] of workers) {
      if (worker.config.model_path === config.model_path) { worker.close(); workers.delete(oldKey); }
    }
    workers.set(key, new Resident(config));
  }
  return workers.get(key).transcribe(path.resolve(file));
}

function close() {
  for (const worker of workers.values()) worker.close();
  workers.clear();
}

module.exports = { operations: { 'media.transcribe': transcribe }, close, Resident, configuration, DEFAULT_MODEL };
