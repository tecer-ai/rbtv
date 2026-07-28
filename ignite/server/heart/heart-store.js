'use strict';

const { DatabaseSync } = require('node:sqlite');
const fs = require('node:fs');
const path = require('node:path');
const {
  HeartStoreError,
  E_SECOND_WRITER,
  E_UNKNOWN_JOB,
  E_JOB_DISABLED,
  E_BAD_ARGS,
  E_UNKNOWN_PROFILE,
  E_UNKNOWN_TOOL,
  E_UNKNOWN_WORKFLOW,
  E_BAD_MESSAGE,
  E_BAD_TRIGGER,
  E_BAD_MODE,
  E_QUEUE_ROW_NOT_FOUND,
  E_JOB_EXISTS,
} = require('./errors');
const { minutesToTicks } = require('./warnings');

const SCHEMA_SQL = fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf8');
const { migrate, isFreshStore } = require('./migrations');

const ACTION_TYPES = new Set(['launch-agent', 'fire-tool', 'start-workflow', 'send-message']);

// The arguments each action type STRUCTURALLY REQUIRES — the same set validateArgs() enforces at
// enqueue, named once so registration and the `fireable` projection cannot drift from it.
//
// Campaign issue S-2(a): `args_schema` defaults to `{}` and registration is CREATE-ONLY, so a
// fire-tool job could register, report `enabled=1` forever, and be structurally unable to EVER
// fire — an empty schema forbids the very `tool` argument fire-tool requires, every enqueue died
// "unknown argument: tool", and there is no update or unregister surface to repair it with. Two
// such ids exist live on this box and cannot be removed. The masking is worth recording: because
// validateArgs() runs BEFORE the catalogue lookup on the same path, the schema failure fires first
// and hides the tool check entirely — which is why an observer testing this reasonably concluded
// the tool name was never validated at all. It is (E_UNKNOWN_TOOL); it was simply unreachable.
const REQUIRED_ARGS_BY_ACTION = Object.freeze({
  'launch-agent': Object.freeze(['profile']),
  'fire-tool': Object.freeze(['tool']),
  'start-workflow': Object.freeze(['workflow']),
  'send-message': Object.freeze(['type', 'thread', 'corpus']),
});

// Can this catalogue row ever actually FIRE, as opposed to merely EXISTING and reading enabled=1?
// `enabled` is evidence a row EXISTS; it has never been evidence the row can RUN, and the whole of
// S-2 is that the false claim was made by a status field. Pure and read-only: it takes a job row
// and answers, so `inspect jobs` reports the distinction instead of implying it.
function jobFireability(job) {
  if (!job || !job.enabled) {
    return { fireable: false, reason: 'disabled' };
  }
  const needed = REQUIRED_ARGS_BY_ACTION[job.action_type] || [];
  let declared;
  try {
    declared = parseArgsSchema(job.args_schema).required;
  } catch {
    return { fireable: false, reason: 'args_schema is unparseable, so every enqueue of this id fails' };
  }
  const missing = needed.filter((key) => !(key in declared));
  if (missing.length) {
    return {
      fireable: false,
      reason: `args_schema declares no ${missing.map((k) => `\`${k}\``).join(', ')} — ` +
        `${job.action_type} requires ${missing.length > 1 ? 'them' : 'it'}, so every enqueue is ` +
        `refused "unknown argument". Registration is create-only with no update or unregister ` +
        `surface, so this id CANNOT be repaired in place: register a new one and stop using this.`,
    };
  }
  return { fireable: true, reason: null };
}
const MESSAGE_TYPES = new Set(['completion', 'ask', 'answer', 'verdict', 'note']);
const SESSION_MODES = new Set(['headless', 'headed']);

// ── Task 7.46 · the two levels, as two enums that share no value.
//
// SESSION states live on `sessions.status`; TURN states live on `jobs_log.status`. Keeping them
// disjoint is what makes a mis-levelled write a REFUSAL rather than a wrong answer — the failure
// mode a `level` column would have had is a forgotten filter returning plausible rows.
const SESSION_STATUSES = new Set(['alive', 'closed', 'killed', 'crashed']);
const TERMINAL_SESSION_STATUSES = new Set(['closed', 'killed', 'crashed']);

// ⚠ `killed` is HERE, in the turn set, and it does not belong to the level conceptually — it is a
// session-level word. It stays writable on a turn because the LIVE kill path writes it
// (spawn/spawn.js) and dispatch.js reads it back; refusing it tonight would be a runtime change,
// and this task is bookkeeping. The kill path now ALSO records the session-level kill on
// `sessions.status`, which is where the meaning actually belongs. Residual filed, not hidden:
// retiring the turn-level `killed` is a change to the kill path plus a rebuild-capable migration
// (see schema.sql's note on why the CHECK cannot be rebuilt inside a migration transaction).
const TURN_STATUSES = new Set(['launching', 'running', 'done', 'blocked', 'failed', 'stalled', 'killed']);

// A turn that HAS REPORTED. ⚠ `stalled` is deliberately absent: it means "the owner should look",
// never "the work is over" (owner ruling 2026-07-20), and a stalled turn's session is still alive —
// so a stalled row stays in the crash sweep's swept set exactly as it always did.
const TERMINAL_TURN_STATUSES = new Set(['done', 'blocked', 'failed', 'killed']);

// The session state implied by a ONE-SHOT session whose turn ended this way. Exported because the
// derivation belongs to the store rather than to whoever happened to observe the end: recordMessage
// uses it below, and the ticker's crash sweep uses it when it finds a process gone under a turn
// that had already reported (G-222).
// ⚠ It is not the only spelling in the tree — ticker.js's endTurnAndSession maps `blocked` to
// `crashed` where this maps it to `closed`. That disagreement PREDATES this function; it is filed,
// not silently rewired here, because changing it is a behaviour change on an accepted path.
function sessionStatusForEndedTurn(turnStatus) {
  if (turnStatus === 'killed') return 'killed';
  return turnStatus === 'failed' ? 'crashed' : 'closed';
}

const TRIGGER_KINDS = new Set(['scheduled', 'periodic']);
const VALID_PRIMITIVE_TYPES = new Set(['string', 'integer', 'number', 'boolean', 'object', 'array']);

let singleton = null;

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function toIsoUtc(d) {
  if (!(d instanceof Date)) d = new Date(d);
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function parseIsoUtc(s) {
  if (typeof s !== 'string') return null;
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(s)) return null;
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return null;
  return d;
}

// The SHAPE half of an args_schema, extracted from validateArgs so registration
// (task 7.12) and enqueue validate a schema through the SAME code, never a second
// implementation. Returns the parsed `{ required, optional }` maps.
//
// ⚑ SHAPE ONLY — deliberately. It does NOT check that each DECLARED type is a valid
// primitive: enqueue has always checked a declared type lazily, on the args a caller
// actually supplied (a bogus type declared for an absent optional arg passes there),
// and tightening that here would change certified enqueue behaviour. Registration
// wants the strict check, so it calls validateSchemaTypes below as well — the extra
// strictness lives at the new door, not inside the old one.
function parseArgsSchema(schemaJson) {
  let schema;
  try {
    schema = JSON.parse(schemaJson);
  } catch {
    throw new HeartStoreError(E_BAD_ARGS, 'args_schema is not valid JSON', { field: 'args_schema' });
  }
  if (schema === null || typeof schema !== 'object' || Array.isArray(schema)) {
    throw new HeartStoreError(E_BAD_ARGS, 'args_schema must be a JSON object', { field: 'args_schema' });
  }

  const required = schema.required || {};
  const optional = schema.optional || {};
  if (typeof required !== 'object' || Array.isArray(required) || typeof optional !== 'object' || Array.isArray(optional)) {
    throw new HeartStoreError(E_BAD_ARGS, 'args_schema.required and args_schema.optional must be objects', { field: 'args_schema' });
  }
  return { required, optional };
}

// Registration-time strictness (task 7.12): the schema a job is registered with must
// be one a future enqueue can actually satisfy. A job whose schema is malformed
// poisons EVERY future enqueue of that job, and — because registration is create-only
// with no update or unregister surface in v1 — a bad schema PERMANENTLY BURNS the
// catalogue id: the only repair is a direct database write on the box, the exact
// out-of-band path this intent exists to close. So the door that accepts the schema is
// the only honest place to refuse it. Three checks, all registration-only:
//
//   (1) UNKNOWN TOP-LEVEL KEYS are refused. `parseArgsSchema` reads `required` and
//       `optional` and ignores everything else, so a one-character typo
//       (`"requried"`) registers happily and then rejects every enqueue with
//       "unknown argument" — the id is burnt with no in-band fix. Found by
//       adversarial review, 2026-07-25.
//   (2) `required`/`optional`, WHEN PRESENT, must really be objects. `parseArgsSchema`
//       coerces `null` to `{}` (`schema.required || {}`), so `{"required": null}`
//       would otherwise register and silently mean "no required args" — and the
//       heart-store spec states these must be objects.
//   (3) Every DECLARED type must be a valid primitive.
//
// ⚑ ALL THREE ARE REGISTRATION-ONLY, deliberately. `validateArgs`/`enqueue` keep the
// permissive reading for rows ALREADY in the catalogue (including any written
// out-of-band before this intent existed) — tightening there would change certified
// behaviour and could strand a live job. Strictness belongs at the new door.
const SCHEMA_TOP_LEVEL_KEYS = new Set(['required', 'optional']);

function validateSchemaTypes(schemaJson, { required, optional }) {
  let raw;
  try {
    raw = JSON.parse(schemaJson);
  } catch {
    // Unreachable in practice: parseArgsSchema already parsed this string and threw
    // on failure. Kept so this function is safe to call on its own terms.
    throw new HeartStoreError(E_BAD_ARGS, 'args_schema is not valid JSON', { field: 'args_schema' });
  }

  for (const key of Object.keys(raw)) {
    if (!SCHEMA_TOP_LEVEL_KEYS.has(key)) {
      throw new HeartStoreError(
        E_BAD_ARGS,
        `args_schema carries an unknown top-level key: ${key} (expected only "required" and "optional" — ` +
        `a typo here would register a job that can never be enqueued)`,
        { field: 'args_schema', key },
      );
    }
  }
  for (const where of SCHEMA_TOP_LEVEL_KEYS) {
    const value = raw[where];
    if (value !== undefined && (value === null || typeof value !== 'object' || Array.isArray(value))) {
      throw new HeartStoreError(
        E_BAD_ARGS,
        `args_schema.${where} must be an object when present`,
        { field: `args_schema.${where}` },
      );
    }
  }

  for (const [map, where] of [[required, 'required'], [optional, 'optional']]) {
    for (const key of Object.keys(map)) {
      const declared = map[key];
      if (!VALID_PRIMITIVE_TYPES.has(declared)) {
        // The declared value may be any JSON — stringify it so the message never
        // renders "[object Object]" (adversarial review, 2026-07-25).
        const shown = typeof declared === 'string' ? declared : JSON.stringify(declared);
        throw new HeartStoreError(
          E_BAD_ARGS,
          `args_schema.${where}.${key} declares an unknown type: ${shown}`,
          { field: `args_schema.${where}.${key}`, declared: shown },
        );
      }
    }
  }
}

function validateArgs(args, schemaJson, actionType) {
  let parsed;
  try {
    parsed = JSON.parse(args);
  } catch {
    throw new HeartStoreError(E_BAD_ARGS, 'args is not valid JSON', { field: 'args' });
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new HeartStoreError(E_BAD_ARGS, 'args must be a JSON object', { field: 'args' });
  }

  const { required, optional } = parseArgsSchema(schemaJson);

  for (const key of Object.keys(required)) {
    if (!(key in parsed)) {
      throw new HeartStoreError(E_BAD_ARGS, `missing required argument: ${key}`, { field: key });
    }
  }
  for (const key of Object.keys(parsed)) {
    if (!(key in required) && !(key in optional)) {
      throw new HeartStoreError(E_BAD_ARGS, `unknown argument: ${key}`, { field: key });
    }
    const expectedType = required[key] || optional[key];
    if (!VALID_PRIMITIVE_TYPES.has(expectedType)) {
      throw new HeartStoreError(E_BAD_ARGS, `unknown expected type for ${key}: ${expectedType}`, { field: key });
    }
    const value = parsed[key];
    let actualType = typeof value;
    if (Array.isArray(value)) actualType = 'array';
    if (value === null) actualType = 'null';
    if (actualType === 'number' && Number.isInteger(value)) actualType = 'integer';
    if (actualType !== expectedType && !(actualType === 'integer' && expectedType === 'number')) {
      throw new HeartStoreError(E_BAD_ARGS, `argument ${key} expected ${expectedType}, got ${actualType}`, { field: key, expected: expectedType, actual: actualType });
    }
  }

  if (actionType === 'launch-agent') {
    if (typeof parsed.profile !== 'string' || parsed.profile.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'launch-agent requires a non-empty profile argument', { field: 'profile' });
    }
  } else if (actionType === 'fire-tool') {
    if (typeof parsed.tool !== 'string' || parsed.tool.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'fire-tool requires a non-empty tool argument', { field: 'tool' });
    }
  } else if (actionType === 'start-workflow') {
    if (typeof parsed.workflow !== 'string' || parsed.workflow.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'start-workflow requires a non-empty workflow argument', { field: 'workflow' });
    }
  } else if (actionType === 'send-message') {
    // Dry-run contract: send-message reference check yields E_BAD_MESSAGE (not E_BAD_ARGS).
    if (typeof parsed.type !== 'string' || !MESSAGE_TYPES.has(parsed.type)) {
      throw new HeartStoreError(E_BAD_MESSAGE, 'send-message requires a valid CMP-8 type', { field: 'type' });
    }
    if (typeof parsed.thread !== 'string' || parsed.thread.length === 0) {
      throw new HeartStoreError(E_BAD_MESSAGE, 'send-message requires a non-empty thread', { field: 'thread' });
    }
    if (typeof parsed.corpus !== 'string') {
      throw new HeartStoreError(E_BAD_MESSAGE, 'send-message requires a corpus string', { field: 'corpus' });
    }
  }
}

function validateTrigger(req) {
  if (!TRIGGER_KINDS.has(req.triggerKind)) {
    throw new HeartStoreError(E_BAD_TRIGGER, `invalid trigger_kind: ${req.triggerKind}`, { field: 'triggerKind' });
  }
  const runAt = parseIsoUtc(req.runAt);
  if (runAt === null) {
    throw new HeartStoreError(E_BAD_TRIGGER, 'run_at must be fixed-width ISO-8601 UTC', { field: 'runAt' });
  }
  if (req.triggerKind === 'scheduled') {
    if (req.repeatRule !== null && req.repeatRule !== undefined) {
      parseCron(req.repeatRule);
    }
  } else if (req.triggerKind === 'periodic') {
    if (!Number.isInteger(req.intervalSeconds) || req.intervalSeconds <= 0) {
      throw new HeartStoreError(E_BAD_TRIGGER, 'periodic trigger requires a positive interval_seconds', { field: 'intervalSeconds' });
    }
    if (req.repeatRule !== null && req.repeatRule !== undefined) {
      throw new HeartStoreError(E_BAD_TRIGGER, 'periodic trigger must not have a repeat_rule', { field: 'repeatRule' });
    }
  }
  if (req.maxFires !== null && req.maxFires !== undefined) {
    if (!Number.isInteger(req.maxFires) || req.maxFires <= 0) {
      throw new HeartStoreError(E_BAD_TRIGGER, 'max_fires must be a positive integer', { field: 'maxFires' });
    }
    if (req.triggerKind !== 'periodic' && (req.repeatRule === null || req.repeatRule === undefined)) {
      throw new HeartStoreError(E_BAD_TRIGGER, 'max_fires requires a repeating trigger', { field: 'maxFires' });
    }
  }
}

function parseCronField(field, min, max) {
  const values = new Set();
  for (const part of field.split(',')) {
    if (part === '*') {
      for (let i = min; i <= max; i++) values.add(i);
    } else if (part.includes('/')) {
      const [range, step] = part.split('/');
      const stepNum = parseInt(step, 10);
      if (!Number.isInteger(stepNum) || stepNum <= 0) throw new Error('invalid step');
      let start = min;
      let end = max;
      if (range !== '*') {
        if (range.includes('-')) {
          [start, end] = range.split('-').map(x => parseInt(x, 10));
        } else {
          start = end = parseInt(range, 10);
        }
      }
      if (!Number.isInteger(start) || !Number.isInteger(end)) throw new Error('invalid range');
      for (let i = start; i <= end; i += stepNum) values.add(i);
    } else if (part.includes('-')) {
      const [start, end] = part.split('-').map(x => parseInt(x, 10));
      if (!Number.isInteger(start) || !Number.isInteger(end)) throw new Error('invalid range');
      for (let i = start; i <= end; i++) values.add(i);
    } else {
      const n = parseInt(part, 10);
      if (!Number.isInteger(n)) throw new Error('invalid number');
      values.add(n);
    }
  }
  for (const v of values) {
    if (v < min || v > max) throw new Error('value out of range');
  }
  return Array.from(values).sort((a, b) => a - b);
}

function parseCron(expr) {
  if (typeof expr !== 'string' || expr.trim().length === 0) throw new Error('empty cron');
  const parts = expr.trim().split(/\s+/);
  if (parts.length !== 5) throw new Error('cron must have 5 fields');
  const minute = parseCronField(parts[0], 0, 59);
  const hour = parseCronField(parts[1], 0, 23);
  const dayOfMonth = parseCronField(parts[2], 1, 31);
  const month = parseCronField(parts[3], 1, 12);
  let dayOfWeek = parseCronField(parts[4], 0, 7).map(v => v === 7 ? 0 : v);
  dayOfWeek = Array.from(new Set(dayOfWeek)).sort((a, b) => a - b);
  // Vixie day-field semantics: dom and dow are ORed only when BOTH are restricted
  // (neither is '*'); if either is '*' they are ANDed (the '*' field always matches).
  const domRestricted = parts[2] !== '*';
  const dowRestricted = parts[4] !== '*';
  return { minute, hour, dayOfMonth, month, dayOfWeek, domRestricted, dowRestricted };
}

function nextCronUtc(after, expr) {
  const cron = parseCron(expr);
  let cursor = new Date(after);
  cursor.setUTCSeconds(0, 0);
  cursor.setUTCMinutes(cursor.getUTCMinutes() + 1);

  for (let safety = 0; safety < 366 * 24 * 60 + 10; safety++) {
    const m = cursor.getUTCMinutes();
    const h = cursor.getUTCHours();
    const dom = cursor.getUTCDate();
    const mon = cursor.getUTCMonth() + 1;
    const dow = cursor.getUTCDay();

    if (!cron.minute.includes(m) || !cron.hour.includes(h) || !cron.month.includes(mon)) {
      cursor.setUTCMinutes(cursor.getUTCMinutes() + 1);
      continue;
    }
    const domMatch = cron.dayOfMonth.includes(dom);
    const dowMatch = cron.dayOfWeek.includes(dow);
    const dayMatch = (cron.domRestricted && cron.dowRestricted)
      ? (domMatch || dowMatch)
      : (domMatch && dowMatch);
    if (!dayMatch) {
      cursor.setUTCMinutes(cursor.getUTCMinutes() + 1);
      continue;
    }
    return toIsoUtc(cursor);
  }
  throw new Error('cron next occurrence not found within one year');
}

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

// The DAEMON passes `dbPath: {data_root}/heart.db` — the heart store is PER-MACHINE
// state (batch-08 item 10 state-layout boundary, owner-ruled 2026-07-20), never under
// the workspace's `.rbtv/`. The `runtimeStateRoot` branch below is the store's
// pre-ruling workspace-shaped resolution, kept ONLY for store-scoped probes that
// exercise the `.rbtv/`-sibling session-dir derivation (D58(3)) against throwaway
// workspaces; server/index.js no longer uses it.
function resolveDbPath(opts) {
  if (opts.dbPath) return path.resolve(opts.dbPath);
  if (opts.runtimeStateRoot) {
    return path.resolve(opts.runtimeStateRoot, '.rbtv', 'heart', 'heart.db');
  }
  throw new Error('openHeartStore requires dbPath or runtimeStateRoot');
}

class HeartStore {
  constructor(opts = {}) {
    if (singleton) {
      throw new HeartStoreError(E_SECOND_WRITER, 'heart store writer already open in this process');
    }
    this.dbPath = resolveDbPath(opts);
    ensureDir(path.dirname(this.dbPath));

    this.db = new DatabaseSync(this.dbPath);
    singleton = this;

    // G-135: asked BEFORE schema.sql runs, and it can ONLY be asked here. Afterwards every store
    // has the six tables and a brand-new one is indistinguishable from a months-old one — which is
    // exactly why a schema change could never tell them apart and silently reached only the new.
    const fresh = isFreshStore(this.db);

    this.db.exec('PRAGMA journal_mode = WAL;');
    this.db.exec(SCHEMA_SQL);
    // schema.sql is six CREATE TABLE IF NOT EXISTS, so against an EXISTING store it has just done
    // nothing at all. Everything that brings such a store forward happens here instead.
    this.migration = migrate(this.db, { fresh });
    this.db.exec('PRAGMA foreign_keys = ON;');
    this.db.exec('PRAGMA busy_timeout = 5000;');
    this.db.exec('PRAGMA synchronous = NORMAL;');

    this.config = {
      profiles: opts.profiles || {},
      tools: opts.tools || {},
      workflows: opts.workflows || {},
      // The live ticker cadence, handed in by the composition root like every other
      // configured value: the minutes→ticks conversion below reads it so a snooze
      // means the same wall-clock duration at any tick_interval_ms. Absent → the
      // ticker's own 10 s default (warnings.js).
      tick_interval_ms: opts.tickIntervalMs,
    };
  }

  _prepare(sql) {
    return this.db.prepare(sql);
  }

  close() {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
    if (singleton === this) singleton = null;
  }

  // Catalogue registration — the write behind the `register-job` intent (task 7.12).
  //
  // ── CREATE-ONLY (owner ruling 2026-07-25, Call 2) ────────────────────────────
  // This method WAS an upsert (`ON CONFLICT(job_id) DO UPDATE`). It is not any
  // more, and the removal is the ruling, not a tidy-up: for the surface that
  // defines what the daemon is CAPABLE of, a re-register that silently replaces a
  // row's action type, args schema, or enabled flag is the failure mode — a typo'd
  // id would quietly repoint a working job. A duplicate is now refused typed
  // (E_JOB_EXISTS) and the sender picks another id.
  //
  // UPDATE / REMOVAL / DISABLE have NO v1 surface and that is deliberate, not an
  // omission: changing or retiring a catalogue row stays an operator action on the
  // box until a future ruling adds `update-job`/`unregister-job` additively — the
  // same interim posture kill held before `kill-session` landed.
  //
  // ⚑ AUTHORIZATION IS NOT ASKED HERE. This is the data layer; the caller (the
  // internal API) owns policy — the D65(B) split p4-0 set for removeQueueRow.
  registerJob({ jobId, actionType, function: fn, argsSchema = '{}', description = null, enabled = 1, goalName = null, seatName = null, createdAt, updatedAt, dryRun = false }) {
    if (typeof jobId !== 'string' || jobId.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'job_id must be a non-empty string', { field: 'jobId' });
    }
    if (!ACTION_TYPES.has(actionType)) {
      throw new HeartStoreError(E_BAD_ARGS, `invalid action_type: ${actionType}`, { field: 'actionType' });
    }
    if (typeof fn !== 'string' || fn.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'function must be a non-empty string', { field: 'function' });
    }
    if (typeof argsSchema !== 'string') {
      throw new HeartStoreError(E_BAD_ARGS, 'args_schema must be a JSON string', { field: 'argsSchema' });
    }
    if (description !== null && typeof description !== 'string') {
      throw new HeartStoreError(E_BAD_ARGS, 'description must be a string or null', { field: 'description' });
    }
    // ── Task 7.12 · the job->seat pointer (owner ruling `r-job-seat-home`, 2026-07-27) ──────────
    // A job is only the TRIGGER; its action is homed as a SEAT in a goal. The pointer names the
    // goal and the seat and NOT the run — the run is resolved at FIRE time, because goal-serving
    // jobs are seats of the goal's LIVE run and retire with it.
    //
    // ⚠ THIS IS WHERE BOTH-OR-NEITHER IS ACTUALLY ENFORCED. `schema.sql` carries the same CHECK,
    // but a store brought forward by MIGRATION_JOB_SEAT_HOME cannot have it (SQLite's ALTER TABLE
    // adds no constraints), so on the live store this writer is the ONLY guard. Relying on the
    // CHECK alone would be a bound that holds exactly where it is tested and nowhere it matters —
    // G-135's lesson, one table over.
    if (goalName !== null && (typeof goalName !== 'string' || goalName.length === 0)) {
      throw new HeartStoreError(E_BAD_ARGS, 'goal_name must be a non-empty string or null', { field: 'goalName' });
    }
    if (seatName !== null && (typeof seatName !== 'string' || seatName.length === 0)) {
      throw new HeartStoreError(E_BAD_ARGS, 'seat_name must be a non-empty string or null', { field: 'seatName' });
    }
    if ((goalName === null) !== (seatName === null)) {
      const given = goalName === null ? 'seat_name' : 'goal_name';
      const missing = goalName === null ? 'goal_name' : 'seat_name';
      throw new HeartStoreError(
        E_BAD_ARGS,
        `${given} was given without ${missing} — the job->seat pointer is both or neither. `
        + 'A half-pointer resolves to nothing and would fail at FIRE time, which is the one moment '
        + 'no operator is watching; it is refused here instead. Omit both to leave the job unhomed '
        + '(it then uses the interim .rbtv/sessions/<exec-id>/ path).',
        { field: missing, goalName, seatName },
      );
    }

    // Schema SHAPE through the shared parser (the same code enqueue validates
    // with), then the registration-only strictness on every declared type.
    validateSchemaTypes(argsSchema, parseArgsSchema(argsSchema));

    if (this.getJob(jobId)) {
      throw new HeartStoreError(E_JOB_EXISTS, `job already registered: ${jobId}`, { field: 'jobId', jobId });
    }

    // ── S-2(a): registration REFUSES a schema its own action type can never satisfy ──────────
    // Registration-only, and placed AFTER the duplicate check on purpose: an existing id is the
    // harder refusal and the certified E_JOB_EXISTS behaviour must not change shape underneath it.
    // Live rows are untouched — the permissive reading stays for anything already in the catalogue,
    // exactly as the three strictness checks above are scoped.
    //
    // WHY AT THIS DOOR AND NOWHERE ELSE: the id is BURNT the moment it lands. Create-only, no
    // update, no unregister, so the only repair is a direct database write on the box — the exact
    // out-of-band path this intent exists to close. And the row does not fail loudly: it reports
    // `enabled=1` forever while being structurally incapable of firing, so nothing downstream ever
    // contradicts it. The door that accepts the schema is the last honest place to refuse it.
    {
      const needed = REQUIRED_ARGS_BY_ACTION[actionType] || [];
      const declared = parseArgsSchema(argsSchema).required;
      const missing = needed.filter((key) => !(key in declared));
      if (missing.length) {
        throw new HeartStoreError(
          E_BAD_ARGS,
          `args_schema.required declares no ${missing.map((k) => `"${k}"`).join(', ')}, but ` +
          `${actionType} requires ${missing.length > 1 ? 'those arguments' : 'that argument'} at ` +
          `enqueue — so this job would register, report enabled=1, and be unable to EVER fire. ` +
          `Registration is create-only: there is no way to repair the id afterwards. ` +
          `Declare it, e.g. {"required":{"${missing[0]}":"string"}}.`,
          { field: 'args_schema', actionType, missing: missing.slice() },
        );
      }
    }

    // Validate-only mode (owner ruling 2026-07-25 Call 3; the D72/D73 model
    // verbatim): every check above — including the duplicate check — has already
    // run and PASSED. Return the verdict WITHOUT touching the single writer; the
    // catalogue row count is UNCHANGED. A failure has already thrown the SAME
    // typed error it throws on the real path, so the two paths refuse identically.
    if (dryRun) {
      return { dryRun: true, valid: true };
    }

    const now = createdAt || isoNow();
    const upd = updatedAt || now;
    const stmt = this._prepare(`
      INSERT INTO jobs (job_id, action_type, function, args_schema, description, enabled, goal_name, seat_name, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    stmt.run(jobId, actionType, fn, argsSchema, description, enabled ? 1 : 0, goalName, seatName, now, upd);
    return this.getJob(jobId);
  }

  getJob(jobId) {
    const stmt = this._prepare('SELECT * FROM jobs WHERE job_id = ?');
    return stmt.get(jobId) || null;
  }

  listJobs() {
    const stmt = this._prepare('SELECT * FROM jobs ORDER BY job_id');
    return stmt.all();
  }

  enqueue(req) {
    const job = this.getJob(req.jobId);
    if (!job) {
      throw new HeartStoreError(E_UNKNOWN_JOB, `unknown job: ${req.jobId}`, { jobId: req.jobId });
    }
    if (!job.enabled) {
      throw new HeartStoreError(E_JOB_DISABLED, `job disabled: ${req.jobId}`, { jobId: req.jobId });
    }

    const args = req.args !== undefined ? req.args : '{}';
    validateArgs(args, job.args_schema, job.action_type);

    const parsedArgs = JSON.parse(args);
    if (job.action_type === 'launch-agent') {
      if (!this.config.profiles[parsedArgs.profile]) {
        throw new HeartStoreError(E_UNKNOWN_PROFILE, `unknown launch profile: ${parsedArgs.profile}`, { profile: parsedArgs.profile });
      }
    } else if (job.action_type === 'fire-tool') {
      if (!this.config.tools[parsedArgs.tool]) {
        throw new HeartStoreError(E_UNKNOWN_TOOL, `unknown tool: ${parsedArgs.tool}`, { tool: parsedArgs.tool });
      }
    } else if (job.action_type === 'start-workflow') {
      if (!this.config.workflows[parsedArgs.workflow]) {
        throw new HeartStoreError(E_UNKNOWN_WORKFLOW, `unknown workflow: ${parsedArgs.workflow}`, { workflow: parsedArgs.workflow });
      }
    }

    validateTrigger(req);

    const sessionMode = req.sessionMode || 'headless';
    if (!SESSION_MODES.has(sessionMode)) {
      throw new HeartStoreError(E_BAD_MODE, `invalid session_mode: ${sessionMode}`, { field: 'sessionMode' });
    }
    if (sessionMode === 'headed') {
      if (job.action_type !== 'launch-agent') {
        throw new HeartStoreError(E_BAD_MODE, 'headed mode only allowed for launch-agent', { field: 'sessionMode' });
      }
      const profile = this.config.profiles[parsedArgs.profile];
      if (!profile || !profile.headed) {
        throw new HeartStoreError(E_BAD_MODE, `profile ${parsedArgs.profile} is not headed-capable`, { field: 'sessionMode', profile: parsedArgs.profile });
      }

      // ── QUEUE-TIME half of the headed prompt-carriage DOUBLE GATE ──────────
      // (session-surface-spec.md Design 3 + Behavior #9; OQ-F RULED D83; task p6-2b.)
      //
      // ADDITIVE: the headed-CAPABILITY check above is UNTOUCHED — this is its
      // sibling, not its replacement. The ruling requires a typed rejection at
      // queue time AND spawn time: the SPAWN half already lives in
      // server/pty/carriage.js (composeHeadedArgv → E_HEADED_PROMPT_REJECTED);
      // this is the QUEUE half, so a prompt the profile has no carriage for is
      // refused BEFORE a queue row exists — nothing is enqueued, nothing starts.
      //
      // WHERE THE PROMPT LIVES: `args.prompt` — the enqueue surface's own field.
      // A launch-agent job's args_schema declares it (`optional: { prompt:
      // 'string' }`), validateArgs() above has already type-checked it, and the
      // ticker's launchAgent reads exactly `args.prompt ?? null` and hands it to
      // the spawn path. So this gate reads the SAME value the spawn gate will.
      //
      // PROMPT-SUPPLIED TEST: mirrors composeHeadedArgv's test EXACTLY
      // (undefined / null / '' = not supplied), so the two gates can never
      // disagree — the queue must not refuse what the spawn path would accept.
      //
      // VOCABULARY: `headed.tui.prompt` ∈ argv | file | keystroke, `stdin`
      // structurally absent. All three gates (profile-LOAD in spawn/config.js,
      // this one, and the spawn-time one in pty/carriage.js) agree on that set;
      // presence of a carriage is the test here, never its value.
      //
      // CODE CHOICE — E_BAD_MODE, NOT a new E_HEADED_PROMPT_REJECTED. The store's
      // typed codes cross the wire through internal-api/dispatch.js's CLOSED
      // STORE_TO_WIRE map, and an UNMAPPED code degrades to INTERNAL "server-core
      // fault" (dispatch.js toWireError) — which would show a sender this
      // validation refusal as an internal fault instead of VALIDATION_FAILED.
      // dispatch.js and heart/errors.js are both outside p6-2b's allowlist, so a
      // new code could not be mapped in this change. E_BAD_MODE is the in-family
      // code the SIBLING headed check immediately above already uses, it maps to
      // VALIDATION_FAILED, and `details.check` + `carriage: null` name this exact
      // refusal on the wire. Minting the distinct code is a follow-up needing
      // errors.js + the dispatch map row together (surfaced in the p6-2b return).
      const promptSupplied = parsedArgs.prompt !== undefined
        && parsedArgs.prompt !== null
        && parsedArgs.prompt !== '';
      if (promptSupplied && !profile.headed.tui?.prompt) {
        throw new HeartStoreError(
          E_BAD_MODE,
          `profile ${parsedArgs.profile}: a prompt was supplied for a headed session but the profile ` +
          `declares NO headed.tui.prompt carriage — rejected by default (spec Design 3, Behavior #9)`,
          { field: 'sessionMode', profile: parsedArgs.profile, carriage: null },
        );
      }
    }

    // ── Validate-only mode (owner ruling D73 / D72) ──────────────────────────
    // ADDITIVE: when `dryRun` is truthy, the COMPLETE re-validation above has
    // already run and PASSED — return the verdict WITHOUT touching the single
    // writer. No INSERT, no rowid advance, the queue row count UNCHANGED. A check
    // FAILURE has already thrown the SAME typed HeartStoreError above, so the
    // dry-run failure path is byte-identical to the normal one. The default path
    // (no `dryRun`) falls straight through to the insert below, byte-behaviour
    // UNCHANGED — this branch is the ONLY addition (narrow single-round grant).
    if (req.dryRun) {
      return { dryRun: true, valid: true };
    }

    const enqueuedAt = req.enqueuedAt || isoNow();
    const stmt = this._prepare(`
      INSERT INTO queue (job_id, args, session_mode, trigger_kind, run_at, repeat_rule, interval_seconds, max_fires, enqueued_by, enqueued_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    const result = stmt.run(
      req.jobId,
      args,
      sessionMode,
      req.triggerKind,
      req.runAt,
      req.repeatRule === undefined ? null : req.repeatRule,
      req.intervalSeconds === undefined ? null : req.intervalSeconds,
      req.maxFires === undefined ? null : req.maxFires,
      req.enqueuedBy,
      enqueuedAt
    );
    return this.getQueueRow(Number(result.lastInsertRowid));
  }

  getQueueRow(queueId) {
    const stmt = this._prepare('SELECT * FROM queue WHERE queue_id = ?');
    return stmt.get(queueId) || null;
  }

  getQueueDue(now) {
    const stmt = this._prepare('SELECT * FROM queue WHERE run_at <= ? ORDER BY run_at, queue_id');
    return stmt.all(toIsoUtc(now));
  }

  listQueue() {
    const stmt = this._prepare('SELECT * FROM queue ORDER BY run_at, queue_id');
    return stmt.all();
  }

  // Sender-initiated removal of a PENDING queue row (p4-0 / D65(A)). The only
  // other DELETEs on `queue` are fire-path (one-shot fire, max_fires retirement).
  //
  // SEMANTICS — whole-row, and therefore: removing a REPEATING trigger's row
  // ends the WHOLE recurring schedule, not one occurrence. This is not a pick;
  // it is what the ratified contract admits. A repeating trigger is ONE row whose
  // `run_at` advances on fire, so "one pending occurrence" HAS NO ROW to delete;
  // `remove-job`'s ratified payload is `{ jobId }` with NO occurrence selector and
  // its result is the boolean `{ removed: true }`; and the store spec already
  // equates ending a repeating trigger with removing its queue row (§ Trigger
  // semantics, max_fires: "the trigger RETIRES: the queue row is removed").
  //
  // The removed row is RETURNED (never a bare boolean) so the caller can tell the
  // sender WHAT it just cancelled — the row carries `trigger_kind`/`repeat_rule`/
  // `interval_seconds`, which is what lets `ignite remove-job` be loud about
  // killing a recurrence (D21(3) loud feedback, BINDING acceptance).
  //
  // NOT this method's business: authorization (the caller owns policy — D65(B)),
  // and removable-state/in-flight checks (the internal API's re-validation). A
  // running execution is NEVER touched: `jobs_log` carries no FK to `queue` and
  // denormalizes `enqueued_by`/`action_type` at fire precisely so the audit
  // survives its queue row's deletion. Removal cancels FUTURE fires only.
  removeQueueRow({ queueId }) {
    if (!Number.isInteger(queueId)) {
      throw new HeartStoreError(E_BAD_ARGS, 'queue_id must be an integer', { field: 'queueId' });
    }
    this.db.exec('BEGIN EXCLUSIVE;');
    try {
      const row = this.getQueueRow(queueId);
      if (!row) {
        this.db.exec('ROLLBACK;');
        // Typed, never a silent no-op (internal-api-contract-spec.md:27).
        throw new HeartStoreError(E_QUEUE_ROW_NOT_FOUND, `queue row not found: ${queueId}`, { queueId });
      }
      this._prepare('DELETE FROM queue WHERE queue_id = ?').run(queueId);
      this.db.exec('COMMIT;');
      return row;
    } catch (err) {
      try { this.db.exec('ROLLBACK;'); } catch {}
      throw err;
    }
  }

  fireQueueRow({ queueId, now, tick, parentExecId = null }) {
    const firedAt = toIsoUtc(now);
    this.db.exec('BEGIN EXCLUSIVE;');
    try {
      const queue = this.getQueueRow(queueId);
      if (!queue) {
        this.db.exec('ROLLBACK;');
        return null;
      }
      if (queue.run_at > firedAt) {
        this.db.exec('ROLLBACK;');
        return null;
      }

      if (parentExecId !== null) {
        const parent = this._prepare('SELECT exec_id FROM jobs_log WHERE exec_id = ?').get(parentExecId);
        if (!parent) {
          this.db.exec('ROLLBACK;');
          throw new HeartStoreError(E_BAD_ARGS, `parent_exec_id does not exist: ${parentExecId}`, { field: 'parentExecId' });
        }
      }

      // Task 7.46: firing a queue row spawns a PROCESS, so it opens a SESSION, and the turn it
      // creates is that session's first. Today it is also its only one — the 1:1 degeneracy — and
      // that is what keeps every existing probe green: `listTurnsOfLiveSessions()` returns exactly
      // the set the old turn-status read returned, for as long as sessions and turns stay 1:1.
      const sessionPk = this._openSessionInTx({ sessionMode: queue.session_mode, openedAt: firedAt });

      const insertLog = this._prepare(`
        INSERT INTO jobs_log
          (parent_exec_id, queue_id, job_id, action_type, args, enqueued_by, session_mode, fired_tick, fired_at, status, session_pk)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'launching', ?)
      `);
      const logResult = insertLog.run(
        parentExecId,
        queue.queue_id,
        queue.job_id,
        queue.action_type || this.getJob(queue.job_id)?.action_type || 'launch-agent',
        queue.args,
        queue.enqueued_by,
        queue.session_mode,
        tick,
        firedAt,
        sessionPk
      );
      const execId = Number(logResult.lastInsertRowid);

      if (queue.trigger_kind === 'scheduled' && (queue.repeat_rule === null || queue.repeat_rule === undefined)) {
        this._prepare('DELETE FROM queue WHERE queue_id = ?').run(queueId);
      } else {
        let nextRunAt;
        if (queue.trigger_kind === 'periodic') {
          nextRunAt = toIsoUtc(new Date(now.getTime() + queue.interval_seconds * 1000));
        } else {
          nextRunAt = nextCronUtc(now, queue.repeat_rule);
        }
        let retired = false;
        if (queue.max_fires !== null && queue.max_fires !== undefined) {
          const countRow = this._prepare('SELECT COUNT(*) AS n FROM jobs_log WHERE queue_id = ?').get(queueId);
          if (countRow.n >= queue.max_fires) {
            this._prepare('DELETE FROM queue WHERE queue_id = ?').run(queueId);
            retired = true;
          }
        }
        if (!retired) {
          this._prepare('UPDATE queue SET run_at = ? WHERE queue_id = ?').run(nextRunAt, queueId);
        }
      }

      this.db.exec('COMMIT;');
      return this.getExecution(execId);
    } catch (err) {
      try { this.db.exec('ROLLBACK;'); } catch {}
      throw err;
    }
  }

  recordExecutionStart({ queueId = null, jobId, actionType, args, enqueuedBy, sessionMode = 'headless', firedTick, firedAt, parentExecId = null, sessionId = null, pid = null, profile = null, workdir = null }) {
    const firedAtIso = toIsoUtc(firedAt);
    this.db.exec('BEGIN EXCLUSIVE;');
    try {
      if (parentExecId !== null) {
        const parent = this._prepare('SELECT exec_id FROM jobs_log WHERE exec_id = ?').get(parentExecId);
        if (!parent) {
          this.db.exec('ROLLBACK;');
          throw new HeartStoreError(E_BAD_ARGS, `parent_exec_id does not exist: ${parentExecId}`, { field: 'parentExecId' });
        }
      }
      // Task 7.46 — same as fireQueueRow: a recorded start is a spawned process, so it opens a
      // session and the new turn is that session's first.
      const sessionPk = this._openSessionInTx({ sessionId, sessionMode, openedAt: firedAtIso });

      const stmt = this._prepare(`
        INSERT INTO jobs_log
          (parent_exec_id, queue_id, job_id, action_type, args, enqueued_by, session_mode, fired_tick, fired_at, status, session_id, pid, profile, workdir, session_pk)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'launching', ?, ?, ?, ?, ?)
      `);
      const result = stmt.run(
        parentExecId,
        queueId,
        jobId,
        actionType,
        args,
        enqueuedBy,
        sessionMode,
        firedTick,
        firedAtIso,
        sessionId,
        pid,
        profile,
        workdir,
        sessionPk
      );
      const execId = Number(result.lastInsertRowid);
      this.db.exec('COMMIT;');
      return this.getExecution(execId);
    } catch (err) {
      try { this.db.exec('ROLLBACK;'); } catch {}
      throw err;
    }
  }

  // Chain-stable thread, DERIVED not stored (ratified DDL carries `thread` on messages
  // only; jobs_log tracks the turn chain via parent_exec_id). The thread is
  // `exec-<exec_id of the chain's FIRST execution>` — the root reached by walking
  // parent_exec_id up to NULL. Carried unchanged across seat-slot recycles.
  _chainThread(execId) {
    const root = this._prepare(`
      WITH RECURSIVE chain(exec_id, parent_exec_id) AS (
        SELECT exec_id, parent_exec_id FROM jobs_log WHERE exec_id = ?
        UNION ALL
        SELECT j.exec_id, j.parent_exec_id
          FROM jobs_log j JOIN chain c ON j.exec_id = c.parent_exec_id
      )
      SELECT exec_id FROM chain WHERE parent_exec_id IS NULL LIMIT 1
    `).get(execId);
    return root ? `exec-${root.exec_id}` : null;
  }

  _attachThread(row) {
    if (row) row.thread = this._chainThread(row.exec_id);
    return row;
  }

  getExecution(execId) {
    const stmt = this._prepare('SELECT * FROM jobs_log WHERE exec_id = ?');
    return this._attachThread(stmt.get(execId) || null);
  }

  listExecutionsByStatus(status) {
    const stmt = this._prepare('SELECT * FROM jobs_log WHERE status = ? ORDER BY exec_id');
    return stmt.all(status).map((r) => this._attachThread(r));
  }

  // ────────────────────────────────────────────────────────────────────────────────────────────
  // Task 7.46 · SESSIONS — the second level. A session is the spawned process; a turn (a jobs_log
  // row) is one unit of work inside it. Today they are 1:1 for every session the daemon spawns
  // (a headless one-shot is a session with exactly ONE turn, R16); the split is what lets the
  // store REPRESENT a session that outlives its turn, which the flat enum could not express.
  //
  // THE STRUCTURAL GUARANTEE, and it is the criterion this task is judged on: no code path moves a
  // session out of `alive` except `closeSession()`. `updateExecutionStatus()` — the turn-end
  // write — does not touch this table at all. So "a session survives its turn's done/blocked
  // report" is a property of the call graph, not a policy anyone has to remember.
  // ────────────────────────────────────────────────────────────────────────────────────────────

  // Opens NO transaction of its own: the turn-creating paths already hold one, and a session and
  // its first turn must land together or not at all — a session with no turn is a ghost the crash
  // sweep would then chase.
  _openSessionInTx({ sessionId = null, sessionMode = 'headless', openedAt = null } = {}) {
    if (!SESSION_MODES.has(sessionMode)) {
      throw new HeartStoreError(E_BAD_MODE, `invalid session_mode: ${sessionMode}`, { field: 'sessionMode' });
    }
    const res = this._prepare(
      'INSERT INTO sessions (session_id, status, session_mode, opened_at) VALUES (?, ?, ?, ?)'
    ).run(sessionId, 'alive', sessionMode, openedAt ? toIsoUtc(openedAt) : isoNow());
    return Number(res.lastInsertRowid);
  }

  openSession(opts = {}) {
    return this.getSession(this._openSessionInTx(opts));
  }

  // The ONLY way out of `alive`. `status` is required and explicit — there is no default and
  // nothing is inferred from the session's turns, which is the whole point of the split.
  closeSession(sessionPk, { status, reason = null, closedAt = null } = {}) {
    if (!Number.isInteger(sessionPk)) {
      throw new HeartStoreError(E_BAD_ARGS, 'sessionPk must be an integer', { field: 'sessionPk' });
    }
    if (!TERMINAL_SESSION_STATUSES.has(status)) {
      throw new HeartStoreError(
        E_BAD_ARGS,
        `closeSession requires a terminal session status (${[...TERMINAL_SESSION_STATUSES].join('|')}), got: ${status}`,
        { field: 'status' }
      );
    }
    const row = this._prepare('SELECT session_pk FROM sessions WHERE session_pk = ?').get(sessionPk);
    if (!row) {
      throw new HeartStoreError(E_BAD_ARGS, `session does not exist: ${sessionPk}`, { field: 'sessionPk' });
    }
    // Scoped to `alive` so a re-close cannot rewrite the FIRST honest close (a crash sweep and a
    // late exit observation can both fire on one session; the first one saw the truth).
    this._prepare(
      'UPDATE sessions SET status = ?, closed_at = ?, close_reason = ? WHERE session_pk = ? AND status = ?'
    ).run(status, closedAt ? toIsoUtc(closedAt) : isoNow(), reason, sessionPk, 'alive');
    return this.getSession(sessionPk);
  }

  getSession(sessionPk) {
    return this._prepare('SELECT * FROM sessions WHERE session_pk = ?').get(sessionPk) || null;
  }

  listSessionsByStatus(status) {
    return this._prepare('SELECT * FROM sessions WHERE status = ? ORDER BY session_pk').all(status);
  }

  // The turns of one session, oldest first. A multi-turn session is exactly a session with more
  // than one of these; today every session has one.
  listTurnsOfSession(sessionPk) {
    return this._prepare('SELECT * FROM jobs_log WHERE session_pk = ? ORDER BY exec_id')
      .all(sessionPk).map((r) => this._attachThread(r));
  }

  // The turn rows of every session that is ALIVE — session-keyed, so callers asking a
  // session-liveness question (is the process there?) never read it out of turn status. The
  // ticker's crash sweep needs the turn row's process fields (pid, unit_name, session_id) and is
  // keyed by exec_id, so it gets rows; what makes this session-level is that `sessions.status` is
  // the ONLY predicate deciding membership.
  listTurnsOfLiveSessions() {
    return this._prepare(`
      SELECT j.* FROM jobs_log j
        JOIN sessions s ON s.session_pk = j.session_pk
       WHERE s.status = 'alive'
       ORDER BY j.exec_id
    `).all().map((r) => this._attachThread(r));
  }

  // How many automatic recycles the seat-slot's WHOLE turn chain has consumed:
  // walk parent_exec_id up to the chain root, then count every execution in the
  // root's descendant set that has a parent (a non-root node = one recycle).
  //
  // CHAIN-scoped, not node-scoped: every execution of a chain reports the same
  // number regardless of its own depth. That is the property that makes it a
  // budget — the slot persists across sessions (`seat-slot`), so the budget is
  // the chain's, never one execution's.
  //
  // This is the ONE determination of recycle-budget consumption. The ticker's
  // advance/re-dispatch gates and the ticker's warning check both read it here;
  // neither re-implements it (D44 — the arithmetic lives in the store, never
  // smeared across call sites).
  countChainRecycles({ execId }) {
    if (!Number.isInteger(execId)) {
      throw new HeartStoreError(E_BAD_ARGS, 'exec_id must be an integer', { field: 'execId' });
    }
    const rootRow = this._prepare(`
      WITH RECURSIVE chain(exec_id, parent_exec_id) AS (
        SELECT exec_id, parent_exec_id FROM jobs_log WHERE exec_id = ?
        UNION ALL
        SELECT j.exec_id, j.parent_exec_id
          FROM jobs_log j JOIN chain c ON j.exec_id = c.parent_exec_id
      )
      SELECT exec_id FROM chain WHERE parent_exec_id IS NULL LIMIT 1
    `).get(execId);
    const root = rootRow ? rootRow.exec_id : execId;
    const row = this._prepare(`
      WITH RECURSIVE descendants(exec_id, parent_exec_id) AS (
        SELECT exec_id, parent_exec_id FROM jobs_log WHERE exec_id = ?
        UNION ALL
        SELECT j.exec_id, j.parent_exec_id
          FROM jobs_log j JOIN descendants d ON j.parent_exec_id = d.exec_id
      )
      SELECT COUNT(*) AS n FROM descendants WHERE parent_exec_id IS NOT NULL
    `).get(root);
    return row ? row.n : 0;
  }

  // Budget ruling (p7-multiturn, owner 2026-07-18): a re-dispatch caused by a
  // real sender's message IS an owner action and never consumes the automatic
  // budget — only AUTOMATIC re-dispatches do, and "the automatic-recycle count
  // restarts on any owner action" (ticker-engine-spec § Budgets). AUTOMATIC
  // executions are identified by marker keys the ticker persists in their args
  // (the compaction turn and its answering re-dispatch); this count is the
  // number of CONSECUTIVE automatic executions at the chain's TAIL, in
  // dispatch (exec_id) order — a sender-triggered (unmarked) execution resets
  // it, and the chain root is never a recycle. This is the ONE determination
  // of the automatic budget (D44); countChainRecycles above remains the
  // chain-TOTAL reading the blocked-slot gate and warning check key on.
  countAutomaticChainRecycles({ execId, markerKeys }) {
    if (!Number.isInteger(execId)) {
      throw new HeartStoreError(E_BAD_ARGS, 'exec_id must be an integer', { field: 'execId' });
    }
    if (!Array.isArray(markerKeys) || markerKeys.length === 0 || !markerKeys.every((k) => typeof k === 'string' && k.length > 0)) {
      throw new HeartStoreError(E_BAD_ARGS, 'markerKeys must be a non-empty string array', { field: 'markerKeys' });
    }
    const rootRow = this._prepare(`
      WITH RECURSIVE chain(exec_id, parent_exec_id) AS (
        SELECT exec_id, parent_exec_id FROM jobs_log WHERE exec_id = ?
        UNION ALL
        SELECT j.exec_id, j.parent_exec_id
          FROM jobs_log j JOIN chain c ON j.exec_id = c.parent_exec_id
      )
      SELECT exec_id FROM chain WHERE parent_exec_id IS NULL LIMIT 1
    `).get(execId);
    const root = rootRow ? rootRow.exec_id : execId;
    const rows = this._prepare(`
      WITH RECURSIVE descendants(exec_id, parent_exec_id, args) AS (
        SELECT exec_id, parent_exec_id, args FROM jobs_log WHERE exec_id = ?
        UNION ALL
        SELECT j.exec_id, j.parent_exec_id, j.args
          FROM jobs_log j JOIN descendants d ON j.parent_exec_id = d.exec_id
      )
      SELECT exec_id, parent_exec_id, args FROM descendants ORDER BY exec_id
    `).all(root);
    let n = 0;
    for (let i = rows.length - 1; i >= 0; i--) {
      if (rows[i].parent_exec_id === null) break;
      let marked = false;
      try {
        const a = JSON.parse(rows[i].args);
        marked = a !== null && typeof a === 'object' && markerKeys.some((k) => a[k] === true);
      } catch {}
      if (!marked) break;
      n++;
    }
    return n;
  }

  // ⚠ Task 7.46 — THIS IS THE TURN-END WRITE AND IT DELIBERATELY NEVER TOUCHES `sessions`.
  // That absence is the structural guarantee the split rests on: a session survives its turn's
  // done/blocked report because NO CODE PATH HERE CAN END IT. A session leaves `alive` only
  // through `closeSession()`, called explicitly by whoever observed the process end.
  updateExecutionStatus(execId, { status, sessionId = null, pid = null, exitCode = null, completionMsgId = null, logPath = null, endedAt = null, carrier = null, unitName = null, pidStarttime = null, sessionRef = null, startedAt = null, profile = null, workdir = null }) {
    // Refuse a SESSION-level value on a turn row. Without this the two enums would be disjoint by
    // convention only, and the first mis-levelled write would land a plausible-looking row that
    // every turn query then reads as real.
    if (!TURN_STATUSES.has(status)) {
      throw new HeartStoreError(
        E_BAD_ARGS,
        SESSION_STATUSES.has(status)
          ? `'${status}' is a SESSION status and cannot be written to a turn (jobs_log.status). `
            + `Use closeSession() for the session level.`
          : `invalid turn status: ${status}`,
        { field: 'status' }
      );
    }
    const stmt = this._prepare(`
      UPDATE jobs_log SET
        status = ?,
        carrier = COALESCE(?, carrier),
        unit_name = COALESCE(?, unit_name),
        pid_starttime = COALESCE(?, pid_starttime),
        session_ref = COALESCE(?, session_ref),
        started_at = COALESCE(?, started_at),
        session_id = COALESCE(?, session_id),
        pid = COALESCE(?, pid),
        exit_code = COALESCE(?, exit_code),
        completion_msg_id = COALESCE(?, completion_msg_id),
        log_path = COALESCE(?, log_path),
        ended_at = COALESCE(?, ended_at),
        profile = COALESCE(?, profile),
        workdir = COALESCE(?, workdir)
      WHERE exec_id = ?
    `);
    stmt.run(status, carrier, unitName, pidStarttime, sessionRef, startedAt ? toIsoUtc(startedAt) : null, sessionId, pid, exitCode, completionMsgId, logPath, endedAt ? toIsoUtc(endedAt) : null, profile, workdir, execId);
    return this.getExecution(execId);
  }

  // ⚠ Task 7.46 · G-225 — END A TURN AND CLOSE ITS SESSION AS ONE ACT.
  //
  // Callers that observe a process end must write BOTH levels. Before this method they did it as
  // two statements — `updateExecutionStatus()` then `closeSession()` — with nothing around them, so
  // a failure or a daemon death BETWEEN the two left a TERMINAL TURN UNDER AN `alive` SESSION.
  // That is the exact state `G-222`'s crash sweep used to overwrite, and this window is the
  // DANGEROUS producer of it: the unclosed writers elsewhere only ever leave `failed` (noise),
  // while this one can leave a `done` — a real outcome, destroyed.
  //
  // ⚠⚠ THE GUARANTEE THIS DOES NOT WEAKEN, and the reason the cure is a NEW method rather than a
  // parameter on the turn-end write: `updateExecutionStatus()` still cannot touch `sessions`. That
  // absence is what lets a session outlive its turn at all (the whole point of the split), and it
  // is precisely what forced every caller into the two-statement shape. Removing the window by
  // letting the turn-end write close the session would remove the window AND the split. So the
  // session close stays an EXPLICIT act by whoever observed the process end — it has simply
  // stopped being a SEPARATE act.
  //
  // `sessionStatus` is required and explicit, exactly as `closeSession()` requires it: nothing is
  // inferred from the turn. The tree holds two different turn->session spellings (this file's
  // `sessionStatusForEndedTurn()` maps `blocked`->`closed`; ticker.js's wrapper maps it to
  // `crashed`), and that disagreement is FILED, not silently resolved here — making this method
  // pick one would be a behaviour change riding in on an atomicity fix.
  //
  // Argument validation is deliberately NOT duplicated ahead of the transaction: the turn status is
  // checked by `updateExecutionStatus()` and the session status by `closeSession()`, each in its
  // one home, and a refusal from either rolls the whole act back. Two copies of a rule are how a
  // defect survives one of them being fixed.
  endTurnAndCloseSession(execId, { turnStatus, sessionStatus, endedAt = null, reason = null, exitCode = null } = {}) {
    this.db.exec('BEGIN EXCLUSIVE;');
    try {
      const exec = this.updateExecutionStatus(execId, { status: turnStatus, endedAt, exitCode });
      let session = null;
      // A turn with no session is not an error: the row predates the split, or the caller is
      // ending something that was never spawned as a session. The turn write still stands.
      if (exec && exec.session_pk) {
        session = this.closeSession(exec.session_pk, { status: sessionStatus, reason, closedAt: endedAt });
      }
      this.db.exec('COMMIT;');
      return { exec, session };
    } catch (err) {
      try { this.db.exec('ROLLBACK;'); } catch { /* rollback best-effort */ }
      throw err;
    }
  }

  recordMessage({ type, sender, thread, corpus, status = null, createdAt, execId = null, exitCode = null }) {
    if (!MESSAGE_TYPES.has(type)) {
      throw new HeartStoreError(E_BAD_MESSAGE, `invalid message type: ${type}`, { field: 'type' });
    }
    if (typeof sender !== 'string' || sender.length === 0) {
      throw new HeartStoreError(E_BAD_MESSAGE, 'sender must be non-empty', { field: 'sender' });
    }
    if (typeof thread !== 'string' || thread.length === 0) {
      throw new HeartStoreError(E_BAD_MESSAGE, 'thread must be non-empty', { field: 'thread' });
    }
    if (typeof corpus !== 'string') {
      throw new HeartStoreError(E_BAD_MESSAGE, 'corpus must be a string', { field: 'corpus' });
    }
    if (type === 'completion' && !['done', 'blocked', 'failed'].includes(status)) {
      throw new HeartStoreError(E_BAD_MESSAGE, 'completion requires status done|blocked|failed', { field: 'status' });
    }
    if (execId !== null && !Number.isInteger(execId)) {
      throw new HeartStoreError(E_BAD_ARGS, 'execId must be an integer when given', { field: 'execId' });
    }
    const createdAtIso = createdAt ? toIsoUtc(createdAt) : isoNow();
    const insertSql = `
      INSERT INTO messages (type, sender, thread, corpus, status, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `;

    if (type !== 'completion') {
      const result = this._prepare(insertSql).run(type, sender, thread, corpus, status, createdAtIso);
      return this.getMessage(Number(result.lastInsertRowid));
    }

    // Completion path (task 7.7, owner ruling 2026-07-23 / heart-store-spec § Single-writer):
    // completion = messages INSERT + jobs_log UPDATE (status, completion_msg_id, ended_at)
    // in ONE transaction — a crash can never leave a finished job's completion message on
    // disk with its jobs_log row unstamped (the former recordMessage-then-resolveCompletion
    // two-transaction window). The ticker's routed_at_tick stamp deliberately stays a
    // ticker-side Advance update (D30 deferred ROUTING unchanged — recycle/wake decisions
    // remain the ticker's, at its own tick). The owning execution is the caller's `execId`
    // when given (the ticker's sweeps know their exec), else resolved from the thread with
    // the same determination Advance used (live execution in the chain first, else the most
    // recent terminal one for a duplicate/late report). A completion on an unknown/inactive
    // thread inserts the message alone — Advance's anomaly path routes it.
    this.db.exec('BEGIN EXCLUSIVE;');
    try {
      const result = this._prepare(insertSql).run(type, sender, thread, corpus, status, createdAtIso);
      const msgId = Number(result.lastInsertRowid);
      const exec = execId !== null ? this.getExecution(execId) : this._findCompletionExecution(thread);
      if (exec) {
        this._prepare(`
          UPDATE jobs_log SET status = ?, completion_msg_id = ?, ended_at = ?, exit_code = COALESCE(?, exit_code)
          WHERE exec_id = ?
        `).run(status, msgId, createdAtIso, exitCode, exec.exec_id);

        // ⚠⚠ STOP — THIS IS THE ONE LINE THAT KEEPS THE 1:1 DEGENERACY EXACT, AND DELETING IT IS
        // BARRED UNTIL THE SEAM ROWS ARE RESOLVED (task 7.81, `#barred`, 2026-07-28).
        //
        // The bar lives HERE and not only on the task, deliberately: the degeneracy is held by TWO
        // CODE SITES — `recordExecutionStart()` opens a session per turn, and this line closes it —
        // so a change that lets a session outlive its turn can arrive under ANY task, but it cannot
        // avoid touching this line. 7.81 is the discoverable anchor; this comment is the load-
        // bearing one.
        //
        // WHY IT IS BARRED, measured 2026-07-28: four live seams answer a SESSION question by
        // reading the TURN level, and at 1:1 the two levels return the same rows, so every probe is
        // green either way. They all change behaviour the moment this line goes:
        //   G-227  the retention sweep deletes a LIVE session's artifacts (data loss)
        //   G-228  a headed session is not reconnected after a daemon restart
        //   G-229  the boot orphan rescan leaves a ghost that the agent cap counts
        //   G-226  `live_agent_sessions` reports a turn count under a session name
        // Plus G-225 (a turn write and its session close are two statements, not one transaction).
        //
        // ⚠ THE PREVIOUS VERSION OF THIS COMMENT SAID "the line 7.32's multi-turn path will delete"
        // AND NAMED "the tmux path, 7.30/7.32" BELOW. BOTH ATTRIBUTIONS WERE FALSE and they were
        // measured false against the task store: 7.30 is DONE and did not remove the degeneracy
        // (its content is the tmux spawn target and containment); 7.32 is the goal-watcher-job and
        // the R4 restart path and touches this lifecycle nowhere. A reader following those numbers
        // landed on two rows that own none of this, with none of the seam knowledge above — and an
        // intention that reaches a code comment instead of a task reads as settled scope and
        // propagates: this seat repeated "7.30/7.32" three times on the strength of this comment.
        //
        // A turn-ending report does not, in itself, end a session — that is the whole point of the
        // split, and `updateExecutionStatus()` structurally cannot end one. But every session the
        // daemon spawns TODAY is a headless one-shot whose PROCESS exits at its report, so the
        // session really does end here. Closing it explicitly (rather than letting a later sweep
        // notice) is what makes `listTurnsOfLiveSessions()` return exactly the set the old
        // turn-status read returned — byte-identical behaviour, which is what keeps the existing
        // ticker and store probes green and what makes this task bookkeeping rather than a
        // runtime change.
        //
        // When a session can outlive its turn, this close moves to whoever observes the PROCESS
        // ending — and "nothing else in the store has to change" is true of the STORE and false of
        // its readers: see the four seam rows above, none of which is in this file.
        if (exec.session_pk) {
          this._prepare(
            'UPDATE sessions SET status = ?, closed_at = ?, close_reason = ? '
            + "WHERE session_pk = ? AND status = 'alive'"
          ).run(
            // ONE derivation, shared with the crash sweep's already-reported branch (G-222).
            sessionStatusForEndedTurn(status),
            createdAtIso,
            `turn ${exec.exec_id} reported '${status}' (one-shot session: the process ends here)`,
            exec.session_pk
          );
        }
      }
      this.db.exec('COMMIT;');
      return this.getMessage(msgId);
    } catch (err) {
      try { this.db.exec('ROLLBACK;'); } catch { /* rollback best-effort */ }
      throw err;
    }
  }

  // Resolve which execution a thread's completion belongs to — the SAME determination the
  // ticker's Advance made before task 7.7 moved the jobs_log stamp to record time: prefer
  // the chain's live execution (running/launching), else the most recent terminal one
  // (duplicate / late report). Returns the jobs_log row or null (unknown/inactive thread).
  _findCompletionExecution(thread) {
    if (typeof thread !== 'string' || !thread.startsWith('exec-')) return null;
    const rootId = parseInt(thread.slice(5), 10);
    if (!Number.isInteger(rootId)) return null;
    const rows = this._prepare(`
      WITH RECURSIVE descendants(exec_id, parent_exec_id) AS (
        SELECT exec_id, parent_exec_id FROM jobs_log WHERE exec_id = ?
        UNION ALL
        SELECT j.exec_id, j.parent_exec_id
          FROM jobs_log j JOIN descendants d ON j.parent_exec_id = d.exec_id
      )
      SELECT j.* FROM jobs_log j JOIN descendants d ON j.exec_id = d.exec_id ORDER BY j.exec_id
    `).all(rootId);
    for (const row of rows) {
      if (row.status === 'running' || row.status === 'launching') return row;
    }
    for (let i = rows.length - 1; i >= 0; i--) {
      if (['done', 'blocked', 'failed', 'stalled'].includes(rows[i].status)) return rows[i];
    }
    return null;
  }

  getMessage(msgId) {
    const stmt = this._prepare('SELECT * FROM messages WHERE msg_id = ?');
    return stmt.get(msgId) || null;
  }

  getMessages({ unroutedOnly = false, unbroadcastOnly = false, type = null, limit = null } = {}) {
    let sql = 'SELECT * FROM messages';
    const conds = [];
    const params = [];
    if (unroutedOnly) conds.push('routed_at_tick IS NULL');
    if (unbroadcastOnly) conds.push('broadcast_at_tick IS NULL');
    // Task 7.19: `{ unroutedOnly: true, type: 'completion' }` is the ticker's
    // bounded Advance fetch — matched by the partial index
    // idx_messages_unrouted_completion so per-tick work never scans the
    // accumulated message history.
    if (type !== null) {
      conds.push('type = ?');
      params.push(type);
    }
    if (conds.length) sql += ' WHERE ' + conds.join(' AND ');
    sql += ' ORDER BY msg_id';
    if (limit !== null) sql += ` LIMIT ${Number(limit)}`;
    const stmt = this._prepare(sql);
    return stmt.all(...params);
  }

  // resolveCompletion was RETIRED by task 7.7: the jobs_log stamp (status, completion_msg_id,
  // ended_at) now lands atomically with the completion INSERT in recordMessage above, and the
  // routed_at_tick stamp is the ticker Advance's own update (stampMessageRouted) — nothing is
  // left for a combined resolve to do.

  recordTick({ tick, ts, actionsJson = '[]' }) {
    const tsIso = ts ? toIsoUtc(ts) : isoNow();
    const stmt = this._prepare('INSERT INTO ticks (tick, ts, actions_json) VALUES (?, ?, ?)');
    stmt.run(tick, tsIso, actionsJson);
    return this.getTick(tick);
  }

  getTick(tick) {
    const stmt = this._prepare('SELECT * FROM ticks WHERE tick = ?');
    return stmt.get(tick) || null;
  }

  getLastTick() {
    const stmt = this._prepare('SELECT * FROM ticks ORDER BY tick DESC LIMIT 1');
    return stmt.get() || null;
  }

  getStandingWarning({ kind, subject }) {
    if (typeof kind !== 'string' || kind.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'kind must be non-empty string', { field: 'kind' });
    }
    if (typeof subject !== 'string' || subject.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'subject must be non-empty string', { field: 'subject' });
    }
    const stmt = this._prepare('SELECT * FROM warnings WHERE kind = ? AND subject = ? AND cleared_at_tick IS NULL');
    return stmt.get(kind, subject) || null;
  }

  raiseWarning({ kind, subject, raisedAtTick }) {
    if (typeof kind !== 'string' || kind.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'kind must be non-empty string', { field: 'kind' });
    }
    if (typeof subject !== 'string' || subject.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'subject must be non-empty string', { field: 'subject' });
    }
    if (!Number.isInteger(raisedAtTick)) {
      throw new HeartStoreError(E_BAD_ARGS, 'raised_at_tick must be an integer', { field: 'raisedAtTick' });
    }
    const existing = this.getStandingWarning({ kind, subject });
    if (existing) return existing;
    const stmt = this._prepare(`
      INSERT INTO warnings (kind, subject, raised_at_tick)
      VALUES (?, ?, ?)
    `);
    const result = stmt.run(kind, subject, raisedAtTick);
    return this._prepare('SELECT * FROM warnings WHERE warning_id = ?').get(result.lastInsertRowid);
  }

  announceWarning({ warningId, tick }) {
    if (!Number.isInteger(warningId)) {
      throw new HeartStoreError(E_BAD_ARGS, 'warning_id must be an integer', { field: 'warningId' });
    }
    if (!Number.isInteger(tick)) {
      throw new HeartStoreError(E_BAD_ARGS, 'tick must be an integer', { field: 'tick' });
    }
    const stmt = this._prepare('UPDATE warnings SET last_announced_tick = ? WHERE warning_id = ?');
    stmt.run(tick, warningId);
    return this._prepare('SELECT * FROM warnings WHERE warning_id = ?').get(warningId);
  }

  // Snooze a standing warning for `minutes` (D45: "the system converts minutes
  // → ticks"). The conversion lives HERE and nowhere else — callers pass
  // MINUTES and never a tick, so no call site ever duplicates the tick-rate
  // arithmetic (D44). That conversion derives from the LIVE configured cadence,
  // never a baked-in ticks-per-minute constant. The reference point is the last
  // recorded tick: a snooze arrives out-of-band between ticks, so "now" is the
  // most recent tick.
  // Suppresses announcement only — it NEVER clears (cleared_at_tick untouched).
  // Snoozing a (kind, subject) with no standing warning is a clean no-op: null,
  // never an error, never a phantom row.
  snoozeWarning({ kind, subject, minutes }) {
    if (typeof kind !== 'string' || kind.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'kind must be non-empty string', { field: 'kind' });
    }
    if (typeof subject !== 'string' || subject.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'subject must be non-empty string', { field: 'subject' });
    }
    if (!Number.isInteger(minutes) || minutes <= 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'minutes must be a positive integer', { field: 'minutes' });
    }
    const existing = this.getStandingWarning({ kind, subject });
    if (!existing) return null;
    const lastTick = this.getLastTick();
    const currentTick = lastTick ? lastTick.tick : 0;
    const snoozedUntilTick = currentTick + minutesToTicks(minutes, this.config.tick_interval_ms);
    const stmt = this._prepare('UPDATE warnings SET snoozed_until_tick = ? WHERE warning_id = ?');
    stmt.run(snoozedUntilTick, existing.warning_id);
    return this._prepare('SELECT * FROM warnings WHERE warning_id = ?').get(existing.warning_id);
  }

  clearWarning({ warningId, tick }) {
    if (!Number.isInteger(warningId)) {
      throw new HeartStoreError(E_BAD_ARGS, 'warning_id must be an integer', { field: 'warningId' });
    }
    if (!Number.isInteger(tick)) {
      throw new HeartStoreError(E_BAD_ARGS, 'tick must be an integer', { field: 'tick' });
    }
    const stmt = this._prepare('UPDATE warnings SET cleared_at_tick = ? WHERE warning_id = ? AND cleared_at_tick IS NULL');
    stmt.run(tick, warningId);
    return this._prepare('SELECT * FROM warnings WHERE warning_id = ?').get(warningId);
  }

  listWarnings({ kind = null, subject = null, standingOnly = false } = {}) {
    let sql = 'SELECT * FROM warnings WHERE 1=1';
    const params = [];
    if (kind !== null && kind !== undefined) {
      sql += ' AND kind = ?';
      params.push(kind);
    }
    if (subject !== null && subject !== undefined) {
      sql += ' AND subject = ?';
      params.push(subject);
    }
    if (standingOnly) {
      sql += ' AND cleared_at_tick IS NULL';
    }
    sql += ' ORDER BY raised_at_tick, warning_id';
    const stmt = this._prepare(sql);
    return stmt.all(...params);
  }

  dump() {
    return {
      jobs: this._prepare('SELECT * FROM jobs ORDER BY job_id').all(),
      queue: this._prepare('SELECT * FROM queue ORDER BY queue_id').all(),
      jobs_log: this._prepare('SELECT * FROM jobs_log ORDER BY exec_id').all().map((r) => this._attachThread(r)),
      messages: this._prepare('SELECT * FROM messages ORDER BY msg_id').all(),
      ticks: this._prepare('SELECT * FROM ticks ORDER BY tick').all(),
      warnings: this._prepare('SELECT * FROM warnings ORDER BY warning_id').all(),
    };
  }
}

function openHeartStore(opts) {
  return new HeartStore(opts);
}

function closeHeartStore() {
  if (singleton) singleton.close();
}

function isHeartStoreOpen() {
  return singleton !== null && singleton.db !== null;
}

module.exports = {
  jobFireability,
  REQUIRED_ARGS_BY_ACTION,
  openHeartStore,
  closeHeartStore,
  isHeartStoreOpen,
  HeartStore,
  HeartStoreError,
  E_QUEUE_ROW_NOT_FOUND,
  E_JOB_EXISTS,
  E_SECOND_WRITER,
  E_UNKNOWN_JOB,
  E_JOB_DISABLED,
  E_BAD_ARGS,
  E_UNKNOWN_PROFILE,
  E_UNKNOWN_TOOL,
  E_UNKNOWN_WORKFLOW,
  E_BAD_MESSAGE,
  E_BAD_TRIGGER,
  E_BAD_MODE,
  // Task 7.46 — the two enums, exported so a caller can ask which level a value belongs to
  // instead of hardcoding a list that drifts from the store's.
  SESSION_STATUSES,
  TERMINAL_SESSION_STATUSES,
  TURN_STATUSES,
  TERMINAL_TURN_STATUSES,
  sessionStatusForEndedTurn,
};
