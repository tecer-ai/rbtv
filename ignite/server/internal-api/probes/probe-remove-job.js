'use strict';

// probe-remove-job — the two rulings this round lands, exercised end-to-end through
// the REAL gateway -> REAL internal API -> REAL heart store:
//
//   D68 — the internal-API `remove-job` RESULT is WIDENED, ADDITIVELY, to
//         `{ removed: true, trigger_kind, repeat_rule, interval_seconds }`.
//         `removed: true` REMAINS — the widening must not break an existing reader.
//         The recurrence fields are what let p4-2's CLI tell the sender that removing
//         a REPEATING trigger cancelled the WHOLE recurring schedule (D21(3) loud
//         feedback, BINDING acceptance — graded at p4-checkpoint).
//
//   D65(B) — the cancel-authorization model, built KNOWINGLY WEAKER than the policy
//         it records: v1 enforces `owner` and the creator APPROXIMATION
//         (`enqueued_by == authenticated sender-id`) and nothing else. The probe
//         asserts the approximation's LIMIT as explicitly as its function — a policy
//         that reads strict but is not is the more dangerous failure.
//
// ⚑ EVERY state assertion reads back from DISK on a fresh read-only connection
// (p4-0's transferable finding: under mutation, return-value checks still PASSED —
// only a raw disk read-back caught the defect).
//
// Isolation: a THROWAWAY db under os.tmpdir(). This probe DELETES rows — it must
// NEVER be pointed at the live store (.rbtv/heart/).
//
// Capture truncated at module load, BEFORE any work (D51). The process exit code is
// the truth; the footer is a hint.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-remove-job.out');
fs.writeFileSync(outPath, '');

const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createInternalApi } = require('../dispatch');
const { createGateway } = require('../../../gateway/gateway');
const { hashToken } = require('../../../gateway/sender-auth');

const tmpDb = path.join(os.tmpdir(), `ignite-probe-remove-${Date.now()}-${process.pid}.db`);
const sendersFile = path.join(os.tmpdir(), `ignite-probe-remove-senders-${Date.now()}-${process.pid}.yaml`);

const OWNER_TOKEN = crypto.randomBytes(16).toString('hex');
const AGENT_A_TOKEN = crypto.randomBytes(16).toString('hex');
const AGENT_B_TOKEN = crypto.randomBytes(16).toString('hex');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
const skipped = 0;
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

function readBackQueue() {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT queue_id, job_id, enqueued_by, trigger_kind FROM queue ORDER BY queue_id').all();
  } finally {
    raw.close();
  }
}

function readBackExecs() {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT exec_id, queue_id, status FROM jobs_log ORDER BY exec_id').all();
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
    '  - sender-id: probe-agent-a',
    '    kind: agent',
    `    token-hash: ${hashToken(AGENT_A_TOKEN)}`,
    '    enabled: true',
    '  - sender-id: probe-agent-b',
    '    kind: agent',
    `    token-hash: ${hashToken(AGENT_B_TOKEN)}`,
    '    enabled: true',
    '',
  ].join('\n'), { mode: 0o600 });
  fs.chmodSync(sendersFile, 0o600);

  const store = openHeartStore({ dbPath: tmpDb, profiles: { 'test-sleep': { headed: false } } });
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

  const now = new Date();
  const runAt = now.toISOString().replace(/\.\d{3}Z$/, 'Z');
  const args = JSON.stringify({ profile: 'test-sleep' });

  const add = async (token, extra) => {
    const r = await gw.handleRequest({
      credential: token,
      body: { intent: 'enqueue-job', payload: { job_id: 'launch-worker', args, trigger_kind: 'scheduled', run_at: runAt, ...extra } },
    });
    if (!r.body.ok) throw new Error('setup enqueue failed: ' + JSON.stringify(r.body.error));
    return r.body.result.jobId;
  };
  const remove = (token, jobId) => gw.handleRequest({ credential: token, body: { intent: 'remove-job', payload: { jobId } } });

  // A: a ONE-SHOT row, enqueued by agent-a.
  const idOneShot = await add(AGENT_A_TOKEN, {});
  // B: a REPEATING (periodic) trigger enqueued by agent-a — the D68 subject.
  const idPeriodic = await add(AGENT_A_TOKEN, { trigger_kind: 'periodic', interval_seconds: 60 });
  // C: a REPEATING (cron) trigger enqueued by agent-a.
  const idCron = await add(AGENT_A_TOKEN, { repeat_rule: '*/5 * * * *' });
  // D: a row enqueued by the OWNER — used to prove agent-a cannot touch it.
  const idOwners = await add(OWNER_TOKEN, {});

  // Fire the periodic row once: its row is UPDATED (not deleted) and an execution is
  // recorded — this is what makes it a LIVE recurring schedule with audit history.
  const execB = store.fireQueueRow({ queueId: idPeriodic, now, tick: 1 });
  check('setup: the repeating row SURVIVED its fire and recorded an execution',
    execB !== null && store.getQueueRow(idPeriodic) !== null,
    `exec_id=${execB && execB.exec_id}`);
  check('setup: 4 rows are on disk', readBackQueue().length === 4, `disk queue rows=${readBackQueue().length}`);

  // --- 1. D68: the ONE-SHOT removal result, widened but backward-compatible.
  let r = await remove(AGENT_A_TOKEN, idOneShot);
  check('remove-job succeeds for the sender that enqueued the row', r.body.ok === true, `ok=${r.body.ok}`);
  check('D68: `removed: true` REMAINS (the widening is ADDITIVE — existing readers keep working)',
    r.body.result.removed === true, `removed=${r.body.result.removed}`);
  check('D68: a ONE-SHOT reports no recurrence (trigger_kind=scheduled, repeat_rule null, interval null)',
    r.body.result.trigger_kind === 'scheduled' && r.body.result.repeat_rule === null && r.body.result.interval_seconds === null,
    JSON.stringify(r.body.result));
  check('the one-shot row is GONE ON DISK (identity, not a count)',
    !readBackQueue().some((x) => x.queue_id === idOneShot),
    `disk queue_ids=[${readBackQueue().map((x) => x.queue_id).join(',')}]`);

  // --- 2. D68 THE POINT: removing a PERIODIC trigger reports the cancelled recurrence.
  // Without these fields the sender is told "removed: true" and never learns that a
  // schedule firing every 60s is gone — the destructive act the warning exists for.
  r = await remove(AGENT_A_TOKEN, idPeriodic);
  check('D68: removing a PERIODIC trigger surfaces trigger_kind + interval_seconds ACROSS the wire',
    r.body.result.removed === true && r.body.result.trigger_kind === 'periodic' && r.body.result.interval_seconds === 60,
    JSON.stringify(r.body.result));
  check('the periodic row is GONE ON DISK — the WHOLE recurring schedule is cancelled',
    !readBackQueue().some((x) => x.queue_id === idPeriodic),
    `disk queue_ids=[${readBackQueue().map((x) => x.queue_id).join(',')}]`);

  // The audit SURVIVES its queue row's deletion: removal cancels FUTURE fires only and
  // never reaches a recorded or running execution (heart-store-spec.md:168).
  check("the fired execution's audit row SURVIVES its queue row's removal",
    readBackExecs().some((e) => e.exec_id === execB.exec_id && e.queue_id === idPeriodic),
    `jobs_log exec_ids=[${readBackExecs().map((e) => e.exec_id).join(',')}]`);

  // --- 3. D68: a CRON repeating trigger surfaces its repeat_rule.
  r = await remove(AGENT_A_TOKEN, idCron);
  check('D68: removing a CRON repeating trigger surfaces its repeat_rule ACROSS the wire',
    r.body.result.removed === true && r.body.result.repeat_rule === '*/5 * * * *',
    JSON.stringify(r.body.result));

  // --- 4. D65(B): the creator APPROXIMATION refuses another sender's row.
  r = await remove(AGENT_B_TOKEN, idOwners);
  check('D65(B): agent-b CANNOT remove a row it did not enqueue -> UNAUTHORIZED_SENDER',
    r.body.error && r.body.error.code === 'UNAUTHORIZED_SENDER',
    `code=${r.body.error && r.body.error.code}`);
  check('D65(B): the refused removal maps to HTTP 403', r.status === 403, `status=${r.status}`);
  check('D65(B): the refused removal wrote NOTHING — the row is still ON DISK',
    readBackQueue().some((x) => x.queue_id === idOwners),
    `disk queue_ids=[${readBackQueue().map((x) => x.queue_id).join(',')}]`);

  // --- 5. D65(B): the OWNER may cancel anything (including another sender's row).
  const idAgentRow = await add(AGENT_A_TOKEN, {});
  r = await remove(OWNER_TOKEN, idAgentRow);
  check('D65(B): kind=owner may remove ANOTHER sender\'s row (the owner principal is enforced)',
    r.body.ok === true && r.body.result.removed === true,
    `ok=${r.body.ok}`);
  check('the owner-removed row is GONE ON DISK',
    !readBackQueue().some((x) => x.queue_id === idAgentRow),
    `disk queue_ids=[${readBackQueue().map((x) => x.queue_id).join(',')}]`);

  // --- 6. NOT_FOUND mapping: an unknown id is typed, never a silent no-op.
  // This is exactly why D66(B) minted E_QUEUE_ROW_NOT_FOUND as a code distinct from
  // E_UNKNOWN_JOB: the contract maps "no such QUEUE ROW" and "no such CATALOGUE job"
  // to DIFFERENT wire codes, so one overloaded store code could not express both.
  r = await remove(OWNER_TOKEN, 999999);
  check('an unknown queue-row id -> typed NOT_FOUND (never a silent no-op)',
    r.body.error && r.body.error.code === 'NOT_FOUND', `code=${r.body.error && r.body.error.code}`);
  check('the NOT_FOUND refusal maps to HTTP 404', r.status === 404, `status=${r.status}`);

  // The sibling wire code stays DISTINCT: an unknown CATALOGUE slug is VALIDATION_FAILED.
  const bad = await gw.handleRequest({
    credential: OWNER_TOKEN,
    body: { intent: 'enqueue-job', payload: { job_id: 'no-such-catalogue-job', args, trigger_kind: 'scheduled', run_at: runAt } },
  });
  check('an unknown CATALOGUE job stays VALIDATION_FAILED — distinct from a missing queue ROW',
    bad.body.error && bad.body.error.code === 'VALIDATION_FAILED' && bad.body.error.details.check === 'E_UNKNOWN_JOB',
    `code=${bad.body.error && bad.body.error.code} check=${bad.body.error && bad.body.error.details.check}`);

  // --- 7. D69: the wire field NAMED `jobId` carries a QUEUE-ROW handle, not a slug.
  // Proven by behaviour: the id minted by enqueue-job is the id remove-job consumes.
  const idRoundTrip = await add(AGENT_A_TOKEN, {});
  const diskRow = readBackQueue().find((x) => x.queue_id === idRoundTrip);
  check('D69: the id enqueue-job MINTS is the queue_id ON DISK (a row handle, not a catalogue slug)',
    diskRow && diskRow.queue_id === idRoundTrip && diskRow.job_id === 'launch-worker',
    `minted jobId=${idRoundTrip} -> disk queue_id=${diskRow && diskRow.queue_id}, catalogue slug=${diskRow && diskRow.job_id}`);
  r = await remove(AGENT_A_TOKEN, idRoundTrip);
  check('D69: feeding that minted id straight into remove-job removes THAT row (gateway-cli-spec test 5)',
    r.body.ok === true && !readBackQueue().some((x) => x.queue_id === idRoundTrip),
    `removed queue_id=${idRoundTrip}`);

  // --- 8. A non-integer id is VALIDATION_FAILED, distinct from a missing row.
  r = await gw.handleRequest({ credential: OWNER_TOKEN, body: { intent: 'remove-job', payload: { jobId: 'launch-worker' } } });
  check('a catalogue SLUG passed as jobId is refused (it is not a row handle)',
    r.body.error && (r.body.error.code === 'SHAPE_INVALID' || r.body.error.code === 'VALIDATION_FAILED'),
    `code=${r.body.error && r.body.error.code}`);

  closeHeartStore();
}

main().then(() => {
  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`SKIPPED_COUNT: ${skipped}`);
  out(`REMOVE_JOB_OK: ${failed.length === 0}`);
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
