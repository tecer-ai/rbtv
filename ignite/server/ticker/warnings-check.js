'use strict';

const { WARNING_KINDS, WARNING_ANNOUNCE_INTERVAL_TICKS } = require('../heart/warnings');

const OWNER_NOTE_THREAD = 'owner-feed';

function countRecycles(execId, heartStore) {
  let count = 0;
  let current = heartStore.getExecution(execId);
  while (current && current.parent_exec_id !== null && current.parent_exec_id !== undefined) {
    count++;
    current = heartStore.getExecution(current.parent_exec_id);
  }
  return count;
}

function findBlockedBudgetExhaustedSubjects(heartStore, slotMaxRepeats) {
  const subjects = new Set();
  for (const exec of heartStore.listExecutionsByStatus('blocked')) {
    if (!exec.thread) continue;
    if (countRecycles(exec.exec_id, heartStore) >= slotMaxRepeats) {
      subjects.add(exec.thread);
    }
  }
  return subjects;
}

function runWarningCheck({ heartStore, tick, now, slotMaxRepeats, actions }) {
  const activeSubjects = findBlockedBudgetExhaustedSubjects(heartStore, slotMaxRepeats);
  const kind = WARNING_KINDS.SEAT_BLOCKED_BUDGET_EXHAUSTED;

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
    if (last === null || last === undefined || tick - last >= WARNING_ANNOUNCE_INTERVAL_TICKS) {
      heartStore.recordMessage({
        type: 'note',
        sender: 'ticker',
        thread: OWNER_NOTE_THREAD,
        corpus: `warning: seat ${w.subject} is blocked and out of budget`,
        createdAt: now,
      });
      heartStore.announceWarning({ warningId: w.warning_id, tick });
      actions.push({ phase: 'warnings', action: 'announce', kind, subject: w.subject, warningId: w.warning_id });
    }
  }
}

module.exports = { runWarningCheck };
