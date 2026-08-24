'use strict';

// cast — `cast api` — the API-worker runner. GOOGLE ONLY since 2026-08-20 (route redesign §7):
// the Gemini chat worker and the Google image-generation worker. Manus and DeepSeek were removed
// with their runner clients — DeepSeek survives through its opencode CLI rows.
//
// File-in / file-out by design, with `-p TEXT` added 2026-08-20 so the prompt can be typed the
// same way the main launch verb takes it.

const path = require('path');
const fs = require('fs');
const { spawnSync } = require('child_process');
const { ROWS } = require('../catalog');

const { fail } = require('./core');

const API_USAGE = 'cast api <model> <effort 1-5> (-p TEXT | -f FILE) --output-folder DIR [--image] [--target-file PATH] [--timeout N] [--grounded] [--extra-params JSON] [--dry-run]';
const API_RUNNER = path.join(__dirname, '..', 'api', 'run.py');

function apiRows() {
  return ROWS.filter((r) => r.mode === 'api');
}

function apiProvider(row) {
  const env = (row.auth && row.auth.env_var) || '';
  return env.replace(/_API_KEY$/i, '').toLowerCase();
}

function parseApiArgs(rawArgv) {
  let dryRun = false;
  let grounded = false;
  let image = false;
  let promptFile = null;
  let promptText = null;
  let promptSource = null;
  let outputFolder = null;
  let targetFile = null;
  let timeout = null;
  let extraParamsRaw = null;
  const positional = [];
  for (let i = 0; i < rawArgv.length; i++) {
    const a = rawArgv[i];
    if (a === '-h' || a === '--help') return { help: true };
    if (a === '--dry-run') {
      dryRun = true;
    } else if (a === '--grounded') {
      grounded = true;
    } else if (a === '--image') {
      image = true;
    } else if (a === '--prompt-file' || a === '-f' || a === '-p') {
      if (promptSource) fail('refused: -p and -f/--prompt-file are mutually exclusive — pass exactly one');
      promptSource = a;
      const val = rawArgv[++i];
      if (val === undefined) fail(`refused: ${a} requires an argument`);
      if (a === '-p') promptText = val;
      else promptFile = val;
    } else if (a === '--output-folder') {
      const val = rawArgv[++i];
      if (val === undefined) fail('refused: --output-folder requires an argument');
      outputFolder = val;
    } else if (a === '--target-file') {
      const val = rawArgv[++i];
      if (val === undefined) fail('refused: --target-file requires an argument');
      targetFile = val;
    } else if (a === '--timeout') {
      const val = rawArgv[++i];
      if (val === undefined) fail('refused: --timeout requires an argument');
      timeout = val;
    } else if (a === '--extra-params') {
      const val = rawArgv[++i];
      if (val === undefined) fail('refused: --extra-params requires an argument');
      extraParamsRaw = val;
    } else if (a.startsWith('-')) {
      fail(`refused: unknown flag '${a}'\nusage: ${API_USAGE}`);
    } else {
      positional.push(a);
    }
  }
  return { dryRun, grounded, image, promptFile, promptText, outputFolder, targetFile,
    timeout, extraParamsRaw, positional };
}

// The runner is file-in, so `-p TEXT` is materialized into the output folder next to the run's own
// artifacts — one file, beside the result it produced, instead of a temp nobody can find later.
function materializePrompt(text, outputFolder) {
  fs.mkdirSync(outputFolder, { recursive: true });
  const file = path.join(path.resolve(outputFolder), 'prompt.md');
  fs.writeFileSync(file, text.endsWith('\n') ? text : `${text}\n`, 'utf8');
  return file;
}

// Gemini's thinking dial rides extra_params: effort 1 turns thinking off, anything above turns the
// dynamic budget on. Image generation has no thinking dial at all.
function mergeApiEffort(row, n, callerExtra) {
  const extra = { ...(callerExtra || {}) };
  const depths = row.depths || [];
  if (depths.includes('off') && depths.includes('on')) {
    if (!Object.prototype.hasOwnProperty.call(extra, 'thinkingBudget')) extra.thinkingBudget = n === 1 ? 0 : -1;
    return { extra, effortWord: n === 1 ? 'off' : 'on' };
  }
  return { extra, effortWord: null };
}

function runApi(rawArgv) {
  const parsed = parseApiArgs(rawArgv);
  if (parsed.help) {
    process.stdout.write(`Usage: ${API_USAGE}\n`);
    process.exit(0);
  }
  if (parsed.positional.length !== 2) fail(`usage: ${API_USAGE}`);
  const [model, effortStr] = parsed.positional;
  const n = Number(effortStr);
  if (!Number.isInteger(n) || n < 1 || n > 5) fail(`effort must be an integer 1-5, got: ${effortStr}`);
  if (parsed.promptFile === null && parsed.promptText === null) {
    fail(`refused: exactly one of -p TEXT or -f FILE is required\nusage: ${API_USAGE}`);
  }
  if (!parsed.outputFolder) fail(`refused: --output-folder DIR is required\nusage: ${API_USAGE}`);
  if (parsed.image && parsed.grounded) fail('refused: --image and --grounded are mutually exclusive');

  const row = apiRows().find((r) => r.model === model || r.id === model);
  if (!row) {
    const known = apiRows().map((r) => r.model || '(blank — owner has not filled the model id)').join(', ');
    fail(`refused: '${model}' is not a known api model\nknown: ${known}`);
  }
  const provider = apiProvider(row);
  if (!provider) fail(`refused: api row '${row.model}' has no provider`);
  // A blank id is the not-yet-chosen image model. Refuse HERE rather than sending an empty model
  // name at the provider and reading its 404 as something else.
  if (!row.id) {
    fail('refused: that api row has no model id yet — the owner fills it in models.csv and catalog.js (both, identically)');
  }

  let callerExtra = null;
  if (parsed.extraParamsRaw) {
    let parsedExtra;
    try { parsedExtra = JSON.parse(parsed.extraParamsRaw); } catch {
      process.stderr.write('ERROR: --extra-params must be a JSON object\n');
      process.exit(1);
    }
    if (!parsedExtra || typeof parsedExtra !== 'object' || Array.isArray(parsedExtra)) {
      process.stderr.write('ERROR: --extra-params must be a JSON object\n');
      process.exit(1);
    }
    callerExtra = parsedExtra;
  }

  const { extra, effortWord } = parsed.image
    ? { extra: { ...(callerExtra || {}) }, effortWord: null }
    : mergeApiEffort(row, n, callerExtra);

  // --dry-run composes the argv and prints it WITHOUT writing the -p prompt file or calling
  // anything: a dry run must spend nothing and leave nothing behind.
  const promptFile = parsed.promptFile !== null
    ? parsed.promptFile
    : (parsed.dryRun ? path.join(path.resolve(parsed.outputFolder), 'prompt.md')
      : materializePrompt(parsed.promptText, parsed.outputFolder));

  const argv = [
    'python', API_RUNNER,
    '--provider', provider,
    '--model', row.id,
    '--prompt-file', promptFile,
    '--output-folder', parsed.outputFolder,
  ];
  if (parsed.targetFile) argv.push('--target-file', parsed.targetFile);
  if (parsed.timeout != null) argv.push('--timeout', String(parsed.timeout));
  if (parsed.grounded) argv.push('--grounded');
  if (parsed.image) argv.push('--image');
  if (Object.keys(extra).length) argv.push('--extra-params', JSON.stringify(extra));

  if (parsed.dryRun) {
    process.stdout.write(`${JSON.stringify({ argv, cwd: process.cwd(), effort_word: effortWord })}\n`);
    process.exit(0);
  }

  const [cmd, ...args] = argv;
  const res = spawnSync(cmd, args, { stdio: 'inherit' });
  if (res.error) fail(`api runner failed: ${res.error.message}`);
  process.exit(res.status === null ? 1 : res.status);
}

module.exports = {
  API_USAGE, API_RUNNER, apiRows, apiProvider,
  parseApiArgs, materializePrompt, mergeApiEffort, runApi,
};
