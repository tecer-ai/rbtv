'use strict';

// cast — `cast doctor`: what this machine can launch, read from cast's own data only.
//
// Two checks: which harness programs are on PATH, and which selected models have their provider's
// login present. Local files and the environment only: no network call, no other program started.
// Accounts, saved logins and plan usage belong to `rbtv providers`, which the report points to.

const fs = require('fs');
const path = require('path');
const { ROWS } = require('../supported-models');
const { providers: PROVIDERS } = require('../providers.json');
const { HARNESSES, fail } = require('./core');
const { installationRoot } = require('./installation');
const { expandHome, isAvailable, readJson, unavailableReason } = require('./route');
const { resolveWindowsExecutable } = require('./win-exec');

const NEXT = ['rbtv providers list', 'rbtv providers usage'];

// The words of `cast doctor`: --json and nothing else. Every other word is refused, so a mistyped
// command never prints a report that looks like an answer to it.
function doctorArgs(args) {
  const refuse = (what, why) => fail(`refused: ${what}\n${why}\nNothing was checked.\ncast doctor -h`);
  let json = false;
  for (const a of args) {
    if (a === '--json') json = true;
    else if (a.startsWith('-')) refuse(`'${a}' is not a cast doctor option`, 'cast doctor takes --json only');
    else refuse(`cast doctor takes no name, got '${a}'`, 'it checks every harness and every selected model; it takes --json only');
  }
  return { json };
}

// Where PATH would find the program, or null. Read from the folders of PATH; nothing is started.
function programPath(name) {
  if (process.platform === 'win32') return resolveWindowsExecutable(name, process.env);
  for (const dir of (process.env.PATH || '').split(path.delimiter).filter(Boolean)) {
    const file = path.join(dir, name);
    try {
      if (fs.statSync(file).isFile()) {
        fs.accessSync(file, fs.constants.X_OK);
        return file;
      }
    } catch { /* not here */ }
  }
  return null;
}

// The models the login check covers: the current selection, which is every model cast can launch.
function selectedModels() {
  return ROWS.filter((r) => r.mode === 'cli');
}

// A provider whose login is a set of files (providers.json `saved_login.files`): what is missing
// from them, or null when every file, and every named entry inside one, is there.
function savedLoginGap(provider) {
  for (const file of Object.values(provider.saved_login.files)) {
    const at = expandHome(file.path);
    if (!fs.existsSync(at)) return `no login file ${file.path}`;
    if (file.key) {
      const data = readJson(at);
      if (!data || !Object.prototype.hasOwnProperty.call(data, file.key)) return `${file.path} holds no '${file.key}' entry`;
    }
  }
  return null;
}

// One model's login: the presence test `cast route` uses, and for a provider with login files,
// those files too. `reason` says what is absent; it never carries a value.
function loginState(row, root) {
  let reason = isAvailable(row, root) ? null : unavailableReason(row);
  const provider = PROVIDERS[row.provider];
  if (reason === null && provider.saved_login) reason = savedLoginGap(provider);
  return { harness: row.harness, model: row.model, provider: row.provider, login: reason === null, reason };
}

function runDoctor(args) {
  const { json } = doctorArgs(args);
  const root = installationRoot(process.cwd());
  const harnesses = {};
  for (const name of HARNESSES) {
    const found = programPath(name);
    harnesses[name] = { ok: found !== null, path: found };
  }
  const models = selectedModels().map((row) => loginState(row, root));
  if (json) {
    process.stdout.write(`${JSON.stringify({ installation: root, harnesses, models, next: NEXT })}\n`);
    process.exit(0);
  }
  const pad = (values) => Math.max(...values.map((v) => v.length));
  const hw = pad(HARNESSES);
  const mw = pad(models.map((m) => m.model));
  const pw = pad(models.map((m) => m.provider));
  const lines = ['cast doctor: what this machine can launch. Local files only; nothing is started.', '',
    'harness programs on PATH'];
  for (const name of HARNESSES) {
    const h = harnesses[name];
    lines.push(`  ${name.padEnd(hw)}  ${h.ok ? `found    ${h.path}` : 'missing'}`);
  }
  lines.push('', 'login of each selected model',
    root ? `  installation: ${root}`
      : '  no installation found from this folder: no environment file is read');
  for (const m of models) {
    lines.push(`  ${m.harness.padEnd(hw)}  ${m.model.padEnd(mw)}  ${m.provider.padEnd(pw)}  ${m.login ? 'present' : 'missing'}`);
    if (!m.login) lines.push(`      ${m.reason}`);
  }
  lines.push(`  ${models.filter((m) => m.login).length} of ${models.length} selected models have a login present.`,
    '', 'accounts, saved logins and plan usage:', ...NEXT.map((c) => `  ${c}`));
  process.stdout.write(`${lines.join('\n')}\n`);
  process.exit(0);
}

module.exports = { doctorArgs, runDoctor };
