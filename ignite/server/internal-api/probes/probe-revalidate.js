'use strict';

// probe-revalidate — internal-api-contract-spec.md test 1 (defense-in-depth):
// "Craft a gateway request that passes gateway parse but is invalid (e.g. a profile
// the server config lacks) -> VALIDATION_FAILED names the check; queue unchanged."
//
// THIS IS THE DEC-3 PROOF: gateway origin is NOT trust. The request below is REAL —
// it is driven through the REAL gateway (authenticated, shape-checked, forwarded)
// into the REAL internal API over the REAL heart store. The gateway CANNOT catch it,
// by design: it holds no server config, so "does this profile exist" is unknowable to
// it. The core catches it anyway. That gap is the whole point of the test.
//
// Also covers the boundary guarantees this module ships and would otherwise leave
// unproven: envelope serialization (test 5), detached inspect snapshots (test 5), and
// the version-skew guard (test 6).
//
// ⚑ EVERY STATE ASSERTION READS BACK FROM DISK on a fresh read-only connection —
// never the store's in-memory view and never a return value. p4-0's transferable
// finding: under mutation, return-value checks still PASSED and only a raw disk
// read-back caught the defect. A count is not a proof; identity on disk is.
//
// Isolation: a THROWAWAY db under os.tmpdir(), per the convention every heart probe
// follows. This probe WRITES — it must NEVER be pointed at the live store
// (.rbtv/heart/), which a live daemon is ticking against.
//
// The capture is truncated at module load, BEFORE any work (D51 evidence-husk
// hazard). The process exit code remains the truth.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-revalidate.out');
fs.writeFileSync(outPath, '');

const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createInternalApi } = require('../dispatch');
const { createGateway } = require('../../../gateway/gateway');
const { hashToken } = require('../../../gateway/sender-auth');

const tmpDb = path.join(os.tmpdir(), `ignite-probe-revalidate-${Date.now()}-${process.pid}.db`);
const sendersFile = path.join(os.tmpdir(), `ignite-probe-revalidate-senders-${Date.now()}-${process.pid}.yaml`);
const AGENT_TOKEN = crypto.randomBytes(16).toString('hex');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
const skipped = 0;
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// DISK truth. Read-only: a reader can never be a second writer.
function readBackQueue() {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT queue_id, job_id, args, enqueued_by, trigger_kind FROM queue ORDER BY queue_id').all();
  } finally {
    raw.close();
  }
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  fs.writeFileSync(sendersFile, [
    'senders:',
    '  - sender-id: probe-agent',
    '    kind: agent',
    `    token-hash: ${hashToken(AGENT_TOKEN)}`,
    '    enabled: true',
    '',
  ].join('\n'), { mode: 0o600 });
  fs.chmodSync(sendersFile, 0o600);

  // The server core's PINNED config knows exactly ONE profile. `ghost-profile` below
  // is therefore semantically invalid while being perfectly well-SHAPED.
  const store = openHeartStore({
    dbPath: tmpDb,
    profiles: { 'test-sleep': { headed: false } },
  });
  store.registerJob({
    jobId: 'launch-worker',
    actionType: 'launch-agent',
    function: 'spawnLaunchAgent',
    argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: {} }),
    enabled: 1,
  });

  const secret = crypto.randomBytes(32).toString('hex');
  const api = createInternalApi({
    heartStore: store,
    spawnManager: { config: { profiles: { 'test-sleep': { headed: false } } } },
    secret,
  });
  const gw = createGateway({ dispatch: api.dispatch, internalSecret: secret, sendersFilePath: sendersFile });

  const runAt = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const addJob = (profile) => ({
    intent: 'enqueue-job',
    payload: {
      job_id: 'launch-worker',
      args: JSON.stringify({ profile }),
      trigger_kind: 'scheduled',
      run_at: runAt,
      session_mode: 'headless',
    },
  });

  const before = readBackQueue();
  check('setup: the queue starts empty ON DISK', before.length === 0, `disk queue rows=${before.length}`);

  // --- 1. THE DEFENSE-IN-DEPTH CASE: parses at the gateway, refused by the core.
  let r = await gw.handleRequest({ credential: AGENT_TOKEN, body: addJob('ghost-profile'), source: '127.0.0.1' });
  check('a semantically-invalid job is REFUSED past the gateway',
    r.body.ok === false, `ok=${r.body.ok}`);
  check('the refusal is typed VALIDATION_FAILED (not a shape error — the gateway could not know)',
    r.body.error && r.body.error.code === 'VALIDATION_FAILED',
    `code=${r.body.error && r.body.error.code}`);
  check('the typed error NAMES the failing check (the contract\'s own requirement)',
    r.body.error && r.body.error.details && r.body.error.details.check === 'E_UNKNOWN_PROFILE',
    `details=${JSON.stringify(r.body.error && r.body.error.details)}`);
  check('the refusal maps to the CLI\'s exit-4 class (HTTP 400)', r.status === 400, `status=${r.status}`);

  let after = readBackQueue();
  check('NOTHING was written — the queue is unchanged ON DISK (identity, not a count)',
    after.length === 0,
    `disk queue rows=${after.length}`);

  // --- 2. The gateway genuinely CANNOT catch it — the guard under test is the core's.
  // If the gateway had refused this at shape-check, the test above would be vacuous:
  // it would prove the gateway works, not that the core re-validates.
  const { parseRequest } = require('../../../gateway/parse');
  let gatewayCaught = false;
  try {
    parseRequest({ intent: 'enqueue-job', payload: addJob('ghost-profile').payload });
  } catch {
    gatewayCaught = true;
  }
  check('the GATEWAY passes this request (so the refusal above is genuinely the CORE re-validating)',
    gatewayCaught === false,
    'gateway shape-check accepted the well-formed-but-semantically-invalid job');

  // --- 3. MUTATION: the same request with a REAL profile MUST enqueue.
  // A core that refused everything would pass every check above.
  r = await gw.handleRequest({ credential: AGENT_TOKEN, body: addJob('test-sleep'), source: '127.0.0.1' });
  check('MUTATION: the SAME request naming a REAL profile is ACCEPTED (the guard discriminates)',
    r.body.ok === true && Number.isInteger(r.body.result.jobId),
    `ok=${r.body.ok} jobId=${r.body.result && r.body.result.jobId}`);

  after = readBackQueue();
  check('the valid job landed ON DISK, identified',
    after.length === 1 && after[0].queue_id === r.body.result.jobId && after[0].job_id === 'launch-worker',
    `disk row=${JSON.stringify(after[0])}`);

  // --- 4. `enqueued_by` is stamped from the ATTESTED sender, never the payload.
  check('enqueued_by ON DISK is the AUTHENTICATED sender id (the audit trail is not caller-supplied)',
    after[0].enqueued_by === 'probe-agent',
    `enqueued_by=${after[0].enqueued_by}`);

  // --- 5. Envelope serialization (test 5): a circular ref is BAD_ENVELOPE.
  const circular = { v: 1, id: 'x', ts: runAt, auth: secret, sender: { id: 'probe-agent', kind: 'agent', via: 'cli' }, intent: 'inspect', payload: { target: 'queue' } };
  circular.payload.self = circular;
  let d = await api.dispatch(circular);
  check('a circular reference is refused BAD_ENVELOPE at the boundary',
    d.error && d.error.code === 'BAD_ENVELOPE', `code=${d.error && d.error.code}`);

  // A live handle (here: a function) must not slip across as a silent hole. JSON
  // .stringify DROPS functions rather than throwing, so without the explicit
  // assertion walk this would cross the boundary as if it were never there.
  const withHandle = { v: 1, id: 'x', ts: runAt, auth: secret, sender: { id: 'probe-agent', kind: 'agent', via: 'cli' }, intent: 'inspect', payload: { target: 'queue', handle: () => {} } };
  d = await api.dispatch(withHandle);
  check('a LIVE HANDLE (function) is refused BAD_ENVELOPE, not silently dropped',
    d.error && d.error.code === 'BAD_ENVELOPE', `code=${d.error && d.error.code}`);

  // --- 6. Detached snapshots (test 5): mutating a returned inspect result cannot
  // reach server-core state.
  const env = (intent, payload) => ({ v: 1, id: crypto.randomUUID(), ts: runAt, auth: secret, sender: { id: 'probe-agent', kind: 'agent', via: 'cli' }, intent, payload });
  d = await api.dispatch(env('inspect', { target: 'queue' }));
  check('inspect returns a plain-data snapshot', d.ok === true && Array.isArray(d.result.rows), `rows=${d.result && d.result.rows.length}`);
  d.result.rows[0].job_id = 'MUTATED-BY-THE-GATEWAY';
  d.result.rows.push({ queue_id: 999, job_id: 'INJECTED' });
  const afterMutation = readBackQueue();
  check('mutating the returned snapshot does NOT reach server-core state (proven ON DISK)',
    afterMutation.length === 1 && afterMutation[0].job_id === 'launch-worker',
    `disk rows=${afterMutation.length} job_id=${afterMutation[0].job_id}`);

  // --- 7. Version skew (test 6) and unknown intent.
  d = await api.dispatch({ ...env('inspect', { target: 'queue' }), v: 99 });
  check('an unsupported major version is refused VERSION_MISMATCH',
    d.error && d.error.code === 'VERSION_MISMATCH', `code=${d.error && d.error.code}`);
  d = await api.dispatch(env('not-an-intent', {}));
  check('an unknown intent is UNKNOWN_INTENT, distinct from a bad payload',
    d.error && d.error.code === 'UNKNOWN_INTENT', `code=${d.error && d.error.code}`);

  closeHeartStore();
}

main().then(() => {
  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`SKIPPED_COUNT: ${skipped}`);
  out(`REVALIDATE_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
}).catch((err) => {
  out('ERROR:', err.message, err.stack);
  out(`SKIPPED_COUNT: ${skipped}`);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
}).finally(() => {
  try { closeHeartStore(); } catch {}
  try { fs.unlinkSync(sendersFile); } catch {}
  for (const suffix of ['', '-wal', '-shm']) {
    try { fs.unlinkSync(tmpDb + suffix); } catch {}
  }
});
