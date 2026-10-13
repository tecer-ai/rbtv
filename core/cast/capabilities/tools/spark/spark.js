#!/usr/bin/env node
'use strict';

// spark AGENT — open an rbtv agent in this terminal, for a person. A thin layer over cast: it
// shows the agent's harness, model and effort (read from its agent.json), then starts
// `cast --agent NAME --headed` (the agent's folder instead of NAME under --target). It passes no
// task, harness, model or effort: cast reads them, and opens the session with the agent's opening
// message when agent.json has one. The headed launch also opens with the agent's prepared memory
// (cast's `withMemory`); spark adds none of its own.
// spark list [AGENT] — the agents spark can open by name, or one of them in full. The list is
// cast's (`cast list --agents`, lib/agent-list.js), and so is the reading of --target FOLDER
// (lib/agent.js `targetAgents`).
// spark resume [CODE] — the sessions a person opened, or one of them opened again. The record of
// those sessions and the code of each are cast's (lib/headed.js); the session is opened by
// `cast resume ... --headed`.

const path = require('path');
const { spawnSync } = require('child_process');

const { findAgentHome, isPath, readAgent, sameNameRefusal, targetAgents } = require('../cast/lib/agent');
const { agentInFull, agentLines, agentList, listLines } = require('../cast/lib/agent-list');
const { HANDLE_TTL_MS } = require('../cast/lib/handles');
const { MAX_SHOWN, openedSessions, sessionLines, sessionOf, sessionRow } = require('../cast/lib/headed');
const { findOnPath, spawnable } = require('../cast/lib/win-exec');

const LIST_FORM = 'spark list [AGENT] [--target FOLDER] [--full] [--json] [-h]';
const USAGE = 'usage: spark AGENT [--target FOLDER] [--dry-run] [--json] [-h]';
const LIST_USAGE = `usage: ${LIST_FORM}`;
const RESUME_FORMS = ['spark resume [-n N] [--json] [-h]', 'spark resume CODE [-h]'];
const RESUME_USAGE = `usage: ${RESUME_FORMS.join('\n       ')}`;
const SHOWN = 5;
const KEPT_DAYS = HANDLE_TTL_MS / 86400000;

const HELP = [
  'spark — help',
  '',
  'Opens an rbtv agent in this terminal, for a person, with that agent\'s',
  'own harness, model and effort. An agent that needs another agent uses',
  'cast --agent.',
  '',
  USAGE,
  `       ${LIST_FORM}`,
  ...RESUME_FORMS.map((form) => `       ${form}`),
  '',
  'AGENT is a name, looked up in <installation>/.rbtv/agents/, or a path',
  'to an agent folder. The installation is the nearest folder above the',
  'current directory that holds .rbtv/. An argument with a slash or a',
  'backslash is a path. Any other argument is a name, except list and',
  'resume. A name not found there is looked up among the listed agent',
  'folders: the agent folders elsewhere in the installation whose',
  'agent.json says "listed": true. A name two of them share is refused',
  'with both folders; open one by its path.',
  '',
  'spark list shows the agents spark can open by name: the agents in the',
  'nearest .rbtv/agents/ folder above the current directory, and the',
  'listed agent folders of that installation. A folder whose name starts',
  'with a dot, and node_modules, are not searched for them. For each:',
  'name, harness, model, effort, Ignite (yes when the agent\'s ignite pack',
  'is on, which ignite connect does; such an agent also wakes from',
  'Slack), Folder (from the installation; shown when a listed agent',
  'folder is in the list), and description. The description is',
  'shortened to fit the line; with --full, or on a narrow terminal, each',
  'agent is a labeled block with its whole description. spark list AGENT',
  'shows that one agent in full:',
  'its folder, its whole description, and the packs, skills, rules,',
  'commands, MCP servers and hooks installed in it, under the names',
  'rbtv show takes. Both open nothing. No agent found is success. Open',
  'an agent whose name is list or resume by its path.',
  '',
  'spark resume shows the sessions opened on this machine with spark or',
  `cast --headed, newest first: the ${SHOWN} newest, or the N newest with -n N.`,
  'For each: its code, the agent (- when the session ran no rbtv',
  'agent), harness, model, when it was opened and the folder it runs',
  'in. It opens nothing. No session on record is success. A session',
  `stays on record for ${KEPT_DAYS} days. spark resume CODE opens that session`,
  'again in this terminal, with its history, on the agent\'s current',
  'harness settings. A code is two letters, drawn at random when the',
  'session is opened, and names that session for as long as it is on',
  'record. A session opened on codex or opencode is found by its folder',
  'and the time it was opened: two of them opened in one folder in the',
  'same moment cannot be told apart.',
  '',
  '--target FOLDER makes AGENT a name among the agents of FOLDER, and',
  'spark list show those agents. FOLDER is an installation (it holds',
  '.rbtv/): the agents in its .rbtv/agents/. Or an agent folder: that',
  'one agent. Or a folder that holds agent folders, such as the agents/',
  'folder of a plan: those agents. A FOLDER that is none of the three is',
  'refused. With --target, AGENT is never a path.',
  '',
  'Harness, model and effort are read from the agent\'s agent.json. To',
  'change them: rbtv agent configure AGENT',
  'spark sets RBTV_AGENT_HOME to the agent folder. It hands prompt.md to',
  'the model. A frontmatter block that still opens the file is ignored',
  'and reported by rbtv doctor; remove it. The session opens with the',
  'opening message of agent.json when the record has one, and with no',
  'first message otherwise: write that field for an agent that must do',
  'something, such as read its board, before you speak.',
  '',
  '--target FOLDER',
  '            Take the agents from FOLDER, not from above the current',
  '            directory.',
  '--dry-run   Print the cast command it would run. Launch nothing.',
  '            spark list refuses it.',
  '--full      With list, show every description whole.',
  `-n N        With resume and no CODE, show the N newest sessions, 1 to ${MAX_SHOWN}.`,
  `            Default ${SHOWN}.`,
  '--json      With --dry-run, one JSON value: agent, home, cast.',
  '            With list, one JSON value: folder and agents, each',
  '            agent with name, description, harness, model, effort,',
  '            ignite and home. With list AGENT, that agent, plus',
  '            installed: the names by kind. With resume and no CODE,',
  '            one JSON value: on_record, the number of sessions on',
  '            record, and sessions, each with code, agent (null',
  '            when it ran none), harness, model, opened and folder.',
  '            A real launch ignores --json. A refusal is text on',
  '            standard error, with or without --json.',
  '-h, --help  Show this help and exit.',
  '',
  'spark needs cast on PATH to open an agent, and rbtv on PATH to show',
  'what is installed in one. It does not ask questions.',
  '',
  'Example:',
  '  spark list',
  '  spark list scout',
  '  spark list --target plans/launch/agents',
  '  spark scout',
  '  spark plans/launch/agents/drafter',
  '  spark drafter --target plans/launch/agents',
  '  spark scout --dry-run',
  '  spark resume',
  '  spark resume -n 20',
  '  spark resume kj',
  '',
  'Exit codes: 0 success, including a list with no agent; 1 refused or',
  'invalid arguments.',
].join('\n');

function refuse(what, why, fix) {
  process.stderr.write(`refused: ${what}\n  why: ${why}\n  fix: ${fix}\n`);
  return 1;
}

function quote(arg) {
  return /^[\w@%+=:,./\\-]+$/.test(arg) ? arg : `"${arg.replace(/"/g, '\\"')}"`;
}

// The agents `--target FOLDER` names, or null after the refusal is printed.
function agentsOf(target) {
  const found = targetAgents(target, process.cwd());
  if (!found.problem) return found;
  refuse(`--target \`${target}\` names no rbtv agents`, `${found.problem}.`,
    'pass an installation, a folder that holds agent folders, or one agent folder.');
  return null;
}

// The agent `value` names, read for launch, or null after the refusal is printed. Under
// `target`, a name among that folder's agents.
function findAgent(value, target) {
  let homes = null;
  if (target) {
    if (isPath(value)) {
      refuse(`\`--target\` goes with a name, and \`${value}\` is a path`,
        'a path already names the agent folder.', 'drop --target, or pass the name.');
      return null;
    }
    const found = agentsOf(target);
    if (!found) return null;
    homes = found.homes;
  }
  const home = findAgentHome(value, process.cwd(), homes);
  if (!home) {
    if (target) {
      refuse(`no rbtv agent \`${value}\` was found`, `looked for an agent folder named ${value} in --target ${target}.`,
        `\`spark list --target ${target}\`.`);
      return null;
    }
    const same = isPath(value) ? null : sameNameRefusal(value, process.cwd());
    if (same) {
      refuse(`no rbtv agent \`${value}\` was found`, same, 'pass the folder of one of them.');
      return null;
    }
    const looked = isPath(value)
      ? `looked for ${path.join(path.resolve(value), 'agent.json')}.`
      : `looked for .rbtv/agents/${value}/agent.json from the current folder upward, and for a listed agent folder of that name.`;
    refuse(`no rbtv agent \`${value}\` was found`, looked, '`spark list`, or pass the folder.');
    return null;
  }
  const read = readAgent(home);
  if (read.problem === 'launch') {
    refuse(`the launch values of \`${value}\` are unreadable`, read.why,
      `repair ${path.join(home, 'agent.json')} (harness, model, effort).`);
    return null;
  }
  if (read.problem === 'prompt') {
    refuse(`the agent \`${value}\` has no prompt.md`, read.why, 'restore that file, then run spark again.');
    return null;
  }
  return read.agent;
}

// spark list [AGENT]: the list, or one agent in full. Nothing is opened.
function list(named, dry, json, full, target) {
  if (dry) {
    return refuse('`--dry-run` is not a spark list option',
      'spark list opens nothing, so it has nothing to preview.', LIST_USAGE);
  }
  if (named.length > 1) {
    return refuse('spark list takes at most one agent', `got ${named.length}.`, LIST_USAGE);
  }
  const print = (value, lines) => process.stdout.write(json ? `${JSON.stringify(value)}\n` : `${lines.join('\n')}\n`);
  if (named.length) {
    const agent = findAgent(named[0], target);
    if (!agent) return 1;
    const row = agentInFull(agent);
    print(row, agentLines(row));
  } else {
    if (target && !agentsOf(target)) return 1;
    const found = agentList(process.cwd(), target);
    print(found, listLines(found, { full }));
  }
  return 0;
}

// The `cast` on PATH, or null after the refusal is printed.
function findCast() {
  const cast = findOnPath('cast');
  if (!cast) refuse('cast is not on PATH', 'spark opens the agent through cast. Nothing was launched.', 'rbtv doctor');
  return cast;
}

// `cast` started in this terminal; the exit code is cast's.
function runCast(cast, castArgs) {
  const win = spawnable(cast, castArgs);
  const res = spawnSync(win.cmd, win.args, { stdio: 'inherit', ...win.opts });
  if (res.error) return refuse('cast did not start', res.error.message, 'rbtv doctor');
  return res.status ?? 1;
}

function header(pairs) {
  for (const [label, text] of pairs) process.stdout.write(`${label.padEnd(8)} ${text}\n`);
}

// spark resume [CODE]: the sessions on record, or one of them opened again.
function resume(args) {
  let json = false;
  let shown = null;
  const positional = [];
  for (let i = 0; i < args.length; i += 1) {
    const a = args[i];
    if (a === '-h' || a === '--help') {
      process.stdout.write(`${HELP}\n`);
      return 0;
    } else if (a === '--json') json = true;
    else if (a === '-n') {
      const n = args[i += 1];
      if (!/^\d+$/.test(n ?? '') || Number(n) < 1 || Number(n) > MAX_SHOWN) {
        return refuse(`\`-n\` takes a number from 1 to ${MAX_SHOWN}`, `got ${n === undefined ? 'nothing' : `\`${n}\``}.`, RESUME_USAGE);
      }
      shown = Number(n);
    } else if (a.startsWith('-')) {
      return refuse(`\`${a}\` is not a spark resume option`,
        'spark resume takes one optional code and the options -n, --json and -h.', RESUME_USAGE);
    } else positional.push(a);
  }
  const codes = positional.slice(1);
  if (codes.length > 1) return refuse('spark resume takes at most one code', `got ${codes.length}.`, RESUME_USAGE);
  const opened = openedSessions();
  if (!codes.length) {
    const list = { on_record: opened.length, sessions: opened.slice(0, shown ?? SHOWN).map(sessionRow) };
    process.stdout.write(json ? `${JSON.stringify(list)}\n` : `${sessionLines(list).join('\n')}\n`);
    return 0;
  }
  const [code] = codes;
  if (shown !== null) {
    return refuse('`-n` goes with the list, not with a code', `\`${code}\` names one session.`, RESUME_USAGE);
  }
  const row = opened.find((h) => h.code === code);
  if (!row) {
    return refuse(`no session \`${code}\` is on record`,
      `a code is the two letters spark resume shows, and a session stays on record for ${KEPT_DAYS} days.`, '`spark resume`');
  }
  const session = sessionOf(row);
  if (session.problem) {
    return refuse(`the session \`${code}\` cannot be opened again`, `${session.problem}. Nothing was launched.`,
      row.agent ? `\`spark ${quote(row.agent)}\` opens a new session.` : '`spark resume` shows the others.');
  }
  const cast = findCast();
  if (!cast) return 1;
  const shownRow = sessionRow(row);
  header([['session', code], ['agent', shownRow.agent ?? '-'], ['folder', row.folder], ['harness', row.harness],
    ['model', row.model]]);
  return runCast(cast, ['resume', row.harness, session.id, row.folder, '--headed']);
}

function spark(args) {
  let dry = false;
  let json = false;
  let full = false;
  let target = null;
  const positional = [];
  // The first argument that is neither an option nor --target's folder decides the form: `list`,
  // `resume`, or an agent.
  const form = args.find((a, i) => !a.startsWith('-') && args[i - 1] !== '--target');
  if (form === 'resume') return resume(args);
  const listing = form === 'list';
  for (let i = 0; i < args.length; i += 1) {
    const a = args[i];
    if (a === '-h' || a === '--help') {
      process.stdout.write(`${HELP}\n`);
      return 0;
    } else if (a === '--target') {
      const folder = args[i + 1];
      if (folder === undefined || folder.startsWith('-') || target !== null) {
        return refuse('`--target` takes one folder',
          'an installation, a folder that holds agent folders, or one agent folder.', listing ? LIST_USAGE : USAGE);
      }
      target = folder;
      i += 1;
    } else if (a === '--dry-run') dry = true;
    else if (a === '--json') json = true;
    else if (a === '--full' && listing) full = true;
    else if (a.startsWith('-')) {
      return listing
        ? refuse(`\`${a}\` is not a spark list option`,
          'spark list takes one optional agent and the options --target, --full, --json and -h.', LIST_USAGE)
        : refuse(`\`${a}\` is not a spark option`,
          'spark takes one agent and the options --target, --dry-run, --json and -h.', USAGE);
    } else positional.push(a);
  }
  if (listing) return list(positional.slice(1), dry, json, full, target);
  if (positional.length !== 1) {
    return refuse('spark needs exactly one agent', `got ${positional.length}.`, USAGE);
  }
  const value = positional[0];
  const agent = findAgent(value, target);
  if (!agent) return 1;
  const { home, harness, model, effort } = agent;
  const cast = findCast();
  if (!cast) return 1;

  // cast has no --target on a launch: under --target it gets the agent's folder.
  const castArgs = ['--agent', target ? home : value, '--headed'];
  const name = path.basename(home);
  if (dry) {
    if (json) process.stdout.write(`${JSON.stringify({ agent: name, home, cast: ['cast', ...castArgs] })}\n`);
    else process.stdout.write(`cast ${castArgs.map(quote).join(' ')}\n`);
    return 0;
  }

  header([['agent', name], ['folder', home], ['harness', harness], ['model', model], ['effort', effort]]);
  return runCast(cast, castArgs);
}

process.exitCode = spark(process.argv.slice(2));
