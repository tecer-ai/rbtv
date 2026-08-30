'use strict';

// ── THE OWNER-ASK RECORD, STAMPED DAEMON-SIDE (owner ruling 2026-08-24, option (a),
// `redesign-implementation/decisions.md`) ────────────────────────────────────────────────────────
//
// THE GAP THIS CLOSES. `spec-state-store` §3 replaces the bridge's per-goal `owner-asks.json` with
// the daemon-owned `open_asks` table, because a seat's wait must be DERIVED from one record (§2.1:
// an ask that is `posted` and still `open`) instead of stored in a file a second component owns.
// The bridge could not make that move itself: `chat` is a SEPARATE PROCESS that reaches the
// daemon only over the gateway, and `probes/probe-chat-boundary.js` forbids a store handle, a child
// process and a sibling require in that subtree — so any write of `open_asks` from there would be a
// second WRITER PROCESS into `heart.db`, which §7's "one writer path per row" forbids for exactly
// the reason the wall exists. Both rules were right and the spec row had no legal implementation.
//
// The owner ruled option (a) on 2026-08-24: ask-writes get their own gateway intent, the bridge
// sends the record through it, and the daemon stamps the table. This module is the daemon half.
// The twelfth intent (`record-bus-answer`) set that pattern and cites its own ruling the same way.
//
// ⚑ THE BRIDGE HOLDS NO STORE HANDLE AND STILL DOES NOT. It makes ONE gateway call per act; the
// `heart.db` write is HERE, in the process that already owns the file. Same shape
// `chat/bus-answer.js` takes for `coordination/messages.md` and `live-sessions.js` takes for the
// warm-session manager: the bridge keeps a caller, the capability stays server-side.
//
// ⚑ THE ASK BODY IS NOT A STORE COLUMN, AND THAT IS THE SPEC'S SHAPE, NOT A SHORTCUT. §3's
// `evidence_pointer` is "thread permalink / on-disk reply copy". This module writes the copy —
// one file per ask under the goal's own `coordination/asks/` — and stores its path, so the
// boot-prompt re-inject and the owed-answers digest still have words to show while the STATE of
// the ask lives in exactly one place. Deleting the body would have made the digest useless;
// adding a column would have put the body in the store the spec keeps free of it.
//
// ⚑ `ask_id` IS THE SLACK THREAD [T5-R7]. No allocator, no per-seat queue. A second owner message
// in a thread that already carries an open ask is the SAME ask — the copy is refreshed and the row
// is left alone — because the release rule [D-4-ruling, T1-R12] binds an authorized reply to THAT
// EXACT thread. The pre-D89 "settle the oldest open ask" rule is deleted with the file that needed
// it: it is how a reply to one question closed a different one.
//
// ⚑ REFUSALS COME BACK AS DATA, never as a throw, for `handleRecordBusAnswer`'s reason: the
// owner's message has ALREADY been delivered by the time the bridge calls, so the caller's job on
// this result is to LOG. A typed error would report a landed message as a failed one.
//
// ⚑ EVERY ACT RESOLVES THE ENDING STORE ITSELF AND TAKES NO STORE HANDLE FROM ITS CALLER — the
// fix `919be192` (`heart/pause-resume.js`) landed for the same table family, restated here because
// `open_asks` lived in this file with the same defect and unmeasured: `openAsk`/`reapAsk`/
// `listOpenAsks` used to `bind(heartStore.db)`, the store the CALLER happened to hold. Under the
// daemon that is `dispatch.js`'s `heartStore`, the PRIVATE per-process lane store
// (`{data_root}/heart.db`); `open_asks` is one of the four tables `state-store/open.js` states its
// ending-store handle is for (`seat_endings`, `goal_states`, `open_asks`, `seat_holds`), resolved at
// `<workspace>/.rbtv/runtime/ignite/heart.db` by `state-store/paths.js#endingStorePath`. A row
// written or read through the caller's own store therefore missed the table the ask actually lives
// in whenever the caller's store was not already the ending store — exactly the daemon's shape, and
// exactly why `state-store/heart/start-execution.js#refuseReason`'s `getAsk` (the approval check)
// could find nothing for an ask opened through this door. `bindEnding` (the READER's fall-through
// resolver in `supervisor/ending-reads.js`) is not reused here for the reason `pause-resume.js`
// gives: it falls through to the lane store when the home cannot be opened, which is fail-safe for
// a reader and wrong for a writer — a writer must throw instead. `openEndingStoreFor` is the one
// resolver both sides spend.

const fs = require('node:fs');
const path = require('node:path');
const { bind, openEndingStoreFor } = require('..');

// A THIRD copy of the name shape, checked against the module that owns it, exactly as
// `bus-answer.js` re-checks the gateway's and dispatch's copies. These names arrive from an
// internet-facing component and become PATH SEGMENTS under `.rbtv/goals/`.
const { isSafeName } = require('../../chat/bus-ferry');

const ASK_LABELS = ['work-content', 'recovery'];

// `YYYY-MM-DD HH:MM`, local clock, no seconds — the format `coord.age_of()` parses. An ISO stamp
// would read as unparseable ('?') on the Python side, which is where the digest renders it.
function coordTimestamp(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// A Slack ts (`1723480000.123456`) is safe as a name but not guaranteed to be, and this becomes a
// FILENAME. Sanitized for the path; the ROW always carries the raw id, so the two never diverge as
// an address.
function askCopyPath(workspaceRoot, goal, askId) {
  const safe = String(askId).replace(/[^A-Za-z0-9._-]/g, '_');
  return path.join(workspaceRoot, '.rbtv', 'goals', String(goal), 'coordination', 'asks', `${safe}.txt`);
}

function goalDirOf(workspaceRoot, goal) {
  return path.join(workspaceRoot, '.rbtv', 'goals', String(goal));
}

// Every reason a record must NOT be written, as a refusal object — the questions the gateway holds
// no handle for and must not grow one: does the goal exist on disk, are the names safe, is the
// label in the closed set.
function refuseReason({ workspaceRoot, goal, seat, thread, label, act }) {
  for (const [field, value] of [['goal', goal], ['seat', seat], ['thread', thread]]) {
    if (!isSafeName(value)) return { reason: 'bad-name', detail: `${field} is not a bare safe name` };
  }
  if (act === 'open' && !ASK_LABELS.includes(label)) {
    return { reason: 'bad-label', detail: `label must be one of ${ASK_LABELS.join(' | ')}` };
  }
  if (!fs.existsSync(goalDirOf(workspaceRoot, goal))) {
    return { reason: 'no-such-goal', detail: `no goal folder for ${goal}` };
  }
  return null;
}

// OPEN — insert the row and mark it POSTED in the same call.
//
// ⚠ POSTED AT INSERT, and that is a fact about the caller, not an assumption: the bridge records an
// ask only after its forward landed (`forward-path.js` gates on `outcome.forwarded === true`). §2.1
// reads `posted`, so a row left at 0 would be an ask NOBODY IS WAITING ON — the exact silent state
// this record exists to prevent.
function openAsk({ workspaceRoot, goal, seat, thread, corpus, label = 'work-content' }) {
  const refusal = refuseReason({ workspaceRoot, goal, seat, thread, label, act: 'open' });
  if (refusal) return { recorded: false, ...refusal };
  const copy = askCopyPath(workspaceRoot, goal, thread);
  try {
    fs.mkdirSync(path.dirname(copy), { recursive: true });
    fs.writeFileSync(copy, String(corpus || ''));
  } catch (err) {
    return { recorded: false, reason: 'copy-unwritable', detail: err.message };
  }
  try {
    const api = bind(openEndingStoreFor(workspaceRoot));
    const existing = api.getAsk(String(thread));
    if (existing) {
      // Same thread, same ask. The body was refreshed above; the ROW is untouched so a reopened
      // conversation cannot resurrect an ask the owner already answered.
      return { recorded: true, ask_id: existing.ask_id, state: existing.state, already: true };
    }
    api.insertAsk({
      ask_id: String(thread),
      goal: String(goal),
      seat: String(seat),
      label,
      evidence_pointer: copy,
    });
    const posted = api.postAsk({ ask_id: String(thread), posted_at: coordTimestamp() });
    return { recorded: true, ask_id: posted.ask_id, state: posted.state, already: false };
  } catch (err) {
    return { recorded: false, reason: 'store-refused', detail: err.message };
  }
}

// REAP — resolution reaps the row and signals the bound seat's relaunch in ONE transaction (§2.8),
// so there is never an open ask whose seat was already released, nor a release whose ask stayed
// open. Idempotent on `ask_id`: a crash mid-act retries the same reap.
function reapAsk({ workspaceRoot, goal, seat, thread }) {
  const refusal = refuseReason({ workspaceRoot, goal, seat, thread, act: 'reap' });
  if (refusal) return { recorded: false, ...refusal };
  try {
    const api = bind(openEndingStoreFor(workspaceRoot));
    const row = api.getAsk(String(thread));
    if (!row) return { recorded: false, reason: 'no-such-ask', detail: `no ask on thread ${thread}` };
    // BOUND TO THE THREAD **AND** TO THE PAIR IT NAMES. A reply arriving in a thread that belongs
    // to a different goal or seat must not settle this one — the thread is the address, but the
    // address is checked against what the caller claims it is answering.
    if (String(row.goal) !== String(goal) || String(row.seat) !== String(seat)) {
      return { recorded: false, reason: 'ask-not-bound-here', detail: `thread ${thread} belongs to ${row.goal}/${row.seat}` };
    }
    const out = api.reapAndRelaunch({ ask_id: String(thread), authorized_reply_at: coordTimestamp() });
    return {
      recorded: true,
      ask_id: String(thread),
      state: out.ask ? out.ask.state : 'closed',
      idempotent: !!out.idempotent,
      relaunch: out.relaunch || null,
    };
  } catch (err) {
    return { recorded: false, reason: 'store-refused', detail: err.message };
  }
}

// ── THE FLEET READ THE 2-HOURLY DIGEST RENDERS (`spec-owner-io` §5) ───────────────────────────
//
// `inspect asks` — a READ-ONLY TARGET of the existing intent, never a fifteenth one (the ce-5/D3
// rule this daemon states twice: read-only store queries are what `inspect` is for). The chat
// bridge is walled off from `heart.db` exactly as it is on the write side, so the digest's
// `readOpenAsks` port is one ordinary gateway call and the read stays in the process that owns the
// file — the same division the thirteenth intent's write half already carries.
//
// ⚠ THE ONE-LINER COMES FROM THE ASK COPY, NOT FROM A NEW COLUMN. §3 keeps the ask BODY out of the
// store and names `evidence_pointer` as the on-disk copy; `openAsk` above writes it. Reading the
// first line back here is what lets the digest render words without the store growing the column
// the spec deliberately does not have.
//
// ⚠ THE ROW SHAPE IS THE DIGEST'S DOCUMENTED PORT — `{ id, seat, one_liner, opened_at, … }`
// (`chat/system-digest.js` § readOpenAsks). `id` is the ask id (the Slack thread [T5-R7])
// and `opened_at` is `posted_at`, because §5 measures how long the OWNER has been waiting, which
// starts when the ask reached them.
const ONE_LINER_MAX = 120;

function oneLinerOf(evidencePointer) {
  if (!evidencePointer) return null;
  let text;
  try {
    text = fs.readFileSync(String(evidencePointer), 'utf8');
  } catch {
    // The row stands without words rather than with invented ones: the digest renders id + seat and
    // the Links section still names the path a human can open.
    return null;
  }
  const first = text.split('\n').map((l) => l.trim()).find((l) => l !== '');
  if (!first) return null;
  return first.length > ONE_LINER_MAX ? `${first.slice(0, ONE_LINER_MAX - 1)}…` : first;
}

function listOpenAsks(workspaceRoot) {
  const api = bind(openEndingStoreFor(workspaceRoot));
  return api.listAllOpenAsks({}).map((row) => ({
    id: row.ask_id,
    goal: row.goal,
    seat: row.seat,
    label: row.label,
    one_liner: oneLinerOf(row.evidence_pointer),
    opened_at: row.posted_at,
    evidence_pointer: row.evidence_pointer,
  }));
}

function recordOwnerAsk(payload) {
  return payload.act === 'reap' ? reapAsk(payload) : openAsk(payload);
}

module.exports = { recordOwnerAsk, openAsk, reapAsk, listOpenAsks, askCopyPath, coordTimestamp, ASK_LABELS };
