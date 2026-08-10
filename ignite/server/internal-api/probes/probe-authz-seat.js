'use strict';

// Task 7.389 — the `creator-seat` grant, asked of THE POLICY MODULE ITSELF.
//
// ⚠ WHY THIS PROBE EXISTS AND WHY IT IS NOT A DUPLICATE OF `probe-remove-job`.
// `authz.js` states its own shape in its header: *"This is a POLICY MODULE, not scattered `if`s at
// the call site: every authorization question in the internal API is asked here and nowhere else."*
// There are FOUR such questions — `canRemoveQueueRow`, `canKillSession`, `canSnoozeWarning`,
// `canRegisterJob` — and until this file there was NO probe over the module at all. Every one of
// them was covered, if at all, only through whichever wire path happened to reach it.
//
// That left `canKillSession` covered by exactly one probe (`cli/probes/probe-cli-kill.js`) which
// boots a REAL daemon in a subprocess. A real daemon injects the REAL `resolvePeerSeat`, which
// walks /proc from a socket inode to the calling pid's cwd and matches it against a run's
// `sessions.csv` — so in probe-land it resolves NOTHING, no seat is ever proven there, and the seat
// half of the kill decision is unreachable from that probe by construction. Re-plumbing a real
// daemon to fake a proven seat would mean teaching `server/index.js` an injection seam that exists
// only for tests; asking the policy module directly is the same claim without that cost, and it is
// where the decision actually lives.
//
// ⚑ WHAT THIS PROBE DOES NOT CLAIM. It does not prove the seat is proven correctly (that is
// `probe-seat-seam`, over a real socket), nor that the wire path carries a decision to a caller
// (that is `probe-remove-job`, end to end through the real gateway). It proves the POLICY: given a
// sender and a subject row, which principals are held and is the action allowed.
//
// ⚠ MUTATION-BACKED READING: every refusal below is paired with the nearest-neighbour ACCEPTANCE in
// the same run, so an implementation that refused everything — which satisfies every refusal
// assertion on its own — turns this suite RED instead of reading as a clean sweep.

const fs = require('node:fs');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-authz-seat.out');
fs.writeFileSync(outPath, '');

const { createAuthzPolicy, PRINCIPALS } = require('../authz');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// The senders. `seat` is what the ingress attaches ONLY when it PROVED one
// (gateway/sender-auth.js `attachProvenSeat`) — never a caller's claim.
const AGENT_NO_SEAT = { id: 'sender-alpha', kind: 'agent' };
const AGENT_SEAT_A = { id: 'sender-alpha', kind: 'agent', seat: 'probe-goal/seat-a' };
const AGENT_SEAT_B = { id: 'sender-bravo', kind: 'agent', seat: 'probe-goal/seat-b' };
const OWNER = { id: 'the-owner', kind: 'owner' };

// The subject rows. A queue row and a jobs_log row carry the SAME two columns for this purpose,
// which is the point of denormalizing the seat at fire.
const ROW_SEAT_A = { queue_id: 1, enqueued_by: 'sender-alpha', enqueued_seat: 'probe-goal/seat-a' };
const ROW_SEAT_B = { queue_id: 2, enqueued_by: 'sender-bravo', enqueued_seat: 'probe-goal/seat-b' };
const ROW_NO_SEAT = { queue_id: 3, enqueued_by: 'sender-charlie', enqueued_seat: null };
const ROW_EMPTY_SEAT = { queue_id: 4, enqueued_by: 'sender-charlie', enqueued_seat: '' };
const EXEC_SEAT_A = { exec_id: 10, enqueued_by: 'sender-delta', enqueued_seat: 'probe-goal/seat-a' };
const EXEC_NO_SEAT = { exec_id: 11, enqueued_by: 'sender-delta', enqueued_seat: null };

try {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const policy = createAuthzPolicy();

  // ── LEG 1 · THE PRINCIPAL IS HELD, AND ON THE SEAT — not on the sender-id ────────────────────
  // `AGENT_SEAT_A` vs `ROW_SEAT_A` matches on BOTH the seat and the sender-id, which would not
  // discriminate. `EXEC_SEAT_A` is enqueued_by a DIFFERENT sender (`sender-delta`), so the ONLY
  // thing that can grant there is the seat — this is the discriminating case.
  let held = policy.principalsOf(AGENT_SEAT_A, EXEC_SEAT_A);
  check('the seat ALONE grants creator-seat — the row was enqueued_by a DIFFERENT sender-id, so the '
    + 'approximation cannot be what granted it',
    held.includes('creator-seat'), `principals=[${held.join(',')}]`);

  held = policy.principalsOf(AGENT_SEAT_B, EXEC_SEAT_A);
  check('a DIFFERENT proven seat holds NOTHING over that row — the grant is an exact seat match, '
    + 'never "holds some seat"',
    !held.includes('creator-seat'), `principals=[${held.join(',')}]`);

  // ── LEG 2 · ABSENCE NEVER MATCHES ABSENCE ────────────────────────────────────────────────────
  // THE failure this column could most easily have introduced: if an unrecorded seat compared equal
  // to an unproven caller, EVERY unproven caller would hold creator-seat over EVERY pre-7.389 row.
  // Both shapes of absence are checked because the store normalizes one to the other, and a probe
  // that only checked the normalized shape would pass with the normalization removed.
  held = policy.principalsOf(AGENT_NO_SEAT, ROW_NO_SEAT);
  check('an UNPROVEN caller holds NO creator-seat over a row with a NULL seat (absence != absence)',
    !held.includes('creator-seat'), `principals=[${held.join(',')}]`);

  held = policy.principalsOf(AGENT_SEAT_A, ROW_NO_SEAT);
  check('a PROVEN seat holds no creator-seat over a NULL-seat row either — a null grants nobody',
    !held.includes('creator-seat'), `principals=[${held.join(',')}]`);

  held = policy.principalsOf({ id: 'x', kind: 'agent', seat: '' }, ROW_EMPTY_SEAT);
  check('an EMPTY-STRING seat on BOTH sides grants nothing — the read-side non-empty test holds '
    + 'even if a row ever reached the column unnormalized',
    !held.includes('creator-seat'), `principals=[${held.join(',')}]`);

  // ── LEG 3 · canKillSession — THE DECISION WITH NO OTHER SEAT COVERAGE ────────────────────────
  // `canKillSession` is handed the jobs_log row, which is why the seat is DENORMALIZED at fire
  // rather than joined back through a queue row that a one-shot fire has already deleted.
  let d = policy.canKillSession({ sender: AGENT_SEAT_A, row: EXEC_SEAT_A });
  check('canKillSession: the creator SEAT may kill its own session — the seat reached the kill '
    + 'decision through the same one resolver chain, with no call-site change',
    d.allowed === true && d.principals.includes('creator-seat'),
    `allowed=${d.allowed} principals=[${d.principals.join(',')}] reason=${d.reason}`);

  d = policy.canKillSession({ sender: AGENT_SEAT_B, row: EXEC_SEAT_A });
  check('canKillSession: a DIFFERENT seat on a different sender-id is REFUSED',
    d.allowed === false, `allowed=${d.allowed} principals=[${d.principals.join(',')}]`);

  d = policy.canKillSession({ sender: AGENT_SEAT_A, row: EXEC_NO_SEAT });
  check('canKillSession: a proven seat is REFUSED over a seatless session row',
    d.allowed === false, `allowed=${d.allowed} principals=[${d.principals.join(',')}]`);

  d = policy.canKillSession({ sender: OWNER, row: EXEC_SEAT_A });
  check('canKillSession: the OWNER is unaffected — the new grant only ever ADDS a principal',
    d.allowed === true && d.principals.includes('owner'),
    `allowed=${d.allowed} principals=[${d.principals.join(',')}]`);

  // ── LEG 4 · canRemoveQueueRow — the same one chain answers the queue-row question ────────────
  d = policy.canRemoveQueueRow({ sender: AGENT_SEAT_A, row: ROW_SEAT_B });
  check('canRemoveQueueRow: seat-a is refused seat-b\'s row (different seat AND different sender-id)',
    d.allowed === false, `allowed=${d.allowed} principals=[${d.principals.join(',')}]`);

  d = policy.canRemoveQueueRow({ sender: AGENT_SEAT_B, row: ROW_SEAT_B });
  check('canRemoveQueueRow: seat-b removes its OWN row — the capability the G-row says was lost',
    d.allowed === true && d.principals.includes('creator-seat'),
    `allowed=${d.allowed} principals=[${d.principals.join(',')}]`);

  // ── LEG 5 · THE APPROXIMATION IS UNRETIRED, AND THE UNION MAKES IT DECISIVE ──────────────────
  // 7.389 landed G-137's precondition (b) ONLY. Precondition (a) — task 7.37's identity columns —
  // is unmet, so retiring the sender-id approximation would leave a live agent holding no principal
  // at all (`p-g137-retirement-falsified-approximations-stay-armed`). Pinned as an assertion so the
  // retirement can never happen as a side effect: BOTH rows below go red on the day it lands, and
  // inverting them is then part of that change.
  held = policy.principalsOf(AGENT_NO_SEAT, { enqueued_by: 'sender-alpha', enqueued_seat: null });
  check('UNRETIRED: the sender-id approximation still grants creator-seat with no seat anywhere '
    + '(RED the day it is retired — invert this row then)',
    held.includes('creator-seat'), `principals=[${held.join(',')}]`);

  d = policy.canRemoveQueueRow({
    sender: AGENT_SEAT_A,
    row: { queue_id: 9, enqueued_by: 'sender-alpha', enqueued_seat: 'probe-goal/seat-b' },
  });
  check('THE UNION MAKES THE WEAKER GRANT DECISIVE: seat-a is refused by the SEAT check yet still '
    + 'ALLOWED, because the approximation matched the shared sender-id. This is D65(B)\'s '
    + 'shared-token coarseness, and 7.389 does not close it — the retirement does',
    d.allowed === true && d.principals.includes('creator-seat'),
    `allowed=${d.allowed} principals=[${d.principals.join(',')}] reason=${d.reason}`);

  // ── LEG 6 · THE TWO SEAT-NAME PRINCIPALS ARE UNCHANGED BY THE NEW GRANT ──────────────────────
  held = policy.principalsOf({ id: 'x', kind: 'agent', seat: 'leader' }, ROW_SEAT_B);
  check('a proven `leader` still holds `leader` — the added creator branch did not disturb the '
    + 'SEAT_NAME_PRINCIPALS table the same resolver already served',
    held.includes('leader') && !held.includes('creator-seat'), `principals=[${held.join(',')}]`);

  // ── LEG 7 · SNOOZE STAYS OWNER-ONLY, ASKED OF THE MODULE ─────────────────────────────────────
  // `canSnoozeWarning` passes `subject = null` so the creator grant is unreachable BY CONSTRUCTION.
  // That construction now guards a second resolver, so it is asserted rather than trusted.
  d = policy.canSnoozeWarning({ sender: AGENT_SEAT_A });
  check('canSnoozeWarning: a proven creator seat is STILL refused — owner-only is unmoved by 7.389',
    d.allowed === false, `allowed=${d.allowed} principals=[${d.principals.join(',')}]`);
  d = policy.canSnoozeWarning({ sender: OWNER });
  check('canSnoozeWarning: the owner is still allowed — the positive control for the row above',
    d.allowed === true, `allowed=${d.allowed}`);

  // ── LEG 8 · THE PRINCIPAL'S SELF-DESCRIPTION STAYS HONEST ────────────────────────────────────
  // `provenBy` is what a reader consults to know how much a grant is worth. While the approximation
  // stands, it must NOT read as a pure seat check — LEG 5 is the measurement behind that sentence.
  check('PRINCIPALS[creator-seat].provenBy still discloses the UNRETIRED approximation rather than '
    + 'describing itself as seat-based',
    /APPROXIMATION/.test(PRINCIPALS['creator-seat'].provenBy),
    PRINCIPALS['creator-seat'].provenBy);

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`AUTHZ_SEAT_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
} catch (err) {
  out('ERROR:', err.message, err.stack);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
}
