'use strict';

// ask-store — the bridge's door onto the ONE open-ask record (spec-state-store §3, [T5-R7,
// D-4-ruling, C-3]). It is an ADAPTER, not a store: the rows live in the `open_asks` table inside
// `.rbtv/runtime/ignite/heart.db`, written through `state-store`'s API, and this module only
// translates the bridge's vocabulary (workspace root + goal id + Slack thread) into that API's.
//
// ⚠ `owner-asks.json` IS GONE. The per-goal JSON file this module used to own was a SECOND record
// of a fact the ending store now holds, and the pair is exactly the dual-writer defect the
// redesign exists to close. Two consequences follow, and neither is an oversight:
//
//   1. `ask_id` IS THE SLACK THREAD ID. There is no allocator and no per-seat queue of asks
//      [T5-R7]. The pre-D89 rule that a reply settles "the oldest open ask" is DELETED: an
//      authorized reply releases the ask bound to THAT EXACT THREAD [D-4-ruling, T1-R12]. A second
//      owner message in the same thread is the same ask, not a second row; a genuinely new
//      question opens a NEW thread and therefore a new `ask_id`.
//   2. THE ASK'S TEXT IS NOT A STORE COLUMN. `open_asks` carries an `evidence_pointer`, which
//      §3 defines as the thread permalink or an ON-DISK REPLY COPY. This module writes that copy
//      (one file per ask under the goal's `coordination/asks/`) and stores its path, so the
//      re-inject readers on the Python side still have the body to read while the STATE of the ask
//      lives in exactly one place.
//
// Wait is DERIVED, never stored (§2.1): a seat is waiting-on-owner iff a row here is `posted=1`
// and still `open`. Nothing in this module writes a seat ending — resolution reaps the ask and
// signals the relaunch in ONE transaction (`reapAndRelaunch`, §2.8), which is the store's job.

const fs = require('node:fs');
const path = require('node:path');
const { openHeartStore } = require('../../server/heart/heart-store');
const { bind, endingStorePath } = require('../../state-store');

const ASK_LABEL_DEFAULT = 'work-content';

function coordTimestamp(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// The ONE store file (spec §1.1). Kept exported under its old name so a caller that logs "where
// does this live" keeps working; it now names heart.db, never a per-goal JSON file.
function storePath(workspaceRoot) {
  return endingStorePath(workspaceRoot);
}

// A thread id is a Slack ts (`1723480000.123456`) or a fixture string; neither is safe as a bare
// filename, so the on-disk copy is named from a sanitized form. The ROW still carries the raw id.
function askCopyPath(workspaceRoot, goalId, askId) {
  const safe = String(askId).replace(/[^A-Za-z0-9._-]/g, '_');
  return path.join(workspaceRoot, '.rbtv', 'goals', String(goalId), 'coordination', 'asks', `${safe}.txt`);
}

function withStore(workspaceRoot, fn) {
  const dbPath = endingStorePath(workspaceRoot);
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const heart = openHeartStore({ dbPath });
  try {
    return fn(bind(heart.db), heart.db);
  } finally {
    heart.close();
  }
}

// Rows for one (goal, seat), oldest first. A plain SELECT rather than an API call because the
// store exposes single-ask and counting reads only — this module CONSUMES the table, it never
// writes it outside the API above.
function selectRows(db, goalId, seat) {
  return db.prepare(
    `SELECT ask_id, goal, seat, label, state, posted, posted_at, authorized_reply_at, evidence_pointer
       FROM open_asks WHERE goal = ? AND seat = ? ORDER BY rowid ASC`,
  ).all(String(goalId), String(seat));
}

// The bridge's view of one row: the store's fields plus the ask body read back off the evidence
// pointer. `text` is '' when the copy is gone — a missing body never turns into a missing ask.
function present(row) {
  let text = '';
  try { text = fs.readFileSync(row.evidence_pointer, 'utf8'); } catch { text = ''; }
  return {
    id: row.ask_id,
    askId: row.ask_id,
    seat: row.seat,
    goalId: row.goal,
    chatThreadId: row.ask_id,
    label: row.label,
    text,
    status: row.state,
    posted: Number(row.posted) === 1,
    askedAt: row.posted_at || null,
    answeredAt: row.authorized_reply_at || null,
    evidencePointer: row.evidence_pointer,
  };
}

// Record an owner ask on `seat` in `goalId`. Idempotent per thread: a second message arriving in a
// thread that already carries an open ask updates the on-disk copy and returns the SAME row — the
// ask is the thread, so there is nothing new to open.
function createAsk({ workspaceRoot, goalId, seat, chatThreadId, text, execId = null, label = ASK_LABEL_DEFAULT }) {
  const askId = chatThreadId != null ? String(chatThreadId) : '';
  if (!askId) throw new Error('createAsk requires chatThreadId — the Slack thread IS the ask id');
  const copy = askCopyPath(workspaceRoot, goalId, askId);
  fs.mkdirSync(path.dirname(copy), { recursive: true });
  fs.writeFileSync(copy, String(text || ''));
  return withStore(workspaceRoot, (api, db) => {
    const existing = api.getAsk(askId);
    if (!existing) {
      api.insertAsk({
        ask_id: askId, goal: String(goalId), seat: String(seat), label, evidence_pointer: copy,
      });
      // POSTED AT INSERT, because the only caller records an ask AFTER its forward landed
      // (`forward-path.js` gates on `outcome.forwarded === true`). §2.1 reads `posted`, so a row
      // left at 0 would be an ask nobody is waiting on — the state this record exists to prevent.
      api.postAsk({ ask_id: askId, posted_at: coordTimestamp() });
    }
    const row = selectRows(db, goalId, seat).find((r) => r.ask_id === askId);
    const out = present(row);
    out.execId = execId != null ? String(execId) : null;
    return out;
  });
}

// Settle the ask a conformant owner-facing reply answered, and signal the bound seat's relaunch in
// the SAME transaction (§2.8 — no orphan-or-twin). `askId` is the thread the reply landed in; it
// is REQUIRED, because "the oldest open ask" is the rule [D-4-ruling] deletes. Returns null when
// the thread carries no ask, so a reply nobody asked for never invents a record.
function markAnswered({ workspaceRoot, goalId, seat, askId = null }) {
  const id = askId != null ? String(askId) : '';
  if (!id) return null;
  return withStore(workspaceRoot, (api, db) => {
    const row = api.getAsk(id);
    if (!row || String(row.goal) !== String(goalId) || String(row.seat) !== String(seat)) return null;
    if (row.state === 'closed') return present(row);
    api.reapAndRelaunch({ ask_id: id, authorized_reply_at: coordTimestamp() });
    const after = selectRows(db, goalId, seat).find((r) => r.ask_id === id);
    return after ? present(after) : null;
  });
}

// ALL of `seat`'s asks in `goalId`, oldest first — open, answered and closed alike. A caller that
// wants only the live ones filters `status === 'open'` (§2.1 also requires `posted`).
function getAsk({ workspaceRoot, goalId, seat }) {
  return withStore(workspaceRoot, (_api, db) => selectRows(db, goalId, seat).map(present));
}

module.exports = { storePath, askCopyPath, createAsk, markAnswered, getAsk, coordTimestamp };
