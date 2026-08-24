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
  const api = bindEnding(heartStore);
  const seats = [...last.keys()];
  const endingMap = endings || endingsForSeats(api, gid, seats);

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
        if (readyAnswer.ready && readyAnswer.ready.has(seat)) continue;
        pending.push(seat);
      }
    }
  }

  const classA = [];
  for (const [seat, sessionRow] of last) {
    if (dead.has(seat)) continue;
    if (summonedSet.has(seat)) continue;
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
    classA,
    classB,
    classE,
    seats: [...last.keys()],
    live: [...liveSet],
    queued: [...queuedSet],
    owed: classA.length > 0 || classB.length > 0,
  };
}

module.exports = { classifyEnding, classifyOwed, endingsForSeats };
