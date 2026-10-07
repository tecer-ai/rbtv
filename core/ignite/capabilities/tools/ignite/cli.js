#!/usr/bin/env node
'use strict';

// API — entry `ignite`. Home from RBTV_AGENT_HOME, or --agent <slug> + --installation <path>.
// main(argv, deps) → exit code, or a Promise for connect/disconnect/dreamer.
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

const COMMANDS = ['schedule', 'schedules-due', 'work', 'wake', 'post', 'board', 'remember', 'dreamer'];
const REPORTS = new Set(['always', 'when-useful']);

const HELP = `ignite — help

Connect an agent to Slack, run one turn, or let the calling agent
manage itself.

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

Usage
  ignite connect AGENT (--channel-name NAME | --dm)
      [--schedule-json FILE] [--installation PATH] [--dry-run]
  ignite disconnect AGENT [--archive-channel]
      [--installation PATH] [--dry-run]
  ignite turn --request FILE --result FILE

Home: RBTV_AGENT_HOME, or --agent NAME --installation PATH.
  The installation defaults to the directory walk that finds
  .rbtv/config/ignite/config.json.
  manage's four change verbs, and schedule, work, wake, post, board,
  remember, and dreamer, use that agent. Help needs neither value.
  Inside a turn the waking program also sets IGNITE_CONVERSATION.

AGENT on connect and disconnect is a name under
<installation>/.rbtv/agents/, or a path to an agent folder there.

Shared options: --json  -h, --help
connect and disconnect also take --dry-run and --installation.
--json selects JSON on stdout for a success.
A refusal is a message on stderr, exit 1, with or without --json.
-h and --help work before or after the verb, with no setup.

Start: ignite connect AGENT --channel-name NAME
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

Result JSON (written even on failure):
  ok, harness, model, effort, sessionId, exitCode,
  startedAt, endedAt, pid, pidStart, stdoutPath, stderrPath, error?
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

Home: RBTV_AGENT_HOME, otherwise --agent <slug> --installation <path>.
Installation: explicit --installation, otherwise the installation containing the home.
IGNITE_CONVERSATION supplies thread provenance and the alert target inside a turn.
Outside a turn, alerts use this agent's configured channel or owner DM.
--help/-h needs no home. Use -- before literal option-like text.
Success: exit 0, "remembered in <path>", then any warning.
--json: {path, appended, lines, warning}; lines counts bullet lines, warning is null
when none. Failure: exit 1, reason on stderr, or {path, error} on stdout with
--json. Missing or empty text, an unresolved installation root or a filesystem write can fail.

Example: ignite remember "Prefers afternoon appointments"
`;

const DREAMER_HELP = `ignite dreamer — memory consolidation for the whole installation

usage: ignite dreamer run [--installation PATH]
       ignite dreamer enable [--installation PATH] [--json]
       ignite dreamer disable [--installation PATH] [--json]

Enable and disable affect automatic Dreamer operation for the entire
installation, not only the calling agent. Agents must use these commands only
when explicitly requested by the owner. Do not disable Dreamer as a workaround
for an individual agent's problem.

enable
  Sets dreamer.enabled to true in .rbtv/config/ignite/config.json. The running
  service reads it on its next tick and turns on the nightly consolidation
  (03:00 America/Sao_Paulo) and the 48-hour watchdog for every agent.
  When dreamer.model is absent, records ${DREAMER_MODEL.harness} ${DREAMER_MODEL.model} effort ${DREAMER_MODEL.effort} there.
  The result names the model in use. To change it, edit dreamer.model
  (harness, model, effort) in that file.
  Already enabled: nothing is written, and the result says so.

disable
  Sets dreamer.enabled to false. The nightly consolidation and the watchdog
  stop for every agent on the service's next tick. A consolidation already in
  progress is not cancelled. dreamer.model is kept.
  Already disabled: nothing is written, and the result says so.

enable and disable change only dreamer.enabled, and dreamer.model when enable
records it. Every other setting and the schedule stay as they are.
Success: exit 0, the new state in plain text, or with --json
{installation, config, enabled, changed, model, modelRecorded}.
Refusal: exit 1, reason on stderr, nothing written. An unreadable or invalid
configuration is refused.

run
  Runs the nightly consolidation path once and exits. Never loops and never
  waits for 03:00. Does not mark or consume that slot, so the daemon can still
  run it the same night.
  Takes the installation lock .rbtv/runtime/ignite/memory.lock for checks,
  snapshot reads and publication. Releases it before every model call.
  Contention at entry prints a busy result and does not start a run.
  A digest or failure notice is queued on the direct-message agent's outbox.
  digestQueued reports a queued digest; noticeQueued reports a queued failure
  notice. Both are false for quiet, busy, or setup-failure results.
  The running daemon delivers it. Reported conflicts are saved only after
  delivery is confirmed. This command does not confirm delivery, so it leaves
  new conflicts unsaved, the same as an unconfirmed nightly digest.
  Runs even when dreamer.enabled is false, and does not enable it. The result
  says so. Uses dreamer.model; without that key the run is refused.
  Prints one JSON line and nothing else. Exit 0 when the run finished without
  an alert. Exit 1 when the run failed or the lock was busy.

Installation: --installation, otherwise the installation containing RBTV_AGENT_HOME,
or the walk up to .rbtv/config/ignite/config.json. No agent flag. No Slack call.

Examples:
  ignite dreamer enable --installation /path/to/installation
  ignite dreamer disable --installation /path/to/installation
  ignite dreamer run --installation /path/to/installation
`;

const BOARD_HELP = `ignite board — checked short-term memory

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

Home: RBTV_AGENT_HOME, otherwise --agent <slug> --installation <path>.
Installation may be discovered by walking up to .rbtv/config/ignite/config.json.
No Slack access. Reads an existing state.sqlite to refresh Timers and Flags as
part of the board write; never creates a database. --help/-h works without a home. -- ends options.
Success: exit 0, "written <path>", "unchanged <path>" or "closed <subject> in <path>".
Failure: exit 1, reason on stderr; fix the candidate and retry. Validation leaves
the board unchanged. --json emits {path, changed, subject?} or {path, error} on
stdout; path is null if home resolution failed. No interactive prompts.

Examples:
  ignite board write --file "board candidate.md"
  ignite board close "Printer toner reorder" "Order confirmed"
`;

// These verbs keep the detailed guidance that was previously embedded in the
// one-page help. Their pages deliberately need no agent home or installation.
const UNCHANGED_HELP = {
  schedule: `ignite — schedule help

usage: ignite schedule add (--at <ISO datetime with offset> | --cron "<5-field>" --tz <IANA zone> | --every <duration>) --note <text> [--subject <title>] [--report always|when-useful] [--conversation <key>]
       ignite schedule list
       ignite schedule change <id> [same cadence flags] [--note <text>] [--report always|when-useful] [--enabled true|false]
       ignite schedule cancel <id>

Cron requires an explicit --tz. Next occurrence is timezone-aware.
--every is a fixed-interval: elapsed time, no timezone, DST does not move it.
A recurring schedule requires a cadence (--cron or --every). An empty cadence is refused.
Timers on _artifacts/board.md show enabled schedules with a next fire and pending/running wakes.
--subject links the timer to a board subject; omitted means none. Changes keep this association.
Add/change/cancel require a valid <home>/_artifacts/board.md before opening SQLite.
If SQLite commits but board refresh fails, exit 0 reports the id and "committed; board refresh pending" (--json adds warning). Do not repeat the mutation.
The next board write or turn refreshes Timers from SQLite.
`,
  'schedules-due': `ignite — schedules-due help

usage: ignite schedules-due --now <ISO datetime>

Enqueue a fresh conversation with no thread or resumed session; input is the schedule id only.
While one schedule wake is pending, further dues are de-duplicated. Never enqueues for a held or stopped schedule, and never clears a hold.
`,
  work: `ignite — work help

usage: ignite work status [--conversation <key>]
       ignite work retry|resume [<id>]
       ignite work stop <id>

With an id, retry clears only that work hold. With no id, it clears only an agent hold.
stop stops that assignment. It does not cancel schedules and does not clear an agent hold.
`,
  wake: `ignite — wake help

usage: ignite wake --conversation <key> --note <text> [--work <id>]

Worker completion. Enqueues a continuation. Does not clear a hold.
`,
  post: `ignite — post help

usage: ignite post (--text <text> | --text-file <path> | --file <path>)... [--audio] [--thread <thread>]

Without --thread, opens a new thread in the agent's channel. --thread selects an existing conversation in this agent's stored history: its full team:channel:root-ts key or a unique root timestamp. Unknown or ambiguous targets are refused.
The post joins that conversation's history after delivery; its session and prior history stay intact.
Enqueues delivery and activates the target. Prints "<conversation key> activated"; --json returns conversationKey, outboxId, clientMsgId, activated and channel. Exit 0 means queued; errors go to stderr with exit 1. No Slack request or interactive prompt in this command.
Example: ignite post --thread T1:C1:123.456 --text "Check complete"
`,
};

function take(argv, i, flag) {
  const value = argv[i + 1];
  if (value == null || value.startsWith('--')) throw new Error(`${flag} requires a value`);
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

function resolveHome(flags, deps) {
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
    const { positionals } = parseOpts(rest.slice(1));
    const id = positionals[0];
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
  if (!config) fail('post requires installation config');
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
  if (flags.help || !rest.length) {
    emit(deps, { json: false }, null, BOARD_HELP);
    return 0;
  }
  let file = null;
  let store;
  try {
    const [action, ...tail] = rest;
    if (!['write', 'close'].includes(action)) fail('board requires write or close; see ignite board --help');
    const { opts, positionals } = parseOpts(tail);
    if (Object.keys(opts).some((key) => action !== 'write' || key !== 'file')) fail('unsupported board option; see ignite board --help');
    if (action === 'write' && (opts.file?.length !== 1 || positionals.length)) fail('board write requires exactly one --file <path>');
    if (action === 'close' && (positionals.length < 2 || positionals.length > 3)) fail('board close requires <subject> <outcome> [thread]');
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

function resolveDreamerWorkspace(flags, deps) {
  if (flags.installation) return path.resolve(flags.installation);
  const env = deps.env || process.env;
  if (env.RBTV_AGENT_HOME) {
    const found = workspaceFromHome(env.RBTV_AGENT_HOME);
    if (found) return found;
  }
  const found = findWorkspace(env.RBTV_AGENT_HOME ? path.dirname(env.RBTV_AGENT_HOME) : process.cwd());
  if (!found) fail('--installation required');
  return found;
}

// Installation-wide: the daemon reads dreamer.enabled on its next tick. A call
// that asks for the state already in force writes nothing.
function setDreamerEnabled(enabled, flags, deps) {
  const workspace = resolveDreamerWorkspace(flags, deps);
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
  if (flags.help) {
    emit(deps, { json: false }, null, DREAMER_HELP);
    return 0;
  }
  const [verb, ...extra] = rest;
  if (!['run', 'enable', 'disable'].includes(verb) || extra.length) {
    fail('dreamer requires exactly one of run, enable, disable\nNothing changed.\nignite dreamer -h');
  }
  if (verb !== 'run') return setDreamerEnabled(verb === 'enable', flags, deps);
  let enabled = null;
  let result;
  try {
    const workspace = resolveDreamerWorkspace(flags, deps);
    const config = loadConfig(workspace);
    enabled = config.dreamer.enabled === true;
    if (!config.dreamer.model) throw new Error(dreamerModelRequired('to run a consolidation'));
    const daemon = require('./daemon.js');
    const run = deps.runInstalledDreamer || daemon.runInstalledDreamer;
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
    note: enabled === false ? 'dreamer.enabled is false; ran because this command was called' : null,
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
    const { opts, positionals } = parseOpts(rest);
    if (Object.keys(opts).length || !positionals.length) fail('remember requires <text>; use -- before option-like text');
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

function dispatch(command, rest, ctx, flags, deps) {
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
  if (rest.length === 0) fail(`usage: ignite ${['connect', 'disconnect', 'manage', 'turn', ...COMMANDS].join('|')}`);
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
  if (command === 'board') return cmdBoard(tail, flags, deps);
  if (command === 'remember') return cmdRemember(tail, flags, deps);
  if (command === 'dreamer') return cmdDreamer(tail, flags, deps);
  if (!COMMANDS.includes(command)) fail(`unknown command: ${command}\nchoose from connect, disconnect, manage, turn,\nschedule, schedules-due, work, wake, post, board, remember, dreamer\nNothing changed.\nignite -h`);
  if (flags.help) {
    const page = UNCHANGED_HELP[command];
    if (page) {
      emit(deps, { json: false }, null, page);
      return 0;
    }
    // board, remember and dreamer have their own complete pages above.
    if (command === 'board') return cmdBoard(tail, flags, deps);
    if (command === 'remember') return cmdRemember(tail, flags, deps);
    if (command === 'dreamer') return cmdDreamer(tail, flags, deps);
    emit(deps, { json: false }, null, HELP);
    return 0;
  }
  const ctx = openContext(flags, deps, command === 'schedule' && ['add', 'change', 'cancel'].includes(tail[0]));
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

module.exports = { main, HELP };
