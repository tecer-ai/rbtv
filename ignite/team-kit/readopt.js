'use strict';

// -- BOOT RE-ADOPT - runs BEFORE any outcome stamp or owed launch [C-15, spec-supervisor 2] -----
//
// THE INCIDENT THIS EXISTS FOR. A watchdog restart used to bring the daemon up with no memory of
// what it had spawned. Every liveness question then answered "no record", "no record" read as
// "dead", and the boot pass was free to stamp every live seat `failed` in one sweep. That is the
// mass-restamp hole (C-15 / F-adversarial-7), and it is a hole in the ORDER of operations as much
// as in the data: no amount of persisted state helps if stamping runs first.
//
// SO THIS PASS CLASSIFIES AND WRITES NOTHING. It returns three disjoint sets and no side effect:
//
//   adopted - the row's pid is live AND its /proc start-time still matches. The sitting survived
//             the restart. It is re-adopted as-is; NOTHING is stamped for it.
//   dead    - the pid is gone, or a different process now holds it (start-time mismatch). Only
//             THESE are eligible for evidence-stamping, and the stamping itself is the
//             death-stamp path's act, not this one's. The row STAYS in the file: write moment
//             (iii) drops it after the ending is stamped and confirm-and-reap succeeds, so a crash
//             between classification and stamp loses no debt.
//   skipped - a row too malformed to classify (no usable pid). Not a death: an unreadable row is
//             an unreadable row, and this module never converts absence of evidence into evidence.
//
// AND THE THREE NEGATIVE RULES, each one an incident:
//
//   1. An EMPTY or ABSENT registry is a legal fresh boot. `dead` is empty, so the count of stamps
//      a caller can make is ZERO. Absence is not evidence of death.
//   2. A live OS process with NO row is NOT `failed`. This pass cannot even see it, and that is the
//      point - it never enumerates the process table, only the rows it persisted. Such a process
//      registers on check-in (write moment ii) or stays unsupervised.
//   3. Only after this pass completes may death-stamps or owed-launches run. `assertReadoptDone`
//      below is the guard a caller uses to make that ordering checkable instead of hoped for.

const { loadRegistry, isRowAlive } = require('./registry');

function readopt(pathOverride) {
  const rows = loadRegistry(pathOverride);
  const adopted = [];
  const dead = [];
  const skipped = [];
  for (const row of rows) {
    const pid = Number(row.pid);
    if (!Number.isInteger(pid) || pid <= 0) { skipped.push(row); continue; }
    if (isRowAlive(row)) adopted.push(row);
    else dead.push(row);
  }
  return {
    // TRUE only for a registry with no rows at all - the fresh-boot case rule 1 names. A caller
    // that wants to log "why did nothing get stamped" reads this rather than inferring it from
    // three empty arrays.
    registryEmpty: rows.length === 0,
    rows,
    adopted,
    dead,
    skipped,
  };
}

// The ordering guard. A death-stamp or owed-launch caller passes the result it got from `readopt`;
// anything else - undefined, a hand-built object, a result from a pass that never ran - is a
// refusal, because "we meant to re-adopt first" is exactly what the incident report said.
function assertReadoptDone(result) {
  if (!result || !Array.isArray(result.adopted) || !Array.isArray(result.dead)) {
    throw new Error(
      'REFUSING to stamp or launch before boot re-adopt: pass the result of readopt() first '
      + '(spec-supervisor 2.4 - a stamp that runs before the re-adopt pass is the mass-restamp hole)');
  }
  return result;
}

module.exports = { readopt, assertReadoptDone };
