'use strict';

// The keystroke audit (owner rulings D92/D93) — the record `send-to-session` MUST write.
//
// WHY THIS EXISTS: the daemon mediates keystrokes instead of handing a caller a direct pty
// because mediation preserves an AUDIT POINT. Until p6-3a that justification was unbacked —
// `send-to-session` wrote no record at all. D92 ruled the record mandatory; D93 ruled its shape.
//
// THE SHAPE (D93, ruled — do NOT redesign it):
//   • An APPEND-ONLY per-session FILE beside the session's existing output log, following the
//     pty host's own `{data_root}/logs/<session-id>.log` watch-tee convention.
//   • NOT a `messages` row: that table's `type` CHECK is closed, and the known unrouted-rescan
//     defect means a browser terminal's thousands of keystroke bursts would degrade the ticker.
//   • NOT a new table.
//
// ⚑ THIS FILE IS ITSELF A NEW SENSITIVE ARTIFACT. Keystrokes are SECRET-BEARING BY NATURE — a
// user may type a password, an API key, or a recovery phrase into a TUI, and this file records
// what they typed, verbatim. It is created 0600 (the mode the ratified prompt-file mechanism
// already uses) and every append RE-VERIFIES the mode fail-closed: if the file has been made
// group/world-accessible, the write is REFUSED rather than appending secrets to a readable file.
// That mirrors the certified `loadSendersFile` posture (a hash file is refused at mode 0077).
//
// ⚑ FAIL-CLOSED IS LOAD-BEARING, NOT DEFENSIVE STYLE. The caller writes the audit BEFORE the
// keystrokes reach the pty, and refuses the send if this throws. Auditing AFTER delivery would
// hand an attacker a real bypass: fill the disk -> the audit write fails -> but the keystrokes
// already landed -> un-audited keystroke injection. Ordered this way, a failed audit means no
// keystrokes were ever delivered.

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

// Append ONE accepted-keystroke record. Throws KeysAuditError on any failure — the caller MUST
// treat a throw as "refuse the send", never as "log and continue".
function appendKeystrokeRecord({ logPath, execId, sessionId, sender, data }) {
  if (typeof logPath !== 'string' || logPath.length === 0) {
    // A live headed session always carries a log_path (the pty host records it at `launching`
    // AND `running`, and reconnect re-derives it). Its absence means the row is not the shape
    // this intent assumes — refuse rather than invent a path and audit somewhere unexpected.
    throw new KeysAuditError('the session row carries no log_path, so the audit file cannot be placed beside its output log', { execId });
  }
  if (!sender || typeof sender.id !== 'string' || sender.id.length === 0) {
    // D93: "A record without sender attribution answers none of the questions this exists to
    // answer." An unattributable record is worse than none — refuse.
    throw new KeysAuditError('no authenticated sender to attribute the keystrokes to', { execId });
  }

  const auditPath = auditPathFor(logPath);

  // Create at 0600 if absent. `mode` applies at CREATION only, so it cannot tighten a file that
  // already exists — which is exactly what the mode re-check below is for.
  try {
    fs.appendFileSync(auditPath, '', { mode: AUDIT_MODE });
  } catch (err) {
    throw new KeysAuditError(`cannot open the keystroke audit at ${auditPath}: ${err.message}`, { execId, auditPath });
  }

  // ⚑ RE-VERIFY THE MODE ON EVERY APPEND, fail-closed. If anything loosened the file after
  // creation, appending verbatim keystrokes to it would leak whatever the user typed — possibly
  // a credential — to any local reader. Refuse instead. (A stat is negligible against a pty write.)
  let mode;
  try {
    mode = fs.statSync(auditPath).mode & 0o777;
  } catch (err) {
    throw new KeysAuditError(`cannot stat the keystroke audit at ${auditPath}: ${err.message}`, { execId, auditPath });
  }
  if (mode & 0o077) {
    throw new KeysAuditError(
      `REFUSING TO AUDIT: the keystroke audit at ${auditPath} is group/world-accessible (mode ${mode.toString(8)}); ` +
      `keystrokes are secret-bearing and MUST NOT be appended to a readable file. Fix with: chmod 600 ${auditPath}`,
      { execId, auditPath, mode: mode.toString(8) },
    );
  }

  // `data` is recorded VERBATIM as a JSON string, not base64: JSON.stringify already escapes the
  // newlines, carriage returns, and control/escape bytes a keystroke burst carries, so the
  // line-oriented format stays intact with NO information lost — and the record stays readable to
  // the human auditor this exists for. `bytes` is the wire-truthful byte length (not .length,
  // which would under-count any multi-byte character).
  const record = {
    ts: new Date().toISOString(),
    event: 'keys-accepted',
    id: execId,
    session_id: sessionId ?? null,
    sender_id: sender.id,
    sender_kind: sender.kind ?? null,
    via: sender.via ?? null,
    bytes: Buffer.byteLength(data, 'utf8'),
    data,
  };

  try {
    fs.appendFileSync(auditPath, JSON.stringify(record) + '\n', { mode: AUDIT_MODE });
  } catch (err) {
    throw new KeysAuditError(`cannot append to the keystroke audit at ${auditPath}: ${err.message}`, { execId, auditPath });
  }

  return { auditPath, bytes: record.bytes };
}

module.exports = { appendKeystrokeRecord, auditPathFor, KeysAuditError, AUDIT_SUFFIX, AUDIT_MODE };
