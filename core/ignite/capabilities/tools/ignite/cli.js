#!/usr/bin/env node
'use strict';

// API — entry `ignite`. Home from RBTV_AGENT_HOME, or --agent <slug> + --installation <path>.
// main(argv, deps) → exit code, or a Promise for connect/disconnect/dreamer/deploy.
// deps.slack stubs Slack.
// deps.stdout / deps.stderr / deps.env optional.
// schedule next-occurrence lives in schedule.js.
// connect and disconnect run before a home is opened. There is no create command.

const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const { Store } = require('./store.js');
const { loadConfig, updateConfig, agentHome, configPath, findWorkspace, DREAMER_MODEL, dreamerModelRequired } = require('./config.js');
const { cadenceSpec, nextOccurrence, FIXED_TZ } = require('./schedule.js');
const { writeBoard, closeSubject, boardPath, preflightBoard, refreshBoard, refreshBoardAfterCommit } = require('./board.js');
const { workspaceFromHome, remember } = require('./memory.js');
const { PAGES, helpPage } = require('./help.js');

const COMMANDS = ['schedule', 'schedules-due', 'work', 'wake', 'post', 'board', 'remember', 'dreamer'];
const REPORTS = new Set(['always', 'when-useful']);

// What each verb takes beside --json, --agent, --installation and -h: its options, and the most
// positional words. parseOpts refuses any other option and one word more.
const VERBS = {
  'schedule add': { options: ['at', 'cron', 'tz', 'every', 'note', 'subject', 'report', 'conversation'], words: 0 },
  'schedule list': { options: [], words: 0 },
  'schedule change': { options: ['at', 'cron', 'tz', 'every', 'note', 'report', 'enabled'], words: 1 },
  'schedule cancel': { options: [], words: 1 },
  'schedules-due': { options: ['now'], words: 0 },
  'work status': { options: ['conversation'], words: 0 },
  'work retry': { options: [], words: 1 },
  'work resume': { options: [], words: 1 },
  'work stop': { options: [], words: 1 },
  wake: { options: ['conversation', 'note', 'work'], words: 0 },
  post: { options: ['text', 'text-file', 'file', 'audio', 'thread'], words: 0 },
  'board write': { options: ['file'], words: 0 },
  'board close': { options: [], words: 3 },
  remember: { options: [], words: Infinity },
};

const HELP = `ignite — help

Connect an agent to Slack, run one turn, let the calling agent
manage itself, or deploy the waking service.

Connect
  connect        Turn the ignite pack on, create working files, connect Slack.
  disconnect     Remove the Slack route and turn the ignite pack off.

Manage and turn
  manage         The calling agent manages itself.
  turn           One turn with an exact session id. Writes a result file.
                 Prints nothing.

Timers, work, messages and memory
  schedule       Add, list, change, or cancel a timer.
  schedules-due  Enqueue a due timer as a fresh conversation.
  work           Show, retry, resume, or stop an assignment.
  wake           Enqueue a continuation when a worker finishes.
  post           Queue a Slack message in this agent's channel.
  board          Write or close a subject on the board.
  remember       Append one owner fact to the installation memory inbox.
  dreamer        Run one memory consolidation, or enable or disable the
                 nightly consolidation for the whole installation.

Waking service
  deploy         Check the service's folder out at a commit, restart the
                 service and confirm it is active. Linux only.

Home: RBTV_AGENT_HOME, or --agent NAME --installation PATH.
  The installation defaults to the directory walk that finds
  .rbtv/config/ignite/config.json.
  manage's four change verbs, and schedule, work, wake, post, board,
  remember, and dreamer, use that agent. Help needs neither value.
  Inside a turn the waking program also sets IGNITE_CONVERSATION.
  A home that is not an existing folder is refused, and nothing is created.

AGENT on connect and disconnect is a name under
<installation>/.rbtv/agents/, or a path to an agent folder there.

Shared options: --json  -h, --help
connect, disconnect and deploy also take --dry-run and --installation.
--json selects JSON on stdout for a success.
A refusal is a message on stderr, exit 1, with or without --json.
An option whose value is empty or only spaces is refused.
-h and --help work before or after the verb, with no setup.

Start: ignite connect -h
More:  ignite COMMAND -h
Exit codes: 0 success; 1 refused, failed, or invalid arguments.
`;
const TURN_HELP = `ignite — turn help

usage: ignite turn --request FILE --result FILE

One foreground turn for a caller that keeps many conversations in one folder.
Never resolves \`last\` and never picks the newest session in the folder.
Resume passes the requested model and effort on that invocation.
The waking program calls this. A person may run it by hand.
This command prints nothing. The result file is the structured value.
It does not take --json.

Request JSON:
  harness          claude | codex | opencode
  model            short name or harness-native id
  effort           integer 1-5, or a native rung word
  cwd              existing absolute directory
  prompt|promptFile  exactly one
  session          {"mode":"new"} or {"mode":"resume","id":"<exact id>"}
  env              optional string map merged over the process environment
  fallbacks        optional list of {harness, model, effort, session, prompt}: the turns
                   to run in this order, each in place of the one before, while a harness
                   fails to start

Result JSON (written even on failure):
  ok, harness, model, effort, sessionId, exitCode,
  startedAt, endedAt, pid, pidStart, stdoutPath, stderrPath, error?, failed?, exhausted?
A harness fails to start when it cannot be started or exits with a failure in its
first 15 seconds. The result describes the last run. A request with fallbacks gets
failed, the harness, model and error of each run before the last, each with end, how
that run ended (error when the harness could not be started, else code, signal and
elapsedMs), and exhausted, true when the last run failed to start as well with no
fallback left. The output of fallback N is in <result>.fallbackN.stdout and .stderr.
pid + pidStart (starttime from /proc/<pid>/stat, read while alive) distinguish a
live run from a reused pid. stdout/stderr are captured to files, not inherited.

Session id: claude mints a UUID and passes --session-id; codex parses thread.started
(thread_id); opencode binds a unique --title tag to that store row. Resume passes
--resume / exec resume <id> / run -s <id> plus the requested model and effort.

An invalid request is a message on stderr, exit 1. If the result path was
never resolved, no result file is written. If the turn fails after the path
is resolved, the result file is still written and this command exits 1.
The child exit code is exitCode in the file.

Example: ignite turn --request request.json --result result.json
Exit codes: 0 success; 1 refused, failed, or invalid arguments.
`;
const REMEMBER_HELP = `ignite remember — save an owner fact for every agent

remember <text>
  Quote the text, or pass several words. Newlines become spaces: one append,
  one line, with today's UTC date, agent slug and current thread when available.
  Empty or whitespace-only text fails before any files are written.
  Creates .rbtv/memory/inbox.md if missing. Never rejects text because of its
  length or existing inbox contents; never rewrites earlier lines or learned.md.
  Above 20 bullet lines, queues an owner alert through the outbox. Headings and blanks do not count.
  No Slack request or interactive prompt. Missing alert configuration does not
  undo the append; the result warns that the owner alert could not be queued.

Home: RBTV_AGENT_HOME, otherwise --agent <slug> --installation <path>. A home that is not an
existing folder is refused, and nothing is appended.
Installation: explicit --installation, otherwise the installation containing the home.
IGNITE_CONVERSATION supplies thread provenance and the alert target inside a turn.
Outside a turn, alerts use this agent's configured channel or owner DM.
--help/-h needs no home. An option is refused; use -- before literal option-like text.
Success: exit 0, "remembered in <path>", then any warning.
--json: {path, appended, lines, warning}; lines counts bullet lines, warning is null
when none. Failure: exit 1, reason on stderr, or {path, error} on stdout with
--json. Missing or empty text, a missing agent folder, an unresolved installation root or a
filesystem write can fail.

Example: ignite remember "Prefers afternoon appointments"
`;

function take(argv, i, flag, help = 'ignite -h') {
  const value = argv[i + 1];
  if (value == null || value.startsWith('--')) throw new Error(`${flag} requires a value`);
  if (!value.trim()) fail(`${flag} requires a value that is not empty or only spaces\nNothing changed.\n${help}`);
  return value;
}

function parseGlobal(argv) {
  const flags = { json: false, help: false, agent: null, installation: null };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--') { rest.push(...argv.slice(i)); break; }
    if (arg === '--json') flags.json = true;
    else if (arg === '--help' || arg === '-h') flags.help = true;
    else if (arg === '--agent') flags.agent = take(argv, i, arg), i += 1;
    else if (arg === '--installation') flags.installation = take(argv, i, arg), i += 1;
    else rest.push(arg);
  }
  return { flags, rest };
}

function parseOpts(argv, verb) {
  const opts = {};
  const positionals = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--') { positionals.push(...argv.slice(i + 1)); break; }
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      if (!VERBS[verb].options.includes(key)) fail(`'${arg}' is not a ${verb} option\nNothing changed.\nignite ${verb} -h`);
      if (key === 'audio') {
        opts.audio = true;
        continue;
      }
      const value = take(argv, i, arg, `ignite ${verb} -h`);
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
  const { words } = VERBS[verb];
  if (positionals.length > words) {
    const limit = words ? `at most ${words} positional word${words > 1 ? 's' : ''}` : 'no positional words';
    fail(`unexpected word '${positionals[words]}': ${verb} takes ${limit}\nNothing changed.\nignite ${verb} -h`);
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

function locateHome(flags, deps) {
  const env = deps.env || process.env;
  if (env.RBTV_AGENT_HOME) {
    const home = env.RBTV_AGENT_HOME;
    return { home, slug: flags.agent || path.basename(home), workspace: flags.installation || workspaceFromHome(home) };
  }
  if (!flags.agent) fail('--agent or RBTV_AGENT_HOME required');
  const workspace = flags.installation || findWorkspace(process.cwd());
  if (!workspace) fail('--installation required with --agent');
  const config = loadConfig(workspace);
  return { home: agentHome(config, flags.agent), slug: flags.agent, workspace, config };
}

// No verb creates the agent folder: a home that is not an existing folder is refused before anything is opened.
function resolveHome(flags, deps) {
  const located = locateHome(flags, deps);
  if (!fs.statSync(located.home, { throwIfNoEntry: false })?.isDirectory()) {
    fail(`agent folder not found: ${located.home}\nNothing changed.\nignite -h`);
  }
  return located;
}

function openContext(flags, deps, requireBoard = false) {
  const located = resolveHome(flags, deps);
  if (requireBoard) preflightBoard(located.home);
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

function addSpec(opts, fromMs) {
  const spec = cadenceSpec({ at: opts.at, cron: opts.cron, every: opts.every, tz: opts.tz });
  const nextAt = spec.nextAt != null ? spec.nextAt : nextOccurrence(spec.cadence, spec.timezone, fromMs);
  return { ...spec, nextAt };
}

function cmdSchedule(rest, ctx, flags, deps, parsed) {
  const action = rest[0];
  if (!action || action === '--help') {
    emit(deps, flags, { help: 'schedule' }, PAGES.schedule);
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
    const { opts } = parsed;
    const note = opts.note ?? fail('--note is required');
    if (/[\r\n]/.test(opts.subject ?? '')) fail('--subject requires a one-line title');
    const key = conversationOf(opts, deps);
    if (!ctx.store.getConversation(key)) fail(`unknown conversation: ${key}`);
    const now = deps.now ? deps.now() : Date.now();
    const spec = addSpec(opts, now);
    preflightBoard(ctx.home);
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
    const warning = refreshBoardAfterCommit(ctx.home, ctx.store, [row.id], now);
    emit(deps, flags, { schedule: row, ...(warning ? { warning } : {}) },
      `${row.id} ${row.cadence} ${row.timezone} next=${row.next_at}\n${warning ? `${warning}\n` : ''}`);
    return 0;
  }
  if (action === 'change') {
    const { opts, positionals } = parsed;
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
    preflightBoard(ctx.home);
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
    const warning = refreshBoardAfterCommit(ctx.home, ctx.store, [row.id], now);
    emit(deps, flags, { schedule: row, ...(warning ? { warning } : {}) },
      `${row.id} ${row.cadence} ${row.timezone} next=${row.next_at}\n${warning ? `${warning}\n` : ''}`);
    return 0;
  }
  if (action === 'cancel') {
    const id = parsed.positionals[0];
    if (!id) fail('schedule cancel requires an id');
    preflightBoard(ctx.home);
    if (!ctx.store.deleteSchedule(id)) fail(`unknown schedule: ${id}`);
    const warning = refreshBoardAfterCommit(ctx.home, ctx.store, [id], deps.now ? deps.now() : Date.now());
    emit(deps, flags, { cancelled: id, ...(warning ? { warning } : {}) }, `cancelled ${id}\n${warning ? `${warning}\n` : ''}`);
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

function cmdDue(ctx, flags, deps, { opts }) {
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

function cmdWork(rest, ctx, flags, deps, parsed) {
  const action = rest[0];
  if (!action || action === '--help') {
    emit(deps, flags, { help: 'work' }, PAGES.work);
    return 0;
  }
  if (!parsed) fail('work requires status, retry, resume, or stop');
  const { opts, positionals } = parsed;
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
  const id = positionals[0];
  if (!id) fail('work stop requires an id');
  const work = ctx.store.stopWork(id);
  emit(deps, flags, { work }, `stopped ${work.id}\n`);
  return 0;
}

function cmdWake(ctx, flags, deps, { opts }) {
  if (!opts.conversation) fail('wake requires --conversation');
  if (!opts.note) fail('wake requires --note');
  const result = ctx.store.wake({ conversationKey: opts.conversation, workId: opts.work || null, note: opts.note });
  emit(deps, flags, result, `${result.reason}\n`);
  return 0;
}

function agentChannel(config, slug) {
  if (!config) fail('post requires installation config');
  const channels = Object.entries(config.routes).filter(([, agent]) => agent === slug).map(([id]) => id);
  if (channels.length > 1) fail(`agent ${slug} has more than one channel route`);
  if (channels.length === 1) return { channel: channels[0], imUser: null };
  if (config.dmAgent === slug) return { channel: config.slack.ownerUserId, imUser: config.slack.ownerUserId };
  fail(`no channel route for agent ${slug}`);
}

function cmdPost(ctx, flags, deps, { opts }) {
  let text = opts.text || '';
  if (opts['text-file']) text = fs.readFileSync(opts['text-file'], 'utf8');
  const files = opts.file || [];
  if (!text && !files.length) fail('post requires --text, --text-file, or --file');
  const payload = { text, audio: Boolean(opts.audio), files };
  if (opts.thread != null) {
    if (!ctx.config) fail('post requires installation config');
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
  if (!rest.length) {
    emit(deps, { json: false }, null, PAGES.board);
    return 0;
  }
  let file = null;
  let store;
  try {
    const [action, ...tail] = rest;
    if (!['write', 'close'].includes(action)) fail('board requires write or close; see ignite board --help');
    const { opts, positionals } = parseOpts(tail, `board ${action}`);
    if (action === 'write' && opts.file?.length !== 1) fail('board write requires exactly one --file <path>');
    if (action === 'close' && positionals.length < 2) fail('board close requires <subject> <outcome> [thread]');
    const { home, slug } = resolveHome(flags, deps);
    file = boardPath(home);
    const db = path.join(home, 'state.sqlite');
    if (fs.existsSync(db)) store = new Store(db);
    const now = deps.now ? deps.now() : Date.now();
    const result = action === 'write'
      ? writeBoard(file, fs.readFileSync(opts.file[0], 'utf8'), { store, now })
      : closeSubject(file, positionals[0], positionals[1], {
        agent: slug, thread: positionals[2] ?? null, now, store,
      });
    emit(deps, flags, result, action === 'close'
      ? `closed ${result.subject} in ${file}\n`
      : `${result.changed ? 'written' : 'unchanged'} ${file}\n`);
    return 0;
  } catch (error) {
    if (flags.json) emit(deps, flags, { path: file, error: error.message }, '');
    else (deps.stderr || ((text) => process.stderr.write(text)))(`${error.message}\n`);
    return 1;
  } finally {
    if (store) store.close();
  }
}

function resolveInstallation(flags, deps) {
  if (flags.installation) return path.resolve(flags.installation);
  const env = deps.env || process.env;
  if (env.RBTV_AGENT_HOME) {
    const found = workspaceFromHome(env.RBTV_AGENT_HOME);
    if (found) return found;
  }
  const start = env.RBTV_AGENT_HOME ? path.dirname(env.RBTV_AGENT_HOME) : process.cwd();
  const found = findWorkspace(start);
  if (!found) {
    fail(env.RBTV_AGENT_HOME
      ? `no installation found: ${configPath(start)} is not in the folder that holds RBTV_AGENT_HOME or above.\nPass --installation PATH.`
      : `no installation found: ${configPath(start)} is not in this folder or above.\nRun from inside an installation, or pass --installation PATH.`);
  }
  return found;
}

// Installation-wide: the daemon reads dreamer.enabled on its next tick. A call
// that asks for the state already in force writes nothing.
function setDreamerEnabled(enabled, flags, deps) {
  const workspace = resolveInstallation(flags, deps);
  const file = configPath(workspace);
  let config;
  let changed;
  let modelRecorded = false;
  try {
    config = loadConfig(workspace);
    changed = config.dreamer.enabled !== enabled;
    if (changed) {
      modelRecorded = enabled && !config.dreamer.model;
      config = updateConfig(workspace, (raw) => {
        raw.dreamer.enabled = enabled;
        if (modelRecorded) raw.dreamer.model = { ...DREAMER_MODEL };
      });
    }
  } catch (error) {
    fail(`${error.message}\nNothing changed.\nignite dreamer -h`);
  }
  const model = config.dreamer.model || null;
  const state = enabled ? 'enabled' : 'disabled';
  const lines = [changed
    ? `Dreamer ${state} for the entire installation ${workspace}, not only the calling agent.`
    : `Dreamer was already ${state} for the entire installation ${workspace}. Nothing changed.`];
  if (changed) {
    lines.push(enabled
      ? 'The nightly consolidation and the 48-hour watchdog turn on for every agent on the running service\'s next tick.'
      : 'The nightly consolidation and the 48-hour watchdog stop for every agent on the running service\'s next tick.');
  }
  if (!enabled) lines.push('A consolidation already in progress is not cancelled. ignite dreamer run still runs one consolidation.');
  lines.push(model
    ? `Model: ${model.harness} ${model.model} effort ${model.effort} (${modelRecorded ? 'recorded now in' : 'from'} dreamer.model${enabled ? '' : ', kept'}).`
    : 'Model: dreamer.model is not set; ignite dreamer enable records one.');
  if (enabled) lines.push(`To use another model, edit dreamer.model in ${file}.`);
  emit(deps, flags, { installation: workspace, config: file, enabled, changed, model, modelRecorded }, `${lines.join('\n')}\n`);
  return 0;
}

async function cmdDreamer(rest, flags, deps) {
  const flag = rest.find((arg) => arg.startsWith('-'));
  if (flag) fail(`'${flag}' is not a dreamer option\nNothing changed.\nignite dreamer -h`);
  const [verb, ...extra] = rest;
  if (!['run', 'enable', 'disable'].includes(verb) || extra.length) {
    fail('dreamer requires exactly one of run, enable, disable\nNothing changed.\nignite dreamer -h');
  }
  if (verb !== 'run') return setDreamerEnabled(verb === 'enable', flags, deps);
  let enabled = null;
  let started = false;
  let result;
  try {
    const workspace = resolveInstallation(flags, deps);
    const config = loadConfig(workspace);
    enabled = config.dreamer.enabled === true;
    if (!config.dreamer.model) throw new Error(dreamerModelRequired('to run a consolidation'));
    const daemon = require('./daemon.js');
    const run = deps.runInstalledDreamer || daemon.runInstalledDreamer;
    started = true;
    result = await run({ config, now: deps.now, runDreamer: deps.runDreamer });
  } catch (error) {
    result = {
      ok: false, busy: false, quiet: false, changed: false, alert: null,
      digestQueued: false, noticeQueued: false, delivered: false, conflictsSaved: false, error: error.message,
    };
  }
  const payload = {
    ...result,
    enabled,
    note: started && enabled === false ? 'dreamer.enabled is false; ran because this command was called' : null,
  };
  const write = deps.stdout || ((text) => process.stdout.write(text));
  write(`${JSON.stringify(payload)}\n`);
  return payload.ok && !payload.busy && !payload.alert && !payload.error ? 0 : 1;
}

function cmdRemember(rest, flags, deps) {
  if (flags.help) {
    emit(deps, { json: false }, null, REMEMBER_HELP);
    return 0;
  }
  let file = null;
  try {
    const { positionals } = parseOpts(rest, 'remember');
    if (!positionals.length) fail('remember requires <text>; use -- before option-like text');
    const text = positionals.join(' ').replace(/[\r\n\u2028\u2029]+/g, ' ').trim();
    if (!text) fail('remember requires non-empty text');
    const { home, slug, workspace } = resolveHome(flags, deps);
  if (!workspace) fail('remember requires an installation root; use --installation <path>');
    file = path.join(workspace, '.rbtv', 'memory', 'inbox.md');
    const env = deps.env || process.env;
    const key = env.IGNITE_CONVERSATION;
    const match = key?.match(/^[^:]+:([A-Z0-9]+):(\d+\.\d+)$/);
    const thread = match ? `[thread](https://app.slack.com/archives/${match[1]}/p${match[2].replace('.', '')})` : null;
    const result = remember(workspace, text, { agent: slug, thread, now: deps.now ? deps.now() : Date.now() });
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

function dispatch(command, rest, ctx, flags, deps, parsed) {
  if (command === 'schedule') return cmdSchedule(rest, ctx, flags, deps, parsed);
  if (command === 'schedules-due') return cmdDue(ctx, flags, deps, parsed);
  if (command === 'work') return cmdWork(rest, ctx, flags, deps, parsed);
  if (command === 'wake') return cmdWake(ctx, flags, deps, parsed);
  if (command === 'post') return cmdPost(ctx, flags, deps, parsed);
  fail(`unknown command: ${command}`);
}

function main(argv, deps = {}) {
  const { flags, rest } = parseGlobal(argv);
  if (flags.help && rest.length === 0) {
    emit(deps, { json: false }, { help: COMMANDS }, HELP);
    return 0;
  }
  if (rest.length === 0) fail(`usage: ignite ${['connect', 'disconnect', 'manage', 'turn', ...COMMANDS, 'deploy'].join('|')}`);
  const [command, ...tail] = rest;
  if (command === 'connect' || command === 'disconnect') return require('./connect.js').run(command, tail, flags, deps);
  if (command === 'manage') return require('./manage.js').run(tail, flags, deps);
  if (command === 'turn') {
    if (flags.help) {
      (deps.stdout || ((text) => process.stdout.write(text)))(TURN_HELP);
      return 0;
    }
    return require('./turn.js').runTurnAsync(tail);
  }
  if (flags.help) {
    const page = helpPage(command, tail);
    if (page) {
      emit(deps, { json: false }, null, page);
      return 0;
    }
  }
  if (command === 'board') return cmdBoard(tail, flags, deps);
  if (command === 'remember') return cmdRemember(tail, flags, deps);
  if (command === 'dreamer') return cmdDreamer(tail, flags, deps);
  if (command === 'deploy') return require('./deploy.js').run(tail, flags, deps, () => resolveInstallation(flags, deps));
  if (!COMMANDS.includes(command)) fail(`unknown command: ${command}\nchoose from connect, disconnect, manage, turn,\nschedule, schedules-due, work, wake, post, board, remember, dreamer, deploy\nNothing changed.\nignite -h`);
  // The words are checked before the home is opened: a refused option creates no database.
  const verb = VERBS[`${command} ${tail[0]}`] ? `${command} ${tail[0]}` : command;
  const parsed = VERBS[verb] && parseOpts(verb === command ? tail : tail.slice(1), verb);
  const ctx = openContext(flags, deps, command === 'schedule' && ['add', 'change', 'cancel'].includes(tail[0]));
  try {
    return dispatch(command, tail, ctx, flags, deps, parsed);
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

module.exports = { main, HELP, VERBS };
