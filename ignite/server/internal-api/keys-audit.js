'use strict';

// The session-surface audit (owner rulings D92/D93, EXTENDED to screen reads by D94) — the record
// `send-to-session` and `capture-session-screen` MUST write.
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
//
// ── D94: SCREEN READS ARE AUDITED TOO ────────────────────────────────────────────────────────
//
// WHY: until D94 only the WRITE path wrote a record, so the cheapest way to obtain a typed secret
// was to READ IT OFF THE SCREEN rather than type it — `capture-session-screen` returned the same
// rendered password/API key/recovery phrase the keystroke audit exists to attribute, and left NO
// trace of who took it. An audit that records only half the ways to reach the secret is not an
// audit; D94 closes that bypass by extending WHICH intents write here. The SHAPE is D93's,
// UNCHANGED (same file, same 0600 + fail-closed re-stat, same sender attribution).
//
// ⚑ A READ RECORD CARRIES NO SCREEN CONTENTS, DELIBERATELY. Logging the captured screen would
// write the very secret this exists to protect into the audit ON EVERY POLL — converting an
// ATTRIBUTION record into a BULK SECRET ARCHIVE, and a far better target than the session itself
// (one file, every screen, forever — D95 rules the audit unbounded for v1). The record answers
// WHO read WHICH session WHEN. It never answers WHAT they saw: the transcript tee
// (`<session-id>.log`) already holds the bytes, under the same 0700 `logs/` dir.
//
// ⚑ THE `event` FIELD IS THE READ/WRITE DISCRIMINATOR (D94: "reads MUST be distinguishable from
// writes"). It is the vocabulary D93's record already carries — EXTENDED, not paralleled:
//   • `keys-accepted`  — a keystroke burst the daemon accepted for delivery (carries `data`).
//   • `screen-read`    — a rendered screen the daemon served to a sender (carries NO `data`).
// A reader holding ONLY this file can tell the two apart from that one field.
//
// ── CLI-EXPANSION (owner ruling, 2026-07-20, at run close): KILLS ARE AUDITED TOO ────────────
//
// `kill-session` writes its own record to the SAME file — attribution only, the screen-read
// shape (a kill carries no typed secret; the record answers WHO killed WHICH session WHEN).
// The vocabulary is EXTENDED again, not paralleled:
//   • `session-killed` — a session the daemon killed on a sender's behalf (carries NO `data`).
// Unlike the two intents above, the caller writes this record AFTER the kill succeeds — the
// owner-ruled success-path placement: a kill delivers no secret whose delivery must be blocked
// on the audit, and refusing a KILL fail-closed would leave a runaway process unkillable behind
// a full disk. The failure POSTURE still mirrors the callers above — an audit-write failure is
// surfaced as a refusal of the success result, never degraded to log-and-continue
// (dispatch.js's handleKillSession reasons the ordering).

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

// Append ONE screen-read record (D94). Throws KeysAuditError on any failure — the caller MUST
// treat a throw as "refuse the read", never as "log and continue" (the fail-closed posture is the
// caller's, reasoned at dispatch.js's handleCaptureSessionScreen).
//
// ⚑ THE GUARD SEQUENCE BELOW IS DUPLICATED FROM appendKeystrokeRecord ON PURPOSE, NOT BY
// OVERSIGHT. That function is CERTIFIED code under an explicit extend-don't-disturb order, and its
// 0600 create + fail-closed re-stat are named byte-intact: factoring them into a helper BOTH
// functions call — the change this file would otherwise want — would rewrite the certified bytes.
// The conservative reading wins here; the extraction is proposed as a follow-up for the owner to
// grant, and until then ANY fix to one guard MUST be applied to the other.
function appendScreenReadRecord({ logPath, execId, sessionId, sender }) {
  if (typeof logPath !== 'string' || logPath.length === 0) {
    throw new KeysAuditError('the session row carries no log_path, so the audit file cannot be placed beside its output log', { execId });
  }
  if (!sender || typeof sender.id !== 'string' || sender.id.length === 0) {
    // D93: an unattributable record answers none of the questions this exists to answer. For a
    // READ that is the whole point — an un-attributed read IS the bypass D94 closes.
    throw new KeysAuditError('no authenticated sender to attribute the screen read to', { execId });
  }

  const auditPath = auditPathFor(logPath);

  try {
    fs.appendFileSync(auditPath, '', { mode: AUDIT_MODE });
  } catch (err) {
    throw new KeysAuditError(`cannot open the session audit at ${auditPath}: ${err.message}`, { execId, auditPath });
  }

  // Re-verify the mode fail-closed, exactly as the keystroke path does. A read record carries no
  // secret itself, but it is appended to the SAME file the keystroke records live in — appending
  // to a file that has been loosened to group/world would keep extending a readable archive of
  // verbatim keystrokes. Refuse instead.
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

  // ⚑ NO `data`, NO `screen`, NO `bytes`. Recording that a read HAPPENED, by whom, when — never
  // what was on the screen. `rows`/`cols` are absent too: this record is written BEFORE the
  // capture (fail-closed ordering), so the dimensions are not yet known, and they describe the
  // exposure's size rather than its attribution.
  const record = {
    ts: new Date().toISOString(),
    event: 'screen-read',
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

// Append ONE session-kill record (cli-expansion owner ruling, 2026-07-20). Throws KeysAuditError
// on any failure — the caller surfaces a throw as a refusal of the success result, never as
// "log and continue" (the kill has already happened by the time this is called; the ordering and
// its posture are reasoned at dispatch.js's handleKillSession).
//
// ⚑ THE GUARD SEQUENCE BELOW IS THE THIRD DELIBERATE COPY of appendKeystrokeRecord's — the same
// extend-don't-disturb order the appendScreenReadRecord note states: the certified bytes are not
// factored into a shared helper, and until the owner grants that extraction ANY fix to one guard
// MUST be applied to all three.
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

// ── TASK 7.13 (owner ruling 2026-07-20, batch 08 item 2 piece 1): SCREEN-READ POLLS ARE
// COALESCED AT SOURCE ─────────────────────────────────────────────────────────────────────────
//
// WHY: the attach client polls `capture-session-screen` every ~250 ms, and the D94 record was
// written once PER POLL — measured on the live box: 2,139 of 2,275 audit records (94%) were
// `screen-read` poll artifacts against 136 keystrokes. A single 10-second human glance wrote
// ~40 "screen was read" entries. The ruling cuts that volume AT SOURCE: a continuous attach by
// one sender is ONE read run, not thousands of reads.
//
// THE SHAPE (extends D93's vocabulary — extended, never paralleled, same as D94 and the kill
// record before it):
//   • `screen-read`         — UNCHANGED, but now written once per read RUN (the first poll of a
//                             continuous attach), not once per poll. Same fields, same fail-closed
//                             ordering: it is appended BEFORE the first screen of the run is
//                             served, and a failed append refuses the read. D94's signal — WHO
//                             read WHICH session's screen, WHEN, distinguishable from writes —
//                             is fully carried by this record.
//   • `screen-read-summary` — NEW: closes a coalesced run, carrying `count` (polls served) and
//                             `first_ts`/`last_ts` (the run's time range) — the ruling's "one
//                             entry carrying a count + time range". Appended when the run closes
//                             (a poll gap past SCREEN_READ_COALESCE_GAP_MS, a kill, or daemon
//                             shutdown), BEST-EFFORT: the screens it summarizes were already
//                             served, so a failed close append cannot retroactively refuse them —
//                             attribution never depended on it (the open record carries that).
//                             A run of exactly one poll writes NO summary (the open record
//                             already says everything).
//
// ⚑ FAIL-CLOSED IS PRESERVED WHERE IT IS LOAD-BEARING. The bypass D94 closes is an
// UN-ATTRIBUTED read. Every run still opens with a fail-closed `screen-read` append before any
// byte is served; polls WITHIN an open run are attributed by that record. What a full disk can
// no longer do is write one record per frame — which is the ruled point.

const SCREEN_READ_COALESCE_GAP_MS = 15000;

// key -> { auditPath, execId, sessionId, sender, firstTs, lastTs, count, lastMs }
const screenReadRuns = new Map();
let coalesceTimer = null;

function runKeyFor(auditPath, execId, senderId) {
  return `${auditPath} ${execId} ${senderId}`;
}

// Append the run-close summary, best-effort. Re-checks the file mode before appending (the
// same posture as the three certified guard copies above: never extend a loosened file that
// holds verbatim keystrokes) — but on ANY failure it drops the summary silently rather than
// throwing: the reads it summarizes already happened.
function appendRunSummary(run) {
  if (run.count <= 1) return;
  try {
    const mode = fs.statSync(run.auditPath).mode & 0o777;
    if (mode & 0o077) return;
    const record = {
      ts: new Date().toISOString(),
      event: 'screen-read-summary',
      id: run.execId,
      session_id: run.sessionId ?? null,
      sender_id: run.sender.id,
      sender_kind: run.sender.kind ?? null,
      via: run.sender.via ?? null,
      count: run.count,
      first_ts: run.firstTs,
      last_ts: run.lastTs,
    };
    fs.appendFileSync(run.auditPath, JSON.stringify(record) + '\n', { mode: AUDIT_MODE });
  } catch { /* best-effort — see the header note */ }
}

function flushExpiredRuns(now = Date.now()) {
  for (const [key, run] of screenReadRuns) {
    if (now - run.lastMs > SCREEN_READ_COALESCE_GAP_MS) {
      screenReadRuns.delete(key);
      appendRunSummary(run);
    }
  }
  if (screenReadRuns.size === 0 && coalesceTimer) {
    clearInterval(coalesceTimer);
    coalesceTimer = null;
  }
}

function ensureCoalesceTimer() {
  if (coalesceTimer) return;
  coalesceTimer = setInterval(() => flushExpiredRuns(), SCREEN_READ_COALESCE_GAP_MS);
  // unref: an idle-attach timer must never hold the daemon (or a probe) alive.
  if (coalesceTimer.unref) coalesceTimer.unref();
}

// Close every open run (optionally only one exec's) and append their summaries. Called on
// daemon shutdown, and before a kill record so the summary lands ahead of `session-killed`
// in the file's order.
function flushScreenReadRuns({ execId = null } = {}) {
  for (const [key, run] of screenReadRuns) {
    if (execId !== null && run.execId !== execId) continue;
    screenReadRuns.delete(key);
    appendRunSummary(run);
  }
  if (screenReadRuns.size === 0 && coalesceTimer) {
    clearInterval(coalesceTimer);
    coalesceTimer = null;
  }
}

// THE screen-read entry point (task 7.13) — call this instead of appendScreenReadRecord.
// First poll of a run: appends the fail-closed `screen-read` record (throws exactly as
// appendScreenReadRecord does — the caller refuses the read). Subsequent polls within the
// coalesce gap: counted in memory, no disk write, `coalesced: true` in the return.
function recordScreenRead({ logPath, execId, sessionId, sender }) {
  const now = Date.now();
  flushExpiredRuns(now);
  const auditPath = auditPathFor(logPath);
  const key = runKeyFor(auditPath, execId, sender && sender.id);
  const run = screenReadRuns.get(key);
  if (run && now - run.lastMs <= SCREEN_READ_COALESCE_GAP_MS) {
    run.count += 1;
    run.lastMs = now;
    run.lastTs = new Date(now).toISOString();
    return { auditPath, coalesced: true };
  }
  // No open run (or the gap elapsed and flushExpiredRuns closed it): open a new run,
  // fail-closed — a throw here propagates and the caller refuses the read (D94 unchanged).
  const res = appendScreenReadRecord({ logPath, execId, sessionId, sender });
  const ts = new Date(now).toISOString();
  screenReadRuns.set(key, {
    auditPath: res.auditPath, execId, sessionId,
    sender: { id: sender.id, kind: sender.kind ?? null, via: sender.via ?? null },
    firstTs: ts, lastTs: ts, count: 1, lastMs: now,
  });
  ensureCoalesceTimer();
  return { ...res, coalesced: false };
}

module.exports = {
  appendKeystrokeRecord, appendScreenReadRecord, appendKillRecord, auditPathFor,
  recordScreenRead, flushScreenReadRuns, SCREEN_READ_COALESCE_GAP_MS,
  KeysAuditError, AUDIT_SUFFIX, AUDIT_MODE,
};
