'use strict';

const path = require('node:path');
const { bind, isLaunchable } = require('../state-store');
const { readExecutionRecord } = require('./execution-record');

function goalNameOf(goalFolder, goal) {
  return goal || path.basename(String(goalFolder || '').replace(/[/\\]+$/, ''));
}

function bindEnding(heartStore) {
  if (!heartStore || !heartStore.db) return null;
  return bind(heartStore.db);
}

function predNames(after) {
  if (Array.isArray(after)) {
    return after.map((m) => String(m).replace(/\[.*$/, '').trim()).filter(Boolean);
  }
  return String(after || '').split(',').map((m) => m.replace(/\[.*$/, '').trim()).filter(Boolean);
}

function endingOf(api, goal, seat) {
  if (!api) return null;
  return api.getCurrentEnding({ goal, seat }) || null;
}

function failedTerminalOf(row) {
  return Boolean(row && row.ending === 'failed' && Number(row.leader_attempt_used) === 1);
}

function predecessorsDone(api, goal, after, doneSet) {
  const preds = predNames(after);
  if (!preds.length) return true;
  return preds.every((seat) => {
    if (doneSet && doneSet.has(seat)) return true;
    const row = endingOf(api, goal, seat);
    return Boolean(row && row.ending === 'done');
  });
}

function launchableOf(api, goal, seat, after, doneSet) {
  const row = endingOf(api, goal, seat);
  return isLaunchable({
    predecessorsDone: predecessorsDone(api, goal, after, doneSet),
    ending: row ? row.ending : null,
    armed: row ? row.armed : null,
    failedTerminal: failedTerminalOf(row),
  });
}

function isPendingWork(api, goal, seat, row) {
  const current = row || endingOf(api, goal, seat);
  if (api && api.seatWaitingOnOwner({ goal, seat })) return false;
  if (current && current.ending === 'done') return false;
  if (failedTerminalOf(current)) return false;
  if (current && current.ending === 'incomplete' && Number(current.armed) === 0) return false;
  return true;
}

function recordView(heartStore, goalFolder, { readyRows = null, goal = null } = {}) {
  const rows = readExecutionRecord(goalFolder).rows;
  const api = bindEnding(heartStore);
  const gid = goalNameOf(goalFolder, goal);
  const done = new Set();
  const foreign = new Map();
  const notFinished = new Map();
  const blocked = new Map();

  const seats = new Set();
  for (const r of readyRows || []) {
    if (r && r.seat) seats.add(r.seat);
  }
  for (const r of rows) {
    if (r && r.seat) seats.add(r.seat);
  }

  for (const seat of seats) {
    const current = endingOf(api, gid, seat);
    if (current && current.ending === 'done') done.add(seat);
    if (api && api.seatWaitingOnOwner({ goal: gid, seat })) {
      blocked.set(seat, 'open posted ask');
      notFinished.set(seat, blocked.get(seat));
    }
  }

  if (!rows.length) {
    const finished = new Set([...done].filter((seat) => !notFinished.has(seat)));
    return { done, finished, foreign, notFinished, blocked };
  }

  const last = new Map();
  for (const r of rows) last.set(r.seat, r);
  for (const [seat, r] of last) {
    if (!(r.outcome || '').trim() && !(r.ended || '').trim()) {
      notFinished.set(seat, `its last execution is still OPEN in the ${r.lane || 'other'} lane (session ${r['session-id']})`);
    }
  }

  const ours = new Set();
  if (heartStore && typeof heartStore.listExecutionsByStatus === 'function') {
    const historyStatuses = ['launching', 'running', 'done', 'blocked', 'failed', 'stalled', 'killed'];
    for (const status of historyStatuses) {
      for (const row of heartStore.listExecutionsByStatus(status, { withThread: false })) {
        if (row.session_id) ours.add(row.session_id);
      }
    }
  }
  for (const r of rows) {
    const outcome = (r.outcome || '').trim();
    if (ours.has(r['session-id'])) continue;
    foreign.set(r.seat, outcome
      ? `ended in the ${r.lane || 'other'} lane (session ${r['session-id']})`
      : `still OPEN in the ${r.lane || 'other'} lane (session ${r['session-id']})`);
  }

  const finished = new Set([...done].filter((seat) => !notFinished.has(seat)));
  for (const seat of finished) foreign.delete(seat);
  return { done, finished, foreign, notFinished, blocked };
}

function readyFromEndings(heartStore, goalFolder, { rows = [], goal = null } = {}) {
  const api = bindEnding(heartStore);
  const gid = goalNameOf(goalFolder, goal);
  const ready = new Map();
  const doneSet = new Set();
  for (const r of rows) {
    if (!r || !r.seat) continue;
    const current = endingOf(api, gid, r.seat);
    if (current && current.ending === 'done') doneSet.add(r.seat);
  }
  for (const r of rows) {
    if (!r || !r.seat) continue;
    if (!launchableOf(api, gid, r.seat, r.after, doneSet)) continue;
    ready.set(r.seat, Array.isArray(r.seed) ? r.seed : []);
  }
  return ready;
}

module.exports = {
  bindEnding,
  goalNameOf,
  predNames,
  endingOf,
  failedTerminalOf,
  predecessorsDone,
  launchableOf,
  isPendingWork,
  recordView,
  readyFromEndings,
};
