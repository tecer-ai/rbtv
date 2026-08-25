'use strict';

// Task 7.11 §4b — THE COMMAND-TIME IDENTITY GATE. CMP-13's protocol at this seam.
//
// The question this answers is not "what does the caller claim to be" but "who is actually
// sitting in this seat". Those came apart tonight, live and expensively: `COORD_AGENT` (asserted)
// outranked pane resolution (verified), two agents ran under one roster name, and the run's own
// message log recorded them as one speaker (G-111). So this checker consults exactly three
// measurables and NOTHING ambient:
//
//   1. the calling process's cwd            -> which seat folder it is in
//   2. the goal's DERIVED LEASE + goals-index, and the seat's `seat.md`/`taskforce.csv`
//                                           -> whether that folder is a LIVE, ROSTERED seat at all
//   3. the goal-level `sessions.csv`        -> who is REGISTERED in that seat
//   4. `/proc` ancestry                     -> whether the caller IS that registered process
//
// ── 7.607 E2a — MEASURABLE 2 IS RE-FOUNDED ON THE LEASE (the E1 residual, #34/#52) ─────────────
// E1 replaced the ticker gate's and the bus authz's register reads but left THIS gate reading
// `runs.csv` through `checkRunLive`, and that residual is closed here. Liveness is now
// `seat-folder.js#checkGoalExecuting` -> `runtime/lease/lease.js`: the goal's tmux room existing
// RIGHT NOW, plus the goals-index membership read that was always a separate question. No stored
// status is read on this path by anything, and the refusal code `E_RUN_NOT_LIVE` is retired with
// the layer that named it — `E_GOAL_NOT_LIVE` says what is actually being refused.
//
// Measurable 2 was absent until G-126 was fixed (task 7.10): the two checks existed but were wired
// into the LAUNCH-time gate only, so the command-time gate confirmed a hand-made folder in a closed
// run. The lesson is not "someone forgot a call" — it is that a suite can prove two helpers work
// and never prove the production entry point INVOKES them, which is what a 13/13 green did here.
//
// There is no env var, no `--as`, no flag, and no config that can substitute for or override the
// match. That is not a policy this module enforces; it is the absence of any code path that reads
// such a thing (G5 bar P7).
//
// AND IT IS CALLER-INDEPENDENT BY CONSTRUCTION. The one input that could smuggle the caller's
// shell shape in is the process ancestry — so the ancestry is searched as a SET (does the
// registered pair appear ANYWHERE among my ancestors) rather than tested against a specific
// generation. `timeout coordinate …` inserts a `timeout` process between the seat's shell and
// this command; a check that asked "is my PARENT the registered process" would answer differently
// under that wrapper, which is exactly G-101's defect — a guard whose verdict was decided by the
// caller's shell line rather than by the artifact. Bar P10 varies the invocation on purpose.

const fs = require('node:fs');
const path = require('node:path');
const { readCsv } = require('./csv');
const { resolveSeatFromCwd, checkGoalExecuting, checkMaterializedSeat } = require('./seat-folder');

// The identity columns §7 pre-registers as the gate's interface to 7.37's writer. `pid` and
// `pid-starttime` are the pair the daemon already trusts everywhere else (spawn.js:396-399) —
// starttime is what defeats pid reuse, so the pid alone is NOT sufficient and is not accepted as
// a degraded mode.
const REQUIRED_IDENTITY_COLUMNS = ['seat', 'pid', 'pid-starttime'];
// The corroborator (§4b step 3). Absent is tolerable — it is not what the decision turns on.
const CORROBORATING_COLUMNS = ['tty'];

function fail(code, message, details = {}) {
  return { ok: false, code, message, ...details };
}

// /proc/<pid>/stat, read defensively: the comm field (2) is parenthesised and may itself contain
// spaces and parentheses, so fields are counted from the LAST ')' rather than by splitting the
// whole line — the classic way this parse goes quietly wrong.
function readProcStat(pid) {
  let raw;
  try {
    raw = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
  } catch {
    return null;
  }
  const close = raw.lastIndexOf(')');
  if (close < 0) return null;
  // Fields from index 0 == field 3 (state), so field N is at index N-3.
  const rest = raw.slice(close + 2).trim().split(/\s+/);
  const ppid = Number.parseInt(rest[4 - 3], 10);        // field 4  — ppid
  const ttyNr = Number.parseInt(rest[7 - 3], 10);       // field 7  — tty_nr
  const starttime = rest[22 - 3];                        // field 22 — starttime (clock ticks)
  if (!Number.isFinite(ppid) || starttime === undefined) return null;
  return { pid: Number(pid), ppid, ttyNr: Number.isFinite(ttyNr) ? ttyNr : null, starttime };
}

// Collect (pid, starttime) for the caller and every ancestor up to pid 1. Bounded: a corrupt
// /proc or a cycle must not spin, and no real ancestry is anywhere near this deep.
function processAncestry(startPid, maxDepth = 64) {
  const chain = [];
  let pid = startPid;
  const seen = new Set();
  for (let i = 0; i < maxDepth; i++) {
    if (!pid || pid < 1 || seen.has(pid)) break;
    seen.add(pid);
    const st = readProcStat(pid);
    if (!st) break;
    chain.push(st);
    if (pid === 1) break;
    pid = st.ppid;
  }
  return chain;
}

// The last row for a seat IS the current occupant: a re-check-in supersedes its predecessor
// (protocol P1), so "latest wins" is the record's own semantics rather than a convenience.
// Rows whose `ended` column is populated are skipped — a departed session is not an occupant.
function currentOccupantRow(rows, seat, header) {
  const hasEnded = header.includes('ended');
  let found = null;
  for (const row of rows) {
    if (row.seat !== seat) continue;
    if (hasEnded && row.ended && row.ended.trim().length > 0) continue;
    found = row;
  }
  return found;
}

// THE GATE. `checkIdentity({ cwd, pid })` — both default to this process, and both are injectable
// so a probe can pose as another process/location WITHOUT this module growing an assertion
// channel: a probe supplies real measurables, it does not supply a claimed name.
//
// Returns { ok: true, seat, ... } or { ok: false, code, message }. Every failure is a typed
// REFUSAL. There is no path that returns ok on missing data — absence fails closed, everywhere,
// because the whole point of this gate is to be the thing that says no.
function checkIdentity({ cwd = process.cwd(), pid = process.pid, readLease = undefined } = {}) {
  const {
    E_IDENTITY_NO_SEAT, E_IDENTITY_NO_SESSION, E_IDENTITY_MISMATCH, E_IDENTITY_SCHEMA,
    E_GOAL_NOT_LIVE, E_NOT_A_SEAT_FOLDER,
  } = require('../../supervisor/spawn/errors');

  // 1 — resolve the folder.
  const parsed = resolveSeatFromCwd(cwd);
  if (!parsed) {
    return fail(
      E_IDENTITY_NO_SEAT,
      `no seat folder encloses ${cwd}. System CLI commands run FROM the seat folder ` +
      '(.rbtv/goals/<goal>/seats/<seat>/); the worktree is for work-product. ' +
      'A command from a non-seat directory has no identity and is refused.',
      { cwd },
    );
  }

  // 2 — L2/L3: is this seat folder a LIVE, MATERIALIZED, ROSTERED seat at all?
  //
  // G-126 (fixed here): these two checks existed and were wired into `spawnSeat`'s LAUNCH-time
  // gate ONLY. The command-time gate — the one a seat runs against for its entire lifetime after
  // launch, and the one task 7.10 wires into the D15 seam — never called them. Proven live before
  // the fix: a hand-made folder with no `seat.md`, an empty `taskforce.csv`, inside a run marked
  // `closed`, returned `{"ok":true}` and exit 0.
  //
  // WHY IT IS NOT ENOUGH THAT LAUNCH CHECKED: launch-time is a single instant, and every fact
  // these two read can change AFTER it. A goal's EXECUTION ENDS while its seats keep running —
  // that is not hypothetical, it is what `G-111` found (a live pane still sitting in a seat folder
  // of an execution the record had already closed), and nothing prunes `sessions.csv` on finish. A
  // gate that only asks at launch answers a question nobody is asking by the time it matters. And
  // seat folders are GOAL-DURABLE now, so the folder outliving the execution is the NORMAL state
  // rather than the exceptional one — which makes this re-ask load-bearing where it was merely
  // prudent before.
  //
  // ORDER IS DELIBERATE: these run BEFORE the session/process match so the refusal names the
  // REAL reason. "this goal is not executing" is actionable; the same case reaching the pid check
  // would refuse with a mismatch message about ancestry, sending the reader after the wrong thing.
  const live = checkGoalExecuting(parsed, readLease ? { readLease } : undefined);
  if (!live.ok) {
    return fail(
      E_GOAL_NOT_LIVE,
      `seat "${parsed.seat}" is a seat of goal ${parsed.goal}, which is not provably EXECUTING: ` +
      `${live.reason}. Identity is scoped to a live execution — a seat whose goal is not running ` +
      'has no standing to act, however genuinely it occupies the folder.',
      { seat: parsed.seat, goal: parsed.goal, reason: live.reason },
    );
  }

  const materialized = checkMaterializedSeat(parsed);
  if (!materialized.ok) {
    return fail(
      E_NOT_A_SEAT_FOLDER,
      `${parsed.seatDir} has the shape of a seat folder but is not a materialized, rostered seat: ` +
      `${materialized.reason}. The path shape is a NAMING convention, not a credential — a folder ` +
      'anyone can mkdir must not confer an identity.',
      { seat: parsed.seat, seatDir: parsed.seatDir, reason: materialized.reason },
    );
  }

  // 3 — resolve the registered occupant.
  const log = readCsv(parsed.sessionsCsv);
  if (!log.exists) {
    return fail(
      E_IDENTITY_NO_SESSION,
      `the goal's session log is unreadable at ${parsed.sessionsCsv} — identity cannot be established, so it is refused`,
      { seat: parsed.seat, sessionsCsv: parsed.sessionsCsv },
    );
  }
  const missing = REQUIRED_IDENTITY_COLUMNS.filter((c) => !log.header.includes(c));
  if (missing.length > 0) {
    return fail(
      E_IDENTITY_SCHEMA,
      `${parsed.sessionsCsv} carries no ${missing.join('/')} column (header: ${log.header.join(',')}). ` +
      'Identity is the (pid, pid-starttime) pair matched against live /proc; a log without it cannot ' +
      'name an occupant, and this gate refuses rather than degrade to "the folder alone". ' +
      'The writer of these columns is task 7.37 (design §7 interface contract).',
      { seat: parsed.seat, sessionsCsv: parsed.sessionsCsv, missing, header: log.header },
    );
  }
  const row = currentOccupantRow(log.rows, parsed.seat, log.header);
  if (!row) {
    return fail(
      E_IDENTITY_NO_SESSION,
      `no open session row for seat "${parsed.seat}" in ${parsed.sessionsCsv} — nobody is registered as sitting here`,
      { seat: parsed.seat, sessionsCsv: parsed.sessionsCsv },
    );
  }

  const regPid = Number.parseInt(row.pid, 10);
  const regStart = (row['pid-starttime'] || '').trim();
  if (!Number.isFinite(regPid) || regStart.length === 0) {
    return fail(
      E_IDENTITY_SCHEMA,
      `the session row for "${parsed.seat}" (line ${row.__line}) carries pid="${row.pid}" ` +
      `pid-starttime="${row['pid-starttime']}" — not a usable identity pair`,
      { seat: parsed.seat, row: row.__line },
    );
  }

  // 4 — match the live process. The registered pair must appear among MY ancestors (or be me).
  const chain = processAncestry(pid);
  const match = chain.find((p) => p.pid === regPid && String(p.starttime) === regStart);
  if (!match) {
    const alsoLive = readProcStat(regPid);
    const stale = alsoLive && String(alsoLive.starttime) !== regStart;
    return fail(
      E_IDENTITY_MISMATCH,
      `seat "${parsed.seat}" is registered to pid ${regPid} (starttime ${regStart})` +
      `${stale ? ' — that pid is now a DIFFERENT process (starttime differs); the row is stale' : ''}` +
      `, which is not among this process's ancestors (${chain.map((p) => p.pid).join('<-')}). ` +
      'Being in the folder is not being the occupant.',
      {
        seat: parsed.seat,
        registeredPid: regPid,
        registeredStarttime: regStart,
        ancestry: chain.map((p) => ({ pid: p.pid, starttime: p.starttime })),
        pidReused: Boolean(stale),
      },
    );
  }

  // Corroborator, never the decision. A tty mismatch is REPORTED so a caller that cares can act,
  // but it does not overturn a pair that matched — the pair is the stronger evidence, and letting
  // a weaker signal veto a stronger one is how a gate acquires false refusals nobody can explain.
  let ttyAgrees = null;
  if (CORROBORATING_COLUMNS.every((c) => log.header.includes(c)) && row.tty) {
    const self = readProcStat(pid);
    ttyAgrees = self && self.ttyNr !== null ? String(self.ttyNr) === String(row.tty).trim() : null;
  }

  return {
    ok: true,
    seat: parsed.seat,
    goal: parsed.goal,
    seatDir: parsed.seatDir,
    goalDir: parsed.goalDir,
    sessionId: row['session-id'] || null,
    registeredPid: regPid,
    matchedAncestor: { pid: match.pid, starttime: match.starttime },
    ttyAgrees,
    // §4b step 4 — permissions attach mechanically from the seat's own records. `seat.md` is the
    // permission surface and §2 makes it unwritable by the occupant, so this is a read of
    // something the confirmed identity could not have authored. No per-command grant exists.
    permissionsSource: path.join(parsed.seatDir, 'seat.md'),
  };
}

module.exports = {
  checkIdentity,
  processAncestry,
  readProcStat,
  currentOccupantRow,
  REQUIRED_IDENTITY_COLUMNS,
};
