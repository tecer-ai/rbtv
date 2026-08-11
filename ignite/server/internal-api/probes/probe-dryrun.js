'use strict';

// probe-dryrun — validate-only enqueue mode (owner ruling D72 + D73, task p4-1c).
//
// Proves the ADDITIVE `dry_run` payload field on `enqueue-job`: the server core runs
// the COMPLETE re-validation, but on success SKIPS the single-writer insert and returns
// the verdict `{ dry_run: true, valid: true }` — the queue is UNCHANGED — and on a check
// failure returns the SAME typed VALIDATION_FAILED (failing check named) it returns today.
//
// It also carries the NARROW-GRANT REGRESSION GUARD (D73): because this reopened a
// certified store (heart-store.js), a NORMAL enqueue (no dry_run) MUST still INSERT (+1).
// The default write path is proven intact BY MUTATION on disk, not by inspection.
//
// The request path is REAL end-to-end: driven through the REAL gateway (authenticated,
// shape-checked, forwarded) into the REAL internal API over the REAL heart store —
// exactly mirroring probe-revalidate.js's construction (DEC-3: gateway origin is not
// trust; the gateway forwards `dry_run`, the CORE decides whether to write).
//
// ⚑ EVERY STATE ASSERTION READS BACK FROM DISK on a fresh read-only connection — never
// the store's in-memory view and never a return value. p4-0's transferable finding:
// under mutation, return-value checks still PASSED and only a raw disk read-back caught
// the defect. A count is not a proof; identity on disk is.
//
// Isolation: a THROWAWAY db under os.tmpdir(). This probe WRITES — it must NEVER be
// pointed at the live store (.rbtv/heart/), which a live daemon is ticking against.
//
// The capture is truncated at module load, BEFORE any work (D51 evidence-husk hazard).
// The process exit code remains the truth.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-dryrun.out');
fs.writeFileSync(outPath, '');

const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createInternalApi } = require('../dispatch');
const { createGateway } = require('../../../gateway/gateway');
const { hashToken } = require('../../../gateway/sender-auth');

const tmpDb = path.join(os.tmpdir(), `ignite-probe-dryrun-${Date.now()}-${process.pid}.db`);
const sendersFile = path.join(os.tmpdir(), `ignite-probe-dryrun-senders-${Date.now()}-${process.pid}.yaml`);
const AGENT_TOKEN = crypto.randomBytes(16).toString('hex');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
let skipped = 0;   // 7.736 §6 raises it where `--arm-state` is unreadable (no python3 → a VPS proof)
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
    // Section 6 (7.736) enqueues a `start-workflow` row, and the store re-validates the named
    // workflow against this map exactly as it re-validates a named profile above.
    workflows: { planning: { argv: ['/usr/bin/python3'] } },
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
  // `dryRun` omitted → the field is ABSENT from the payload (proves the default write
  // path is truly opt-out, not merely `dry_run: false`); when supplied it is a boolean.
  const addJob = (profile, dryRun) => {
    const payload = {
      job_id: 'launch-worker',
      args: JSON.stringify({ profile }),
      trigger_kind: 'scheduled',
      run_at: runAt,
      session_mode: 'headless',
    };
    if (dryRun !== undefined) payload.dry_run = dryRun;
    return { intent: 'enqueue-job', payload };
  };

  // --- 0. SEED a KNOWN count on disk: one real enqueue → the queue holds exactly 1 row.
  // Every dry-run assertion below is measured against THIS seeded count (D72's mutation-
  // backed proof: seed, dry-run, re-count = same).
  let r = await gw.handleRequest({ credential: AGENT_TOKEN, body: addJob('test-sleep'), source: '127.0.0.1' });
  check('SEED: a normal enqueue lands one row (establishes a known count)',
    r.body.ok === true && Number.isInteger(r.body.result.jobId),
    `ok=${r.body.ok} jobId=${r.body.result && r.body.result.jobId}`);
  const seeded = readBackQueue();
  check('SEED: the queue holds exactly 1 row ON DISK', seeded.length === 1, `disk queue rows=${seeded.length}`);
  const seededCount = seeded.length;

  // --- 1. VALID dry_run → verdict, and NOTHING written (count UNCHANGED on disk).
  r = await gw.handleRequest({ credential: AGENT_TOKEN, body: addJob('test-sleep', true), source: '127.0.0.1' });
  check('a VALID dry_run is ACCEPTED past the gateway',
    r.body.ok === true, `ok=${r.body.ok} error=${JSON.stringify(r.body.error)}`);
  check('the result is the verdict { dry_run: true, valid: true } (NOT a jobId)',
    r.body.result && r.body.result.dry_run === true && r.body.result.valid === true
      && r.body.result.jobId === undefined,
    `result=${JSON.stringify(r.body.result)}`);
  let after = readBackQueue();
  check('NOTHING was written — the queue row count is UNCHANGED ON DISK (seed vs after dry-run)',
    after.length === seededCount,
    `disk queue rows=${after.length} (seeded=${seededCount})`);

  // --- 2. INVALID dry_run → the SAME typed VALIDATION_FAILED (check named), still nothing written.
  r = await gw.handleRequest({ credential: AGENT_TOKEN, body: addJob('ghost-profile', true), source: '127.0.0.1' });
  check('an INVALID dry_run (unknown profile) is REFUSED', r.body.ok === false, `ok=${r.body.ok}`);
  check('the refusal is typed VALIDATION_FAILED (identical to the non-dry_run failure path)',
    r.body.error && r.body.error.code === 'VALIDATION_FAILED',
    `code=${r.body.error && r.body.error.code}`);
  check('the typed error NAMES the failing check (E_UNKNOWN_PROFILE — the core re-validated)',
    r.body.error && r.body.error.details && r.body.error.details.check === 'E_UNKNOWN_PROFILE',
    `details=${JSON.stringify(r.body.error && r.body.error.details)}`);
  check('the invalid-dry_run refusal maps to the CLI exit-4 class (HTTP 400)', r.status === 400, `status=${r.status}`);
  after = readBackQueue();
  check('an INVALID dry_run writes NOTHING — queue row count UNCHANGED ON DISK',
    after.length === seededCount,
    `disk queue rows=${after.length} (seeded=${seededCount})`);

  // --- 3. NARROW-GRANT REGRESSION GUARD (D73): a NORMAL enqueue (no dry_run) STILL INSERTS (+1).
  // This is the proof that reopening the certified store left the DEFAULT write path intact —
  // by MUTATION on disk, not inspection. A store that had lost its insert would fail HERE.
  r = await gw.handleRequest({ credential: AGENT_TOKEN, body: addJob('test-sleep'), source: '127.0.0.1' });
  check('MUTATION: a NORMAL enqueue (no dry_run) is ACCEPTED and mints a jobId',
    r.body.ok === true && Number.isInteger(r.body.result.jobId),
    `ok=${r.body.ok} jobId=${r.body.result && r.body.result.jobId}`);
  after = readBackQueue();
  check('the DEFAULT write path is INTACT — the queue grew by exactly 1 ON DISK (+1 over seed)',
    after.length === seededCount + 1 && after.some((row) => row.queue_id === r.body.result.jobId),
    `disk queue rows=${after.length} (seeded=${seededCount}) newId=${r.body.result && r.body.result.jobId}`);

  // --- 4. `dry_run: false` explicitly ALSO inserts (opt-in is by truthiness, not presence).
  r = await gw.handleRequest({ credential: AGENT_TOKEN, body: addJob('test-sleep', false), source: '127.0.0.1' });
  check('an explicit dry_run:false STILL INSERTS (the mode is opt-in by TRUE, not by presence)',
    r.body.ok === true && Number.isInteger(r.body.result.jobId),
    `ok=${r.body.ok} jobId=${r.body.result && r.body.result.jobId}`);
  after = readBackQueue();
  check('dry_run:false grew the queue by one more ON DISK (+2 over seed)',
    after.length === seededCount + 2,
    `disk queue rows=${after.length} (seeded=${seededCount})`);

  // --- 5. A non-boolean dry_run is refused at SHAPE-CHECK (gateway), never reaching the core.
  const badShape = await gw.handleRequest({
    credential: AGENT_TOKEN,
    body: { intent: 'enqueue-job', payload: { ...addJob('test-sleep').payload, dry_run: 'yes' } },
    source: '127.0.0.1',
  });
  check('a non-boolean dry_run is REFUSED (shape-check) — a bad shape can never flip the write path',
    badShape.body.ok === false, `ok=${badShape.body.ok} error=${JSON.stringify(badShape.body.error)}`);
  after = readBackQueue();
  check('the non-boolean dry_run wrote NOTHING ON DISK (count still +2 over seed)',
    after.length === seededCount + 2,
    `disk queue rows=${after.length} (seeded=${seededCount})`);

  // --- 6. TASK 7.736 DOOR 1: a `start-workflow` dry-run carries the goal's ARMING verdict. ------
  // The point of the door: `dry-run: VALID` used to be printed for a start-workflow whose goal
  // could never advance past its first seat, because arming (`coordination/edge-fastpath.json`) is
  // read only by `jobs/edge-runner-job.py` at CHECK-OUT time and is silent there when unarmed.
  //
  // ⚠ THE NEGATIVE ROW IS THE ONE THAT CANNOT BE FAKED: a non-start-workflow dry-run must carry NO
  // `edge_fastpath` KEY AT ALL. An absent key and a `null` verdict are different claims — "never
  // asked" versus "could not answer" — and a door that emitted the key everywhere would make the
  // action gate unobservable.
  //
  // ⚠ The two ARMED/UNARMED rows shell out to `edge-runner-job.py --arm-state` through `python3`.
  // Where that is unavailable (the Windows desktop) the door correctly reports `armed: null` —
  // UNKNOWN, never armed — and these rows read that as the SKIP it is, so the probe never claims a
  // verdict it did not obtain. The armed/unarmed verdicts are a VPS proof.
  const wfRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-dryrun-wf-'));
  const armedPkg = path.join(wfRoot, '.rbtv', 'goals', 'probe-armed-goal');
  const unarmedPkg = path.join(wfRoot, '.rbtv', 'goals', 'probe-unarmed-goal');
  fs.mkdirSync(path.join(armedPkg, 'coordination'), { recursive: true });
  fs.mkdirSync(path.join(unarmedPkg, 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(armedPkg, 'coordination', 'edge-fastpath.json'),
    JSON.stringify({ 'job-id': 'probe-edge-runner', profile: 'planning' }));

  store.registerJob({
    jobId: 'start-planning',
    actionType: 'start-workflow',
    function: 'startWorkflow',
    argsSchema: JSON.stringify({ required: { workflow: 'string', workdir: 'string', goal: 'string', 'entry-seat': 'string' }, optional: {} }),
    enabled: 1,
  });
  const wfDry = async (workdir) => (await gw.handleRequest({
    credential: AGENT_TOKEN,
    source: '127.0.0.1',
    body: {
      intent: 'enqueue-job',
      payload: {
        job_id: 'start-planning',
        args: JSON.stringify({ workflow: 'planning', workdir, goal: path.basename(workdir), 'entry-seat': 'elicitator' }),
        trigger_kind: 'scheduled',
        run_at: runAt,
        session_mode: 'headless',
        dry_run: true,
      },
    },
  })).body.result;

  const unarmedVerdict = await wfDry(unarmedPkg);
  const armedVerdict = await wfDry(armedPkg);
  check('7.736 D1: a start-workflow dry-run is still VALID and now CARRIES an edge_fastpath verdict',
    unarmedVerdict && unarmedVerdict.dry_run === true && unarmedVerdict.valid === true
      && unarmedVerdict.edge_fastpath !== undefined,
    `result=${JSON.stringify(unarmedVerdict)}`);
  if (unarmedVerdict && unarmedVerdict.edge_fastpath && unarmedVerdict.edge_fastpath.armed === null) {
    skipped += 2;
    out(`SKIP: --arm-state UNREADABLE here, so the armed/unarmed verdicts are a VPS proof — ${unarmedVerdict.edge_fastpath.scope}`);
  } else {
    check('7.736 D1: an UNARMED goal reports armed===false (the warning add-job renders)',
      unarmedVerdict && unarmedVerdict.edge_fastpath && unarmedVerdict.edge_fastpath.armed === false,
      `edge_fastpath=${JSON.stringify(unarmedVerdict && unarmedVerdict.edge_fastpath)}`);
    check('7.736 D1 (control): an ARMED goal reports armed===true — the door reads the package, not the action',
      armedVerdict && armedVerdict.edge_fastpath && armedVerdict.edge_fastpath.armed === true,
      `edge_fastpath=${JSON.stringify(armedVerdict && armedVerdict.edge_fastpath)}`);
  }
  const plainVerdict = (await gw.handleRequest({
    credential: AGENT_TOKEN, body: addJob('test-sleep', true), source: '127.0.0.1',
  })).body.result;
  check('7.736 D1 (control): a NON-start-workflow dry-run carries NO edge_fastpath key at all — '
    + 'absent is not null, and the action gate is what makes that observable',
    plainVerdict && plainVerdict.valid === true && !('edge_fastpath' in plainVerdict),
    `result=${JSON.stringify(plainVerdict)}`);
  after = readBackQueue();
  check('7.736 D1: every one of those dry-runs wrote NOTHING ON DISK (count still +2 over seed)',
    after.length === seededCount + 2,
    `disk queue rows=${after.length} (seeded=${seededCount})`);

  // --- 7. The envelope version is UNCHANGED (additive field, no envelope bump — D72/D73).
  // The invariant is that the internal-API ENVELOPE_VERSION constant stays 1 (no bump).
  // NOTE: the gateway's success response body is { ok, result } — it does NOT echo `v`
  // (pre-existing gateway behaviour, untouched by p4-1c), so `r.body.v` is legitimately
  // undefined; asserting it would test a non-existent gateway feature, not this invariant.
  check('the internal-API envelope version is UNCHANGED at 1 (additive field, no bump)',
    api.ENVELOPE_VERSION === 1,
    `api.ENVELOPE_VERSION=${api.ENVELOPE_VERSION}`);

  closeHeartStore();
}

main().then(() => {
  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`SKIPPED_COUNT: ${skipped}`);
  out(`DRYRUN_OK: ${failed.length === 0}`);
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
