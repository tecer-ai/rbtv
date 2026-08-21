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
  E_UNKNOWN_LAUNCH_SPEC,
  E_UNKNOWN_TOOL,
  E_UNKNOWN_WORKFLOW,
  E_BAD_MESSAGE,
  E_BAD_TRIGGER,
  E_BAD_MODE,
  E_QUEUE_ROW_NOT_FOUND,
  E_JOB_EXISTS,
  E_JOB_PURGE_REFUSED,
} = require('./errors');
const { minutesToTicks } = require('./warnings');

const SCHEMA_SQL = fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf8');
const { migrate, isFreshStore } = require('./migrations');
const { checkTemplateArgs, checkFireToolWorkdir } = require('./argv-template');

const ACTION_TYPES = new Set(['launch-agent', 'fire-tool', 'start-workflow', 'send-message']);

// The arguments each action type STRUCTURALLY REQUIRES — the same set validateArgs() enforces at
// enqueue, named once so registration and the `fireable` projection cannot drift from it.
//
// Campaign issue S-2(a) — ⚠ TRUE OF LEGACY ROWS ONLY, AND THAT SCOPE IS THE WHOLE POINT (G-258).
// The registration door below (search `args_schema.required declares no`) now REFUSES this shape
// outright, so the unfireable job described here CAN NO LONGER BE CREATED. What follows describes
// rows that landed BEFORE that guard existed; `jobFireability()` still exists to report them,
// which is exactly why this note reads as current when it is not.
//
// As it stood: `args_schema` defaults to `{}` and registration is CREATE-ONLY, so a fire-tool job
// could register, report `enabled=1` forever, and be structurally unable to EVER fire — an empty
// schema forbids the very `tool` argument fire-tool requires, every enqueue died "unknown
// argument: tool", and there is no update or unregister surface to repair it with. Two such ids
// exist live on this box and cannot be removed.
//
// ⚠ WHY THE SCOPE IS WRITTEN AT THE TOP RATHER THAN APPENDED: this comment was READ AND BELIEVED
// by a seat writing a probe control, which then reported a severity the code no longer supports.
// A stale comment is checked against nothing until somebody relies on it, and THE READER LEAST
// ABLE TO CATCH IT IS THE ONE WHO OPENED IT BECAUSE THEY DID NOT ALREADY KNOW. The masking is worth recording: because
// validateArgs() runs BEFORE the catalogue lookup on the same path, the schema failure fires first
// and hides the tool check entirely — which is why an observer testing this reasonably concluded
// the tool name was never validated at all. It is (E_UNKNOWN_TOOL); it was simply unreachable.
const REQUIRED_ARGS_BY_ACTION = Object.freeze({
  // 7.787 — EMPTY, and that is the pivot of `#d-abolish-profile-names`. `launch-agent` required
  // a non-empty `profile` string, and EVERY caller-facing `--profile` flag in ignite existed only
  // to satisfy it: the goal-lane marker's second token, `rbtv run --profile`, `cli add-job
  // --profile`, the chat bridge's `session_profile` ("decides NOTHING", its own comment). Sub-ruling
  // 2 empties the row instead: a launch carries NOTHING profile-shaped, and the daemon derives the
  // cast at spawn time from the seat's own descriptor, read per launch. Nothing on the wire can
  // drift from the binding because nothing on the wire says anything about it.
  'launch-agent': Object.freeze([]),
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
        `refused "unknown argument". Registration is create-only — there is no update surface, so this ` +
        `id CANNOT be repaired in place: register a new one and retire this one via deregister-job.`,
    };
  }
  return { fireable: true, reason: null };
}
// W4 — the vocabulary was CLOSED AT SEVEN; the D2 routed-types change (owner ruling, 2026-08-19)
// makes it EIGHT. `queue-request` (engine-internal: a judged milestone PASS asking for the next
// wave) and `escalation` (owner-directed: a halt the leader could not fix) joined the original
// five; `stuck` joins them as the SYSTEM-ROUTED blocked signal — an agent emits it typed and the
// routing table, not the agent, picks the recipient (always the `leader`). All EIGHT copies of
// this set move in ONE change — this one, `internal-api/dispatch.js`, `gateway/parse.js`,
// `bridges/chat/forward-path.js`, `coord.py`'s `MESSAGE_TYPES` + `TYPE_COLOR`, and `schema.sql`'s
// CHECK (rebuilt by migration 5, widened again by migration 7). A partial move is the D3 silent
// class rebuilt: the sender writes locally, the daemon door refuses, and the sender exits
// non-zero with the row already permanent in the append-only log.
const MESSAGE_TYPES = new Set(['completion', 'ask', 'answer', 'verdict', 'note', 'queue-request', 'escalation', 'stuck']);
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

// LE-13 Change 2 (2026-08-19) — the K in "K consecutive periodic-job failures escalates". Five
// consecutive misses of a 300 s (5 min) periodic job is 25 minutes of a recovery mechanism that is
// not recovering — long past a transient blip, short of the multi-hour silences this rule exists
// to catch (121 consecutive recorded `selfheal` failures, never escalated). A PROPOSAL, not a
// ruling — tune it here if it proves too eager or too slow in practice.
const PERIODIC_FAILURE_STREAK_K = 5;

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

// ── Task Q9 · THE IDEMPOTENT DOOR's key (owner-authorized ruling `d-q9-door`, 2026-08-08) ────────
//
// The (run, seat) a queue row DECLARES, as a comparable string — or null when the row names no
// seat at all. It is deliberately THE SAME DISJUNCTION the fire path resolves a home with
// (`ticker.js` resolveJobHome), minus the filesystem: a catalogue-homed job carries the pointer on
// `jobs.goal_name`/`jobs.seat_name`, an unhomed one carries it as `args.workdir`, and supplying
// BOTH is already a refusal at fire — so exactly one of them identifies the seat. Keying on
// anything else would let the door dedupe one seat while the ticker launched another.
//
// ⚠ THE RUN IS NOT IN THE `goal:` KEY, AND THAT IS THE POINT — not an omission. `r-job-seat-home`
// stores goal+seat and NEVER the run, because a goal-serving job is a seat of the goal's LIVE run
// and the run is resolved at FIRE time; pinning a run here would key the door to a run that later
// closes. Two pending rows for one homed job therefore resolve to the same run by construction,
// which is exactly the (run, seat) pair the ruling names. The `workdir:` arm carries the run
// explicitly in its path (`…/goals/<goal>/runs/<run>/seats/<seat>`).
//
// ⚠ NEVER a hash of `args`. C5 templates per-row argv out of these rows, so an args-content key
// would change the moment a prompt or an argument did, and the door would stop recognising a seat
// it had already queued. `workdir` is read as the seat's ADDRESS, not as row content.
//
// Trailing separators are stripped so `…/seats/x` and `…/seats/x/` are one seat. No path
// resolution beyond that: every producer in this tree submits an already-resolved absolute path
// (`engine/seeding.js` and `engine/attached-execution.js` path.join theirs), and resolving a relative path
// HERE would resolve it against the daemon's CWD, which is not the caller's.
// ⚠ LAUNCH-AGENT ONLY, and this bound is load-bearing rather than cautious. Occupying a seat is
// what an AGENT SESSION does — the ruling's hazard is "a seat that has not yet REGISTERED ITSELF",
// and registration is an agent-seat act. A `fire-tool` / `start-workflow` / `send-message` job
// homed at a (goal, seat) is a one-shot process running OUT OF that home, not a claim on it, and
// firing one twice is ordinary. Keying those too would gate every homed fire-tool job — the
// edge-runner was the measured one — and would make the door forbid the very cadence it serves.
//
// ── THE SHARD (`__seat_shard`) — one seat, N INDEPENDENT CONVERSATIONS ───────────────────────────
//
// A seat key answers "may these two rows run at the same time?". For a seat that serves ONE line of
// work that is the seat itself, and everything above holds unchanged. But `_channel-master` serves
// EVERY Slack DM: `forward-path.js#workdirFor` falls through to the configured `workdir` for every
// master route, so every DM thread resolved to `workdir:<that one path>` and the ticker's seat-busy
// gate serialized the whole surface — a question typed in thread B waited behind an unrelated
// twenty-minute turn in thread A. What the gate SHOULD serialize is a CONVERSATION, which is what
// the shard names.
//
// ⚠ THE STORE IS ITS SOLE MINTER, AND THAT IS WHAT MAKES IT SAFE TO READ FROM `args`. The key is
// spelled `__seat_shard`, which no job's `args_schema` declares — so a caller that puts it in `args`
// itself is refused by `validateArgs`'s unknown-argument arm before it can reach here. It arrives on
// the WIRE as the top-level `seat_shard` field (allowlisted at gateway/parse.js AND dispatch.js,
// exactly like `on_seat_busy`), and `enqueue()` stamps it into the persisted args. Args is the
// carrier because it is the ONE per-row payload BOTH `findSeatHolder` arms parse — the pending arm
// off `queue.args`, the live-turn arm off `jobs_log.args` — so a column would have had to be added
// to both tables to say the same thing.
//
// ⚠ ABSENT ⇒ BYTE-IDENTICAL TO BEFORE. Every non-chat producer in this tree supplies no shard, so
// its key is the unsuffixed one above. It appends to WHICHEVER key was computed rather than to the
// `workdir:` arm alone: the arm a row takes is a property of how its job was registered, and a rule
// that silently dropped the shard on one of them would be a caller asking for isolation and not
// getting it. `#` is barred from the value at the wire, so the split is unambiguous.

// The reserved args key the shard is stamped under. Double-underscored so it can never collide with
// a declared argument name, and so `validateArgs` refuses it from a caller (see the header above).
const SEAT_SHARD_ARG = '__seat_shard';

// `#` is the key separator; whitespace would make a key unreadable in a log line and a tick action.
// Everything else is the caller's business — a Slack thread id (`D0BJ50Y1DC6:1786501607`) is the
// only producer today and nothing here should know that.
const SEAT_SHARD_RE = /^[^\s#]{1,200}$/;

function seatKeyOf(job, args) {
  if (!job || job.action_type !== 'launch-agent') return null;
  const raw = args && typeof args[SEAT_SHARD_ARG] === 'string' ? args[SEAT_SHARD_ARG] : '';
  const shard = raw ? `#${raw}` : '';
  if (job.goal_name && job.seat_name) return `goal:${job.goal_name}/seat:${job.seat_name}${shard}`;
  const workdir = args && typeof args.workdir === 'string' ? args.workdir : null;
  if (!workdir) return null;
  const trimmed = workdir.replace(/\/+$/, '');
  return trimmed ? `workdir:${trimmed}${shard}` : null;
}

// enqueue_log.goal / .seat come off the job row (job.goal_name / job.seat_name). seedTaskforce
// registers seat jobs UNHOMED, so the workdir the seeding pass already submits
// (`{goalFolder}/seats/{seat}`) is the fallback that still names the 08-19 path.
function enqueueHomeOf(job, args) {
  const goal = job && job.goal_name ? job.goal_name : null;
  const seat = job && job.seat_name ? job.seat_name : null;
  if (goal && seat) return { goal, seat };
  const workdir = args && typeof args.workdir === 'string' ? args.workdir.replace(/\/+$/, '') : '';
  const m = workdir.match(/\/\.rbtv\/goals\/([^/]+)\/seats\/([^/]+)$/);
  return { goal: goal || (m && m[1]) || null, seat: seat || (m && m[2]) || null };
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

// `tools` is the BOOT-READ merged config's `tools:` catalogue (`this.config.tools`), handed in
// rather than reached for, because this function is module-level and has no `this`. Task 7.574
// needs it for the fire-tool branch below; every other branch ignores it, and the `null` default
// keeps a caller that has no catalogue behaving exactly as before.
// `workdirRoot` is the same config's `default_workdir_root` (task 7.562), handed in for the same
// reason and with the same null-default semantics.
function validateArgs(args, schemaJson, actionType, tools = null, workdirRoot = null) {
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

  if (actionType === 'fire-tool') {
    if (typeof parsed.tool !== 'string' || parsed.tool.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'fire-tool requires a non-empty tool argument', { field: 'tool' });
    }
    // ── Task 7.574 · the ENQUEUE half of 7.559's `args_allowlist` gate (its design step 3, the one
    // its builder deferred). UX / defence in depth, NOT the boundary: the boundary is the fire path
    // (owner ruling B1), and a hostile row already dies there. What this buys is that a bad value is
    // refused at the CLI immediately instead of failing minutes later inside a recorded execution.
    //
    // ⚠⚠ THE ENTRY'S ALLOWLIST KEYS ONLY, AND NEVER `checkTemplateArgs(parsed)` WITH NO `allow`.
    // The bare call switches admission to the per-key GRAMMAR — including `workdirRule`'s
    // `.rbtv/goals/<goal>` containment, which is a WORKFLOW's rule. A fire-tool row's workdir is
    // legitimately a repo or a state root, so a grammar call here would refuse the live self-heal
    // rows. The start-workflow branch below records the same invariant from the other
    // side; this is why that branch is not simply widened to cover both.
    //
    // ⚠ AMENDED BY TASK 7.562, and the correction matters because this paragraph is the reason the
    // gap survived. Its warning is right about the BARE call and MEASURABLY OVER-BROAD about the
    // rows: the self-heal rows supply NO `workdir` at all (24,918 fires, zero supplied), so no rule
    // on the caller-supplied value can refuse them, and the one edge-runner fire that ever supplied
    // one supplied the configured `default_workdir_root` exactly. The workdir check added below is
    // therefore NOT the bare grammar call this warns against — it reads only `workdir`, only when
    // the caller SUPPLIED it, against a two-root predicate that admits both live shapes.
    //
    // NO `args_allowlist` ON THE ENTRY ⇒ THIS DOOR DOES NOTHING, matching the fire path EXACTLY
    // (`ticker.js` launchFireTool: a falsy `allow` on an untemplated argv falls through to the
    // byte-identical exec, never reaching `checkTemplateArgs`). A door stricter than the fire path
    // would refuse rows the fire path accepts, which is the failure this comment exists to prevent.
    // `Object.hasOwn` for the same reason the catalogue lookups in `enqueue` carry it: the name
    // comes from the ROW, and `tool: "constructor"` walks the prototype chain on a plain index.
    //
    // ⚠⚠ A MALFORMED `args_allowlist` IS NOT THIS DOOR'S BUSINESS — the well-formedness test below
    // is a REFUSAL TO JUDGE, not an oversight, and removing it re-breaks task 7.577's guard.
    // A scalar or bare-list `args_allowlist:` is an OPERATOR's typo in a reviewed config file, not
    // anything the enqueuing sender did; `checkTemplateArgs` reports it as a shape error, and if
    // this door raised that the row could never be STORED — so the shape error would be refused at
    // a door instead of RECORDED on a fired execution, which is the exact property 7.577 restored
    // (`config/spawn-profiles.yaml` rule 9 states it to operators: the daemon "refuses them at FIRE
    // as a shape error and records the execution `failed`"). MEASURED, not reasoned: without this
    // test, `server/ticker/probes/probe-argv-template.js` arm S2b could no longer build the fixture
    // its fire-path arms need, and 7.577's guard went vacuous. The predicate is `checkTemplateArgs`'
    // own shape test, so "well-formed here" and "not a shape error there" cannot drift apart.
    const entry = tools && Object.hasOwn(tools, parsed.tool) ? tools[parsed.tool] : null;
    const raw = (entry && entry.args_allowlist) || null;
    const allow = (raw && typeof raw === 'object' && !Array.isArray(raw)) ? raw : null;
    if (allow) {
      const templateRefusal = checkTemplateArgs(parsed, allow);
      if (templateRefusal) {
        throw new HeartStoreError(E_BAD_ARGS, `fire-tool args refused: ${templateRefusal}`, { field: 'args' });
      }
    }
    // Task 7.562 · the ENQUEUE half of the workdir gate — UX and defence in depth, NOT the
    // boundary (that is `ticker.js` launchFireTool). What it buys: a bad value is refused at the
    // CLI immediately instead of poisoning a PERIODIC row that then records a failed execution
    // every cadence forever. Unconditional on `allow`, because the allowlist branch above switches
    // the per-key grammar OFF and would otherwise leave `workdir` unchecked on exactly the entries
    // that declare one. Silent when the composition root handed no root (probes, attached-execution
    // stores): the fire door knows it and is the boundary anyway.
    if (workdirRoot) {
      const workdirRefusal = checkFireToolWorkdir(parsed, workdirRoot);
      if (workdirRefusal) {
        throw new HeartStoreError(E_BAD_ARGS, `fire-tool args refused: ${workdirRefusal}`, { field: 'workdir' });
      }
    }
  } else if (actionType === 'start-workflow') {
    if (typeof parsed.workflow !== 'string' || parsed.workflow.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'start-workflow requires a non-empty workflow argument', { field: 'workflow' });
    }
    // ── Task C5 · the ENQUEUE half of the templating gate (ruling `d-owner-q10-launcher-0808`).
    //
    // A start-workflow row's args expand into the registered workflow's argv at fire, so these
    // values become tokens of an exec'd command line. They are bounded HERE so no such row is ever
    // stored — the fire path re-checks the same rule for rows that predate this code.
    //
    // START-WORKFLOW ONLY, and the narrowness is the point. `workdir` is an argument of every
    // action type, and the `.rbtv/goals/` containment is true of a WORKFLOW's workdir specifically
    // (a workflow belongs to a goal); a fire-tool row's workdir is legitimately a repo or a state
    // root, and widening this to every action would refuse the live self-heal rows.
    const templateRefusal = checkTemplateArgs(parsed);
    if (templateRefusal) {
      throw new HeartStoreError(E_BAD_ARGS, `start-workflow args refused: ${templateRefusal}`, { field: 'args' });
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

    // ── The jobs_log list cache (2026-08-21) ───────────────────────────────────────────────────
    // `listExecutionsByStatus` is asked ~20× per 10 s cadence by the engine passes (recordView,
    // executionsByJob, publishToRecord — one call per status per goal per pass), and each call
    // re-materialized EVERY terminal row ever recorded: 29,301 `done` rows × 197 ms a scan on
    // 2026-08-21, ~4 s of every cadence, synchronously, on the SAME event loop as the gateway.
    // That starved the HTTP ingress completely — every `rbtv ignite inspect` POST outwaited the
    // CLI's 10 s timeout (measured 39.7 s / 50–60+ s to first byte) while the daemon stayed
    // "healthy". This is the exact upgrade the ponytail note in execution-record.js reserved
    // ("paid once per execution EVER RECORDED").
    // The cache is invalidated by TWO signals, either one killing it:
    //   · `_jobsLogGen` — bumped by every method of THIS store that writes jobs_log;
    //   · `PRAGMA data_version` — SQLite's own counter for commits by ANY OTHER connection,
    //     so a foreign writer process can never be served stale rows.
    // Rows are cached WITHOUT the `thread` attach and the array is copied per call; the row
    // objects themselves are shared — callers treat them as read-only (they all do today).
    this._jobsLogGen = 0;
    this._execListCache = null;

    this.db = new DatabaseSync(this.dbPath);

    // Everything below can throw. Two things must not survive that throw: the DatabaseSync handle
    // opened above (leaked fd + a lingering lock on the db file, unchanged pre-existing behaviour
    // until R3/2026-08-15) and the writer slot (claimed last, see the comment at the end).
    try {
      // R3(b), owner-ruled 2026-08-15: busy_timeout is set FIRST, ahead of WAL/schema/migrate.
      // It used to sit after them, so those three ran with no busy timeout and a concurrent writer
      // made them throw `database is locked` immediately instead of waiting — observed live
      // 2026-08-14 20:25Z. Guarded by probe-single-writer.js arm (d).
      this.db.exec('PRAGMA busy_timeout = 5000;');

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
      this.db.exec('PRAGMA synchronous = NORMAL;');

      this.config = {
        // The (harness, model) -> launch-spec table, keyed by `catalog.js#specKey`. NOT handed in at
        // open: it lives in the launch-spec config the SPAWN MANAGER loads, and the spawn manager is
        // built FROM this store — so the composition root assigns it after the load, exactly as it
        // already does for `workdirRoot` below. Empty until then. The store itself reads it for
        // nothing; it is here because `engine/seeding.js` needs each seat's cage template at
        // pre-enqueue admission time and holds only the store.
        launchSpecs: {},
        tools: opts.tools || {},
        workflows: opts.workflows || {},
        // The live ticker cadence, handed in by the composition root like every other
        // configured value: the minutes→ticks conversion below reads it so a snooze
        // means the same wall-clock duration at any tick_interval_ms. Absent → the
        // ticker's own 10 s default (warnings.js).
        tick_interval_ms: opts.tickIntervalMs,
        // Task 7.562 — the sanctioned fire-tool workdir. Set by the composition root AFTER the spawn
        // manager loads the launch-profile config (engine/index.js), because that config is where
        // `default_workdir_root` lives and the spawn manager is built from this store. Null until
        // then, and null forever for a store opened without one — the enqueue door then stays silent
        // and the fire door, which reads the value directly, remains the boundary.
        workdirRoot: opts.workdirRoot || null,
      };
    } catch (err) {
      // The handle leaked here until R3/2026-08-15: `new DatabaseSync` had succeeded, so a throw
      // above left an open fd (and its lock on the db file) for the life of the process. It only
      // ever mattered to a caller that retries the SAME path in-process — which is exactly what the
      // 2026-08-14 20:25Z incident was — so close it rather than reason about who those callers are.
      try { this.db.close(); } catch {}
      this.db = null;
      throw err;
    }

    // The writer slot is claimed LAST, and that ordering is the fix, not a style choice: it used to
    // be claimed right after `new DatabaseSync`, so any throw below (a WAL/schema/migrate failure,
    // e.g. a locked db) left a half-built store owning the slot and every later openHeartStore in
    // the process died with E_SECOND_WRITER forever — observed live 2026-08-14 20:25Z, where a
    // probe's retry around `database is locked` turned a transient flake into a permanent failure.
    // Safe to claim last because nothing above reads `singleton` (directly or via
    // openHeartStore/isHeartStoreOpen). Guarded by probe-single-writer.js arm (c).
    singleton = this;
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
  // UPDATE has no v1 surface. DISABLE and DELETE both do — `deregisterJob` below, whose
  // purge arm is the RECLAIM path (read its header for why deletion stopped being refused
  // a surface): an id whose retirement is complete becomes registerable again. Changing a
  // LIVE row's action type or schema is still an operator action on the box — the supported
  // sequence is deregister → purge → register, never an in-place rewrite, so a working
  // definition can still never be silently repointed.
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
        + '(firing an unhomed launch is a refusal — r-seats-only-architecture retired the flat path).',
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
    // WHY AT THIS DOOR AND NOWHERE ELSE: the row does not fail loudly. It reports `enabled=1`
    // forever while being structurally incapable of firing, so nothing downstream ever contradicts
    // it — the live catalogue carried two such rows (`goal-watcher`, `goal-watcher-throwaway`),
    // registered with `{}` before this check existed; both were purged when the reconciliation
    // loop replaced the goal-watcher job (retire-health, 2026-08-20). The door that accepts the schema is the last
    // honest place to refuse it. The purge arm now makes such a row RECOVERABLE (deregister →
    // purge → re-register), which is a repair path, not a reason to admit the row.
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

  // ── The RETIREMENT arm (task 7.364 / F20; G-m4-demo-verdict-assembler-0804-1610) ──
  // The catalogue's stop path, in TWO steps that are deliberately not one act.
  //
  // DISABLE (default) flips `enabled` to 0 and nothing else — the row, its id, and its
  // audit trail stay. It is a REAL stop, not a cosmetic flag: the ticker's dispatch defers
  // any due queue row whose job is not enabled (ticker.js, `job-invalid`), and enqueue
  // refuses with E_JOB_DISABLED. So a definition disabled AFTER its rows were queued still
  // never fires.
  //
  // IDEMPOTENT: disabling an already-disabled job is a clean success reporting
  // `was_enabled: false`, never an error — a teardown must be re-runnable. An UNKNOWN
  // id is the opposite and is refused typed (E_UNKNOWN_JOB): reporting success over a
  // job that does not exist is the exact failure a stop path must not have.
  //
  // ── PURGE (`purge: true`) — THE RECLAIM PATH, added because disable alone was not one ──
  // It DELETES the row, which frees the id for re-registration. This reverses the
  // "DELETION is refused a surface" line this comment used to carry, and the reason is
  // measured, not stylistic: the catalogue holds TWO populations. Hand-authored durable
  // definitions (~10) — for which create-only is exactly right, since a re-register that
  // silently repoints a working job is the disaster the 2026-07-25 ruling prevents — and
  // MACHINE-MINTED goal-scoped rows: `<goal>-workflow-start` plus one `seat-<goal>-<seat>`
  // per seat, minted by `capabilities/goal-creation-request` and `engine/seeding.js`, whose
  // ids derive from a REUSABLE goal name and whose lifetime is the goal's. With no reclaim
  // path those accumulate forever and a deleted goal folder BURNS its whole id set: the live
  // catalogue reached 44 rows with 22 dead, and `-v2` re-minting (`chat-agent-v2`,
  // `goal-watcher-job`) had already become the house workaround for an un-repairable id.
  //
  // THE HISTORY OBJECTION DOES NOT HOLD, and it was checked rather than assumed:
  // `queue.job_id` is the ONLY foreign key into `jobs` in the whole schema, and
  // `jobs_log.job_id` is a plain column that denormalizes `action_type` and `args` — so past
  // executions read correctly with the catalogue row gone. What a purge DOES cost is that an
  // id may name two different jobs across time; `jobs_log.fired_at` is what separates them.
  //
  // THREE GUARDS, all inside the transaction, all refusing E_JOB_PURGE_REFUSED with a
  // `reason` and the command that clears it:
  //   enabled            — purge only finishes a retirement someone already declared. This is
  //                        what makes a bulk purge loop over the disabled rows structurally
  //                        unable to touch a live definition.
  //   pending-queue-rows — the FK would fail anyway; refusing by name beats an SQLITE_
  //                        CONSTRAINT, and a cascade here would silently cancel a schedule.
  //   live-executions    — the real hazard, and the one not visible from the schema: with the
  //                        row gone, `_findSeatHolder`'s `seatKeyOf(getJob(...))` reads null
  //                        for that job, so the idempotent door stops seeing the running turn.
  //                        Re-register the same id (the whole point of a purge) and the seat
  //                        could double-fire under a turn still in flight.
  //
  // ⚑ AUTHORIZATION IS NOT ASKED HERE — the caller owns policy (the D65(B) split).
  deregisterJob({ jobId, updatedAt, purge = false }) {
    if (typeof jobId !== 'string' || jobId.length === 0) {
      throw new HeartStoreError(E_BAD_ARGS, 'job_id must be a non-empty string', { field: 'jobId' });
    }
    this.db.exec('BEGIN EXCLUSIVE;');
    try {
      const row = this.getJob(jobId);
      if (!row) {
        this.db.exec('ROLLBACK;');
        throw new HeartStoreError(E_UNKNOWN_JOB, `unknown job: ${jobId}`, { field: 'jobId', jobId });
      }
      const wasEnabled = row.enabled === 1;
      // Counted INSIDE the transaction and reported out loud (D21(3)): a disable leaves
      // pending rows in the queue, deferred every tick rather than removed. An operator
      // who wants them gone runs `remove-job <queue-id>` — and cannot learn that from a
      // bare success line. The purge arm turns the same count into a refusal.
      const pending = this._prepare('SELECT COUNT(*) AS n FROM queue WHERE job_id = ?').get(jobId).n;

      if (purge) {
        const refuse = (reason, message, details) => {
          this.db.exec('ROLLBACK;');
          throw new HeartStoreError(E_JOB_PURGE_REFUSED, message, { field: 'jobId', jobId, reason, ...details });
        };
        if (wasEnabled) {
          refuse('enabled',
            `job still enabled: ${jobId}. A purge only completes a retirement that was already `
            + `declared — run \`ignite deregister-job ${jobId}\` first, then purge. `
            + 'That order is what lets a bulk purge over the disabled rows never reach a live job.',
            {});
        }
        if (pending > 0) {
          refuse('pending-queue-rows',
            `${pending} pending queue row(s) still reference ${jobId}. They are not cascaded away: `
            + 'removing a repeating row cancels the WHOLE schedule (D68), which is not something a '
            + 'catalogue purge may do silently. Clear them with `ignite remove-job <queue-id>` '
            + '(`ignite inspect queue` lists them), then purge.',
            { pending_queue_rows: pending });
        }
        const nonTerminal = [...TURN_STATUSES].filter((s) => !TERMINAL_TURN_STATUSES.has(s));
        const live = this._prepare(
          `SELECT COUNT(*) AS n FROM jobs_log WHERE job_id = ? AND status IN (${nonTerminal.map(() => '?').join(',')})`,
        ).get(jobId, ...nonTerminal).n;
        if (live > 0) {
          refuse('live-executions',
            `${live} execution(s) of ${jobId} are still non-terminal (${nonTerminal.join('/')}). `
            + 'Purging now would hide those turns from the idempotent door, so a re-registration of '
            + 'this id could double-fire the seat under a turn still in flight. Let them finish, or '
            + '`ignite kill <session-id>` them, then purge.',
            { live_executions: live });
        }
        this._prepare('DELETE FROM jobs WHERE job_id = ?').run(jobId);
        this.db.exec('COMMIT;');
        // The DELETED row's own fields ride the answer: after the commit there is nothing left
        // to read back, and a caller that cannot say WHAT it purged cannot write a useful log.
        return { ...row, purged: true, was_enabled: wasEnabled, pending_queue_rows: 0 };
      }

      if (wasEnabled) {
        this._prepare('UPDATE jobs SET enabled = 0, updated_at = ? WHERE job_id = ?')
          .run(updatedAt || isoNow(), jobId);
      }
      const after = this.getJob(jobId);
      this.db.exec('COMMIT;');
      return { ...after, purged: false, was_enabled: wasEnabled, pending_queue_rows: pending };
    } catch (err) {
      try { this.db.exec('ROLLBACK;'); } catch {}
      throw err;
    }
  }

  getJob(jobId) {
    const stmt = this._prepare('SELECT * FROM jobs WHERE job_id = ?');
    return stmt.get(jobId) || null;
  }

  listJobs() {
    const stmt = this._prepare('SELECT * FROM jobs ORDER BY job_id');
    return stmt.all();
  }

  // ── Task Q9 · THE IDEMPOTENT DOOR's lookup (ruling `d-q9-door`) ─────────────────────────────
  //
  // Who currently HOLDS this (run, seat), or null. TWO surfaces, and both are required — this is
  // the `engine/attached-execution.js` enqueueEligible grammar (pending row OR prior execution), read
  // against the ruled non-terminal set rather than "ever ran".
  //
  // ⚠ THE SECOND SURFACE IS THE WHOLE FIX. A queue-only check is VACUOUS in the configuration
  // this exists for, and the measured case was the edge-runner's: it enqueued `--trigger scheduled
  // --at now`, fireQueueRow DELETES such a row at fire, the ticker cadence is 10s and its shipped
  // recipe was `--every 300` — so the pending row existed for ~3% of the cycle and the re-fire
  // almost always landed when the seat was held by a LIVE TURN and nothing was pending. A door that
  // only read `queue` would look exactly like this one and suppress almost nothing. That caller is
  // retired; the shape binds every periodic re-enqueuer, which is why the surface stays.
  //
  // NON-TERMINAL is the store's own TERMINAL_TURN_STATUSES, negated — never a second list here.
  // So `launching`/`running`/`stalled` hold the seat; `done`/`blocked`/`failed`/`killed` release
  // it, which is what keeps crash-retry alive (ruling: escalation of a crash-looping seat is the
  // goal-watcher's stall row, not the door's).
  //
  // ORDERING: a holder that carries an ORIGINATING queue id wins over one that does not, then the
  // most recent. The ruled return is that originating id, so a turn born outside the queue (a
  // direct recordExecutionStart, as probes do) must never mask a turn that has one.
  //
  // ⚠ PUBLIC SINCE THE SEAT-BUSY GATE. The ticker's dispatch phase asks the SAME busy question
  // this door asks, so it calls THIS method rather than re-deriving one — one predicate by
  // construction (`_findSeatHolder` stays below as an alias for anything still binding it).
  // `excludeQueueId` exists for that caller only, and it applies to BOTH arms — it means "held by
  // anyone OTHER THAN THIS ROW". The pending arm needs it because the asking row is itself pending
  // and would otherwise match its own key and mask every other holder. The LIVE-TURN arm needs it
  // for a measured reason: a recurring row keeps its queue_id across fires, so its own previous
  // execution is a live turn carrying THIS row's originating id — and gating on that would stop
  // every periodic launch-agent job from re-firing while its predecessor runs, which is certified
  // behaviour this gate has no business changing (probe-periodic, measured red).
  //
  // ⚠⚠ `pendingAheadOf` — WITHOUT IT, TWO PENDING ROWS FOR ONE SEAT DEADLOCK. Measured here
  // 2026-08-17 by this method's own probe: with rows 1 and 2 pending at one idle seat, row 1's gate
  // finds row 2 (excluded from itself, not from its sibling) and row 2 finds row 1 — BOTH defer,
  // every tick, until the age bound silently drops both an hour later. The seat-busy gate's own
  // header claims the ordering "falls out of `getQueueDue`'s (run_at, queue_id)", and it does not:
  // this scan returned the first row that MATCHED, never the first row that came BEFORE the asker.
  // Live path: two chat messages landing at an idle seat inside one tick interval — neither runs.
  //
  // So the ticker passes the ASKING ROW and the pending arm counts only rows genuinely ahead of it
  // in dispatch order. The oldest row then has no holder and fires; its siblings wait on it. The
  // Q9 door passes nothing and is unchanged: for an enqueue there is no asking row yet, so ANY
  // pending row for the seat legitimately holds it.
  //
  // ⚠ THE LIVE-TURN ARM IS DELIBERATELY NOT ORDERED. A running turn holds the seat whatever its
  // row's ordinal — that is the whole gate.
  findSeatHolder(seatKey, { excludeQueueId = null, pendingAheadOf = null } = {}) {
    for (const row of this.listQueue()) {
      if (excludeQueueId !== null && row.queue_id === excludeQueueId) continue;
      if (pendingAheadOf && !(row.run_at < pendingAheadOf.run_at
        || (row.run_at === pendingAheadOf.run_at && row.queue_id < pendingAheadOf.queue_id))) continue;
      let args;
      try { args = JSON.parse(row.args); } catch { args = {}; }
      if (seatKeyOf(this.getJob(row.job_id), args) === seatKey) {
        return { because: 'pending-queue-row', queueId: row.queue_id, execId: null, status: null };
      }
    }
    const nonTerminal = [...TURN_STATUSES].filter((s) => !TERMINAL_TURN_STATUSES.has(s));
    const rows = this._prepare(`
      SELECT exec_id, queue_id, job_id, args, status FROM jobs_log
      WHERE status IN (${nonTerminal.map(() => '?').join(',')})
      ORDER BY (queue_id IS NULL), exec_id DESC
    `).all(...nonTerminal);
    for (const row of rows) {
      if (excludeQueueId !== null && row.queue_id === excludeQueueId) continue;
      let args;
      try { args = JSON.parse(row.args); } catch { args = {}; }
      if (seatKeyOf(this.getJob(row.job_id), args) === seatKey) {
        return { because: 'live-turn', queueId: row.queue_id, execId: row.exec_id, status: row.status };
      }
    }
    return null;
  }

  // Kept so nothing that binds the pre-rename name breaks. One implementation, one alias.
  _findSeatHolder(seatKey, opts) { return this.findSeatHolder(seatKey, opts); }

  enqueue(req) {
    const job = this.getJob(req.jobId);
    if (!job) {
      throw new HeartStoreError(E_UNKNOWN_JOB, `unknown job: ${req.jobId}`, { jobId: req.jobId });
    }
    if (!job.enabled) {
      throw new HeartStoreError(E_JOB_DISABLED, `job disabled: ${req.jobId}`, { jobId: req.jobId });
    }

    const args = req.args !== undefined ? req.args : '{}';
    validateArgs(args, job.args_schema, job.action_type, this.config.tools, this.config.workdirRoot);

    const parsedArgs = JSON.parse(args);

    // ── THE SEAT SHARD's stamp (seatKeyOf § THE SHARD) ────────────────────────────────────────
    //
    // AFTER `validateArgs`, and that ordering is the guarantee: the caller's args have already been
    // checked against the job's schema, so `__seat_shard` arriving in them is a refusal and cannot
    // reach this line. What lands here comes from `req.seatShard` — the wire's `seat_shard` — and
    // the store is therefore the only thing that can put the key in a row.
    //
    // `argsForRow` and not `args`: the stamped JSON is what the INSERT writes, so every later reader
    // (`findSeatHolder`'s pending arm, `fireQueueRow`'s copy into `jobs_log.args`, the ticker's
    // gate) sees the shard off the row itself. An absent shard leaves `args` untouched by reference
    // — no re-serialization, so a row enqueued without one is byte-identical to before this landed.
    let argsForRow = args;
    if (req.seatShard !== undefined && req.seatShard !== null && req.seatShard !== '') {
      if (typeof req.seatShard !== 'string' || !SEAT_SHARD_RE.test(req.seatShard)) {
        throw new HeartStoreError(E_BAD_ARGS, 'seat_shard must be 1-200 chars with no whitespace and no "#"', { field: 'seatShard' });
      }
      parsedArgs[SEAT_SHARD_ARG] = req.seatShard;
      argsForRow = JSON.stringify(parsedArgs);
    }

    // ⚠ `Object.hasOwn`, NOT a truthiness test, on both catalogue lookups below (C5 review
    // 2026-08-08). The name comes from the ROW, and a plain `catalogue[name]` walks the prototype
    // chain: `constructor` is a legal kebab-case value, so `workflow: "constructor"` resolved
    // truthy and ENQUEUED past this very guard while `no-such-workflow` was refused (measured,
    // `evidence/c5-review/c5r-02-integration-attacks.txt` § P1). Nothing exploitable followed —
    // the fire path then found no argv and recorded a failed turn — but a row-controlled name
    // that defeats its own existence check is a guard that reports absence wrongly.
    //
    // ⚠ `launch-agent` HAS NO ROW TO LOOK UP ANY MORE (7.787). It carried an unknown-profile
    // refusal here; under `#d-abolish-profile-names` the row names no launch spec, so there is
    // nothing at queue time to check. What replaces it is STRICTLY LOUDER, not absent: the seat's
    // own cast is resolved at spawn (`launch-profiles/catalog.js#specForSeatCast`), and an uncast
    // or unmappable seat is a NAMED refusal there — `E_UNCAST_SEAT` / `E_UNMAPPED_BINDING`.
    if (job.action_type === 'fire-tool') {
      if (!Object.hasOwn(this.config.tools, parsedArgs.tool)) {
        throw new HeartStoreError(E_UNKNOWN_TOOL, `unknown tool: ${parsedArgs.tool}`, { tool: parsedArgs.tool });
      }
    } else if (job.action_type === 'start-workflow') {
      if (!Object.hasOwn(this.config.workflows, parsedArgs.workflow)) {
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
      // ⚠ THE PROFILE-SHAPED HALVES OF THIS GATE MOVED TO SPAWN (7.787). Two checks stood here —
      // "is the profile headed-capable" and "does it declare a headed prompt carriage" — and BOTH
      // read `this.config.profiles[args.profile]`, the parameter `#d-abolish-profile-names`
      // deletes. They are not dropped: `server/spawn/spawn.js#spawn` now runs both against the
      // spec the SEAT is cast to, which is the one that will actually launch. That is strictly
      // more correct than what stood here even before the abolition — the queue checked the
      // CALLER'S profile while ruling D19 already had the seat's own cast outranking it, so a
      // headed launch could pass this gate on one spec and spawn on another.
      //
      // What survives at queue time is the action-type bound above, which needs no config at all.
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

    // ── Task Q9 · THE IDEMPOTENT DOOR (owner-authorized ruling `d-q9-door`, 2026-08-08) ────────
    //
    // A second add-job for a (run, seat) still held is a NO-OP that RETURNS THE HELD OPERATION'S
    // ID — idempotent-return-of-the-existing-operation, not a refusal. The caller it was built for
    // was a PERIODIC edge-runner pass whose door contract was exit 0 plus a parseable queue id; a
    // typed refusal here would record that productive pass
    // `failed` on every fire while any seat is booting — rebirthing the recorded-failure-each-
    // cadence noise this run exists to remove. So: pending hold returns the REAL pending row;
    // live-turn hold returns the ORIGINATING queue id (the row whose fire produced that turn).
    //
    // PLACED AFTER THE DRY-RUN RETURN, deliberately: `--dry-run` keeps its certified meaning
    // ("the complete re-validation passed, nothing was written") byte-identically, and the door
    // governs only acts that would actually mint a row.
    //
    // NOT A GUARD ON THE RECYCLE PATH: the ticker's own `insertQueueRow` is a raw INSERT that
    // never reaches this method, so a turn chain's recycle is untouched by construction (it has
    // its own `slot-live-session` defer). That is the ruled split, not an oversight.
    //
    // ⚠ SUPPRESSION DISCARDS THE ENTIRE NEW REQUEST — payload AND schedule, not just the row.
    // This returns BEFORE the INSERT, so the second call's `args` (a `prompt` included),
    // `run_at`, `trigger_kind` and `session_mode` are dropped and the caller is handed the HELD
    // operation's id. That is exactly right when the re-submission is REDUNDANT — the caller it was
    // built for re-submitted an IDENTICAL launch request, so nothing unique was lost, which is
    // why the door was safe for it. It is LOSSY for any caller whose
    // payload carries something the held operation never saw. One such caller is in-tree and
    // live: `bridges/chat/forward-path.js` forwardSessionCreate homes every goal-channel session
    // at that goal's `goal-master` seat, so a NEW chat thread opened while that seat holds a live
    // turn is suppressed, its user text is dropped, and the bridge maps the thread to the held id
    // and logs a success (measured, Q9 review 2026-08-08). THAT BRIDGE FIX HAS SINCE LANDED, at
    // `78c7ac2`: `forwardSessionCreate` now reads `deduped` and refuses the thread rather than
    // mapping it to the held id, so the loss path above is closed for that caller specifically.
    // The lossiness of THIS method is unchanged and is not a bug to be fixed here — a caller that
    // must not lose its payload MUST read `deduped` on the result rather than treating a returned
    // id as delivery. The bridge is the precedent for doing so, not an exemption from it.
    //
    // ⚠ THE LOSSINESS IS NOW OPT-OUT, NOT UNCONDITIONAL (`on_seat_busy`, owner-ruled). A caller
    // whose payload carries something the held operation never saw — a chat message typed while
    // the seat's turn is still running — passes `onSeatBusy: 'queue'` and gets an ORDINARY INSERT:
    // no dedupe, no suppression, the row waits its turn. `'dedupe'` (and absent) is the behaviour
    // above, byte-identical. Queueing is safe only because the ticker's dispatch phase asks THIS
    // OBJECT's `findSeatHolder` before it launches, so two pending rows for one seat fire one
    // after the other rather than at once; the per-seat pending CAP is enforced at the bridge.
    const home = enqueueHomeOf(job, parsedArgs);
    const onSeatBusy = req.onSeatBusy === undefined || req.onSeatBusy === null ? 'dedupe' : req.onSeatBusy;
    if (onSeatBusy !== 'dedupe' && onSeatBusy !== 'queue') {
      throw new HeartStoreError(E_BAD_ARGS, `on_seat_busy must be 'dedupe' or 'queue'`, { onSeatBusy });
    }
    const seatKey = onSeatBusy === 'queue' ? null : seatKeyOf(job, parsedArgs);
    if (seatKey) {
      const holder = this.findSeatHolder(seatKey);
      if (holder) {
        this._recordEnqueueLog({
          jobId: req.jobId, goal: home.goal, seat: home.seat, seatKey,
          outcome: 'suppressed', because: holder.because,
          queueId: holder.queueId, execId: holder.execId, heldStatus: holder.status,
          at: isoNow(),
        });
        return {
          deduped: true,
          seat_key: seatKey,
          because: holder.because,
          queue_id: holder.queueId,
          exec_id: holder.execId,
          held_status: holder.status,
        };
      }
    }

    const enqueuedAt = req.enqueuedAt || isoNow();
    const stmt = this._prepare(`
      INSERT INTO queue (job_id, args, session_mode, trigger_kind, run_at, repeat_rule, interval_seconds, max_fires, enqueued_by, enqueuing_seat, enqueued_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    const result = stmt.run(
      req.jobId,
      argsForRow,
      sessionMode,
      req.triggerKind,
      req.runAt,
      req.repeatRule === undefined ? null : req.repeatRule,
      req.intervalSeconds === undefined ? null : req.intervalSeconds,
      req.maxFires === undefined ? null : req.maxFires,
      req.enqueuedBy,
      // Task 7.389 — the PROVEN enqueuing seat, or NULL. Normalized to NULL rather than passed
      // through: `undefined` (every caller that predates this column) and `''` must both land as
      // SQL NULL, because the `creator-seat` grant compares this against `sender.seat` and an
      // empty string that compared equal to an unproven caller's empty seat would grant the
      // principal to a caller who proved nothing.
      typeof req.enqueuingSeat === 'string' && req.enqueuingSeat.length > 0 ? req.enqueuingSeat : null,
      enqueuedAt
    );
    const queueId = Number(result.lastInsertRowid);
    this._recordEnqueueLog({
      jobId: req.jobId, goal: home.goal, seat: home.seat,
      seatKey: req.onSeatBusy === 'queue' ? null : seatKeyOf(job, parsedArgs),
      outcome: 'enqueued', because: null,
      queueId, execId: null, heldStatus: null,
      at: enqueuedAt,
    });
    return this.getQueueRow(queueId);
  }

  // enqueue_log is the enqueue→launch record. Written here, the single writer, so every caller
  // is recorded and no caller can forget. A row clears itself from listEnqueueUnfired the moment
  // a jobs_log fire exists at or after its `at` — no lifecycle column, no sweeper.
  _recordEnqueueLog({ jobId, goal, seat, seatKey, outcome, because, queueId, execId, heldStatus, at }) {
    this._prepare(`
      INSERT INTO enqueue_log (job_id, goal, seat, seat_key, outcome, because, queue_id, exec_id, held_status, at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(jobId, goal, seat, seatKey, outcome, because, queueId, execId, heldStatus, at);
  }

  listEnqueueUnfired(goal, cutoffIso) {
    return this._prepare(`
      SELECT * FROM enqueue_log e
       WHERE e.goal = ? AND e.at <= ?
         AND NOT EXISTS (SELECT 1 FROM jobs_log j WHERE j.job_id = e.job_id AND j.fired_at >= e.at)
       ORDER BY e.at
    `).all(goal, cutoffIso);
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
    this._jobsLogGen += 1;    // jobs_log write — invalidate the list cache (constructor note)
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
          (parent_exec_id, queue_id, job_id, action_type, args, enqueued_by, enqueuing_seat, session_mode, fired_tick, fired_at, status, session_pk)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'launching', ?)
      `);
      const logResult = insertLog.run(
        parentExecId,
        queue.queue_id,
        queue.job_id,
        queue.action_type || this.getJob(queue.job_id)?.action_type || 'launch-agent',
        queue.args,
        queue.enqueued_by,
        // Task 7.389 — denormalized at fire exactly as `enqueued_by` is, and for the same reason
        // this method's own header gives: the queue row is DELETED on a one-shot fire, so a
        // jobs_log row that pointed at it instead of carrying the value would lose the seat the
        // moment the turn it authorizes actually exists. `?? null` covers a store migrated before
        // the column landed, where the SELECT yields `undefined`.
        queue.enqueuing_seat ?? null,
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

  // `enqueuingSeat` (task 7.389) defaults to null: this method's callers are the daemon's own
  // internal starts (the attached-execution carrier, the deploy probes), which hold no proven seat.
  recordExecutionStart({ queueId = null, jobId, actionType, args, enqueuedBy, enqueuingSeat = null, sessionMode = 'headless', firedTick, firedAt, parentExecId = null, sessionId = null, pid = null, profile = null, workdir = null }) {
    this._jobsLogGen += 1;    // jobs_log write — invalidate the list cache (constructor note)
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
          (parent_exec_id, queue_id, job_id, action_type, args, enqueued_by, enqueuing_seat, session_mode, fired_tick, fired_at, status, session_id, pid, profile, workdir, session_pk)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'launching', ?, ?, ?, ?, ?)
      `);
      const result = stmt.run(
        parentExecId,
        queueId,
        jobId,
        actionType,
        args,
        enqueuedBy,
        // Task 7.389 — same normalization the queue insert applies: `''` must never reach the
        // column, or it would compare equal to an unproven caller's seat at the grant.
        typeof enqueuingSeat === 'string' && enqueuingSeat.length > 0 ? enqueuingSeat : null,
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

  // `withThread: false` skips the per-row `_chainThread` walk. It is not a micro-optimisation: the
  // walk is a RECURSIVE CTE per row, so a caller that scans every status pays one such query per
  // execution in the store's whole history — 743 ms of the 874 ms this call cost on the daemon's
  // store 2026-08-12, every tick, to serve a caller (`engine/execution-record.js#publishToRecord`)
  // that never reads `thread`. Callers that DO read it get it, unchanged, by default.
  listExecutionsByStatus(status, { withThread = true } = {}) {
    // Served from the jobs_log list cache (see the constructor note): a repeat call with no
    // intervening jobs_log write — by this store OR any other connection — costs an array copy
    // instead of a full-history scan. `data_version` moves only on OTHER connections' commits;
    // this store's own writes are tracked by `_jobsLogGen`.
    const dv = this.db.prepare('PRAGMA data_version').get().data_version;
    if (!this._execListCache
        || this._execListCache.gen !== this._jobsLogGen
        || this._execListCache.dataVersion !== dv) {
      this._execListCache = { gen: this._jobsLogGen, dataVersion: dv, byStatus: new Map() };
    }
    const byStatus = this._execListCache.byStatus;
    if (!byStatus.has(status)) {
      const stmt = this._prepare('SELECT * FROM jobs_log WHERE status = ? ORDER BY exec_id');
      byStatus.set(status, stmt.all(status));
    }
    const rows = byStatus.get(status);
    // `_attachThread` mutates its row in place, so the thread walk runs on COPIES — the cached
    // rows must never grow a `thread` property a `withThread: false` caller did not ask for.
    return withThread ? rows.map((r) => this._attachThread({ ...r })) : rows.slice();
  }

  // LE-13 Change 2 (2026-08-19) — THE ONE COUNTER, both escalation consumers call this and neither
  // re-implements it (PRIN-11). How many of `jobId`'s MOST RECENT `jobs_log` rows are consecutively
  // `status = 'failed'`, newest first, stopping at the first row that is not. Bounded to `limit`
  // rows — `jobs_log.job_id` is a plain, denormalized column (the same id can name a DIFFERENT job
  // across time, see the note above `deregisterJob`), so a small bounded read is what makes that
  // irrelevant: the caller only ever needs to know whether the CURRENT streak reaches K, never the
  // job's whole history.
  getReconcileAttempt(goal, seat, reason) {
    return this._prepare(
      'SELECT * FROM reconcile_attempts WHERE goal = ? AND seat = ? AND reason = ?'
    ).get(goal, seat, reason) || null;
  }

  upsertReconcileAttempt({ goal, seat, reason, attempts, stuckEmitted, signature, updatedAt }) {
    this._prepare(`
      INSERT INTO reconcile_attempts (goal, seat, reason, attempts, stuck_emitted, signature, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(goal, seat, reason) DO UPDATE SET
        attempts = excluded.attempts,
        stuck_emitted = excluded.stuck_emitted,
        signature = excluded.signature,
        updated_at = excluded.updated_at
    `).run(goal, seat, reason, attempts, stuckEmitted ? 1 : 0, signature || null, updatedAt);
    return this.getReconcileAttempt(goal, seat, reason);
  }

  clearReconcileAttempt(goal, seat, reason) {
    this._prepare(
      'DELETE FROM reconcile_attempts WHERE goal = ? AND seat = ? AND reason = ?'
    ).run(goal, seat, reason);
  }

  getReconcilePass(goal) {
    return this._prepare('SELECT * FROM reconcile_pass WHERE goal = ?').get(goal) || null;
  }

  setReconcilePass(goal, lastAt) {
    this._prepare(`
      INSERT INTO reconcile_pass (goal, last_at) VALUES (?, ?)
      ON CONFLICT(goal) DO UPDATE SET last_at = excluded.last_at
    `).run(goal, lastAt);
    return this.getReconcilePass(goal);
  }

  consecutiveFailures(jobId, limit) {
    const stmt = this._prepare('SELECT status FROM jobs_log WHERE job_id = ? ORDER BY exec_id DESC LIMIT ?');
    let n = 0;
    for (const row of stmt.all(jobId, limit)) {
      if (row.status !== 'failed') break;
      n += 1;
    }
    return n;
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
    this._jobsLogGen += 1;    // jobs_log write — invalidate the list cache (constructor note)
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
    this._jobsLogGen += 1;    // jobs_log write — invalidate the list cache (constructor note)
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

  // `thread` filters IN SQL, and that is the whole point of it existing. Every caller that wanted
  // one thread used to fetch the table and filter in JS — which materialises EVERY message row,
  // corpus included, into JS objects to keep a handful. On this daemon's store that was ~27k rows
  // and ~27 MB of text per call, on a path the chat bridge polls every 3 s: the main thread ends up
  // permanently allocating and collecting, and libuv can only `accept()` between JS turns, so the
  // gateway's LISTEN backlog stops draining while the ticker's timers still fire. Measured
  // 2026-08-12: 160 ms and ~90 MB of garbage per call, and the cost grows with history forever
  // (retention never touches heart.db by construction).
  getMessages({ unroutedOnly = false, unbroadcastOnly = false, type = null, thread = null, limit = null } = {}) {
    let sql = 'SELECT * FROM messages';
    const conds = [];
    const params = [];
    if (unroutedOnly) conds.push('routed_at_tick IS NULL');
    if (unbroadcastOnly) conds.push('broadcast_at_tick IS NULL');
    if (thread !== null) {
      conds.push('thread = ?');
      params.push(thread);
    }
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
  E_JOB_PURGE_REFUSED,
  E_SECOND_WRITER,
  E_UNKNOWN_JOB,
  E_JOB_DISABLED,
  E_BAD_ARGS,
  E_UNKNOWN_LAUNCH_SPEC,
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
  // The (run, seat) key. Exported so the ticker's seat-busy gate asks the door's own question
  // with the door's own key rather than a second spelling of it.
  seatKeyOf,
  // The reserved args key the seat shard is stamped under, exported for the same reason: a probe or
  // a reader that needs to see a row's shard reads THE name, never a second spelling of it.
  SEAT_SHARD_ARG,
  // LE-13 Change 2 — the ONE tunable both escalation consumers (`engine/lane-watch.js`'s
  // `alarmOnStall`, `server/ticker/warnings-check.js`'s unhomed fallback) read rather than each
  // carrying its own guess.
  PERIODIC_FAILURE_STREAK_K,
};
