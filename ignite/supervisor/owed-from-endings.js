'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { bindEnding, endingOf, goalNameOf } = require('./ending-reads');
const counters = require('./attempt-counters');
const { loadRecoveryConfig } = require('./recovery-config');

// -- THE CHAIR'S READ CURSOR - workers.md's `lastread` column ------------------------------------
//
// WHAT WAS BROKEN. `checkinOf` marked WHEN THE CHAIR ARRIVED, not what it read, at MINUTE
// granularity (`sessions.csv`'s `checkin` column). Check-in and `coordinate read` land in the same
// daemon-lane sitting, seconds apart - so a message stamped in that same minute read as "after
// check-in" and was filed READ FOREVER, even when the sitting died before ever calling `read`.
// Merely checking in discharged the wake; nothing verified the mail was shown, let alone acted on.
//
// THE CURSOR IS THE ONE FACT THAT SAYS SO. `coordinate read` (coord/records.py `cmd_read` +
// `persist_cursor`) advances the chair's OWN roster row - `workers.md`'s `lastread` cell - past the
// LAST MESSAGE IT WAS ACTUALLY SHOWN, and by nothing else: `coordinate checkin` never touches it.
// Comparing a message's own number against that cursor is exact (an integer either is or is not
// past another integer) where a minute-stamp comparison could only ever be approximate - and it is
// resolution the checkin timestamp cannot manufacture, because checking in and reading are two
// different acts the old comparison conflated into one.
//
// A chair with no roster row, an unreadable file, or a blank/non-numeric cursor is owed ALL its
// mail - the same "no evidence of a read yet" default `checkinOf` used for a chair with no session.
//
// ⚠ 2026-08-30 LIVE DEFECT, deployed daemon 26773c34: `workers.md` carries ONE ROW PER SITTING,
// append-only — `coord/checkout.py#cmd_checkin` appends a fresh row on every check-in and never
// rewrites an old one (`coord/messages.py#current_row`: "Latest row for an agent (last check-in
// wins)", `mine[-1]` — the LAST match in file order). A first version of this function returned on
// the FIRST matching row instead, which on `meet-transcript-summarizer-planning` (8 leader rows)
// answered the FIRST sitting's cursor (0) instead of the newest sitting's (25): every message
// #1-#25 read as unread on every pass, and the leader was relaunched twice (cf59debf 17:57Z,
// c82409d8 18:02Z) with no new mail before the orchestrator placed a `supervise hold` at 18:04Z.
//
// THE FIX READS THE SAME INVARIANT `cmd_checkin` WRITES. Check-in never starts a new row at 0: it
// scans every PRIOR row of the SAME agent and inherits `max(prior lastread values)` onto the new
// row (`checkout.py` "the new row inherits the highest cursor any prior row of the SAME agent
// reached"). So the cursor is a SEAT-level fact, monotonic across that seat's sittings, and the
// newest row's own value is authoritative whenever it is numeric. A non-numeric/blank cursor on
// the newest row (a row written by something other than `cmd_checkin` - the only writer this
// invariant binds) falls back to the highest number ANY earlier row of the same chair reached,
// because that number is still the seat's last known truth; only a chair with NO numeric cursor
// anywhere in its history is owed ALL its mail (`null`).
const WORKER_ROW = /^\|\s*([^|]+?)\s*\|\s*(?:yes|no)\s*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*([^|]*?)\s*\|$/;

function workersPath(goalFolder) {
  const coord = path.join(goalFolder, 'coordination', 'workers.md');
  if (fs.existsSync(coord)) return coord;
  return path.join(goalFolder, 'workers.md');
}

// -- THE FINISH EVENT (canonical source for "was it DECLARED finished?") --------------------------
//
// The lease answers "is it EXECUTING?" from the room and MUST stay blind to this event
// (`probe-finish-edge.py` F5, `d-extinguishment-design-lock`). Watchers read THIS marker, never
// `goal_states.stored='finished'` (`isGoalFinished`): live heart.db has zero such rows, and
// existing finished goals already carry the append-only completion. Byte-identical to
// `coord/records.py` FINISH_MARKER (PIN in owed-from-endings.selftest.js).
const FINISH_MARKER = 'goal-finished: the finish edge fired';

function finishMessagesPath(goalFolder) {
  const coord = path.join(goalFolder, 'coordination', 'messages.md');
  if (fs.existsSync(coord)) return coord;
  return path.join(goalFolder, 'messages.md');
}

function finishEvent(goalFolder) {
  if (!goalFolder) return false;
  let text;
  try { text = fs.readFileSync(finishMessagesPath(goalFolder), 'utf8'); } catch { return false; }
  for (const block of text.split(/^## /m)) {
    const nl = block.indexOf('\n');
    const header = nl === -1 ? block : block.slice(0, nl);
    if (!/\|\s*type:\s*completion\s*\|/.test(header)) continue;
    const body = (nl === -1 ? '' : block.slice(nl)).trim();
    if (body.startsWith(FINISH_MARKER)) return true;
  }
  return false;
}

function readCursor(goalFolder, chair) {
  let text;
  try { text = fs.readFileSync(workersPath(goalFolder), 'utf8'); } catch { return null; }
  let newestValue = null; // the LAST matching row's own cell, numeric or not (null if not numeric)
  let bestNumeric = null; // the highest numeric cursor this chair's history has ever reached
  for (const line of text.split('\n')) {
    const m = line.match(WORKER_ROW);
    if (!m || m[1] !== chair) continue;
    const numeric = /^\d+$/.test(m[2]) ? Number(m[2]) : null;
    newestValue = numeric;
    if (numeric !== null && (bestNumeric === null || numeric > bestNumeric)) bestNumeric = numeric;
  }
  // The newest row's own value wins whenever it is numeric — it is what `cmd_checkin`/`persist_
  // cursor` last wrote for THIS sitting. Only a non-numeric newest row falls back to history.
  return newestValue !== null ? newestValue : bestNumeric;
}

// -- THE ATTEMPT-COUNTER BRAKE, READ AT THE WAKE ITSELF -----------------------------------------
//
// `reconcile.js` already KEYS a class B relaunch on this same ledger — `driverFor('unread') ===
// RECONCILE_RESPAWN`, `subject: '<goal>/<chair>'`, `reasonClass: 'unread'`, `items: ['#<lastNum>']`
// (`reconcile.js:983-991,1187-1206`) — and WRITES the attempt on every pass a wake fires. What it
// does not do is stop the WAKE itself from being reported: its own `counterDisarmed` gate compares
// only `attempts >= n`, with no frontier check, so it cannot tell "the same stale mail, N times" from
// "brand new mail that happens to land on an exhausted lane" — and a caller of `deriveOwed` other
// than `reconcile.js`'s own launch loop sees `owed: true` regardless. This reads the SAME ledger,
// SAME key, at the point class B decides a chair is owed at all, and adds the ONE check
// `counterDisarmed` is missing: whether the exhausted attempts were spent on THIS EXACT frontier.
//
// KEYED IDENTICALLY TO THE WRITER, ON PURPOSE. `driver`/`subject`/`reasonClass` here are the exact
// three fields `attempt-counters.js#keyOf` hashes into one string - a caller that spells any of them
// differently reads a DIFFERENT counter and this brake would never see what `reconcile.js` wrote.
//
// THE RESET IS THE FRONTIER, NOT A NEW EVENT. `attempts >= n` alone never expires - only a named
// `RE_ARM_EVENT` clears the row (spec-recovery §5), and this function must NOT invent a second
// clock beside it. So exhaustion only SUPPRESSES the wake when the current unread frontier
// (`#<lastNum>`) is the SAME one recorded on the row (`row.owed_items`, `countAttempt`'s own
// overlap marker) - a chair whose mail advanced past the exhausted item is owed a first attempt at
// different work, exactly as `countAttempt`'s own `isRetryOf` already treats it, and this function
// re-derives that same test rather than trusting `attempts` alone. `rearm` (`resume {goal}`, a
// code-deploy, a config change, an owner/leader act) deletes the row outright, so the very next
// read here answers "not exhausted" with no extra wiring - the same re-arm list, unchanged.
//
// `n` comes from `recovery-config.js`, never a literal: a workspace whose recovery config cannot be
// read applies no clock here either, matching `reconcile.js#recoveryNumbers`'s own rule - a brake
// that cannot verify its own threshold must not silently suppress a real wake.
function unreadFrontierExhausted(goal, chair, lastNum, countersFile) {
  let n;
  try {
    n = loadRecoveryConfig({ workspace: process.env.RBTV_IGNITE_WORKSPACE_ROOT }).attempt_counter_n;
  } catch {
    return false;
  }
  const row = counters.peekCounter(
    { driver: counters.DRIVERS.RECONCILE_RESPAWN, goal, seat: chair, reasonClass: 'unread' },
    { countersFile },
  );
  if (!row || !(Number(row.attempts) >= n)) return false;
  const recorded = Array.isArray(row.owed_items) ? row.owed_items : [];
  return recorded.includes(`#${lastNum}`);
}

function classifyEnding(row) {
  if (!row || !row.ending) return null;
  if (row.ending === 'done') return null;
  if (row.ending === 'incomplete' && Number(row.armed) === 1) {
    return { reason: 'incomplete', ending: row.ending };
  }
  if (row.ending === 'incomplete' && Number(row.armed) === 0) return null;
  if (row.ending === 'failed') return { reason: 'nonterm', ending: row.ending };
  return null;
}

// ── THE LEADER'S HOLD, HONOURED WHERE THE RELAUNCH IS DECIDED ─────────────────────────────────
//
// WHAT WAS BROKEN. `classifyEnding` below turns any `failed` ending into a `nonterm` owed row, and
// `reconcile.js:953-969` answers a `nonterm` row by launching the LEADER to rule it — every ~5-min
// pass, for as long as the row stays `failed`. The leader's two ruling acts (`supervise accept`,
// `supervise instruct`) both END the row, so they stop the wake. Its THIRD legitimate verdict —
// "hold, this is waiting on the owner" — was a message and nothing else: invisible here, and so
// indistinguishable from a sitting that did nothing. Each pass therefore counted the HOLD as a
// burned attempt (`reconcile.js:1165-1178`), N=3 disarmed the lane, and the next code-deploy
// re-arm wiped the counter and bought three more. Nine identical HOLD verdicts on
// `goal-memory-management`, 2026-08-28, nine paid opus-5 sittings, nothing honoured.
//
// WHAT THIS IS. A seat under a LIVE hold (`state-store/predicates.js#seatHeld`, over the
// `seat_holds` row `supervise hold` writes into the ONE workspace ending store) is not class A at
// all — the same shape `dead` and `summoned` seats already have below. No class A row means no
// launch target, which means no leader launch AND no attempt counted: the two follow from one
// exclusion rather than from two agreeing rules.
//
// ⚠ THE EXCLUSION IS THE SEAT'S, NOT THE REASON CLASS'S. A hold says "the leader has ruled this
// row: do not re-drive it until <named change>", and that is as true of an `armed incomplete`
// relaunch of the seat itself as of the leader wake over its `failed` row, AND of a class-B
// relaunch driven by unread mail: mail addressed to a held chair does not un-hold the chair, and
// a chair the leader has told the daemon not to re-drive must not be re-driven because someone
// sent it a message. ⚠ 2026-08-30 LIVE DEFECT, deployed daemon 26773c34: class B skipped this
// check — `heldExcluded` named `leader:until release` on the SAME pass that `classB` also named
// `leader` and launched it (sittings `ed9ffb12`, `e60bb439`, `meet-transcript-summarizer-planning`)
// — because the two classes independently reasoned about the same exclusion instead of sharing it.
//
// ⚠ IT IS EVALUATED EVERY PASS AND CLEARS ITSELF. `seatHeld` returns null the moment the named
// change is observed, so the row is class A again on that pass with no sweep, no watcher and no
// write — and the leader gets ONE sitting to re-rule it, not three.
function heldSeats(api, goal, seats) {
  const out = new Map();
  if (!api || typeof api.seatHeld !== 'function') return out;
  for (const seat of seats) {
    const hold = api.seatHeld({ goal, seat });
    if (hold) out.set(seat, hold);
  }
  return out;
}

// ── THE LANE'S ABANDONMENT, HONOURED WHERE THE OWED SET IS DECIDED ───────────────────────────────
//
// `d-recovery-abandoned-is-an-ending` (owner ruling, 2026-08-31): `drop-lane` retires ONE lane
// `(goal, seat)` forever — no undo, from Slack or a terminal. It is recorded over
// `state-store/tables.sql`'s `seat_abandonments` (a sibling table beside `seat_endings`, for the
// same reasons `seat_holds` already is one: the live CHECK on `seat_endings.ending` cannot be
// widened after the fact, and a re-stamp would archive the fact away). A seat with a row here is
// not class A, class B, or the `pending` frontier at all — the same shape `dead`, `summoned`, and
// `held` already have below. No owed row means no relaunch and no attempt counted, from one
// exclusion rather than a rule taught separately to each of the three loops.
//
// ⚠ THIS IS UNCONDITIONAL, UNLIKE A HOLD. A hold clears itself on a named change (`seatHeld`
// re-evaluates a release condition every pass); an abandonment never does — the row's mere presence
// IS the answer, permanently, so there is no matching "still abandoned?" liveness check to run.
function abandonedSeats(api, goal, seats) {
  const out = new Map();
  if (!api || typeof api.getSeatAbandonment !== 'function') return out;
  for (const seat of seats) {
    const row = api.getSeatAbandonment({ goal, seat });
    if (row) out.set(seat, row);
  }
  return out;
}

function endingsForSeats(api, goal, seats) {
  const out = new Map();
  if (!api) return out;
  for (const seat of seats) {
    const row = endingOf(api, goal, seat);
    if (row) out.set(seat, row);
  }
  return out;
}

function classifyOwed(goalFolder, {
  readyAnswer = null,
  live = null,
  queued = null,
  summoned = null,
  heartStore = null,
  endings = null,
  goal = null,
  loadSessions,
  loadMessages,
  lastBySeat,
  liveSeatsFromLedgers,
  // ⚠ `checkinOf`/`tsAfter` are UNUSED by this function's own body now (class B reads the chair's
  // read cursor below, never the checkin timestamp) but MUST STAY IN THE DESTRUCTURE: reconcile
  // .selftest.js's F-1 red-mutation splices a line calling `tsAfter(...)` verbatim into this
  // function's own source and re-compiles it, relying on `tsAfter` resolving through THIS closure.
  // Dropping either name here is invisible to every other test and breaks only that mutant.
  checkinOf,
  tsAfter,
  STAFF_CHAIRS,
  SYSTEM_MAIL_SENDER,
  countersFile,
} = {}) {
  if (finishEvent(goalFolder)) {
    return {
      readyRefused: null,
      deadSeats: [],
      summonedSeats: [],
      heldSeats: [],
      abandonedSeats: [],
      classA: [],
      classB: [],
      classE: null,
      seats: [],
      live: [],
      queued: [],
      owed: false,
      finished: true,
    };
  }
  const sessions = loadSessions(goalFolder);
  const messages = loadMessages(goalFolder);
  const last = lastBySeat(sessions);
  const liveSet = live || liveSeatsFromLedgers(sessions);
  const queuedSet = queued || new Set();
  const summonedSet = summoned || new Set();
  const gid = goalNameOf(goalFolder, goal);
  const api = bindEnding(heartStore, goalFolder);
  const seats = [...last.keys()];
  const endingMap = endings || endingsForSeats(api, gid, seats);
  const holdMap = heldSeats(api, gid, seats);
  const abandonedMap = abandonedSeats(api, gid, seats);

  const dead = new Set();
  let readyRefused = null;
  let readyCount = 0;
  const pending = [];
  if (readyAnswer) {
    if (readyAnswer.reason && readyAnswer.ready === null) {
      readyRefused = readyAnswer.reason;
    } else {
      for (const r of readyAnswer.rows || []) {
        if (!r || !r.seat) continue;
        if (r.dead === true) dead.add(r.seat);
      }
      readyCount = readyAnswer.ready ? readyAnswer.ready.size : 0;
      for (const seat of seats) {
        const row = endingMap.get(seat);
        if (row && row.ending === 'done') continue;
        if (dead.has(seat)) continue;
        // A HELD seat is not an unexplained frozen frontier: the reason it is not advancing is
        // recorded, named and owner-visible. Class E exists to surface a frontier NOBODY explained.
        if (holdMap.has(seat)) continue;
        // An ABANDONED seat is not an unexplained frozen frontier either — the owner explained it
        // permanently, by dropping the lane.
        if (abandonedMap.has(seat)) continue;
        if (readyAnswer.ready && readyAnswer.ready.has(seat)) continue;
        pending.push(seat);
      }
    }
  }

  const classA = [];
  for (const [seat, sessionRow] of last) {
    if (dead.has(seat)) continue;
    if (summonedSet.has(seat)) continue;
    if (holdMap.has(seat)) continue;
    if (abandonedMap.has(seat)) continue;
    const ended = (sessionRow.ended || '').trim();
    if (!ended) continue;
    const classified = classifyEnding(endingMap.get(seat));
    if (!classified) continue;
    classA.push({
      seat,
      ending: classified.ending,
      ended,
      reason: classified.reason,
    });
  }
  classA.sort((x, y) => (x.seat < y.seat ? -1 : x.seat > y.seat ? 1 : 0));

  const classB = [];
  for (const chair of STAFF_CHAIRS) {
    if (dead.has(chair)) continue;
    if (summonedSet.has(chair)) continue;
    if (holdMap.has(chair)) continue;
    if (abandonedMap.has(chair)) continue;
    if (liveSet.has(chair) || queuedSet.has(chair)) continue;
    const cursor = readCursor(goalFolder, chair);
    const unread = messages.filter((m) => m.to === chair && m.sender !== chair
      && m.sender !== SYSTEM_MAIL_SENDER
      && (cursor === null || m.num > cursor));
    if (!unread.length) continue;
    const lastNum = unread[unread.length - 1].num;
    if (unreadFrontierExhausted(gid, chair, lastNum, countersFile)) continue;
    classB.push({
      seat: chair,
      unreadCount: unread.length,
      lastNum,
      reason: 'unread',
    });
  }

  const moving = liveSet.size > 0 || queuedSet.size > 0;
  const classE = (!readyRefused && readyCount === 0 && pending.length && !moving)
    ? { pending: pending.slice().sort(), ready: 0 }
    : null;

  return {
    readyRefused,
    deadSeats: [...dead],
    summonedSeats: [...summonedSet],
    heldSeats: [...holdMap.values()].map((h) => ({
      seat: h.seat, until: h.until, ask_id: h.ask_id, anchor: h.anchor, held_by: h.held_by, held_at: h.held_at,
    })),
    abandonedSeats: [...abandonedMap.values()].map((a) => ({
      seat: a.seat, anchor: a.anchor, abandoned_by: a.abandoned_by, abandoned_at: a.abandoned_at, ask_id: a.ask_id,
    })),
    classA,
    classB,
    classE,
    seats: [...last.keys()],
    live: [...liveSet],
    queued: [...queuedSet],
    owed: classA.length > 0 || classB.length > 0,
  };
}

module.exports = {
  classifyEnding, classifyOwed, endingsForSeats, heldSeats, abandonedSeats, readCursor, workersPath,
  finishEvent, FINISH_MARKER,
};
