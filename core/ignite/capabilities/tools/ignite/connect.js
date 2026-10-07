'use strict';

// API — ignite connect | disconnect. run(command, argv, flags, deps) → Promise<exit code>.
// flags.installation / flags.json / flags.help come from cli.js parseGlobal.
// deps.slack stubs Slack. deps.afterChannel() runs after the route write and before the bot joins.
// The agent must already be installed (prompt.md and agent.json). Config must already exist; this does not create it.
// Slack tokens come from slackToken(config, …) and are never printed.
// A re-run reuses the channel already routed; config.json is the only record of a connection.
// disconnect removes routes and dmAgent, optionally archives the channel, and cancels timers.
// It does not delete the agent folder.

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const { loadConfig, updateConfig, agentHome, configPath, findWorkspace, slackToken } = require('./config.js');
const { agentsFolder, isAgentFolder, isPath, readAgent } = require('../../../../cast/capabilities/tools/cast/lib/agent');
const { Slack } = require('./slack.js');
const { Store, conversationKey } = require('./store.js');
const { cadenceSpec, nextOccurrence, FIXED_TZ } = require('./schedule.js');
const { boardPath, migrateBoard, preflightBoard, refreshBoard, refreshBoardAfterCommit, writeBoard } = require('./board.js');

const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;
const CHANNEL = /^[a-z0-9][a-z0-9_-]{0,79}$/;
const BOARD_ROOT = 'board';
const RUNBOOK = 'core/ignite/capabilities/runbook.md';
const INSTALLER_ENTRY = path.resolve(__dirname, '../../../../..', 'core/rbtv/capabilities/tools/rbtv/install.py');

const HELP = {
  connect: `ignite — connect help

usage: ignite connect [-h] (--channel-name NAME | --dm)
                      [--schedule-json FILE] [--installation PATH]
                      [--dry-run] [--json]
                      AGENT

Turn the ignite pack on, create Ignite's working files, and connect
Slack. Three steps, each reported. Run on the machine that will run
the agent.

AGENT is a name under <installation>/.rbtv/agents/, or a path to an
agent folder there. A path outside .rbtv/agents/ is refused. ignite
does not copy an agent. A name that is not there is refused, even
when a component ships an agent of that name. Add it first:
  rbtv agent add AGENT

The installation is found by walking up from the current folder to
.rbtv/config/ignite/config.json, or from --installation PATH.
The agent must already be installed (agent.json in
<installation>/.rbtv/agents/<agent>/).
Needs <installation>/.rbtv/config/ignite/config.json. This command
does not write that file. See ${RUNBOOK}.

Steps, in order:
  1. rbtv agent add AGENT --pack ignite
     Turns the pack on. Files already recorded stay. A file listed
     by two packs counts once.
  2. Create working files if missing. An existing board is not
     overwritten.
       <agent>/_artifacts/board.md
       <agent>/state.sqlite
       <agent>/conversations/
  3. Connect Slack. --channel-name creates the channel, the bot
     joins, the owner is invited, and the route is written. A re-run
     reuses a channel already routed and finishes a partial
     connection. It is not refused. --dm sets the direct-message
     agent and creates no channel. Pass one of the two, not both.

Slack tokens are read from the environment variables the config
names. They are never printed.

--schedule-json binds one timer after the working files exist.
Object, exactly one of cron, every, at:
  { "cron": "<5-field>", "tz": "<IANA zone>", "note": "<check>", "report": "always|when-useful" }
  { "every": "<duration>", "tz": "fixed", "note": "<check>" }
  { "at": "<ISO datetime with offset>", "note": "<check>" }
report defaults to when-useful. A missing cadence or timezone is refused.
Binding a timer requires a valid <home>/_artifacts/board.md before opening SQLite.
A committed timer whose board refresh fails still exits 0, with its id and
"committed; board refresh pending" (--json adds warning). Do not repeat the mutation.
The next board write or turn refreshes Timers from SQLite. This also applies
to timers cancelled by disconnect.

--dry-run validates and prints the plan. It writes nothing.
--json selects JSON on stdout for a success. A refusal is a message
on stderr, exit 1, with or without --json.

options:
  -h, --help            show this help message and exit
  --channel-name NAME   Slack channel to create and route to this agent
  --dm                  route the owner's direct messages to this agent
  --schedule-json FILE  bind one timer from this file
  --installation PATH   installation folder; overrides the walk up
  --dry-run             print the plan; write nothing
  --json                JSON on stdout for a success
  AGENT                 name, or a path under .rbtv/agents/

Example: ignite connect research --channel-name research
Next: ignite disconnect research
Exit codes: 0 success or dry-run; 1 refused, failed, or invalid arguments.
`,
  disconnect: `ignite — disconnect help

usage: ignite disconnect [-h] [--archive-channel]
                         [--installation PATH] [--dry-run] [--json]
                         AGENT

Removes the agent's route(s) and direct-message assignment, turns the
ignite pack off, cancels its timers, and archives its channel when
asked. Does not delete the agent folder or its working files.

AGENT is a name under <installation>/.rbtv/agents/, or a path to an
agent folder there. A path outside .rbtv/agents/ is refused, the same
rule as connect. ignite does not copy an agent.

Pack off runs:
  rbtv agent remove AGENT --pack ignite
This command does not remove the agent. To remove files by name:
  rbtv agent remove AGENT NAME

The installation is found by walking up from the current folder to
.rbtv/config/ignite/config.json, or from --installation PATH.

--archive-channel archives the Slack channel when asked.
--dry-run validates and prints the plan. It writes nothing.
--json selects JSON on stdout for a success. A refusal is a message
on stderr, exit 1, with or without --json.

A committed timer cancel whose board refresh fails still exits 0,
with its id and "committed; board refresh pending" (--json adds
warning). Do not repeat the mutation. The next board write or turn
refreshes Timers from SQLite.

options:
  -h, --help            show this help message and exit
  --archive-channel     archive the Slack channel when asked
  --installation PATH   installation folder; overrides the walk up
  --dry-run             print the plan; write nothing
  --json                JSON on stdout for a success
  AGENT                 name, or a path under .rbtv/agents/

Example: ignite disconnect research
Next: ignite connect research --channel-name research
Exit codes: 0 success or dry-run; 1 refused, failed, or invalid arguments.
`,
};

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
  const opts = { dryRun: false, dm: false, archiveChannel: false };
  const positionals = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--dry-run') {
      opts.dryRun = true;
      continue;
    }
    if (arg === '--dm' || arg === '--archive-channel') {
      const key = arg.slice(2);
      if (!known.has(key)) fail(`unexpected flag ${arg}`);
      if (arg === '--dm') opts.dm = true;
      else opts.archiveChannel = true;
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
  if (flags.installation) return path.resolve(flags.installation);
  const workspace = findWorkspace(process.cwd());
  if (!workspace) fail(`no installation found: ${configPath(process.cwd())} is not in this folder or above.\nRun from inside an installation, or pass --installation PATH.\nNothing changed.`);
  return workspace;
}

function readJson(file, label) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    fail(`cannot read ${label}: ${error.message}`);
  }
}

function routesFor(config, agent) {
  return Object.entries(config.routes).filter(([, name]) => name === agent);
}

function requireConfig(workspace) {
  const file = configPath(workspace);
  if (!fs.existsSync(file)) {
    fail(`Ignite config not found: ${file}\nCreate that file before connect. See ${RUNBOOK}\nNothing changed.`);
  }
  try {
    return loadConfig(workspace);
  } catch (error) {
    fail(error.message);
  }
}

function agentOutsideMessage(raw, home, agents, command) {
  return `agent ${JSON.stringify(raw)} is not under\n${agents}${path.sep}.\nignite ${command}s only an agent that lives there. ignite does not copy an agent.\nNothing changed.\nPlace it under ${agents}${path.sep}, then ${command} that name.`;
}

function isInside(folder, parent) {
  const relative = path.relative(parent, folder);
  return relative !== '' && !relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative);
}

function resolveAgent(config, raw, command) {
  const agents = agentsFolder(config.workspace);
  const home = isPath(raw) ? path.resolve(raw) : agentHome(config, raw);
  if (!isInside(home, agents)) fail(agentOutsideMessage(raw, home, agents, command));
  const agent = path.basename(home);
  if (!SLUG.test(agent)) fail(`agent name must match [a-z0-9][a-z0-9-]{0,63}`);
  return { agent, home, agents };
}

function requireInstalled(config, raw, command) {
  const resolved = resolveAgent(config, raw, command);
  const { agent, home } = resolved;
  if (!fs.existsSync(home)) {
    fail(`agent ${agent} is not installed (no folder at ${home}).\nAdd it with: rbtv agent add ${agent} --harness HARNESS --model MODEL --effort EFFORT\nNothing changed.`);
  }
  if (!isAgentFolder(home)) {
    fail(`agent ${agent} is not installed (needs prompt.md and agent.json at ${home})`);
  }
  return resolved;
}

function installerCommand(args, workspace) {
  const python = process.platform === 'win32' ? 'python' : 'python3';
  return spawnSync(python, [INSTALLER_ENTRY, ...args], {
    cwd: workspace,
    encoding: 'utf8',
    maxBuffer: 10 * 1024 * 1024,
  });
}

async function runInstaller(args, workspace, deps) {
  if (deps.install) {
    const result = await deps.install(args);
    return { status: result?.status ?? 0, stdout: result?.stdout || '', stderr: result?.stderr || '' };
  }
  const result = installerCommand(args, workspace);
  if (result.error) fail(`rbtv agent failed: ${result.error.message}`);
  return { status: result.status ?? 1, stdout: result.stdout || '', stderr: result.stderr || '' };
}

function installerResult(result) {
  if (result.status === 0) {
    try { return JSON.parse(result.stdout); } catch { return {}; }
  }
  try {
    const body = JSON.parse(result.stdout);
    if (body.error?.message) fail(body.error.message);
  } catch (error) {
    if (error.exitCode) throw error;
  }
  fail((result.stderr || result.stdout || 'rbtv agent failed').trim());
}

// The installer's JSON carries the files after the change and the files it added or removed; the
// count before it is the difference. Every file is counted once, packs' files included.
async function setIgnitePack(verb, home, workspace, dryRun, deps) {
  const args = ['agent', verb, home, '--pack', 'ignite', '--json'];
  if (dryRun) args.push('--dry-run');
  const body = installerResult(await runInstaller(args, workspace, deps));
  const after = body.files.length;
  return { before: verb === 'add' ? after - body.added.length : after + body.files_removed.length, after };
}

function packIsOn(home) {
  const read = readAgent(home);
  if (read.problem) fail(`agent.json: ${read.why}`);
  return read.agent.ignite;
}

function ensureRuntime(home) {
  fs.mkdirSync(path.join(home, 'conversations'), { recursive: true });
  const board = migrateBoard(home);
  if (!fs.existsSync(board)) {
    writeBoard(board, fs.readFileSync(path.join(__dirname, 'templates', 'board.md.tmpl'), 'utf8'));
  }
  const db = path.join(home, 'state.sqlite');
  if (!fs.existsSync(db)) {
    const store = new Store(db);
    store.close();
  }
}

function runtimeChanges(home) {
  const paths = [boardPath(home), path.join(home, 'state.sqlite'), path.join(home, 'conversations')];
  const missing = paths.filter((file) => !fs.existsSync(file));
  ensureRuntime(home);
  return missing;
}

function scheduleFrom(file, now) {
  const body = readJson(file, '--schedule-json');
  if (!body || typeof body !== 'object' || Array.isArray(body)) fail('--schedule-json must be an object');
  const cadenceKeys = ['cron', 'every', 'at'].filter((key) => body[key] != null && body[key] !== '');
  if (cadenceKeys.length !== 1) fail('--schedule-json requires exactly one of cron, every, at');
  if (body.cron != null && !body.tz) fail('--schedule-json cron requires tz');
  if (body.every != null && body.tz !== FIXED_TZ) fail(`--schedule-json every requires tz ${FIXED_TZ}`);
  if (body.at != null && body.tz) fail('--schedule-json at carries its offset; do not also set tz');
  if (!body.note || !String(body.note).trim()) fail('--schedule-json note is required');
  const report = body.report || 'when-useful';
  if (report !== 'always' && report !== 'when-useful') fail('--schedule-json report must be always or when-useful');
  const spec = cadenceSpec({
    at: body.at || undefined,
    cron: body.cron || undefined,
    every: body.every || undefined,
    tz: body.every != null ? undefined : body.tz || undefined,
  });
  const nextAt = spec.nextAt != null ? spec.nextAt : nextOccurrence(spec.cadence, spec.timezone, now);
  return { ...spec, nextAt, note: String(body.note).trim(), report };
}

function slackClient(config, deps) {
  if (deps.slack) return deps.slack;
  return new Slack({
    botToken: slackToken(config, 'bot'),
    stoolsWorkspace: config.slack.stoolsWorkspace,
  });
}

// The route is written the moment the channel exists, so config.json is the one record of it:
// a re-run after any later failure finds the route and reuses the channel.
async function ensureChannel(ctx, slack, deps) {
  const { opts, routes, workspace } = ctx;
  if (routes.length > 1) fail(`agent ${opts.agent} has more than one channel route`);
  if (routes.length === 1) return { id: routes[0][0], name: opts['channel-name'], reused: true };
  const created = await slack.createChannel(opts['channel-name']);
  if (!created?.id) fail('createChannel returned no id');
  updateConfig(workspace, (raw) => {
    const taken = raw.routes[created.id];
    if (taken && taken !== opts.agent) fail(`channel ${created.id} is already routed to ${taken}`);
    raw.routes[created.id] = opts.agent;
  });
  if (deps.afterChannel) await deps.afterChannel({ channelId: created.id });
  return { id: created.id, name: created.name || opts['channel-name'], reused: false };
}

// One timer per connection: a re-run updates the timer already bound to the board conversation.
async function bindSchedule(ctx) {
  const { config, opts, home, schedule, channel } = ctx;
  if (!schedule) return { scheduleId: null, warning: null };
  const channelId = opts.dm ? config.slack.ownerUserId : channel.id;
  const key = conversationKey(config.slack.team, channelId, BOARD_ROOT);
  preflightBoard(home);
  const store = new Store(path.join(home, 'state.sqlite'));
  try {
    store.upsertConversation({
      key, agent: opts.agent, workspace: config.slack.team, channel: channelId, rootTs: BOARD_ROOT, activated: false,
    });
    const bound = store.listSchedules().find((row) => row.conversation_key === key);
    const id = bound ? bound.id : randomUUID();
    store.upsertSchedule({
      id,
      conversationKey: key,
      cadence: schedule.cadence,
      timezone: schedule.timezone,
      nextAt: schedule.nextAt,
      enabled: true,
      note: schedule.note,
      report: schedule.report,
      subject: bound?.subject ?? null,
    });
    const warning = refreshBoardAfterCommit(home, store, [id]);
    return { scheduleId: id, warning };
  } finally {
    store.close();
  }
}

function cancelTimers(home) {
  const db = path.join(home, 'state.sqlite');
  if (!fs.existsSync(db)) return { timers: [], warning: null };
  const store = new Store(db);
  try {
    const ids = store.listSchedules().map((row) => row.id);
    preflightBoard(home);
    for (const id of ids) store.deleteSchedule(id);
    if (!ids.length) refreshBoard(home, store);
    const warning = ids.length ? refreshBoardAfterCommit(home, store, ids) : null;
    return { timers: ids, warning };
  } finally {
    store.close();
  }
}

function connectPlan(opts, home, schedule, pack) {
  return [
    'dry-run',
    `connect: ${opts.agent}`,
    `home: ${home}`,
    'pack: ignite',
    `files: ${pack.before}${pack.after === pack.before ? '' : ` -> ${pack.after}`}`,
    'working files: would create',
    opts.dm ? 'channel: none (dm)' : `channel: ${opts['channel-name']}`,
    `schedule: ${schedule ? `${schedule.cadence} ${schedule.timezone}` : 'none'}`,
    'writes: none',
    '',
  ].join('\n');
}

async function connectAgent(opts, flags, deps) {
  const workspace = workspaceOf(flags);
  const config = requireConfig(workspace);
  const resolved = requireInstalled(config, opts.agent, 'connect');
  const { home, agent } = resolved;
  opts.agent = agent;
  if (opts.dm && opts['channel-name']) fail('pass either --channel-name or --dm, not both');
  if (!opts.dm && !opts['channel-name']) fail('--channel-name or --dm required');
  if (opts['channel-name'] && !CHANNEL.test(opts['channel-name'])) {
    fail('channel name must be lowercase letters, numbers, hyphens, or underscores, at most 80 characters');
  }
  const routes = routesFor(config, opts.agent);
  if (routes.length > 1) fail(`agent ${opts.agent} has more than one channel route`);
  if (opts.dm && routes.length === 1) fail(`agent ${opts.agent} already has a channel route`);
  if (!opts.dm && config.dmAgent === opts.agent) fail(`agent ${opts.agent} already receives direct messages`);
  if (opts.dm && config.dmAgent && config.dmAgent !== opts.agent) {
    fail(`direct messages already go to ${config.dmAgent}. Disconnect that agent first.`);
  }
  const now = deps.now ? deps.now() : Date.now();
  const schedule = opts['schedule-json'] ? scheduleFrom(opts['schedule-json'], now) : null;
  const pack = await setIgnitePack('add', home, workspace, opts.dryRun, deps);
  if (opts.dryRun) {
    emit(deps, flags, {
      dryRun: true,
      agent: opts.agent,
      home,
      dm: opts.dm,
      channelName: opts['channel-name'] || null,
      schedule: schedule ? { cadence: schedule.cadence, timezone: schedule.timezone } : null,
      writes: 'none',
    }, connectPlan(opts, home, schedule, pack));
    return 0;
  }
  const created = runtimeChanges(home);
  let channel = null;
  let joined = false;
  let invited = false;
  let scheduleId;
  let warning;
  try {
    if (!opts.dm) {
      const slack = slackClient(config, deps);
      channel = await ensureChannel({ opts, routes, workspace }, slack, deps);
      await slack.joinChannel(channel.id);
      joined = true;
      await slack.inviteUser(channel.id, config.slack.ownerUserId);
      invited = true;
    } else {
      updateConfig(workspace, (raw) => {
        raw.dmAgent = opts.agent;
      });
    }
    ({ scheduleId, warning } = await bindSchedule({ config, opts, home, schedule, channel }));
  } catch (error) {
    const details = [`failed: Slack, after the pack and the working files`, `files: ${pack.before}${pack.after === pack.before ? '' : ` -> ${pack.after}`}`, 'pack: ignite', runtimeText(created)];
    details.push(`Slack failed: ${error.message}`, 'The pack and the working files stay.',
      channel ? `The route ${channel.id} stays and will be reused.` : 'No route was written.',
      `Rerun: ignite connect ${agent}${opts.dm ? ' --dm' : ` --channel-name ${opts['channel-name']}`}`);
    fail(details.join('\n'));
  }
  const link = channel ? `https://slack.com/app_redirect?channel=${channel.id}&team=${config.slack.team}` : null;
  const lines = [`connected ${opts.agent}`, 'pack: ignite', `files: ${pack.before}${pack.after === pack.before ? '' : ` -> ${pack.after}`}`, runtimeText(created)];
  if (opts.dm) {
    lines.push('channel: none (dm)', `dmAgent: ${opts.agent}`);
  } else {
    lines.push(`channel: ${channel.id} ${channel.name}`, `route: ${channel.id} -> ${opts.agent}`);
    lines.push(joined && invited ? 'bot=joined owner=invited' : `bot=${joined ? 'joined' : 'missing'} owner=${invited ? 'invited' : 'missing'}`);
    lines.push(`link: ${link}`);
  }
  lines.push(`schedule: ${scheduleId || 'none'}`);
  if (warning) lines.push(warning);
  emit(deps, flags, {
    connected: opts.agent, channel, link, scheduleId, dmAgent: opts.dm ? opts.agent : null,
    ...(warning ? { warning } : {}),
  }, `${lines.join('\n')}\n`);
  return 0;
}

async function disconnectAgent(opts, flags, deps) {
  const workspace = workspaceOf(flags);
  const config = requireConfig(workspace);
  const resolved = requireInstalled(config, opts.agent, 'disconnect');
  const { home, agent } = resolved;
  opts.agent = agent;
  const routes = routesFor(config, opts.agent).map(([id]) => id);
  const dm = config.dmAgent === opts.agent;
  const channelIds = routes;
  if (opts.dryRun) {
    const pack = await setIgnitePack('remove', home, workspace, true, deps);
    emit(deps, flags, {
      dryRun: true, agent: opts.agent, home, routes, dm, archive: opts.archiveChannel, writes: 'none',
    }, `dry-run\ndisconnect: ${opts.agent}\nhome: ${home}\nroutes: ${routes.join(', ') || 'none'}\ndm: ${dm}\narchive: ${opts.archiveChannel}\npack: ignite\nfiles: ${pack.before}${pack.after === pack.before ? '' : ` -> ${pack.after}`}\nwrites: none\n`);
    return 0;
  }
  const archived = [];
  if (opts.archiveChannel && channelIds.length) {
    const slack = slackClient(config, deps);
    for (const id of channelIds) {
      await slack.archiveChannel(id);
      archived.push(id);
    }
  }
  updateConfig(workspace, (raw) => {
    for (const id of Object.keys(raw.routes)) {
      if (raw.routes[id] === opts.agent) delete raw.routes[id];
    }
    if (raw.dmAgent === opts.agent) delete raw.dmAgent;
  });
  const { timers, warning } = fs.existsSync(home) ? cancelTimers(home) : { timers: [], warning: null };
  const wasOn = packIsOn(home);
  const pack = await setIgnitePack('remove', home, workspace, false, deps);
  emit(deps, flags, {
    disconnected: opts.agent, archived, timers, home, kept: true, ...(warning ? { warning } : {}),
  }, `disconnected ${opts.agent}\nroutes: ${routes.length ? `removed ${routes.join(', ')}` : 'none'}\ndmAgent: ${dm ? 'cleared' : 'unchanged'}\narchived: ${opts.archiveChannel ? archived.join(', ') || 'none' : 'no'}\ntimers: ${timers.join(', ') || 'none'}\npack: ignite ${wasOn ? 'off' : 'already off'}\nfiles: ${pack.before}${pack.after === pack.before ? '' : ` -> ${pack.after}`}\nhome: kept\n${warning ? `${warning}\n` : ''}`);
  return 0;
}

function runtimeText(created) {
  return created.length ? `working files: created\n${created.map((file) => `  ${file}`).join('\n')}` : 'working files: present';
}

function agentOf(positionals) {
  const agent = positionals[0];
  if (!agent) fail('an agent name is required');
  if (positionals.length > 1) fail(`unexpected argument: ${positionals[1]}`);
  return agent;
}

async function run(command, argv, flags, deps = {}) {
  if (flags.help) {
    emit(deps, { json: false }, { help: command }, HELP[command]);
    return 0;
  }
  const known = command === 'connect'
    ? new Set(['channel-name', 'schedule-json', 'dm'])
    : new Set(['archive-channel']);
  const { opts, positionals } = parseArgs(argv, known);
  opts.agent = agentOf(positionals);
  if (command === 'connect') return connectAgent(opts, flags, deps);
  if (command === 'disconnect') return disconnectAgent(opts, flags, deps);
  fail(`unknown command: ${command}`);
}

module.exports = { run, HELP, ensureRuntime, runInstaller, installerCommand, INSTALLER_ENTRY };
