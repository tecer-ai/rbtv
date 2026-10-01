'use strict';

// API — ignite-agent install | update. run(command, argv, flags, deps) → Promise<exit code>.
// flags.workspace / flags.json / flags.help come from cli.js parseGlobal.
// deps.install(args) stubs the installer. args are the install.py argv. Absent: the real installer.
// install runs `agent add`, then installs STANDARD_UNITS with `add`. No Slack.
// Refuses when agent.md is already there; point at `ignite-agent update`.
// update re-runs both and does not replace launch.json, settings.json, board.md,
// state.sqlite, or conversations.

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { Store } = require('./store.js');

const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;
const INSTALLER_ENTRY = path.resolve(__dirname, '../../../../..', 'core/installer/capabilities/tools/rbtv-install/install.py');

const STANDARD_UNITS = [
  'meta/communication#slack-message-format',
  'meta/communication#audio-aware',
  'meta/sub-agents#sub-agents',
  'meta/functions#investignosis',
  'core/ignite#agent-controls',
  'web/browse#web',
  'office/document#office',
  'meta/communication#google-workspace',
  'core/ignite#ignite-standing-instructions',
];

const HELP = `ignite-agent install — install or update an Ignite agent

install <agent file> --harness <name> --model <cast short name> --effort <rung or 1-5>
       [--workspace <path>] [--dry-run] [--json]

  Any machine. No Slack. Runs:
    rbtv install agent add <file> --harness … --model … --effort … --target <workspace>
  then installs Ignite's standard units into <workspace>/.rbtv/agents/<name>/ with
    rbtv install add <unit>… --target <home> --harness <the agent's harness> --guidance none
  then writes what the agent needs to run and the installer does not: board.md
  (never overwrites an existing one), state.sqlite, and conversations/.
  Refuses when that agent is already installed. Refresh it with: ignite-agent update <agent>
  --workspace defaults to the current directory.
  --dry-run validates and prints the plan, including the standard units. It writes nothing.

update <agent> [--workspace <path>] [--dry-run] [--json]

  Runs rbtv install agent update <agent>, then re-installs the standard units.
  Keeps launch.json, settings.json, board.md, state.sqlite, and conversations.
`;

function fail(message) {
  const error = new Error(message);
  error.exitCode = 1;
  throw error;
}

function take(argv, i, flag) {
  const value = argv[i + 1];
  if (value == null || value.startsWith('--')) fail(`${flag} requires a value`);
  return value;
}

function emit(deps, flags, payload, human) {
  const write = deps.stdout || ((text) => process.stdout.write(text));
  write(flags.json ? `${JSON.stringify(payload)}\n` : human);
}

function parseArgs(argv, known) {
  const opts = { dryRun: false };
  const positionals = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--dry-run') {
      opts.dryRun = true;
      continue;
    }
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      if (!known.has(key)) fail(`unexpected flag ${arg}`);
      if (opts[key] != null) fail(`duplicate flag --${key}`);
      opts[key] = take(argv, i, arg);
      i += 1;
      continue;
    }
    positionals.push(arg);
  }
  return { opts, positionals };
}

function workspaceOf(flags) {
  return path.resolve(flags.workspace || process.cwd());
}

function agentHome(workspace, name) {
  return path.join(workspace, '.rbtv', 'agents', name);
}

function agentNameFromFile(file) {
  let text;
  try {
    text = fs.readFileSync(file, 'utf8');
  } catch (error) {
    fail(`cannot read agent file: ${error.message}`);
  }
  const front = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!front) fail(`agent file has no frontmatter: ${file}`);
  const name = front[1].match(/^name:\s*([a-z0-9][a-z0-9-]{0,63})\s*$/m);
  if (!name) fail(`agent file name is missing or not a slug: ${file}`);
  return name[1];
}

function installerCommand(args) {
  const python = process.platform === 'win32' ? 'python' : 'python3';
  return spawnSync(python, [INSTALLER_ENTRY, ...args], {
    encoding: 'utf8',
    maxBuffer: 10 * 1024 * 1024,
  });
}

async function runInstaller(args, deps) {
  if (deps.install) {
    const result = await deps.install(args);
    if (result == null) return { status: 0, stdout: '', stderr: '' };
    return {
      status: result.status ?? 0,
      stdout: result.stdout || '',
      stderr: result.stderr || '',
    };
  }
  const res = installerCommand(args);
  if (res.error) fail(`installer failed: ${res.error.message}`);
  return { status: res.status ?? 1, stdout: res.stdout || '', stderr: res.stderr || '' };
}

function installerError(res) {
  if (res.status === 0) return null;
  let message = (res.stderr || res.stdout || 'installer failed').trim();
  try {
    const body = JSON.parse(res.stdout);
    if (body.error?.message) message = body.error.message;
  } catch {
    // plain text
  }
  return message || 'installer failed';
}

function launchFrom(res, requested) {
  try {
    const body = JSON.parse(res.stdout);
    if (body.launch?.harness && body.launch.model && body.launch.effort) return body.launch;
  } catch {
    // stubbed installer
  }
  return requested;
}

function readLaunch(home) {
  const file = path.join(home, 'launch.json');
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    fail(`cannot read launch.json: ${error.message}`);
  }
}

function ensureRuntime(home) {
  fs.mkdirSync(path.join(home, 'conversations'), { recursive: true });
  const board = path.join(home, 'board.md');
  if (!fs.existsSync(board)) {
    fs.copyFileSync(path.join(__dirname, 'templates', 'board.md.tmpl'), board);
  }
  const db = path.join(home, 'state.sqlite');
  if (!fs.existsSync(db)) {
    const store = new Store(db);
    store.close();
  }
}

function unitArgs(home, harness, dryRun) {
  const args = ['add', ...STANDARD_UNITS, '--target', home, '--harness', harness, '--guidance', 'none', '--json'];
  if (dryRun) args.push('--dry-run');
  return args;
}

function planText(plan) {
  return [
    plan.dryRun ? 'dry-run' : plan.verb,
    `agent: ${plan.agent}`,
    `home: ${plan.home}`,
    `launch: ${plan.launch.harness} ${plan.launch.model} ${plan.launch.effort}`,
    `units: ${plan.units.join(', ')}`,
    'writes: none',
    '',
  ].join('\n');
}

async function installAgent(opts, positionals, flags, deps) {
  const file = positionals[0];
  if (!file) fail('install requires an agent file');
  if (positionals.length > 1) fail(`unexpected argument: ${positionals[1]}`);
  if (!opts.harness || !opts.model || !opts.effort) fail('install requires --harness, --model, and --effort');
  const workspace = workspaceOf(flags);
  const name = agentNameFromFile(file);
  if (!SLUG.test(name)) fail('agent name must match [a-z0-9][a-z0-9-]{0,63}');
  const home = agentHome(workspace, name);
  if (fs.existsSync(path.join(home, 'launch.json'))) {
    fail(`agent ${name} is already installed at ${home}. Refresh it with: ignite-agent update ${name}`);
  }
  const requested = { harness: opts.harness, model: opts.model, effort: opts.effort };
  const addArgs = [
    'agent', 'add', path.resolve(file),
    '--harness', opts.harness, '--model', opts.model, '--effort', opts.effort,
    '--target', workspace, '--json',
  ];
  if (opts.dryRun) addArgs.push('--dry-run');
  const added = await runInstaller(addArgs, deps);
  const addedError = installerError(added);
  if (addedError) fail(addedError);
  const launch = launchFrom(added, requested);
  const units = unitArgs(home, launch.harness, opts.dryRun);
  const installed = await runInstaller(units, deps);
  const unitsError = installerError(installed);
  if (unitsError) fail(unitsError);
  const plan = { dryRun: opts.dryRun, verb: 'install', agent: name, home, launch, units: STANDARD_UNITS };
  if (opts.dryRun) {
    emit(deps, flags, { dryRun: true, ...plan, writes: 'none' }, planText(plan));
    return 0;
  }
  const boardExisted = fs.existsSync(path.join(home, 'board.md'));
  ensureRuntime(home);
  emit(deps, flags, {
    installed: name, home, launch, units: STANDARD_UNITS, board: boardExisted ? 'kept' : 'written',
  }, `installed ${name}\nhome: ${home}\nlaunch: ${launch.harness} ${launch.model} ${launch.effort}\nunits: ${STANDARD_UNITS.join(', ')}\nboard: ${boardExisted ? 'kept' : 'written'}\n`);
  return 0;
}

async function updateAgent(opts, positionals, flags, deps) {
  const name = positionals[0];
  if (!name) fail('update requires an agent name');
  if (positionals.length > 1) fail(`unexpected argument: ${positionals[1]}`);
  if (!SLUG.test(name)) fail('agent name must match [a-z0-9][a-z0-9-]{0,63}');
  const workspace = workspaceOf(flags);
  const home = agentHome(workspace, name);
  if (!fs.existsSync(path.join(home, 'launch.json'))) {
    fail(`agent ${name} is not installed (no launch.json at ${home}). Install it with: ignite-agent install <agent file> --harness … --model … --effort …`);
  }
  const launch = readLaunch(home);
  if (!launch?.harness) fail(`no launch.json in ${home}`);
  const updateArgs = ['agent', 'update', name, '--target', workspace, '--json'];
  if (opts.dryRun) updateArgs.push('--dry-run');
  const updated = await runInstaller(updateArgs, deps);
  const updatedError = installerError(updated);
  if (updatedError) fail(updatedError);
  const units = unitArgs(home, launch.harness, opts.dryRun);
  const installed = await runInstaller(units, deps);
  const unitsError = installerError(installed);
  if (unitsError) fail(unitsError);
  const kept = ['launch.json', 'settings.json', 'board.md', 'state.sqlite', 'conversations'];
  if (opts.dryRun) {
    emit(deps, flags, {
      dryRun: true, verb: 'update', agent: name, home, launch, units: STANDARD_UNITS, kept, writes: 'none',
    }, planText({ dryRun: true, verb: 'update', agent: name, home, launch, units: STANDARD_UNITS }));
    return 0;
  }
  ensureRuntime(home);
  emit(deps, flags, { updated: name, home, units: STANDARD_UNITS, kept },
    `updated ${name}\nhome: ${home}\nunits: ${STANDARD_UNITS.join(', ')}\nkept: ${kept.join(', ')}\n`);
  return 0;
}

async function run(command, argv, flags, deps = {}) {
  if (flags.help) {
    emit(deps, { json: false }, { help: command }, HELP);
    return 0;
  }
  const known = command === 'install' ? new Set(['harness', 'model', 'effort']) : new Set();
  const { opts, positionals } = parseArgs(argv, known);
  if (command === 'install') return installAgent(opts, positionals, flags, deps);
  if (command === 'update') return updateAgent(opts, positionals, flags, deps);
  fail(`unknown command: ${command}`);
}

module.exports = { run, HELP, STANDARD_UNITS, INSTALLER_ENTRY };
