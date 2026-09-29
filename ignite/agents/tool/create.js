'use strict';

// API — ignite-agent create. run(argv, flags, deps) → Promise<exit code>.
// flags.workspace / flags.json come from cli.js parseGlobal. deps.slack stubs Slack.
// deps.install(ids, home, args) stubs `rbtv install add`. deps.resolveSkill stubs `rbtv install show`.
// deps.afterChannel() runs after the channel id is saved and before the route write.
// Effort is stored as the rung word validateLaunch returns, never a number string.
// Skill installs use canonical part keys (`module/component#part`), never --write-path.
// Skill ids resolve through the installer's public show command (repo + workspace mirror).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const { loadConfig, agentHome } = require('./config.js');
const { Slack } = require('./slack.js');
const { Store, conversationKey } = require('./store.js');
const { cadenceSpec, nextOccurrence, FIXED_TZ } = require('./schedule.js');
const { validateLaunch, applySetting } = require('./cli.js');

const SLUG = /^[a-z0-9][a-z0-9-]{0,63}$/;
const CHANNEL = /^[a-z0-9][a-z0-9_-]{0,79}$/;
const INSTALLER = path.resolve(__dirname, '../../../meta/installer');
const INSTALLER_ENTRY = path.join(INSTALLER, 'install.py');
const BOARD_ROOT = 'board';

const HELP = `ignite-agent create — create or remove a primary-agent home

create --workspace <path> --slug <slug> --purpose-file <file>
       [--reference <path>]... [--skill <id>]...
       [--harness <name> --model <cast short name> --effort <rung>]
       [--voice <id>]
       (--channel-name <name> | --dm)
       [--schedule-json <file>] [--settings-file <file>] [--dry-run] [--json]

  Validates first: slug free or resumable, launch setting through cast,
  reference paths exist, skill ids resolve, channel name legal.
  Default launch is config.defaultLaunch. A passed effort number is stored
  as the rung word cast returns, never as the number.
  Home: CLAUDE.md and AGENTS.md (one body), launch.json, board.md,
  settings.json, state.sqlite, conversations/.
  settings.json is {} unless --settings-file is passed. The file must be JSON.
  A re-run keeps an existing settings.json. Pass --settings-file again to replace it.
  Slack (omit with --dm): create the channel, bot joins, owner is invited,
  routes[channelId] = slug written atomically. Re-running the same slug
  reuses a channel id already saved or already routed.
  Skills: template defaults plus --skill; short names or module/component#part,
  installed with --guidance none and no path links.
  Schedule: only when --schedule-json has an explicit cadence and timezone.
  --dry-run validates and prints the plan, including the instruction diff. It writes nothing.
  Re-running the same slug rewrites CLAUDE.md and AGENTS.md from the current
  standing-instructions template when that text differs, and keeps the Purpose
  section already in the home. --purpose-file is required only when that
  section is not there yet.

  --schedule-json object, exactly one of cron, every, at:
    { "cron": "<5-field>", "tz": "<IANA zone>", "note": "<check>", "report": "always|when-useful" }
    { "every": "<duration>", "tz": "fixed", "note": "<check>" }
    { "at": "<ISO datetime with offset>", "note": "<check>" }
  report defaults to when-useful. A missing cadence or timezone is refused.

create --remove --workspace <path> --slug <slug> [--archive-channel] [--dry-run]
  Removes the route, archives the channel when asked, and moves the home to
  .rbtv/agents/.removed/<slug>-<timestamp>/. History is moved, never deleted.
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

function parseCreate(argv) {
  const opts = { reference: [], skill: [], dm: false, dryRun: false, remove: false, archiveChannel: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--dm') opts.dm = true;
    else if (arg === '--dry-run') opts.dryRun = true;
    else if (arg === '--remove') opts.remove = true;
    else if (arg === '--archive-channel') opts.archiveChannel = true;
    else if (arg === '--reference') opts.reference.push(take(argv, i, arg)), i += 1;
    else if (arg === '--skill') opts.skill.push(take(argv, i, arg)), i += 1;
    else if (arg.startsWith('--')) {
      const key = arg.slice(2);
      if (opts[key] != null) fail(`duplicate flag --${key}`);
      opts[key] = take(argv, i, arg);
      i += 1;
    } else fail(`unexpected argument: ${arg}`);
  }
  return opts;
}

function emit(deps, flags, payload, human) {
  const write = deps.stdout || ((text) => process.stdout.write(text));
  write(flags.json ? `${JSON.stringify(payload)}\n` : human);
}

function readJson(file, label) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    fail(`cannot read ${label}: ${error.message}`);
  }
}

function atomicJson(file, body) {
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(body, null, 2)}\n`);
  fs.renameSync(tmp, file);
}

function writeRoutes(workspace, mutate) {
  const file = path.join(workspace, '.rbtv', 'agents', 'ignite.json');
  const backup = fs.readFileSync(file);
  const raw = JSON.parse(backup.toString('utf8'));
  mutate(raw);
  atomicJson(file, raw);
  try {
    return loadConfig(workspace);
  } catch (error) {
    fs.writeFileSync(file, backup);
    throw error;
  }
}

function defaultSkills() {
  const file = path.join(__dirname, '../templates', 'skills.txt');
  return fs.readFileSync(file, 'utf8').split('\n').map((line) => line.trim()).filter((line) => line && !line.startsWith('#'));
}

function installerCommand(args) {
  const python = process.platform === 'win32' ? 'python' : 'python3';
  return spawnSync(python, [INSTALLER_ENTRY, ...args], { encoding: 'utf8' });
}

function resolveSkill(id, deps, workspace) {
  if (deps.resolveSkill) return deps.resolveSkill(id, workspace);
  const res = installerCommand(['show', id, '--kind', 'skill', '--json', '--target', workspace]);
  if (res.error) fail(`installer resolver failed: ${res.error.message}`);
  let body;
  try {
    body = JSON.parse(res.stdout);
  } catch {
    fail(`installer resolver did not return JSON: ${(res.stderr || res.stdout || 'empty result').trim()}`);
  }
  if (res.status !== 0 || !body.ok) fail(`unknown skill: ${id}: ${body.refusal?.message || 'resolution failed'}`);
  const selection = body.selection;
  if (selection?.kind !== 'part' || selection.method !== 'skill' || typeof selection.id !== 'string') {
    fail(`skill name must select one skill part: ${id}`);
  }
  return selection.id;
}

function launchFrom(config, opts, deps) {
  const base = config.defaultLaunch;
  const requested = {
    harness: opts.harness || base.harness,
    model: opts.model || base.model,
    effort: opts.effort || base.effort,
    voice: opts.voice !== undefined ? opts.voice : (base.voice || null),
  };
  if ((opts.harness || opts.model || opts.effort) && !(opts.harness && opts.model && opts.effort)) {
    fail('--harness, --model, and --effort are set together');
  }
  const setting = deps.validateLaunch
    ? deps.validateLaunch(requested)
    : validateLaunch(config.tools.cast, requested);
  if (setting.voice === undefined) setting.voice = requested.voice ?? null;
  if (/^[1-5]$/.test(String(setting.effort))) fail('effort must be stored as a rung word, not a number');
  return setting;
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
    tz: body.tz || undefined,
  });
  const nextAt = spec.nextAt != null ? spec.nextAt : nextOccurrence(spec.cadence, spec.timezone, now);
  return { ...spec, nextAt, note: String(body.note).trim(), report };
}

function setupPath(home) {
  return path.join(home, 'setup.json');
}

function readSetup(home) {
  const file = setupPath(home);
  if (!fs.existsSync(file)) return null;
  return readJson(file, 'setup.json');
}

function writeSetup(home, setup) {
  atomicJson(setupPath(home), setup);
}

function routeFor(config, slug) {
  return Object.entries(config.routes).filter(([, agent]) => agent === slug);
}

const PURPOSE_MARK = '\n## Purpose\n';

function standingNow() {
  return fs.readFileSync(path.join(__dirname, '../templates', 'standing-instructions.md'), 'utf8').trim();
}

function renderBody(purpose, references, skills) {
  const refs = references.length ? references.map((item) => `- ${item}`).join('\n') : 'None.';
  const listed = skills.map((id) => `- ${id}`).join('\n');
  return `${standingNow()}\n\n## Purpose\n\n${purpose.trim()}\n\n## Reference paths\n\n${refs}\n\n## Skills\n\n${listed}\n`;
}

function agentTail(text) {
  const at = text.indexOf(PURPOSE_MARK);
  if (at < 0) return null;
  const tail = text.slice(at + 1);
  return tail.endsWith('\n') ? tail : `${tail}\n`;
}

function readInstruction(home, name) {
  const file = path.join(home, name);
  if (!fs.existsSync(file)) return null;
  return fs.readFileSync(file, 'utf8');
}

function instructionPlan(home, freshBody) {
  const current = {
    'CLAUDE.md': readInstruction(home, 'CLAUDE.md'),
    'AGENTS.md': readInstruction(home, 'AGENTS.md'),
  };
  const tails = {};
  for (const name of Object.keys(current)) {
    if (current[name] == null) continue;
    tails[name] = agentTail(current[name]);
    if (!tails[name]) fail(`${name} has no Purpose section; refusing to overwrite per-agent text`);
  }
  const present = Object.values(tails);
  if (present.length === 2 && present[0] !== present[1]) {
    fail('CLAUDE.md and AGENTS.md Purpose sections differ; refusing to pick one');
  }
  if (!present.length) return { body: freshBody, current };
  return { body: `${standingNow()}\n\n${present[0]}`, current };
}

function unified(name, before, after) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-instr-'));
  try {
    const left = path.join(dir, 'current');
    const right = path.join(dir, 'next');
    fs.writeFileSync(left, before);
    fs.writeFileSync(right, after);
    const res = spawnSync('git', ['diff', '--no-index', '--', left, right], { encoding: 'utf8' });
    if (res.status === 0) return '';
    if (res.status === 1) {
      const output = res.stdout.replaceAll(left, name).replaceAll(right, `${name} (template)`);
      return output.endsWith('\n') ? output : `${output}\n`;
    }
    fail(`diff failed: ${(res.stderr || res.error?.message || 'unknown').trim()}`);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function instructionReport(plan) {
  const claude = plan.current['CLAUDE.md'];
  const agents = plan.current['AGENTS.md'];
  if (claude === plan.body && agents === plan.body) return 'instructions: unchanged\n';
  const lines = [];
  if (claude !== plan.body) lines.push(unified('CLAUDE.md', claude ?? '', plan.body));
  else lines.push('CLAUDE.md: unchanged\n');
  if (agents !== plan.body) {
    if ((agents ?? '') === (claude ?? '')) lines.push('AGENTS.md: same change as CLAUDE.md\n');
    else lines.push(unified('AGENTS.md', agents ?? '', plan.body));
  } else lines.push('AGENTS.md: unchanged\n');
  return lines.join('');
}

function settingsSeed(file) {
  let raw;
  try {
    raw = fs.readFileSync(file, 'utf8');
  } catch (error) {
    fail(`cannot read --settings-file: ${error.message}`);
  }
  try {
    return JSON.parse(raw);
  } catch (error) {
    fail(`--settings-file is not JSON: ${error.message}`);
  }
}

function settingsPlan(home, seed) {
  const exists = fs.existsSync(path.join(home, 'settings.json'));
  if (seed === undefined) {
    return { action: exists ? 'kept' : 'empty', text: exists ? 'settings: kept' : 'settings: {}' };
  }
  return { action: 'seed', body: `${JSON.stringify(seed, null, 2)}\n`, text: `settings: ${JSON.stringify(seed)}` };
}

function writeSettings(home, plan) {
  if (plan.action === 'kept') return;
  fs.writeFileSync(path.join(home, 'settings.json'), plan.action === 'empty' ? '{}\n' : plan.body);
}

function writeInstructions(home, body) {
  const claude = path.join(home, 'CLAUDE.md');
  const agents = path.join(home, 'AGENTS.md');
  const same = fs.existsSync(claude) && fs.existsSync(agents)
    && fs.readFileSync(claude, 'utf8') === body
    && fs.readFileSync(agents, 'utf8') === body;
  if (same) return false;
  fs.writeFileSync(claude, body);
  fs.writeFileSync(agents, body);
  return true;
}

function writeBoard(home, schedule) {
  const file = path.join(home, 'board.md');
  if (!fs.existsSync(file)) {
    fs.copyFileSync(path.join(__dirname, '../templates', 'board.md.tmpl'), file);
  }
  if (!schedule) return;
  const text = fs.readFileSync(file, 'utf8');
  const block = [
    '## Recurring checks',
    '',
    `- cadence: ${schedule.cadence}`,
    `- timezone: ${schedule.timezone}`,
    `- check: ${schedule.note}`,
    `- report: ${schedule.report}`,
    '',
  ].join('\n');
  const next = text.replace(/## Recurring checks\r?\n\r?\n[\s\S]*?\r?\n\r?\n## Open work/, `${block}\n## Open work`);
  if (next === text) fail('board template has no recurring-checks section');
  fs.writeFileSync(file, next);
}

function botToken(file) {
  const data = readJson(file, 'slack bot token file');
  if (!data.bot_token || typeof data.bot_token !== 'string') fail('bot token file has no bot_token');
  return data.bot_token;
}

function slackClient(config, deps) {
  if (deps.slack) return deps.slack;
  return new Slack({ botToken: botToken(config.slack.botTokenFile) });
}

async function installSkills(home, skills, deps) {
  const args = ['add', ...skills, '--target', home];
  if (!fs.existsSync(path.join(home, '.rbtv', 'config', 'install.json'))) {
    args.push('--harness', 'claude,codex,opencode', '--guidance', 'none');
  }
  try {
    if (deps.install) await deps.install(skills, home, args);
    else {
      const res = installerCommand(args);
      if (res.error) throw new Error(res.error.message);
      if (res.status !== 0) throw new Error((res.stderr || res.stdout || 'install failed').trim());
    }
    return [];
  } catch (error) {
    return [`${skills.join(', ')}: ${error.message}`];
  }
}

function loaderMissing(home, skills) {
  const missing = [];
  for (const id of skills) {
    const pid = id.slice(id.lastIndexOf('#') + 1);
    for (const rel of [path.join('.claude', 'skills', pid, 'SKILL.md'), path.join('.agents', 'skills', pid, 'SKILL.md')]) {
      if (!fs.existsSync(path.join(home, rel))) missing.push(rel);
    }
  }
  return missing;
}

function planText(plan) {
  const lines = [
    plan.dryRun ? 'dry-run' : 'create',
    `slug: ${plan.slug}`,
    `home: ${plan.home}`,
    `launch: ${plan.launch.harness} ${plan.launch.model} ${plan.launch.effort}${plan.launch.voice ? ` voice=${plan.launch.voice}` : ''}`,
    plan.dm ? 'channel: none (dm)' : `channel: ${plan.channelName}`,
    `skills: ${plan.skills.join(', ')}`,
    `references: ${plan.references.length ? plan.references.join(', ') : 'none'}`,
    `schedule: ${plan.schedule ? `${plan.schedule.cadence} ${plan.schedule.timezone}` : 'none'}`,
    plan.settings,
    'writes: none',
  ];
  return `${lines.join('\n')}\n`;
}

function validateCreate(opts, flags, deps) {
  const workspace = flags.workspace || opts.workspace;
  if (!workspace) fail('--workspace required');
  if (!opts.slug) fail('--slug required');
  if (!SLUG.test(opts.slug)) fail('slug must match [a-z0-9][a-z0-9-]{0,63}');
  const config = loadConfig(workspace);
  if (opts.dm && opts['channel-name']) fail('pass either --channel-name or --dm, not both');
  if (!opts.dm && !opts['channel-name']) fail('--channel-name or --dm required');
  if (opts['channel-name'] && !CHANNEL.test(opts['channel-name'])) {
    fail('channel name must be lowercase letters, numbers, hyphens, or underscores, at most 80 characters');
  }
  const home = agentHome(config, opts.slug);
  const kept = ['CLAUDE.md', 'AGENTS.md'].map((name) => readInstruction(home, name)).find((text) => text && agentTail(text));
  let purpose = '';
  if (opts['purpose-file']) {
    if (!fs.existsSync(opts['purpose-file'])) fail(`purpose file not found: ${opts['purpose-file']}`);
    purpose = fs.readFileSync(opts['purpose-file'], 'utf8');
    if (!purpose.trim()) fail('purpose file is empty');
  } else if (!kept) fail('--purpose-file required');
  const references = opts.reference.map((item) => {
    const abs = path.resolve(item);
    if (!fs.existsSync(abs)) fail(`reference path not found: ${item}`);
    return abs;
  });
  const skills = [...new Set([...defaultSkills(), ...opts.skill].map((id) => resolveSkill(id, deps, workspace)))];
  const launch = launchFrom(config, opts, deps);
  const now = deps.now ? deps.now() : Date.now();
  const schedule = opts['schedule-json'] ? scheduleFrom(opts['schedule-json'], now) : null;
  const settings = opts['settings-file'] ? settingsSeed(opts['settings-file']) : undefined;
  const routes = routeFor(config, opts.slug);
  if (routes.length > 1) fail(`agent ${opts.slug} has more than one channel route`);
  const setup = fs.existsSync(home) ? readSetup(home) : null;
  if (setup && Boolean(setup.dm) !== opts.dm) fail(`slug ${opts.slug} was started as ${setup.dm ? 'dm' : 'a channel agent'}`);
  if (routes.length === 1 && opts.dm) fail(`slug ${opts.slug} already has a channel route`);
  return { workspace, config, purpose, references, skills, launch, schedule, settings, home, routes, setup, now };
}

async function ensureChannel(ctx, slack, deps) {
  const { config, opts, home, setup, routes } = ctx;
  if (routes.length === 1) return { id: routes[0][0], name: setup?.channelName || opts['channel-name'], reused: true };
  if (setup?.channelId) return { id: setup.channelId, name: setup.channelName || opts['channel-name'], reused: true };
  const created = await slack.createChannel(opts['channel-name']);
  if (!created?.id) fail('createChannel returned no id');
  writeSetup(home, {
    slug: opts.slug, dm: false, channelId: created.id, channelName: created.name || opts['channel-name'], scheduleId: setup?.scheduleId || null,
  });
  if (deps.afterChannel) await deps.afterChannel({ channelId: created.id });
  return { id: created.id, name: created.name || opts['channel-name'], reused: false };
}

async function bindSchedule(ctx) {
  const { config, opts, home, schedule, channel } = ctx;
  if (!schedule) return null;
  const setup = readSetup(home) || { slug: opts.slug, dm: opts.dm };
  if (setup.scheduleId) {
    const store = new Store(path.join(home, 'state.sqlite'));
    try {
      if (store.getSchedule(setup.scheduleId)) return setup.scheduleId;
    } finally {
      store.close();
    }
  }
  const channelId = opts.dm ? config.slack.ownerUserId : channel.id;
  const key = conversationKey(config.slack.team, channelId, BOARD_ROOT);
  const store = new Store(path.join(home, 'state.sqlite'));
  try {
    store.upsertConversation({
      key, agent: opts.slug, workspace: config.slack.team, channel: channelId, rootTs: BOARD_ROOT, activated: false,
    });
    const id = setup.scheduleId || randomUUID();
    store.upsertSchedule({
      id,
      conversationKey: key,
      cadence: schedule.cadence,
      timezone: schedule.timezone,
      nextAt: schedule.nextAt,
      enabled: true,
      note: schedule.note,
      report: schedule.report,
    });
    writeSetup(home, { ...setup, slug: opts.slug, dm: opts.dm, scheduleId: id, channelId: channel?.id || setup.channelId || null, channelName: channel?.name || setup.channelName || null });
    writeBoard(home, schedule);
    return id;
  } finally {
    store.close();
  }
}

function selfCheck(ctx, extras) {
  const { home, opts, config, skills, channel } = ctx;
  const lines = ['self-check'];
  const required = ['CLAUDE.md', 'AGENTS.md', 'launch.json', 'board.md', 'settings.json', 'state.sqlite'];
  const missing = required.filter((name) => !fs.existsSync(path.join(home, name)));
  if (!fs.existsSync(path.join(home, 'conversations'))) missing.push('conversations/');
  lines.push(missing.length ? `home: missing ${missing.join(', ')}` : 'home: ok');
  let identical = false;
  if (!missing.includes('CLAUDE.md') && !missing.includes('AGENTS.md')) {
    identical = fs.readFileSync(path.join(home, 'CLAUDE.md'), 'utf8') === fs.readFileSync(path.join(home, 'AGENTS.md'), 'utf8');
  }
  lines.push(identical ? 'instructions: identical' : 'instructions: CLAUDE.md and AGENTS.md differ or are missing');
  const launch = fs.existsSync(path.join(home, 'launch.json')) ? readJson(path.join(home, 'launch.json'), 'launch.json') : null;
  lines.push(launch && launch.effort && !/^[1-5]$/.test(String(launch.effort)) ? 'launch: ok' : 'launch: missing or effort is a number');
  if (opts.dm) lines.push('route: none (dm)');
  else {
    const routed = loadConfig(ctx.workspace).routes[channel.id];
    lines.push(routed === opts.slug ? `route: ${channel.id} -> ${opts.slug}` : `route: missing for ${channel?.id || 'channel'}`);
    const members = extras.joined && extras.invited ? 'bot=joined owner=invited' : `bot=${extras.joined ? 'joined' : 'missing'} owner=${extras.invited ? 'invited' : 'missing'}`;
    lines.push(`channel: ${channel.id} ${members}`);
    if (extras.link) lines.push(`link: ${extras.link}`);
  }
  const loaders = loaderMissing(home, skills);
  lines.push(loaders.length ? `loaders: missing ${loaders.join(', ')}` : 'loaders: ok');
  if (extras.installErrors?.length) lines.push(`install: ${extras.installErrors.join('; ')}`);
  lines.push(`schedule: ${extras.scheduleId || 'none'}`);
  const ok = lines.every((line) => !line.includes('missing') && !line.includes('differ') && !line.startsWith('install:'));
  return { ok, text: `${lines.join('\n')}\n`, lines };
}

async function createAgent(opts, flags, deps) {
  const ctx = validateCreate(opts, flags, deps);
  ctx.opts = opts;
  const plan = {
    dryRun: true,
    slug: opts.slug,
    home: ctx.home,
    launch: ctx.launch,
    dm: opts.dm,
    channelName: opts['channel-name'] || null,
    skills: ctx.skills,
    references: ctx.references,
    schedule: ctx.schedule,
    settings: settingsPlan(ctx.home, ctx.settings).text,
  };
  const fresh = ctx.purpose ? renderBody(ctx.purpose, ctx.references, ctx.skills) : null;
  const instr = instructionPlan(ctx.home, fresh);
  if (opts.dryRun) {
    emit(deps, flags, { dryRun: true, ...plan, writes: 'none', instructions: instructionReport(instr) }, planText(plan) + instructionReport(instr));
    return 0;
  }
  fs.mkdirSync(ctx.home, { recursive: true });
  fs.mkdirSync(path.join(ctx.home, 'conversations'), { recursive: true });
  writeInstructions(ctx.home, instr.body);
  writeSettings(ctx.home, settingsPlan(ctx.home, ctx.settings));
  if (!fs.existsSync(path.join(ctx.home, 'board.md'))) writeBoard(ctx.home, null);
  const store = new Store(path.join(ctx.home, 'state.sqlite'));
  try {
    if (!fs.existsSync(path.join(ctx.home, 'launch.json')) || opts.harness) applySetting(store, ctx.home, ctx.launch);
  } finally {
    store.close();
  }
  let channel = null;
  let joined = false;
  let invited = false;
  if (!opts.dm) {
    const slack = slackClient(ctx.config, deps);
    channel = await ensureChannel(ctx, slack, deps);
    ctx.channel = channel;
    await slack.joinChannel(channel.id);
    joined = true;
    await slack.inviteUser(channel.id, ctx.config.slack.ownerUserId);
    invited = true;
    writeRoutes(ctx.workspace, (raw) => {
      const taken = raw.routes[channel.id];
      if (taken && taken !== opts.slug) fail(`channel ${channel.id} is already routed to ${taken}`);
      raw.routes[channel.id] = opts.slug;
    });
    const setup = readSetup(ctx.home) || {};
    writeSetup(ctx.home, { ...setup, slug: opts.slug, dm: false, channelId: channel.id, channelName: channel.name });
  } else {
    writeSetup(ctx.home, { ...(readSetup(ctx.home) || {}), slug: opts.slug, dm: true });
  }
  ctx.channel = channel;
  const installErrors = await installSkills(ctx.home, ctx.skills, deps);
  const scheduleId = await bindSchedule(ctx);
  const link = channel ? `https://slack.com/app_redirect?channel=${channel.id}&team=${ctx.config.slack.team}` : null;
  const check = selfCheck(ctx, { joined, invited, link, installErrors, scheduleId });
  emit(deps, flags, { ok: check.ok, slug: opts.slug, home: ctx.home, channel, link, scheduleId, check: check.lines }, check.text);
  return check.ok ? 0 : 1;
}

function removePlan(config, slug, archive) {
  const home = agentHome(config, slug);
  const routes = routeFor(config, slug);
  return {
    slug,
    home,
    routes: routes.map(([id]) => id),
    archive,
    exists: fs.existsSync(home),
  };
}

async function removeAgent(opts, flags, deps) {
  const workspace = flags.workspace || opts.workspace;
  if (!workspace) fail('--workspace required');
  if (!opts.slug) fail('--slug required');
  if (!SLUG.test(opts.slug)) fail('slug must match [a-z0-9][a-z0-9-]{0,63}');
  if (opts['purpose-file'] || opts['channel-name'] || opts.dm || opts.skill.length || opts.reference.length || opts['settings-file']) {
    fail('--remove accepts only --slug, --workspace, and --archive-channel');
  }
  const config = loadConfig(workspace);
  const plan = removePlan(config, opts.slug, opts.archiveChannel);
  if (opts.dryRun) {
    emit(deps, flags, { dryRun: true, remove: plan, writes: 'none' }, `dry-run remove ${opts.slug}\nhome: ${plan.home}\nroutes: ${plan.routes.join(', ') || 'none'}\narchive: ${opts.archiveChannel}\nwrites: none\n`);
    return 0;
  }
  const setup = plan.exists ? readSetup(plan.home) : null;
  const channelIds = [...new Set([...plan.routes, ...(setup?.channelId ? [setup.channelId] : [])])];
  if (opts.archiveChannel && channelIds.length) {
    const slack = slackClient(config, deps);
    for (const id of channelIds) await slack.archiveChannel(id);
  }
  writeRoutes(workspace, (raw) => {
    for (const id of Object.keys(raw.routes)) {
      if (raw.routes[id] === opts.slug) delete raw.routes[id];
    }
  });
  let moved = null;
  if (plan.exists) {
    const stamp = new Date(deps.now ? deps.now() : Date.now()).toISOString().replace(/[:.]/g, '');
    const dest = path.join(workspace, '.rbtv', 'agents', '.removed', `${opts.slug}-${stamp}`);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.renameSync(plan.home, dest);
    moved = dest;
  }
  emit(deps, flags, { removed: opts.slug, archived: opts.archiveChannel ? channelIds : [], moved }, `removed ${opts.slug}\narchived: ${opts.archiveChannel ? channelIds.join(', ') || 'none' : 'no'}\nmoved: ${moved || 'none'}\n`);
  return 0;
}

async function run(argv, flags, deps = {}) {
  if (flags.help) {
    emit(deps, { json: false }, { help: 'create' }, HELP);
    return 0;
  }
  const opts = parseCreate(argv);
  if (opts.remove) return removeAgent(opts, flags, deps);
  return createAgent(opts, flags, deps);
}

module.exports = { run, HELP };
