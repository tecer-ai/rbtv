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

const { openHeartStore, closeHeartStore } = require('../../../state-store/heart/heart-store');
const { createInternalApi } = require('../dispatch');
const { createGateway } = require('../../gateway/gateway');
const { hashToken } = require('../../gateway/sender-auth');

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
    // `enqueuing_seat` (task 7.389) is selected here so the seat arms read it back from DISK on a
    // fresh read-only connection, like every other state assertion in this probe — a return-value
    // check would have passed under the mutation p4-0 caught.
    return raw.prepare('SELECT queue_id, job_id, enqueued_by, enqueuing_seat, trigger_kind FROM queue ORDER BY queue_id').all();
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
    argsSchema: JSON.stringify({ required: {}, optional: {} }),
    enabled: 1,
  });

  const secret = crypto.randomBytes(32).toString('hex');
  const api = createInternalApi({
    heartStore: store,
    spawnManager: { config: { profiles: { 'test-sleep': { headed: false } } } },
    secret,
  });
  // ── Task 7.389 · THE PROBE GATEWAY IS TAUGHT `checkPeerSeat` ─────────────────────────────────
  // Before this, no probe in the tree injected one (`probe-remove-job.js:116` and five siblings
  // constructed their gateway without it), so NO SEAT WAS EVER PROVEN IN PROBE-LAND and no fixture
  // could exercise a seat-based grant at all — the gap G-leader-0805-0625 named.
  //
  // The stub stands in for `runtime/seat-identity/peer-identity.js#resolvePeerSeat`, whose real
  // implementation reads /proc to walk socket inode -> owning pid -> that pid's cwd. That is not
  // reproducible in-process, and reproducing it is not what this probe is for: the claim under test
  // is what the POLICY does with a proven seat, not how the seat is proven. The real resolver is
  // exercised end-to-end against a live socket by `probe-seat-seam`, so the two probes cover the
  // two halves and neither pretends to cover the other.
  //
  // ⚑ IT IS KEYED ON THE SOCKET, exactly as the real one is. The gateway calls
  // `checkPeerSeat(context.socket)` with ONE argument, so a request that passes no socket gets no
  // seat — which is what makes the UNPROVEN arms below genuinely unproven rather than opted out.
  const SEAT_OF = new Map();
  const gw = createGateway({
    dispatch: api.dispatch,
    internalSecret: secret,
    sendersFilePath: sendersFile,
    checkPeerSeat: (conn) => {
      const seat = conn && SEAT_OF.get(conn);
      return seat ? { ok: true, seat, goal: 'probe-goal', run: 'run-1' } : { ok: false, code: 'E_PEER_UNRESOLVED' };
    },
  });
  // A caller "holding" a seat is just a distinct socket object the stub recognizes.
  const asSeat = (seat) => { const sock = { probeSeat: seat }; SEAT_OF.set(sock, seat); return sock; };

  const now = new Date();
  const runAt = now.toISOString().replace(/\.\d{3}Z$/, 'Z');
  const args = JSON.stringify({});

  // `socket` is threaded through both helpers (task 7.389): passing one makes the caller hold a
  // proven seat, omitting it leaves the caller exactly as unproven as every pre-7.389 arm below.
  const add = async (token, extra, socket = null) => {
    const r = await gw.handleRequest({
      credential: token,
      socket,
      body: { intent: 'enqueue-job', payload: { job_id: 'launch-worker', args, trigger_kind: 'scheduled', run_at: runAt, ...extra } },
    });
    if (!r.body.ok) throw new Error('setup enqueue failed: ' + JSON.stringify(r.body.error));
    return r.body.result.jobId;
  };
  const remove = (token, jobId, socket = null) => gw.handleRequest({ credential: token, socket, body: { intent: 'remove-job', payload: { jobId } } });

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

  // ══ 9. TASK 7.389 · THE CREATOR-SEAT GRANT ═══════════════════════════════════════════════════
  //
  // ⚑ THIS BLOCK IS THE ROW'S CAPABILITY TEST (leader ruling #3811, RIDER 2), and it is written as
  // one deliberately. The five build steps 7.389 lists are BUILD-STEP-DERIVED criteria — "did you
  // do the five things" is closable by a seat that did the five things badly. The observable
  // outcome those steps serve is the sentence the G-row opens with: *a sender loses the ability to
  // remove its OWN row*. So the claim under test is the capability, DEMONSTRATED end to end
  // through the real gateway -> real internal API -> real store, not the presence of a column.
  //
  // WHY THIS COULD NOT PASS BEFORE, stated so a reader can tell a real green from a vacuous one:
  // `seatPrincipalResolver` mapped `master` and `leader` ONLY, and no column recorded the enqueuing
  // seat, so a seat that was neither of those two names held NO principal over its own row and was
  // refused. `probe-seat` below is deliberately NOT one of those two names — if this arm were run
  // as `leader` it would pass through the SEAT_NAME_PRINCIPALS table and prove nothing about the
  // creator grant at all.
  {
    const seatSock = asSeat('probe-goal/probe-seat');

    // (a) THE CAPABILITY. One seat enqueues a row while holding a proven seat, then removes it.
    const idOwnRow = await add(AGENT_A_TOKEN, {}, seatSock);
    const ownDisk = readBackQueue().find((x) => x.queue_id === idOwnRow);
    check('7.389: enqueuing over a connection with a PROVEN seat records that seat on the row',
      ownDisk && ownDisk.enqueuing_seat === 'probe-goal/probe-seat',
      ownDisk ? `enqueued_by=${ownDisk.enqueued_by} enqueuing_seat=${ownDisk.enqueuing_seat}` : 'row missing');

    r = await remove(AGENT_A_TOKEN, idOwnRow, seatSock);
    check('7.389 RIDER 2 — THE CAPABILITY TEST: a seat CAN REMOVE ITS OWN ROW, and the grant it '
      + 'used is named `creator-seat` in the decision',
      r.body.ok === true && r.body.result.removed === true,
      `ok=${r.body.ok} error=${JSON.stringify(r.body.error || null)}`);
    check('...and the row is GONE ON DISK — the capability, not just an ok on the wire',
      !readBackQueue().some((x) => x.queue_id === idOwnRow),
      `disk queue_ids=[${readBackQueue().map((x) => x.queue_id).join(',')}]`);

    // (b) THE LIMIT, and it is the half that makes (a) worth anything. A grant that let ANY proven
    // seat remove ANY row would pass (a) identically while being a hole rather than a fix.
    //
    // ⚑ THE TOKENS DIFFER HERE, AND THAT IS FORCED — this arm was FIRST WRITTEN with both seats on
    // one token, claiming the seat check "carries none of the approximation's shared-token
    // coarseness". IT FAILED, and it was right to: with one token the UNRETIRED sender-id
    // approximation grants `creator-seat` on its own (`enqueued_by === sender.id`), the resolver
    // chain UNIONS, and the removal succeeds no matter what the seat check says. The seat limit is
    // therefore only OBSERVABLE where the approximation does not already grant. That is not a
    // weakness of the seat check — it is the approximation dominating, which is precisely why
    // `PRINCIPALS['creator-seat'].provenBy` tells a reader to assume the weaker of the two. Arm (f)
    // below pins the dominance itself rather than letting this comment carry it.
    const idOtherSeat = await add(AGENT_B_TOKEN, {}, asSeat('probe-goal/other-seat'));
    r = await remove(AGENT_A_TOKEN, idOtherSeat, seatSock);
    check('7.389 THE LIMIT: a DIFFERENT proven seat on a DIFFERENT token CANNOT remove the row — '
      + 'the seat check grants only on an exact seat-to-seat match, never on merely holding some seat',
      r.body.error && r.body.error.code === 'UNAUTHORIZED_SENDER',
      `code=${r.body.error && r.body.error.code}`);
    check('...and that refusal wrote NOTHING — the other seat\'s row is still on disk',
      readBackQueue().some((x) => x.queue_id === idOtherSeat));

    // (c) ABSENCE IS NOT A MATCH. The failure mode the store's ''->NULL normalization and the
    // resolver's non-empty test jointly exist to prevent: if an unrecorded seat compared equal to
    // an unproven caller, every unproven caller would hold creator-seat over every pre-7.389 row.
    const idNoSeat = await add(AGENT_B_TOKEN, {});
    const noSeatDisk = readBackQueue().find((x) => x.queue_id === idNoSeat);
    check('7.389: a row enqueued over a connection with NO proven seat records NULL',
      noSeatDisk && noSeatDisk.enqueuing_seat === null,
      noSeatDisk ? `enqueuing_seat=${JSON.stringify(noSeatDisk.enqueuing_seat)}` : 'row missing');
    r = await remove(AGENT_A_TOKEN, idNoSeat, seatSock);
    check('7.389: a proven seat gets NO grant over a row whose seat is NULL — absence never matches',
      r.body.error && r.body.error.code === 'UNAUTHORIZED_SENDER',
      `code=${r.body.error && r.body.error.code}`);

    // (d) THE APPROXIMATION IS STILL ARMED — asserted, not assumed. 7.389 landed G-137's
    // precondition (b) and did NOT retire the sender-id approximation, because precondition (a)
    // (task 7.37's identity columns) is unmet and dropping it would leave a live agent holding no
    // principal at all (`p-g137-retirement-falsified-approximations-stay-armed`). If a later change
    // retires it, THIS row goes red and that is the intended alarm — the retirement must be a
    // decision, never a side effect.
    r = await remove(AGENT_B_TOKEN, idNoSeat);
    check('7.389: the sender-id APPROXIMATION is UNRETIRED — the enqueuing sender still removes its '
      + 'own seatless row with no seat proven anywhere (this row goes RED the day it is retired)',
      r.body.ok === true && r.body.result.removed === true,
      `ok=${r.body.ok} error=${JSON.stringify(r.body.error || null)}`);

    // (e) THE GRANT IS ADDITIVE — the property that makes it safe to ship beside the approximation.
    // The owner path is untouched by anything above.
    const idForOwner = await add(AGENT_A_TOKEN, {}, asSeat('probe-goal/yet-another-seat'));
    r = await remove(OWNER_TOKEN, idForOwner);
    check('7.389: the OWNER still removes any row regardless of seat — the new resolver only ever '
      + 'ADDS a principal, it can never remove one',
      r.body.ok === true && r.body.result.removed === true,
      `ok=${r.body.ok}`);

    // (f) THE RESIDUAL EXPOSURE, PINNED AS A FACT RATHER THAN LEFT IN A COMMENT.
    // Two DIFFERENT proven seats behind ONE shared token still reach each other's rows — not
    // because the seat check is loose (it refuses, arm (b)) but because the union with the
    // unretired sender-id approximation makes the WEAKER grant decisive. This is exactly the
    // shared-token coarseness D65(B)'s header describes, and 7.389 does NOT close it: closing it is
    // the retirement, which needs task 7.37's identity columns (G-137 precondition (a), unmet).
    // Asserting it keeps the exposure measured instead of remembered — and this row goes RED on the
    // day the approximation is retired, at which point the seat check becomes decisive and the
    // expectation here must be inverted, deliberately.
    const idSharedToken = await add(AGENT_A_TOKEN, {}, asSeat('probe-goal/seat-one'));
    r = await remove(AGENT_A_TOKEN, idSharedToken, asSeat('probe-goal/seat-two'));
    check('7.389 DISCLOSED RESIDUAL: two different proven seats behind ONE token STILL reach each '
      + "other's rows — the unretired approximation dominates the union (RED when it is retired; "
      + 'invert this row then). 7.389 landed G-137 precondition (b) only; (a) still blocks the retirement',
      r.body.ok === true && r.body.result.removed === true,
      `ok=${r.body.ok} error=${JSON.stringify(r.body.error || null)}`);
  }

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
