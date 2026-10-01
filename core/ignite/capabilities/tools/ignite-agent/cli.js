#!/usr/bin/env node
'use strict';

// API — entry `ignite-agent`. Home from IGNITE_AGENT_HOME, or --agent <slug> + --workspace <path>.
// main(argv, deps) → exit code, or a Promise for install/update/connect/disconnect.
// deps.validateLaunch stubs cast. deps.install stubs the installer. deps.slack stubs Slack.
// deps.stdout / deps.stderr / deps.env optional.
// settings set validates through cast list --json (never a copied model list) and writes launch.json
// plus the store row together. schedule next-occurrence lives in schedule.js.
// install, update, connect, and disconnect run before a home is opened. There is no create command.

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const { Store } = require('./store.js');
const { loadConfig, agentHome, configPath } = require('./config.js');
const { cadenceSpec, nextOccurrence, FIXED_TZ } = require('./schedule.js');

const APPLIES = 'applies from the next turn in every conversation';
const COMMANDS = ['settings', 'schedule', 'schedules-due', 'work', 'wake', 'post'];
const REPORTS = new Set(['always', 'when-useful']);

const HELP = `ignite-agent — install update connect disconnect settings schedule schedules-due work wake post

install <agent file> --harness <name> --model <cast short name> --effort <rung or 1-5> [--workspace <path>] [--dry-run]
  Runs rbtv install agent add, then installs Ignite's standard units. No Slack.
  Refuses when the agent is already installed; use update.
update <agent> [--workspace <path>] [--dry-run]
  Runs rbtv install agent update, then re-installs Ignite's standard units.
  Keeps launch.json, settings.json, board.md, the database, and conversations.
connect <agent> (--channel-name <name> | --dm) [--schedule-json <file>] [--workspace <path>] [--dry-run]
  On the machine that will run the agent. Needs .rbtv/config/ignite/config.json.
  See core/ignite/capabilities/runbook.md. Does not write that file.
disconnect <agent> [--archive-channel] [--workspace <path>] [--dry-run]
  Removes the route and direct-message assignment. Does not delete the agent folder.

Home: IGNITE_AGENT_HOME, or --agent <slug> --workspace <path>
      (workspace defaults to the directory walk that finds .rbtv/config/ignite/config.json).
--json selects JSON on stdout. Inside a turn the runtime also sets IGNITE_CONVERSATION.

settings show
settings set --harness <name> --model <cast short name> --effort <rung or 1-5> [--voice <id>]
  Validates the combination through cast. ${APPLIES}.

schedule add (--at <ISO datetime with offset> | --cron "<5-field>" --tz <IANA zone> | --every <duration>) --note <text> [--report always|when-useful] [--conversation <key>]
schedule list
schedule change <id> [same cadence flags] [--note <text>] [--report always|when-useful] [--enabled true|false]
schedule cancel <id>
  Cron requires an explicit --tz. Next occurrence is timezone-aware.
  --every is a fixed-interval: elapsed time, no timezone, DST does not move it.
  A recurring schedule requires a cadence (--cron or --every). An empty cadence is refused.

schedules-due --now <ISO datetime>
  Enqueue one board wake per due schedule. While one schedule wake is pending, further dues are de-duplicated. Never enqueues for a held or stopped item, and never clears a hold.

work status [--conversation <key>]
work retry|resume [<id>]
  With an id, clears only that work hold. With no id, clears only an agent hold.
work stop <id>
  Stops that assignment. Does not cancel schedules and does not clear an agent hold.

wake --conversation <key> --note <text> [--work <id>]
  Worker completion. Enqueues a continuation. Does not clear a hold.

post (--text <text> | --text-file <path> | --file <path>)... [--audio]
  Enqueues an outbox row that opens a new thread in the agent's channel (the DM agent uses the owner's user id as the IM target) and associates that conversation immediately, activated.
`;

function take(argv, i, flag) {
  const value = argv[i + 1];
  if (value == null || value.startsWith('--')) throw new Error(`${flag} requires a value`);
  return value;
}

function parseGlobal(argv) {
  const flags = { json: false, help: false, agent: null, workspace: null };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--json') flags.json = true;
    else if (arg === '--help' || arg === '-h') flags.help = true;
    else if (arg === '--agent') flags.agent = take(argv, i, arg), i += 1;
    else if (arg === '--workspace') flags.workspace = take(argv, i, arg), i += 1;
    else rest.push(arg);
  }
  return { flags, rest };
}

function parseOpts(argv) {
  const opts = {};
  const positionals = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--audio') opts.audio = true;
    else if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const value = take(argv, i, arg);
      i += 1;
      if (key === 'file') {
        opts.file = opts.file || [];
        opts.file.push(value);
      } else if (opts[key] != null) {
        throw new Error(`duplicate flag --${key}`);
      } else {
        opts[key] = value;
      }
    } else {
      positionals.push(arg);
    }
  }
  return { opts, positionals };
}

function emit(deps, flags, payload, human) {
  const write = deps.stdout || ((text) => process.stdout.write(text));
  write(flags.json ? `${JSON.stringify(payload)}\n` : human);
}

function fail(message) {
  const error = new Error(message);
  error.exitCode = 1;
  throw error;
}

function workspaceFromHome(home) {
  const agents = path.dirname(home);
  const dot = path.dirname(agents);
  if (path.basename(agents) === 'agents' && path.basename(dot) === '.rbtv') return path.dirname(dot);
  return null;
}

function findWorkspace(start) {
  let dir = path.resolve(start);
  for (;;) {
    if (fs.existsSync(configPath(dir))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function resolveHome(flags, deps) {
  const env = deps.env || process.env;
  if (env.IGNITE_AGENT_HOME) {
    const home = env.IGNITE_AGENT_HOME;
    return { home, slug: flags.agent || path.basename(home), workspace: flags.workspace || workspaceFromHome(home) };
  }
  if (!flags.agent) fail('--agent or IGNITE_AGENT_HOME required');
  const workspace = flags.workspace || findWorkspace(process.cwd());
  if (!workspace) fail('--workspace required with --agent');
  const config = loadConfig(workspace);
  return { home: agentHome(config, flags.agent), slug: flags.agent, workspace, config };
}

function openContext(flags, deps) {
  const located = resolveHome(flags, deps);
  const config = located.config || (located.workspace && fs.existsSync(configPath(located.workspace))
    ? loadConfig(located.workspace)
    : null);
  return {
    ...located,
    config,
    store: new Store(path.join(located.home, 'state.sqlite')),
    castCmd: config?.tools?.cast || 'cast',
  };
}

function resolveEffort(rungs, effort, harness, model) {
  if (!rungs.length) {
    if (effort === 'inert') return 'inert';
    const n = Number(effort);
    if (String(n) === String(effort) && Number.isInteger(n) && n >= 1 && n <= 5) return 'inert';
    throw new Error(`unsupported effort for ${harness}/${model}: ${effort}`);
  }
  if (rungs.includes(effort)) return effort;
  const n = Number(effort);
  if (String(n) === String(effort) && Number.isInteger(n) && n >= 1 && n <= 5) {
    return rungs[Math.min(n, rungs.length) - 1];
  }
  throw new Error(`unsupported effort for ${harness}/${model}: ${effort}`);
}

function validateLaunch(castCmd, setting) {
  const res = spawnSync(castCmd, ['list', '--json'], { encoding: 'utf8' });
  if (res.error) throw new Error(`cannot run cast: ${res.error.message}`);
  if (res.status !== 0) throw new Error((res.stderr || res.stdout || 'cast list failed').trim());
  let inventory;
  try {
    inventory = JSON.parse(res.stdout);
  } catch {
    throw new Error('cast list --json did not return JSON');
  }
  const models = inventory[setting.harness];
  if (!models || typeof models !== 'object') throw new Error(`unknown harness: ${setting.harness}`);
  if (!Object.prototype.hasOwnProperty.call(models, setting.model)) {
    throw new Error(`unknown model for ${setting.harness}: ${setting.model}`);
  }
  return {
    harness: setting.harness,
    model: setting.model,
    effort: resolveEffort(models[setting.model], setting.effort, setting.harness, setting.model),
    voice: setting.voice ?? null,
  };
}

function launchBody(setting) {
  const body = { harness: setting.harness, model: setting.model, effort: setting.effort };
  if (setting.voice) body.voice = setting.voice;
  return body;
}

function readLaunch(home) {
  const file = path.join(home, 'launch.json');
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function applySetting(store, home, setting) {
  const file = path.join(home, 'launch.json');
  const backup = fs.existsSync(file) ? fs.readFileSync(file) : null;
  const tmp = `${file}.${process.pid}.tmp`;
  fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(tmp, `${JSON.stringify(launchBody(setting), null, 2)}\n`);
  try {
    return store.transaction(() => {
      const row = store.setLaunchSetting(setting);
      fs.renameSync(tmp, file);
      return row;
    });
  } catch (error) {
    fs.rmSync(tmp, { force: true });
    if (backup == null) fs.rmSync(file, { force: true });
    else fs.writeFileSync(file, backup);
    throw error;
  }
}

function requireNote(opts) {
  if (!opts.note || !opts.note.trim()) fail('--note is required');
  return opts.note;
}

function reportOf(opts, fallback) {
  const report = opts.report ?? fallback ?? 'when-useful';
  if (!REPORTS.has(report)) fail('--report must be always or when-useful');
  return report;
}

function conversationOf(opts, deps) {
  const env = deps.env || process.env;
  const key = opts.conversation || env.IGNITE_CONVERSATION;
  if (!key) fail('schedule requires IGNITE_CONVERSATION or --conversation');
  return key;
}

function settingFrom(opts, previous) {
  return {
    harness: opts.harness,
    model: opts.model,
    effort: opts.effort,
    voice: opts.voice !== undefined ? opts.voice : (previous?.voice ?? null),
  };
}

function cmdSettings(rest, ctx, flags, deps) {
  const action = rest[0];
  if (!action || action === '--help') {
    emit(deps, flags, { help: 'settings' }, HELP);
    return 0;
  }
  if (action === 'show') {
    const storeRow = ctx.store.getLaunchSetting();
    const file = readLaunch(ctx.home);
    emit(deps, flags, { store: storeRow, file }, storeRow
      ? `${storeRow.harness} ${storeRow.model} ${storeRow.effort}${storeRow.voice ? ` voice=${storeRow.voice}` : ''}\n`
      : 'no launch setting\n');
    return 0;
  }
  if (action !== 'set') fail('settings requires show or set');
  const { opts } = parseOpts(rest.slice(1));
  if (!opts.harness || !opts.model || !opts.effort) fail('settings set requires --harness, --model and --effort');
  const previous = ctx.store.getLaunchSetting() || readLaunch(ctx.home);
  const requested = settingFrom(opts, previous);
  const setting = deps.validateLaunch
    ? deps.validateLaunch(requested)
    : validateLaunch(ctx.castCmd, requested);
  if (setting.voice === undefined) setting.voice = requested.voice;
  const row = applySetting(ctx.store, ctx.home, setting);
  emit(deps, flags, { setting: row, notice: APPLIES }, `${APPLIES}\n`);
  return 0;
}

function addSpec(opts, fromMs) {
  const spec = cadenceSpec({ at: opts.at, cron: opts.cron, every: opts.every, tz: opts.tz });
  const nextAt = spec.nextAt != null ? spec.nextAt : nextOccurrence(spec.cadence, spec.timezone, fromMs);
  return { ...spec, nextAt };
}

function cmdSchedule(rest, ctx, flags, deps) {
  const action = rest[0];
  if (!action || action === '--help') {
    emit(deps, flags, { help: 'schedule' }, HELP);
    return 0;
  }
  if (action === 'list') {
    const rows = ctx.store.listSchedules();
    emit(deps, flags, { schedules: rows }, rows.length
      ? `${rows.map((row) => `${row.id} ${row.cadence} ${row.timezone} next=${row.next_at} enabled=${row.enabled} ${row.note || ''}`).join('\n')}\n`
      : 'no schedules\n');
    return 0;
  }
  if (action === 'add') {
    const { opts } = parseOpts(rest.slice(1));
    const note = requireNote(opts);
    const key = conversationOf(opts, deps);
    if (!ctx.store.getConversation(key)) fail(`unknown conversation: ${key}`);
    const now = deps.now ? deps.now() : Date.now();
    const spec = addSpec(opts, now);
    const row = ctx.store.upsertSchedule({
      id: randomUUID(),
      conversationKey: key,
      cadence: spec.cadence,
      timezone: spec.timezone,
      nextAt: spec.nextAt,
      enabled: true,
      note,
      report: reportOf(opts),
    });
    emit(deps, flags, { schedule: row }, `${row.id} ${row.cadence} ${row.timezone} next=${row.next_at}\n`);
    return 0;
  }
  if (action === 'change') {
    const { opts, positionals } = parseOpts(rest.slice(1));
    const id = positionals[0];
    if (!id) fail('schedule change requires an id');
    const existing = ctx.store.getSchedule(id);
    if (!existing) fail(`unknown schedule: ${id}`);
    const now = deps.now ? deps.now() : Date.now();
    let cadence = existing.cadence;
    let timezone = existing.timezone;
    let nextAt = existing.next_at;
    if (opts.at != null || opts.cron != null || opts.every != null || opts.tz != null) {
      const spec = addSpec({
        at: opts.at,
        cron: opts.cron ?? (opts.at == null && opts.every == null && existing.cadence.startsWith('cron:') ? existing.cadence.slice(5) : undefined),
        every: opts.every ?? (opts.at == null && opts.cron == null && existing.cadence.startsWith('every:') ? existing.cadence.slice(6) : undefined),
        tz: opts.tz ?? (opts.at == null && opts.every == null && existing.cadence.startsWith('cron:') ? existing.timezone : undefined),
      }, now);
      cadence = spec.cadence;
      timezone = spec.timezone;
      nextAt = spec.nextAt;
    }
    if ((cadence.startsWith('cron:') || cadence.startsWith('every:')) && !cadence.slice(cadence.indexOf(':') + 1)) {
      fail('a recurring schedule requires a cadence');
    }
    const enabled = opts.enabled == null ? existing.enabled : opts.enabled === 'true';
    if (opts.enabled != null && opts.enabled !== 'true' && opts.enabled !== 'false') fail('--enabled must be true or false');
    const row = ctx.store.upsertSchedule({
      id,
      conversationKey: existing.conversation_key,
      workId: existing.work_id,
      cadence,
      timezone,
      nextAt,
      enabled,
      note: opts.note ?? existing.note,
      report: reportOf(opts, existing.report),
    });
    emit(deps, flags, { schedule: row }, `${row.id} ${row.cadence} ${row.timezone} next=${row.next_at}\n`);
    return 0;
  }
  if (action === 'cancel') {
    const { positionals } = parseOpts(rest.slice(1));
    const id = positionals[0];
    if (!id) fail('schedule cancel requires an id');
    if (!ctx.store.deleteSchedule(id)) fail(`unknown schedule: ${id}`);
    emit(deps, flags, { cancelled: id }, `cancelled ${id}\n`);
    return 0;
  }
  fail('schedule requires add, list, change, or cancel');
}

function blockedReason(store, sched) {
  if (store.agentHold()) return 'agent_hold';
  if (!sched.work_id) return null;
  const work = store.getWork(sched.work_id);
  if (!work) return null;
  if (work.state === 'held' || work.state === 'stopped') return work.state;
  return null;
}

function cmdDue(rest, ctx, flags, deps) {
  const { opts } = parseOpts(rest);
  if (!opts.now) fail('schedules-due requires --now <ISO datetime>');
  const now = Date.parse(opts.now);
  if (Number.isNaN(now)) fail(`bad --now datetime: ${opts.now}`);
  const results = [];
  for (const sched of ctx.store.dueSchedules(now)) {
    const blocked = blockedReason(ctx.store, sched);
    if (blocked) {
      results.push({ id: sched.id, inserted: false, reason: blocked, nextAt: sched.next_at });
      continue;
    }
    const wake = ctx.store.enqueueScheduleWake({
      id: `schedule:${sched.id}:${sched.next_at}`,
      conversationKey: sched.conversation_key,
      scheduleId: sched.id,
      workId: sched.work_id,
      payload: { note: sched.note, report: sched.report, cadence: sched.cadence },
    });
    if (!wake.inserted && wake.reason !== 'duplicate') {
      results.push({ id: sched.id, inserted: false, reason: wake.reason, nextAt: sched.next_at });
      continue;
    }
    const oneShot = sched.cadence.startsWith('at:');
    const nextAt = oneShot ? sched.next_at : nextOccurrence(sched.cadence, sched.timezone, now);
    ctx.store.upsertSchedule({
      id: sched.id,
      conversationKey: sched.conversation_key,
      workId: sched.work_id,
      cadence: sched.cadence,
      timezone: sched.timezone,
      nextAt,
      enabled: !oneShot,
      note: sched.note,
      report: sched.report,
    });
    results.push({ id: sched.id, inserted: wake.inserted, reason: wake.reason, nextAt: oneShot ? null : nextAt });
  }
  emit(deps, flags, { now, results }, results.map((row) => `${row.id} ${row.reason}`).join('\n') + (results.length ? '\n' : 'none due\n'));
  return 0;
}

function cmdWork(rest, ctx, flags, deps) {
  const action = rest[0];
  if (!action || action === '--help') {
    emit(deps, flags, { help: 'work' }, HELP);
    return 0;
  }
  const { opts, positionals } = parseOpts(rest.slice(1));
  if (action === 'status') {
    const works = ctx.store.listWork({ conversationKey: opts.conversation || null });
    const hold = ctx.store.agentHold();
    emit(deps, flags, { agentHold: hold, works }, `agentHold=${hold ? 'yes' : 'no'}\n${works.map((row) => `${row.id} ${row.state} ${row.conversation_key}`).join('\n')}${works.length ? '\n' : ''}`);
    return 0;
  }
  if (action === 'retry' || action === 'resume') {
    const id = positionals[0];
    if (!id) {
      if (!ctx.store.clearHold({})) fail('no agent hold');
      emit(deps, flags, { cleared: 'agent' }, 'cleared agent hold\n');
      return 0;
    }
    if (!ctx.store.clearHold({ workId: id })) fail(`work ${id} is not held`);
    emit(deps, flags, { cleared: id }, `cleared ${id}\n`);
    return 0;
  }
  if (action === 'stop') {
    const id = positionals[0];
    if (!id) fail('work stop requires an id');
    const work = ctx.store.stopWork(id);
    emit(deps, flags, { work }, `stopped ${work.id}\n`);
    return 0;
  }
  fail('work requires status, retry, resume, or stop');
}

function cmdWake(rest, ctx, flags, deps) {
  const { opts } = parseOpts(rest);
  if (!opts.conversation) fail('wake requires --conversation');
  if (!opts.note) fail('wake requires --note');
  const result = ctx.store.wake({ conversationKey: opts.conversation, workId: opts.work || null, note: opts.note });
  emit(deps, flags, result, `${result.reason}\n`);
  return 0;
}

function agentChannel(config, slug) {
  if (!config) fail('post requires workspace config');
  const channels = Object.entries(config.routes).filter(([, agent]) => agent === slug).map(([id]) => id);
  if (channels.length > 1) fail(`agent ${slug} has more than one channel route`);
  if (channels.length === 1) return { channel: channels[0], imUser: null };
  if (config.dmAgent === slug) return { channel: config.slack.ownerUserId, imUser: config.slack.ownerUserId };
  fail(`no channel route for agent ${slug}`);
}

function cmdPost(rest, ctx, flags, deps) {
  const { opts } = parseOpts(rest);
  let text = opts.text || '';
  if (opts['text-file']) text = fs.readFileSync(opts['text-file'], 'utf8');
  const files = opts.file || [];
  if (!text && !files.length) fail('post requires --text, --text-file, or --file');
  const target = agentChannel(ctx.config, ctx.slug);
  const payload = { text, audio: Boolean(opts.audio), files };
  if (target.imUser) payload.imUser = target.imUser;
  const result = ctx.store.beginProactive({
    id: randomUUID(),
    agent: ctx.slug,
    workspace: ctx.config.slack.team,
    channel: target.channel,
    payload,
  });
  emit(deps, flags, { ...result, channel: target.channel }, `${result.conversationKey} activated\n`);
  return 0;
}

function dispatch(command, rest, ctx, flags, deps) {
  if (command === 'settings') return cmdSettings(rest, ctx, flags, deps);
  if (command === 'schedule') return cmdSchedule(rest, ctx, flags, deps);
  if (command === 'schedules-due') return cmdDue(rest, ctx, flags, deps);
  if (command === 'work') return cmdWork(rest, ctx, flags, deps);
  if (command === 'wake') return cmdWake(rest, ctx, flags, deps);
  if (command === 'post') return cmdPost(rest, ctx, flags, deps);
  fail(`unknown command: ${command}`);
}

function main(argv, deps = {}) {
  const { flags, rest } = parseGlobal(argv);
  if (flags.help && rest.length === 0) {
    emit(deps, { json: false }, { help: COMMANDS }, HELP);
    return 0;
  }
  if (rest.length === 0) fail(`usage: ignite-agent ${['install', 'update', 'connect', 'disconnect', ...COMMANDS].join('|')}`);
  const [command, ...tail] = rest;
  if (command === 'install' || command === 'update') return require('./install.js').run(command, tail, flags, deps);
  if (command === 'connect' || command === 'disconnect') return require('./connect.js').run(command, tail, flags, deps);
  if (!COMMANDS.includes(command)) fail(`unknown command: ${command}`);
  const ctx = openContext(flags, deps);
  try {
    return dispatch(command, tail, ctx, flags, deps);
  } finally {
    ctx.store.close();
  }
}

if (require.main === module) {
  Promise.resolve()
    .then(() => main(process.argv.slice(2)))
    .then((code) => process.exit(code ?? 0))
    .catch((error) => {
      process.stderr.write(`${error.message}\n`);
      process.exit(error.exitCode || 1);
    });
}

module.exports = { main, validateLaunch, applySetting, HELP };
