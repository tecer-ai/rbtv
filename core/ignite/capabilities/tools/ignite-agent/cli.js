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
const { writeBoard, closeSubject, migrateBoard, refreshBoard } = require('./board.js');
const { workspaceFromHome, remember } = require('./memory.js');

const APPLIES = 'applies from the next turn in every conversation';
const COMMANDS = ['settings', 'schedule', 'schedules-due', 'work', 'wake', 'post', 'board', 'remember'];
const REPORTS = new Set(['always', 'when-useful']);

const HELP = `ignite-agent — install update connect disconnect settings schedule schedules-due work wake post board remember

install <agent file> --harness <name> --model <cast short name> --effort <rung or 1-5> [--workspace <path>] [--dry-run]
  Runs rbtv install agent add, then installs Ignite's standard units. No Slack.
  Refuses when the agent is already installed; use update.
update <agent> [--workspace <path>] [--dry-run]
  Runs rbtv install agent update, then re-installs Ignite's standard units and removes
  any it installed earlier that are no longer standard units.
  Keeps launch.json, settings.json, _artifacts/board.md, the database, and conversations.
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

schedule add (--at <ISO datetime with offset> | --cron "<5-field>" --tz <IANA zone> | --every <duration>) --note <text> [--subject <title>] [--report always|when-useful] [--conversation <key>]
schedule list
schedule change <id> [same cadence flags] [--note <text>] [--report always|when-useful] [--enabled true|false]
schedule cancel <id>
  Cron requires an explicit --tz. Next occurrence is timezone-aware.
  --every is a fixed-interval: elapsed time, no timezone, DST does not move it.
  A recurring schedule requires a cadence (--cron or --every). An empty cadence is refused.
  Timers on _artifacts/board.md show enabled schedules with a next fire and pending/running wakes.
  --subject links the timer to a board subject; omitted means none. Changes keep this association.

schedules-due --now <ISO datetime>
  Enqueue a fresh conversation with no thread or resumed session; input is the schedule id only.
  While one schedule wake is pending, further dues are de-duplicated. Never enqueues for a held or stopped item, and never clears a hold.

work status [--conversation <key>]
work retry|resume [<id>]
  With an id, clears only that work hold. With no id, clears only an agent hold.
work stop <id>
  Stops that assignment. Does not cancel schedules and does not clear an agent hold.

wake --conversation <key> --note <text> [--work <id>]
  Worker completion. Enqueues a continuation. Does not clear a hold.

post (--text <text> | --text-file <path> | --file <path>)... [--audio] [--thread <thread>]
  Without --thread, opens a new thread in the agent's channel (the DM agent uses the owner's user id as the IM target).
  --thread selects an existing conversation in this agent's stored history: its full
  team:channel:root-ts key or a unique root timestamp. Unknown or ambiguous targets are refused.
  The post joins that conversation's history after delivery; its session and prior history stay intact.
  Enqueues delivery and activates the target. Prints "<conversation key> activated";
  --json returns conversationKey, outboxId, clientMsgId, activated and channel. Exit 0 means queued;
  errors go to stderr with exit 1. No Slack request or interactive prompt in this command.
  Example: ignite-agent post --thread T1:C1:123.456 --text "Check complete"

board write --file <path>
board close <subject> <outcome> [thread]
  Checked board edits and closures. See ignite-agent board --help for the form and caps.

remember <text>
  Atomically append one owner fact to the installation's .rbtv/memory/inbox.md.
  Never refuses for format or length; alerts the owner past 20 lines.
  See ignite-agent remember --help for provenance and output.
`;

const REMEMBER_HELP = `ignite-agent remember — save an owner fact for every agent

remember <text>
  Quote the text, or pass several words. Newlines become spaces: one append,
  one line, with today's UTC date, agent slug and current thread when available.
  Creates .rbtv/memory/inbox.md if missing. Never rejects text because of its
  length or existing inbox contents; never rewrites earlier lines or learned.md.
  Above 20 lines (including headings and blanks), queues an owner alert through the outbox.
  No Slack request or interactive prompt. Missing alert configuration does not
  undo the append; the result warns that the owner alert could not be queued.

Home: IGNITE_AGENT_HOME, otherwise --agent <slug> --workspace <path>.
Workspace: explicit --workspace, otherwise the installation containing the home.
IGNITE_CONVERSATION supplies thread provenance and the alert target inside a turn.
Outside a turn, alerts use this agent's configured channel or owner DM.
--help/-h needs no home. Use -- before literal option-like text.
Success: exit 0, "remembered in <path>", then any warning.
--json: {path, appended, lines, warning}; lines counts file lines, warning is null
when none. Failure: exit 1, reason on stderr, or {path, error} on stdout with
--json. A missing text argument, installation root or filesystem write can fail.

Example: ignite-agent remember "Prefers afternoon appointments"
`;

const BOARD_HELP = `ignite-agent board — checked short-term memory

board write --file <path>
  Read a complete UTF-8 Markdown candidate; create or update <home>/_artifacts/board.md.
  Keep all four headings in order: ## What matters now, ## Watch-outs,
  ## Timers, ## Recently closed. Empty sections keep their headings.
  Each subject: a unique ### Title, 1–3 state lines, then these three lines:
    - Threads: none OR [label](https://example.com/thread) links separated by " · "
    - Detail: none OR a Markdown page path/link (agent detail: ../memory/<slug>.md)
    - Flags: none OR answered YYYY-MM-DD OR idle since YYYY-MM-DD
  Watch-outs: - Rule (YYYY-MM-DD · agent[/[label](URL)])
  Temporary facts end with until YYYY-MM-DD, before any provenance tail.
  Only subjects and watch-outs may change. Keep Timers, Recently closed and
  existing Flags unchanged; new Flags must be none. Remove subjects with close.
  Caps: 90 non-empty lines excluding the Timers table; 8 subjects, 6 watch-outs,
  6 closed entries. Invalid or over-cap writes are refused, never truncated.

board close <subject> <outcome> [thread]
  Use the exact title; quote arguments containing spaces. Outcome is one line.
  Optional thread is a "[label](URL)" link. Removes the subject and appends its
  outcome with today's UTC date and agent slug to Recently closed.
  A full closed section refuses the whole change; archive old entries first.
  Nothing is pruned automatically.

Home: IGNITE_AGENT_HOME, otherwise --agent <slug> --workspace <path>.
Workspace may be discovered by walking up to .rbtv/config/ignite/config.json.
No Slack or database access. --help/-h works without a home. -- ends options.
Success: exit 0, "written <path>", "unchanged <path>" or "closed <subject> in <path>".
Failure: exit 1, reason on stderr; fix the candidate and retry. Validation leaves
the board unchanged. --json emits {path, changed, subject?} or {path, error} on
stdout; path is null if home resolution failed. No interactive prompts.

Examples:
  ignite-agent board write --file "board candidate.md"
  ignite-agent board close "Printer toner reorder" "Order confirmed"
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
    if (arg === '--') { rest.push(...argv.slice(i)); break; }
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
    if (arg === '--') { positionals.push(...argv.slice(i + 1)); break; }
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
    if (opts.subject != null && (!opts.subject.trim() || /[\r\n]/.test(opts.subject))) fail('--subject requires a non-empty one-line title');
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
      subject: opts.subject?.trim() ?? null,
    });
    refreshBoard(ctx.home, ctx.store, now);
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
      subject: existing.subject,
    });
    refreshBoard(ctx.home, ctx.store, now);
    emit(deps, flags, { schedule: row }, `${row.id} ${row.cadence} ${row.timezone} next=${row.next_at}\n`);
    return 0;
  }
  if (action === 'cancel') {
    const { positionals } = parseOpts(rest.slice(1));
    const id = positionals[0];
    if (!id) fail('schedule cancel requires an id');
    if (!ctx.store.deleteSchedule(id)) fail(`unknown schedule: ${id}`);
    refreshBoard(ctx.home, ctx.store, deps.now ? deps.now() : Date.now());
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
      subject: sched.subject,
    });
    results.push({ id: sched.id, inserted: wake.inserted, reason: wake.reason, nextAt: oneShot ? null : nextAt });
  }
  refreshBoard(ctx.home, ctx.store, now);
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
  const payload = { text, audio: Boolean(opts.audio), files };
  if (opts.thread != null) {
    if (!ctx.config) fail('post requires workspace config');
    const matches = ctx.store.db.prepare(`SELECT * FROM conversations
      WHERE agent=? AND workspace=? AND (key=? OR root_ts=?)
      AND root_ts IS NOT NULL AND root_ts!='board'`).all(ctx.slug, ctx.config.slack.team, opts.thread, opts.thread);
    if (!matches.length) fail(`unknown thread: ${opts.thread}; use an existing conversation key from this agent's history`);
    if (matches.length > 1) fail(`ambiguous thread: ${opts.thread}; use a full conversation key: ${matches.map((row) => row.key).join(', ')}`);
    const conv = matches[0];
    const outboxId = `post:${randomUUID()}`;
    ctx.store.transaction(() => {
      ctx.store.activateConversation(conv.key);
      ctx.store.enqueueOutbox({ id: outboxId, conversationKey: conv.key, payload });
    });
    emit(deps, flags, {
      conversationKey: conv.key, outboxId, clientMsgId: outboxId, activated: true, channel: conv.channel,
    }, `${conv.key} activated\n`);
    return 0;
  }
  const target = agentChannel(ctx.config, ctx.slug);
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

function cmdBoard(rest, flags, deps) {
  if (flags.help || !rest.length) {
    emit(deps, { json: false }, null, BOARD_HELP);
    return 0;
  }
  let file = null;
  try {
    const [action, ...tail] = rest;
    if (!['write', 'close'].includes(action)) fail('board requires write or close; see ignite-agent board --help');
    const { opts, positionals } = parseOpts(tail);
    if (Object.keys(opts).some((key) => action !== 'write' || key !== 'file')) fail('unsupported board option; see ignite-agent board --help');
    if (action === 'write' && (opts.file?.length !== 1 || positionals.length)) fail('board write requires exactly one --file <path>');
    if (action === 'close' && (positionals.length < 2 || positionals.length > 3)) fail('board close requires <subject> <outcome> [thread]');
    const { home, slug } = resolveHome(flags, deps);
    file = migrateBoard(home);
    const result = action === 'write'
      ? writeBoard(file, fs.readFileSync(opts.file[0], 'utf8'))
      : closeSubject(file, positionals[0], positionals[1], {
        agent: slug, thread: positionals[2] ?? null, now: deps.now ? deps.now() : Date.now(),
      });
    emit(deps, flags, result, action === 'close'
      ? `closed ${result.subject} in ${file}\n`
      : `${result.changed ? 'written' : 'unchanged'} ${file}\n`);
    return 0;
  } catch (error) {
    if (flags.json) emit(deps, flags, { path: file, error: error.message }, '');
    else (deps.stderr || ((text) => process.stderr.write(text)))(`${error.message}\n`);
    return 1;
  }
}

function cmdRemember(rest, flags, deps) {
  if (flags.help) {
    emit(deps, { json: false }, null, REMEMBER_HELP);
    return 0;
  }
  let file = null;
  try {
    const { opts, positionals } = parseOpts(rest);
    if (Object.keys(opts).length || !positionals.length) fail('remember requires <text>; use -- before option-like text');
    const { home, slug, workspace } = resolveHome(flags, deps);
    if (!workspace) fail('remember requires an installation root; use --workspace <path>');
    file = path.join(workspace, '.rbtv', 'memory', 'inbox.md');
    const env = deps.env || process.env;
    const key = env.IGNITE_CONVERSATION;
    const match = key?.match(/^[^:]+:([A-Z0-9]+):(\d+\.\d+)$/);
    const thread = match ? `[thread](https://app.slack.com/archives/${match[1]}/p${match[2].replace('.', '')})` : null;
    const result = remember(workspace, positionals.join(' '), { agent: slug, thread, now: deps.now ? deps.now() : Date.now() });
    // Append first. Missing config, a broken database or unavailable delivery
    // must never discard a remembered fact or make callers retry the append.
    if (result.warning) {
      let store;
      try {
        store = new Store(path.join(home, 'state.sqlite'));
        const payload = { text: result.warning, audio: false, files: [] };
        if (key && store.getConversation(key)) {
          store.enqueueOutbox({ id: `memory:${randomUUID()}`, conversationKey: key, payload });
        } else {
          const config = loadConfig(workspace);
          const target = agentChannel(config, slug);
          if (target.imUser) payload.imUser = target.imUser;
          store.beginProactive({ id: randomUUID(), agent: slug, workspace: config.slack.team, channel: target.channel, payload });
        }
      } catch { result.warning += ' Owner alert could not be queued; tell the owner.'; }
      finally {
        if (store) {
          try { store.close(); } catch { /* The fact is already appended. */ }
        }
      }
    }
    emit(deps, flags, result, `remembered in ${file}\n${result.warning ? `${result.warning}\n` : ''}`);
    return 0;
  } catch (error) {
    if (flags.json) emit(deps, flags, { path: file, error: error.message }, '');
    else (deps.stderr || ((text) => process.stderr.write(text)))(`${error.message}\n`);
    return 1;
  }
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
  if (command === 'board') return cmdBoard(tail, flags, deps);
  if (command === 'remember') return cmdRemember(tail, flags, deps);
  if (!COMMANDS.includes(command)) fail(`unknown command: ${command}`);
  if (flags.help && command === 'post') {
    emit(deps, { json: false }, null, HELP);
    return 0;
  }
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
