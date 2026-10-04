'use strict';

// API — ignite manage SUBCOMMAND ARGS... delegates exactly once to rbtv or cast.

const { spawnSync } = require('node:child_process');
const path = require('node:path');
const { INSTALLER_ENTRY, runInstaller } = require('./connect.js');
const CAST_LIB = '../../../../cast/capabilities/tools/cast/lib';
const { spawnable } = require(`${CAST_LIB}/win-exec`);

const CHANGE = new Set(['add', 'remove', 'configure', 'update']);
const READ = new Set(['list', 'search', 'show']);
const SUBCOMMANDS = [...CHANGE, 'models', ...READ];
const HELP = `ignite — manage help

One place for the calling agent to manage itself. This command has no
logic of its own. Each sub-verb runs the command named here and passes
arguments and output through unchanged.

Change — refused outside a turn. Use rbtv agent instead.
  add        runs  rbtv agent add <this agent>
  remove     runs  rbtv agent remove <this agent>
  configure  runs  rbtv agent configure <this agent>
  update     runs  rbtv agent update <this agent>

Read — a calling agent is not required.
  models     runs  cast list
  list       runs  rbtv list
  search     runs  rbtv search
  show       runs  rbtv show

<this agent> is RBTV_AGENT_HOME, or --agent NAME --installation PATH.
Do not pass the agent to a change verb. Outside a turn, use rbtv agent.
Help needs neither value.

Next: ignite manage COMMAND -h
Exit codes: ignite's own refusal or invalid arguments exit 1.
A passed-through command keeps that command's exit code.
`;

function write(deps, stream, text) { (deps[stream] || process[stream].write.bind(process[stream]))(text); }
function callCast(args, deps) {
  if (deps.cast) return deps.cast(args);
  const win = spawnable('cast', args);
  const result = spawnSync(win.cmd, win.args, { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024, ...win.opts });
  if (result.error) return { status: 1, stdout: '', stderr: `${result.error.message}\n` };
  return { status: result.status ?? 1, stdout: result.stdout || '', stderr: result.stderr || '' };
}
async function callInstaller(args, installation, deps) { return runInstaller(args, installation || process.cwd(), deps); }
function callingAgent(flags, deps) {
  const env = deps.env || process.env;
  if (env.RBTV_AGENT_HOME) return env.RBTV_AGENT_HOME;
  if (flags.agent && flags.installation) return path.join(flags.installation, '.rbtv', 'agents', flags.agent);
  return null;
}
function absent(subcommand, args) {
  return `ignite manage ${subcommand} needs the calling agent.\nRBTV_AGENT_HOME is not set, and --agent with --installation was not given.\nNothing changed.\nrbtv agent ${subcommand} AGENT${args.length ? ` ${args.join(' ')}` : ''}\n`;
}
// The installer names an agent by its folder name when the agent lives under an installation's
// .rbtv/agents/ (its "Next:" line then names no path). Any other agent is passed by folder path.
function installerAgent(home) {
  const agents = path.dirname(home);
  if (path.basename(agents) !== 'agents' || path.basename(path.dirname(agents)) !== '.rbtv') {
    return { args: [home], cwd: null };
  }
  return { args: [path.basename(home)], cwd: path.dirname(path.dirname(agents)) };
}
function prefixOf(command) {
  if (command === 'models') {
    return ['ignite manage models — runs cast list.', 'Arguments and output pass through unchanged.', 'No calling agent is required.'];
  }
  if (CHANGE.has(command)) {
    return [
      `ignite manage ${command} — runs rbtv agent ${command} <this agent>.`,
      '<this agent> is RBTV_AGENT_HOME, or --agent NAME --installation PATH.',
      `Outside a turn this is refused. Use: rbtv agent ${command} AGENT`,
    ];
  }
  return [
    `ignite manage ${command} — runs rbtv ${command}.`,
    'Arguments and output pass through. A calling agent is not required.',
    'RBTV_AGENT_HOME, when set, is the target after --target.',
  ];
}
async function delegate(command, args, flags, deps, home) {
  let result;
  if (command === 'models') {
    result = await callCast(['list', ...args], deps);
  } else if (CHANGE.has(command)) {
    const agent = home ? installerAgent(home) : { args: [], cwd: null };
    result = await callInstaller(['agent', command, ...agent.args, ...args], agent.cwd || flags.installation, deps);
  } else {
    result = await callInstaller([command, ...args], flags.installation, deps);
  }
  if (result.stdout) write(deps, 'stdout', result.stdout);
  if (result.stderr) write(deps, 'stderr', result.stderr);
  return result.status ?? 0;
}
async function run(argv, flags, deps = {}) {
  const [command, ...args] = argv;
  if (!command) { write(deps, 'stdout', HELP); return 0; }
  if (!SUBCOMMANDS.includes(command)) {
    throw Object.assign(new Error(`unknown command: ${command}\nchoose from ${SUBCOMMANDS.join(', ')}\nNothing changed.\nignite manage -h`), { exitCode: 1 });
  }
  const wantsHelp = flags.help || (args.length === 1 && (args[0] === '-h' || args[0] === '--help'));
  if (flags.help) args.push('-h');
  const home = callingAgent(flags, deps);
  if (CHANGE.has(command) && !home && !wantsHelp) {
    write(deps, 'stderr', absent(command, args)); return 1;
  }
  if (wantsHelp) write(deps, 'stdout', `${prefixOf(command).join('\n')}\n\n`);
  return delegate(command, args, flags, deps, home);
}

module.exports = { run, HELP };
