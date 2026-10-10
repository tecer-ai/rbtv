'use strict';

// cast — `cast api` — the API-worker runner. GOOGLE ONLY since 2026-08-20 (route redesign §7).
// It generates and edits images and does nothing else: the one supported api model is the Google
// image-generation worker, and a call without --image is refused. Text and code work run through
// a harness; the general Gemini models have opencode CLI rows, as DeepSeek does.
//
// File-in / file-out by design, with `-p TEXT` added 2026-08-20 so the prompt can be typed the
// same way the main launch verb takes it.

const path = require('path');
const fs = require('fs');
const { spawnSync } = require('child_process');
const { ROWS } = require('../supported-models');
const { providers: PROVIDERS } = require('../providers.json');

const { fail, taskFile, taskText } = require('./core');
const { gate } = require('./model-catalog');

const API_USAGE = 'cast api <model> <effort 1-5> (-p TEXT | -f FILE) --output-folder DIR --image [--input-image PATH ...] [--target-file PATH] [--timeout N] [--extra-params JSON] [--dry-run]';
const API_RUNNER = path.join(__dirname, '..', 'api', 'run.py');

function apiRows() {
  return ROWS.filter((r) => r.mode === 'api');
}

// The runner names a provider by the stem of its key variable (GEMINI_API_KEY -> gemini).
function apiProvider(row) {
  return PROVIDERS[row.provider].env_var.replace(/_API_KEY$/i, '').toLowerCase();
}

function parseApiArgs(rawArgv) {
  let dryRun = false;
  let image = false;
  let promptFile = null;
  let promptText = null;
  let promptSource = null;
  let outputFolder = null;
  let targetFile = null;
  let timeout = null;
  let extraParamsRaw = null;
  const inputImages = [];
  const positional = [];
  for (let i = 0; i < rawArgv.length; i++) {
    const a = rawArgv[i];
    if (a === '-h' || a === '--help') return { help: true };
    if (a === '--dry-run') {
      dryRun = true;
    } else if (a === '--image') {
      image = true;
    } else if (a === '--input-image') {
      const val = rawArgv[++i];
      if (val === undefined) fail('refused: --input-image requires an argument');
      inputImages.push(val);
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
  return { dryRun, image, promptFile, promptText, outputFolder, targetFile,
    timeout, extraParamsRaw, inputImages, positional };
}

// The file a `-p TEXT` task is saved to, in the output folder.
const TASK_MD = 'task.md';

// The runner is file-in, so `-p TEXT` is materialized into the output folder next to the run's own
// artifacts — one file, beside the result it produced, instead of a temp nobody can find later.
function materializeTask(text, outputFolder) {
  fs.mkdirSync(outputFolder, { recursive: true });
  const file = path.join(path.resolve(outputFolder), TASK_MD);
  fs.writeFileSync(file, text.endsWith('\n') ? text : `${text}\n`, 'utf8');
  return file;
}

function runApi(rawArgv) {
  const parsed = parseApiArgs(rawArgv);
  if (parsed.help) {
    process.stdout.write(`Usage: ${API_USAGE}\n`);
    process.exit(0);
  }
  if (parsed.positional.length !== 2) fail(`usage: ${API_USAGE}`);
  // An image model has no effort dial: the number is checked, as every cast form checks it, and
  // changes nothing in the request.
  const [model, effortStr] = parsed.positional;
  const n = Number(effortStr);
  if (!Number.isInteger(n) || n < 1 || n > 5) fail(`effort must be an integer 1-5, got: ${effortStr}`);
  if (parsed.promptFile === null && parsed.promptText === null) {
    fail(`refused: exactly one of -p TEXT or -f FILE is required\nusage: ${API_USAGE}`);
  }
  // The task is read as a launch reads it, before anything is written or started: a -f file that
  // cannot be read and a task with no text are refused here, with and without --dry-run.
  if (parsed.promptFile !== null) taskText(taskFile(parsed.promptFile), `the -f file ${parsed.promptFile}`);
  else taskText(parsed.promptText, 'the -p text');
  if (!parsed.outputFolder) fail(`refused: --output-folder DIR is required\nusage: ${API_USAGE}`);
  if (!parsed.image) {
    fail(`refused: cast api generates and edits images and nothing else: pass --image\ntext and code work run through a harness: cast route -h\nusage: ${API_USAGE}`);
  }

  const row = apiRows().find((r) => r.model === model || r.id === model);
  if (!row) {
    const known = apiRows().map((r) => r.model || '(blank — owner has not filled the model id)').join(', ');
    fail(`refused: '${model}' is not a known api model\nknown: ${known}`);
  }
  try { gate(row.harness, row.model, process.cwd()); } catch (e) { fail(e.message); }
  const provider = apiProvider(row);
  if (!provider) fail(`refused: api row '${row.model}' has no provider`);
  // A blank id is the not-yet-chosen image model. Refuse HERE rather than sending an empty model
  // name at the provider and reading its 404 as something else.
  if (!row.id) {
    fail('refused: that api row has no model id yet — the owner fills it in the model catalog and supported-models.js (both, identically)');
  }

  let extra = {};
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
    extra = parsedExtra;
  }

  // --dry-run composes the argv and prints it WITHOUT writing the -p task file or calling
  // anything: a dry run must spend nothing and leave nothing behind.
  const promptFile = parsed.promptFile !== null
    ? parsed.promptFile
    : (parsed.dryRun ? path.join(path.resolve(parsed.outputFolder), TASK_MD)
      : materializeTask(parsed.promptText, parsed.outputFolder));

  const argv = [
    'python', API_RUNNER,
    '--provider', provider,
    '--model', row.id,
    '--prompt-file', promptFile,
    '--output-folder', parsed.outputFolder,
  ];
  if (parsed.targetFile) argv.push('--target-file', parsed.targetFile);
  if (parsed.timeout != null) argv.push('--timeout', String(parsed.timeout));
  for (const imgPath of parsed.inputImages) argv.push('--input-image', imgPath);
  if (Object.keys(extra).length) argv.push('--extra-params', JSON.stringify(extra));

  if (parsed.dryRun) {
    process.stdout.write(`${JSON.stringify({ argv, cwd: process.cwd() })}\n`);
    process.exit(0);
  }

  const [cmd, ...args] = argv;
  const res = spawnSync(cmd, args, { stdio: 'inherit' });
  if (res.error) fail(`api runner failed: ${res.error.message}`);
  process.exit(res.status === null ? 1 : res.status);
}

module.exports = {
  API_USAGE, API_RUNNER, apiRows, apiProvider,
  parseApiArgs, materializeTask, runApi,
};
