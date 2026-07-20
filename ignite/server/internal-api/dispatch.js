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
const { appendKeystrokeRecord, appendScreenReadRecord, appendKillRecord } = require('./keys-audit');

const ENVELOPE_VERSION = 1;

// The ratified intent surface (contract § 1). NEVER a raw spawn command,
// NEVER a raw SQL/store handle. Future intents are ADDED by name under the same
// envelope, each with its own re-validation clause — never by widening an
// existing intent's payload semantics. `snooze` is the fifth, added ADDITIVELY by
// owner ruling D71 (envelope version UNCHANGED) so p4-2's CLI snooze subcommand has
// a gateway path to wrap.
//
// `send-to-session` + `capture-session-screen` are the SIXTH and SEVENTH, added
// ADDITIVELY by owner ruling D90 (p6-3a) under the SAME §1 extension rule — the
// Batch-6 session surface. Each carries its OWN complete re-validation clause and its
// OWN authz decision; the ENVELOPE VERSION IS UNCHANGED (the extension rule is explicit
// that adding an intent never bumps it), and no existing intent's payload semantics move.
//
// ⚑ Screen capture is a SEPARATE INTENT, deliberately — it MUST NOT ride `inspect` as a
// new `target: screen`. `inspect`'s ratified target set is jobs|queue|status|logs; adding
// to it would be "widening an existing intent's payload semantics", which the extension
// rule forbids. A separate intent is the RATIFIED shape (D90), not a style preference.
// `kill-session` is the EIGHTH, added ADDITIVELY by the cli-expansion run (ruling D2,
// ce-4) under the SAME §1 extension rule: it exposes the spawn module's EXISTING kill
// surface (TERM → grace → KILL of the whole tree, status → `killed`) on the wire, with
// its OWN complete re-validation clause and its OWN authz decision (D65(B) — the same
// model as remove-job's cancel). The ENVELOPE VERSION IS UNCHANGED and no existing
// intent's payload semantics move.
const INTENTS = new Set([
  'enqueue-job', 'remove-job', 'inspect', 'spawn-via-named-profile', 'snooze',
  'send-to-session', 'capture-session-screen', 'kill-session',
]);

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

// ⚑ `messages` ADDED by the cli-expansion run (ruling D3, ce-5): a new read-only TARGET
// of `inspect`, ruled a target rather than a ninth intent — read-only store queries are
// what `inspect` is for, and a separate intent would duplicate its plumbing. (Contrast
// the D90 note above: screen capture is a LIVE pty read, not a store query, which is why
// IT is a separate intent.) Execution-scoped like `status`/`logs` — the id is a jobs_log
// exec_id; the handler resolves the execution's chain-stable thread and returns that
// thread's message rows, paged.
const INSPECT_TARGETS = new Set(['jobs', 'queue', 'status', 'logs', 'daemon', 'ticker', 'messages']);
// Server-enforced max page (contract § 1, `inspect`: "offset/limit bounded").
const MAX_PAGE = 500;
const DEFAULT_PAGE = 200;

// Server-enforced max keystroke payload for `send-to-session` (contract § 1's
// bounded-payload precedent — the same principle `inspect` applies to a page: the sender
// does not get to choose how much it pushes through the core in one call).
//
// The VALUE is grounded in the mechanism this intent actually drives, not picked round:
// sendKeys writes to the pty bridge's STDIN, which is a PIPE (pty-host.js attachBridge —
// stdio ['pipe','pipe','pipe']). POSIX guarantees a write of at most PIPE_BUF bytes to a
// pipe is ATOMIC, and PIPE_BUF is 4096 on this platform (/usr/include/linux/limits.h:14,
// `getconf PIPE_BUF` — both verified on the deploy box). At or below it, two concurrent
// send-to-session calls CANNOT interleave their keystrokes into one live TUI; above it the
// kernel may split a write and a second sender's bytes can land mid-command.
//
// ⚑ REJECTS, never CLAMPS — deliberately UNLIKE `inspect`'s pageBounds. Clamping a READ
// page is safe: the sender simply pages on via nextOffset, and no state changes. Clamping
// a WRITE is DESTRUCTIVE: the truncated head of a command still reaches a LIVE tty and
// executes there. An over-long payload is refused typed, and nothing is written.
const MAX_KEYS_BYTES = 4096;

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
  // The pty host's liveness refusal (server/pty/errors.js) — the ONLY typed code the two
  // Batch-6 session-surface intents can raise from below. WITHOUT this row the map is a
  // CLOSED literal Map that does not match it, so toWireError() below degrades it to
  // { code: INTERNAL, message: 'server-core fault' } — and a sender could not tell "you sent
  // keys to a session that is no longer live" from "the daemon broke". VALIDATION_FAILED,
  // not NOT_FOUND: reaching sendKeys/captureScreen means the execution row EXISTS (the
  // re-validation clause proved it) — what refused is the liveness CHECK, and `details.check`
  // names it. Same shape as E_BAD_MODE / E_HEADED_NOT_CAPABLE, the other state refusals.
  ['E_SESSION_NOT_LIVE', VALIDATION_FAILED],
  // The spawn module's carrier refusal — through THIS dispatch it is reachable ONLY from
  // `kill-session` (the one intent that calls into the spawn manager: spawn-via-named-profile
  // is D70-excluded before any spawn call, and inspect status/logs never throw it). spawn.kill
  // raises it for a row with NO usable carrier metadata — a row that never reached spawn, or
  // whose carrier identity was lost — so there is no process to signal. VALIDATION_FAILED, not
  // NOT_FOUND: the execution row EXISTS (the re-validation clause proved it); what refused is a
  // state check on the row, and `details.check` names it. Same shape as E_SESSION_NOT_LIVE.
  ['E_CARRIER_FAILED', VALIDATION_FAILED],
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

function createInternalApi({ heartStore, spawnManager, secret, logger = null, authzPolicy = null, daemonStartTime = null, daemonConfig = null, ptyHost = null }) {
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

  async function handleInspectDaemon() {
    const lastTick = heartStore.getLastTick();
    const liveRows = heartStore.listExecutionsByStatus('running')
      .concat(heartStore.listExecutionsByStatus('launching'));
    const liveAgentSessions = liveRows.filter((r) => r.action_type === 'launch-agent').length;

    const queueRows = heartStore.listQueue();
    const warnings = heartStore.listWarnings({ standingOnly: true });

    const configKnobs = daemonConfig || {};
    const uptimeMs = daemonStartTime ? Date.now() - daemonStartTime : null;

    return {
      target: 'daemon',
      pid: process.pid,
      uptime_ms: uptimeMs,
      last_tick: lastTick ? lastTick.tick : null,
      live_agent_sessions: liveAgentSessions,
      max_live_agent_sessions: configKnobs.max_live_agent_sessions ?? 2,
      queue_depth: queueRows.length,
      standing_warnings: warnings.map((w) => ({
        id: w.warning_id,
        kind: w.kind,
        subject: w.subject,
        raised_at_tick: w.raised_at_tick,
        snoozed_until_tick: w.snoozed_until_tick,
      })),
      config: {
        tick_interval_ms: configKnobs.tick_interval_ms ?? 10000,
        stall_warn_ticks: configKnobs.stall_warn_ticks ?? 12,
        stall_halt_ticks: configKnobs.stall_halt_ticks ?? 24,
        slot_max_repeats: configKnobs.slot_max_repeats ?? 10,
        max_live_agent_sessions: configKnobs.max_live_agent_sessions ?? 2,
      },
    };
  }

  function handleInspectTicker() {
    const lastTick = heartStore.getLastTick();
    const tickRows = [];
    if (lastTick) {
      const lastN = lastTick.tick;
      for (let n = lastN; n > 0 && tickRows.length < 10; n--) {
        const t = heartStore.getTick(n);
        if (t) tickRows.push({ tick: t.tick, actions: safeParseActionsJson(t.actions_json) });
      }
    }

    const liveRows = heartStore.listExecutionsByStatus('running')
      .concat(heartStore.listExecutionsByStatus('launching'));
    const liveSessions = liveRows.map((r) => ({
      exec_id: r.exec_id,
      status: r.status,
      action_type: r.action_type,
      job_id: r.job_id,
      queue_id: r.queue_id,
      fired_tick: r.fired_tick,
      thread: r.thread,
    }));

    const queueRows = heartStore.listQueue();
    const dueSoon = queueRows.filter((r) => r.run_at !== undefined).slice(0, 20);

    // getMessages orders msg_id ASC; its `limit` is a HEAD bound and the store
    // exposes no thread filter and no DESC order (read-only surface — no store
    // change here, D75). Passing a limit here would take the OLDEST N messages,
    // then filter owner-feed within them — so once the head fills with non-feed
    // messages the "recent" notes silently vanish. Fetch all, filter, take the
    // tail: the 10 most-recent owner-feed notes. v1-scale only (loads all rows).
    const allMessages = heartStore.getMessages();
    const ownerFeedNotes = allMessages
      .filter((m) => m.thread === 'owner-feed')
      .slice(-10)
      .map((m) => ({
        msg_id: m.msg_id,
        type: m.type,
        corpus: m.corpus,
        created_at: m.created_at,
      }));

    const configKnobs = daemonConfig || {};

    return {
      target: 'ticker',
      recent_ticks: tickRows,
      live_sessions: liveSessions,
      queue_rows: dueSoon.map((r) => ({
        queue_id: r.queue_id,
        job_id: r.job_id,
        run_at: r.run_at,
        trigger_kind: r.trigger_kind,
      })),
      owner_feed_notes: ownerFeedNotes,
      config: {
        tick_interval_ms: configKnobs.tick_interval_ms ?? 10000,
        stall_warn_ticks: configKnobs.stall_warn_ticks ?? 12,
        stall_halt_ticks: configKnobs.stall_halt_ticks ?? 24,
        slot_max_repeats: configKnobs.slot_max_repeats ?? 10,
        max_live_agent_sessions: configKnobs.max_live_agent_sessions ?? 2,
      },
    };
  }

  function safeParseActionsJson(json) {
    try { return JSON.parse(json); } catch { return json; }
  }

  async function handleInspect(payload) {
    for (const key of Object.keys(payload)) {
      if (!['target', 'id', 'offset', 'limit'].includes(key)) {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }
    const { target } = payload;
    if (!INSPECT_TARGETS.has(target)) {
      throw new InternalApiError(VALIDATION_FAILED, `unknown inspect target: ${target} (known: jobs, queue, status, logs, daemon, ticker, messages)`, { check: 'inspect-target', field: 'target' });
    }

    if (target === 'jobs') return { target, rows: heartStore.listJobs() };
    if (target === 'queue') return { target, rows: heartStore.listQueue() };
    if (target === 'daemon') return handleInspectDaemon();
    if (target === 'ticker') return handleInspectTicker();

    // status/logs/messages are execution-scoped: `id` is required and must exist
    // (one execution = one session row, D16).
    const id = payload.id;
    if (!Number.isInteger(id)) {
      throw new InternalApiError(VALIDATION_FAILED, `inspect ${target} requires an integer id`, { check: 'id-shape', field: 'id' });
    }
    const execRow = heartStore.getExecution(id);
    if (!execRow) {
      throw new InternalApiError(NOT_FOUND, `execution not found: ${id}`, { check: 'id-exists', id });
    }

    if (target === 'messages') {
      // The message rows of this execution's chain-stable thread (cli-expansion
      // ruling D3, ce-5). The thread is NEVER re-derived here: getExecution()
      // already attaches it via the store's ONE derivation (_chainThread — D24
      // Q3a: `exec-<exec_id of the chain's FIRST execution>`, carried unchanged
      // across recycles), and re-implementing that walk would smear the
      // arithmetic across call sites (D44).
      //
      // Fetch-all-then-filter mirrors handleInspectTicker's owner-feed read
      // above, for the SAME reason: getMessages() orders msg_id ASC and exposes
      // no thread filter (read-only surface — no store change, D75), and passing
      // its HEAD-bound `limit` would page over the WRONG set. v1-scale only.
      // The page bound is server-ENFORCED on the filtered set, same clamp as
      // `logs` (contract § 1: offset/limit bounded).
      const { offset, limit } = pageBounds(payload);
      const all = heartStore.getMessages().filter((m) => m.thread === execRow.thread);
      const rows = all.slice(offset, offset + limit);
      const nextOffset = offset + rows.length;
      return { target, id, thread: execRow.thread, rows, nextOffset, eof: nextOffset >= all.length };
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

  // ── The Batch-6 session surface (owner ruling D90; contract §1 extension rule) ──────
  //
  // Two intents that let a SEPARATE process drive a live headed session THROUGH the daemon,
  // keeping the daemon the sole keystroke mediator and the single audit point. Task 6.3's
  // attach client is the intended caller. Nothing here streams: the contract's §3 boundary
  // prohibition forbids a pty handle, a stream, or an emitter crossing in EITHER direction,
  // so keystroke bytes cross INBOUND as data and the screen crosses OUTBOUND as a detached
  // value snapshot — the `inspect logs` precedent (a bounded chunk, never a stream handle).

  // The pty host is threaded in by the composition root (index.js). Its absence is a WIRING
  // fault, never a sender error — fail LOUD as a server-core fault rather than let the
  // session surface look present-but-broken. (The internal-api probes construct the API
  // without a pty host; they call neither intent, and this keeps that honest.)
  function requirePtyHost(intentName) {
    if (!ptyHost) {
      throw new InternalApiError(
        INTERNAL,
        `${intentName} requires the pty host; the composition root did not thread it into createInternalApi`,
        { check: 'pty-host-wired' },
      );
    }
  }

  // The COMPLETE session-target re-validation both intents run, server-side, on EVERY call,
  // regardless of what the gateway already validated (DEC-3: gateway origin is not trust).
  // Deterministic, no LLM. The single principal RESOLVER lives in authz.js and is reused, so
  // this is one clause invoked in full by each intent — never a second authorization model.
  function revalidateSessionTarget(payload, sender, intentName) {
    // ⚑ THE ID FIELD IS `id` — the SAME wire field `inspect` already uses for an
    // execution-scoped call, carrying the SAME integer jobs_log.exec_id (one execution = one
    // session row, D16). D23: the surface already names this thing, so no synonym is minted.
    // It is NOT `jobId` — that is remove-job's RATIFIED queue-row misnomer (D69), a different
    // identity space (queue.job_id has no UNIQUE; one slug maps to many rows). It is NOT
    // `sessionId` — jobs_log.session_id is a distinct TEXT column (schema.sql:62), the
    // holder/session-id string, not this integer.
    const id = payload.id;
    if (!Number.isInteger(id)) {
      throw new InternalApiError(VALIDATION_FAILED, `${intentName} requires an integer id`, { check: 'id-shape', field: 'id' });
    }
    const row = heartStore.getExecution(id);
    if (!row) {
      throw new InternalApiError(NOT_FOUND, `execution not found: ${id}`, { check: 'id-exists', id });
    }

    // Authorization BEFORE the mode/liveness checks — remove-job's own order (existence, then
    // authorization). An unauthorized sender therefore learns only that the id exists, never
    // whether the session is headed or live.
    const decision = authz.canDriveSession({ sender, row });
    if (!decision.allowed) {
      throw new InternalApiError(UNAUTHORIZED_SENDER, decision.reason, { check: 'authorization', id });
    }

    // Headed-only: JOIN/TAKE-OVER exist only for a session that runs inside a server-owned pty
    // (D7/D17). A headless session's id is refused by a CHECK, not by a fault.
    if (row.session_mode !== 'headed') {
      throw new InternalApiError(
        VALIDATION_FAILED,
        `session ${id} is session_mode:${row.session_mode} — the session surface is headed-only (D7/D17)`,
        { check: 'session-mode', field: 'id', id, session_mode: row.session_mode },
      );
    }
    return row;
  }

  // Write keystroke bytes into a live headed session's pty — the keystroke rung (CMP-9).
  function handleSendToSession(payload, sender) {
    for (const key of Object.keys(payload)) {
      if (key !== 'id' && key !== 'data') {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }
    requirePtyHost('send-to-session');

    // The bytes cross as DATA (§3 prohibition: no pty handle, no stream, no emitter). `data`
    // is the name pty-host.js's sendKeys already gives this argument — D23: use the existing
    // term, never an alias.
    const data = payload.data;
    if (typeof data !== 'string') {
      throw new InternalApiError(VALIDATION_FAILED, 'data must be a string of keystroke bytes', { check: 'data-shape', field: 'data' });
    }
    const bytes = Buffer.byteLength(data, 'utf8');
    if (bytes === 0) {
      throw new InternalApiError(VALIDATION_FAILED, 'data must be a non-empty keystroke payload', { check: 'data-bound', field: 'data', bytes });
    }
    if (bytes > MAX_KEYS_BYTES) {
      throw new InternalApiError(
        VALIDATION_FAILED,
        `data is ${bytes} bytes; the server-enforced max keystroke payload is ${MAX_KEYS_BYTES}`,
        { check: 'data-bound', field: 'data', bytes, max: MAX_KEYS_BYTES },
      );
    }

    const row = revalidateSessionTarget(payload, sender, 'send-to-session');

    // ⚑ A row carrying NO log_path NEVER REACHED SPAWN, so it cannot possibly have a live pty.
    // That is the LIVENESS refusal — answer the SAME typed code the pty host would, never "the
    // audit could not be written". Without this the audit below (which sits beside that very
    // log) would fail first and mis-report a dead session as a server fault: found by the C3(b)
    // check when the audit landed, and fixed here rather than by loosening the check.
    //
    // Deliberately NARROW — this is a structural fact about the row (no transcript log ⇒ never
    // spawned), NOT a general liveness check. Real liveness stays the pty host's ONE authority:
    // a row that DID spawn and has since died still flows to sendKeys below and gets its
    // E_SESSION_NOT_LIVE through the STORE_TO_WIRE map. The wire shape is identical either way.
    if (typeof row.log_path !== 'string' || row.log_path.length === 0) {
      throw new InternalApiError(
        VALIDATION_FAILED,
        `no live headed pty for session ${row.exec_id} (the row never spawned: it carries no transcript log)`,
        { check: 'E_SESSION_NOT_LIVE', execId: row.exec_id },
      );
    }

    // ── THE KEYSTROKE AUDIT (owner rulings D92/D93) ──────────────────────────────
    //
    // ⚑ BEFORE the pty write, and FAIL-CLOSED. The daemon mediates keystrokes rather than
    // handing out a pty precisely BECAUSE mediation preserves an audit point; delivering a
    // keystroke this file did not record would void that justification.
    //
    // The ORDER is a security property, not a style choice. Auditing AFTER delivery would hand
    // an attacker a real bypass: fill the disk -> the audit write fails -> but the keystrokes
    // already landed -> un-audited injection. Written first, a failed audit means NOTHING was
    // ever delivered.
    //
    // ⚑ WHAT AN ENTRY MEANS (D93 leaves this to the build; stated here): an entry records a
    // burst the daemon ACCEPTED for delivery — D93's own word. A request refused by the strict
    // schema, the byte bound, the re-validation clause, or authz is NEVER written, so the file
    // is not a log of attempts. The one over-record this ordering admits: a burst accepted here
    // and THEN refused by the liveness check below (E_SESSION_NOT_LIVE) leaves an entry for
    // bytes no TUI received. That trade is deliberate — for an audit, UNDER-recording (a
    // delivered keystroke with no record) is the fatal direction; an over-record is visible,
    // harmless, and correlatable against the typed refusal the sender received.
    let audited;
    try {
      audited = appendKeystrokeRecord({
        logPath: row.log_path,
        execId: row.exec_id,
        sessionId: row.session_id,
        sender,          // the ATTESTED sender — D93: a record without attribution answers nothing
        data,
      });
    } catch (err) {
      // Loud, and the keystrokes do NOT go through. An InternalApiError carries its own message
      // to the wire (toWireError passes it verbatim), so the sender learns the daemon refused —
      // never the opaque generic 'server-core fault' the unmapped path would give.
      log('error', 'send-to-session REFUSED: the keystroke audit could not be written — no keys were delivered', {
        execId: row.exec_id, senderId: sender.id, error: err.message,
      });
      throw new InternalApiError(
        INTERNAL,
        `send-to-session refused: the keystroke audit could not be written (${err.message}). No keystrokes were delivered — ` +
        `the daemon does not deliver un-audited input (owner rulings D92/D93).`,
        { check: 'keys-audit' },
      );
    }

    // LIVE is the pty host's own check: with no attached/live bridge it raises the TYPED
    // E_SESSION_NOT_LIVE — never a hang (Behavior #11) — and the STORE_TO_WIRE row above
    // carries it to the wire AS ITSELF instead of degrading it to INTERNAL.
    const res = ptyHost.sendKeys(row.exec_id, data);
    log('info', 'keystrokes delivered to a headed session', { execId: row.exec_id, senderId: sender.id, bytes: res.wrote, audit: audited.auditPath });
    return { id: row.exec_id, wrote: res.wrote };
  }

  // Return the session's current rendered screen from the server-side vt model.
  function handleCaptureSessionScreen(payload, sender) {
    for (const key of Object.keys(payload)) {
      if (key !== 'id') {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }
    requirePtyHost('capture-session-screen');
    const row = revalidateSessionTarget(payload, sender, 'capture-session-screen');

    // ⚑ SAME NARROW STRUCTURAL GUARD send-to-session carries, for the SAME reason (the C3(b)
    // finding): a row with NO log_path never reached spawn, so it has no pty AND no place to put
    // an audit record. Without this, the audit below would fail FIRST and mis-report a never-
    // spawned session as an audit fault instead of the liveness refusal it is. Deliberately NARROW
    // — real liveness stays the pty host's ONE authority (see D96 below).
    if (typeof row.log_path !== 'string' || row.log_path.length === 0) {
      throw new InternalApiError(
        VALIDATION_FAILED,
        `no live headed pty for session ${row.exec_id} (the row never spawned: it carries no transcript log)`,
        { check: 'E_SESSION_NOT_LIVE', execId: row.exec_id },
      );
    }

    // ── THE SCREEN-READ AUDIT (owner ruling D94) ─────────────────────────────────
    //
    // ⚑ BEFORE the capture, and FAIL-CLOSED — the SAME posture as the keystroke path, but this is
    // NOT reasoned from symmetry with it. It is reasoned from the BYPASS D94 exists to close:
    //
    //   D94 exists because a rendered screen can expose the SAME typed secret the keystroke audit
    //   attributes, so the cheap way to steal a credential is to READ it, not type it. If the
    //   audit were written AFTER the capture (or best-effort), an attacker fills the disk -> the
    //   audit write fails -> the screen is served anyway -> a secret leaves the daemon with NO
    //   record of who took it. That is precisely, and exactly, the hole D94 was ruled to close —
    //   re-opened by the ordering. Written first, a failed audit means NO screen was ever served.
    //
    // THE TRADE, STATED (it is real, not hypothetical): a full disk — or a loosened audit mode —
    // now disables READS too, not just writes. The attach client (task 6.3) goes blind rather than
    // reading un-recorded. That is the correct direction for an ATTRIBUTION record: an audit an
    // attacker can defeat by filling a disk is not an audit, and availability of a screen-read
    // surface is worth less than the attributability of every secret that leaves through it.
    // ⚑ But see the volume note on the audit's growth (D95 leaves it UNBOUNDED and 6.3 will POLL
    // this intent): fail-closed + unbounded means the audit's OWN growth can eventually disable
    // the surface. That interaction is SURFACED for tasks 6.3 and 7.5; it is not resolved here,
    // and it does NOT justify a fail-open read (which would reopen the bypass).
    //
    // The over-record this ordering admits: a read audited here and THEN refused by the liveness
    // check below leaves an entry for a screen no sender received. Deliberate, and the same trade
    // the keystroke path takes — for an audit, UNDER-recording is the fatal direction; an
    // over-record is visible, harmless, and correlatable against the typed refusal.
    try {
      appendScreenReadRecord({
        logPath: row.log_path,
        execId: row.exec_id,
        sessionId: row.session_id,
        sender,          // the ATTESTED sender — D93/D94: a record without attribution answers nothing
      });
    } catch (err) {
      log('error', 'capture-session-screen REFUSED: the screen-read audit could not be written — no screen was served', {
        execId: row.exec_id, senderId: sender.id, error: err.message,
      });
      throw new InternalApiError(
        INTERNAL,
        `capture-session-screen refused: the screen-read audit could not be written (${err.message}). No screen was served — ` +
        `the daemon does not serve un-audited screen reads (owner ruling D94).`,
        { check: 'screen-read-audit' },
      );
    }

    const cap = ptyHost.captureScreen(row.exec_id);
    // A DETACHED VALUE SNAPSHOT: the rendered screen as a plain string plus its dimensions.
    // NEVER the vt model itself, the bridge, or a stream (§3). `screen` is already a rendered
    // string — a copy, not a view into vt state — and the outbound round-trip in dispatch()
    // re-asserts the whole thing is plain data before it crosses.
    //
    // `repainting` (D96): true means the vt model has not yet received a byte — the session was
    // just re-attached and dtach's `-r winch` repaint is still in flight, so `screen` is blank or
    // partial. It exists because session-surface-spec.md Behavior #7 permits a first capture that
    // is "momentarily stale" but forbids one that is SILENTLY blank: a lazily re-attached session
    // would otherwise return an empty screen indistinguishable from a genuinely empty one. A
    // polling client simply reads again.
    return { id: row.exec_id, rows: cap.rows, cols: cap.cols, screen: cap.screen, repainting: Boolean(cap.repainting) };
  }

  // Kill a session — expose the spawn module's EXISTING kill surface (TERM → grace →
  // KILL of the whole process tree, status → `killed`) on the wire (cli-expansion ruling
  // D2, ce-4). Kill is NOT headed-only — a session is "killable at any time" regardless
  // of session_mode (D7) — so this handler does NOT reuse revalidateSessionTarget (whose
  // headed-only check belongs to the JOIN/TAKE-OVER surface); it runs its own complete
  // re-validation clause in remove-job's own order: existence, then authorization, then
  // state. An unauthorized sender therefore learns only that the id exists, never the
  // session's state.
  async function handleKillSession(payload, sender) {
    for (const key of Object.keys(payload)) {
      if (key !== 'id') {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }

    // ⚑ The id field is `id` — the same wire field the session surface and exec-scoped
    // `inspect` use, carrying the same integer jobs_log.exec_id (D16/D23; see the note on
    // revalidateSessionTarget for why it is neither `jobId` nor `sessionId`).
    const id = payload.id;
    if (!Number.isInteger(id)) {
      throw new InternalApiError(VALIDATION_FAILED, 'kill-session requires an integer id', { check: 'id-shape', field: 'id' });
    }
    const row = heartStore.getExecution(id);
    if (!row) {
      throw new InternalApiError(NOT_FOUND, `execution not found: ${id}`, { check: 'id-exists', id });
    }

    // D65(B) applied to kill (ce-4): the SAME v1 model as cancel — owner may kill
    // anything; the creator APPROXIMATION may kill their own. The question is asked in
    // the ONE policy module (authz.js), never as a scattered `if` here.
    const decision = authz.canKillSession({ sender, row });
    if (!decision.allowed) {
      throw new InternalApiError(UNAUTHORIZED_SENDER, decision.reason, { check: 'authorization', id });
    }

    // A session already TERMINAL (`done`/`failed`/`killed` — the closed jobs_log.status
    // enum's terminal states) is refused TYPED, never re-killed: its process already
    // resolved, so there is nothing to signal, and letting spawn.kill run would OVERWRITE
    // the honest lifecycle record (a `done` row re-marked `killed` falsifies how the turn
    // actually ended). `blocked`/`stalled` deliberately pass through: a stalled session's
    // process still lives (D23 — stalled is NOT auto-killed), and liveness for the rest is
    // the spawn module's own carrier check.
    if (row.status === 'done' || row.status === 'failed' || row.status === 'killed') {
      throw new InternalApiError(
        VALIDATION_FAILED,
        `session ${id} is already terminal (status: ${row.status}) — nothing to kill`,
        { check: 'session-terminal', field: 'id', id, status: row.status },
      );
    }

    // The kill capability is CONSUMED, not reimplemented: TERM → grace → KILL and the
    // status → `killed` store write live in the spawn module. A row spawn.kill cannot
    // signal (no usable carrier metadata) raises E_CARRIER_FAILED, carried to the wire as
    // VALIDATION_FAILED by the STORE_TO_WIRE row above. The result is already plain data.
    const res = await spawnManager.kill(row.exec_id);

    // ── THE KILL AUDIT (cli-expansion owner ruling, 2026-07-20) ──────────────────
    //
    // AFTER the kill, on the SUCCESS path — the owner-ruled placement, deliberately NOT the
    // audit-first ordering the session surface above uses. That fail-closed-BEFORE posture
    // exists to stop a SECRET leaving un-audited (keystrokes delivered, a screen served); a
    // kill delivers nothing, and refusing a KILL because an audit file cannot be written would
    // leave a runaway process unkillable behind a full disk — inverting the kill switch's whole
    // point ("killable at any time", D7). The record mirrors the screen-read shape: WHO killed
    // WHICH session WHEN; no payload data.
    //
    // The failure POSTURE mirrors the session surface exactly (refuse, never log-and-continue):
    // the kill has already landed and cannot be un-done, so what is refused is the SUCCESS
    // REPORT — the sender gets a loud INTERNAL naming the audit fault instead of a clean
    // result, and the store's `killed` status remains the disk truth to reconcile against. The
    // one gap this ordering admits — a kill that lands while the audit write fails leaves no
    // record — is inherent to the ruled placement, visible in the daemon log, and correlatable
    // against the store row.
    //
    // `row.log_path` is read from the pre-kill row: every row spawn.kill can actually signal
    // reached spawn, and spawn writes log_path at `launching` before any carrier launch — a row
    // with carrier metadata but no log_path is not a shape the daemon produces, and if one
    // appears the appender's own guard refuses rather than inventing an audit location.
    try {
      appendKillRecord({
        logPath: row.log_path,
        execId: row.exec_id,
        sessionId: row.session_id,
        sender,          // the ATTESTED sender — D93: a record without attribution answers nothing
      });
    } catch (err) {
      log('error', 'kill-session AUDIT FAILED: the session was killed but the kill audit could not be written', {
        execId: row.exec_id, senderId: sender.id, error: err.message,
      });
      throw new InternalApiError(
        INTERNAL,
        `kill-session: the session WAS killed (the store now reads status 'killed') but the kill audit could not be ` +
        `written (${err.message}) — the success result is withheld rather than reporting an un-audited kill ` +
        `(session-audit posture, D92/D94 lineage; owner ruling 2026-07-20).`,
        { check: 'kill-audit' },
      );
    }

    log('info', 'session killed via kill-session', { execId: row.exec_id, senderId: sender.id, signal: res.signal });
    return { execId: res.execId, killed: res.killed, signal: res.signal ?? null };
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
        case 'send-to-session': result = handleSendToSession(env.payload, env.sender); break;
        case 'capture-session-screen': result = handleCaptureSessionScreen(env.payload, env.sender); break;
        case 'kill-session': result = await handleKillSession(env.payload, env.sender); break;
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
