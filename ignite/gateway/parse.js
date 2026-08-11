'use strict';

// The gateway's half of the deterministic dry-run (gateway-cli-spec.md § Gateway
// Pipeline, step 3): parse raw sender input into a typed request envelope —
// known intent, required fields present, well-formed trigger, well-formed args.
//
// ⚑ SHAPE ONLY. NO store lookups, NO config lookups. The gateway cannot check
// "does this profile exist" or "is this function in the catalogue" because it holds
// no server config and no queue handle — and it MUST NOT grow one to try. That is
// the server core's SEMANTIC re-validation, and the duplication is the point:
// defense-in-depth means the core re-runs the COMPLETE dry-run regardless of what
// passed here (DEC-3 — gateway origin is not trust).

const { GatewayError, SHAPE_INVALID, UNKNOWN_INTENT } = require('./errors');

// The ratified intent surface the gateway speaks (internal-api-contract-spec.md
// § 1). v1's CLI drives add-job/remove-job/inspect (D15) plus `snooze` (the fifth
// intent, added ADDITIVELY by owner ruling D71 — p4-2's CLI wraps it); the gateway
// also routes `spawn-via-named-profile` because a bridge or a later client may name
// it — the gateway is the internal API's single client and speaks its whole surface.
//
// ⚑ `send-to-session` + `capture-session-screen` (owner ruling D91, p6-3a) are RETIRED by task
// 7.29. The server-owned pty they drove is deleted, tmux holds the headed session, and SSH is
// the human trust boundary — so both are removed from THIS set, from the core's set, and from
// the dispatch switch IN LOCKSTEP (probe-intent-drift.js is the guard a half-done edit cannot
// survive). The reason they were ever added here still binds every future intent: handleRequest
// parses BEFORE it forwards, so a core intent missing from this set is a dead intent.
// ⚑ `kill-session` ADDED by the cli-expansion run (ruling D2, ce-4): exposes the spawn
// module's existing kill surface (TERM → grace → KILL, status → `killed`). Session-scoped
// integer id, on the same coercion path the retired Batch-6 intents used.
// ⚑ `register-job` ADDED by owner ruling 2026-07-25 (task 7.12): the NINTH intent —
// the daemon's first catalogue-WRITE surface. Before it, the only way a job entered
// the `jobs` catalogue was a direct database write on the box, bypassing this parser,
// authorization, validation, and audit entirely.
// ⚑ `deregister-job` ADDED by task 7.364 (F20, issue G-m4-demo-verdict-assembler-0804-1610):
// the TENTH intent — the catalogue's first RETIREMENT surface. Before it, `register-job`
// permanently burnt every id it wrote and a HOMED job outlived the goal tree it names, with
// no CLI path to stop it. Added ADDITIVELY; the envelope version is UNCHANGED.
// ⚑ `live-feed` ADDED by live-session-design.md §1/§4 (owner ruling 2026-08-10): the ELEVENTH
// intent — the direct feed of an owner turn into an already-warm session. It is a new intent
// rather than a new `inspect` target or an `enqueue-job` variant for one reason: it is the one
// verb whose whole value is NOT going through the queue. §4 rejected the queue path by ruling
// (the 0.3–1.9s nudge+tick cost would put the warm total over the 3s target), and an intent that
// enqueues nothing cannot honestly be an enqueue. It reaches ONLY the live-session manager.
// ⚑ `send-message` ADDED by task 7.93 (owner ruling `r-793-unbarred-slot-address-door`,
// 2026-07-30): the addressed-message door the coordination client had nothing to route to. It is
// a new intent rather than an `enqueue-job` variant for the same reason `live-feed` is: its whole
// value is NOT going through the queue — a coordination message between seats is delivered, not
// scheduled, and an intent that enqueues nothing cannot honestly be an enqueue.
// ⚑ THE NAME COINS NOTHING. `send-message` is already this system's ratified word for this act:
// it is a member of the closed `action_type` enum (ACTION_TYPES below) whose required argument set
// is already `(type, thread, corpus)`. One act with both a QUEUED carrier and a DIRECT gateway
// carrier is the shape `launch-agent` (action) / `spawn-via-named-profile` (intent) already has.
// ⚑ IT MINTS NO RECIPIENT AND NO COLUMN. The ADDRESS travels in `thread` — the owner's frozen
// D39/D42 semantics ("the thread CARRIES the address"; "addressing is ONE recipient field — a slot
// address OR a groupchat address — v1 collapses it into the thread column"). `d-team-kit-
// realization`'s divergences (1) explicit recipient addressing and (4) a stored `to:` column STAND
// as substrate facts; the client is adapted to the gateway's shape, the gateway is never taught a
// recipient. The write lands through the already-shipped heartStore.recordMessage — NO store change.
// ⚑ `record-bus-answer` ADDED by task 7.771 (owner ruling 2026-08-11, design
// `one-readiness-predicate.md` § D8): the TWELFTH intent — the owner's Slack reply, recorded on the
// asking seat's coordination bus. Before it the bus kept every question and no reply, so nothing
// mechanical could tell an answered ask from an unanswered one and a seat could walk past the
// owner's question (`engine/execution-record.js#blockAndQueueVerdict`).
// ⚑ WHY A NEW INTENT AND NOT AN `enqueue-job` VARIANT — the owner's ruling, with the alternative it
// beat: `enqueue-job` carrying a `fire-tool` job needs a `config/spawn-profiles.yaml` entry plus a
// CREATE-ONLY `register-job` row on the live box (open issue S-2: no in-place repair, and that box
// already carries two permanently dead ids from exactly this). This is also `live-feed`'s and
// `send-message`'s reason in one line: an intent that enqueues nothing cannot honestly be an
// enqueue — an answer to a waiting human is delivered, not scheduled.
// ⚑ IT IS NOT THE BRIDGE HOLDING A NEW CAPABILITY (`chat-bridge-spec.md` line 26, "no new intent of
// its own"). The bridge makes ONE ordinary authenticated gateway call and holds no spawn path; the
// daemon shells to `coord.py`, which is the same split `live-feed` already carries for the warm
// session manager. Authorization is `kind: bridge` ONLY (`authz.canRecordBusAnswer`) — narrower
// than any sibling here, because forging an owner's answer clears another seat's mechanical hold.
const INTENTS = new Set([
  'enqueue-job', 'remove-job', 'inspect', 'spawn-via-named-profile', 'snooze',
  'kill-session', 'register-job', 'deregister-job', 'live-feed', 'send-message',
  'record-bus-answer',
]);

// A goal id and a seat name, SHAPE ONLY. A deliberate SECOND copy of `bus-ferry.js#SAFE_NAME_RE`,
// for exactly the reason every sibling copy in this file exists: the gateway holds no store, no
// config and no sibling import by design (DEC-4), so it cannot read the constant from the module
// that owns it — and the core re-validates independently (DEC-3), which is the point.
//
// ⚠ THESE TWO TOKENS REACH THE DAEMON FROM AN INTERNET-FACING COMPONENT and become PATH SEGMENTS
// under `.rbtv/goals/`. The anchors are load-bearing: no separator, no `..`, no control character,
// no leading dot, no empty string. Refused here rather than sanitized — a name that needs cleaning
// is a name nobody meant.
const BUS_NAME_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

const TRIGGER_KINDS = new Set(['scheduled', 'periodic']);
const SESSION_MODES = new Set(['headless', 'headed']);
// A deliberate SECOND copy of the schema's closed action_type enum (schema.sql:5-6),
// exactly like SESSION_MODES/TRIGGER_KINDS above: the gateway holds no store or schema
// import by design (DEC-4), so it cannot read the enum from the source of truth. A
// closed enum is SHAPE, so an unknown value is refused here — the same reasoning that
// puts session_mode's enum at the door.
const ACTION_TYPES = new Set(['launch-agent', 'fire-tool', 'start-workflow', 'send-message']);
// A deliberate SECOND copy of the store's closed message-type enum (heart-store.js MESSAGE_TYPES),
// for exactly the reason every sibling copy above exists: the gateway holds no store import by
// design (DEC-4), and a closed enum is SHAPE, so an unknown type is refused at the door. The core
// re-validates it independently (recordMessage's own E_BAD_MESSAGE), which is the point of DEC-3.
const MESSAGE_TYPES = new Set(['completion', 'ask', 'answer', 'verdict', 'note']);
// ⚑ `messages` ADDED by the cli-expansion run (ruling D3, ce-5): a new TARGET of the
// existing `inspect` intent, never a sixth intent — read-only store queries are what
// `inspect` is for. Execution-scoped like `status`/`logs`: the id is a jobs_log exec_id,
// same coercion path; the core resolves the execution's chain-stable thread and returns
// that thread's message rows.
// ⚑ `executions` ADDED by task 7.62: the state-filtered execution listing — again a new TARGET
// of `inspect`, never a ninth intent, for the same ce-5/D75 reason. It is neither fixed-view nor
// execution-SCOPED: it takes no `id` and instead filters the whole jobs_log by `status`, which
// is why `status` joins the allowed payload keys below.
const INSPECT_TARGETS = new Set(['jobs', 'queue', 'status', 'logs', 'daemon', 'ticker', 'messages', 'executions']);

// A deliberate SECOND copy of the schema's closed jobs_log.status enum (schema.sql:65-66),
// exactly like SESSION_MODES / TRIGGER_KINDS / ACTION_TYPES above: the gateway holds no store or
// schema import by design (DEC-4), so it cannot read the enum from the source of truth. A closed
// enum is SHAPE, so an unknown status is refused at the door.
//
// ⚑ THE DRIFT THIS COPY CREATES IS GUARDED, unlike the target set it rides on: probe-inspect-
// executions.js derives the LIVE enum from the database's own DDL and fails loud on any mismatch
// with this constant. Task 7.46 will SPLIT this enum into session-level and turn-level states —
// when it does, the probe fails here first and names the member, which is the point.
const EXEC_STATUSES = new Set(['launching', 'running', 'done', 'blocked', 'failed', 'stalled', 'killed']);

// Fixed-width ISO-8601 UTC. The store's own contract: lexicographic compare must
// equal chronological compare, so "due" checks stay deterministic string compares.
const ISO_UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;

function bad(message, field) {
  throw new GatewayError(SHAPE_INVALID, message, field ? { field } : null);
}

function requireObject(payload) {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) {
    bad('payload must be an object', 'payload');
  }
}

function rejectUnknownKeys(payload, allowed, intent) {
  for (const key of Object.keys(payload)) {
    if (!allowed.has(key)) bad(`${intent}: unknown field "${key}"`, key);
  }
}

function optionalPositiveInt(value, field) {
  if (value === undefined || value === null) return null;
  if (!Number.isInteger(value) || value <= 0) bad(`${field} must be a positive integer`, field);
  return value;
}

// `enqueued_by` is deliberately NOT accepted from a sender: the gateway STAMPS it
// from the authenticated identity (spawn-profiles-spec.md:172, Design 4). A sender
// that could set it could forge the audit trail — so it is refused at shape-check
// rather than quietly overwritten downstream.
const ENQUEUE_KEYS = new Set([
  'job_id', 'args', 'session_mode', 'trigger_kind', 'run_at',
  'repeat_rule', 'interval_seconds', 'max_fires', 'dry_run',
]);

function parseEnqueueJob(payload) {
  requireObject(payload);
  rejectUnknownKeys(payload, ENQUEUE_KEYS, 'add-job');

  if (typeof payload.job_id !== 'string' || payload.job_id.length === 0) {
    bad('add-job requires a non-empty job_id', 'job_id');
  }

  let args = payload.args ?? {};
  if (typeof args === 'string') {
    try {
      args = JSON.parse(args);
    } catch {
      bad('args is not valid JSON', 'args');
    }
  }
  if (args === null || typeof args !== 'object' || Array.isArray(args)) {
    bad('args must be a JSON object', 'args');
  }

  const sessionMode = payload.session_mode ?? 'headless';
  // An unknown mode value is refused HERE (gateway-cli-spec.md behavior row 3:
  // "An unknown mode value -> refused at shape-check"). The closed enum is shape,
  // not semantics — whether the named profile is headed-CAPABLE is the core's call.
  if (!SESSION_MODES.has(sessionMode)) {
    bad(`session_mode must be headless|headed (got "${sessionMode}")`, 'session_mode');
  }

  const triggerKind = payload.trigger_kind;
  if (!TRIGGER_KINDS.has(triggerKind)) {
    bad(`trigger_kind must be scheduled|periodic (got "${triggerKind}")`, 'trigger_kind');
  }
  if (typeof payload.run_at !== 'string' || !ISO_UTC.test(payload.run_at)) {
    bad('run_at must be fixed-width ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ)', 'run_at');
  }

  let repeatRule = payload.repeat_rule ?? null;
  let intervalSeconds = payload.interval_seconds ?? null;

  if (triggerKind === 'periodic') {
    if (!Number.isInteger(intervalSeconds) || intervalSeconds <= 0) {
      bad('a periodic trigger requires a positive interval_seconds', 'interval_seconds');
    }
    if (repeatRule !== null) bad('a periodic trigger must not carry a repeat_rule', 'repeat_rule');
  } else {
    if (intervalSeconds !== null) bad('a scheduled trigger must not carry interval_seconds', 'interval_seconds');
    if (repeatRule !== null && (typeof repeatRule !== 'string' || repeatRule.trim().split(/\s+/).length !== 5)) {
      // Shape only: five whitespace-separated fields. Whether each field is a valid
      // cron expression is the core's deterministic re-validation.
      bad('repeat_rule must be a 5-field cron expression', 'repeat_rule');
    }
  }

  const maxFires = optionalPositiveInt(payload.max_fires, 'max_fires');
  if (maxFires !== null && triggerKind !== 'periodic' && repeatRule === null) {
    bad('max_fires requires a repeating trigger', 'max_fires');
  }

  // `dry_run` (owner ruling D72/D73): validate-only mode — SHAPE ONLY here, a boolean,
  // default false when absent. The gateway forwards it; it does NOT decide dry-run
  // semantics (the core runs the complete re-validation and chooses whether to write).
  // A non-boolean is refused at shape-check, like every other field.
  let dryRun = false;
  if (payload.dry_run !== undefined) {
    if (typeof payload.dry_run !== 'boolean') bad('dry_run must be a boolean', 'dry_run');
    dryRun = payload.dry_run;
  }

  return {
    job_id: payload.job_id,
    args: JSON.stringify(args),
    session_mode: sessionMode,
    trigger_kind: triggerKind,
    run_at: payload.run_at,
    repeat_rule: repeatRule,
    interval_seconds: intervalSeconds,
    max_fires: maxFires,
    dry_run: dryRun,
  };
}

function parseRemoveJob(payload) {
  requireObject(payload);
  rejectUnknownKeys(payload, new Set(['jobId']), 'remove-job');
  // ⚑ The field is NAMED `jobId` and carries a QUEUE-ROW handle — a ratified
  // MISNOMER settled by D69. Keep the name verbatim; do NOT rename it, do NOT
  // "fix" it. (The same name means a catalogue SLUG in add-job's request.)
  const raw = payload.jobId;
  // The CLI passes `ignite remove-job <job-id>` straight from argv, so a numeric
  // string is the normal shape off a terminal; coerce it here — at the ONE place
  // raw sender input is parsed — so the wire always carries the integer the
  // contract means, and the core never has to guess about a string.
  const value = typeof raw === 'string' && /^\d+$/.test(raw) ? Number(raw) : raw;
  if (!Number.isInteger(value) || value <= 0) {
    bad('remove-job requires an integer job id', 'jobId');
  }
  return { jobId: value };
}

function parseInspect(payload) {
  requireObject(payload);
  rejectUnknownKeys(payload, new Set(['target', 'id', 'offset', 'limit', 'status', 'thread']), 'inspect');
  if (!INSPECT_TARGETS.has(payload.target)) {
    bad(`inspect target must be ${[...INSPECT_TARGETS].join('|')} (got "${payload.target}")`, 'target');
  }
  const out = { target: payload.target };

  // ⚑ `thread` ADDED by task 7.93 as an ALTERNATIVE addressing key for `messages` — NOT a new
  // intent, per the ce-5/D75 rule this file already states twice: read-only store queries are what
  // `inspect` is for. It is the read half of the addressed-message door: a tmux seat holds a SLOT
  // ADDRESS and no execution id, so an execution-scoped read is one it can never call
  // (the exact finding task 7.57 fork 1 ruled NOT MET). Exactly one of `id`/`thread` — both, or
  // neither, is refused here rather than one silently winning.
  if (payload.thread !== undefined) {
    if (payload.target !== 'messages') {
      bad(`inspect ${payload.target} takes no thread`, 'thread');
    }
    if (typeof payload.thread !== 'string' || payload.thread.length === 0) {
      bad('inspect messages requires a non-empty thread', 'thread');
    }
    if (payload.id !== undefined) {
      bad('inspect messages takes an id OR a thread, never both', 'thread');
    }
    out.thread = payload.thread;
    if (payload.offset !== undefined) {
      if (!Number.isInteger(payload.offset) || payload.offset < 0) bad('offset must be a non-negative integer', 'offset');
      out.offset = payload.offset;
    }
    if (payload.limit !== undefined) out.limit = optionalPositiveInt(payload.limit, 'limit');
    if (payload.status !== undefined) bad('inspect messages takes no status', 'status');
    return out;
  }

  if (payload.target === 'status' || payload.target === 'logs' || payload.target === 'messages') {
    const raw = payload.id;
    const id = typeof raw === 'string' && /^\d+$/.test(raw) ? Number(raw) : raw;
    if (!Number.isInteger(id) || id <= 0) bad(`inspect ${payload.target} requires an integer id`, 'id');
    out.id = id;
  } else if (payload.target === 'daemon' || payload.target === 'ticker') {
    if (payload.id !== undefined) bad(`inspect ${payload.target} takes no id`, 'id');
  } else if (payload.id !== undefined) {
    bad(`inspect ${payload.target} takes no id`, 'id');
  }

  // `status` belongs to `executions` and to NOTHING else. Both directions are refused: the
  // listing without its filter (an unfiltered whole-jobs_log dump is not what this target is,
  // and defaulting to one silently would be a design invented at the door), and the filter on a
  // target that cannot honour it (accepted-and-ignored is the shape that teaches a caller a
  // filter works when it does not).
  if (payload.target === 'executions') {
    if (typeof payload.status !== 'string' || payload.status.length === 0) {
      bad('inspect executions requires a status', 'status');
    }
    if (!EXEC_STATUSES.has(payload.status)) {
      bad(`inspect executions status must be ${[...EXEC_STATUSES].join('|')} (got "${payload.status}")`, 'status');
    }
    out.status = payload.status;
  } else if (payload.status !== undefined) {
    bad(`inspect ${payload.target} takes no status`, 'status');
  }

  if (payload.offset !== undefined) {
    if (!Number.isInteger(payload.offset) || payload.offset < 0) bad('offset must be a non-negative integer', 'offset');
    out.offset = payload.offset;
  }
  if (payload.limit !== undefined) {
    out.limit = optionalPositiveInt(payload.limit, 'limit');
  }
  return out;
}

function parseSpawnViaNamedProfile(payload) {
  requireObject(payload);
  rejectUnknownKeys(payload, new Set(['profile', 'args', 'session_mode']), 'spawn-via-named-profile');
  if (typeof payload.profile !== 'string' || payload.profile.length === 0) {
    bad('spawn-via-named-profile requires a non-empty profile NAME', 'profile');
  }
  const sessionMode = payload.session_mode ?? 'headless';
  if (!SESSION_MODES.has(sessionMode)) {
    bad(`session_mode must be headless|headed (got "${sessionMode}")`, 'session_mode');
  }
  const out = { profile: payload.profile, session_mode: sessionMode };
  if (payload.args !== undefined) {
    if (payload.args === null || typeof payload.args !== 'object' || Array.isArray(payload.args)) {
      bad('args must be an object', 'args');
    }
    out.args = payload.args;
  }
  return out;
}

// `snooze` (the fifth intent, added ADDITIVELY by owner ruling D71) — SHAPE ONLY,
// like every parse here: kind/subject non-empty strings, minutes a positive integer.
// Whether a standing warning actually EXISTS for (kind, subject) is the CORE's
// semantic re-validation (the gateway holds no store handle), and minutes→ticks is
// the STORE's business (D44) — the gateway forwards `minutes` untouched.
function parseSnooze(payload) {
  requireObject(payload);
  rejectUnknownKeys(payload, new Set(['kind', 'subject', 'minutes']), 'snooze');
  if (typeof payload.kind !== 'string' || payload.kind.length === 0) {
    bad('snooze requires a non-empty kind', 'kind');
  }
  if (typeof payload.subject !== 'string' || payload.subject.length === 0) {
    bad('snooze requires a non-empty subject', 'subject');
  }
  // The CLI passes `--minutes <N>` straight from argv, so a numeric string is the
  // normal shape off a terminal; coerce it HERE — at the one place raw sender input
  // is parsed — so the wire always carries the integer the contract means (mirrors
  // remove-job's jobId / inspect's id coercion).
  const raw = payload.minutes;
  const minutes = typeof raw === 'string' && /^\d+$/.test(raw) ? Number(raw) : raw;
  if (!Number.isInteger(minutes) || minutes <= 0) {
    bad('snooze requires a positive integer minutes', 'minutes');
  }
  return { kind: payload.kind, subject: payload.subject, minutes };
}

// The session-scoped id coercion — SHAPE ONLY, like every parse here. The session id is the
// SAME wire field `inspect` uses for an execution-scoped call, so it gets the SAME numeric-string
// coercion `remove-job`/`inspect` already apply: the CLI passes `ignite <cmd> <id>` straight from
// argv, so a numeric string is the normal shape off a terminal, and coercing HERE — at the one
// place raw sender input is interpreted — means the wire always carries the integer the contract
// means. Introduced for the Batch-6 session-surface intents (D90/D91, both retired by task 7.29);
// `kill-session` is its remaining caller and the coercion is unchanged.
function parseSessionScopedId(raw, intent) {
  const id = typeof raw === 'string' && /^\d+$/.test(raw) ? Number(raw) : raw;
  if (!Number.isInteger(id) || id <= 0) bad(`${intent} requires an integer session id`, 'id');
  return id;
}

// `kill-session` (cli-expansion ruling D2) — SHAPE ONLY, like every parse here. The id is a
// session-scoped integer (a `jobs_log` execution id) on the coercion path above. Whether the row
// exists, who may kill it, and whether anything is left to kill are the core's semantic
// re-validation (DEC-3).
function parseKillSession(payload) {
  requireObject(payload);
  rejectUnknownKeys(payload, new Set(['id']), 'kill-session');
  return { id: parseSessionScopedId(payload.id, 'kill-session') };
}

// `register-job` (the ninth intent, owner ruling 2026-07-25 / task 7.12) — SHAPE ONLY,
// like every parse here. What the gateway CANNOT check, and must not grow a handle to
// try: whether the id is already taken, and anything semantic about how the schema
// interacts with the action type. Both are the core's complete re-validation (DEC-3).
const REGISTER_KEYS = new Set([
  'job_id', 'action_type', 'function', 'args_schema', 'description', 'enabled', 'dry_run',
  // task 7.12 · the job->seat pointer (`r-job-seat-home`). SHAPE ONLY here, like everything else
  // in this file: whether the goal exists, whether it has a live run, and whether the seat is
  // materialized and rostered are resolved at FIRE time against the filesystem — which the gateway
  // holds no handle to and must not grow one to (DEC-3, the no-state-writes bound).
  'goal_name', 'seat_name',
]);

function parseRegisterJob(payload) {
  requireObject(payload);
  rejectUnknownKeys(payload, REGISTER_KEYS, 'register-job');

  if (typeof payload.job_id !== 'string' || payload.job_id.length === 0) {
    bad('register-job requires a non-empty job_id', 'job_id');
  }
  if (!ACTION_TYPES.has(payload.action_type)) {
    bad(`action_type must be launch-agent|fire-tool|start-workflow|send-message (got "${payload.action_type}")`, 'action_type');
  }
  if (typeof payload.function !== 'string' || payload.function.length === 0) {
    bad('register-job requires a non-empty function', 'function');
  }

  // `args_schema` takes the SAME object-or-JSON-string normalization enqueue-job's
  // `args` takes (above), and rides the wire as a canonical JSON string — so the core
  // and the store see one shape regardless of how a client expressed it.
  let argsSchema = payload.args_schema ?? {};
  if (typeof argsSchema === 'string') {
    try {
      argsSchema = JSON.parse(argsSchema);
    } catch {
      bad('args_schema is not valid JSON', 'args_schema');
    }
  }
  if (argsSchema === null || typeof argsSchema !== 'object' || Array.isArray(argsSchema)) {
    bad('args_schema must be a JSON object', 'args_schema');
  }

  let description = null;
  if (payload.description !== undefined && payload.description !== null) {
    if (typeof payload.description !== 'string') bad('description must be a string', 'description');
    description = payload.description;
  }

  let enabled = true;
  if (payload.enabled !== undefined) {
    if (typeof payload.enabled !== 'boolean') bad('enabled must be a boolean', 'enabled');
    enabled = payload.enabled;
  }

  let dryRun = false;
  if (payload.dry_run !== undefined) {
    if (typeof payload.dry_run !== 'boolean') bad('dry_run must be a boolean', 'dry_run');
    dryRun = payload.dry_run;
  }

  // task 7.12 · the job->seat pointer. The both-or-neither rule IS a shape fact — it is decidable
  // from the payload alone with no store and no filesystem — so it is refused at the front door as
  // well as at the writer. The two checks are not redundant: this one turns a malformed wire
  // message away before it reaches the core, and the writer's covers every non-gateway caller.
  let goalName = null;
  if (payload.goal_name !== undefined && payload.goal_name !== null) {
    if (typeof payload.goal_name !== 'string' || payload.goal_name.length === 0) {
      bad('goal_name must be a non-empty string', 'goal_name');
    }
    goalName = payload.goal_name;
  }
  let seatName = null;
  if (payload.seat_name !== undefined && payload.seat_name !== null) {
    if (typeof payload.seat_name !== 'string' || payload.seat_name.length === 0) {
      bad('seat_name must be a non-empty string', 'seat_name');
    }
    seatName = payload.seat_name;
  }
  if ((goalName === null) !== (seatName === null)) {
    bad(
      'goal_name and seat_name are both or neither — a job is only the trigger, and its action is '
      + 'homed as a seat in a goal (r-job-seat-home). Omit both to leave the job unhomed.',
      goalName === null ? 'goal_name' : 'seat_name',
    );
  }

  return {
    job_id: payload.job_id,
    action_type: payload.action_type,
    function: payload.function,
    args_schema: JSON.stringify(argsSchema),
    description,
    enabled,
    goal_name: goalName,
    seat_name: seatName,
    dry_run: dryRun,
  };
}

// `deregister-job` (the tenth intent, task 7.364) — SHAPE ONLY, like every parse here.
// ⚑ `job_id` is a catalogue SLUG and gets NO numeric coercion: `remove-job`'s `jobId`
// carries a queue-row integer (the ratified D69 misnomer) and coerces for that reason.
// A catalogue id named "7" is a legitimate string id, so coercing here would turn a
// valid slug into an integer the store can never match.
// What the gateway CANNOT check and must not grow a handle to try: whether the id is in
// the catalogue at all. That is the core's complete re-validation (DEC-3), and it is the
// discriminating refusal this whole intent exists to have.
function parseDeregisterJob(payload) {
  requireObject(payload);
  rejectUnknownKeys(payload, new Set(['job_id']), 'deregister-job');
  if (typeof payload.job_id !== 'string' || payload.job_id.length === 0) {
    bad('deregister-job requires a non-empty job_id', 'job_id');
  }
  return { job_id: payload.job_id };
}

// live-session-design.md §1 — feed one owner turn to a warm session.
//
// SHAPE ONLY, like every sibling: whether the profile exists, whether the workdir is a seat, and
// whether that seat may run warm are the CORE's questions (DEC-3 complete re-validation) and are
// answered by `liveSessions.eligible`. `exec_id` is the chain's FIRST execution — the core reads
// its `session_ref` and resumes THAT session, which is what makes a warm turn a continuation of
// the same conversation rather than a new one. `start` is the caller saying it is willing to pay
// a cold launch to become warm; without it a cold conversation is answered `no-warm-session` and
// the caller keeps its own path.
function parseLiveFeed(payload) {
  requireObject(payload);
  rejectUnknownKeys(payload, new Set(['conversation', 'prompt', 'workdir', 'profile', 'exec_id', 'start']), 'live-feed');
  for (const key of ['conversation', 'prompt', 'profile']) {
    if (typeof payload[key] !== 'string' || payload[key].length === 0) {
      bad(`live-feed requires a non-empty ${key}`, key);
    }
  }
  if (payload.workdir !== undefined && payload.workdir !== null && typeof payload.workdir !== 'string') {
    bad('live-feed workdir must be a string when present', 'workdir');
  }
  if (payload.exec_id !== undefined && payload.exec_id !== null && !Number.isInteger(payload.exec_id)) {
    bad('live-feed exec_id must be an integer when present', 'exec_id');
  }
  if (payload.start !== undefined && typeof payload.start !== 'boolean') {
    bad('live-feed start must be a boolean when present', 'start');
  }
  return {
    conversation: payload.conversation,
    prompt: payload.prompt,
    workdir: payload.workdir ?? null,
    profile: payload.profile,
    exec_id: payload.exec_id ?? null,
    start: payload.start === true,
  };
}

// `send-message` (task 7.93) — SHAPE ONLY, like every parse here. Three fields, closed set.
//
// ⚑ `sender` is deliberately NOT accepted from a sender, for the SAME reason `enqueued_by` is
// refused on enqueue-job (see ENQUEUE_KEYS above): the daemon STAMPS it from the authenticated
// identity, and a sender that could set it could forge the audit trail. That refusal is what makes
// this door safe to open to an ordinary agent token.
// ⚑ `thread` IS THE ADDRESS (D39/D42) and is a free-form non-empty string here BY DESIGN: whether
// a slot of that name exists, and who may address it, are not shape — the gateway holds no store
// and no roster handle and must not grow one (DEC-3/DEC-4).
function parseSendMessage(payload) {
  requireObject(payload);
  rejectUnknownKeys(payload, new Set(['type', 'thread', 'corpus']), 'send-message');
  if (!MESSAGE_TYPES.has(payload.type)) {
    bad(`send-message type must be ${[...MESSAGE_TYPES].join('|')} (got "${payload.type}")`, 'type');
  }
  if (typeof payload.thread !== 'string' || payload.thread.length === 0) {
    bad('send-message requires a non-empty thread (the address — D39/D42)', 'thread');
  }
  // An empty corpus is legal; a non-string is not. Same bound the store's recordMessage enforces.
  if (typeof payload.corpus !== 'string') {
    bad('send-message requires a string corpus', 'corpus');
  }
  return { type: payload.type, thread: payload.thread, corpus: payload.corpus };
}

// `record-bus-answer` (task 7.771) — SHAPE ONLY, like every parse here. Three fields, closed set.
//
// ⚑ WHAT THE GATEWAY CANNOT CHECK AND MUST NOT GROW A HANDLE TO TRY: whether the goal exists,
// whether the seat is materialized in it, and which ask the answer settles. All three are
// filesystem questions and all three are the CORE's complete re-validation (DEC-3) — see
// `engine/bus-answer.js`. What IS decidable from the payload alone is the SHAPE of the two names,
// and that is refused here as well as there, because a malformed one should never reach the core.
// ⚑ `re` IS NOT A FIELD. The ask id is RESOLVED daemon-side from the goal's own bus through the
// same pairing the mechanical hold makes; accepting one from the wire would let a caller point an
// answer at a question it does not settle.
// ⚑ AN EMPTY CORPUS IS REFUSED, unlike `send-message`'s. That door records a message; this one
// records that a HUMAN ANSWERED, and an empty answer is a row asserting something that did not
// happen — it would clear a seat's hold with no content behind it.
function parseRecordBusAnswer(payload) {
  requireObject(payload);
  rejectUnknownKeys(payload, new Set(['goal', 'seat', 'corpus']), 'record-bus-answer');
  for (const key of ['goal', 'seat']) {
    if (typeof payload[key] !== 'string' || !BUS_NAME_RE.test(payload[key])) {
      bad(`record-bus-answer ${key} must be a bare name — letters, digits, '.', '_' or '-', starting alphanumeric (no path separators, no "..", no control characters)`, key);
    }
  }
  if (typeof payload.corpus !== 'string' || payload.corpus.trim().length === 0) {
    bad('record-bus-answer requires a non-empty corpus (the owner\'s words)', 'corpus');
  }
  return { goal: payload.goal, seat: payload.seat, corpus: payload.corpus };
}

// Raw sender input -> a typed request payload, or a typed refusal. This is the
// ONLY function in the daemon that interprets raw sender input.
function parseRequest({ intent, payload }) {
  if (!INTENTS.has(intent)) {
    throw new GatewayError(UNKNOWN_INTENT, `unknown intent: ${intent}`, { intent });
  }
  switch (intent) {
    case 'enqueue-job': return parseEnqueueJob(payload);
    case 'remove-job': return parseRemoveJob(payload);
    case 'inspect': return parseInspect(payload);
    case 'spawn-via-named-profile': return parseSpawnViaNamedProfile(payload);
    case 'snooze': return parseSnooze(payload);
    case 'kill-session': return parseKillSession(payload);
    case 'register-job': return parseRegisterJob(payload);
    case 'deregister-job': return parseDeregisterJob(payload);
    case 'live-feed': return parseLiveFeed(payload);
    case 'send-message': return parseSendMessage(payload);
    case 'record-bus-answer': return parseRecordBusAnswer(payload);
  }
}

// INSPECT_TARGETS and EXEC_STATUSES are exported as DATA for probe-inspect-executions.js (task
// 7.62), for the same reason dispatch.js exports INTENTS for the 7.16 lockstep guard: a drift
// probe must compare the modules' own constants, NEVER regex over source text (7.16's ruled
// construction requirement — a false-alarming probe gets ignored, which is worse than no probe).
module.exports = { parseRequest, INTENTS, INSPECT_TARGETS, EXEC_STATUSES };
