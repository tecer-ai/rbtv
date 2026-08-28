'use strict';

const { bindEnding, endingOf, goalNameOf } = require('./ending-reads');

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
// relaunch of the seat itself as of the leader wake over its `failed` row. Class B is untouched:
// mail to a chair is not the held row, and a held seat must stay reachable.
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
  checkinOf,
  tsAfter,
  STAFF_CHAIRS,
  SYSTEM_MAIL_SENDER,
} = {}) {
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
    if (liveSet.has(chair) || queuedSet.has(chair)) continue;
    const since = checkinOf(last.get(chair));
    const unread = messages.filter((m) => m.to === chair && m.sender !== chair
      && m.sender !== SYSTEM_MAIL_SENDER
      && (!since || tsAfter(m.ts, since)));
    if (!unread.length) continue;
    classB.push({
      seat: chair,
      unreadCount: unread.length,
      lastNum: unread[unread.length - 1].num,
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
  classifyEnding, classifyOwed, endingsForSeats, heldSeats,
};
