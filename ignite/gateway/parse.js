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
const INTENTS = new Set(['enqueue-job', 'remove-job', 'inspect', 'spawn-via-named-profile', 'snooze']);

const TRIGGER_KINDS = new Set(['scheduled', 'periodic']);
const SESSION_MODES = new Set(['headless', 'headed']);
const INSPECT_TARGETS = new Set(['jobs', 'queue', 'status', 'logs', 'daemon', 'ticker']);

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
  rejectUnknownKeys(payload, new Set(['target', 'id', 'offset', 'limit']), 'inspect');
  if (!INSPECT_TARGETS.has(payload.target)) {
    bad(`inspect target must be jobs|queue|status|logs|daemon|ticker (got "${payload.target}")`, 'target');
  }
  const out = { target: payload.target };

  if (payload.target === 'status' || payload.target === 'logs') {
    const raw = payload.id;
    const id = typeof raw === 'string' && /^\d+$/.test(raw) ? Number(raw) : raw;
    if (!Number.isInteger(id) || id <= 0) bad(`inspect ${payload.target} requires an integer id`, 'id');
    out.id = id;
  } else if (payload.target === 'daemon' || payload.target === 'ticker') {
    if (payload.id !== undefined) bad(`inspect ${payload.target} takes no id`, 'id');
  } else if (payload.id !== undefined) {
    bad(`inspect ${payload.target} takes no id`, 'id');
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
  }
}

module.exports = { parseRequest, INTENTS };
