'use strict';

const path = require('node:path');
const { bind, isLaunchable, openEndingStoreFor } = require('../state-store');
const { readExecutionRecord } = require('./execution-record');

function goalNameOf(goalFolder, goal) {
  return goal || path.basename(String(goalFolder || '').replace(/[/\\]+$/, ''));
}

// `<workspace>/.rbtv/goals/<goal>` → `<workspace>`. The goal folder is the ONE thing every caller
// on this path already holds, and the shape is fixed by the launcher (`execution-record.js`'s
// `SEAT_DIR_RE` walks the same three segments from the other end).
const GOAL_DIR_RE = /^(.*)[/\\]\.rbtv[/\\]goals[/\\][^/\\]+[/\\]?$/;

function workspaceRootOf(goalFolder) {
  const m = GOAL_DIR_RE.exec(path.resolve(String(goalFolder || '')));
  return m ? m[1] : null;
}

// ── WHICH FILE THE ENDINGS COME OUT OF, AND WHY IT IS NOT THE LANE'S OWN STORE ────────────────
//
// Spec-state-store §1.1: the ONE ending store is `<workspace>/.rbtv/runtime/ignite/heart.db`,
// workspace-scoped — NOT per-goal `heart.db`, NOT `{state_root}/heart.db` after cutover. Binding
// `heartStore.db` (which this function did, and which is why the fallback below is still spelled
// out) bound whichever store THIS lane happened to open: `<goal>/heart.db` under `rbtv run`,
// `{data_root}/heart.db` under the daemon. Two lanes, two files, one seat — so a seat the attached
// lane finished read UNFINISHED to the daemon, which is exactly the cross-lane resume this build
// exists to guarantee. It is also how the kit already resolves it: `coord/ending_store.py`
// walks up for `.rbtv` and lands on the same path, so coord and the engine agree by construction
// rather than by configuration.
//
// THE FALLBACK IS FOR A CALLER WITH NO GOAL FOLDER, and it is the old behaviour deliberately kept:
// a bound `heartStore` whose db carries the tables still answers. A caller with NEITHER gets
// `null`, and every reader here treats a null api as "no ending declared" — the absence that §1.1
// says is not a word.
function bindEnding(heartStore, goalFolder = null) {
  const root = workspaceRootOf(goalFolder);
  if (root) {
    try {
      return bind(openEndingStoreFor(root));
    } catch {
      // An unopenable home must not take the pass down with it — fall through to the lane store,
      // and failing that answer "nothing declared", which is the fail-safe direction: a seat with
      // no ending is launchable, never silently finished.
    }
  }
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
  const api = bindEnding(heartStore, goalFolder);
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
    // OPEN-vs-ENDED IS THE `ended` STAMP, NOT THE `outcome` WORD. Row D emptied that column, so
    // this line reported every foreign row — closed ones included — as "still OPEN", which is the
    // one thing an operator reads this string to tell apart.
    const ended = (r.ended || '').trim();
    if (ours.has(r['session-id'])) continue;
    foreign.set(r.seat, ended
      ? `ended in the ${r.lane || 'other'} lane (session ${r['session-id']})`
      : `still OPEN in the ${r.lane || 'other'} lane (session ${r['session-id']})`);
  }

  const finished = new Set([...done].filter((seat) => !notFinished.has(seat)));
  for (const seat of finished) foreign.delete(seat);
  return { done, finished, foreign, notFinished, blocked };
}

function readyFromEndings(heartStore, goalFolder, { rows = [], goal = null } = {}) {
  // THE LAUNCHABLE SET IS THE KIT'S `verdict === 'READY'` — one door. The ending ledger is a
  // CROSS-CHECK only: a READY row whose current ending is `done` is a SKEW the kit should have
  // raised. Log it at the caller; do not launch it. Predecessor/`after` arithmetic lives in
  // `ready.py`; re-deriving it here is how HELD/STOPPED/IDLE/SKEW seats still launched.
  const api = bindEnding(heartStore, goalFolder);
  const gid = goalNameOf(goalFolder, goal);
  const ready = new Map();
  for (const r of rows) {
    if (!r || !r.seat) continue;
    if (r.verdict !== 'READY') continue;
    const current = endingOf(api, gid, r.seat);
    if (current && current.ending === 'done') continue;
    ready.set(r.seat, Array.isArray(r.seed) ? r.seed : []);
  }
  return ready;
}

module.exports = {
  bindEnding,
  workspaceRootOf,
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
