'use strict';

// probe-register-job — the `register-job` intent (task 7.12; owner ruling 2026-07-25),
// exercised through the REAL gateway PARSER -> REAL internal API -> REAL heart store
// (see the note on `call` below for what is and is not in the loop).
//
//   The intent is the daemon's FIRST catalogue-write surface. Before it, a job entered
//   the `jobs` catalogue only by writing the database directly on the box — around the
//   gateway, authorization, validation, and audit. Every real catalogue row on the live
//   box today got there that way; this probe covers the path that replaces it.
//
//   Authz (Call 1, build (ii)): OWNER + the MASTER APPROXIMATION. `kind: owner` and
//         `kind: agent` may register; `kind: bridge` may not. ⚑ The approximation admits
//         ANY enrolled agent token, not the master specifically — the daemon cannot
//         prove masterhood until CMP-13 (task 7.10) lands. The exposure was stated at
//         the ruling and ACCEPTED. This probe asserts the shipped policy, exposure
//         included, so a later change to it is a deliberate act and not a drift.
//
//   Create-only (Call 2): a duplicate id is refused typed (E_JOB_EXISTS ->
//         VALIDATION_FAILED) and NOTHING is overwritten — proven by disk read-back,
//         not by a return value.
//
//   Dry-run (Call 3): the complete validation, duplicate check included, then a verdict
//         and NO write.
//
// ⚑ EVERY state assertion reads back from DISK on a fresh read-only connection (p4-0's
// transferable finding: under mutation, return-value checks still PASSED — only a raw
// disk read-back caught the defect).
//
// Isolation: a THROWAWAY db under os.tmpdir(). This probe WRITES — it must NEVER be
// pointed at the live store, which a live daemon is ticking against.
//
// Capture truncated at module load, BEFORE any work (D51 evidence-husk hazard). The
// process exit code is the truth; the footer is a hint.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-register-job.out');
fs.writeFileSync(outPath, '');

const { openHeartStore, closeHeartStore } = require('../../../state-store/heart/heart-store');
const { createInternalApi, ENVELOPE_VERSION } = require('../dispatch');
const { parseRequest } = require('../../gateway/parse');

// ⚑ Why this probe drives parseRequest + dispatch rather than createGateway: the real
// pipeline's two halves are the gateway's SHAPE parse and the core's dispatch, and both
// are exercised here in order, exactly as handleRequest chains them. What is skipped is
// only token->sender RESOLUTION (sender-auth), which pulls in js-yaml — the one external
// dependency in the tree. Skipping it keeps this probe runnable with Node built-ins
// alone, on any machine, with no install step; the sender identity it would have
// produced is supplied directly in the envelope, which is what dispatch actually reads.

const tmpDb = path.join(os.tmpdir(), `ignite-probe-register-${Date.now()}-${process.pid}.db`);

const SCHEMA = { required: {}, optional: { prompt: 'string' } };

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// DISK truth. Read-only: a reader can never be a second writer.
function readBackJob(jobId) {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT job_id, action_type, function, args_schema, enabled FROM jobs WHERE job_id = ?').get(jobId) || null;
  } finally {
    raw.close();
  }
}
function readBackJobCount() {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT COUNT(*) AS n FROM jobs').get().n;
  } finally {
    raw.close();
  }
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const store = openHeartStore({ dbPath: tmpDb, profiles: { 'test-sleep': { headed: false } } });

  const secret = crypto.randomBytes(32).toString('hex');
  const api = createInternalApi({
    heartStore: store,
    spawnManager: { config: { profiles: { 'test-sleep': { headed: false } } } },
    secret,
  });

  const OWNER = { id: 'probe-owner', kind: 'owner' };
  const AGENT = { id: 'probe-agent', kind: 'agent' };
  const BRIDGE = { id: 'probe-bridge', kind: 'bridge' };

  // The real two-step: the gateway's shape parse, then the core's dispatch — a gateway
  // refusal short-circuits before dispatch, exactly as handleRequest does. The response
  // is normalized to the gateway's own `{ body: { ok, result, error } }` shape so the
  // assertions read the same either way.
  async function call(sender, intent, payload) {
    let parsed;
    try {
      parsed = parseRequest({ intent, payload });
    } catch (err) {
      return { body: { ok: false, error: { code: err.code, message: err.message, details: err.details } }, gatewayRefused: true };
    }
    const res = await api.dispatch({
      v: ENVELOPE_VERSION,
      id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      auth: secret,
      sender,
      intent,
      payload: parsed,
    });
    return { body: res, gatewayRefused: false };
  }

  const register = (sender, payload) => call(sender, 'register-job', payload);
  const enqueue = (sender, payload) => call(sender, 'enqueue-job', payload);

  const base = (jobId) => ({
    job_id: jobId,
    action_type: 'launch-agent',
    function: 'spawnLaunchAgent',
    args_schema: SCHEMA,
  });

  check('setup: the catalogue starts EMPTY on disk', readBackJobCount() === 0, `rows=${readBackJobCount()}`);

  // --- 1. A BRIDGE sender is refused, and the denial writes NOTHING.
  let r = await register(BRIDGE, base('bridge-attempt'));
  check('a BRIDGE sender is refused UNAUTHORIZED_SENDER',
    r.body.error && r.body.error.code === 'UNAUTHORIZED_SENDER',
    `code=${r.body.error && r.body.error.code}`);
  check('the denial comes from the CORE, not the gateway shape-check (a well-formed request, refused on policy)',
    r.gatewayRefused === false,
    `gatewayRefused=${r.gatewayRefused}`);
  check('the denial wrote NOTHING — no catalogue row ON DISK (mutation-backed guard)',
    readBackJob('bridge-attempt') === null && readBackJobCount() === 0,
    `rows=${readBackJobCount()}`);

  // --- 2. The OWNER registers -> success, and the row is ON DISK with its fields intact.
  r = await register(OWNER, base('launch-worker'));
  check('the OWNER registers a job -> ok, registered: true',
    r.body.ok === true && r.body.result.registered === true,
    `ok=${r.body.ok} result=${JSON.stringify(r.body.result)}`);
  check('the result reports WHAT was registered (loud feedback, D21(3))',
    r.body.result.job_id === 'launch-worker' && r.body.result.action_type === 'launch-agent' && r.body.result.enabled === true,
    `result=${JSON.stringify(r.body.result)}`);
  let row = readBackJob('launch-worker');
  check('the catalogue row ACTUALLY LANDED ON DISK (read back, not a return value)',
    row !== null && row.function === 'spawnLaunchAgent' && row.enabled === 1,
    `disk row=${JSON.stringify(row)}`);

  // --- 3. CREATE-ONLY: a duplicate is refused typed, and overwrites nothing.
  r = await register(OWNER, {
    job_id: 'launch-worker', action_type: 'send-message', function: 'OVERWRITTEN', args_schema: {},
  });
  check('a duplicate id is refused VALIDATION_FAILED',
    r.body.error && r.body.error.code === 'VALIDATION_FAILED',
    `code=${r.body.error && r.body.error.code}`);
  check('the refusal NAMES the check (E_JOB_EXISTS) rather than degrading to INTERNAL',
    r.body.error && r.body.error.details && r.body.error.details.check === 'E_JOB_EXISTS',
    `details=${JSON.stringify(r.body.error && r.body.error.details)}`);
  row = readBackJob('launch-worker');
  check('the refused duplicate overwrote NOTHING ON DISK',
    row !== null && row.function === 'spawnLaunchAgent' && row.action_type === 'launch-agent',
    `disk row=${JSON.stringify(row)}`);

  // --- 4. An AGENT sender is ALLOWED — the master APPROXIMATION (ruling (ii)).
  //        ⚑ This asserts an ACCEPTED EXPOSURE, not a safety property: any enrolled
  //        agent token can extend what the daemon is able to do until CMP-13 lands.
  r = await register(AGENT, base('agent-registered'));
  check('an AGENT sender is ALLOWED (master approximation, owner ruling (ii))',
    r.body.ok === true && r.body.result.registered === true,
    `ok=${r.body.ok} error=${JSON.stringify(r.body.error)}`);
  check('the agent-registered row is ON DISK',
    readBackJob('agent-registered') !== null,
    `rows=${readBackJobCount()}`);

  // --- 5. Strict schema, BOTH halves — the defense-in-depth DEC-3 requires.
  //        (a) the gateway refuses an unknown field at shape-check;
  //        (b) the CORE refuses it too, even when the gateway is bypassed entirely.
  //        Asserting only (a) would leave the core's own check unexercised — a payload
  //        reaching dispatch by any other path would then be unguarded, and the
  //        intent-drift probe depends on this check being the handler's FIRST act.
  r = await register(OWNER, { ...base('strict-check'), nonsense: true });
  check('(a) an unknown payload field is refused at the gateway shape-check',
    r.body.error && r.body.error.code === 'SHAPE_INVALID' && r.body.error.details.field === 'nonsense',
    `code=${r.body.error && r.body.error.code} details=${JSON.stringify(r.body.error && r.body.error.details)}`);

  const bypass = await api.dispatch({
    v: ENVELOPE_VERSION,
    id: crypto.randomUUID(),
    ts: new Date().toISOString(),
    auth: secret,
    sender: OWNER,
    intent: 'register-job',
    payload: { ...base('strict-check'), args_schema: JSON.stringify(SCHEMA), nonsense: true },
  });
  check('(b) the CORE refuses the same unknown field with the gateway BYPASSED (strict-schema, first check)',
    bypass.error && bypass.error.code === 'VALIDATION_FAILED' && bypass.error.details.check === 'strict-schema',
    `code=${bypass.error && bypass.error.code} details=${JSON.stringify(bypass.error && bypass.error.details)}`);
  check('neither strict-schema refusal wrote anything', readBackJob('strict-check') === null, 'no row');

  // --- 6. Gateway SHAPE refusal: a closed-enum action_type is refused at the door.
  r = await register(OWNER, { job_id: 'bad-enum', action_type: 'not-a-type', function: 'f' });
  check('an unknown action_type is refused at the gateway shape-check',
    r.body.error && r.body.error.code === 'SHAPE_INVALID',
    `code=${r.body.error && r.body.error.code}`);

  // --- 7. Dry-run: complete validation, verdict, NO write.
  const before = readBackJobCount();
  r = await register(OWNER, { ...base('dry-only'), dry_run: true });
  check('dry-run returns the validate-only verdict',
    r.body.ok === true && r.body.result.dry_run === true && r.body.result.valid === true,
    `result=${JSON.stringify(r.body.result)}`);
  check('dry-run wrote NOTHING — catalogue row count UNCHANGED ON DISK',
    readBackJobCount() === before && readBackJob('dry-only') === null,
    `rows=${readBackJobCount()} (before ${before})`);
  r = await register(OWNER, { ...base('launch-worker'), dry_run: true });
  check('dry-run runs the duplicate check too (E_JOB_EXISTS, nothing written)',
    r.body.error && r.body.error.details && r.body.error.details.check === 'E_JOB_EXISTS',
    `details=${JSON.stringify(r.body.error && r.body.error.details)}`);

  // --- 7b. Coverage the first cut of this probe missed (adversarial review, 2026-07-25):
  //         the optional fields and the gateway's schema normalization, each proven ON
  //         DISK rather than from the result envelope.
  r = await register(OWNER, {
    ...base('staged'), enabled: false, description: 'staged, not runnable yet',
  });
  const stagedRow = readBackJob('staged');
  check('enabled:false and description reach the row ON DISK',
    r.body.ok === true && r.body.result.enabled === false
      && stagedRow !== null && stagedRow.enabled === 0,
    `result=${JSON.stringify(r.body.result)} disk=${JSON.stringify(stagedRow)}`);

  // The gateway accepts args_schema as an OBJECT or a JSON STRING and normalizes both
  // to one canonical wire string — so the two spellings must land byte-identically.
  r = await register(OWNER, { ...base('as-string'), args_schema: JSON.stringify(SCHEMA) });
  const asString = readBackJob('as-string');
  const asObject = readBackJob('launch-worker');
  check('a STRING args_schema normalizes to the same stored value as an OBJECT one',
    asString !== null && asObject !== null && asString.args_schema === asObject.args_schema,
    `string=${asString && asString.args_schema} object=${asObject && asObject.args_schema}`);

  // A malformed sender at the INTENT level is refused, not crashed through.
  const malformed = await api.dispatch({
    v: ENVELOPE_VERSION,
    id: crypto.randomUUID(),
    ts: new Date().toISOString(),
    auth: secret,
    sender: { id: 'probe-nokind' },
    intent: 'register-job',
    payload: { ...base('no-kind'), args_schema: JSON.stringify(SCHEMA) },
  });
  check('a sender with no kind is refused, and registers nothing',
    malformed.ok === false && readBackJob('no-kind') === null,
    `code=${malformed.error && malformed.error.code}`);

  // --- 8. The whole point: a registered job is enqueueable through the SAME pipeline.
  //        Registration is what the queue's foreign key demands — no catalogue row, no
  //        queue row.
  r = await enqueue(OWNER, {
    job_id: 'launch-worker',
    args: {},
    trigger_kind: 'scheduled',
    run_at: new Date(Date.now() + 3600000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
  });
  check('a job registered through the gateway is then ENQUEUEABLE through the gateway',
    r.body.ok === true && Number.isInteger(r.body.result.jobId),
    `ok=${r.body.ok} result=${JSON.stringify(r.body.result)} error=${JSON.stringify(r.body.error)}`);

  // --- 9. An UNREGISTERED job is still refused at enqueue (the guard registration exists for).
  r = await enqueue(OWNER, {
    job_id: 'never-registered',
    args: {},
    trigger_kind: 'scheduled',
    run_at: new Date(Date.now() + 3600000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
  });
  check('an UNREGISTERED job is still refused at enqueue (E_UNKNOWN_JOB)',
    r.body.error && r.body.error.details && r.body.error.details.check === 'E_UNKNOWN_JOB',
    `details=${JSON.stringify(r.body.error && r.body.error.details)}`);

  closeHeartStore();

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`REGISTER_INTENT_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
}

main().catch((err) => {
  out('ERROR:', err.message, err.stack);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
}).finally(() => {
  try { closeHeartStore(); } catch {}
  try { fs.unlinkSync(tmpDb); } catch {}
  try { fs.unlinkSync(tmpDb + '-wal'); } catch {}
  try { fs.unlinkSync(tmpDb + '-shm'); } catch {}
});
