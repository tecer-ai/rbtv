'use strict';

// ask-store — the durable record of owner asks to a goal's `goal-master` that have not yet been
// answered (D57/D75, widened D89 Q4). ONE writer (this module, called from the bridge); coord.py's
// `boot_prompt` and `owed-answers.py` read the same file read-only — see their own headers for why.
//
// Storage is a plain JSON file at `{goalDir}/coordination/owner-asks.json`, keyed by seat name
// (today only ever `goal-master`) — each value a LIST of asks, oldest first (append order), not a
// single object (D89 Q4: a second owner message arriving before the first is answered is QUEUED
// alongside it, never overwrites it). This is still a DELIBERATE placeholder for the owner's
// still-open storage-location ruling (bridge state vs heart.db, Q3) — every caller goes through
// this interface, so the location can move without touching a caller.
//
// A legacy file written by the pre-D89 single-object shape (`store[seat]` = one bare entry, not a
// list) is migrated to a one-element list ON READ — see `readStore`. Every write from this module
// on writes the list shape only; an old file keeps working with no separate migration step.
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

// Returns `{ [seat]: AskEntry[] }`, oldest-first per seat. A seat's value in the raw file may be
// EITHER shape — the current list, or a legacy bare object (one ask, no `id`) written before D89
// Q4 — both normalize to a list here, so every caller below only ever sees the list shape.
function readStore(p) {
  try {
    const raw = fs.readFileSync(p, 'utf8');
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    const store = {};
    for (const [seat, val] of Object.entries(parsed)) {
      let list;
      if (Array.isArray(val)) {
        list = val.filter((e) => e && typeof e === 'object');
      } else if (val && typeof val === 'object') {
        // Legacy pre-D89 shape: one bare entry object per seat, not a list. Migrate in place.
        list = [val];
      } else {
        list = [];
      }
      // Legacy entries (and any hand-written fixture) carry no `id` — assign one from array
      // position. Stable across re-reads because entries are only ever APPENDED, never removed
      // or reordered (an answered ask stays in the list, same as the pre-D89 single-entry store
      // never deleted an answered entry either).
      list.forEach((e, i) => { if (e.id == null) e.id = i + 1; });
      store[seat] = list;
    }
    return store;
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

// Append a new open ask for `seat` in `goalId`'s package. D89 Q4: this NEVER replaces an
// already-open ask — a second, different owner message arriving before the first is answered is
// QUEUED alongside it (both are stored, both re-inject) instead of overwriting the first.
function createAsk({ workspaceRoot, goalId, seat, chatThreadId, text, execId = null }) {
  const p = storePath(workspaceRoot, goalId);
  const store = readStore(p);
  const list = store[seat] || (store[seat] = []);
  const entry = {
    id: list.length + 1,
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
  list.push(entry);
  writeStore(p, store);
  return entry;
}

// Mark ONE of `seat`'s open asks answered. A no-op (returns null) when there is nothing open —
// idempotent, and it never re-opens or invents a record for a reply nobody asked for.
//
// WHICH-ASK RULE (several asks can be open at once under D89 Q4): an explicit `askId` — the ask a
// reply's thread/`--re` names — settles THAT ask; with none supplied, the OLDEST open ask settles.
// The list is append-ordered (oldest first), so "first open entry found" IS the oldest. No caller
// in this build passes `askId` yet — the chat bridge carries no per-ask thread reference today
// (Slack threading here is one thread per goal conversation, not per ask), so every call resolves
// to the oldest-open rule. `askId` exists so a future caller that DOES know which ask a reply
// answers (a `--re`-style reference) can settle that one specifically without widening this
// function's contract again.
function markAnswered({ workspaceRoot, goalId, seat, askId = null }) {
  const p = storePath(workspaceRoot, goalId);
  const store = readStore(p);
  const list = store[seat] || [];
  const entry = askId != null
    ? list.find((e) => e && e.status === 'open' && String(e.id) === String(askId))
    : list.find((e) => e && e.status === 'open');
  if (!entry) return null;
  entry.status = 'answered';
  entry.answeredAt = coordTimestamp();
  writeStore(p, store);
  return entry;
}

// ALL of `seat`'s asks, oldest first — open and answered alike. Empty array when the seat has no
// record. Widened from the pre-D89 single-object-or-null return: a caller that wants only the
// still-open ones filters `status === 'open'` itself (both readers below do exactly that).
function getAsk({ workspaceRoot, goalId, seat }) {
  const p = storePath(workspaceRoot, goalId);
  const store = readStore(p);
  return store[seat] || [];
}

module.exports = { storePath, createAsk, markAnswered, getAsk, coordTimestamp };
