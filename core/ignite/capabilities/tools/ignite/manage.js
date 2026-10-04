'use strict';

// API — ignite manage SUBCOMMAND ARGS... delegates exactly once to rbtv or cast.

const { spawnSync } = require('node:child_process');
const path = require('node:path');
const { INSTALLER_ENTRY, runInstaller } = require('./connect.js');

const CHANGE = new Set(['add', 'remove', 'configure', 'update']);
const READ = new Set(['list', 'search', 'show']);
const HELP = `ignite — manage help

One place for the calling agent to manage itself. This command has no logic of its own.

Change — refused outside a turn. Use rbtv agent instead.
  add        runs rbtv agent add <this agent>
  remove     runs rbtv agent remove <this agent>
  configure  runs rbtv agent configure <this agent>
  update     runs rbtv agent update <this agent>

Read — a calling agent is not required.
  models     runs cast list
  list       runs rbtv list
  search     runs rbtv search
  show       runs rbtv show

Next: ignite manage COMMAND -h
`;

function write(deps, stream, text) { (deps[stream] || process[stream].write.bind(process[stream]))(text); }
function callCast(args, deps) {
  if (deps.cast) return deps.cast(args);
  const result = spawnSync('cast', args, { encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 });
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
async function delegate(command, args, flags, deps, home) {
  const result = command === 'models'
    ? await callCast(['list', ...args], deps)
    : await callInstaller(command === 'models' ? [] : (CHANGE.has(command)
      ? ['agent', command, home, ...args]
      : [command, ...args]), flags.installation, deps);
  if (result.stdout) write(deps, 'stdout', result.stdout);
  if (result.stderr) write(deps, 'stderr', result.stderr);
  return result.status ?? 0;
}
async function run(argv, flags, deps = {}) {
  const [command, ...args] = argv;
  if (!command) { write(deps, 'stdout', HELP); return 0; }
  if (![...CHANGE, ...READ, 'models'].includes(command)) throw Object.assign(new Error(`unknown manage command: ${command}`), { exitCode: 1 });
  const wantsHelp = flags.help || (args.length === 1 && (args[0] === '-h' || args[0] === '--help'));
  if (flags.help) args.push('-h');
  const home = callingAgent(flags, deps);
  if (CHANGE.has(command) && !home && !wantsHelp) {
    write(deps, 'stderr', absent(command, args)); return 1;
  }
  if (wantsHelp) {
    const prefix = command === 'models'
      ? 'ignite manage models — runs cast list.\nArguments and output pass through unchanged.\n\n'
      : `ignite manage ${command} — runs rbtv ${CHANGE.has(command) ? `agent ${command} <this agent>` : command}.\n\n`;
    write(deps, 'stdout', prefix);
  }
  return delegate(command, args, flags, deps, home);
}

module.exports = { run, HELP };
