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
// The ENABLED-vs-FIREABLE derivation (S-2). Imported rather than reimplemented: it reads the same
// required-argument set enqueue enforces, so the report and the runtime cannot disagree.
const { jobFireability } = require('../heart/heart-store');
const { appendKillRecord } = require('./keys-audit');
// The `record-bus-answer` act (task 7.771). Required rather than injected, like `appendKillRecord`
// above and unlike `liveSessions`: it is a stateless call, not a manager holding processes.
const { recordBusAnswer } = require('../../engine/bus-answer');
const path = require('path');

const ENVELOPE_VERSION = 1;

// The ratified intent surface (contract § 1). NEVER a raw spawn command,
// NEVER a raw SQL/store handle. Future intents are ADDED by name under the same
// envelope, each with its own re-validation clause — never by widening an
// existing intent's payload semantics. `snooze` is the fifth, added ADDITIVELY by
// owner ruling D71 (envelope version UNCHANGED) so p4-2's CLI snooze subcommand has
// a gateway path to wrap.
//
// `send-to-session` + `capture-session-screen` were the SIXTH and SEVENTH (owner ruling
// D90, p6-3a — the Batch-6 session surface). Both are RETIRED by task 7.29: the
// server-owned pty they drove is deleted, tmux holds the headed session, and SSH is the
// human trust boundary. Removal is a LOCKSTEP edit across this set, the gateway's
// `parse.js` INTENTS, and the dispatch switch below — probe-intent-drift.js exists to
// catch a half-done one. Retiring an intent does NOT bump the ENVELOPE VERSION either:
// the wire answer for a name no longer in this set is the same UNKNOWN_INTENT any
// never-registered name gets, which is a refusal the envelope already specifies.
// `kill-session` is the EIGHTH, added ADDITIVELY by the cli-expansion run (ruling D2,
// ce-4) under the SAME §1 extension rule: it exposes the spawn module's EXISTING kill
// surface (TERM → grace → KILL of the whole tree, status → `killed`) on the wire, with
// its OWN complete re-validation clause and its OWN authz decision (D65(B) — the same
// model as remove-job's cancel). The ENVELOPE VERSION IS UNCHANGED and no existing
// intent's payload semantics move.
// `register-job` is the NINTH, added ADDITIVELY by owner ruling 2026-07-25 (task 7.12)
// under the SAME §1 extension rule: it is the daemon's first catalogue-WRITE surface,
// with its OWN complete re-validation clause and its OWN authz decision (owner + the
// master APPROXIMATION — see authz.canRegisterJob). The ENVELOPE VERSION IS UNCHANGED
// and no existing intent's payload semantics move. Before it, catalogue rows could only
// be created by writing the database directly on the box — around this entire pipeline.
// `deregister-job` is the TENTH, added ADDITIVELY by task 7.364 (F20, issue
// G-m4-demo-verdict-assembler-0804-1610) under the SAME §1 extension rule: it is the
// catalogue's first RETIREMENT surface, with its OWN re-validation clause and its OWN
// authz decision (authz.canDeregisterJob — the same policy as its create arm). The
// ENVELOPE VERSION IS UNCHANGED and no existing intent's payload semantics move. Before
// it, a registered definition could never be stopped: `remove-job` takes a QUEUE id and
// never touches the catalogue, and `--disabled` existed only at registration time.
// `send-message` is the ELEVENTH intent, added ADDITIVELY by task 7.93 under the SAME §1
// extension rule as register-job/deregister-job: the addressed-message door the coordination
// client had nothing to route to (owner ruling `r-793-unbarred-slot-address-door`). The ENVELOPE
// VERSION IS UNCHANGED and no existing intent's payload semantics move. It is addressed by
// SLOT/THREAD (D39/D42 — "the thread CARRIES the address") and mints NO recipient column: the
// write lands through the already-shipped heartStore.recordMessage, whose `messages` row has
// carried (type, sender, thread, corpus) since before this task. `d-team-kit-realization`'s
// divergences 1 and 4 STAND — the client is adapted to the gateway's shape, never the reverse.
// `record-bus-answer` is the TWELFTH intent, added ADDITIVELY by task 7.771 (owner ruling
// 2026-08-11, design `one-readiness-predicate.md` § D8) under the SAME §1 extension rule as its
// three predecessors: it records the owner's Slack reply as a `type: answer` row on the asking
// seat's coordination bus, with its OWN complete re-validation clause and its OWN authz decision
// (`authz.canRecordBusAnswer` — BRIDGE ONLY, the narrowest in the policy module). The ENVELOPE
// VERSION IS UNCHANGED and no existing intent's payload semantics move. Before it, the bus kept
// every question and no reply, so nothing could see an ask close and a run could walk past a
// question the owner had already answered. The seeing is now done by `coord.py ready-seats`: an
// unanswered owner ask makes the seat `HELD` — for EVERY seat since W2, with no `fallback:`
// arm and no ferry-delivery gate in the way — and `engine/seeding.js#recordView` holds that
// seat's dependents until this row lands and the verdict clears.
// ⚑ THE WRITE IS NOT PERFORMED HERE AND NOT IN JAVASCRIPT AT ALL: `coordination/messages.md` has
// exactly one writer, `coord.py`, and `engine/bus-answer.js` shells to it. This handler validates,
// authorizes, and delegates — the same shape `live-feed` has over the live-session manager.
const INTENTS = new Set([
  'enqueue-job', 'remove-job', 'inspect', 'spawn-via-named-profile', 'snooze',
  'kill-session', 'register-job', 'deregister-job', 'live-feed', 'send-message',
  'record-bus-answer',
]);

// The goal/seat name shape, re-checked at the core independently of the gateway's copy
// (`gateway/parse.js#BUS_NAME_RE`) — DEC-3: gateway origin is not trust, and these two tokens
// become path segments under `.rbtv/goals/`.
const BUS_NAME_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

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
// what `inspect` is for, and a separate intent would duplicate its plumbing. (The contrast that
// made the rule legible — screen capture was a LIVE read, not a store query, so IT got its own
// intent — is history: task 7.29 retired it with the pty. The rule it illustrates is unchanged.)
// Execution-scoped like `status`/`logs` — the id is a jobs_log
// exec_id; the handler resolves the execution's chain-stable thread and returns that
// thread's message rows, paged.
//
// ⚑ `executions` ADDED by task 7.62 — the state-filtered listing the built read surface lacked:
// the fixed views (jobs|queue|daemon|ticker) and the execution-SCOPED views (status|logs|messages)
// between them offered no way to ask "every failed run" or "every stalled worker". Again a TARGET
// and not a ninth intent (same ce-5/D75 reason as `messages`), and again NO STORE CHANGE — it
// reads the shipped `listExecutionsByStatus()` (heart-store.js:849, fourteen live callers).
// Unlike every other target it is neither fixed nor id-scoped: it takes `status` and pages.
const INSPECT_TARGETS = new Set(['jobs', 'queue', 'status', 'logs', 'daemon', 'ticker', 'messages', 'executions']);
// The closed jobs_log.status enum (schema.sql:65-66), re-validated at the core independently of
// gateway origin — the defense-in-depth posture probe-snooze already proves for `minutes`. Task
// 7.46 SPLITS this enum into session-level and turn-level states; probe-inspect-executions.js
// derives the live enum from the database's own DDL and fails loud when this copy drifts from it.
const EXEC_STATUSES = new Set(['launching', 'running', 'done', 'blocked', 'failed', 'stalled', 'killed']);
// Server-enforced max page (contract § 1, `inspect`: "offset/limit bounded").
const MAX_PAGE = 500;
const DEFAULT_PAGE = 200;

// The closed message-type enum (heart-store.js MESSAGE_TYPES), re-validated at the core
// independently of gateway origin — the same defense-in-depth copy EXEC_STATUSES above is.
// Verified 2026-08-10 identical to the coordination client's own type vocabulary
// (`d-team-kit-realization` protocol rule P2), which is what lets one message cross both substrates.
// W4 closed it at seven; D2's routed types make it EIGHT (`stuck`). See heart-store.js
// MESSAGE_TYPES for the whole site list.
const MESSAGE_TYPES = new Set(['completion', 'ask', 'answer', 'verdict', 'note', 'queue-request', 'escalation', 'stuck']);

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
  // What to do when this row's (run, seat) is already held: 'dedupe' (default, absent = this)
  // suppresses per the Q9 idempotent door; 'queue' inserts the row anyway and lets the ticker's
  // seat-busy gate serialize it behind the holder. Also not a queue column.
  'on_seat_busy',
  // Which CONVERSATION at the seat this row belongs to. The store stamps it into the row's args
  // under a reserved key and `seatKeyOf` suffixes the seat key with it, so two shards of one seat
  // run concurrently while one shard stays serialized. Also not a queue column.
  'seat_shard',
]);

// The register-job payload's field set (task 7.12). The `jobs` DDL is the authoritative
// field source here exactly as it is for enqueue above, so the wire carries the ratified
// column names. `created_at`/`updated_at` are deliberately ABSENT: the store stamps them,
// and a sender that could set them could forge a catalogue row's history.
const REGISTER_ALLOWED_KEYS = new Set([
  'job_id', 'action_type', 'function', 'args_schema', 'description', 'enabled',
  // Validate-only mode (owner ruling 2026-07-25 Call 3) — not a column; it selects a
  // pre-insert exit and is never written.
  'dry_run',
  // task 7.12 · the job->seat pointer (owner ruling `r-job-seat-home`, 2026-07-27).
  'goal_name', 'seat_name',
]);

// The live-feed payload's field set (live-session-design.md §1). A DELIBERATE second copy of the
// gateway parser's set, exactly like ENQUEUE_ALLOWED_KEYS above and for the same DEC-3 reason: the
// core re-validates raw shape without importing the gateway. `session_ref` is deliberately ABSENT
// — a sender naming the session to resume could resume someone else's conversation, so the core
// derives it from `exec_id` through the store instead.
// ⚠ `profile` LEFT THIS SET AT 7.787 (`#d-abolish-profile-names`): a sender naming what a seat
// runs on is precisely the variable the abolition deletes. The warm leg resolves the seat's own
// cast off `workdir` like every other lane; an uncast seat is an ineligible reason, then a refusal
// on the cold path. A payload still carrying the key is now an ordinary unknown-field rejection.
const LIVE_FEED_KEYS = new Set(['conversation', 'prompt', 'workdir', 'exec_id', 'start']);

// The deregister-job payload's field set (task 7.364) — the id, plus `purge` for the reclaim
// arm. No `dry_run`: every refusal either arm can raise (unknown id; still enabled; pending
// queue rows; live executions) is decidable from `inspect jobs`/`inspect queue`/`inspect
// executions` reads the sender can already make, so a validate-only mode would add a second
// code path with nothing to validate that a read does not already answer.
const DEREGISTER_ALLOWED_KEYS = new Set(['job_id', 'purge']);

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
  // The create-only duplicate refusal from `register-job` (task 7.12). Sender-
  // correctable — the same family as E_UNKNOWN_JOB, which is its exact inverse:
  // "that catalogue id is already taken", fixed by picking another id. Not NOT_FOUND
  // (nothing is missing) and not INTERNAL (nothing broke).
  ['E_JOB_EXISTS', VALIDATION_FAILED],
  // The purge arm's three state refusals (still enabled / pending queue rows / live
  // executions). VALIDATION_FAILED for the E_JOB_EXISTS reason exactly: the id is there, the
  // sender may act on it, and what refused is a state check naming the command that clears it.
  ['E_JOB_PURGE_REFUSED', VALIDATION_FAILED],
  ['E_JOB_DISABLED', VALIDATION_FAILED],
  ['E_BAD_ARGS', VALIDATION_FAILED],
  ['E_UNKNOWN_LAUNCH_SPEC', VALIDATION_FAILED],
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
  // The spawn module's carrier refusal — through THIS dispatch it is reachable ONLY from
  // `kill-session` (the one intent that calls into the spawn manager: spawn-via-named-profile
  // is D70-excluded before any spawn call, and inspect status/logs never throw it). spawn.kill
  // raises it for a row with NO usable carrier metadata — a row that never reached spawn, or
  // whose carrier identity was lost — so there is no process to signal. VALIDATION_FAILED, not
  // NOT_FOUND: the execution row EXISTS (the re-validation clause proved it); what refused is a
  // state check on the row, and `details.check` names it. It is now the only state refusal of
  // its family on the map: the pty pair it was written beside (E_SESSION_NOT_LIVE,
  // E_PTY_BRIDGE) left with their module at task 7.29.
  ['E_CARRIER_FAILED', VALIDATION_FAILED],
]);

// ── The classification's other half: typed codes DELIBERATELY absent from the map ────────────
//
// STORE_TO_WIRE is a CLOSED literal map, and an unmapped typed code silently degrades to the
// anonymous INTERNAL "server-core fault" below — the decay mode batch-08 item 7 ruled against
// (the THIRD closed set in that batch with no drift detection). The durable fix is not the rows,
// it is this invariant, held by probe-error-map-drift.js:
//
//   EVERY typed code exported by server/{spawn,heart}/errors.js is either a STORE_TO_WIRE
//   key or a NOT_WIRE_REACHABLE key — exactly one, never neither, never both.
//
// (`server/pty/errors.js` was the third module in that set until task 7.29 deleted it; its seven
// codes left both maps in the same change, and probe-error-map-drift.js's ERROR_MODULES lost the
// path in lockstep. The invariant is unchanged — only its membership shrank.)
//
// Adding a new typed code without deciding its wire fate fails the probe NAMING the code. The
// rationale strings are the reachability ruling of record: each states WHY the code cannot cross
// toWireError() from a request path (verified at task 7.18 against every dispatch handler's call
// graph — the intents reach heartStore.* and spawnManager.status/logs/kill ONLY; spawn itself is
// never wire-triggered, because spawn-via-named-profile is D70-dropped on entry and dispatch
// never calls spawnManager.spawn).
// If a later change makes one of these codes cross the wire, MOVE it to STORE_TO_WIRE with a
// ruled wire code — do not widen a rationale.
const NOT_WIRE_REACHABLE = new Map([
  // Boot / config-load only — the daemon refuses to START; no request path exists yet.
  ['E_CONFIG_LOAD', 'config-load failure at boot; the daemon never comes up to serve a request'],
  ['E_MISSING_KEY', 'missing required config key at boot/config-load; never raised in a handler'],
  ['E_UNKNOWN_SLOT', 'unknown template slot at profile config-load; never raised in a handler'],
  ['E_SYSTEMD_NOT_AVAILABLE', 'carrier availability check at boot; never raised in a handler'],
  ['E_ORPHAN_RESCAN_FAILED', 'boot orphan rescan only (spawn.orphanRescan); dispatch never calls it'],
  ['E_MIGRATION_FAILED', 'heart-store schema migration at store OPEN (G-135); the store is constructed before any listener exists, so the daemon refuses to start and no request path is reachable'],
  ['E_STORE_NEWER_THAN_CODE', 'heart-store version check at store OPEN (G-135); same boot-only path — refusing a store written by a newer build, before the daemon serves anything'],
  // A genuine internal fault — the anonymous INTERNAL fall-through IS the honest wire answer
  // (batch-08 item 7 ruled it correctly absent; a map row would add nothing but false precision).
  ['E_SECOND_WRITER', 'single-writer invariant breach — a real daemon fault; INTERNAL is honest'],
  // Ticker-spawn-path only (task 7.18 reachability finding, refining the item-7 table): these
  // fire inside spawn/spawnSeat/bwrap, which ONLY the ticker's dispatch phase invokes.
  // A spawn failure lands as jobs_log status 'failed' + a spawn-failed feed action — it never
  // crosses toWireError(), so it cannot degrade to the wire's "server-core fault" today.
  // (E_HOLDER_FAILED, E_PROMPT_INJECTION_TIMEOUT, E_HEADED_PROMPT_REJECTED,
  // E_HEADED_PROMPT_CARRIAGE and E_HEADED_STDIN_CARRIAGE sat in this class until task 7.29:
  // every one was raised inside server/pty/, and all five left with the module.)
  ['E_FS_SANDBOX_UNAVAILABLE', 'ticker-spawn-path only (bwrap sandbox resolve); spawn is never wire-triggered'],
  ['E_SPEC_HALVES_UNSUPPORTED', 'ticker-spawn-path only (the G-144 profile-shape guard, raised by spawn AND spawnSeat immediately after the profile lookup); spawn is never wire-triggered — spawn-via-named-profile is D70-dropped on entry, dispatch never calls spawnManager.spawn/spawnSeat, and the only route to spawnSeat is server/index.js spawnManagerWithPty.spawn, which is the ticker dispatch phase'],
  // Task 7.75 / r-seats-only-architecture (3) — the DISPATCH DOOR's two raise sites, both inside
  // spawn() (no workdir at all, and a resolved workdir that is no seat folder). Same ticker-only
  // ground as the two rows above, measured not inherited: spawn()'s ONLY caller is the decorated
  // spawn at server/index.js:602, whose only caller is ticker.js's dispatch phase.
  ['E_SEATLESS_GOAL_DISPATCH', 'ticker-spawn-path only (the task 7.75 dispatch door, raised at both sites inside spawn — no workdir, and a resolved workdir that is not a seat folder); spawn is never wire-triggered — spawn-via-named-profile is D70-dropped on entry before any spawn call, dispatch reaches the spawn manager only via status/logs/kill, and spawn()\'s sole caller is the ticker dispatch phase'],
  // Task 7.10 — the peer-identity resolver's refusals, classified on a stronger ground than "no
  // handler raises them": they are never THROWN at all. `resolvePeerSeat` returns every refusal as
  // DATA (`{ ok: false, code }`) and its one caller — the gateway's authenticate step — consumes
  // that data to decide whether to attach a proven seat. Nothing constructs an Error from these,
  // so no value carrying them can reach toWireError() by any path. If a future caller throws one,
  // MOVE it to STORE_TO_WIRE with a ruled wire code rather than widen this rationale.
  ['E_PEER_NOT_LOCAL', 'seat-resolution outcome returned as DATA to the gateway auth step, never thrown; a remote caller simply carries no proven seat'],
  ['E_PEER_UNRESOLVED', 'seat-resolution outcome returned as DATA to the gateway auth step, never thrown'],
  ['E_PEER_AMBIGUOUS', 'seat-resolution outcome returned as DATA to the gateway auth step, never thrown'],

  // ── G-138: the fourteen codes this map had never ruled on (task 7.11/7.13/7.42 arrivals) ────
  //
  // Filed when it was NINE and measured at FOURTEEN (G-166) — it grew because 7.42's profile work
  // landed hours after the row. It stayed open on a GOOD objection: "a rationale written by
  // someone who did not trace those call graphs would be a guess wearing a ruling's clothes."
  // Each line below is a traced call graph, not a plausible sentence.
  //
  // ⚠ THE QUESTION WAS ASKED IN BOTH DIRECTIONS. The six identity-gate codes looked like the
  // likeliest STORE_TO_WIRE candidates — identity.js is the COMMAND-TIME gate task 7.10 wired
  // into the gateway seam, so a refusal there could plausibly cross the wire. It cannot, and the
  // reason is structural rather than incidental: identity.js contains ZERO `throw` statements.
  // Every refusal is `fail()` -> `{ ok: false, code, ... }` returned as DATA. That is the same
  // strong ground the E_PEER_* rows above stand on, arrived at by measurement, not by symmetry.

  // Task 7.11 — the seat cage (server/spawn/cage.js).
  // ⚠ E_CAGE_TEMPLATE HAS TWO RAISE CONTEXTS and a single-context rationale would be false for
  // half its sites: (1) config LOAD, via validateSeatBindTemplate <- config.js's seatBindValidator
  // <- loadConfig — boot-only, the daemon refuses to start; (2) seat compose, via composeSeatCage
  // /parseEntry/substituteScalars/normalize <- spawnSeat. Neither is wire-triggered.
  ['E_CAGE_TEMPLATE', 'TWO contexts, both non-wire: config LOAD (validateSeatBindTemplate via loadConfig — the daemon refuses to start) and seat compose (composeSeatCage <- spawnSeat, ticker-spawn path); dispatch never calls spawnSeat'],
  ['E_CAGE_PRIVATE_ALIAS', 'ticker-spawn-path only (composePrivateScope <- composeAncestorMasks <- composeCageFor <- spawnSeat); dispatch never calls spawnSeat, and a cage whose opening resolves into a private path without naming it is refused before any unit exists'],

  // Task 7.11 §4b — the COMMAND-TIME identity gate (server/seat-identity/identity.js).
  // Never thrown, by construction: zero `throw` in that module. Consumers are resolvePeerSeat
  // (-> the gateway's authenticate step) and seat-identity/cli.js, both of which read the result
  // as data. If a future caller ever THROWS one, MOVE it to STORE_TO_WIRE with a ruled wire code
  // rather than widen this rationale.
  ['E_IDENTITY_NO_SEAT', 'identity-gate outcome returned as DATA (identity.js has zero throws), consumed by resolvePeerSeat and the seat-identity CLI; nothing constructs an Error from it'],
  ['E_IDENTITY_NO_SESSION', 'identity-gate outcome returned as DATA (identity.js has zero throws); absence of a session row is a refusal value, never an exception'],
  ['E_IDENTITY_MISMATCH', 'identity-gate outcome returned as DATA (identity.js has zero throws); the refusal names the registered occupant to its caller, it does not raise'],
  ['E_IDENTITY_SCHEMA', 'identity-gate outcome returned as DATA (identity.js has zero throws); the live sessions.csv carries none of the identity columns today, so this is the DEFAULT state until 7.37 — which is exactly why it must stay a typed refusal and never a fall-through to allow'],

  // ⚠ These two are DUAL-CONTEXT — data on one path, thrown on the other. Both non-wire, but a
  // rationale naming only the identity.js half would be false for the spawn.js half, and vice
  // versa. That is the trap this whole block exists to avoid.
  ['E_NOT_A_SEAT_FOLDER', 'TWO contexts, both non-wire: returned as DATA by the command-time gate (identity.js, zero throws) AND thrown by the launch-time gate (spawn.js spawnSeat), which is ticker-spawn-path only — dispatch never calls spawnSeat'],
  ['E_GOAL_NOT_LIVE', 'TWO contexts, both non-wire: returned as DATA by the command-time gate (identity.js, zero throws) AND thrown by the launch-time gate (spawn.js spawnSeat), which is ticker-spawn-path only. 7.607 E2a renamed it from E_RUN_NOT_LIVE with the run layer; the call graph is unchanged, so the classification carries over unaltered'],

  // Task 7.13 — server-composed tmux target names.
  ['E_TMUX_NAME_INVALID', 'ticker-spawn-path only (tmux.js <- composeSeatSpawn <- spawnSeat); the names are server-composed, never caller strings, so no request path can carry one'],

  // Task 7.42 — the shared launch-profile resolver (ignite/launch-profiles/).
  // ⚠ STRONGER THAN "not wire-reachable": NO DAEMON PATH REACHES THESE AT ALL TODAY. Measured —
  // server/spawn/config.js requires the launch-profiles barrel but calls only loadConfig,
  // resolveTemplateSlots, resolveWorkdir, resolveWorkspaceRoot, sessionsRootFor and CLOSED_SLOTS.
  // `resolveProfile` has ZERO callers in this repo outside its own module and the probes; that is
  // G-144's finding stated from the other side (7.42 shipped with one live consumer, and the
  // daemon spawn path is not it). preflight is exported but deliberately unwired — the barrel
  // says so at launch-profiles/index.js:46.
  // ⚠ TASKS 7.43 / 7.54 WIRE resolveProfile INTO THE SPAWN PATH. When they do, RE-RULE these five
  // rather than inheriting this rationale: it is true of today's call graph, not of the design's.
  //
  // ⚑ ONE OF THE FIVE HAS BEEN RE-RULED — E_UNKNOWN_EFFORT, on 2026-08-11, owner ruling
  // `d-0811lp-effort-lane-build-now` (run exec-0811-live-proofs), which explicitly overrode the
  // "Re-rule at 7.43/7.54" reservation on that ONE code rather than waiting for the refactor. The
  // effort ladder was separable from half selection: `resolveEffort()` (launch-profiles) is now
  // called BOTH by resolveProfile and by `server/spawn/spawn.js#composeArgv`, so the daemon raises
  // this code live, on a request it received. The other four notes are UNCHANGED and still true —
  // half selection, the caller-slot bound and the pre-flight remain unwired.
  ['E_NO_PORTABLE_HALF', 'raised only inside resolveProfile (launch-profiles/profiles.js), which has NO daemon caller today — the spawn path resolves exec: directly (G-144). Re-rule at 7.43/7.54'],
  ['E_RAW_FLAG', 'raised only inside resolveProfile (the caller-slot bound), which has NO daemon caller today. Re-rule at 7.43/7.54'],
  // RE-RULED 2026-08-11 (d-0811lp-effort-lane-build-now): this one now has a live daemon caller.
  ['E_UNKNOWN_EFFORT', 'raised by resolveEffort (launch-profiles/profiles.js) — the effort LADDER, shared by resolveProfile AND by the daemon spawn path since 2026-08-11 (d-0811lp-effort-lane-build-now). A request naming a rung outside the target profile\'s 1..N range, or a non-integer rung, reaches this code live; config-LOAD ladder validation still raises E_CONFIG_LOAD instead'],
  ['E_PINNED_FLAG_ABSENT', 'raised only inside preflightPinnedFlags (launch-profiles/preflight.js), exported but deliberately NOT wired into the daemon spawn path (barrel comment, index.js:46). Re-rule when pre-flight is wired'],
  ['E_PREFLIGHT_UNAVAILABLE', 'raised only inside the pre-flight help reader (launch-profiles/preflight.js), same deliberately-unwired module; a --help that cannot be read is a pre-flight outcome, not a request outcome'],
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

// `readConfiguredTickIntervalMs` (task 7.66) is a LIVE READ of settings.json, deliberately a
// closure rather than a value: the daemon's own cadence was materialized at boot, so the only way
// `inspect daemon` can report a PENDING edit is to read the file at request time. Absent → the
// fields report `null`, which means "not readable", never "no pending edit" — the two must not
// look alike.
// `onEnqueue` is the ticker's latency valve, injected at the composition root (server/index.js).
// It is called ONLY after a real queue row is minted — never on a dry run, never on a validation
// failure — and it is the one external-work signal the ticker is allowed to react to. Absent →
// the enqueue behaves exactly as before and the row waits out the cadence.
function createInternalApi({ heartStore, spawnManager, secret, logger = null, authzPolicy = null, daemonStartTime = null, daemonLoadedCode = null, daemonConfig = null, readConfiguredTickIntervalMs = null, onEnqueue = null, liveSessions = null, workspaceRoot = null }) {
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

    // Re-checked here for the same DEC-3 reason as `dry_run`: the enum selects which door the
    // store takes, so an unrecognised value must be a typed refusal at the wire, never a silent
    // fall-through to the default. Absent → 'dedupe' (today's behaviour, unchanged).
    if (payload.on_seat_busy !== undefined && payload.on_seat_busy !== 'dedupe' && payload.on_seat_busy !== 'queue') {
      throw new InternalApiError(VALIDATION_FAILED, `on_seat_busy must be 'dedupe' or 'queue'`, { check: 'on_seat_busy-enum', field: 'on_seat_busy' });
    }

    // Same DEC-3 reason, and the same shape the gateway already refused: a malformed shard would
    // otherwise reach the store as part of a SEAT KEY, where a stray `#` or newline would split or
    // corrupt the very string the busy gate compares. Absent/null/'' → no shard, today's key.
    if (payload.seat_shard !== undefined && payload.seat_shard !== null && payload.seat_shard !== ''
      && (typeof payload.seat_shard !== 'string' || !/^[^\s#]{1,200}$/.test(payload.seat_shard))) {
      throw new InternalApiError(VALIDATION_FAILED, 'seat_shard must be a 1-200 char string with no whitespace and no "#"', { check: 'seat_shard-shape', field: 'seat_shard' });
    }

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
      // Task 7.389 — the enqueuing SEAT, stamped from the PROVEN seat the ingress attached
      // (gateway/sender-auth.js `attachProvenSeat`: socket inode → owning pid → cwd + /proc
      // ancestry), never from the payload, for the same reason `enqueued_by` is not accepted from a
      // sender (gateway/parse.js:126 — audit forgery). `sender.seat` is present ONLY when proven,
      // so an unproven caller writes NULL and is byte-identical to the pre-7.389 row.
      enqueuingSeat: sender.seat || null,
      dryRun,
      onSeatBusy: payload.on_seat_busy,
      seatShard: payload.seat_shard,
    });

    // Validate-only verdict — no queue row minted (D72/D73). Reaching here means the
    // store's COMPLETE re-validation PASSED (a failure throws VALIDATION_FAILED,
    // identical to the non-dry_run failure path). The verdict is plain data.
    if (dryRun) {
      // ⚠ THE 7.736 DOOR-1 `edge_fastpath` KEY IS GONE (`one-readiness-predicate.md` § Deletions).
      // It reported whether a goal's EDGE FAST PATH was armed — a mechanism that no longer exists:
      // readiness is `coordinate ready-seats`, consumed by the daemon's own seeding pass, and there
      // is no arm file to be armed or unarmed. A verdict about a deleted mechanism is worse than no
      // verdict, so the key is DELETED rather than left reporting `false` forever.
      return { dry_run: true, valid: true };
    }

    // ── Task Q9 · the idempotent door's AUDIT SURFACE (ruling `d-q9-door`) ───────────────────
    // The store suppressed this enqueue because the (run, seat) is already held. It is a NO-OP,
    // so the ticker is NOT nudged — there is no new row to serve. The suppression MUST be
    // observable or it is indistinguishable from a real enqueue on the wire: the caller gets a
    // valid queue id either way, by design (that is what kept the retired periodic edge-runner's
    // pass green instead of recording `failed` every cadence, and what keeps a re-seeding pass
    // idempotent now that the seeding pass is the one driver). This line is that observability, and
    // `idempotent-suppress` is the marker probes and log greps key on.
    // The daemon log is the operator's view; `deduped` on the result is the machine's.
    if (result.deduped) {
      log('info', 'idempotent-suppress', {
        seatKey: result.seat_key,
        heldBy: result.because,
        heldStatus: result.held_status,
        originatingQueueId: result.queue_id,
        execId: result.exec_id,
        jobId: payload.job_id,
        senderId: sender.id,
      });
      return {
        jobId: result.queue_id,
        deduped: true,
        because: result.because,
        seat_key: result.seat_key,
        exec_id: result.exec_id,
      };
    }
    // `jobId` here is the QUEUE-ROW id — see the note on handleRemoveJob. This is
    // the id gateway-cli-spec.md:26 calls "the NEW job id" and feeds straight into
    // remove-job at its test 5.
    // The row exists now, so the ticker may run early for it. Best-effort and non-fatal: a
    // scheduling hiccup must never turn a COMMITTED enqueue into a wire error — the row is
    // already banked and the cadence still fires it.
    if (onEnqueue) {
      try { onEnqueue(); } catch (err) { log('warn', 'enqueue nudge failed', { error: err.message }); }
    }
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
    // A live read, and a failing one is `null` rather than an exception: `inspect daemon` is the
    // surface an operator reaches for when things are wrong, so an unreadable settings file must
    // not be the thing that stops them reading everything else.
    let configuredTick = null;
    if (typeof readConfiguredTickIntervalMs === 'function') {
      try {
        const v = readConfiguredTickIntervalMs();
        configuredTick = typeof v === 'number' && Number.isFinite(v) ? v : null;
      } catch { configuredTick = null; }
    }

    return {
      target: 'daemon',
      pid: process.pid,
      uptime_ms: uptimeMs,
      // G-188 stage 2. null is a REPORTABLE STATE, not a gap to paper over: a daemon that predates
      // this field, or whose capture failed, publishes null and the reader must say UNKNOWN rather
      // than treat the silence as health — the absence-reads-as-health shape this whole class is
      // made of. It is the value captured at BOOT and is deliberately never recomputed here:
      // hashing the files again at request time would compare them against themselves and could
      // only ever report agreement, which is a detector that cannot fire.
      code: daemonLoadedCode,
      last_tick: lastTick ? lastTick.tick : null,
      live_agent_sessions: liveAgentSessions,
      max_live_agent_sessions: configKnobs.max_live_agent_sessions ?? 14,
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
        // Task 7.66, design § 2.1: the RUNNING cadence above and the CONFIGURED cadence here, as
        // two fields. They differ exactly when a cadence edit is written and not yet restarted
        // into effect — without this pair the edit mechanism is silent about its own pending
        // state, and an operator cannot tell "my change is live" from "my change is on disk".
        // `null` = the configured value could not be read, NOT "nothing pending".
        tick_interval_ms_configured: configuredTick,
        tick_interval_pending_restart: configuredTick === null
          ? null
          : configuredTick !== (configKnobs.tick_interval_ms ?? 10000),
        stall_warn_ticks: configKnobs.stall_warn_ticks ?? 12,
        stall_halt_ticks: configKnobs.stall_halt_ticks ?? 24,
        // The hung-kill rung's window, in ticks of silence past `stalled`. 0 = the rung is off.
        stall_kill_ticks: configKnobs.stall_kill_ticks ?? 60,
        // How long a seat-busy-deferred queue row may wait before the ticker drops it with an
        // owner note. Seconds.
        seat_queue_max_age_s: configKnobs.seat_queue_max_age_s ?? 3600,
        slot_max_repeats: configKnobs.slot_max_repeats ?? 10,
        max_live_agent_sessions: configKnobs.max_live_agent_sessions ?? 14,
        // Task 7.13 piece 3: the retention window, READ-ONLY, as a FIELD on this existing
        // config block — never a new intent (ce-5/D3: read-only queries extend `inspect`;
        // the closed intent set is not touched). 0 = never delete.
        log_retention_days: configKnobs.log_retention_days ?? 90,
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
    const liveSessions = liveRows.map((r) => {
      let args;
      try { args = JSON.parse(r.args); } catch { args = {}; }
      return {
        exec_id: r.exec_id,
        status: r.status,
        action_type: r.action_type,
        job_id: r.job_id,
        queue_id: r.queue_id,
        fired_tick: r.fired_tick,
        thread: r.thread,
        workdir: typeof args.workdir === 'string' ? args.workdir : null,
      };
    });

    const queueRows = heartStore.listQueue();
    const dueSoon = queueRows.filter((r) => r.run_at !== undefined).slice(0, 20);

    // getMessages orders msg_id ASC; its `limit` is a HEAD bound, so passing one here would take
    // the OLDEST N messages and the "recent" notes would silently vanish once the head filled with
    // non-feed rows. The THREAD is filtered in SQL and the tail taken in JS — the fetch-all-then-
    // filter this used to do materialised every message row in the store, corpus included, on a
    // path the chat bridge polls every 3 s (see getMessages' header: it is what wedged the gateway
    // on 2026-08-12).
    const ownerFeedNotes = heartStore.getMessages({ thread: 'owner-feed' })
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
        // The hung-kill rung's window, in ticks of silence past `stalled`. 0 = the rung is off.
        stall_kill_ticks: configKnobs.stall_kill_ticks ?? 60,
        // How long a seat-busy-deferred queue row may wait before the ticker drops it with an
        // owner note. Seconds.
        seat_queue_max_age_s: configKnobs.seat_queue_max_age_s ?? 3600,
        slot_max_repeats: configKnobs.slot_max_repeats ?? 10,
        max_live_agent_sessions: configKnobs.max_live_agent_sessions ?? 14,
      },
    };
  }

  function safeParseActionsJson(json) {
    try { return JSON.parse(json); } catch { return json; }
  }

  async function handleInspect(payload) {
    for (const key of Object.keys(payload)) {
      // `thread` (task 7.93) — the messages target's ALTERNATIVE addressing key, re-validated here
      // independently of gateway origin exactly like every other field (DEC-3 defense in depth).
      if (!['target', 'id', 'offset', 'limit', 'status', 'thread'].includes(key)) {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }
    const { target } = payload;
    if (!INSPECT_TARGETS.has(target)) {
      throw new InternalApiError(VALIDATION_FAILED, `unknown inspect target: ${target} (known: ${[...INSPECT_TARGETS].join(', ')})`, { check: 'inspect-target', field: 'target' });
    }

    // ENABLED is not FIREABLE, and until now this surface only reported the first (S-2). `enabled`
    // is evidence a catalogue ROW EXISTS; it has never been evidence that row can RUN. A fire-tool
    // job registered with an empty args_schema reads `enabled=1` forever and is structurally unable
    // to fire, with no in-place repair — two such ids are live on this box right now. So every row
    // carries the derived verdict AND, when it is false, the reason. Derived in heart-store from the
    // SAME required-argument set enqueue enforces, never re-implemented here.
    if (target === 'jobs') {
      return {
        target,
        rows: heartStore.listJobs().map((row) => ({ ...row, ...jobFireability(row) })),
      };
    }
    if (target === 'queue') return { target, rows: heartStore.listQueue() };
    if (target === 'daemon') return handleInspectDaemon();
    if (target === 'ticker') return handleInspectTicker();

    // executions: every jobs_log row in ONE status, paged (task 7.62). The gap it closes is
    // "list every failed run / every stalled worker" — askable of no other target.
    //
    // The status is RE-VALIDATED here, never trusted from the gateway: probe-snooze's ruled
    // defense-in-depth posture, and the core is reachable by a direct envelope that never
    // passed a gateway at all. An unknown status is VALIDATION_FAILED naming the check — it is
    // NOT an empty listing, because "no such status" and "no rows in that status" are different
    // answers and collapsing them would make a typo indistinguishable from a healthy fleet.
    if (target === 'executions') {
      const { status } = payload;
      if (!EXEC_STATUSES.has(status)) {
        throw new InternalApiError(VALIDATION_FAILED, `unknown execution status: ${status} (known: ${[...EXEC_STATUSES].join(', ')})`, { check: 'exec-status', field: 'status' });
      }
      // Slice-after-fetch, exactly like `messages` above and for the same stated reason: the
      // store read is the filter (`WHERE status = ?`, index-backed by idx_jobslog_status), and
      // pushing the page bound into it would need a store change this target does not warrant
      // (D75 — read-only surface, no store change). v1-scale only, same as its precedent.
      const { offset, limit } = pageBounds(payload);
      const all = heartStore.listExecutionsByStatus(status);
      const rows = all.slice(offset, offset + limit);
      const nextOffset = offset + rows.length;
      // `total` — the size of the WHOLE filtered set, not of this page. It is free here (the
      // read already materialised `all`) and it is what makes the last page ADDRESSABLE: without
      // it the listing is oldest-first with no end marker, so reaching the newest row costs blind
      // offset probes or a walk of every page (`inspect executions --tail`, which jumps straight
      // to `total - n` when this field is present). `eof` answers "is this the last page I asked
      // for"; only `total` answers "where IS the last page".
      return { target, status, rows, total: all.length, nextOffset, eof: nextOffset >= all.length };
    }

    // ── task 7.93 · the THREAD-ADDRESSED messages read ──────────────────────────────────────
    // The read half of the addressed-message door. A tmux seat holds a SLOT ADDRESS and no
    // execution id, so the execution-scoped read below is one it can never call — which is
    // exactly what 7.57 fork 1 ruled NOT MET. Addressing by thread makes it callable.
    //
    // ⚑ NO STORE CHANGE, and the fetch-all-then-filter is inherited deliberately from the
    // id-addressed branch below for the SAME stated reason (getMessages orders msg_id ASC and
    // exposes no thread filter, so its HEAD-bound `limit` would page over the WRONG set).
    // ⚑ An unknown thread is an EMPTY page, never NOT_FOUND: a thread is an address, not a row,
    // and a slot legitimately has no messages before its first one. Answering 404 would make
    // "nobody has written to me yet" indistinguishable from "you addressed nothing".
    if (target === 'messages' && payload.thread !== undefined) {
      if (typeof payload.thread !== 'string' || payload.thread.length === 0) {
        throw new InternalApiError(VALIDATION_FAILED, 'inspect messages requires a non-empty thread', { check: 'thread-shape', field: 'thread' });
      }
      if (payload.id !== undefined) {
        throw new InternalApiError(VALIDATION_FAILED, 'inspect messages takes an id OR a thread, never both', { check: 'thread-xor-id', field: 'thread' });
      }
      const { offset, limit } = pageBounds(payload);
      const all = heartStore.getMessages({ thread: payload.thread });
      const rows = all.slice(offset, offset + limit);
      const nextOffset = offset + rows.length;
      // `total` — same reason as the executions listing above: the read already materialised the
      // whole filtered set, and it is what makes the LAST page addressable on a msg_id-ASC listing
      // with no reverse read (`inspect messages --tail` jumps to `total - n` on it).
      return { target, thread: payload.thread, rows, total: all.length, nextOffset, eof: nextOffset >= all.length };
    }

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
      // The thread is filtered IN SQL, mirroring handleInspectTicker's owner-feed read above: its
      // HEAD-bound `limit` would page over the WRONG set, so the page bound stays server-ENFORCED
      // on the filtered set (same clamp as `logs`, contract § 1: offset/limit bounded).
      const { offset, limit } = pageBounds(payload);
      const all = heartStore.getMessages({ thread: execRow.thread });
      const rows = all.slice(offset, offset + limit);
      const nextOffset = offset + rows.length;
      // `total` — see the thread-addressed branch above; free here for the same reason (`all` is
      // already materialised) and it is what `inspect messages --tail` jumps on.
      return { target, id, thread: execRow.thread, rows, total: all.length, nextOffset, eof: nextOffset >= all.length };
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

  // Register a catalogue job — add to the set of actions the daemon is ABLE to run
  // (task 7.12; owner ruling 2026-07-25). A MUTATION intent: it serializes at the
  // store's single-writer connection like enqueue-job/remove-job/snooze, and writes
  // exactly one row in one statement. Added ADDITIVELY under the contract §1 extension
  // rule — the envelope version is UNCHANGED.
  //
  // CREATE-ONLY (Call 2): a duplicate id is refused typed; nothing is ever overwritten.
  // Update/removal/disable have no v1 surface — deliberately, and stated in the spec.
  function handleRegisterJob(payload, sender) {
    // ⚑ STRICT SCHEMA FIRST, matching every sibling handler. It also keeps
    // probe-intent-drift.js's derivation CLEAN: that probe exercises dispatch() with a
    // one-unknown-field payload against stub stores, and a handler refusing it typed is
    // unambiguous proof the case ran. (Correction, 2026-07-25 adversarial review: this
    // ordering is NOT the probe's detection PRECONDITION, as an earlier comment here
    // claimed — the probe also counts an anonymous INTERNAL fault as "handler ran", so
    // a handler that touched a stub first would still be detected. The ordering earns
    // its place on hygiene and on giving the probe an unambiguous signal, not on being
    // load-bearing for the guard.)
    for (const key of Object.keys(payload)) {
      if (!REGISTER_ALLOWED_KEYS.has(key)) {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }

    // Field shapes are RE-CHECKED here, never trusted from the gateway (DEC-3).
    if (typeof payload.job_id !== 'string' || payload.job_id.length === 0) {
      throw new InternalApiError(VALIDATION_FAILED, 'job_id must be a non-empty string', { check: 'job_id-shape', field: 'job_id' });
    }
    if (typeof payload.function !== 'string' || payload.function.length === 0) {
      throw new InternalApiError(VALIDATION_FAILED, 'function must be a non-empty string', { check: 'function-shape', field: 'function' });
    }
    if (payload.enabled !== undefined && typeof payload.enabled !== 'boolean') {
      throw new InternalApiError(VALIDATION_FAILED, 'enabled must be a boolean', { check: 'enabled-shape', field: 'enabled' });
    }
    if (payload.dry_run !== undefined && typeof payload.dry_run !== 'boolean') {
      throw new InternalApiError(VALIDATION_FAILED, 'dry_run must be a boolean', { check: 'dry_run-shape', field: 'dry_run' });
    }
    const dryRun = payload.dry_run === true;

    // Authorization: owner + the master APPROXIMATION (owner ruling 2026-07-25, Call 1,
    // build (ii)). Asked in the ONE policy module, never as a scattered `if` here, and
    // asked BEFORE any store read so a refused sender learns nothing about the
    // catalogue. ⚑ The approximation admits ANY enrolled agent token, not the master
    // specifically — the exposure is stated at the policy and was accepted at the
    // ruling; it retires when CMP-13 lands (task 7.10).
    const decision = authz.canRegisterJob({ sender });
    if (!decision.allowed) {
      throw new InternalApiError(UNAUTHORIZED_SENDER, decision.reason, { check: 'authorization' });
    }

    // The store re-runs the COMPLETE deterministic validation (id/function shape,
    // action_type enum, args_schema shape AND declared types, duplicate id) and writes
    // NOTHING on any failure — the single place all mutations pass. Under `dryRun` it
    // runs the SAME checks, duplicate included, and returns the verdict BEFORE the
    // insert; the catalogue is UNCHANGED.
    const result = heartStore.registerJob({
      jobId: payload.job_id,
      actionType: payload.action_type,
      function: payload.function,
      argsSchema: typeof payload.args_schema === 'string'
        ? payload.args_schema
        : JSON.stringify(payload.args_schema ?? {}),
      description: payload.description ?? null,
      enabled: payload.enabled === undefined ? 1 : (payload.enabled ? 1 : 0),
      // task 7.12 · the job->seat pointer, passed through UNVALIDATED-BY-SHAPE here on purpose:
      // the store re-runs the complete deterministic validation including both-or-neither, and
      // this handler's contract is to hand the core the payload, never to pre-judge it (DEC-3).
      goalName: payload.goal_name ?? null,
      seatName: payload.seat_name ?? null,
      dryRun,
    });

    if (dryRun) {
      return { dry_run: true, valid: true };
    }
    // Loud, owner-readable feedback (D21(3)) in the shape remove-job/snooze established.
    return {
      registered: true,
      job_id: result.job_id,
      action_type: result.action_type,
      enabled: result.enabled === 1,
      // Echoed because an UNHOMED job is a silent condition otherwise: it registers, reports
      // enabled=1, and only reveals at fire time that it lands in the interim path. Saying
      // `homed: null` out loud at registration is the difference between a decision and a default.
      homed: result.goal_name ? { goal: result.goal_name, seat: result.seat_name } : null,
    };
  }

  // `deregister-job` (task 7.364 / F20) — the catalogue's RETIREMENT surface. A MUTATION
  // intent: it serializes at the store's single-writer connection like its siblings and
  // writes at most one column of one row. Added ADDITIVELY; the envelope version is
  // UNCHANGED.
  //
  // TWO ARMS, and the default is the safe one. Bare = DISABLE: the ticker defers every due row
  // whose job is not enabled, and enqueue refuses E_JOB_DISABLED, so the definition stops for
  // real while its row and audit trail stay. `purge: true` = DELETE, which frees the id for
  // re-registration; it exists because disable alone left every machine-minted goal-scoped id
  // (`<goal>-workflow-start`, `seat-<goal>-<seat>`) burnt for the life of the store. Its three
  // guards live in the store, next to the transaction that has to hold them — see
  // `heartStore.deregisterJob`'s header for why deletion stopped being refused a surface.
  function handleDeregisterJob(payload, sender) {
    // STRICT SCHEMA FIRST, matching every sibling handler — and load-bearing for
    // probe-intent-drift.js, which proves this case exists by sending one unknown field.
    for (const key of Object.keys(payload)) {
      if (!DEREGISTER_ALLOWED_KEYS.has(key)) {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }

    // Re-checked here, never trusted from the gateway (DEC-3).
    if (typeof payload.job_id !== 'string' || payload.job_id.length === 0) {
      throw new InternalApiError(VALIDATION_FAILED, 'job_id must be a non-empty string', { check: 'job_id-shape', field: 'job_id' });
    }
    // Same re-check on the destructive flag, and STRICT for the reason the gateway states: a
    // truthiness convention guessed wrong here deletes a row. Absent is false.
    if (payload.purge !== undefined && typeof payload.purge !== 'boolean') {
      throw new InternalApiError(VALIDATION_FAILED, 'purge must be a boolean', { check: 'purge-shape', field: 'purge' });
    }
    const purge = payload.purge === true;

    // Authorization BEFORE the store read, so a refused sender learns nothing about the
    // catalogue — including whether an id exists. Same policy as the create arm.
    const decision = authz.canDeregisterJob({ sender });
    if (!decision.allowed) {
      throw new InternalApiError(UNAUTHORIZED_SENDER, decision.reason, { check: 'authorization' });
    }

    // The store owns existence: an unknown id throws E_UNKNOWN_JOB, which the wire map
    // renders VALIDATION_FAILED. That refusal is the POINT of this intent — a stop path
    // that reported success over a job that does not exist would be worse than none.
    const row = heartStore.deregisterJob({ jobId: payload.job_id, purge });

    // Loud, owner-readable feedback (D21(3)) in the shape remove-job/register-job set.
    // `pending_queue_rows` is stated because a disable does NOT empty the queue: those
    // rows stay, deferred every tick, until someone runs `remove-job <queue-id>`.
    // `purged` rides as its own field rather than being inferred from `enabled: false` —
    // a disabled row and a deleted one are both "not enabled", and a caller writing a
    // teardown ledger must be able to tell "stopped" from "gone".
    return {
      deregistered: true,
      purged: row.purged === true,
      job_id: row.job_id,
      enabled: row.enabled === 1,
      was_enabled: row.was_enabled,
      pending_queue_rows: row.pending_queue_rows,
      homed: row.goal_name ? { goal: row.goal_name, seat: row.seat_name } : null,
    };
  }

  // ── live-feed (live-session-design.md §1/§4) ────────────────────────────────────────────────
  //
  // Feed one owner turn to the conversation's WARM session and answer with the reply. This is the
  // daemon's only synchronous, reply-carrying intent, and that is the ruling, not an accident:
  // §4 chose the direct feed precisely so the answer does not have to travel back through the
  // queue, a spawn and a 3s reply poll. The caller holds the request open for the length of one
  // turn (its own timeout bounds it; the manager's `turnTimeoutMs` bounds this side).
  //
  // ⚑ NO AUTHZ CALL, and that matches `enqueue-job` DELIBERATELY. A live feed can do strictly
  // LESS than an enqueue: it reaches only conversations that are already warm — sessions this
  // daemon itself launched, at seats it already admitted — and it can create nothing that an
  // `enqueue-job` from the same token could not create by the cold path. Gating it harder than
  // the verb it is an optimization OF would refuse the bridge the fast path to work it is already
  // authorized to do slowly.
  //
  // ⚑ IT FAILS SOFT, ALWAYS. Every refusal is `{ fed: false, reason }` with HTTP ok — never a
  // typed error — because the caller's correct response to every one of them is the same: take
  // the cold path. Rendering "this conversation is not warm" as an error would make the bridge's
  // normal, expected, majority case look like a fault in its logs.
  async function handleLiveFeed(payload, sender) {
    for (const key of Object.keys(payload)) {
      if (!LIVE_FEED_KEYS.has(key)) {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }
    if (typeof payload.conversation !== 'string' || !payload.conversation) {
      throw new InternalApiError(VALIDATION_FAILED, 'conversation must be a non-empty string', { check: 'conversation-shape', field: 'conversation' });
    }
    if (typeof payload.prompt !== 'string' || !payload.prompt) {
      throw new InternalApiError(VALIDATION_FAILED, 'prompt must be a non-empty string', { check: 'prompt-shape', field: 'prompt' });
    }
    if (!liveSessions) return { fed: false, reason: 'live-sessions-not-armed' };

    // The chain's `session_ref` is read from the STORE, never taken from the caller. That is what
    // stops a bridge from resuming a session it was never told about: it names an execution id it
    // already holds for its own conversation, and the daemon looks up what that execution is.
    let sessionRef = null;
    if (payload.exec_id != null) {
      const row = heartStore.getExecution(payload.exec_id);
      sessionRef = (row && row.session_ref) || null;
    }

    const out = await liveSessions.feed({
      conversationId: payload.conversation,
      workdir: payload.workdir || null,
      prompt: payload.prompt,
      sessionRef,
      start: payload.start === true,
    });

    if (!out.ok) {
      return { fed: false, reason: out.reason, unanswered: out.unanswered === true, warm: liveSessions.size() };
    }
    log('info', 'live-feed answered a warm turn', { conversation: payload.conversation, senderId: sender && sender.id, ms: out.ms, sessionId: out.sessionId });
    return { fed: true, reply: out.reply, is_error: out.isError === true, session_id: out.sessionId, session_ref: out.sessionRef, ms: out.ms, warm: liveSessions.size() };
  }

  // ── task 7.93 · the addressed-message door, WRITE half ────────────────────────────────────
  //
  // Its own COMPLETE re-validation clause (DEC-3: gateway origin is not trust), in the same order
  // every sibling handler uses: strict schema, then shape, then the write.
  //
  // ⚑ `sender` is STAMPED from the attested identity and is REFUSED from the wire (the strict
  // schema below rejects it as an unknown field). Same rule and same reason as `enqueued_by`: a
  // sender that could set it could forge the audit trail. This is what makes the door safe to
  // open to an ordinary agent token, and it is why no new authz predicate is minted here — the
  // act is exactly as consequential as `enqueue-job`, which is open to any authenticated sender,
  // and strictly less so than register-job/snooze/kill-session, which carry their own decisions.
  // ⚑ NO STORE CHANGE AND NO RECIPIENT COLUMN. `thread` carries the address (D39/D42) and the row
  // is written by the already-shipped recordMessage. A `completion` is deliberately NOT special-
  // cased here: the store's own completion path (its jobs_log stamp) is reached by passing the
  // type through untouched, exactly as the ticker's own callers do.
  function handleSendMessage(payload, sender) {
    for (const key of Object.keys(payload)) {
      if (!['type', 'thread', 'corpus'].includes(key)) {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }
    if (!MESSAGE_TYPES.has(payload.type)) {
      throw new InternalApiError(VALIDATION_FAILED, `send-message type must be ${[...MESSAGE_TYPES].join('|')} (got "${payload.type}")`, { check: 'type-enum', field: 'type' });
    }
    if (typeof payload.thread !== 'string' || payload.thread.length === 0) {
      throw new InternalApiError(VALIDATION_FAILED, 'send-message requires a non-empty thread', { check: 'thread-shape', field: 'thread' });
    }
    if (typeof payload.corpus !== 'string') {
      throw new InternalApiError(VALIDATION_FAILED, 'send-message requires a string corpus', { check: 'corpus-shape', field: 'corpus' });
    }
    // A `completion` requires a status the door has no field for, and inventing one would be a
    // fourth payload field this task does not need. Refused explicitly rather than handed to the
    // store to fail with a message about a field the caller was never offered.
    if (payload.type === 'completion') {
      throw new InternalApiError(VALIDATION_FAILED, 'send-message does not carry completions — a completion needs a status (done|blocked|failed) and a turn to stamp, which this door has no field for', { check: 'completion-not-carried', field: 'type' });
    }
    const senderId = (sender && sender.id) || 'unknown';
    const row = heartStore.recordMessage({
      type: payload.type, sender: senderId, thread: payload.thread, corpus: payload.corpus,
    });
    log('info', 'send-message accepted', { thread: payload.thread, type: payload.type, senderId, msgId: row && row.msg_id });
    return { sent: true, msg_id: row && row.msg_id, thread: payload.thread, type: payload.type, sender: senderId };
  }

  // ── task 7.771 · the owner's answer, recorded on the coordination bus ─────────────────────
  //
  // Its own COMPLETE re-validation clause (DEC-3: gateway origin is not trust), in the same order
  // every sibling handler uses: strict schema, then shape, then authorization, then the act.
  //
  // ⚑ THE TWO NAMES ARE RE-CHECKED HERE. They arrived from an internet-facing component and become
  // PATH SEGMENTS under `.rbtv/goals/`, so the front door's copy is not the only thing between a
  // traversal and a directory read. `engine/bus-answer.js` checks them a THIRD time against the
  // module that owns the constant (`bus-ferry#isSafeName`) and then asks disk whether the goal and
  // the seat actually exist — the questions the gateway holds no handle for and must not grow one.
  // ⚑ NOTHING HERE WRITES THE BUS. `coordination/messages.md` has exactly one writer, `coord.py`.
  // ⚑ AUTHORIZATION IS BRIDGE-ONLY and is asked in the ONE policy module, never as an `if` here.
  async function handleRecordBusAnswer(payload, sender) {
    for (const key of Object.keys(payload)) {
      if (!['goal', 'seat', 'corpus'].includes(key)) {
        throw new InternalApiError(VALIDATION_FAILED, `unknown payload field: ${key}`, { check: 'strict-schema', field: key });
      }
    }
    for (const key of ['goal', 'seat']) {
      if (typeof payload[key] !== 'string' || !BUS_NAME_RE.test(payload[key])) {
        throw new InternalApiError(VALIDATION_FAILED, `record-bus-answer ${key} must be a bare name (no path separators, no "..", no control characters)`, { check: 'name-shape', field: key });
      }
    }
    if (typeof payload.corpus !== 'string' || payload.corpus.trim().length === 0) {
      throw new InternalApiError(VALIDATION_FAILED, 'record-bus-answer requires a non-empty corpus', { check: 'corpus-shape', field: 'corpus' });
    }

    const decision = authz.canRecordBusAnswer({ sender });
    if (!decision.allowed) {
      throw new InternalApiError(UNAUTHORIZED_SENDER, decision.reason, { check: 'authorization' });
    }
    if (!workspaceRoot) {
      throw new InternalApiError(INTERNAL, 'this daemon has no workspace root, so it can reach no goal bus', { check: 'workspace-root' });
    }

    const out = await recordBusAnswer({
      workspaceRoot, goal: payload.goal, seat: payload.seat, corpus: payload.corpus,
    });
    if (!out.recorded) {
      // A REFUSAL AS DATA, not a throw — and deliberately not a typed error either. The caller's
      // delivery has already happened; its job on this result is to LOG, never to change course
      // (the bookkeeping must not be able to undo the act). A typed error would be reported to the
      // owner as a failed reply, which would be a lie about a message that landed.
      log('warn', 'record-bus-answer did NOT record a row — the reply was still delivered', {
        goal: payload.goal, seat: payload.seat, senderId: sender && sender.id, reason: out.reason, detail: out.detail || out.error || null,
      });
      return { recorded: false, reason: out.reason, goal: payload.goal, seat: payload.seat };
    }
    log('info', 'recorded the owner\'s answer on the coordination bus', {
      goal: payload.goal, seat: payload.seat, msgId: out.msgId, re: out.re, senderId: sender && sender.id,
    });
    return { recorded: true, msg_id: out.msgId, re: out.re, goal: payload.goal, seat: payload.seat };
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
        case 'kill-session': result = await handleKillSession(env.payload, env.sender); break;
        case 'register-job': result = handleRegisterJob(env.payload, env.sender); break;
        case 'deregister-job': result = handleDeregisterJob(env.payload, env.sender); break;
        case 'live-feed': result = await handleLiveFeed(env.payload, env.sender); break;
        case 'send-message': result = handleSendMessage(env.payload, env.sender); break;
        case 'record-bus-answer': result = await handleRecordBusAnswer(env.payload, env.sender); break;
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

// STORE_TO_WIRE + NOT_WIRE_REACHABLE are exported as DATA for probe-error-map-drift.js (the
// batch-08 item 7 decay guard) — read-only introspection; no caller mutates them.
// INTENTS is exported as DATA for probe-intent-drift.js (the batch-08 item 5 lockstep guard,
// task 7.16): the closed intent set is duplicated BY DESIGN across the DEC-4 boundary
// (gateway/parse.js holds its own copy — the gateway may not import core), so the probe must
// read this gate's copy here. Read-only introspection; no caller mutates it.
module.exports = { createInternalApi, ENVELOPE_VERSION, assertSerializable, constantTimeEquals, STORE_TO_WIRE, NOT_WIRE_REACHABLE, INTENTS, INSPECT_TARGETS, EXEC_STATUSES };
