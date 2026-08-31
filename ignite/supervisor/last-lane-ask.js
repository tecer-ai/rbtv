'use strict';

// -- THE CLOSE-OR-KEEP ASK — raised when drop-lane abandons a goal's LAST owed lane -------------
// `d-recovery-last-lane-asks` + `d-recovery-waiting-goal-freeze` (owner ruling, 2026-08-31): when
// the dropped lane was the goal's last one with work, the system does NOT close the goal on its
// own and does NOT leave it silent either — it raises ONE question in the goal's own channel:
// close this goal, or keep it open? While that question is open, the goal's shutdown clock (the
// frozen-goal alarm's `open_ask` exclusion) is already suspended by the ONE existing mechanism —
// minting a POSTED, OPEN ask IS the suspension [`state-store/predicates.js#countOpenAsks`]. This
// file mints; it never posts and never suspends anything of its own — see the header below.
//
// THE CONDITION IS `deriveOwed`'s OWN ANSWER, NEVER RE-DERIVED [spec-supervisor §5]. `owed-from-
// endings.js#classifyOwed` already excludes an abandoned seat from classA/classB/pending
// (`dl-abandoned-outcome`, live today — no extra wiring needed for reconcile's own ledger half).
// `lastLaneAbandoned` below reads `derived.owed` and `derived.abandonedSeats`, both already on
// `owed.js#deriveOwed` / `reconcile.js#owedFromLedgers`'s return object, and asks nothing about
// endings, sessions or the ledger itself. A goal that finished normally carries an empty
// `abandonedSeats`, so ordinary completion never mints this ask.
//
// MINTING FOLLOWS `exhaustion.js#recordGroupedAsk`'s OWN SHAPE — the same ask surface
// `reconcile.js#announceDisarm` already uses: a JSON record under `.rbtv/runtime/ignite/asks/`
// with `posted: 0`, plus an `open_asks` row with `state: 'open'`. Posting (the Slack side, the act
// that flips `posted` to 1) is a SEPARATE, later act — `exhaustion.js`'s own header states the same
// split for its ask: "NO SLACK, NO OUTBOX, NOT ONE BYTE. This module writes a RECORD and stops."
//
// ONE RECORD PER GOAL, STABLE ID, IDEMPOTENT. The id is derived from the goal name alone, never a
// timestamp: `d-recovery-drop-is-one-lane-permanent` makes every lane's drop permanent, so a goal
// reaches "last lane abandoned" at most once, and a stable id means a later pass that finds the
// record already on disk mints nothing twice — the same read-before-write `recordGroupedAsk` uses.

const crypto = require('node:crypto');
const {
  askRecordPath, readAskRecord, writeAskRecord,
} = require('./exhaustion');

const DISPOSITION_OPTIONS = Object.freeze(['close', 'keep']);
const DISPOSITION_LABEL = 'recovery';
const DISPOSITION_KIND = 'goal-disposition';

function askIdForGoal(goal) {
  return `disposition-${crypto.createHash('sha256').update(String(goal)).digest('hex').slice(0, 12)}`;
}

// `derived` is `owed.js#deriveOwed` / `reconcile.js#owedFromLedgers`'s own return object — read
// here, never recomputed.
function lastLaneAbandoned(derived) {
  if (!derived || derived.owed) return false;
  return Array.isArray(derived.abandonedSeats) && derived.abandonedSeats.length > 0;
}

function composeBody({ goal, abandonedSeats }) {
  const names = abandonedSeats.map((a) => a.seat).join(', ');
  return [
    `*GOAL*: ${goal}`,
    `Every lane still owed work on this goal was dropped (drop-lane): ${names}.`,
    '',
    'Reply with one word: close · keep',
    'close — mark this goal closed, and NOT as a success.',
    'keep — leave this goal open. Nothing more is owed and nothing launches on its own.',
    'Comments after the first word.',
  ].join('\n');
}

// Mints the disk record + the `open_asks` row, idempotent per goal. Never posts to Slack — see
// the header. `store` is the ending store bound API (`state-store#bind`'s return, the same handle
// `announceDisarm` passes to `recordGroupedAsk`).
function mintLastLaneAsk({
  store, workspaceRoot, goal, abandonedSeats, at,
} = {}) {
  if (!workspaceRoot) return { minted: false, reason: 'no-workspace-root' };
  if (!Array.isArray(abandonedSeats) || !abandonedSeats.length) {
    return { minted: false, reason: 'no-abandoned-seats' };
  }
  const askId = askIdForGoal(goal);
  const stamp = at || new Date().toISOString();
  const existing = readAskRecord(workspaceRoot, askId);
  if (existing) {
    return {
      askId, file: askRecordPath(workspaceRoot, askId), record: existing, minted: false, reason: 'already-open',
    };
  }
  const record = {
    ask_id: askId,
    kind: DISPOSITION_KIND,
    label: DISPOSITION_LABEL,
    goal,
    options: [...DISPOSITION_OPTIONS],
    abandoned_seats: abandonedSeats.map((a) => a.seat),
    opened_at: stamp,
    body: composeBody({ goal, abandonedSeats }),
  };
  const file = writeAskRecord(workspaceRoot, record);
  let row = store && typeof store.getAsk === 'function' ? store.getAsk(askId) : null;
  if (!row && store && typeof store.insertAsk === 'function') {
    row = store.insertAsk({
      ask_id: askId,
      goal,
      seat: abandonedSeats[0].seat,
      label: DISPOSITION_LABEL,
      evidence_pointer: file,
    });
  }
  return {
    askId, file, record, row, minted: true,
  };
}

module.exports = {
  askIdForGoal,
  lastLaneAbandoned,
  composeBody,
  mintLastLaneAsk,
  DISPOSITION_OPTIONS,
  DISPOSITION_LABEL,
  DISPOSITION_KIND,
};
