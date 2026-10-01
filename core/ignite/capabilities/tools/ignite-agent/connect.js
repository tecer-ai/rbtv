'use strict';

// API — ignite-agent connect | disconnect. run(command, argv, flags, deps) → Promise<exit code>.
// flags.workspace / flags.json / flags.help come from cli.js parseGlobal.
// deps.slack stubs Slack. deps.afterChannel() runs after the route write and before the bot joins.
// The agent must already be installed (launch.json). Config must already exist; this does not create it.
// Slack tokens come from slackToken(config, …) and are never printed.
// A re-run reuses the channel already routed; config.json is the only record of a connection.
// disconnect removes routes and dmAgent, optionally archives the channel, and cancels timers.
// It does not delete the agent folder.

const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { loadConfig, updateConfig, agentHome, configPath, slackToken } = require('./config.js');
const { Slack } = require('./slack.js');
const { Store, conversationKey } = require('./store.js');
const { cadenceSpec, nextOccurrence, FIXED_TZ } = require('./schedule.js');
const { migrateBoard, refreshBoard } = require('./board.js');

const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;
const CHANNEL = /^[a-z0-9][a-z0-9_-]{0,79}$/;
const BOARD_ROOT = 'board';
const RUNBOOK = 'core/ignite/capabilities/runbook.md';

const HELP = `ignite-agent connect — connect or disconnect an installed agent

connect <agent> (--channel-name <name> | --dm) [--schedule-json <file>]
        [--workspace <path>] [--dry-run] [--json]

  Run on the machine that will run the agent. The agent must already be installed
  (agent.md in <workspace>/.rbtv/agents/<agent>/).
  Needs <workspace>/.rbtv/config/ignite/config.json. This command does not write that
  file. See ${RUNBOOK}.
  --channel-name: create the Slack channel, the bot joins, the owner is invited,
  routes[channelId] = agent. A re-run reuses a channel already routed.
  --dm: set dmAgent to the agent. Pass either --channel-name or --dm, not both.
  --schedule-json binds a timer the way a creation-time schedule was bound.
  --dry-run validates and prints the plan. It writes nothing.
  Slack tokens are read from the environment variables the config names. They are never printed.

  --schedule-json object, exactly one of cron, every, at:
    { "cron": "<5-field>", "tz": "<IANA zone>", "note": "<check>", "report": "always|when-useful" }
    { "every": "<duration>", "tz": "fixed", "note": "<check>" }
    { "at": "<ISO datetime with offset>", "note": "<check>" }
  report defaults to when-useful. A missing cadence or timezone is refused.

disconnect <agent> [--archive-channel] [--workspace <path>] [--dry-run] [--json]

  Removes the agent's route(s) and dmAgent from the config, cancels its timers,
  and archives its channel when asked. Does not delete the agent folder.
  Uninstalling is: rbtv install agent remove <agent>
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
  if (!flags.workspace) fail('--workspace required');
  return path.resolve(flags.workspace);
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
    fail(`Ignite config not found: ${file}\nCreate that file before connect. See ${RUNBOOK}`);
  }
  try {
    return loadConfig(workspace);
  } catch (error) {
    fail(error.message);
  }
}

function requireInstalled(config, agent) {
  const home = agentHome(config, agent);
  if (!fs.existsSync(path.join(home, 'launch.json'))) {
    fail(`agent ${agent} is not installed (no launch.json at ${home}). Install it with: ignite-agent install <agent file> --harness … --model … --effort …`);
  }
  return home;
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
  if (!schedule) {
    migrateBoard(home);
    return null;
  }
  const channelId = opts.dm ? config.slack.ownerUserId : channel.id;
  const key = conversationKey(config.slack.team, channelId, BOARD_ROOT);
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
    refreshBoard(home, store);
    return id;
  } finally {
    store.close();
  }
}

function cancelTimers(home) {
  const db = path.join(home, 'state.sqlite');
  if (!fs.existsSync(db)) return [];
  const store = new Store(db);
  try {
    const ids = store.listSchedules().map((row) => row.id);
    for (const id of ids) store.deleteSchedule(id);
    refreshBoard(home, store);
    return ids;
  } finally {
    store.close();
  }
}

function connectPlan(opts, home, schedule) {
  return [
    'dry-run',
    `connect: ${opts.agent}`,
    `home: ${home}`,
    opts.dm ? 'channel: none (dm)' : `channel: ${opts['channel-name']}`,
    `schedule: ${schedule ? `${schedule.cadence} ${schedule.timezone}` : 'none'}`,
    'writes: none',
    '',
  ].join('\n');
}

async function connectAgent(opts, flags, deps) {
  const workspace = workspaceOf(flags);
  const config = requireConfig(workspace);
  const home = requireInstalled(config, opts.agent);
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
  if (opts.dryRun) {
    emit(deps, flags, {
      dryRun: true,
      agent: opts.agent,
      home,
      dm: opts.dm,
      channelName: opts['channel-name'] || null,
      schedule: schedule ? { cadence: schedule.cadence, timezone: schedule.timezone } : null,
      writes: 'none',
    }, connectPlan(opts, home, schedule));
    return 0;
  }
  let channel = null;
  let joined = false;
  let invited = false;
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
  const scheduleId = await bindSchedule({ config, opts, home, schedule, channel });
  const link = channel ? `https://slack.com/app_redirect?channel=${channel.id}&team=${config.slack.team}` : null;
  const lines = [`connected ${opts.agent}`];
  if (opts.dm) {
    lines.push('channel: none (dm)', `dmAgent: ${opts.agent}`);
  } else {
    lines.push(`channel: ${channel.id} ${channel.name}`, `route: ${channel.id} -> ${opts.agent}`);
    lines.push(joined && invited ? 'bot=joined owner=invited' : `bot=${joined ? 'joined' : 'missing'} owner=${invited ? 'invited' : 'missing'}`);
    lines.push(`link: ${link}`);
  }
  lines.push(`schedule: ${scheduleId || 'none'}`);
  emit(deps, flags, {
    connected: opts.agent, channel, link, scheduleId, dmAgent: opts.dm ? opts.agent : null,
  }, `${lines.join('\n')}\n`);
  return 0;
}

async function disconnectAgent(opts, flags, deps) {
  const workspace = workspaceOf(flags);
  const config = requireConfig(workspace);
  const home = agentHome(config, opts.agent);
  const routes = routesFor(config, opts.agent).map(([id]) => id);
  const dm = config.dmAgent === opts.agent;
  const channelIds = routes;
  if (opts.dryRun) {
    emit(deps, flags, {
      dryRun: true, agent: opts.agent, home, routes, dm, archive: opts.archiveChannel, writes: 'none',
    }, `dry-run\ndisconnect: ${opts.agent}\nhome: ${home}\nroutes: ${routes.join(', ') || 'none'}\ndm: ${dm}\narchive: ${opts.archiveChannel}\nwrites: none\n`);
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
  const timers = fs.existsSync(home) ? cancelTimers(home) : [];
  emit(deps, flags, {
    disconnected: opts.agent, archived, timers, home, kept: true,
  }, `disconnected ${opts.agent}\nroutes: ${routes.length ? `removed ${routes.join(', ')}` : 'none'}\ndmAgent: ${dm ? 'cleared' : 'unchanged'}\narchived: ${opts.archiveChannel ? archived.join(', ') || 'none' : 'no'}\ntimers: ${timers.join(', ') || 'none'}\nhome: kept\n`);
  return 0;
}

function agentOf(positionals) {
  const agent = positionals[0];
  if (!agent) fail('an agent name is required');
  if (positionals.length > 1) fail(`unexpected argument: ${positionals[1]}`);
  if (!SLUG.test(agent)) fail('agent name must match [a-z0-9][a-z0-9-]{0,63}');
  return agent;
}

async function run(command, argv, flags, deps = {}) {
  if (flags.help) {
    emit(deps, { json: false }, { help: command }, HELP);
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

module.exports = { run, HELP };
