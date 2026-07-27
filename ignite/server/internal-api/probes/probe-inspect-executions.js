'use strict';

// probe-inspect-executions — `inspect executions --status <s>`, the state-filtered execution
// listing added by task 7.62, exercised end-to-end through the REAL gateway -> REAL internal API
// -> REAL heart store.
//
// WHAT THE TARGET IS FOR: the built read surface had fixed views (jobs|queue|daemon|ticker) and
// execution-SCOPED views (status|logs|messages), and between them no way to ask "every failed
// run" or "every stalled worker". `executions` is that question. It is a TARGET and not a ninth
// intent (the ce-5/D3 precedent `messages` set) and it changes NO store code — it reads the
// shipped listExecutionsByStatus() (heart-store.js:849, fourteen live callers).
//
// ⚑ WHY THIS PROBE ALSO GUARDS TWO CLOSED SETS, WHICH IS NOT WHERE THE TASK POINTED IT.
// Task 7.62's criteria ask for the change to be "in lockstep across the three closed intent sets
// with the 7.16 intent-drift probe green". Measured while auditing the brief: this change touches
// NO intent, so probe-intent-drift is green before and after BY CONSTRUCTION. That check cannot
// fail here, and a check that cannot fail is not evidence — offering it as such would be exactly
// the green-harness-over-a-broken-mechanism shape this run has catalogued all evening. Leader
// ruled it NECESSARY BUT NOT SUFFICIENT and ruled the real guard to be this one.
//
// The set genuinely at risk is the inspect TARGET set, which lives in THREE copies —
// gateway/parse.js INSPECT_TARGETS, dispatch.js INSPECT_TARGETS, cli/commands/inspect.js TARGETS
// — and was guarded by NOTHING before this probe. That is the precise shape probes/lib/
// closed-set.js's own header warns about, arrived at from the other side. The `status` enum this
// task adds to the gateway is a FOURTH copy of a closed set, so it is guarded here too, against
// the database's OWN DDL rather than against a source file.
//
// ★ CONSTRUCTION, inheriting task 7.16's ruling: the copies are compared as EXPORTED CONSTANTS,
// never by regex over source text (a false-alarming probe gets ignored, which is worse than no
// probe). The status enum has no exported form on the store side — its truth is the schema's
// CHECK constraint — so it is derived from the LIVE DATABASE's own `sqlite_master` DDL and then
// CROSS-CHECKED BEHAVIOURALLY: every derived member must actually insert, and a value outside the
// set must be refused by the constraint. Reading the DDL alone would prove only that a string
// appears in a string; the insert is what proves the set is the one the database enforces.
//
// ⚑ Task 7.46 will SPLIT this enum into session-level and turn-level states. When it lands, THIS
// probe fails first and names the member — which is the point of writing it now rather than
// discovering the drift through a caller.
//
// Isolation: a THROWAWAY db under os.tmpdir(). This probe SEEDS rows — it must NEVER be pointed
// at the live store (.rbtv/heart/), which a live daemon is ticking against.
//
// Capture truncated at module load, BEFORE any work (D51 evidence-husk hazard). The process exit
// code is the truth; the footer is a hint.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-inspect-executions.out');
fs.writeFileSync(outPath, '');

const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createInternalApi, INSPECT_TARGETS: CORE_TARGETS, EXEC_STATUSES: CORE_STATUSES } = require('../dispatch');
const { createGateway } = require('../../../gateway/gateway');
const { parseRequest, INSPECT_TARGETS: GW_TARGETS, EXEC_STATUSES: GW_STATUSES } = require('../../../gateway/parse');
const { TARGETS: CLI_TARGETS, run: cliInspect } = require('../../../cli/commands/inspect');
const { hashToken } = require('../../../gateway/sender-auth');
const { checkClosedSetsLockstep } = require('./lib/closed-set');

const tmpDb = path.join(os.tmpdir(), `ignite-probe-inspect-executions-${Date.now()}-${process.pid}.db`);
const sendersFile = path.join(os.tmpdir(), `ignite-probe-inspect-executions-senders-${Date.now()}-${process.pid}.yaml`);

const OWNER_TOKEN = crypto.randomBytes(16).toString('hex');
const TICK_INTERVAL_MS = 10000;

// The seeded fleet. Deliberately UNEVEN across statuses and deliberately NOT sorted by status, so
// a handler that ignored its filter and returned everything, or returned the first N rows, is
// distinguishable from one that filtered. `killed` is seeded ZERO TIMES on purpose — it is the
// empty-result case, and it is a VALID status, which is what makes empty-vs-invalid a real
// distinction rather than a formality.
const SEED = [
  { status: 'failed', jobId: 'job-alpha' },
  { status: 'running', jobId: 'job-beta' },
  { status: 'failed', jobId: 'job-gamma' },
  { status: 'stalled', jobId: 'job-delta' },
  { status: 'failed', jobId: 'job-epsilon' },
  { status: 'done', jobId: 'job-zeta' },
  { status: 'stalled', jobId: 'job-eta' },
];

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass: Boolean(pass) });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// ⚑ EVERY result access goes through these. On PRE-FIX code the target does not exist, so the
// envelope carries an error and `body.result` is null — and a probe that dereferenced it would
// THROW at the first failing check and exit before reporting the rest. That is G-121's shape: a
// truncated run reads greener than a complete one, with only the exit code dissenting. Here the
// truncation happened to read RED, which is luck, not construction. A probe must be able to state
// its WHOLE finding on the code it is meant to fail against — that is what makes the pre-change
// control readable as evidence instead of as a crash.
function resultOf(r) {
  return (r && r.body && r.body.result) || {};
}
function rowsOf(r) {
  const rows = resultOf(r).rows;
  return Array.isArray(rows) ? rows : [];
}

// A closed set that is not EXPORTED is not merely unreachable — it is the lockstep check's own
// blind spot, and dereferencing it would fault the probe out mid-run (the same G-121 truncation
// the result guards above exist to prevent). An absent export is reported as the finding it is.
function setOrNull(v) { return v instanceof Set ? v : null; }

// The gateway's typed refusals carry `details.field`. Asserting the FIELD, not merely that
// something was refused, is what makes these checks discriminate: on pre-change code the target
// itself is unknown, so EVERY payload is refused — for the wrong reason. A check that passes on
// code lacking the feature is not evidence of the feature.
function refusedField(r) {
  const e = r && r.body && r.body.error;
  return (e && e.details && e.details.field) || null;
}

// DISK truth on a fresh read-only connection: a reader can never be a second writer.
function readBackAllExecutions() {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT exec_id, job_id, status FROM jobs_log ORDER BY exec_id').all();
  } finally {
    raw.close();
  }
}

// The LIVE status universe, as the DATABASE defines it: the CHECK constraint on jobs_log.status,
// read out of sqlite_master (the DDL the engine itself enforces, not a source file). Narrow,
// unambiguous parse of one constraint — and never trusted alone: main() insert-tests every member
// it returns, which is what separates "this string appears in the DDL" from "the database accepts
// this value".
function deriveStatusUniverseFromDdl() {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    const row = raw.prepare("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'jobs_log'").get();
    if (!row || !row.sql) return null;
    const m = /status[\s\S]*?CHECK\s*\(\s*status\s+IN\s*\(([^)]*)\)/i.exec(row.sql);
    if (!m) return null;
    return new Set(m[1].split(',').map((s) => s.trim().replace(/^'|'$/g, '')).filter(Boolean));
  } finally {
    raw.close();
  }
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  fs.writeFileSync(sendersFile, [
    'senders:',
    '  - sender-id: probe-owner',
    '    kind: owner',
    `    token-hash: ${hashToken(OWNER_TOKEN)}`,
    '    enabled: true',
    '',
  ].join('\n'), { mode: 0o600 });
  fs.chmodSync(sendersFile, 0o600);

  const store = openHeartStore({ dbPath: tmpDb, profiles: {}, tickIntervalMs: TICK_INTERVAL_MS });

  // ── Seed the fleet through the store's OWN API (never raw SQL): recordExecutionStart always
  // inserts 'launching', so each row is then moved to its seeded status the way the daemon does.
  const seeded = { }; // status -> [exec_id] in insertion order
  let firedTick = 1;
  for (const { status, jobId } of SEED) {
    const row = store.recordExecutionStart({
      jobId,
      actionType: 'launch-agent',
      args: '{}',
      enqueuedBy: 'probe-inspect-executions',
      firedTick: firedTick++,
      firedAt: new Date(),
    });
    store.updateExecutionStatus(row.exec_id, { status });
    (seeded[status] = seeded[status] || []).push(row.exec_id);
  }
  out(`seeded: ${JSON.stringify(seeded)}`);

  const secret = crypto.randomBytes(32).toString('hex');
  const api = createInternalApi({ heartStore: store, spawnManager: { config: { profiles: {} } }, secret });
  const gw = createGateway({ dispatch: api.dispatch, internalSecret: secret, sendersFilePath: sendersFile });

  const inspect = (payload) => gw.handleRequest({ credential: OWNER_TOKEN, body: { intent: 'inspect', payload } });
  // A direct-dispatch envelope bypassing the gateway entirely — the core's own guards must hold
  // for a caller that never passed a door (probe-snooze's defense-in-depth pattern).
  const coreEnv = (payload) => ({
    v: 1, id: crypto.randomUUID(), ts: new Date().toISOString(), auth: secret,
    sender: { id: 'probe-owner', kind: 'owner', via: 'cli' }, intent: 'inspect', payload,
  });

  const diskBefore = readBackAllExecutions();

  // ── 1. TWO status filters, each returning EXACTLY its own rows (criteria: "at least two"). ──
  // The assertion is on the exec_id SET, not on a count: a count passes for a handler that
  // returned the wrong three rows, and this run has already paid for reading a count as a result.
  for (const status of ['failed', 'stalled']) {
    const r = await inspect({ target: 'executions', status });
    const rows = rowsOf(r);
    const gotIds = rows.map((x) => x.exec_id);
    const wantIds = seeded[status];
    check(`inspect executions --status ${status} returns EXACTLY its own ${wantIds.length} row(s), by exec_id`,
      r.body.ok === true && JSON.stringify(gotIds) === JSON.stringify(wantIds),
      `got=${JSON.stringify(gotIds)} want=${JSON.stringify(wantIds)}`);
    check(`every row returned for '${status}' actually CARRIES status '${status}' (no unfiltered leak)`,
      rows.length > 0 && rows.every((x) => x.status === status),
      `statuses=${JSON.stringify([...new Set(rows.map((x) => x.status))])}`);
    check(`the '${status}' result ECHOES its filter and reports eof`,
      resultOf(r).status === status && resultOf(r).eof === true,
      `status=${resultOf(r).status} eof=${resultOf(r).eof}`);
  }

  // The discriminator that a per-status check alone cannot make: the two filters must disagree.
  // A handler ignoring `status` returns the same rows for both and passes neither of the above
  // only by luck of the seed — this asserts the difference directly.
  {
    const a = await inspect({ target: 'executions', status: 'failed' });
    const b = await inspect({ target: 'executions', status: 'stalled' });
    const aIds = rowsOf(a).map((x) => x.exec_id);
    const bIds = rowsOf(b).map((x) => x.exec_id);
    const disjoint = aIds.every((id) => !bIds.includes(id)) && aIds.length > 0 && bIds.length > 0;
    check('two different filters return DISJOINT, NON-EMPTY sets (the filter is load-bearing, not decorative)',
      disjoint, `failed=${JSON.stringify(aIds)} stalled=${JSON.stringify(bIds)}`);
    check('neither filter returned the whole fleet (a filter that filters nothing would)',
      aIds.length < SEED.length && bIds.length < SEED.length,
      `failed=${aIds.length} stalled=${bIds.length} fleet=${SEED.length}`);
  }

  // ── 2. EMPTY RESULT — a VALID status with no rows (criteria: "plus an empty result"). ────────
  {
    const r = await inspect({ target: 'executions', status: 'killed' });
    check("a valid status with NO rows ('killed') is a SUCCESS with an empty list, never an error",
      r.body.ok === true && Array.isArray(resultOf(r).rows) && rowsOf(r).length === 0,
      `ok=${r.body.ok} rows=${JSON.stringify(resultOf(r).rows)}`);
    check('the empty result still echoes its filter and reports eof true, nextOffset 0',
      resultOf(r).status === 'killed' && resultOf(r).eof === true && resultOf(r).nextOffset === 0,
      `result=${JSON.stringify(resultOf(r).status ? resultOf(r) : r.body.error)}`);
    check('the empty result maps to HTTP 200 — no rows is not a failure', r.status === 200, `status=${r.status}`);
  }

  // ── 3. EMPTY is NOT the same answer as INVALID — the distinction that makes a typo visible. ──
  {
    const r = await inspect({ target: 'executions', status: 'no-such-status' });
    check('an UNKNOWN status is REFUSED at the gateway blaming status, never answered with an empty list',
      r.body.ok !== true && refusedField(r) === 'status',
      `ok=${r.body.ok} field=${refusedField(r)} error=${JSON.stringify(r.body.error && r.body.error.code)}`);
    check('the refusal NAMES the valid set (a refusal that does not is a guessing game)',
      Boolean(r.body.error) && /launching/.test(String(r.body.error.message)) && /killed/.test(String(r.body.error.message)),
      `message=${r.body.error && r.body.error.message}`);

    // Defense-in-depth: the CORE re-validates for a caller that never passed the gateway.
    const d = await api.dispatch(coreEnv({ target: 'executions', status: 'no-such-status' }));
    check('the CORE independently refuses an unknown status VALIDATION_FAILED, naming its check',
      d.error && d.error.code === 'VALIDATION_FAILED' && d.error.details && d.error.details.check === 'exec-status',
      `code=${d.error && d.error.code} details=${JSON.stringify(d.error && d.error.details)}`);
  }

  // ── 4. `status` is REQUIRED for executions, and REFUSED on every other target. ───────────────
  {
    const r = await inspect({ target: 'executions' });
    check('inspect executions WITHOUT --status is refused, and the refusal BLAMES status (not the target)',
      r.body.ok !== true && refusedField(r) === 'status',
      `ok=${r.body.ok} field=${refusedField(r)} error=${JSON.stringify(r.body.error && r.body.error.message)}`);

    const r2 = await inspect({ target: 'jobs', status: 'failed' });
    check("a `status` on a target that cannot honour it is REFUSED, blaming status, never accepted-and-ignored",
      r2.body.ok !== true && refusedField(r2) === 'status',
      `ok=${r2.body.ok} field=${refusedField(r2)} error=${JSON.stringify(r2.body.error && r2.body.error.message)}`);

    const r3 = await inspect({ target: 'executions', status: 'failed', id: 1 });
    check('inspect executions takes NO id (fleet-scoped, not execution-scoped), and the refusal blames id',
      r3.body.ok !== true && refusedField(r3) === 'id',
      `ok=${r3.body.ok} field=${refusedField(r3)} error=${JSON.stringify(r3.body.error && r3.body.error.message)}`);
  }

  // ── 5. PAGING — offset/limit, server-bounded, walkable to completion. ───────────────────────
  {
    const all = rowsOf(await inspect({ target: 'executions', status: 'failed' })).map((x) => x.exec_id);
    const page1 = await inspect({ target: 'executions', status: 'failed', offset: 0, limit: 2 });
    check('limit 2 returns the FIRST two rows and reports eof:false with a nextOffset',
      all.length >= 3 && rowsOf(page1).map((x) => x.exec_id).join() === all.slice(0, 2).join()
        && resultOf(page1).eof === false && resultOf(page1).nextOffset === 2,
      `rows=${JSON.stringify(rowsOf(page1).map((x) => x.exec_id))} eof=${resultOf(page1).eof} next=${resultOf(page1).nextOffset}`);

    const page2 = await inspect({ target: 'executions', status: 'failed', offset: resultOf(page1).nextOffset ?? 0, limit: 2 });
    const walked = rowsOf(page1).concat(rowsOf(page2)).map((x) => x.exec_id);
    check('walking nextOffset reaches EVERY row exactly once and terminates at eof:true',
      all.length > 0 && walked.join() === all.join() && resultOf(page2).eof === true,
      `walked=${JSON.stringify(walked)} all=${JSON.stringify(all)} eof=${resultOf(page2).eof}`);

    const past = await inspect({ target: 'executions', status: 'failed', offset: 999 });
    check('an offset past the end is an empty page at eof, never an error',
      past.body.ok === true && rowsOf(past).length === 0 && resultOf(past).eof === true,
      `ok=${past.body.ok} rows=${rowsOf(past).length}`);

    const over = await api.dispatch(coreEnv({ target: 'executions', status: 'failed', limit: 100000 }));
    check('an over-large limit is CLAMPED by the server, never honoured (contract § 1 bounded page)',
      over.ok === true && all.length > 0 && (over.result.rows || []).length === all.length,
      `rows=${over.result && over.result.rows && over.result.rows.length}`);
  }

  // ── 6. READ-ONLY — the whole exercise wrote NOTHING, read back from disk. ───────────────────
  {
    const diskAfter = readBackAllExecutions();
    check('the entire inspect exercise left jobs_log BYTE-IDENTICAL on disk (read-only surface)',
      JSON.stringify(diskBefore) === JSON.stringify(diskAfter),
      `before=${diskBefore.length} row(s) after=${diskAfter.length} row(s)`);
  }

  // ── 7. TARGET-SET LOCKSTEP — the three copies, guarded by nothing before this probe. ────────
  {
    const gwT = setOrNull(GW_TARGETS), coreT = setOrNull(CORE_TARGETS), cliT = setOrNull(CLI_TARGETS);
    const unexported = [
      gwT ? null : 'gateway/parse.js INSPECT_TARGETS',
      coreT ? null : 'dispatch.js INSPECT_TARGETS',
      cliT ? null : 'cli/commands/inspect.js TARGETS',
    ].filter(Boolean);
    check('all three inspect TARGET sets are EXPORTED as data (a set the probe cannot read is a set nothing guards)',
      unexported.length === 0, unexported.length ? `NOT exported: ${unexported.join(' · ')}` : 'all three exported');

    const failures = unexported.length ? [] : checkClosedSetsLockstep({
      sets: [
        { name: 'gateway/parse.js INSPECT_TARGETS (front-door allowlist)', keys: [...gwT] },
        { name: 'dispatch.js INSPECT_TARGETS (server-core gate)', keys: [...coreT] },
        { name: 'cli/commands/inspect.js TARGETS (the CLI surface)', keys: [...cliT] },
      ],
      describe: {
        missing: (setName, target) =>
          `INSPECT-TARGET DRIFT: ${setName} is MISSING '${target}'. The inspect target set is duplicated ` +
          `BY DESIGN across the DEC-4 boundary (the gateway holds no core import) and again in the CLI, so ` +
          `every new target must extend ALL THREE together. A target in the core but not the gateway is ` +
          `refused at the front door; a target in the gateway but not the CLI is unreachable by the shipped ` +
          `client; a target in the CLI but not the gateway fails at the door with a shape error.`,
      },
    });
    for (const f of failures) out(`FAIL  ${f}`);
    check('the THREE copies of the inspect TARGET set are in lockstep',
      unexported.length === 0 && failures.length === 0,
      `gateway=${gwT ? gwT.size : 'unexported'} core=${coreT ? coreT.size : 'unexported'} cli=${cliT ? cliT.size : 'unexported'}`);
    check("'executions' is present in ALL THREE copies (this task's own additive change)",
      Boolean(gwT && coreT && cliT && gwT.has('executions') && coreT.has('executions') && cliT.has('executions')),
      `gateway=${gwT && gwT.has('executions')} core=${coreT && coreT.has('executions')} cli=${cliT && cliT.has('executions')}`);
  }

  // ── 8. STATUS-ENUM LOCKSTEP — the two code copies against the DATABASE'S OWN DDL. ───────────
  {
    const ddlStatuses = deriveStatusUniverseFromDdl();
    check('the live jobs_log.status CHECK constraint is derivable from the database DDL',
      ddlStatuses !== null && ddlStatuses.size > 0,
      `derived=${ddlStatuses ? JSON.stringify([...ddlStatuses]) : 'null'}`);

    if (ddlStatuses) {
      // The derivation is CROSS-CHECKED BEHAVIOURALLY before it is trusted as a universe: a
      // string parsed out of DDL text is not yet evidence the database accepts that value.
      const probeRow = store.recordExecutionStart({
        jobId: 'job-ddl-crosscheck', actionType: 'launch-agent', args: '{}',
        enqueuedBy: 'probe-inspect-executions', firedTick: 999, firedAt: new Date(),
      });
      let allInsertable = true;
      for (const s of ddlStatuses) {
        try { store.updateExecutionStatus(probeRow.exec_id, { status: s }); } catch { allInsertable = false; }
      }
      check('EVERY status derived from the DDL is one the database actually ACCEPTS (derivation cross-checked, not read)',
        allInsertable, `derived=${JSON.stringify([...ddlStatuses])}`);

      let bogusRefused = false;
      try { store.updateExecutionStatus(probeRow.exec_id, { status: 'probe-bogus-status' }); } catch { bogusRefused = true; }
      check('a status OUTSIDE the derived set is REFUSED by the constraint (the set is closed, and the probe can tell)',
        bogusRefused, `refused=${bogusRefused}`);

      const gwS = setOrNull(GW_STATUSES), coreS = setOrNull(CORE_STATUSES);
      check('both code copies of the status enum are EXPORTED as data',
        Boolean(gwS && coreS),
        `gateway=${gwS ? 'exported' : 'NOT exported'} core=${coreS ? 'exported' : 'NOT exported'}`);
      const failures = (!gwS || !coreS) ? [] : checkClosedSetsLockstep({
        sets: [
          { name: "the LIVE database's jobs_log.status CHECK constraint", keys: [...ddlStatuses] },
          { name: 'gateway/parse.js EXEC_STATUSES (front-door allowlist)', keys: [...gwS] },
          { name: 'dispatch.js EXEC_STATUSES (server-core re-validation)', keys: [...coreS] },
        ],
        describe: {
          missing: (setName, status) =>
            `EXEC-STATUS DRIFT: ${setName} is MISSING '${status}'. The status enum is copied into the gateway ` +
            `and the core because neither may import the schema (DEC-4), so the schema's CHECK constraint is ` +
            `the source of truth and both copies must track it. ⚑ IF TASK 7.46 HAS JUST LANDED, THIS IS THE ` +
            `EXPECTED FAILURE: 7.46 splits this enum into session-level and turn-level states, and ` +
            `'inspect executions' must be re-keyed to whichever level it filters (state it explicitly — ` +
            `do not default into one).`,
        },
      });
      for (const f of failures) out(`FAIL  ${f}`);
      check('the gateway and core status enums are in lockstep with the DATABASE, not merely with each other',
        Boolean(gwS && coreS) && failures.length === 0,
        `ddl=${ddlStatuses.size} gateway=${gwS ? gwS.size : 'unexported'} core=${coreS ? coreS.size : 'unexported'}`);
    }
  }

  // ── 9. THE CLI SEAM — the half a gateway+core probe cannot see. ─────────────────────────────
  // Every check above enters at the gateway, so all of them would stay green with the CLI command
  // broken, absent, or building the wrong payload — the shipped client is the ONLY thing an
  // operator actually types. This run has already paid for exactly this: a suite whose gate probes
  // ran outside the cage and whose wall probes ran inside, both halves green, the SEAM never
  // taken. So the CLI is driven here for real, through its own `run()`, with a stub ctx that
  // captures the payload it builds.
  {
    const seen = [];
    const stubCtx = {
      json: false,
      call: async (intent, payload) => {
        seen.push({ intent, payload });
        return { envelope: { ok: true, result: { target: 'executions', status: payload.status, rows: [], nextOffset: 0, eof: true } } };
      },
    };
    // ⚑ EVERY CLI DRIVE IS WRAPPED, and the reason is a defect THIS BLOCK ITSELF SHIPPED WITH.
    // When `executions` is missing from the CLI's TARGETS copy — the precise drift the lockstep
    // check above exists to catch — `run()` THROWS, and an unwrapped call faulted the probe out
    // AFTER the lockstep legs had correctly gone red but BEFORE the summary printed: no tally, no
    // FAILED list, just a stack trace and exit 1. G-121's truncation shape, introduced in the very
    // block added to close a seam, in a file whose other guards (resultOf/rowsOf/setOrNull) exist
    // to prevent exactly it. Caught by re-running the mutation against the COMMITTED probe rather
    // than trusting an earlier run's numbers. A probe must state its WHOLE finding on the code it
    // is meant to fail against — most of all when that code is the drift it guards.
    const driveCli = async (args) => {
      seen.length = 0;
      try { await cliInspect(args, stubCtx); return null; } catch (e) { return e; }
    };

    let err = await driveCli(['executions', '--status', 'failed']);
    check('the CLI builds the executions payload the server expects (intent inspect, target+status)',
      !err && seen.length === 1 && seen[0].intent === 'inspect'
        && seen[0].payload.target === 'executions' && seen[0].payload.status === 'failed',
      err ? `CLI REFUSED the target: ${err.message}` : `sent=${JSON.stringify(seen[0])}`);

    err = await driveCli(['executions', '--status', 'done', '--offset', '5', '--limit', '10']);
    check('the CLI forwards --offset/--limit as NUMBERS (a string offset would be shape-refused at the door)',
      !err && seen.length === 1 && seen[0].payload.offset === 5 && seen[0].payload.limit === 10,
      err ? `CLI REFUSED the target: ${err.message}` : `sent=${JSON.stringify(seen[0].payload)}`);

    let usageErr = null;
    try { await cliInspect(['executions'], stubCtx); } catch (e) { usageErr = e; }
    check('the CLI refuses `inspect executions` with no --status locally, without a round trip',
      Boolean(usageErr) && /status/.test(String(usageErr.message)),
      `error=${usageErr && usageErr.message}`);

    usageErr = null;
    try { await cliInspect(['executions', '--status', 'failed', '--bogus', 'x'], stubCtx); } catch (e) { usageErr = e; }
    check('the CLI refuses an unrecognized flag on executions (no silently-dropped argument)',
      Boolean(usageErr) && /unrecognized/.test(String(usageErr.message)),
      `error=${usageErr && usageErr.message}`);

    check("the CLI HELP documents the executions target (a surface nobody can discover is not shipped)",
      /inspect executions/.test(require('../../../cli/commands/inspect').HELP),
      'HELP checked for the executions line');
  }

  // ── 10. The parser is reachable as a unit — the shape refusal is the gateway's, not the core's.
  {
    let threw = false;
    try { parseRequest({ intent: 'inspect', payload: { target: 'executions', status: 'nope' } }); } catch { threw = true; }
    check('gateway parseRequest refuses an unknown status BEFORE the core is ever reached',
      threw, `threw=${threw}`);
  }

  closeHeartStore(store);

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`checks: ${checks.length}  passed: ${checks.length - failed.length}  failed: ${failed.length}`);
  if (failed.length) for (const f of failed) out(`FAILED: ${f.name}`);
  out(failed.length ? `RESULT: FAIL — ${failed.length} check(s) above.` : 'RESULT: PASS — inspect executions filters, pages, refuses, stays read-only, and both closed sets it extends are in lockstep.');
  out(`WALL_MS ${Date.now() - start}`);
  out(`EXIT ${failed.length ? 1 : 0}`);
  console.log(fs.readFileSync(outPath, 'utf8'));

  try { fs.unlinkSync(tmpDb); } catch {}
  try { fs.unlinkSync(sendersFile); } catch {}
  process.exit(failed.length ? 1 : 0);
}

main().catch((err) => {
  out(`PROBE FAULT: ${err && err.stack ? err.stack : err}`);
  out('EXIT 1');
  console.log(fs.readFileSync(outPath, 'utf8'));
  try { fs.unlinkSync(tmpDb); } catch {}
  try { fs.unlinkSync(sendersFile); } catch {}
  process.exit(1);
});
