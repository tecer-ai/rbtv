'use strict';

// -- THE DEATH STAMP - the ONE path from observed exit to a stamped ending [T4-R7, T1-R1, T1-R18]
//
// WHAT WAS BROKEN. Death was stamped in two places and neither of them looked at any evidence.
// `close_session_seat` (the daemon-lane closer) and `attest-exit --force-dead` (the tmux-lane one)
// each wrote the word `exited` onto a pid-less OPEN row: a fifth ending vocabulary carrying NO
// reason at all. A reason-less terminal is unclassifiable, so the recovery ladder had nothing to
// act on and every consumer downstream read a stored status as if it were liveness. Worse, the
// `done` side had the mirror hole: a seat that finished was only killed-and-reaped when its
// descriptor said `ephemeral: yes` (CODE-GROUND-TRUTH section 4), so every NON-ephemeral seat
// finished its work and left its process holding memory with nobody owed the reap.
//
// THE CURE, and it is one function. The supervisor DETECTS the exit (the registry probe, and only
// that) and STAMPS FROM EVIDENCE into a mandatory reason field. Nothing here invents a work
// outcome: a seat's own declared ending, where one exists, always stands. What this path adds is
// the ending NO SEAT CAN WITNESS ABOUT ITSELF - that its process died without declaring anything.
//
//   +---------------------------------------+--------------------------------------------------+
//   | evidence                              | stamp / act                                      |
//   +---------------------------------------+--------------------------------------------------+
//   | checkout `done` present                | confirm-and-reap the process, EVERY seat, never  |
//   |                                        | only `ephemeral: yes`. No `failed`.              |
//   | checkout `incomplete` present          | the seat-declared ending stands; reap.           |
//   | dead, no checkout, never checked in    | `failed: crash` - a strike.                      |
//   | dead, no checkout, DID check in        | `failed: crash` + exit code + transcript-tail.   |
//   | evidence is provider-shaped            | `failed: provider-error`. Whether that costs a   |
//   |                                        | strike or a reroute is spec-recovery's, not ours.|
//   +---------------------------------------+--------------------------------------------------+
//
// `exited` IS NOT REACHABLE FROM HERE, and not by convention: the ending store's own killed-word
// list refuses it at the write boundary (`state-store/vocabulary.js`), so a caller that tried
// would be refused rather than silently believed.
//
// WHAT THIS FILE DOES NOT HOLD. No ending-store handle: `store` is INJECTED, exactly as
// `awaitingReap` injects `hasEnding`, so liveness and endings stay two files that one caller wires
// together instead of two modules that import each other. No kill-trigger POLICY either - nothing
// here decides that a seat has stalled and should die (spec-recovery owns that). The only process
// this file may signal is one whose sitting has ALREADY declared its ending.

const { isAliveProcess, loadRegistry, dropRow, keyOf } = require('./registry');

// -- PROVIDER-SHAPED EVIDENCE -------------------------------------------------------------------
//
// A death whose evidence names the MODEL PROVIDER refusing or failing is not the seat crashing -
// it is the seat being denied the thing it runs on, and the two want opposite responses (a crash
// is investigated, a provider error is rerouted). The marker list is deliberately SHORT and
// literal: every entry is a string a provider SDK or gateway actually emits. A loose match here
// would misclassify ordinary crashes as infrastructure and hide real defects behind a reroute,
// which is the more expensive error - so anything unrecognised falls through to `crash`.
const PROVIDER_MARKERS = Object.freeze([
  'overloaded_error',
  'rate_limit',
  'rate limit',
  'insufficient_quota',
  'authentication_error',
  'permission_error',
  'api_error',
  'upstream_error',
  'service_unavailable',
  'provider-error',
  'http 429',
  'http 503',
]);

function providerShaped(text) {
  if (!text) return false;
  const hay = String(text).toLowerCase();
  return PROVIDER_MARKERS.some((m) => hay.includes(m));
}

// -- THE EVIDENCE POINTER - mandatory, and the store refuses an empty one -----------------------
//
// spec-state-store section 1.4 requires `reason_class=crash` to carry a pointer naming the OBSERVED
// death. The two facts a witness holds and nobody else does are the EXIT CODE it read and the PATH
// of the transcript whose tail says what the process was doing - [T1-R18] names both for the
// did-check-in row specifically, because that is the row a human will actually have to read.
function buildEvidence({ session, seat, pid, exitCode, transcriptTail, detail }) {
  const parts = [];
  if (session) parts.push(`session:${session}`);
  else if (seat) parts.push(`seat:${seat}`);
  if (pid) parts.push(`pid:${pid}`);
  parts.push(exitCode === null || exitCode === undefined ? 'exit=unknown' : `exit=${exitCode}`);
  if (transcriptTail) parts.push(`transcript-tail:${transcriptTail}`);
  if (detail) parts.push(String(detail).trim().slice(0, 400));
  return parts.join('; ');
}

// -- CONFIRM AND REAP --------------------------------------------------------------------------
//
// CONFIRM first, always. The registry probe (`kill(pid,0)` + /proc start-time) is the ONLY question
// asked - never a pane, never a stored status. A row whose process is still alive after its sitting
// declared an ending is a seat that finished its work and left its harness running; the reap is
// what frees it, and it is owed for EVERY seat now, not only the `ephemeral: yes` ones.
//
// THE START-TIME MATCH IS WHAT MAKES SIGNALLING SAFE. `isAliveProcess` compares the /proc
// start-time the row was written with, so a recycled pid reads DEAD and is never signalled. Without
// that pair this function could terminate whatever unrelated process inherited the number.
//
// `terminate` is injected for the same reason `store` is: a selftest must be able to prove the
// order of acts without killing anything, and a module that can only send a real signal cannot be
// tested at all.
function defaultTerminate(pid) {
  process.kill(pid, 'SIGTERM');
}

// A SIGTERM is a REQUEST, and a process does not stop existing on the line after it is sent. The
// first draft re-probed immediately, read the still-running process as "refused the signal" and
// left the row standing FOREVER - a permanent reap debt manufactured by the reaper itself. So the
// confirm step WAITS, bounded: short synchronous sleeps up to `REAP_CONFIRM_BUDGET_MS`, answering
// the moment the process is gone. Synchronous because every caller of this path is synchronous (the
// ticker's close arm, coord's python door), and an async reap would change six call sites to buy
// nothing - the budget is under three seconds.
const REAP_CONFIRM_BUDGET_MS = 3000;
const REAP_POLL_MS = 25;

function sleepMs(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function waitGone(pid, startTime, budgetMs = REAP_CONFIRM_BUDGET_MS) {
  const deadline = Date.now() + budgetMs;
  while (isAliveProcess(pid, startTime)) {
    if (Date.now() >= deadline) return false;
    sleepMs(REAP_POLL_MS);
  }
  return true;
}

function confirmAndReap({ goal, seat, pid, start_time: startTime }, opts = {}) {
  const registryFile = opts.registryFile;
  const terminate = opts.terminate || defaultTerminate;
  const rows = loadRegistry(registryFile);
  const key = keyOf({ goal: goal || '', seat });
  const row = rows.find((r) => keyOf(r) === key) || null;
  // The row carries the identity pair; a caller may also hold it (the spawn door does). The ROW
  // wins where both exist - it is what the reap is about.
  const targetPid = (row && row.pid) || pid || null;
  const targetStart = (row && row.start_time) || startTime || null;

  let alive = targetPid ? isAliveProcess(targetPid, targetStart) : false;
  let signalled = false;
  if (alive) {
    try {
      terminate(Number(targetPid));
      signalled = true;
    } catch {
      // ESRCH means it went away between the probe and the signal, which is the outcome we wanted.
      // Any other failure leaves the row standing: an unreaped debt is visible (`awaitingReap`),
      // and a row dropped for a process still running is a leak nobody can see.
    }
    alive = !waitGone(targetPid, targetStart);
  }
  if (alive) {
    return { reaped: false, rowDropped: false, processGone: false, signalled, reason: `pid ${targetPid} is still alive after the reap signal` };
  }
  // Write moment (iii): the row goes ONLY once the ending is stamped AND the process is confirmed
  // gone. `dropRow` answering false means there was no row - an unsupervised sitting, not an error.
  const rowDropped = row ? dropRow({ goal, seat }, registryFile) : false;
  return { reaped: true, rowDropped, processGone: true, signalled, reason: '' };
}

// -- THE ONE DEATH-STAMP ENTRY POINT ------------------------------------------------------------
//
// Every door that used to stamp independently calls THIS: `spawn.js#closeSeatSessionRow`, coord's
// `attest-exit --force-dead`, and the boot pass over `readopt().dead`. They supply only the facts
// they alone hold - which sitting, that the process is gone, the exit code, the transcript path -
// and this function decides the ending. An engine that passed a work disposition would be putting
// words in a seat's mouth from the one side that cannot witness the work.
//
// `checkedIn` DISCRIMINATES THE TWO CRASH ROWS. Both stamp `failed: crash`; the did-check-in row
// additionally REQUIRES the exit code and the transcript-tail pointer in its evidence [T1-R18],
// because a seat that reached check-in produced a transcript worth reading and a human triaging
// the strike will need it. A never-checked-in seat has no transcript to point at.
function stampDeath(evidence, deps = {}) {
  const { goal, seat } = evidence || {};
  if (!goal || !seat) throw new Error('death stamp requires goal and seat');
  const store = deps.store;
  if (!store || typeof store.getCurrentEnding !== 'function' || typeof store.stampSystem !== 'function') {
    throw new Error('death stamp requires an ending store exposing getCurrentEnding + stampSystem');
  }
  const reapOpts = { registryFile: deps.registryFile, terminate: deps.terminate };
  const current = store.getCurrentEnding({ goal, seat }) || null;
  const declared = current && current.ending;

  // ROW 1 and ROW 2 - a checkout is present, so the seat already spoke. Nothing is stamped and no
  // `failed` is invented on top of a declaration; what is owed is the reap.
  if (declared === 'done' || declared === 'incomplete') {
    const reap = confirmAndReap(evidence, reapOpts);
    return {
      act: declared === 'done' ? 'confirm-and-reap' : 'declared-ending-stands',
      stamped: false,
      ending: declared,
      reason_class: null,
      ...reap,
    };
  }
  // An ending already `failed` means this path (or another witness) has run. Re-stamping would
  // rewrite a settled ending; the reap may still be owed, so it is attempted and nothing else is.
  if (declared === 'failed') {
    const reap = confirmAndReap(evidence, reapOpts);
    return { act: 'already-stamped', stamped: false, ending: 'failed', reason_class: current.reason_class || null, ...reap };
  }

  // ROWS 3-5 - dead, and no checkout. This is the ending no seat can witness about itself.
  const detail = evidence.detail || '';
  const isProvider = providerShaped(`${detail} ${evidence.transcriptTail || ''}`);
  const reasonClass = isProvider ? 'provider-error' : 'crash';
  const checkedIn = Boolean(evidence.checkedIn);
  const pointer = evidence.evidencePointer || buildEvidence({
    session: evidence.session,
    seat,
    pid: evidence.pid,
    exitCode: evidence.exitCode,
    // A seat that never checked in has no transcript to point at; carrying the field anyway would
    // put a path in the record that nobody can open.
    transcriptTail: checkedIn ? evidence.transcriptTail : (evidence.transcriptTail || ''),
    detail,
  });
  const stamped = store.stampSystem({
    goal,
    seat,
    ending: 'failed',
    reason_class: reasonClass,
    evidence_pointer: pointer,
    diagnostic: checkedIn ? `${reasonClass} after check-in` : `${reasonClass} before check-in`,
  });
  const reap = confirmAndReap(evidence, reapOpts);
  return {
    act: 'stamped',
    stamped: true,
    ending: 'failed',
    reason_class: reasonClass,
    checkedIn,
    evidence_pointer: pointer,
    row: stamped,
    ...reap,
  };
}

module.exports = {
  PROVIDER_MARKERS,
  REAP_CONFIRM_BUDGET_MS,
  waitGone,
  providerShaped,
  buildEvidence,
  confirmAndReap,
  stampDeath,
};
