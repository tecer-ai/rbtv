'use strict';

// The server core's internal-only API — the ONE door the gateway reaches the
// core through (internal-api-contract-spec.md, ratified D14/D24 Q1a).
//
// Everything here is shaped by ONE bar (DEC-4): a later split into two OS
// processes must be WIRING, not redesign. So:
//   • envelopes are JSON-round-tripped at the boundary in BOTH directions, in
//     process — nothing that cannot survive a socket can quietly cross today;
//   • errors are DATA (typed codes), never exceptions thrown across;
//   • `inspect` results are DETACHED snapshots (the round-trip guarantees it);
//   • the server authenticates its SINGLE client with a real per-boot secret,
//     even though both halves live in one process (DEC-3: localhost is not trust).
//
// The server core RE-runs the COMPLETE dry-run on every mutating intent
// regardless of what the gateway already validated — gateway origin is not trust.

const {
  InternalApiError,
  AUTH_FAILED,
  VERSION_MISMATCH,
  BAD_ENVELOPE,
  UNKNOWN_INTENT,
  VALIDATION_FAILED,
  NOT_FOUND,
  UNAUTHORIZED_SENDER,
  INTERNAL,
} = require('./errors');
const { createAuthzPolicy } = require('./authz');

const ENVELOPE_VERSION = 1;

// The ratified five-intent surface (contract § 1). NEVER a raw spawn command,
// NEVER a raw SQL/store handle. Future intents are ADDED by name under the same
// envelope, each with its own re-validation clause — never by widening an
// existing intent's payload semantics. `snooze` is the fifth, added ADDITIVELY by
// owner ruling D71 (envelope version UNCHANGED) so p4-2's CLI snooze subcommand has
// a gateway path to wrap.
const INTENTS = new Set(['enqueue-job', 'remove-job', 'inspect', 'spawn-via-named-profile', 'snooze']);

const ALLOWED_ENVELOPE_KEYS = new Set(['v', 'id', 'ts', 'auth', 'sender', 'intent', 'payload']);

// ⚑ `auth` is deliberately NOT in the REQUIRED list, even though every well-formed
// envelope carries it. Contract § 4 is explicit: "any call WITHOUT it — any other
// module, any test bypass, any future code path — gets AUTH_FAILED". Requiring it as
// a present key here would answer a MISSING secret with BAD_ENVELOPE, preempting the
// ratified AUTH_FAILED with a syntax error. (This is not hypothetical: it is exactly
// what an earlier cut of this file did, and probe-cli-authfail caught it.) A missing
// credential is an AUTH failure, not a malformed envelope — the absence is handled by
// the auth check below, which is where the contract puts it.
const REQUIRED_ENVELOPE_KEYS = ['v', 'id', 'ts', 'sender', 'intent', 'payload'];

const INSPECT_TARGETS = new Set(['jobs', 'queue', 'status', 'logs']);
// Server-enforced max page (contract § 1, `inspect`: "offset/limit bounded").
const MAX_PAGE = 500;
const DEFAULT_PAGE = 200;

const SENDER_KINDS = new Set(['owner', 'agent', 'bridge']);

// The job schema IS the authoritative field set for the enqueue-job payload
// (contract § 1) — so the wire carries the ratified DDL's own column names, and
// `session_mode` is the wire field D17 fixed. `enqueued_by` is deliberately ABSENT:
// it is NOT a caller field — the gateway stamps it from the authenticated sender
// (spawn-profiles-spec.md:172), and accepting it from the wire would let a sender
// forge its own audit trail.
const ENQUEUE_ALLOWED_KEYS = new Set([
  'job_id', 'args', 'session_mode', 'trigger_kind', 'run_at',
  'repeat_rule', 'interval_seconds', 'max_fires',
  // Validate-only mode (owner ruling D72/D73): opt-in, default false. NOT a job
  // column — it selects a pre-insert exit, it is never written to the queue.
  'dry_run',
]);

// ── Boundary serialization ───────────────────────────────────────────────────
//
// The forced round-trip is what keeps the DEC-4 boundary honest: no shared
// mutable object, no object identity, no closure, and no exception can cross it,
// so nothing in-process can quietly grow a dependency a socket cannot carry.
//
// A bare JSON round-trip is NOT sufficient on its own: JSON.stringify silently
// DROPS functions and undefined rather than throwing, so a live handle could slip
// across as a hole in the data. Hence the explicit assertion walk first — it
// rejects exactly the contract's own forbidden list (functions, class instances,
// live handles, circular refs) LOUDLY instead of laundering them into nulls.
function assertSerializable(value, path = '$', seen = new Set()) {
  const t = typeof value;
  if (value === null || t === 'string' || t === 'number' || t === 'boolean' || t === 'undefined') {
    if (t === 'number' && !Number.isFinite(value)) {
      throw new InternalApiError(BAD_ENVELOPE, `non-finite number at ${path}`, { path });
    }
    return;
  }
  if (t === 'function' || t === 'symbol' || t === 'bigint') {
    throw new InternalApiError(BAD_ENVELOPE, `non-serializable ${t} at ${path}`, { path });
  }
  if (seen.has(value)) {
    throw new InternalApiError(BAD_ENVELOPE, `circular reference at ${path}`, { path });
  }
  seen.add(value);
  if (Array.isArray(value)) {
    value.forEach((v, i) => assertSerializable(v, `${path}[${i}]`, seen));
  } else {
    // A class instance / live handle has a prototype that is neither Object.prototype
    // nor null. Plain data has one of those two. This is the check that catches a
    // store cursor, a child process, a stream, or a Date — every one of which the
    // contract forbids across the boundary.
    const proto = Object.getPrototypeOf(value);
    if (proto !== Object.prototype && proto !== null) {
      throw new InternalApiError(BAD_ENVELOPE, `non-plain object (${value.constructor && value.constructor.name}) at ${path}`, { path });
    }
    for (const [k, v] of Object.entries(value)) assertSerializable(v, `${path}.${k}`, seen);
  }
  seen.delete(value);
}

function roundTrip(value) {
  assertSerializable(value);
  return JSON.parse(JSON.stringify(value));
}

// ── Envelope shape ───────────────────────────────────────────────────────────

function validateEnvelopeShape(env) {
  if (env === null || typeof env !== 'object' || Array.isArray(env)) {
    throw new InternalApiError(BAD_ENVELOPE, 'envelope must be an object');
  }
  for (const key of REQUIRED_ENVELOPE_KEYS) {
    if (!(key in env)) throw new InternalApiError(BAD_ENVELOPE, `envelope missing field: ${key}`, { field: key });
  }
  for (const key of Object.keys(env)) {
    if (!ALLOWED_ENVELOPE_KEYS.has(key)) {
      throw new InternalApiError(BAD_ENVELOPE, `envelope carries unknown field: ${key}`, { field: key });
    }
  }
  if (typeof env.id !== 'string' || env.id.length === 0) {
    throw new InternalApiError(BAD_ENVELOPE, 'envelope id must be a non-empty string', { field: 'id' });
  }
  if (env.payload === null || typeof env.payload !== 'object' || Array.isArray(env.payload)) {
    throw new InternalApiError(BAD_ENVELOPE, 'payload must be an object', { field: 'payload' });
  }
  const s = env.sender;
  if (s === null || typeof s !== 'object' || Array.isArray(s)) {
    throw new InternalApiError(BAD_ENVELOPE, 'sender must be an object', { field: 'sender' });
  }
  if (typeof s.id !== 'string' || s.id.length === 0) {
    throw new InternalApiError(BAD_ENVELOPE, 'sender.id must be a non-empty string', { field: 'sender.id' });
  }
  if (!SENDER_KINDS.has(s.kind)) {
    throw new InternalApiError(BAD_ENVELOPE, `sender.kind must be owner|agent|bridge`, { field: 'sender.kind' });
  }
}

// ── Store-error → wire-code mapping ──────────────────────────────────────────
//
// The store's typed codes are the core's INTERNAL vocabulary; the wire has its
// own ratified, CLOSED set. This is the one place the two meet.
//
// E_QUEUE_ROW_NOT_FOUND -> NOT_FOUND while E_UNKNOWN_JOB -> VALIDATION_FAILED is
// exactly why D66(B) minted a separate store code: "no such CATALOGUE job" and
// "no such QUEUE ROW" are different things and the contract maps them to DIFFERENT
// wire codes — one overloaded code would make this mapping unimplementable.
const STORE_TO_WIRE = new Map([
  ['E_QUEUE_ROW_NOT_FOUND', NOT_FOUND],
  ['E_SESSION_NOT_FOUND', NOT_FOUND],
  ['E_UNKNOWN_JOB', VALIDATION_FAILED],
  ['E_JOB_DISABLED', VALIDATION_FAILED],
  ['E_BAD_ARGS', VALIDATION_FAILED],
  ['E_UNKNOWN_PROFILE', VALIDATION_FAILED],
  ['E_UNKNOWN_TOOL', VALIDATION_FAILED],
  ['E_UNKNOWN_WORKFLOW', VALIDATION_FAILED],
  ['E_BAD_MESSAGE', VALIDATION_FAILED],
  ['E_BAD_TRIGGER', VALIDATION_FAILED],
  ['E_BAD_MODE', VALIDATION_FAILED],
  ['E_UNKNOWN_MODE', VALIDATION_FAILED],
  ['E_HEADED_NOT_CAPABLE', VALIDATION_FAILED],
  ['E_FLAG_INJECTION', VALIDATION_FAILED],
  ['E_WORKDIR_ESCAPE', VALIDATION_FAILED],
  ['E_WORKDIR_MISSING', VALIDATION_FAILED],
  ['E_UNKNOWN_REQUEST_KEY', VALIDATION_FAILED],
  ['E_BAD_REQUEST', VALIDATION_FAILED],
]);

function toWireError(err) {
  if (err instanceof InternalApiError) {
    return { code: err.code, message: err.message, details: err.details };
  }
  const mapped = err && err.code ? STORE_TO_WIRE.get(err.code) : null;
  if (mapped) {
    // `details` names the failing check — the contract's own requirement for
    // VALIDATION_FAILED, and what lets a sender see WHICH check refused it.
    return {
      code: mapped,
      message: err.message,
      details: { check: err.code, ...(err.details && typeof err.details === 'object' ? err.details : {}) },
    };
  }
  // An unmapped throw is a server-core fault. Nothing about it leaks a handle or
  // a stack across the boundary — the message is data, the stack stays here.
  return { code: INTERNAL, message: 'server-core fault', details: null };
}

function createInternalApi({ heartStore, spawnManager, secret, logger = null, authzPolicy = null }) {
  if (typeof secret !== 'string' || secret.length === 0) {
    throw new Error('createInternalApi requires a non-empty per-boot client secret');
  }
  const authz = authzPolicy || createAuthzPolicy();

  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // ── Intent handlers ────────────────────────────────────────────────────────

  function handleEnqueueJob(payload, sender) {
    for (const key of Object.keys(payload)) {
      if (!ENQUEUE_ALLOWED_KEYS.has(key)) {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }
    // `dry_run` is RE-CHECKED here, not trusted from the gateway (DEC-3): a non-boolean
    // is refused before it can flip the write path in either direction. Absent → false.
    if (payload.dry_run !== undefined && typeof payload.dry_run !== 'boolean') {
      throw new InternalApiError(VALIDATION_FAILED, 'dry_run must be a boolean', { check: 'dry_run-shape', field: 'dry_run' });
    }
    const dryRun = payload.dry_run === true;

    // The store re-runs the COMPLETE deterministic dry-run (function in catalogue,
    // args shape, trigger, named profile, session_mode) inside enqueue() and writes
    // NOTHING on any failure — the single place all mutations pass. Under `dryRun` it
    // runs the SAME checks and returns the verdict BEFORE the single-writer insert
    // (owner ruling D73) — the queue is UNCHANGED; nothing is written.
    const result = heartStore.enqueue({
      jobId: payload.job_id,
      args: typeof payload.args === 'string' ? payload.args : JSON.stringify(payload.args ?? {}),
      sessionMode: payload.session_mode,
      triggerKind: payload.trigger_kind,
      runAt: payload.run_at,
      repeatRule: payload.repeat_rule,
      intervalSeconds: payload.interval_seconds,
      maxFires: payload.max_fires,
      // Stamped from the ATTESTED sender, never from the payload (the audit trail
      // into job and session rows — spawn-profiles-spec.md Design 4).
      enqueuedBy: sender.id,
      dryRun,
    });

    // Validate-only verdict — no queue row minted (D72/D73). Reaching here means the
    // store's COMPLETE re-validation PASSED (a failure throws VALIDATION_FAILED,
    // identical to the non-dry_run failure path). The verdict is plain data.
    if (dryRun) {
      return { dry_run: true, valid: true };
    }
    // `jobId` here is the QUEUE-ROW id — see the note on handleRemoveJob. This is
    // the id gateway-cli-spec.md:26 calls "the NEW job id" and feeds straight into
    // remove-job at its test 5.
    return { jobId: result.queue_id };
  }

  function handleRemoveJob(payload, sender) {
    for (const key of Object.keys(payload)) {
      if (key !== 'jobId') {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }
    // ⚑ THE WIRE FIELD IS NAMED `jobId` AND CARRIES A QUEUE-ROW HANDLE. This is a
    // RATIFIED MISNOMER, settled by D69 — do NOT rename it and do NOT "fix" it.
    // The same name means a CATALOGUE SLUG in enqueue-job's REQUEST: one name, two
    // identity spaces, one ratified surface. Settled from five ratified rows:
    // heart-store-spec.md:26 (removal "for a pending queue ROW"), :27 (it "names a
    // queue row that does not exist" -> E_QUEUE_ROW_NOT_FOUND), internal-api-
    // contract-spec.md:110 (the id must be "in a removable STATE" — a catalogue
    // slug has no state, only a row does), gateway-cli-spec.md:26 + :94 test 5 (the
    // id remove-job consumes is the one enqueue-job just MINTED, and a slug is not
    // "new"), and schema.sql:17 (queue.job_id has NO UNIQUE — one slug maps to MANY
    // rows, so a slug-keyed removal could never yield a singular `{ removed: true }`).
    const queueId = payload.jobId;
    if (!Number.isInteger(queueId)) {
      throw new InternalApiError(VALIDATION_FAILED, 'jobId must be an integer queue-row id', { check: 'jobId-shape', field: 'jobId' });
    }

    // The pre-read is CONTRACT-MANDATED, not a convenience: the ratified
    // re-validation clause requires proving the row exists, is in a removable
    // state, and that the attested sender may remove it — none of which is
    // knowable without reading the row (heart-store-spec.md:167 puts both checks
    // on the caller).
    //
    // ⚑ It is NOT the pre-read D68 DECLINED. That declined option read the queue to
    // source the RECURRENCE FIELDS for the sender-facing warning, which races: the
    // row can fire and advance between the read and the delete, printing the WRONG
    // schedule on exactly the destructive act the warning exists for. The recurrence
    // fields below come from removeQueueRow's OWN returned row — the value the
    // delete transaction actually removed — never from this read.
    const row = heartStore.getQueueRow(queueId);
    if (!row) {
      throw new InternalApiError(NOT_FOUND, `queue row not found: ${queueId}`, { check: 'row-exists', jobId: queueId });
    }

    // Removable state = "pending, not in-flight". A row PRESENT in `queue` is
    // pending by construction: the queue holds pending jobs ONLY, and the fire path
    // deletes-or-advances the row atomically under BEGIN EXCLUSIVE, so a row cannot
    // be observed mid-fire (heart-store-spec.md:222 — both take BEGIN EXCLUSIVE, the
    // loser sees the other's committed result). A row whose PRIOR execution is still
    // running is still removable: removal cancels FUTURE fires only and never reaches
    // a live process (:168).
    const decision = authz.canRemoveQueueRow({ sender, row });
    if (!decision.allowed) {
      throw new InternalApiError(UNAUTHORIZED_SENDER, decision.reason, { check: 'authorization', jobId: queueId });
    }

    const removed = heartStore.removeQueueRow({ queueId });

    // ⚑ WIDENED, ADDITIVELY, by owner ruling D68 — `removed: true` REMAINS, so every
    // existing reader keeps working. The recurrence fields ride along because removal
    // on a REPEATING trigger cancels the WHOLE recurring schedule (one row whose
    // run_at advances — there is no per-occurrence row to delete), which is materially
    // more destructive than removing a one-shot. Telling the sender a recurring
    // schedule was cancelled is D21(3) loud feedback and BINDING acceptance, not a
    // nicety — and p4-2's CLI sits ACROSS this wire, so the fields MUST cross it.
    // D68 supersedes D66(A)'s "the wire result stays `{ removed: true }`" sentence.
    return {
      removed: true,
      trigger_kind: removed.trigger_kind,
      repeat_rule: removed.repeat_rule,
      interval_seconds: removed.interval_seconds,
    };
  }

  function pageBounds(payload) {
    const rawOffset = payload.offset ?? 0;
    const rawLimit = payload.limit ?? DEFAULT_PAGE;
    if (!Number.isInteger(rawOffset) || rawOffset < 0) {
      throw new InternalApiError(VALIDATION_FAILED, 'offset must be a non-negative integer', { check: 'paging', field: 'offset' });
    }
    if (!Number.isInteger(rawLimit) || rawLimit <= 0) {
      throw new InternalApiError(VALIDATION_FAILED, 'limit must be a positive integer', { check: 'paging', field: 'limit' });
    }
    // Server-ENFORCED max page: an over-large limit is clamped, never honoured —
    // the sender does not get to choose how much of the core it pulls at once.
    return { offset: rawOffset, limit: Math.min(rawLimit, MAX_PAGE) };
  }

  async function handleInspect(payload) {
    for (const key of Object.keys(payload)) {
      if (!['target', 'id', 'offset', 'limit'].includes(key)) {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }
    const { target } = payload;
    if (!INSPECT_TARGETS.has(target)) {
      throw new InternalApiError(VALIDATION_FAILED, `unknown inspect target: ${target}`, { check: 'inspect-target', field: 'target' });
    }

    if (target === 'jobs') return { target, rows: heartStore.listJobs() };
    if (target === 'queue') return { target, rows: heartStore.listQueue() };

    // status/logs are execution-scoped: `id` is required and must exist (one
    // execution = one session row, D16).
    const id = payload.id;
    if (!Number.isInteger(id)) {
      throw new InternalApiError(VALIDATION_FAILED, `inspect ${target} requires an integer id`, { check: 'id-shape', field: 'id' });
    }
    if (!heartStore.getExecution(id)) {
      throw new InternalApiError(NOT_FOUND, `execution not found: ${id}`, { check: 'id-exists', id });
    }

    if (target === 'status') {
      const s = await spawnManager.status(id);
      // carrierInfo is a live carrier observation; the ratified result is a
      // detached plain-data snapshot, and the round-trip on the way out would
      // reject anything non-plain anyway. Keep the value facts, drop the probe.
      const { carrierInfo, ...snapshot } = s;
      return { target, id, ...snapshot, live: Boolean(s.live) };
    }

    // logs: a BOUNDED CHUNK, never a stream handle. spawnManager.logs() can hand
    // back a live `tail -f` child process in follow mode — a handle the contract
    // forbids across the boundary in both directions — so follow is never asked for
    // here; the API pages over the captured bytes instead.
    const { offset, limit } = pageBounds(payload);
    const chunk = spawnManager.logs(id, { follow: false });
    if (!chunk.exists) return { target, id, lines: [], nextOffset: offset, eof: true };
    const all = String(chunk.data ?? '').split('\n');
    if (all.length && all[all.length - 1] === '') all.pop();
    const lines = all.slice(offset, offset + limit);
    const nextOffset = offset + lines.length;
    return { target, id, lines, nextOffset, eof: nextOffset >= all.length };
  }

  async function handleSpawnViaNamedProfile() {
    // ⚑ THE EXCLUSION FIRES IMMEDIATELY ON ENTRY — before any profile lookup,
    // session_mode check, or headed check. The intent is DROPPED, so a call with ANY
    // input (valid profile, unknown profile, any/missing session_mode) gets this ONE
    // typed D70 exclusion, NEVER VALIDATION_FAILED. Pre-validating first would be
    // unreachable-for-success dead code surfacing an inconsistent error that reads as
    // "the intent works, you gave a bad profile" — the opposite of D70's fail-loud
    // permanent posture. (Simplification applied at p4-1 review, owner-ruled.)
    //
    // ⚑ PERMANENTLY EXCLUDED FROM v1 — owner ruling D70 (2026-07-16). This is a
    // SETTLED posture, NOT an open escalation and NOT a pending ruling. The intent
    // stays REGISTERED in the intent surface (a call reaches this handler and
    // gets a TYPED InternalApiError, never UNKNOWN_INTENT), but it is never
    // implemented or CLI-exposed in v1 — its fail-loud is permanent. D70 chose to
    // DROP the intent from v1 over the two design-inventing alternatives (minting a
    // catalogue job id for direct launches, or carrying a job name in the already-
    // ratified payload), because dropping it closes a seam the spec ALREADY sanctioned
    // an exit for: gateway-cli-spec.md:35 flagged this exact seam at p1-checkpoint with
    // two sanctioned exits, and dropping the intent IS the "narrow p1-4's exposure note
    // to the job path" exit — a closure of a pre-existing known seam, not new design.
    // D70 SUPERSEDES the clause of D34 that described this intent as "materializes an
    // IMMEDIATELY-DUE queue row"; D34's ruling on the ticker-driven fire->row->spawn-
    // updates path (p2-2/p3-1) is UNCHANGED.
    //
    // Why this was never buildable (historical record — all three verified on disk
    // 2026-07-16, still true, kept for the future reader):
    //  1. NO JOB IDENTIFIER. The queue-row path D34 once described for this intent
    //     needs a job id — queue.job_id is `NOT NULL REFERENCES jobs(job_id)`
    //     (schema.sql) and jobs_log.job_id is NOT NULL — but the ratified payload is
    //     `{profile, args?, session_mode?}` and carries none. The contract's OTHER
    //     sanctioned option ("calls the spawn module directly") does not escape it:
    //     D34 makes spawn() a pure UPDATER, so a row must exist first, and
    //     recordExecutionStart also requires jobId.
    //  2. `args` HAS NOTHING TO VALIDATE AGAINST. The clause says args "validate
    //     against the profile's declared parameter schema" — no profile key declares
    //     one (spawn-profiles-spec.md Design 1 § Profile shape).
    //  3. `args` vs THE SPAWN REQUEST SCHEMA. The ratified spawn request is
    //     `{profile, session_mode?, prompt?, workdir?}`, strict and closed with
    //     unknown keys rejected (spawn-profiles-spec.md:162-172) — it has no `args`.
    //
    // Nothing regresses by failing loud here: v1 ships NO caller of this intent
    // (gateway-cli-spec.md:35; D15 scopes the CLI to add-job/remove-job/inspect).
    // Failing LOUD (never a silent no-op, never a false `{sessionId}`) means a caller
    // learns the path is permanently unbuilt instead of believing a worker launched.
    throw new InternalApiError(
      INTERNAL,
      'spawn-via-named-profile is PERMANENTLY EXCLUDED from v1 (owner ruling D70): it is DROPPED from v1 rather ' +
      'than built, because its ratified payload {profile, args?, session_mode?} carries no job identifier while ' +
      'every ratified execution-recording path requires one (queue.job_id is NOT NULL REFERENCES jobs(job_id); ' +
      'jobs_log.job_id is NOT NULL). The intent stays registered but ships no implementation and no CLI caller in ' +
      'v1 (gateway-cli-spec.md:35 / D15).',
      { check: 'excluded-intent', ruling: 'D70' }
    );
  }

  // Snooze a STANDING warning for `minutes`. A MUTATION intent (it serializes at the
  // store's single-writer connection, like enqueue-job/remove-job), added ADDITIVELY
  // by owner ruling D71 under the SAME envelope (contract §1 extension rule) — the
  // envelope version is UNCHANGED. Snooze NEVER clears (D45) — it only suppresses a
  // standing warning's announcement; it does not dismiss/acknowledge/delete.
  function handleSnooze(payload, sender) {
    for (const key of Object.keys(payload)) {
      if (key !== 'kind' && key !== 'subject' && key !== 'minutes') {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }

    // Owner-only (D45/D71): the MASTER may snooze and v1's owner IS the master; a
    // warning is SYSTEM-raised, so there is no sender-"creator" to approximate (unlike
    // remove-job's owner+creator model). The authorization question is asked in the
    // ONE policy module (authz.js), never as a scattered `if` here — a non-owner
    // sender maps onto the ratified UNAUTHORIZED_SENDER wire code.
    const decision = authz.canSnoozeWarning({ sender });
    if (!decision.allowed) {
      throw new InternalApiError(UNAUTHORIZED_SENDER, decision.reason, { check: 'authorization' });
    }

    // minutes→ticks is the STORE's business (D44): pass `minutes` through named fields,
    // never re-implement the arithmetic and never raw SQL here. The store re-validates
    // deterministically (kind/subject non-empty, `minutes` a positive integer →
    // E_BAD_ARGS → VALIDATION_FAILED naming the failing check) and, for a (kind,
    // subject) with NO standing warning, returns null — a CLEAN NO-OP, never an error
    // and never a phantom row (D45; ADX-14).
    const row = heartStore.snoozeWarning({
      kind: payload.kind,
      subject: payload.subject,
      minutes: payload.minutes,
    });

    // Loud, owner-readable feedback (D21(3)), mirroring remove-job's result shape
    // (D23): a hit reports WHAT was snoozed and until WHICH tick; the no-op reports
    // honestly that nothing stood to be snoozed.
    if (!row) {
      return { snoozed: false, kind: payload.kind, subject: payload.subject };
    }
    return {
      snoozed: true,
      kind: row.kind,
      subject: row.subject,
      snoozed_until_tick: row.snoozed_until_tick,
    };
  }

  // ── The single entry point ─────────────────────────────────────────────────

  async function dispatch(requestEnvelope) {
    let env;
    let requestId = null;

    try {
      // Inbound round-trip FIRST. After the split this is where socket framing
      // sits, so a payload that cannot be framed fails here in v1 too — the
      // assertion fires exactly where the socket would.
      env = roundTrip(requestEnvelope);
      validateEnvelopeShape(env);
      requestId = env.id;
    } catch (err) {
      return respond(requestId, null, toWireError(err));
    }

    try {
      // AUTH BEFORE INTENT DISPATCH. The endpoint is never exported globally and
      // the secret is handed to exactly ONE module, so any other holder — another
      // module, a test bypass, a future code path — lands here. This makes "the
      // server authenticates the gateway" (DEC-3) a REAL check even in-process.
      // Compared constant-time: a timing-distinguishable compare on a per-boot
      // secret is a side channel, cheap to close and expensive to reason about later.
      if (typeof env.auth !== 'string' || !constantTimeEquals(env.auth, secret)) {
        log('warn', 'internal API refused a non-gateway caller', { intent: env.intent, senderId: env.sender && env.sender.id });
        throw new InternalApiError(AUTH_FAILED, 'internal API client authentication failed');
      }

      if (env.v !== ENVELOPE_VERSION) {
        throw new InternalApiError(VERSION_MISMATCH, `unsupported envelope version: ${env.v}`, { supported: ENVELOPE_VERSION });
      }

      if (!INTENTS.has(env.intent)) {
        // Distinct from a known intent with a bad payload (VALIDATION_FAILED) — the
        // gateway can tell contract drift from sender error.
        throw new InternalApiError(UNKNOWN_INTENT, `unknown intent: ${env.intent}`, { intent: env.intent });
      }

      let result;
      switch (env.intent) {
        case 'enqueue-job': result = handleEnqueueJob(env.payload, env.sender); break;
        case 'remove-job': result = handleRemoveJob(env.payload, env.sender); break;
        case 'inspect': result = await handleInspect(env.payload); break;
        case 'spawn-via-named-profile': result = await handleSpawnViaNamedProfile(env.payload); break;
        case 'snooze': result = handleSnooze(env.payload, env.sender); break;
      }

      // Outbound round-trip: the snapshot the gateway receives is DETACHED, so
      // mutating it on the gateway side cannot reach server-core state.
      return respond(env.id, roundTrip(result), null);
    } catch (err) {
      const wire = toWireError(err);
      if (wire.code === INTERNAL) {
        log('error', 'internal API fault', { intent: env.intent, error: err.message });
      }
      return respond(env.id, null, wire);
    }
  }

  function respond(id, result, error) {
    return { v: ENVELOPE_VERSION, id: id ?? null, ok: error === null, result: error === null ? result : null, error };
  }

  return { dispatch, ENVELOPE_VERSION, INTENTS };
}

// Length-independent equality. Compares over a fixed span so an early mismatch
// costs the same as a late one.
function constantTimeEquals(a, b) {
  const ab = Buffer.from(String(a), 'utf8');
  const bb = Buffer.from(String(b), 'utf8');
  let diff = ab.length ^ bb.length;
  const n = Math.max(ab.length, bb.length);
  for (let i = 0; i < n; i++) {
    diff |= (ab[i] ?? 0) ^ (bb[i] ?? 0);
  }
  return diff === 0;
}

module.exports = { createInternalApi, ENVELOPE_VERSION, assertSerializable, constantTimeEquals };
