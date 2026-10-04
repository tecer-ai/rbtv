#!/usr/bin/env node
'use strict';

// spark AGENT — open an rbtv agent in this terminal, for a person. A thin layer over cast: it
// shows the agent's harness, model and effort (read from its agent.json), then starts
// `cast -rbtv AGENT --headed` with a greeting. It passes no harness, model or effort: cast reads them.
// spark list [FOLDER] — the agents spark can open. It runs `rbtv agent list` and prints what that
// prints, so spark keeps no second listing.

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const { findAgentHome, isPath, readAgent } = require('../cast/lib/agent');
const { spawnable } = require('../cast/lib/win-exec');

// cast needs a first message to open the session; this one starts a conversation and waits.
const OPENING = 'You have just been started by your owner in an interactive terminal. '
  + 'Greet them in one line and wait for what they need.';

const LIST_FORM = 'spark list [FOLDER] [--json] [-h]';
const USAGE = 'usage: spark AGENT [--dry-run] [--json] [-h]';
const LIST_USAGE = `usage: ${LIST_FORM}`;

const HELP = [
  'spark — help',
  '',
  'Opens an rbtv agent in this terminal, for a person, with that agent\'s',
  'own harness, model and effort. An agent that needs another agent uses',
  'cast -rbtv.',
  '',
  USAGE,
  `       ${LIST_FORM}`,
  '',
  'AGENT is a name, looked up in <installation>/.rbtv/agents/, or a path',
  'to an agent folder. The installation is the nearest folder above the',
  'current directory that holds .rbtv/. An argument with a slash is a',
  'path. Any other argument is a name, except list.',
  '',
  'spark list shows the agents spark can open, with the harness, model',
  'and effort of each. It runs rbtv agent list and prints what that',
  'prints. With no FOLDER it lists the installation\'s .rbtv/agents/. With',
  'FOLDER it lists every agent folder found in that folder. It opens',
  'nothing. Open an agent whose name is list by its path.',
  '',
  'Harness, model and effort are read from the agent\'s agent.json. To',
  'change them: rbtv agent configure AGENT',
  'spark sets RBTV_AGENT_HOME to the agent folder. It hands agent.md to',
  'the model without its frontmatter.',
  '',
  '--dry-run   Print the cast command it would run. Launch nothing.',
  '            spark list refuses it.',
  '--json      With --dry-run, one JSON value: agent, home, cast.',
  '            With list, the one JSON value rbtv agent list --json',
  '            prints, for success or failure. A real launch ignores',
  '            --json. A refusal by spark itself is text on standard',
  '            error, with or without --json.',
  '-h, --help  Show this help and exit.',
  '',
  'spark needs cast on PATH to open an agent and rbtv on PATH to list.',
  'It does not ask questions.',
  '',
  'Example:',
  '  spark list',
  '  spark scout',
  '  spark plans/launch/agents/drafter',
  '  spark scout --dry-run',
  '  spark list plans/launch',
  '',
  'Exit codes: 0 success, including a list with no agent; 1 refused or',
  'invalid arguments.',
].join('\n');

function refuse(what, why, fix) {
  process.stderr.write(`refused: ${what}\n  why: ${why}\n  fix: ${fix}\n`);
  return 1;
}

// The program of that name on PATH, or null. Windows also tries each PATHEXT extension.
function findOnPath(name) {
  const exts = process.platform === 'win32'
    ? ['', ...(process.env.PATHEXT || '.EXE;.CMD;.BAT;.COM').split(';')]
    : [''];
  const mode = process.platform === 'win32' ? fs.constants.F_OK : fs.constants.X_OK;
  for (const dir of (process.env.PATH || '').split(path.delimiter)) {
    if (!dir) continue;
    for (const ext of exts) {
      const file = path.join(dir, name + ext);
      try {
        fs.accessSync(file, mode);
        if (fs.statSync(file).isFile()) return file;
      } catch { /* not here */ }
    }
  }
  return null;
}

function quote(arg) {
  return /^[\w@%+=:,./\\-]+$/.test(arg) ? arg : `"${arg.replace(/"/g, '\\"')}"`;
}

// spark list: hand the listing to `rbtv agent list`, with its output and its exit status.
function list(folders, dry, json) {
  if (dry) {
    return refuse('`--dry-run` is not a spark list option',
      'spark list opens nothing, so it has nothing to preview.', LIST_USAGE);
  }
  if (folders.length > 1) {
    return refuse('spark list takes at most one folder', `got ${folders.length}.`, LIST_USAGE);
  }
  const rbtv = findOnPath('rbtv');
  if (!rbtv) {
    return refuse('rbtv is not on PATH', 'spark list prints the list through `rbtv agent list`. Nothing was listed.',
      'put rbtv on PATH (its shortcut is in ~/.rbtv/bin), then run the same command again.');
  }
  const win = spawnable(rbtv, ['agent', 'list', ...folders, ...(json ? ['--json'] : [])]);
  const res = spawnSync(win.cmd, win.args, { stdio: 'inherit', ...win.opts });
  if (res.error) {
    return refuse('rbtv did not start', `${res.error.message}. Nothing was listed.`, 'check that it runs: rbtv -h');
  }
  return res.status ?? 1;
}

function spark(args) {
  let dry = false;
  let json = false;
  const positional = [];
  // The first argument that is not an option decides the form: `list`, or an agent.
  const listing = args.find((a) => !a.startsWith('-')) === 'list';
  for (const a of args) {
    if (a === '-h' || a === '--help') {
      process.stdout.write(`${HELP}\n`);
      return 0;
    } else if (a === '--dry-run') dry = true;
    else if (a === '--json') json = true;
    else if (a.startsWith('-')) {
      return listing
        ? refuse(`\`${a}\` is not a spark list option`,
          'spark list takes one optional folder and the options --json and -h.', LIST_USAGE)
        : refuse(`\`${a}\` is not a spark option`,
          'spark takes one agent and the options --dry-run, --json and -h.', USAGE);
    } else positional.push(a);
  }
  if (listing) return list(positional.slice(1), dry, json);
  if (positional.length !== 1) {
    return refuse('spark needs exactly one agent', `got ${positional.length}.`, USAGE);
  }
  const value = positional[0];
  const home = findAgentHome(value, process.cwd());
  if (!home) {
    const looked = isPath(value)
      ? `looked for ${path.join(path.resolve(value), 'agent.json')}.`
      : `looked for .rbtv/agents/${value}/agent.json from the current folder upward.`;
    return refuse(`no rbtv agent \`${value}\` was found`, looked, '`spark list`, or pass the folder.');
  }
  const read = readAgent(home);
  if (read.problem === 'launch') {
    return refuse(`the launch values of \`${value}\` are unreadable`, read.why,
      `repair ${path.join(home, 'agent.json')} (harness, model, effort).`);
  }
  if (read.problem === 'prompt') {
    return refuse(`the agent \`${value}\` has no agent.md`, read.why, 'restore that file, then run spark again.');
  }
  const cast = findOnPath('cast');
  if (!cast) {
    return refuse('cast is not on PATH', 'spark opens the agent through cast. Nothing was launched.', 'rbtv doctor');
  }

  const castArgs = ['-rbtv', value, '--headed', '-p', OPENING];
  const name = path.basename(home);
  if (dry) {
    if (json) process.stdout.write(`${JSON.stringify({ agent: name, home, cast: ['cast', ...castArgs] })}\n`);
    else process.stdout.write(`cast ${castArgs.map(quote).join(' ')}\n`);
    return 0;
  }

  const { harness, model, effort } = read.agent;
  for (const [label, text] of [['agent', name], ['folder', home], ['harness', harness], ['model', model],
    ['effort', effort || 'none']]) {
    process.stdout.write(`${label.padEnd(8)} ${text}\n`);
  }
  const win = spawnable(cast, castArgs);
  const res = spawnSync(win.cmd, win.args, { stdio: 'inherit', ...win.opts });
  if (res.error) return refuse('cast did not start', res.error.message, 'rbtv doctor');
  return res.status ?? 1;
}

process.exitCode = spark(process.argv.slice(2));
