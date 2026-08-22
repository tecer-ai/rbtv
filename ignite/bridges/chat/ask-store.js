'use strict';

// ask-store — the durable record of an owner ask to a goal's `goal-master` that has not yet been
// answered (D57/D75). ONE writer (this module, called from the bridge); coord.py's `boot_prompt`
// and `owed-answers.py` read the same file read-only — see their own headers for why.
//
// Storage is a plain JSON file at `{goalDir}/coordination/owner-asks.json`, keyed by seat name
// (today only ever `goal-master`). This is a DELIBERATE placeholder for the owner's still-open
// storage-location ruling (bridge state vs heart.db) — every caller goes through this interface,
// so the location can move without touching a caller.
//
// Timestamps use coord.py's own `now()` format (`YYYY-MM-DD HH:MM`, local clock, no seconds) so
// `coord.age_of()` can parse them — an ISO timestamp would silently read as unparseable ('?') on
// the Python side.

const fs = require('node:fs');
const path = require('node:path');

function coordTimestamp(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function storePath(workspaceRoot, goalId) {
  return path.join(workspaceRoot, '.rbtv', 'goals', String(goalId), 'coordination', 'owner-asks.json');
}

function readStore(p) {
  try {
    const raw = fs.readFileSync(p, 'utf8');
    const parsed = JSON.parse(raw);
    return (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) ? parsed : {};
  } catch {
    return {};
  }
}

function writeStore(p, store) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  const tmp = `${p}.tmp-${process.pid}-${coordTimestamp().replace(/[^0-9]/g, '')}`;
  fs.writeFileSync(tmp, JSON.stringify(store, null, 2));
  fs.renameSync(tmp, p);
}

// Create or REPLACE the open ask for `seat` in `goalId`'s package. One open ask per seat at a
// time (Q4, surfaced not built — a second ask before the first is answered overwrites the first,
// matching thread-map's existing one-conversation-per-channel model).
function createAsk({ workspaceRoot, goalId, seat, chatThreadId, text, execId = null }) {
  const p = storePath(workspaceRoot, goalId);
  const store = readStore(p);
  const entry = {
    seat: String(seat),
    goalId: String(goalId),
    chatThreadId: chatThreadId != null ? String(chatThreadId) : null,
    text: String(text || ''),
    execId: execId != null ? String(execId) : null,
    status: 'open',
    askedAt: coordTimestamp(),
    answeredAt: null,
    lastReinjectedAt: null,
  };
  store[seat] = entry;
  writeStore(p, store);
  return entry;
}

// Mark `seat`'s currently-open ask answered. A no-op (returns null) when there is nothing open —
// idempotent, and it never re-opens or invents a record for a reply nobody asked for.
function markAnswered({ workspaceRoot, goalId, seat }) {
  const p = storePath(workspaceRoot, goalId);
  const store = readStore(p);
  const entry = store[seat];
  if (!entry || entry.status !== 'open') return null;
  entry.status = 'answered';
  entry.answeredAt = coordTimestamp();
  writeStore(p, store);
  return entry;
}

function getAsk({ workspaceRoot, goalId, seat }) {
  const p = storePath(workspaceRoot, goalId);
  const store = readStore(p);
  return store[seat] || null;
}

module.exports = { storePath, createAsk, markAnswered, getAsk, coordTimestamp };
