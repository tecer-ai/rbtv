#!/usr/bin/env node
'use strict';

// API — entry `ignite`. Home from RBTV_AGENT_HOME, or --agent <slug> + --installation <path>.
// main(argv, deps) → exit code, or a Promise for connect/disconnect/deploy.
// deps.slack stubs Slack.
// deps.stdout / deps.stderr / deps.env optional.
// schedule next-occurrence lives in schedule.js.
// connect and disconnect run before a home is opened. There is no create command.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { randomUUID, createHash } = require('node:crypto');
const { Store, checkTool } = require('./store.js');
const { loadConfig, updateConfig, agentHome, configPath, findWorkspace, paymentsConfig, ignitePaths, resolveIgniteRuntime, legacyLayout, migrationGuardPath, MIGRATION_COMMAND, MARKER_NAME, DATABASE_NAME, LEGACY_FILES, LEGACY_DIRS } = require('./config.js');
const { cadenceSpec, nextOccurrence, FIXED_TZ } = require('./schedule.js');
const { writeBoard, closeSubject, boardPath, preflightBoard, refreshBoard, refreshBoardAfterCommit } = require('./board.js');
const { workspaceFromHome, remember } = require('./memory.js');
const { PAGES, helpPage } = require('./help.js');
const live = require('./live-status.js');
const { Gate, STATES, publicRow, formatMoney } = require('./payments.js');

const COMMANDS = ['schedule', 'schedules-due', 'work', 'wake', 'post', 'status', 'payment', 'board', 'remember', 'runtime'];
const REPORTS = new Set(['always', 'when-useful']);

// What each verb takes beside --json, --agent, --installation and -h: its options, and the most
// positional words. parseOpts refuses any other option and one word more.
const VERBS = {
  'schedule add': { options: ['at', 'cron', 'tz', 'every', 'note', 'subject', 'report', 'check', 'conversation'], words: 0 },
  'schedule list': { options: [], words: 0 },
  'schedule change': { options: ['at', 'cron', 'tz', 'every', 'note', 'report', 'check', 'enabled'], words: 1 },
  'schedule cancel': { options: [], words: 1 },
  'schedules-due': { options: ['now'], words: 0 },
  'work status': { options: ['conversation'], words: 0 },
  'work retry': { options: [], words: 1 },
  'work resume': { options: [], words: 1 },
  'work stop': { options: [], words: 1 },
  wake: { options: ['conversation', 'note', 'work'], words: 0 },
  post: { options: ['text', 'text-file', 'file', 'audio', 'thread'], words: 0 },
  status: { options: ['task', 'message', 'note'], words: 1 },
  'payment request': { options: ['connector', 'provider', 'request'], words: 0 }, // provider: the older spelling
  'payment show': { options: [], words: 1 },
  'payment list': { options: ['state'], words: 0 },
  'payment cancel': { options: [], words: 1 },
  'board write': { options: ['file', 'revision'], words: 0 },
  'board close': { options: [], words: 3 },
  remember: { options: [], words: Infinity },
  'runtime migrate': { options: [], words: 0 },
  'docs list': { options: [], words: 0 },
  'docs open': { options: ['force'], words: 1 },
  'docs pull': { options: [], words: 0 },
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
  status         Show the owner what kind of work this turn is doing, keep
                 a note for the /agent panel, or set an earlier owner
                 message's task state.
  payment        Ask the payment gate to pay, and read or withdraw this
                 agent's payment requests.
  board          Write or close a subject on the board.
  remember       Append one owner fact to the installation memory inbox.
  runtime        Move this agent's database, conversations and turns into
                 runtime/ignite/.
  docs           List this agent's recent Markdown outputs, open one in
                 its channel canvas, or pull the canvas back as Markdown.

Waking service
  deploy         Check the service's folder out at a commit, restart the
                 service and confirm it is active. Linux only.

Home: RBTV_AGENT_HOME, or --agent NAME --installation PATH.
  The installation defaults to the directory walk that finds
  .rbtv/config/ignite/config.json.
  manage's four change verbs, and schedule, work, wake, post, status,
  payment, board, remember and docs, use that agent. Help needs neither value.
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
  agentHome        optional absolute path of the rbtv agent folder this turn launches: the
                   harness then loads nothing from a folder above it and keeps no native
                   memory. Absent: the harness also loads what the folders above cwd hold
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
      if (key === 'audio' || key === 'force') {
        opts[key] = true;
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
  resolveIgniteRuntime(located.home, { workspace: located.workspace, slug: located.slug });
  return {
    ...located,
    config,
    store: new Store(ignitePaths(located.home).database),
    castCmd: config?.tools?.cast || 'cast',
  };
}

function reportOf(opts, fallback) {
  const report = opts.report ?? fallback ?? 'when-useful';
  if (!REPORTS.has(report)) fail('--report must be always or when-useful');
  return report;
}

function checkOf(opts, fallback = null) {
  if (opts.check == null) return fallback;
  try {
    return checkTool(opts.check);
  } catch (error) {
    fail(`--${error.message}`);
  }
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
      ? `${rows.map((row) => `${row.id} ${row.cadence} ${row.timezone} next=${row.next_at} enabled=${row.enabled} ${row.check_tool ? `check=${row.check_tool} ` : ''}${row.note || ''}`).join('\n')}\n`
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
    const check = checkOf(opts);
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
      checkTool: check,
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
    const check = checkOf(opts, existing.check_tool);
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
      checkTool: check,
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
    // This command runs no check tool: a timer that has one stays due for the waking service.
    if (sched.check_tool) {
      results.push({ id: sched.id, inserted: false, reason: 'check', nextAt: sched.next_at });
      continue;
    }
    const nextAt = nextOccurrence(sched.cadence, sched.timezone, now);
    const wake = ctx.store.fireSchedule({ schedule: sched, nextAt });
    results.push({ id: sched.id, inserted: wake.inserted, reason: wake.reason, nextAt: wake.advanced ? nextAt : sched.next_at });
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
  // The DM agent's channel is the owner's direct conversation, a contact: a new thread there goes through the
  // message port command, which checks the permission and picks the connector (connector architecture, phase 2).
  if (target.imUser) fail(`post refused: this agent's channel is the owner's direct conversation, a contact; use message send --to ${target.imUser} --via slack TEXT. Nothing changed.`);
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

// The open document of the agent's channel canvas (docs.js): the same operations the /agent panel's Docs tab runs.
// Its own context, closed when the Slack calls are done.
async function cmdDocs(rest, flags, deps) {
  const [action, ...tail] = rest;
  if (!['list', 'open', 'pull'].includes(action)) fail('docs requires list, open or pull\nNothing changed.\nignite docs -h');
  const { opts, positionals } = parseOpts(tail, `docs ${action}`);
  if (action === 'open' && !positionals[0]) fail('docs open requires the path of a Markdown file, relative to the installation\nNothing changed.\nignite docs open -h');
  const ctx = openContext(flags, deps);
  try {
    const docs = require('./docs.js');
    if (action === 'list') {
      const list = docs.recentDocs(ctx.store, ctx.workspace);
      const open = docs.openDocument(ctx.store)?.path || null;
      emit(deps, flags, { docs: list, open }, `${list.map((doc) => `${doc.path}  (from a turn ${new Date(doc.at).toISOString()})`).join('\n')}${list.length ? '\n' : 'no Markdown document in the recent turn outputs\n'}in the canvas: ${open || 'nothing'}\n`);
      return 0;
    }
    if (!ctx.config) fail('docs needs Ignite\'s config.json\nNothing changed.');
    const { Slack } = require('./slack.js');
    const { slackToken } = require('./config.js');
    const slack = deps.slack || new Slack({ botToken: slackToken(ctx.config, 'bot'), stoolsWorkspace: ctx.config.slack.stoolsWorkspace });
    if (action === 'pull') {
      const pulled = await docs.pullDoc({ slack, store: ctx.store });
      if (!pulled) {
        emit(deps, flags, { path: null }, 'no document is open in the canvas\n');
        return 0;
      }
      emit(deps, flags, pulled, `path: ${pulled.path}\nedited: ${pulled.edited ? 'yes' : 'no'}\ncomments: ${pulled.comments} (their text stays in the canvas)\n---\n${pulled.markdown}`);
      return 0;
    }
    const channel = Object.entries(ctx.config.routes || {}).find(([, routed]) => routed === ctx.slug)?.[0];
    if (!channel) fail(`agent ${ctx.slug} has no channel of its own: documents open in a channel canvas\nNothing changed.`);
    const result = await docs.openDoc({ slack, store: ctx.store, workspace: ctx.workspace, channel, path: positionals[0], force: Boolean(opts.force) });
    const next = result.refused === 'edited' ? 'bring the edits in first with ignite docs pull, or replace them with --force' : 'replace it with --force when what it holds can be lost';
    if (result.refused) fail(`not opened: ${result.why}\n${next}\nNothing changed.`);
    emit(deps, flags, result, `opened ${result.opened} in the canvas ${result.canvasId} of channel ${channel}\n`);
    return 0;
  } finally {
    ctx.store.close();
  }
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
    const { home, slug, workspace } = resolveHome(flags, deps);
    file = boardPath(home);
    resolveIgniteRuntime(home, { workspace, slug });
    const db = ignitePaths(home).database;
    if (fs.existsSync(db)) store = new Store(ignitePaths(home).database);
    const now = deps.now ? deps.now() : Date.now();
    const result = action === 'write'
      ? writeBoard(file, fs.readFileSync(opts.file[0], 'utf8'), { store, now, revision: opts.revision ?? null })
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
        resolveIgniteRuntime(home, { workspace, slug });
        store = new Store(ignitePaths(home).database);
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

// The most characters a progress note keeps: one line the /agent panel shows whole.
const NOTE_CHARS = 300;

// The words of status are checked before the home is opened: a refused one changes nothing.
function checkStatus({ opts, positionals }, deps) {
  const again = '\nNothing changed.\nignite status -h';
  if (opts.note != null) {
    if (/[\r\n]/.test(opts.note)) fail(`--note takes one line${again}`);
    if ([...opts.note].length > NOTE_CHARS) fail(`--note takes at most ${NOTE_CHARS} characters; this one has ${[...opts.note].length}${again}`);
    if (opts.task != null || opts.message != null) fail(`--note goes with a state word or alone, not with --task${again}`);
  }
  if (opts.task != null || opts.message != null) {
    if (positionals.length) fail(`unexpected word '${positionals[0]}': status --task takes no state word${again}`);
    if (opts.task == null) fail(`--message requires --task ${live.TASK.join('|')}${again}`);
    if (opts.message == null) fail(`--task requires --message <ts>, the Slack timestamp of an earlier owner message or reply${again}`);
    if (!live.TASK.includes(opts.task)) fail(`unknown task state: ${opts.task}\nchoose from ${live.TASK.join(', ')}${again}`);
  } else if (!positionals.length) {
    if (opts.note == null) fail(`status requires a state: ${live.DECLARED.join(', ')}, or --note <text>${again}`);
  } else if (!live.DECLARED.includes(positionals[0])) {
    fail(`unknown state: ${positionals[0]}\nchoose from ${live.DECLARED.join(', ')}${again}`);
  }
  if (!(deps.env || process.env).IGNITE_CONVERSATION) {
    fail(`ignite status runs inside a turn: IGNITE_CONVERSATION is not set${again}`);
  }
}

function cmdStatus(ctx, flags, deps, { opts, positionals }) {
  const key = (deps.env || process.env).IGNITE_CONVERSATION;
  if (opts.task != null) {
    const row = live.markTask(ctx.store, key, opts.message, opts.task);
    emit(deps, flags, { task: row.kept, message: row.ts }, `task ${row.kept} shown on ${row.ts}\n`);
    return 0;
  }
  // A note is kept with the conversation for the owner's /agent panel; it shows nothing in the thread. It is
  // saved after the declaration, so a refused declaration saves no note either.
  const note = opts.note != null;
  const noted = note ? 'note saved\n' : '';
  const row = positionals.length ? live.declare(ctx.store, key, positionals[0]) : null;
  if (note) ctx.store.addNote({ conversationKey: ctx.store.followConversation(key)?.key || key, text: opts.note.trim() });
  if (!positionals.length) {
    emit(deps, flags, { state: null, message: null, note }, noted);
    return 0;
  }
  if (!row) {
    emit(deps, flags, { state: positionals[0], message: null, note }, `nothing shown: this turn answers no owner message\n${noted}`);
    return 0;
  }
  emit(deps, flags, { state: row.agent, message: row.ts, note }, `${row.agent} shown on ${row.ts}\n${noted}`);
  return 0;
}

// The words of payment are checked before the home is opened: a refused one changes nothing. No verb
// approves, refuses or changes the gate's settings: those are the owner's, in Slack.
function checkPayment(tail, parsed, deps) {
  const again = '\nNothing changed.\nignite payment -h';
  if (!parsed) fail(`${tail[0] ? `unknown payment verb: ${tail[0]}` : 'payment requires request, show, list or cancel'}${again}`);
  const action = tail[0];
  if (action === 'request') {
    if (parsed.opts.connector && parsed.opts.provider) fail(`payment request takes --connector <name>; --provider is its older spelling: give one${again}`);
    if (!parsed.opts.connector && !parsed.opts.provider) fail(`payment request requires --connector <name>${again}`); // older spelling: --provider
    if (!parsed.opts.request) fail(`payment request requires --request <JSON>, or --request - to read it from stdin${again}`);
    if (!(deps.env || process.env).IGNITE_CONVERSATION) fail(`ignite payment request runs inside a turn: IGNITE_CONVERSATION is not set${again}`);
  }
  if ((action === 'show' || action === 'cancel') && !parsed.positionals[0]) fail(`payment ${action} requires a request id, such as P-0007${again}`);
  if (action === 'list' && parsed.opts.state != null && !STATES.includes(parsed.opts.state)) {
    fail(`unknown state: ${parsed.opts.state}\nchoose from ${STATES.join(', ')}${again}`);
  }
}

function paymentRequest(raw) {
  let value;
  try { value = JSON.parse(raw); } catch (error) { fail(`--request is not JSON: ${error.message}\nNothing changed.`); }
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail('--request must be a JSON object\nNothing changed.');
  const recipient = value.recipient && typeof value.recipient === 'object' ? value.recipient : {};
  return {
    method: value.method,
    recipient: {
      name: recipient.name, key: recipient.key, keyType: recipient.key_type,
      document: recipient.document, bank: recipient.bank,
    },
    amountCents: value.amount_cents,
    feeCents: value.fee_cents ?? 0,
    note: value.note,
    details: value.details,
  };
}

function paymentLines(row, money) {
  const r = row.recipient;
  return [
    `${row.id}  ${row.state}${row.reason ? `: ${row.reason}` : ''}`,
    `Recipient  ${[r.name, r.document, r.bank].filter(Boolean).join(' · ') || '-'}`,
    `Key        ${r.key}${r.key_type ? ` (${r.key_type})` : ''}`,
    `Amount     ${money(row.amount_cents)}${row.fee_cents ? ` + fee ${money(row.fee_cents)}` : ''}`,
    `Note       ${row.note || '-'}`,
    `Connector  ${row.connector} ${row.method}, id ${row.connector_id || '-'}${row.connector_status ? ` (${row.connector_status})` : ''}, receipt ${row.receipt_url || '-'}`,
  ].join('\n');
}

function cmdPayment(rest, ctx, flags, deps, { opts, positionals }) {
  if (!ctx.config || !paymentsConfig(ctx.config)) {
    fail("payments are not set up in this installation: Ignite's config has no payments section\nNothing changed.");
  }
  const settings = paymentsConfig(ctx.config);
  const gate = new Gate({ workspace: ctx.config.workspace, now: deps.now, timeZone: settings.timeZone, currency: settings.currency });
  const money = (cents) => formatMoney(cents, settings.currency);
  try {
    const action = rest[0];
    if (action === 'request') {
      const key = (deps.env || process.env).IGNITE_CONVERSATION;
      if (!ctx.store.getConversation(key)) fail(`unknown conversation: ${key}\nNothing changed.`);
      const raw = opts.request === '-' ? (deps.stdin ?? fs.readFileSync(0, 'utf8')) : opts.request;
      const row = publicRow(gate.request({ agent: ctx.slug, conversationKey: key, connector: opts.connector || opts.provider, ...paymentRequest(raw) })); // older spelling: --provider
      emit(deps, flags, row, `${row.id} ${row.state}: ${row.reason}\n`);
      return 0;
    }
    if (action === 'list') {
      const rows = gate.list({ agent: ctx.slug, state: opts.state || null, limit: 20 }).map(publicRow);
      emit(deps, flags, { payments: rows }, rows.length
        ? `${rows.map((row) => `${row.id}  ${row.state.padEnd(9)} ${money(row.amount_cents + row.fee_cents).padStart(12)}  ${row.recipient.name || row.recipient.key}${row.reason ? `  (${row.reason})` : ''}`).join('\n')}\n`
        : 'no payment requests\n');
      return 0;
    }
    const id = positionals[0];
    if (action === 'show') {
      const row = gate.get(id);
      if (!row || row.agent !== ctx.slug) fail(`unknown payment request: ${id}\nNothing changed.\nignite payment list`);
      const out = publicRow(row);
      emit(deps, flags, out, `${paymentLines(out, money)}\n`);
      return 0;
    }
    const { row } = gate.cancel(id, ctx.slug);
    const out = publicRow(row);
    emit(deps, flags, out, `cancelled ${out.id}\n`);
    return 0;
  } finally {
    gate.close();
  }
}

function dispatch(command, rest, ctx, flags, deps, parsed) {
  if (command === 'schedule') return cmdSchedule(rest, ctx, flags, deps, parsed);
  if (command === 'schedules-due') return cmdDue(ctx, flags, deps, parsed);
  if (command === 'work') return cmdWork(rest, ctx, flags, deps, parsed);
  if (command === 'wake') return cmdWake(ctx, flags, deps, parsed);
  if (command === 'post') return cmdPost(ctx, flags, deps, parsed);
  if (command === 'status') return cmdStatus(ctx, flags, deps, parsed);
  if (command === 'payment') return cmdPayment(rest, ctx, flags, deps, parsed);
  fail(`unknown command: ${command}`);
}

function cmdAlbert(tail, flags, deps) {
  const evidence = require('./albert-evidence.js');
  const stdout = deps.stdout || ((text) => process.stdout.write(text));
  const stderr = deps.stderr || ((text) => process.stderr.write(text));
  if (!tail[0] || flags.help) {
    stdout(PAGES.albert);
    return 0;
  }
  const installation = resolveInstallation(flags, deps);
  const env = deps.env || process.env;
  const home = env.RBTV_AGENT_HOME || path.join(installation, '.rbtv', 'agents', flags.agent || 'albert');
  const previous = process.env.RBTV_AGENT_HOME;
  process.env.RBTV_AGENT_HOME = home;
  const chunks = [];
  const write = process.stdout.write.bind(process.stdout);
  process.stdout.write = (text) => { chunks.push(String(text)); return true; };
  try {
    const code = evidence.main(tail);
    process.stdout.write = write;
    stdout(chunks.join(''));
    return code;
  } catch (error) {
    stderr(`${error.message}\n`);
    return 1;
  } finally {
    process.stdout.write = write;
    if (previous == null) delete process.env.RBTV_AGENT_HOME;
    else process.env.RBTV_AGENT_HOME = previous;
  }
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
  if (command === 'albert') return cmdAlbert(tail, flags, deps);
  if (command === 'runtime') return cmdRuntime(tail, flags, deps);
  if (command === 'docs') return cmdDocs(tail, flags, deps);
  if (command === 'deploy') return require('./deploy.js').run(tail, flags, deps, () => resolveInstallation(flags, deps));
  if (!COMMANDS.includes(command)) fail(`unknown command: ${command}\nchoose from connect, disconnect, manage, turn,\nschedule, schedules-due, work, wake, post, status, payment, board, remember, runtime, docs, deploy\nNothing changed.\nignite -h`);
  // The words are checked before the home is opened: a refused option creates no database.
  const verb = VERBS[`${command} ${tail[0]}`] ? `${command} ${tail[0]}` : command;
  const parsed = VERBS[verb] && parseOpts(verb === command ? tail : tail.slice(1), verb);
  if (command === 'status') checkStatus(parsed, deps);
  if (command === 'payment') checkPayment(tail, parsed, deps);
  const ctx = openContext(flags, deps, command === 'schedule' && ['add', 'change', 'cancel'].includes(tail[0]));
  try {
    return dispatch(command, tail, ctx, flags, deps, parsed);
  } finally {
    ctx.store.close();
  }
}

const STAGES = ['staged', 'validated', 'renamed', 'completion-recorded', 'legacy-retired'];
const LEGACY_NAMES = [...LEGACY_FILES, ...LEGACY_DIRS];

function refuseMigration(message) {
  const error = new Error(message);
  error.exitCode = 1;
  throw error;
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  const fd = fs.openSync(tmp, 'w', 0o600);
  try {
    fs.writeFileSync(fd, `${JSON.stringify(value)}\n`, 'utf8');
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
  fs.renameSync(tmp, file);
}

function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

function hashFile(file) {
  return createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function walkFiles(dir, out) {
  if (!fs.existsSync(dir)) return;
  const stat = fs.lstatSync(dir);
  if (stat.isSymbolicLink()) refuseMigration(`refusing to copy symlink: ${dir}`);
  if (stat.isDirectory()) {
    for (const name of fs.readdirSync(dir)) walkFiles(path.join(dir, name), out);
    return;
  }
  if (stat.isFile()) out.push(dir);
}

function legacyFiles(home) {
  const files = [];
    for (const name of LEGACY_FILES) {
    const file = path.join(home, name);
    if (!fs.existsSync(file)) continue;
    if (fs.lstatSync(file).isSymbolicLink()) refuseMigration(`refusing to copy symlink: ${file}`);
    files.push(file);
  }
  walkFiles(path.join(home, 'conversations'), files);
  walkFiles(path.join(home, 'turns'), files);
  return files;
}

function hashSet(home, files) {
  const hashes = {};
  for (const file of files) hashes[path.relative(home, file)] = hashFile(file);
  return hashes;
}

function sameHashes(left, right) {
  const keys = new Set([...Object.keys(left), ...Object.keys(right)]);
  for (const key of keys) if (left[key] !== right[key]) return false;
  return true;
}

function orphanSidecar(home) {
  return !fs.existsSync(path.join(home, DATABASE_NAME))
    && (fs.existsSync(path.join(home, `${DATABASE_NAME}-wal`)) || fs.existsSync(path.join(home, `${DATABASE_NAME}-shm`)));
}

function copyFileDurable(from, to) {
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.copyFileSync(from, to);
  const fd = fs.openSync(to, 'r+');
  try { fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
}

function copyEntry(from, to) {
  const stat = fs.lstatSync(from);
  if (stat.isSymbolicLink()) refuseMigration(`refusing to copy symlink: ${from}`);
  if (stat.isDirectory()) {
    fs.mkdirSync(to, { recursive: true });
    for (const name of fs.readdirSync(from)) copyEntry(path.join(from, name), path.join(to, name));
    return;
  }
  copyFileDurable(from, to);
}

function copyLegacy(home, staging) {
  for (const name of LEGACY_NAMES) {
    const from = path.join(home, name);
    if (fs.existsSync(from)) copyEntry(from, path.join(staging, name));
  }
}

const AGENT_HOME_FN = `def _ignite_agent_home():
    here = Path(__file__).resolve()
    for folder in here.parents:
        rel = here.relative_to(folder).parts
        if len(rel) >= 5 and rel[:4] == ("rbtv", "capabilities", "tools", rel[3]):
            return folder
        if len(rel) >= 4 and rel[:3] == ("capabilities", "tools", rel[2]) and folder.name != "rbtv":
            return folder
    raise RuntimeError(f"agent home not found from {here}")
`;

function toolDestRel(value) {
  if (typeof value !== 'string' || !value) return null;
  const slash = value.replaceAll('\\', '/');
  if (slash.startsWith('rbtv/capabilities/tools/')) return slash;
  if (slash.startsWith('capabilities/tools/')) return `rbtv/${slash}`;
  return null;
}

function checkToolsFromLegacyCopy(home) {
  const database = path.join(home, DATABASE_NAME);
  if (!fs.existsSync(database)) return [];
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-rm-'));
  try {
    for (const name of LEGACY_FILES) {
      const from = path.join(home, name);
      if (fs.existsSync(from)) fs.copyFileSync(from, path.join(scratch, name));
    }
    return readCheckTools(path.join(scratch, DATABASE_NAME));
  } finally {
    fs.rmSync(scratch, { recursive: true, force: true });
  }
}

function readCheckTools(database) {
  if (!fs.existsSync(database)) return [];
  const { DatabaseSync } = require('node:sqlite');
  const db = new DatabaseSync(database, { readOnly: true });
  try {
    if (!db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='schedules'").get()) return [];
    return db.prepare('SELECT check_tool FROM schedules').all().map((row) => row.check_tool).filter(Boolean);
  } finally {
    db.close();
  }
}

function sourceToolNames(home) {
  const dir = path.join(home, 'capabilities', 'tools');
  if (!fs.existsSync(dir)) return [];
  const names = [];
  for (const name of fs.readdirSync(dir).sort()) {
    const full = path.join(dir, name);
    const stat = fs.lstatSync(full);
    if (stat.isSymbolicLink()) refuseMigration(`refusing to move symlink: ${full}`);
    if (stat.isDirectory()) names.push(name);
  }
  return names;
}

function destToolNames(home) {
  const dir = path.join(home, 'rbtv', 'capabilities', 'tools');
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((name) => {
    const full = path.join(dir, name);
    return fs.statSync(full).isDirectory() && !fs.lstatSync(full).isSymbolicLink();
  }).sort();
}

function assertCheckToolsPlaceable(home, tools) {
  for (const stored of tools) {
    const destRel = toolDestRel(stored);
    if (!destRel) continue;
    if (fs.existsSync(path.join(home, ...destRel.split('/')))) continue;
    const sourceRel = destRel.slice('rbtv/'.length);
    if (fs.existsSync(path.join(home, ...sourceRel.split('/')))) continue;
    const error = new Error(`cannot place check tool ${stored}`);
    error.exitCode = 1;
    error.unplaced = true;
    throw error;
  }
}

function assertToolsMovable(home) {
  try {
    for (const name of sourceToolNames(home)) {
      if (fs.existsSync(path.join(home, 'rbtv', 'capabilities', 'tools', name))) {
        refuseMigration(`cannot place capabilities/tools/${name}; rbtv/capabilities/tools/${name} already exists`);
      }
    }
  } catch (error) {
    error.unplaced = true;
    error.exitCode = error.exitCode || 1;
    throw error;
  }
}

function ownToolsPending(home) {
  if (sourceToolNames(home).length) return true;
  const database = ignitePaths(home).database;
  for (const stored of readCheckTools(database)) {
    const destRel = toolDestRel(stored);
    if (!destRel) continue;
    if (fs.existsSync(path.join(home, ...destRel.split('/')))) continue;
    const sourceRel = destRel.startsWith('rbtv/') ? destRel.slice('rbtv/'.length) : null;
    if (sourceRel && fs.existsSync(path.join(home, ...sourceRel.split('/')))) return true;
  }
  return false;
}

function removeEmptyDir(dir) {
  if (!fs.existsSync(dir)) return;
  if (fs.readdirSync(dir).length) return;
  fs.rmdirSync(dir);
}

function insertAfterImports(text, block) {
  const lines = text.split('\n');
  let insertAt = 0;
  let doc = null;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (i === 0 && line.startsWith('#!')) { insertAt = 1; continue; }
    if (doc) {
      if (line.includes(doc)) { doc = null; insertAt = i + 1; }
      continue;
    }
    if (line.startsWith('"""') || line.startsWith("'''")) {
      const quote = line.slice(0, 3);
      if (line.length > 3 && line.slice(3).includes(quote)) insertAt = i + 1;
      else doc = quote;
      continue;
    }
    if (line.startsWith('import ') || line.startsWith('from ')) { insertAt = i + 1; continue; }
    if (line.trim() === '') continue;
    break;
  }
  lines.splice(insertAt, 0, block.trimEnd());
  return lines.join('\n');
}

const TOKEN_START = " \t\n\r\"'`";

function startsToken(text, index) {
  return index === 0 || TOKEN_START.includes(text[index - 1]);
}

function startsSegment(text, index) {
  return index === 0 || text[index - 1] === '/' || TOKEN_START.includes(text[index - 1]);
}

function homePrefixes(home) {
  const slug = path.basename(path.resolve(home));
  const folders = [path.resolve(home), home].map((item) => `${item.replaceAll('\\', '/').replace(/\/$/, '')}/`);
  return { slug, folders, relative: `.rbtv/agents/${slug}/` };
}

function ownStart(text, at, home) {
  const before = text.slice(0, Math.max(0, at));
  if (before.endsWith('./') && startsToken(text, at - 2)) return true;
  const { folders, relative } = homePrefixes(home);
  const homeAngle = '<home>/';
  if (before.endsWith(homeAngle) && startsSegment(text, at - homeAngle.length)) return true;
  if (folders.some((prefix) => before.endsWith(prefix) && startsSegment(text, at - prefix.length))) return true;
  if (before.endsWith(relative) && startsSegment(text, at - relative.length)) return true;
  return startsToken(text, at);
}

// Classify one occurrence of capabilities/tools/<tool>/, in this order.
// 1. Rewrite: what stands immediately before it is a token start (start of the text, whitespace, a backtick, a quote), or ./ standing at a token start, or this agent's own home (<home>/, the absolute agent folder with a trailing slash, .rbtv/agents/<this slug>/). ./ counts only when the character before the dot is a token start, so ../ and x./ do not. A home prefix counts only as a whole segment: it starts at the text, after /, or at a token start, so x.rbtv/agents/<slug>/ and x<home>/ do not, and a slug that is only a prefix of another name does not.
// 2. Left silently, already moved: what stands immediately before it is the path segment rbtv/, and what stands before that rbtv/ satisfies 1. notrbtv/, xrbtv/ and vendor/rbtv/ do not qualify.
// 3. Left silently, another agent's folder: .rbtv/agents/<other>/ or /agents/<other>/, the other name a whole segment. /myagents/x/ is not /agents/x/. .rbtv/agents/<slug>extra/ is that other name, not this slug.
// 4. Everything else: left byte-identical and printed not rewritten: <file>:<line>.
function classifyOwnToolRef(text, at, home) {
  if (ownStart(text, at, home)) return 'own';
  const before = text.slice(0, at);
  if (before.endsWith('rbtv/') && ownStart(text, at - 'rbtv/'.length, home)) return 'already';
  const { slug } = homePrefixes(home);
  const other = before.match(/(?:^|\/)\.rbtv\/agents\/([^/]+)\/$/) || before.match(/\/agents\/([^/]+)\/$/);
  if (other && other[1] !== slug) return 'leave';
  return 'unsure';
}

function rewriteHomeAngle(text) {
  const from = '<home>/capabilities/tools/';
  const to = '<home>/rbtv/capabilities/tools/';
  let out = '';
  let i = 0;
  while (i < text.length) {
    const at = text.indexOf(from, i);
    if (at === -1) return out + text.slice(i);
    out += text.slice(i, at);
    out += startsSegment(text, at) ? to : from;
    i = at + from.length;
  }
  return out;
}

function rewriteOwnToolRefs(text, names, home) {
  const needles = names.map((name) => `capabilities/tools/${name}/`);
  let out = '';
  let i = 0;
  while (i < text.length) {
    let at = -1;
    let needle = null;
    for (const item of needles) {
      const found = text.indexOf(item, i);
      if (found !== -1 && (at === -1 || found < at)) {
        at = found;
        needle = item;
      }
    }
    if (at === -1) return out + text.slice(i);
    out += text.slice(i, at);
    if (classifyOwnToolRef(text, at, home) === 'own') out += 'rbtv/';
    out += needle;
    i = at + needle.length;
  }
  return out;
}

function unsureOwnToolRefs(text, names, home, rel) {
  const lines = new Set();
  for (const name of names) {
    const needle = `capabilities/tools/${name}/`;
    let from = 0;
    while (from < text.length) {
      const at = text.indexOf(needle, from);
      if (at === -1) break;
      if (classifyOwnToolRef(text, at, home) === 'unsure') lines.add(`not rewritten: ${rel}:${text.slice(0, at).split('\n').length}`);
      from = at + needle.length;
    }
  }
  return [...lines];
}

function rewriteInvocations(home, names) {
  const changes = [];
  const roots = ['prompt.md', 'AGENTS.md', 'CLAUDE.md', 'skills', 'rbtv', 'capabilities']
    .map((name) => path.join(home, name));
  const visit = (file) => {
    if (!fs.existsSync(file)) return;
    const stat = fs.lstatSync(file);
    if (stat.isSymbolicLink()) return;
    if (stat.isDirectory()) {
      for (const name of fs.readdirSync(file)) visit(path.join(file, name));
      return;
    }
    if (!stat.isFile()) return;
    const buf = fs.readFileSync(file);
    if (buf.includes(0)) return;
    let text = buf.toString('utf8');
    let next = rewriteOwnToolRefs(text, names, home);
    next = rewriteHomeAngle(next);
    const rel = path.relative(home, file).split(path.sep);
    const relPath = rel.join('/');
    if (rel[0] === 'rbtv' && rel[1] === 'capabilities' && rel[2] === 'tools' && names.includes(rel[3]) && file.endsWith('.py')) {
      const oldParts = ['capabilities', 'tools', rel[3], ...rel.slice(4)];
      const homeIndex = oldParts.length - 1;
      const pattern = `Path(__file__).resolve().parents[${homeIndex}]`;
      if (next.includes(pattern)) {
        next = next.replaceAll(pattern, '_ignite_agent_home()');
        if (!next.includes('def _ignite_agent_home(')) next = insertAfterImports(next, AGENT_HOME_FN);
      }
    }
    for (const notice of unsureOwnToolRefs(next, names, home, relPath)) changes.push(notice);
    if (next === text) return;
    fs.writeFileSync(file, next);
    changes.push(`rewrote ${relPath}`);
  };
  for (const root of roots) visit(root);
  return changes.sort();
}

function placeOwnTools(home) {
  const changes = [];
  for (const name of sourceToolNames(home)) {
    const from = path.join(home, 'capabilities', 'tools', name);
    const to = path.join(home, 'rbtv', 'capabilities', 'tools', name);
    if (fs.existsSync(to)) refuseMigration(`cannot place capabilities/tools/${name}; rbtv/capabilities/tools/${name} already exists`);
    fs.mkdirSync(path.dirname(to), { recursive: true });
    fs.renameSync(from, to);
    changes.push(`moved capabilities/tools/${name} -> rbtv/capabilities/tools/${name}`);
  }
  removeEmptyDir(path.join(home, 'capabilities', 'tools'));
  removeEmptyDir(path.join(home, 'capabilities'));
  const names = [...new Set([...changes.map((line) => line.split(' ')[1].split('/').pop()), ...destToolNames(home)])];
  return [...changes.sort(), ...rewriteInvocations(home, names)];
}

function finishOwnTools(home) {
  assertToolsMovable(home);
  assertCheckToolsPlaceable(home, readCheckTools(ignitePaths(home).database));
  const changes = placeOwnTools(home);
  for (const stored of readCheckTools(ignitePaths(home).database)) {
    const destRel = toolDestRel(stored);
    if (!destRel) continue;
    if (!fs.existsSync(path.join(home, ...destRel.split('/')))) refuseMigration(`cannot place check tool ${stored}`);
  }
  return changes;
}

function mapStoredPath(value, home) {
  if (typeof value !== 'string' || !value) return null;
  const paths = ignitePaths(home);
  const pairs = [
    [path.join(home, 'conversations'), paths.conversations],
    [path.join(home, 'turns'), paths.turns],
    [path.join(home, DATABASE_NAME), paths.database],
  ];
  const normalized = path.normalize(value);
  for (const [from, to] of pairs) {
    if (normalized === from || normalized.startsWith(from + path.sep)) return to + normalized.slice(from.length);
  }
  const slash = value.replaceAll('\\', '/');
  if (slash.startsWith('capabilities/tools/') && !slash.startsWith('rbtv/')) return `rbtv/${slash}`;
  for (const [prefix, dest] of [['conversations', paths.conversations], ['turns', paths.turns], [DATABASE_NAME, paths.database]]) {
    if (slash === prefix || slash.startsWith(`${prefix}/`)) {
      return dest + slash.slice(prefix.length).replaceAll('/', path.sep);
    }
  }
  return null;
}

function unmappableStorePath(value, home) {
  if (typeof value !== 'string' || !path.isAbsolute(value) || mapStoredPath(value, home)) return false;
  const parts = value.split(/[/\\]/);
  return parts.includes('conversations') || parts.includes('turns') || parts.includes(DATABASE_NAME);
}

function rewriteNode(value, home, active, blocked, log, where) {
  if (Array.isArray(value)) return value.map((item, index) => rewriteNode(item, home, active, blocked, log, `${where}[${index}]`));
  if (value && typeof value === 'object') {
    const out = {};
    for (const [key, child] of Object.entries(value)) out[key] = rewriteNode(child, home, active, blocked, log, `${where}.${key}`);
    return out;
  }
  if (typeof value !== 'string') return value;
  const mapped = mapStoredPath(value, home);
  if (mapped) {
    log.push({ where, old: value, new: mapped });
    return mapped;
  }
  if (active && unmappableStorePath(value, home)) blocked.push(where);
  return value;
}

function rewriteField(text, home, active, blocked, log, where) {
  if (text == null) return { text, changed: false };
  const before = log.length;
  const raw = String(text);
  let next;
  try {
    next = JSON.stringify(rewriteNode(JSON.parse(raw), home, active, blocked, log, where));
  } catch {
    next = rewriteNode(raw, home, active, blocked, log, where);
  }
  return log.length === before ? { text, changed: false } : { text: next, changed: true };
}

function tableCounts(db) {
  const integrity = db.prepare('PRAGMA integrity_check').all().map((row) => row.integrity_check);
  const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all();
  const counts = {};
  for (const { name } of tables) {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) refuseMigration(`unexpected table name: ${name}`);
    counts[name] = db.prepare(`SELECT COUNT(*) AS n FROM ${name}`).get().n;
  }
  return { integrity, counts };
}

function validateCopy(staging, home) {
  const database = path.join(staging, DATABASE_NAME);
  if (!fs.existsSync(database)) return;
  const scratch = path.join(home, 'runtime', `.ignite-count-${path.basename(staging)}`);
  fs.rmSync(scratch, { recursive: true, force: true });
  fs.mkdirSync(scratch, { recursive: true });
  try {
  for (const name of LEGACY_FILES) {
      const from = path.join(staging, name);
      if (fs.existsSync(from)) copyFileDurable(from, path.join(scratch, name));
    }
    const { DatabaseSync } = require('node:sqlite');
    const legacyDb = new DatabaseSync(path.join(scratch, DATABASE_NAME));
    let legacyCounts;
    try { legacyCounts = tableCounts(legacyDb).counts; } finally { legacyDb.close(); }
    const staged = new DatabaseSync(database);
    try {
      const checked = tableCounts(staged);
      if (checked.integrity.join(',') !== 'ok') refuseMigration(`staged database failed integrity_check: ${checked.integrity.join(',')}`);
      const names = new Set([...Object.keys(legacyCounts), ...Object.keys(checked.counts)]);
      for (const name of names) {
        if (legacyCounts[name] !== checked.counts[name]) refuseMigration(`row count mismatch on ${name}`);
      }
      assertToolsMovable(home);
      const scheduleTable = staged.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='schedules'").get();
      const checkTools = scheduleTable
        ? staged.prepare('SELECT check_tool FROM schedules').all().map((row) => row.check_tool).filter(Boolean)
        : [];
      assertCheckToolsPlaceable(home, checkTools);
      const blocked = [];
      const log = [];
      const rewrite = (table, id, column, text, active) => {
        const next = rewriteField(text, home, active, blocked, log, `${table} ${id} ${column}`);
        if (next.changed) staged.prepare(`UPDATE ${table} SET ${column}=? WHERE id=?`).run(String(next.text), id);
      };
      for (const row of staged.prepare('SELECT id, state, launch_snapshot, output FROM runs').all()) {
        const active = row.state !== 'finished' && row.state !== 'failed';
        rewrite('runs', row.id, 'launch_snapshot', row.launch_snapshot, active);
        rewrite('runs', row.id, 'output', row.output, active);
      }
      for (const row of staged.prepare('SELECT id, state, payload FROM outbox').all()) {
        rewrite('outbox', row.id, 'payload', row.payload, row.state !== 'delivered' && row.state !== 'failed');
      }
      for (const row of staged.prepare('SELECT id, files FROM messages').all()) {
        rewrite('messages', row.id, 'files', row.files, false);
      }
      for (const row of staged.prepare('SELECT id, check_tool FROM schedules').all()) {
        rewrite('schedules', row.id, 'check_tool', row.check_tool, false);
      }
      for (const row of staged.prepare('SELECT conversation_key, harness, session_id FROM conversation_sessions').all()) {
        const where = `conversation_sessions ${row.conversation_key} ${row.harness} session_id`;
        const next = rewriteField(row.session_id, home, false, blocked, log, where);
        if (next.changed) {
          staged.prepare('UPDATE conversation_sessions SET session_id=? WHERE conversation_key=? AND harness=?')
            .run(String(next.text), row.conversation_key, row.harness);
        }
      }
      if (blocked.length) refuseMigration(`cutover blocked: ${blocked.join('; ')}`);
      const after = tableCounts(staged).counts;
      for (const name of Object.keys(legacyCounts)) {
        if (after[name] !== legacyCounts[name]) refuseMigration(`rewrite changed row count of ${name}`);
      }
      fs.writeFileSync(path.join(staging, 'path-map.jsonl'), `${log.map((line) => JSON.stringify(line)).join('\n')}${log.length ? '\n' : ''}`, 'utf8');
    } finally {
      staged.close();
    }
  } finally {
    fs.rmSync(scratch, { recursive: true, force: true });
  }
}

function retireLegacy(home) {
  const retention = path.join(home, 'runtime', 'ignite-premigration');
  fs.mkdirSync(retention, { recursive: true });
  for (const name of LEGACY_NAMES) {
    const from = path.join(home, name);
    if (!fs.existsSync(from)) continue;
    const to = path.join(retention, name);
    if (fs.existsSync(to)) refuseMigration(`retention already holds ${name}; refused`);
    fs.renameSync(from, to);
  }
}

function migrateAgentRuntime(home, options = {}) {
  if (!options.workspace) refuseMigration('installation required to migrate an agent runtime');
  const root = path.resolve(home);
  if (!fs.statSync(root, { throwIfNoEntry: false })?.isDirectory()) refuseMigration(`agent folder not found: ${root}`);
  const paths = ignitePaths(root);
  const journalFile = path.join(root, 'runtime', '.ignite-migration.json');
  const completionFile = path.join(root, 'runtime', 'ignite-migration.json');
  const marker = fs.existsSync(paths.marker);
  const legacy = legacyLayout(root);
  if (!marker && orphanSidecar(root)) refuseMigration(`orphan sidecar at ${root}; refused. A sidecar without ${DATABASE_NAME} is not a live store`);
  if (!marker && fs.existsSync(paths.root) && legacy.length) {
    refuseMigration(`ambiguous Ignite layout at ${root}: runtime/ignite exists without ${MARKER_NAME} and legacy files remain; refused`);
  }
  if (!marker && !legacy.length) refuseMigration(`no legacy Ignite store at ${root}; a backup is not a live store`);
  const pendingTools = marker && !legacy.length && ownToolsPending(root);
  if (marker && !legacy.length && !pendingTools) return { ok: true, already: true, changes: [], database: paths.database, command: MIGRATION_COMMAND };
  if (options.interruptAfter && !STAGES.includes(options.interruptAfter)) refuseMigration(`unknown stage: ${options.interruptAfter}`);
  const { acquireLock, releaseLock } = require('./daemon.js');
  const { runtimeFolder } = require('./memory-write.js');
  const lockPath = path.join(runtimeFolder(options.workspace), 'daemon.lock');
  let held;
  let interrupted = null;
  let changes = [];
  let unplaced = false;
  try {
    held = acquireLock(lockPath);
    if (marker && !legacy.length) {
      assertToolsMovable(root);
      assertCheckToolsPlaceable(root, readCheckTools(paths.database));
    } else {
      assertToolsMovable(root);
      assertCheckToolsPlaceable(root, checkToolsFromLegacyCopy(root));
    }
    fs.mkdirSync(path.dirname(migrationGuardPath(root)), { recursive: true });
    fs.writeFileSync(migrationGuardPath(root), `${process.pid}\n`, 'utf8');
    if (options.whileHeld) options.whileHeld();
    changes = marker && !legacy.length
      ? finishOwnTools(root)
      : publishRuntime(root, paths, journalFile, completionFile, options.interruptAfter);
  } catch (error) {
    if (error.interrupted) interrupted = error;
    else {
      if (error.unplaced) unplaced = true;
      throw error;
    }
  } finally {
    try { fs.unlinkSync(migrationGuardPath(root)); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (unplaced) removeEmptyDir(path.join(root, 'runtime'));
    releaseLock(held);
  }
  if (interrupted) throw interrupted;
  return { ok: true, changes, database: paths.database, command: MIGRATION_COMMAND };
}

function checkpoint(journalFile, body, interruptAfter) {
  writeJson(journalFile, body);
  if (interruptAfter === body.stage) {
    const error = new Error(`interrupted after ${body.stage}`);
    error.interrupted = body.stage;
    throw error;
  }
}

function publishRuntime(root, paths, journalFile, completionFile, interruptAfter) {
  if (fs.existsSync(paths.marker)) {
    if (!fs.existsSync(completionFile)) {
      const prior = readJson(journalFile);
      writeJson(completionFile, { id: prior?.id || null, completed: true, command: MIGRATION_COMMAND });
      checkpoint(journalFile, { ...(prior || {}), stage: 'completion-recorded' }, interruptAfter);
    }
    if (legacyLayout(root).length) {
      retireLegacy(root);
      const prior = readJson(journalFile) || {};
      checkpoint(journalFile, { ...prior, stage: 'legacy-retired' }, interruptAfter);
    }
    return;
  }
  const runtimeDir = path.join(root, 'runtime');
  const incoming = fs.existsSync(runtimeDir)
    ? fs.readdirSync(runtimeDir).filter((name) => name.startsWith('.ignite-incoming-'))
    : [];
  const journal = readJson(journalFile);
  if (incoming.length > 1 || (incoming.length === 1 && journal?.id !== incoming[0].slice('.ignite-incoming-'.length))) {
    refuseMigration(`ambiguous staging at ${root}; refused`);
  }
  const id = journal?.id || randomUUID();
  const staging = path.join(runtimeDir, `.ignite-incoming-${id}`);
  if (!fs.existsSync(staging)) {
    const files = legacyFiles(root);
    const before = hashSet(root, files);
    fs.mkdirSync(staging, { recursive: true });
    copyLegacy(root, staging);
    const after = hashSet(root, legacyFiles(root));
    if (!sameHashes(before, after)) {
      fs.rmSync(staging, { recursive: true, force: true });
      refuseMigration('legacy files changed during copy; aborted');
    }
    checkpoint(journalFile, { id, stage: 'staged', hashes: before }, interruptAfter);
  } else if (journal?.hashes && !sameHashes(journal.hashes, hashSet(root, legacyFiles(root)))) {
    refuseMigration('legacy files changed after staging; aborted');
  }
  const recorded = readJson(journalFile);
  if (recorded.stage === 'staged') {
    try {
      validateCopy(staging, root);
    } catch (error) {
      if (error.unplaced) {
        fs.rmSync(staging, { recursive: true, force: true });
        fs.rmSync(journalFile, { force: true });
      }
      throw error;
    }
    const markerFile = path.join(staging, MARKER_NAME);
    const fd = fs.openSync(markerFile, 'w', 0o600);
    try {
      fs.writeFileSync(fd, `MIGRATED ${id}\n`, 'utf8');
      fs.fsyncSync(fd);
    } finally { fs.closeSync(fd); }
    checkpoint(journalFile, { ...recorded, stage: 'validated' }, interruptAfter);
  }
  if (!sameHashes(readJson(journalFile).hashes, hashSet(root, legacyFiles(root)))) {
    refuseMigration('legacy files changed before publish; aborted');
  }
  let changes = [];
  if (!fs.existsSync(paths.root)) {
    changes = placeOwnTools(root);
    fs.renameSync(staging, paths.root);
  }
  checkpoint(journalFile, { ...readJson(journalFile), stage: 'renamed' }, interruptAfter);
  if (!fs.existsSync(completionFile)) {
    writeJson(completionFile, { id, completed: true, command: MIGRATION_COMMAND });
  }
  checkpoint(journalFile, { ...readJson(journalFile), stage: 'completion-recorded' }, interruptAfter);
  retireLegacy(root);
  checkpoint(journalFile, { ...readJson(journalFile), stage: 'legacy-retired' }, interruptAfter);
  return changes;
}

function cmdRuntime(rest, flags, deps) {
  const [verb, ...extra] = rest;
  if (verb !== 'migrate') fail(`runtime requires migrate\nNothing changed.\nignite runtime -h`);
  parseOpts(extra, 'runtime migrate');
  const located = resolveHome(flags, deps);
  if (!located.workspace) fail('runtime migrate requires an installation; pass --installation PATH\nNothing changed.\nignite runtime migrate -h');
  const result = migrateAgentRuntime(located.home, { workspace: located.workspace, slug: located.slug });
  const detail = (result.changes || []).join('\n');
  emit(deps, flags, result, `${detail ? `${detail}\n` : ''}migrated ${located.slug}\n`);
  return 0;
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

module.exports = { main, HELP, VERBS, migrateAgentRuntime };
