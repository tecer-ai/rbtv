'use strict';

const { WARNING_KINDS, announceIntervalTicks } = require('../../state-store/heart/warnings');

const OWNER_NOTE_THREAD = 'owner-feed';

// "Blocked AND out of budget" — evaluated from the SAME determination the
// ticker's blocked-slot re-dispatch gate uses (`heartStore.countChainRecycles`),
// never a second re-implementation of it. A local chain walk here would be a
// divergent source of truth for one condition: it would count an execution's
// own ancestors rather than the CHAIN's total recycles, so any blocked
// execution that is not the chain's deepest node would under-count, and the
// ticker could halt a seat for budget exhaustion while this check stayed
// silent — the exact situation D45 exists to surface to the master.
// (p7-multiturn scope note: the sender-triggered recycle/wake paths are
// UNGATED per the owner's budget ruling; this warning and the blocked gate
// keep the chain-total arithmetic.)
// `jobs_log.status='blocked'` is read HERE AS HISTORY [T4-R8] — the audit record that this chat
// slot's turn ended awaiting input. It is not a seat work-state and not a liveness claim; the
// arithmetic below counts recycles ON that history, which is exactly what a turn log is for.
function findBlockedBudgetExhaustedSubjects(heartStore, slotMaxRepeats) {
  const subjects = new Set();
  for (const exec of heartStore.listExecutionsByStatus('blocked')) {
    if (!exec.thread) continue;
    if (heartStore.countChainRecycles({ execId: exec.exec_id }) >= slotMaxRepeats) {
      subjects.add(exec.thread);
    }
  }
  return subjects;
}

function runWarningCheck({ heartStore, tick, now, slotMaxRepeats, tickIntervalMs, actions }) {
  const activeSubjects = findBlockedBudgetExhaustedSubjects(heartStore, slotMaxRepeats);
  const kind = WARNING_KINDS.SEAT_BLOCKED_BUDGET_EXHAUSTED;
  // D45's "every 60 s" in ticks at the cadence this ticker is ACTUALLY running.
  const announceInterval = announceIntervalTicks(tickIntervalMs);

  const standing = heartStore.listWarnings({ standingOnly: true, kind });
  for (const w of standing) {
    if (!activeSubjects.has(w.subject)) {
      heartStore.clearWarning({ warningId: w.warning_id, tick });
      actions.push({ phase: 'warnings', action: 'clear', kind, subject: w.subject, warningId: w.warning_id });
    }
  }

  for (const subject of activeSubjects) {
    const existing = heartStore.getStandingWarning({ kind, subject });
    if (!existing) {
      const raised = heartStore.raiseWarning({ kind, subject, raisedAtTick: tick });
      actions.push({ phase: 'warnings', action: 'raise', kind, subject, warningId: raised.warning_id });
    }
  }

  for (const w of heartStore.listWarnings({ standingOnly: true, kind })) {
    const snoozed = w.snoozed_until_tick !== null && w.snoozed_until_tick !== undefined && tick < w.snoozed_until_tick;
    if (snoozed) continue;
    const last = w.last_announced_tick;
    if (last === null || last === undefined || tick - last >= announceInterval) {
      const noted = heartStore.recordMessage({
        type: 'note',
        sender: 'ticker',
        thread: OWNER_NOTE_THREAD,
        corpus: `warning: seat ${w.subject} is blocked and out of budget`,
        createdAt: now,
      });
      // Stamp routed AT WRITE (task 7.25 — roots task 7.19's model in this write-site): a
      // ticker-authored owner-feed note is informational — nothing routes it — so it must
      // never enter the unrouted set. tick()'s in-tick compensation only covers calls made
      // inside a tick; a direct caller of runWarningCheck outside tick() would otherwise
      // reintroduce unstamped notes. Same _prepare surface ticker.js's runSql uses.
      heartStore._prepare('UPDATE messages SET routed_at_tick = ? WHERE msg_id = ?').run(tick, noted.msg_id);
      heartStore.announceWarning({ warningId: w.warning_id, tick });
      actions.push({ phase: 'warnings', action: 'announce', kind, subject: w.subject, warningId: w.warning_id });
    }
  }
}

module.exports = { runWarningCheck };
