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

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {
  askRecordPath, readAskRecord, writeAskRecord, asksDir,
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

// Mints the disk record + the `open_asks` row, idempotent per goal. Never posts to Slack — see
// the header. `store` is the ending store bound API (`state-store#bind`'s return, the same handle
// `announceDisarm` passes to `recordGroupedAsk`). The body text is NOT composed here — mirroring
// `exhaustion.js#recordGroupedAsk`'s own split (a lane record carries raw fields, `chat/
// recovery-poster.js` composes at POST time), `chat/disposition-poster.js#composeDispositionBody`
// composes fresh from these raw fields, so there is exactly one place that decides what the owner
// reads, not a mint-time string frozen ahead of the ruled template [`redesign-continue-1`, DoD 4].
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
    // The full rows, not just names — `abandoned_by` is what the composer's recommendation rule
    // reads (DoD 4: recommend `keep` unless every lane was dropped BY THE OWNER) and `anchor` is
    // the closest thing to "how it ended" this data has.
    abandoned_seats: abandonedSeats.map((a) => ({
      seat: a.seat, anchor: a.anchor || null, abandoned_by: a.abandoned_by || null, abandoned_at: a.abandoned_at || null,
    })),
    opened_at: stamp,
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

// -- THE POSTING SIDE — read-side for `chat/disposition-poster.js`, write-side for the gateway's
// `record-owner-ask` handler. Neither touches minting: they read/stamp the SAME record
// `mintLastLaneAsk` already wrote, exactly the split `exhaustion.js#listUnpostedLanes` /
// `#markLanePosted` draw for the recovery ladder's own grouped ask — this is the disposition
// record's own shape (one row per GOAL, no `.lanes` array, body already fully composed at mint
// time), so it needs its own pair rather than a call into `exhaustion.js`'s lane-shaped readers.

// Every disposition record not yet posted as its own Slack thread. `chat/disposition-poster.js`'s
// only read (through `inspect disposition-asks`, never this file directly — the bridge is a
// separate process). Once posted, `markDispositionPosted` stamps `posted_ask_id` and this stops
// returning it.
function listUnpostedDispositions(workspaceRoot) {
  if (!workspaceRoot) return [];
  let entries;
  try {
    entries = fs.readdirSync(asksDir(workspaceRoot), { withFileTypes: true });
  } catch {
    return [];             // no directory is the ordinary state: no goal has reached this yet
  }
  const out = [];
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith('.json')) continue;
    const file = path.join(asksDir(workspaceRoot), entry.name);
    let record;
    try {
      record = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch {
      continue;             // an unreadable record costs its own row, never the listing
    }
    if (!record || record.kind !== DISPOSITION_KIND || !record.goal || record.posted_ask_id) continue;
    out.push({
      record_ask_id: record.ask_id,
      goal: record.goal,
      abandoned_seats: Array.isArray(record.abandoned_seats) ? record.abandoned_seats : [],
      opened_at: record.opened_at || null,
    });
  }
  return out;
}

// Stamps the goal's disposition record POSTED, in place, once its thread exists. Called server-side
// (daemon process, which already holds this file) right after a `record-owner-ask` open for
// `label: 'recovery'` succeeds — never from `chat/`, which may not reach this file directly
// [`probes/probe-chat-boundary.js`]. Idempotent by construction: a record that already carries
// `posted_ask_id` is left alone, so a retried call after a crash costs nothing.
function markDispositionPosted(workspaceRoot, { goal }, { askId, at } = {}) {
  if (!askId) throw new Error('markDispositionPosted requires askId — the thread this ask was posted to');
  const record = readAskRecord(workspaceRoot, askIdForGoal(goal));
  if (!record || record.kind !== DISPOSITION_KIND || record.posted_ask_id) {
    return { marked: false, reason: 'not-found-or-already-posted' };
  }
  record.posted_ask_id = String(askId);
  record.posted_at = at || new Date().toISOString();
  const file = writeAskRecord(workspaceRoot, record);
  return { marked: true, ask_id: record.ask_id, file };
}

module.exports = {
  askIdForGoal,
  lastLaneAbandoned,
  mintLastLaneAsk,
  listUnpostedDispositions,
  markDispositionPosted,
  DISPOSITION_OPTIONS,
  DISPOSITION_LABEL,
  DISPOSITION_KIND,
};
