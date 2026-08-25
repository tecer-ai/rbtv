'use strict';

// -- THE POST-RESTART SUPPRESSION WINDOW (task #113 criterion 2) --------------------------------
//
// WHAT WAS BROKEN. Incident BIT-7, 2026-08-19: the ignite daemon was down 3h05m, and when it came
// back a relaunch grant's pickup latency swung from 17 seconds to 10 minutes 35 seconds ACROSS the
// restart. Every latency-shaped check measured that swing as a stall and would have paged the owner
// about it — but the swing was the restart itself, not a stuck goal: the queue the daemon woke up
// to was three hours deep, and everything in it was "late" by definition. An alarm that cannot tell
// "this goal stopped" from "the daemon was just restarted underneath it" trains its reader to
// ignore it, which is how a real page gets ignored too.
//
// THE RULE. A latency- or stall-shaped alarm that would fire within the configured window of a
// WATCHDOG-DETECTED daemon restart is suppressed. Not deleted — suppressed: the condition is
// re-checked on the next cadence, and once the window is past it alarms exactly as it would have.
//
// WHERE THE FACT COMES FROM, AND WHY NOT FROM THE DAEMON'S OWN MEMORY. A daemon that has just
// restarted cannot know it restarted: its own process-lifetime state is precisely what the restart
// erased (the same defect that made `goal-stall-alarm.js`'s dedup Map re-page everything). The
// external watchdog's APPEND-ONLY outage ledger is the record that survives it —
// `observation/daemon-watchdog`, `.rbtv/runtime/watchdog/outage-ledger.jsonl`, one JSON object per
// line, written by a process that stays up while the daemon does not.
//
// ⚠ TWO DECISIONS COUNT AS A RESTART AND NO OTHERS. `recovered` (the unit reads determinately
// running again after a non-healthy streak) and `restart-taken` (the watchdog restarted it). The
// withheld-restart arms and `observed-not-healthy` are deliberately NOT restarts: the daemon never
// went away and nothing about its queue depth changed, so suppressing alarms on them would be a
// silence bought with no event.
//
// ⚠ NO WINDOW IS CONFIGURED MEANS NO SUPPRESSION, SAID OUT LOUD. The number is not a literal here
// and there is no fallback constant — the same discipline spec-recovery §2.1 imposes on the five
// recovery knobs, applied to a number that is NOT one of its eight keys (that schema is closed and
// refuses extras). An unconfigured window degrades to today's behaviour — every alarm fires — which
// is the honest direction: a suppression nobody configured must never silence a real page.

const fs = require('node:fs');
const path = require('node:path');

// The watchdog's own default, derived from the workspace and never hardcoded absolute (repo law:
// per-instance inputs resolve at runtime). `RBTV_WATCHDOG_LEDGER` is the SAME env knob the watchdog
// reads, so pointing one at a test ledger points both.
const LEDGER_REL = ['.rbtv', 'runtime', 'watchdog', 'outage-ledger.jsonl'];

// `daemon_health_streak()` writes the first on recovery; `main()`'s action path writes the second
// for every row it actually restarted.
const RESTART_DECISIONS = new Set(['recovered', 'restart-taken']);

// The ledger is append-only and never rotated, so it is read from the END. 64 KB is thousands of
// rows — far more than any suppression window can span — and it bounds a per-cadence read that
// would otherwise grow without limit. The first line of a tail read may be a fragment; an
// unparseable line is skipped, never guessed at.
const TAIL_BYTES = 64 * 1024;

function ledgerPathFor(workspaceRoot, env = process.env) {
  if (env && env.RBTV_WATCHDOG_LEDGER) return path.resolve(env.RBTV_WATCHDOG_LEDGER);
  if (!workspaceRoot) return null;
  return path.resolve(workspaceRoot, ...LEDGER_REL);
}

function tailLines(file) {
  let fd;
  try {
    fd = fs.openSync(file, 'r');
  } catch {
    return [];   // no ledger yet: no watchdog has ever written, so nothing is suppressed
  }
  try {
    const size = fs.fstatSync(fd).size;
    const start = size > TAIL_BYTES ? size - TAIL_BYTES : 0;
    const buf = Buffer.alloc(size - start);
    fs.readSync(fd, buf, 0, buf.length, start);
    const text = buf.toString('utf8');
    const lines = text.split('\n');
    if (start > 0) lines.shift();   // a partial first line, never a record
    return lines.filter((l) => l.trim() !== '');
  } catch {
    return [];
  } finally {
    try { fs.closeSync(fd); } catch { /* the read already answered */ }
  }
}

// The most recent restart the watchdog recorded, as epoch ms, or null. The ledger is append-only so
// the LAST matching row is the newest, but the rows carry their own `at` and the max is taken from
// the value rather than from the position — a ledger concatenated by hand during an incident must
// not be able to make an old restart look current.
function lastRestartMs(file) {
  if (!file) return null;
  let newest = null;
  let row = null;
  for (const line of tailLines(file)) {
    let doc;
    try { doc = JSON.parse(line); } catch { continue; }
    if (!doc || !RESTART_DECISIONS.has(doc.decision)) continue;
    const at = Date.parse(doc.at);
    if (Number.isNaN(at)) continue;
    if (newest === null || at > newest) { newest = at; row = doc; }
  }
  return newest === null ? null : { at: newest, row };
}

// The one question a caller asks: may this alarm fire right now?
//
// Returns `{ suppressed, reason, ... }` and NEVER throws — a suppression check that could abort the
// pass would be a new way for the liveness surface to go silent, which is the class of failure the
// whole watchdog exists to remove.
function restartSuppression({
  workspaceRoot = null,
  ledgerFile = null,
  windowMin = null,
  now = () => Date.now(),
  env = process.env,
} = {}) {
  const minutes = Number(windowMin);
  if (!Number.isInteger(minutes) || minutes <= 0) {
    return { suppressed: false, armed: false, reason: 'no-window-configured' };
  }
  const file = ledgerFile ? path.resolve(ledgerFile) : ledgerPathFor(workspaceRoot, env);
  if (!file) return { suppressed: false, armed: false, reason: 'no-ledger-path' };
  let found;
  try {
    found = lastRestartMs(file);
  } catch {
    return { suppressed: false, armed: true, reason: 'ledger-unreadable', ledger: file };
  }
  if (!found) return { suppressed: false, armed: true, reason: 'no-restart-on-the-ledger', ledger: file };
  const at = typeof now === 'function' ? now() : Number(now);
  const windowMs = minutes * 60 * 1000;
  const elapsedMs = at - found.at;
  if (elapsedMs < 0 || elapsedMs >= windowMs) {
    return {
      suppressed: false, armed: true, reason: 'outside-the-window', ledger: file,
      restart_at: new Date(found.at).toISOString(), elapsed_ms: elapsedMs, window_min: minutes,
    };
  }
  return {
    suppressed: true,
    armed: true,
    reason: 'a watchdog-detected daemon restart is inside the suppression window [task #113]',
    ledger: file,
    decision: found.row.decision,
    restart_at: new Date(found.at).toISOString(),
    elapsed_ms: elapsedMs,
    window_min: minutes,
    until: new Date(found.at + windowMs).toISOString(),
  };
}

module.exports = {
  LEDGER_REL,
  RESTART_DECISIONS,
  TAIL_BYTES,
  ledgerPathFor,
  lastRestartMs,
  restartSuppression,
};
