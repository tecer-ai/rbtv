'use strict';

// probe-snooze — the `snooze` intent added by owner ruling D71, exercised end-to-end
// through the REAL gateway -> REAL internal API -> REAL heart store:
//
//   D71 — a FIFTH intent, `snooze`, is ADDED ADDITIVELY to the internal-API surface
//         (envelope version UNCHANGED) so p4-2's CLI snooze subcommand has a gateway
//         path to wrap. Payload `{ kind, subject, minutes }` -> the already-shipped
//         store API `heartStore.snoozeWarning(...)` (p3-3).
//
//   Authz OWNER-ONLY (D45/D71): the MASTER may snooze and v1's owner IS the master;
//         a warning is SYSTEM-raised, so — unlike remove-job — there is NO creator
//         seat to approximate. A non-owner sender -> UNAUTHORIZED_SENDER. The guard
//         is proven MUTATION-BACKED: after the denial the warning is UNCHANGED ON
//         DISK (a policy that reads strict but is not is the more dangerous failure).
//
//   Re-validation (D45; ADX-14): NO standing warning for (kind, subject) is a CLEAN
//         NO-OP success — not an error, not a phantom row; bad `minutes` (zero /
//         negative / non-integer) is VALIDATION_FAILED at the CORE (defense-in-depth:
//         the gateway ALSO shape-refuses it). minutes->ticks stays the STORE's
//         business (D44) — the intent forwards `minutes` only. Snooze NEVER clears.
//
// ⚑ EVERY state assertion reads back from DISK on a fresh read-only connection
// (p4-0's transferable finding: under mutation, return-value checks still PASSED —
// only a raw disk read-back caught the defect. A count is not a proof; identity on
// disk is).
//
// Isolation: a THROWAWAY db under os.tmpdir(). This probe WRITES — it must NEVER be
// pointed at the live store (.rbtv/heart/), which a live daemon is ticking against.
//
// Capture truncated at module load, BEFORE any work (D51 evidence-husk hazard). The
// process exit code is the truth; the footer is a hint.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-snooze.out');
fs.writeFileSync(outPath, '');

const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { TICKS_PER_MINUTE } = require('../../heart/warnings');
const { createInternalApi } = require('../dispatch');
const { createGateway } = require('../../../gateway/gateway');
const { hashToken } = require('../../../gateway/sender-auth');

const tmpDb = path.join(os.tmpdir(), `ignite-probe-snooze-${Date.now()}-${process.pid}.db`);
const sendersFile = path.join(os.tmpdir(), `ignite-probe-snooze-senders-${Date.now()}-${process.pid}.yaml`);

const OWNER_TOKEN = crypto.randomBytes(16).toString('hex');
const AGENT_TOKEN = crypto.randomBytes(16).toString('hex');

// The reference tick and the warning under test.
const REF_TICK = 10;
const KIND = 'seat-blocked-budget-exhausted';
const SUBJECT = 'client-x/leader';
const MINUTES = 5;
const EXPECT_UNTIL = REF_TICK + MINUTES * TICKS_PER_MINUTE; // 10 + 5*6 = 40

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
function readBackWarning(kind, subject) {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare(
      'SELECT warning_id, kind, subject, raised_at_tick, snoozed_until_tick, cleared_at_tick FROM warnings WHERE kind = ? AND subject = ?'
    ).get(kind, subject) || null;
  } finally {
    raw.close();
  }
}
function readBackWarningCount() {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT COUNT(*) AS n FROM warnings').get().n;
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
    '  - sender-id: probe-agent',
    '    kind: agent',
    `    token-hash: ${hashToken(AGENT_TOKEN)}`,
    '    enabled: true',
    '',
  ].join('\n'), { mode: 0o600 });
  fs.chmodSync(sendersFile, 0o600);

  const store = openHeartStore({ dbPath: tmpDb, profiles: { 'test-sleep': { headed: false } } });

  // Seed a reference tick (so snoozeWarning's "now" is a real tick, not 0) and ONE
  // standing warning. The warning is SYSTEM-raised via the store's own API — there is
  // no sender in the loop, which is exactly why snooze authz is owner-only.
  store.recordTick({ tick: REF_TICK, ts: new Date() });
  store.raiseWarning({ kind: KIND, subject: SUBJECT, raisedAtTick: 3 });

  const secret = crypto.randomBytes(32).toString('hex');
  const api = createInternalApi({
    heartStore: store,
    spawnManager: { config: { profiles: { 'test-sleep': { headed: false } } } },
    secret,
  });
  const gw = createGateway({ dispatch: api.dispatch, internalSecret: secret, sendersFilePath: sendersFile });

  const snooze = (token, payload) => gw.handleRequest({ credential: token, body: { intent: 'snooze', payload } });
  // A direct-dispatch envelope (bypasses the gateway) to prove the CORE's own guards,
  // exactly as probe-revalidate crafts envelopes for the boundary tests.
  const ownerEnv = (payload) => ({
    v: 1, id: crypto.randomUUID(), ts: new Date().toISOString(), auth: secret,
    sender: { id: 'probe-owner', kind: 'owner', via: 'cli' }, intent: 'snooze', payload,
  });

  // --- setup: the warning stands ON DISK, not yet snoozed.
  let w = readBackWarning(KIND, SUBJECT);
  check('setup: the warning is standing ON DISK, snoozed_until_tick NULL',
    w && w.cleared_at_tick === null && w.snoozed_until_tick === null,
    `disk warning=${JSON.stringify(w)}`);

  // --- 1. A NON-OWNER sender is REFUSED (owner-only, D45/D71) — and the denial writes NOTHING.
  let r = await snooze(AGENT_TOKEN, { kind: KIND, subject: SUBJECT, minutes: MINUTES });
  check('a NON-OWNER (kind: agent) snooze is refused UNAUTHORIZED_SENDER',
    r.body.error && r.body.error.code === 'UNAUTHORIZED_SENDER',
    `code=${r.body.error && r.body.error.code}`);
  check('the refused snooze maps to HTTP 403', r.status === 403, `status=${r.status}`);
  w = readBackWarning(KIND, SUBJECT);
  check('the denial wrote NOTHING — snoozed_until_tick is STILL NULL ON DISK (mutation-backed guard)',
    w && w.snoozed_until_tick === null,
    `disk snoozed_until_tick=${w && w.snoozed_until_tick}`);

  // --- 2. The OWNER snoozes the STANDING warning -> success; snoozed_until_tick ADVANCES ON DISK.
  r = await snooze(OWNER_TOKEN, { kind: KIND, subject: SUBJECT, minutes: MINUTES });
  check('the OWNER snoozes the standing warning -> ok, snoozed: true',
    r.body.ok === true && r.body.result.snoozed === true,
    `ok=${r.body.ok} result=${JSON.stringify(r.body.result)}`);
  check('the result reports until WHICH tick (loud feedback, D21(3))',
    r.body.result.snoozed_until_tick === EXPECT_UNTIL,
    `snoozed_until_tick=${r.body.result.snoozed_until_tick} (expected ${EXPECT_UNTIL})`);
  w = readBackWarning(KIND, SUBJECT);
  check('snoozed_until_tick ACTUALLY ADVANCED ON DISK (read back, not a return value)',
    w && w.snoozed_until_tick === EXPECT_UNTIL,
    `disk snoozed_until_tick=${w && w.snoozed_until_tick} (expected ${EXPECT_UNTIL})`);
  check('snooze NEVER clears (D45): cleared_at_tick is STILL NULL ON DISK',
    w && w.cleared_at_tick === null,
    `disk cleared_at_tick=${w && w.cleared_at_tick}`);

  // --- 3. The intent is REGISTERED — routed to a typed result, never UNKNOWN_INTENT.
  check('the snooze intent is REGISTERED (a typed snooze result, never UNKNOWN_INTENT)',
    r.body.ok === true && Object.prototype.hasOwnProperty.call(r.body.result, 'snoozed'),
    `result keys=${JSON.stringify(Object.keys(r.body.result))}`);

  // --- 4. A numeric-STRING minutes is coerced at the gateway (approved sub-decision #2).
  r = await snooze(OWNER_TOKEN, { kind: KIND, subject: SUBJECT, minutes: '5' });
  check('a numeric-string minutes "5" is coerced at the gateway and accepted',
    r.body.ok === true && r.body.result.snoozed === true && r.body.result.snoozed_until_tick === EXPECT_UNTIL,
    `ok=${r.body.ok} result=${JSON.stringify(r.body.result)}`);

  // --- 5. NO standing warning for (kind, subject) -> a CLEAN NO-OP success, no phantom row.
  const beforeCount = readBackWarningCount();
  r = await snooze(OWNER_TOKEN, { kind: 'no-such-kind', subject: 'no-such-subject', minutes: MINUTES });
  check('snooze with NO standing warning -> clean NO-OP SUCCESS (ok, snoozed: false), never an error',
    r.body.ok === true && r.body.result.snoozed === false,
    `ok=${r.body.ok} result=${JSON.stringify(r.body.result)}`);
  const afterCount = readBackWarningCount();
  check('the no-op wrote NO PHANTOM ROW ON DISK (warnings count unchanged; no row for the absent subject)',
    afterCount === beforeCount && readBackWarning('no-such-kind', 'no-such-subject') === null,
    `count before=${beforeCount} after=${afterCount}`);

  // --- 6. BAD minutes at the CORE -> VALIDATION_FAILED (defense-in-depth, direct dispatch).
  // The gateway would shape-refuse these; dispatching straight at the core proves the
  // core RE-VALIDATES minutes independently of gateway origin.
  for (const badMin of [0, -5, 1.5]) {
    const d = await api.dispatch(ownerEnv({ kind: KIND, subject: SUBJECT, minutes: badMin }));
    check(`bad minutes (${badMin}) is refused VALIDATION_FAILED at the CORE, naming the check`,
      d.error && d.error.code === 'VALIDATION_FAILED' && d.error.details && d.error.details.check === 'E_BAD_ARGS',
      `code=${d.error && d.error.code} details=${JSON.stringify(d.error && d.error.details)}`);
  }
  w = readBackWarning(KIND, SUBJECT);
  check('the bad-minutes refusals wrote NOTHING — snoozed_until_tick is UNCHANGED ON DISK',
    w && w.snoozed_until_tick === EXPECT_UNTIL,
    `disk snoozed_until_tick=${w && w.snoozed_until_tick} (expected ${EXPECT_UNTIL})`);

  // --- 7. Defense-in-depth: the GATEWAY also shape-refuses bad minutes (SHAPE_INVALID).
  r = await snooze(OWNER_TOKEN, { kind: KIND, subject: SUBJECT, minutes: 0 });
  check('the GATEWAY also shape-refuses bad minutes (SHAPE_INVALID, exit-4 class) — both layers guard',
    r.body.error && r.body.error.code === 'SHAPE_INVALID' && r.status === 400,
    `code=${r.body.error && r.body.error.code} status=${r.status}`);

  closeHeartStore();
}

main().then(() => {
  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`SKIPPED_COUNT: ${skipped}`);
  out(`SNOOZE_OK: ${failed.length === 0}`);
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
