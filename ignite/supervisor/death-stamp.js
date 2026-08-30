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

const path = require('node:path');
const { isAliveProcess, loadRegistry, dropRow, keyOf } = require('./registry');
const { readCsv } = require('../runtime/seat-identity/csv');

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

// -- WHICH SITTING A DECLARED ENDING BELONGS TO -------------------------------------------------
//
// `seat_endings` is keyed `(goal, seat)` [spec-state-store schema: goal, seat, ending, armed,
// reason_class, who_stamped, evidence_pointer, diagnostic, named_event, stamped_at, ...] - NO
// session column, ever, for a `done`/`incomplete` row: `stamp_seat_declare` (coord/checkout.py)
// writes an `evidence_pointer` that is a declared-output PATH or the literal `checkout:<seat>`,
// never a session id. So "does this declared ending belong to the sitting dying RIGHT NOW" cannot
// be read off the row directly - there is nothing on it to compare a session against.
//
// `sessions.csv` is the FALLBACK SOURCE of the dying sitting's own identity: `evidence.session` is
// the id the closer wrote at spawn (`spawn.js`'s at-dispatch record, `coord/records.py`
// SESSIONS_COLS), and that row's `started` column is the one fact this file can trust as "when
// THIS sitting began" - it is written once, by the sitting's own spawn, under a name coord's
// checkout path never touches. A declared ending STAMPED BEFORE that sitting started cannot be
// its own declaration: it is a stale row an EARLIER sitting of the same seat left behind, and the
// stamp table's first two rows (§ above) were never meant to cover that case.
//
// Both facts are OPTIONAL. No `evidence.session` (the tmux-lane closer does not pass one today),
// no `RBTV_IGNITE_WORKSPACE_ROOT` (set on the daemon's own unit, inherited by every closer it
// spawns - `runtime/index.js` reads the same variable), no readable `sessions.csv`, or no row for
// that session: any of these leaves this function unable to prove staleness, and the guard falls
// back to today's behaviour (the declaration stands) rather than inventing one from partial data.
function goalFolderOf(goal) {
  const root = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  if (!root || !goal) return null;
  return path.join(root, '.rbtv', 'goals', String(goal));
}

function sittingStartedAt(evidence) {
  const session = evidence && evidence.session;
  const goalFolder = goalFolderOf(evidence && evidence.goal);
  if (!session || !goalFolder) return null;
  const candidates = [
    path.join(goalFolder, 'coordination', 'sessions.csv'),
    path.join(goalFolder, 'sessions.csv'),
  ];
  for (const file of candidates) {
    const { exists, rows } = readCsv(file);
    if (!exists) continue;
    const row = rows.find((r) => (r['session-id'] || '').trim() === String(session));
    if (row) return (row.started || '').trim() || null;
  }
  return null;
}

// A declared ending is stale for THIS sitting only when both timestamps parse and the ending
// predates the sitting's own start. An unparseable or missing side is "cannot prove it", never
// "assume stale" - the whole point of a fallback comparison is that it only fires on real evidence.
function declaredEndingIsStale(current, evidence) {
  const started = sittingStartedAt(evidence);
  if (!started || !current || !current.stamped_at) return false;
  const startedMs = Date.parse(started);
  const stampedMs = Date.parse(current.stamped_at);
  if (Number.isNaN(startedMs) || Number.isNaN(stampedMs)) return false;
  return stampedMs < startedMs;
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

  // ROW 1 and ROW 2 - a checkout is present, so THE SITTING DYING NOW already spoke. Nothing is
  // stamped and no `failed` is invented on top of a declaration; what is owed is the reap.
  //
  // ⚠ THIS IS UNSOUND FOR A LATER SITTING OF THE SAME SEAT (the cause `declaredEndingIsStale`
  // exists to close): `(goal, seat)` has no session in it, so a sitting that declared nothing and
  // died on its own (a provider 429, a crash) inherited whatever an EARLIER sitting of the same
  // seat last declared. `declaredEndingIsStale` is the one place that checks whether the row could
  // possibly be this sitting's own before trusting it.
  if ((declared === 'done' || declared === 'incomplete') && !declaredEndingIsStale(current, evidence)) {
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
  // `replace: true` is a no-op when no ending row exists yet (ROWS 3-5's ordinary case: `current`
  // is null, `writeEnding`'s write-once guard never fires either way) and is REQUIRED the one case
  // it is not - a stale `done`/`incomplete` from an earlier sitting that `declaredEndingIsStale`
  // just proved is not this sitting's own. Without it the store's write-once guard (spec-state-store
  // §1: one ending per (goal, seat) unless the caller says replace) throws `E_WRITE_ONCE` on exactly
  // the row this fix exists to get past.
  const stamped = store.stampSystem({
    goal,
    seat,
    ending: 'failed',
    reason_class: reasonClass,
    evidence_pointer: pointer,
    diagnostic: checkedIn ? `${reasonClass} after check-in` : `${reasonClass} before check-in`,
    replace: true,
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
  goalFolderOf,
  sittingStartedAt,
  declaredEndingIsStale,
  REAP_CONFIRM_BUDGET_MS,
  waitGone,
  providerShaped,
  buildEvidence,
  confirmAndReap,
  stampDeath,
};
