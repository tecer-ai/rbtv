'use strict';

// The session-kill audit (owner ruling, cli-expansion run 2026-07-20) — the record
// `kill-session` MUST write.
//
// ⚑ WHAT THIS FILE WAS, AND WHY THE REMAINDER IS SMALL. It began as the SESSION-SURFACE audit
// (D92/D93, extended to screen reads by D94 and coalesced by task 7.13): the mandatory record
// behind `send-to-session` and `capture-session-screen`. Task 7.29 retired both intents with the
// server-owned pty they drove, and the keystroke appender, the screen-read appender and the
// whole poll-coalescing machine went with them — nothing calls a function whose intent no longer
// exists. `kill-session` did NOT retire, so its record, and the file it appends to, stay.
//
// THE SHAPE (D93, ruled — do NOT redesign it):
//   • An APPEND-ONLY per-session FILE beside the session's existing output log,
//     `{data_root}/logs/<session-id>.log` -> `<session-id>.keys.jsonl`.
//   • NOT a `messages` row: that table's `type` CHECK is closed.
//   • NOT a new table.
//
// ⚑ THE 0600 + FAIL-CLOSED RE-STAT POSTURE STAYS, and it is NOT vestigial. Existing audit files
// on deployed boxes hold verbatim keystrokes written before 7.29 — appending to one that has
// been made group/world-accessible would still expose them. The re-stat refuses that write, the
// same way the certified `loadSendersFile` refuses a hash file at mode 0077.
//
// ⚑ THE `event` FIELD REMAINS THE DISCRIMINATOR. The vocabulary this file can now WRITE is one
// value; the vocabulary a READER may encounter is four, because history is on disk:
//   • `session-killed`      — written here, today.
//   • `keys-accepted` · `screen-read` · `screen-read-summary` — pre-7.29 records. No code writes
//     them any more; any tool that READS this file must still understand them.
//
// The kill record is attribution only — WHO killed WHICH session WHEN, never any payload. Unlike
// the retired keystroke path, it is written AFTER the kill succeeds (the owner-ruled success-path
// placement: a kill delivers no secret whose delivery must be blocked on the audit, and refusing
// a KILL fail-closed would leave a runaway process unkillable behind a full disk). An audit-write
// failure is surfaced as a refusal of the success RESULT, never degraded to log-and-continue —
// dispatch.js's handleKillSession reasons that ordering.

const fs = require('node:fs');
const path = require('node:path');

// Sits BESIDE the session's output log: `<session-id>.log` -> `<session-id>.keys.jsonl`.
// JSON Lines: append-only by construction — one self-contained record per line, no rewrite of
// any earlier byte, and a truncated tail never corrupts the records before it.
const AUDIT_SUFFIX = '.keys.jsonl';
const AUDIT_MODE = 0o600;

class KeysAuditError extends Error {
  constructor(message, details = {}) {
    super(message);
    this.name = 'KeysAuditError';
    this.code = 'E_KEYS_AUDIT';
    this.details = details;
  }
}

// Derived from the ROW's own recorded log_path — the authoritative "existing output log" for
// this session — so the audit needs no second source of truth for data_root and cannot drift
// from where the pty host actually tees the transcript.
function auditPathFor(logPath) {
  const dir = path.dirname(logPath);
  const base = path.basename(logPath, '.log');
  return path.join(dir, `${base}${AUDIT_SUFFIX}`);
}

// Append ONE session-kill record (cli-expansion owner ruling, 2026-07-20). Throws KeysAuditError
// on any failure — the caller surfaces a throw as a refusal of the success result, never as
// "log and continue" (the kill has already happened by the time this is called; the ordering and
// its posture are reasoned at dispatch.js's handleKillSession).
//
// ⚑ THE GUARD SEQUENCE BELOW was the THIRD deliberate copy of the same certified sequence, kept
// unfactored under the extend-don't-disturb order. It is the ONLY copy now — its two siblings
// (the keystroke and screen-read appenders) left with the intents they served at task 7.29. The
// bytes are UNCHANGED: this is a deletion of the other copies, never an edit to this one, and no
// owner grant to extract a shared helper was needed or taken.
function appendKillRecord({ logPath, execId, sessionId, sender }) {
  if (typeof logPath !== 'string' || logPath.length === 0) {
    throw new KeysAuditError('the session row carries no log_path, so the audit file cannot be placed beside its output log', { execId });
  }
  if (!sender || typeof sender.id !== 'string' || sender.id.length === 0) {
    // D93: an unattributable record answers none of the questions this exists to answer — and
    // WHO killed this session is this record's entire content.
    throw new KeysAuditError('no authenticated sender to attribute the kill to', { execId });
  }

  const auditPath = auditPathFor(logPath);

  try {
    fs.appendFileSync(auditPath, '', { mode: AUDIT_MODE });
  } catch (err) {
    throw new KeysAuditError(`cannot open the session audit at ${auditPath}: ${err.message}`, { execId, auditPath });
  }

  // Re-verify the mode fail-closed, exactly as the two paths above do — the screen-read copy's
  // reasoning holds unchanged: this record carries no secret itself, but it appends to the SAME
  // file the verbatim keystroke records live in.
  let mode;
  try {
    mode = fs.statSync(auditPath).mode & 0o777;
  } catch (err) {
    throw new KeysAuditError(`cannot stat the session audit at ${auditPath}: ${err.message}`, { execId, auditPath });
  }
  if (mode & 0o077) {
    throw new KeysAuditError(
      `REFUSING TO AUDIT: the session audit at ${auditPath} is group/world-accessible (mode ${mode.toString(8)}); ` +
      `it carries verbatim keystrokes and MUST NOT be appended to while readable. Fix with: chmod 600 ${auditPath}`,
      { execId, auditPath, mode: mode.toString(8) },
    );
  }

  // ⚑ NO payload data, mirroring the screen-read record: a kill carries no typed secret. The
  // record answers WHO killed WHICH session WHEN — nothing else.
  const record = {
    ts: new Date().toISOString(),
    event: 'session-killed',
    id: execId,
    session_id: sessionId ?? null,
    sender_id: sender.id,
    sender_kind: sender.kind ?? null,
    via: sender.via ?? null,
  };

  try {
    fs.appendFileSync(auditPath, JSON.stringify(record) + '\n', { mode: AUDIT_MODE });
  } catch (err) {
    throw new KeysAuditError(`cannot append to the session audit at ${auditPath}: ${err.message}`, { execId, auditPath });
  }

  return { auditPath };
}

module.exports = {
  appendKillRecord, auditPathFor,
  KeysAuditError, AUDIT_SUFFIX, AUDIT_MODE,
};
