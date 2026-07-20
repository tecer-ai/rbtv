'use strict';

// Retention for the per-machine state root (task 7.13, owner ruling 2026-07-20 —
// registry-reconciliation batch 08 item 2 + item 10 part 5; settles D95 + D97).
//
// WHY THIS EXISTS: two artifact families in the per-machine root grow forever with no cleanup
// path — the keystroke/screen audit + pty transcript (both secret-bearing: a TUI echoes typed
// input) and the daemon's own ticker.log/feed.jsonl. The audit is FAIL-CLOSED, so an unbounded
// audit plus a full disk self-disables `send-to-session` — the owner loses the ability to type
// into any session. Retention is the ruled fix: an AGE-based sweep, run at daemon boot and daily.
//
// ⚑ NO SIZE CAP, BY RULING. A cap either fires fail-closed and kills `send-to-session` (the very
// lockout being avoided) or silently discards evidence. Age is the only deletion basis here.
//
// ⚑ THE SCOPE IS A POSITIVE ENUMERATION, NEVER A ROOT-WIDE SWEEP. The swept artifact classes are
// enumerated below (`logs/`, `prompts/`, `exits/`, `ptys/`, `ticker.log`, `feed.jsonl`, and —
// per the batch-08 D8 conductor ruling — `ttyd.log`). Everything else in the root is untouched
// BY CONSTRUCTION: the sweep iterates only the enumerated entries, so `heart.db` (which task
// 7.20 moved into this exact root) and `.runtime-config/` are never visited, let alone deleted.
// A denylist would fail OPEN the moment someone adds a new file to the root; this enumeration
// fails CLOSED — a new artifact class is NOT swept until it is added here deliberately.
//
// ⚑ "SESSIONS ENDED beyond the window" is the ruled deletion test. Per-session artifacts are
// aged by mtime (the last write ≈ the session's last activity), and a session that is still
// LIVE in the store (running/launching/stalled) is never swept regardless of age — the caller
// passes the live-session predicate.
//
// The continuously-appended singletons (ticker.log, feed.jsonl, ttyd.log) can never age out by
// mtime (an active daemon refreshes it every tick), so age-based retention reaches them through
// DATED ROTATION: at most once per UTC day the live file is renamed to `<name>.<YYYY-MM-DD>` and
// recreated by its writer's next append (both writers append by PATH, not by held fd), and the
// rotated segments age out by mtime like any artifact. Rotation is not a size cap — nothing is
// deleted at rotation time.

const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_RETENTION_DAYS = 90;
const MIN_RETENTION_DAYS = 7;
const DAY_MS = 24 * 60 * 60 * 1000;
const RETENTION_ENV_VAR = 'RBTV_IGNITE_LOG_RETENTION_DAYS';

// THE enumerated sweep scope (positive enumeration — see the header note).
const SWEPT_SESSION_DIRS = ['logs', 'prompts', 'exits', 'ptys'];
const SWEPT_SINGLETON_FILES = ['ticker.log', 'feed.jsonl', 'ttyd.log'];

// The transcript/audit mode the `logs/` class is normalized to (piece 4 of the ruling: the
// transcript is tightened 664 -> 0600, matching the audit — D97's asymmetry closed).
const TRANSCRIPT_MODE = 0o600;

class RetentionConfigError extends Error {
  constructor(message) {
    super(message);
    this.name = 'RetentionConfigError';
    this.code = 'E_CONFIG_LOAD';
  }
}

// Parse the retention window from the env knob. Default 90; `0` = never delete; values below
// 7 are REJECTED LOUDLY (a typo must not be able to erase the audit trail) — a config-LOAD
// failure: the daemon refuses to boot rather than booting with an audit-erasing window.
function parseRetentionDays(raw) {
  if (raw === undefined || raw === null || raw === '') return DEFAULT_RETENTION_DAYS;
  const n = Number(raw);
  if (!Number.isInteger(n) || n < 0) {
    throw new RetentionConfigError(
      `${RETENTION_ENV_VAR} must be a non-negative integer number of days (got '${raw}'). ` +
      `Default ${DEFAULT_RETENTION_DAYS}; 0 disables deletion entirely.`
    );
  }
  if (n !== 0 && n < MIN_RETENTION_DAYS) {
    throw new RetentionConfigError(
      `${RETENTION_ENV_VAR}=${n} is below the ${MIN_RETENTION_DAYS}-day floor and is REJECTED: ` +
      `a typo must not be able to erase the keystroke/screen audit trail (task 7.13 ruling). ` +
      `Use ${MIN_RETENTION_DAYS} or more, or 0 to never delete.`
    );
  }
  return n;
}

function utcDateStamp(ms) {
  return new Date(ms).toISOString().slice(0, 10); // YYYY-MM-DD
}

// One retention pass over the per-machine state root. Deletion-safe by design: any entry it
// cannot stat or remove is reported in `errors`, never retried destructively. Returns a summary
// { removed, rotated, tightened, skipped_live, errors } with full paths.
function sweepRetention({ dataRoot, retentionDays, now = Date.now(), isSessionLive = null, logger = null }) {
  const out = { removed: [], rotated: [], tightened: [], skipped_live: [], errors: [] };
  const log = (level, message, extra = {}) => { if (logger) logger({ level, message, ...extra }); };
  if (!dataRoot) return out;

  const cutoff = retentionDays > 0 ? now - retentionDays * DAY_MS : null;

  // ── Piece 4 heal pass: normalize every regular file in logs/ to 0600 ─────────────────────
  // Runs even when retentionDays === 0 — mode-tightening is not deletion. Heals transcripts
  // created 664 by systemd's `StandardOutput=append:` before the 0600 pre-create landed.
  const logsDir = path.join(dataRoot, 'logs');
  let logEntries = [];
  try { logEntries = fs.existsSync(logsDir) ? fs.readdirSync(logsDir) : []; } catch (err) {
    out.errors.push({ path: logsDir, error: err.message });
  }
  for (const name of logEntries) {
    const p = path.join(logsDir, name);
    try {
      const st = fs.lstatSync(p);
      if (st.isFile() && (st.mode & 0o077)) { // any group/world bit set -> loosened
        fs.chmodSync(p, TRANSCRIPT_MODE);
        out.tightened.push(p);
      }
    } catch (err) { out.errors.push({ path: p, error: err.message }); }
  }

  // ── Per-session artifact dirs: delete files for sessions ended beyond the window ─────────
  if (cutoff !== null) {
    for (const dirName of SWEPT_SESSION_DIRS) {
      const dir = path.join(dataRoot, dirName);
      let entries = [];
      try { entries = fs.existsSync(dir) ? fs.readdirSync(dir) : []; } catch (err) {
        out.errors.push({ path: dir, error: err.message });
        continue;
      }
      for (const name of entries) {
        const p = path.join(dir, name);
        try {
          const st = fs.lstatSync(p);
          if (st.isDirectory()) continue; // never recurse — the classes are flat by construction
          // `<session-id>.<ext>` — everything before the first dot is the session id.
          const sessionId = name.split('.')[0];
          if (isSessionLive && sessionId && isSessionLive(sessionId)) {
            out.skipped_live.push(p);
            continue; // a LIVE session's artifacts are never swept, regardless of age
          }
          if (st.mtimeMs < cutoff) {
            fs.rmSync(p, { force: true });
            out.removed.push(p);
          }
        } catch (err) { out.errors.push({ path: p, error: err.message }); }
      }
    }
  }

  // ── Singletons: dated rotation + age sweep of rotated segments ────────────────────────────
  const today = utcDateStamp(now);
  for (const fileName of SWEPT_SINGLETON_FILES) {
    const live = path.join(dataRoot, fileName);
    const rotatedToday = `${live}.${today}`;
    try {
      if (fs.existsSync(live) && !fs.existsSync(rotatedToday)) {
        const st = fs.lstatSync(live);
        if (st.isFile() && st.size > 0) {
          fs.renameSync(live, rotatedToday); // writer appends by path -> next append recreates
          out.rotated.push(rotatedToday);
        }
      }
    } catch (err) { out.errors.push({ path: live, error: err.message }); }

    if (cutoff === null) continue;
    // Rotated segments live BESIDE the singleton, named `<name>.YYYY-MM-DD` — match exactly
    // that shape so nothing else in the root can ever be caught by this pass.
    let rootEntries = [];
    try { rootEntries = fs.readdirSync(dataRoot); } catch (err) {
      out.errors.push({ path: dataRoot, error: err.message });
      break;
    }
    const segRe = new RegExp(`^${fileName.replace(/\./g, '\\.')}\\.\\d{4}-\\d{2}-\\d{2}$`);
    for (const name of rootEntries) {
      if (!segRe.test(name)) continue;
      const p = path.join(dataRoot, name);
      try {
        const st = fs.lstatSync(p);
        if (st.isFile() && st.mtimeMs < cutoff) {
          fs.rmSync(p, { force: true });
          out.removed.push(p);
        }
      } catch (err) { out.errors.push({ path: p, error: err.message }); }
    }
  }

  log('info', 'retention sweep complete', {
    dataRoot, retentionDays,
    removed: out.removed.length, rotated: out.rotated.length,
    tightened: out.tightened.length, skippedLive: out.skipped_live.length,
    errors: out.errors.length,
  });
  return out;
}

module.exports = {
  parseRetentionDays,
  sweepRetention,
  RetentionConfigError,
  DEFAULT_RETENTION_DAYS,
  MIN_RETENTION_DAYS,
  RETENTION_ENV_VAR,
  SWEPT_SESSION_DIRS,
  SWEPT_SINGLETON_FILES,
  TRANSCRIPT_MODE,
};
