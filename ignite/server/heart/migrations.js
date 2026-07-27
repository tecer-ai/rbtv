'use strict';

// migrations — bring an EXISTING heart store forward to the schema the code expects.
//
// WHY THIS EXISTS (G-135). `schema.sql` is six `CREATE TABLE IF NOT EXISTS` statements re-run on
// every open. On a store that already has those tables it does NOTHING — so adding a column to
// `schema.sql` lands in the file, passes every test, and NEVER REACHES A STORE THAT ALREADY
// EXISTS. Every fixture in this repo builds a FRESH store, and fresh is the one path where a
// schema change works: the change is invisible exactly where it is tested and broken exactly where
// it matters. Measured before this landed: zero `ALTER TABLE`, zero `user_version`, zero migration
// machinery anywhere under `server/`, and `internal-api/authz.js:198` already names the absent
// migration as the blocker for proving creator-seat.
//
// TWO STATES, DELIBERATELY NOT ONE:
//   · a FRESH store gets its shape from `schema.sql`, which always describes the CURRENT schema,
//     and is stamped straight to LATEST — its migrations are already baked into the CREATE
//     statements and re-running them would try to add columns that exist.
//   · an EXISTING store is walked forward one migration at a time from its own `user_version`.
// Freshness is decided by the caller BEFORE `schema.sql` runs, because afterwards every store
// looks identical — which is the whole defect, restated.
//
// THE FAILURE MODE IS THE HARD PART, not the mechanism. This runs at DAEMON START. A migration
// that throws does not fail in the author's terminal; it fails the ONE restart the owner performs,
// carrying whatever else is riding that deploy. So each migration runs in its OWN transaction with
// its version stamped INSIDE it: either the change and its version both land, or neither does.
// There is no state in which the store is half-migrated but claims to be whole, and a failure
// names the migration that caused it rather than surfacing a bare SQLite message.

const { HeartStoreError, E_MIGRATION_FAILED, E_STORE_NEWER_THAN_CODE } = require('./errors');

// ⚠ A LANDED MIGRATION IS IMMUTABLE. Editing one changes what already-migrated stores did, which
// no version number can detect. To change the schema again, APPEND a new entry.
const MIGRATIONS = [
  {
    version: 1,
    name: 'baseline-2026-07-27',
    // Deliberately empty. Version 1 is the shape `schema.sql` had when versioning was introduced,
    // so an existing store from before this mechanism is CORRECT already and only needs stamping.
    // Without this baseline the first real migration would run against a store that already had
    // its columns and fail on the duplicate — adopting an existing database is the step a
    // migration system usually gets wrong, and it is the one this store needs today.
    up() {},
  },
];

// ── Task 7.46 · the session/turn split, WRITTEN AND EXERCISED BUT DELIBERATELY NOT REGISTERED.
//
// ⚠ LANDING A MIGRATION ARMS IT. `migrate()` runs at DAEMON START, so appending this to MIGRATIONS
// would mean the owner's next restart — already required by other backlog items — migrates the
// CERTIFIED store, and the morning ratification would be ratifying a deploy rather than deciding
// the migration. `r-746-schema-pregrant` parks the LIVE migration until that ratification; a
// registered migration makes the park unenforceable. So it is exported and proven by INJECTION
// (`migrate(db, { migrations: [...] })` — the parameter this module exposes for exactly this).
//
// RATIFICATION IS THEN ONE REVIEWABLE LINE: append MIGRATION_SESSION_SPLIT to MIGRATIONS. Nothing
// else changes. `up()` is idempotent throughout (CREATE IF NOT EXISTS, a column-exists guard, and a
// backfill scoped to `session_pk IS NULL`), which is what makes that append a NO-OP on stores
// created tonight from schema.sql — which already carries the shape — and a REAL migration on the
// live store, which does not.
//
// Proven against a COPY OF THE REAL LIVE STORE (324 rows), never on fresh fixtures — G-135's own
// lesson is that fresh is exactly where this class of bug is invisible.
const MIGRATION_SESSION_SPLIT = {
  version: 2,
  name: 'session-turn-split-7.46',
  up(db) {
    db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        session_pk    INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id    TEXT,
        status        TEXT NOT NULL DEFAULT 'alive'
                      CHECK (status IN ('alive','closed','killed','crashed')),
        session_mode  TEXT NOT NULL DEFAULT 'headless'
                      CHECK (session_mode IN ('headless','headed')),
        opened_at     TEXT NOT NULL,
        closed_at     TEXT,
        close_reason  TEXT
      );
    `);
    db.exec('CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);');

    // ALTER TABLE ADD COLUMN has no IF NOT EXISTS in SQLite — guard on the live column list so a
    // second run is a no-op instead of an error.
    const cols = db.prepare('PRAGMA table_info(jobs_log)').all().map((r) => r.name);
    if (!cols.includes('session_pk')) {
      db.exec('ALTER TABLE jobs_log ADD COLUMN session_pk INTEGER REFERENCES sessions(session_pk);');
    }

    // Backfill. Every pre-split row was a session with exactly ONE turn — the degenerate case,
    // which is what every existing row actually WAS. Scoped to rows with no session yet, so
    // re-running adds nothing.
    const rows = db.prepare(
      'SELECT exec_id, status, session_id, session_mode, fired_at, ended_at FROM jobs_log '
      + 'WHERE session_pk IS NULL ORDER BY exec_id'
    ).all();

    // The mapping, so no row is stranded. Three entries are judgment, not mechanics:
    //  · `failed` → session `crashed`: `crashed` is the session-level state for an unplanned end,
    //    and the crash sweep is what writes `failed` today.
    //  · `killed` → turn `failed`: `killed` carried SESSION-level meaning only, so the turn's true
    //    outcome was never recorded by the flat enum either. The mapping is lossy against reality
    //    but NOT against what the store ever held — the honest framing. Leaving the turn `running`
    //    under a terminal session would strand a non-terminal turn that no query could ever close.
    //  · `stalled` → session stays `alive`: stalled is turn-level, and the owner ruling of
    //    2026-07-20 (batch-08 item 4 half B) already means a stalled worker is still tracked.
    const SESSION_OF = {
      launching: 'alive', running: 'alive', stalled: 'alive',
      done: 'closed', blocked: 'closed', failed: 'crashed', killed: 'killed',
    };
    const TURN_OF = { killed: 'failed' }; // every other flat value already IS a turn state

    const insSession = db.prepare(
      'INSERT INTO sessions (session_id, status, session_mode, opened_at, closed_at, close_reason) '
      + 'VALUES (?, ?, ?, ?, ?, ?)'
    );
    const linkTurn = db.prepare('UPDATE jobs_log SET session_pk = ?, status = ? WHERE exec_id = ?');

    for (const r of rows) {
      // An unknown legacy value maps to `crashed`, never `alive`: a store sitting on disk cannot
      // have live processes, and guessing `alive` would resurrect ghosts into the crash sweep at
      // the first tick after the deploy.
      const sStatus = SESSION_OF[r.status] || 'crashed';
      const tStatus = TURN_OF[r.status] || r.status;
      const res = insSession.run(
        r.session_id ?? null,
        sStatus,
        r.session_mode || 'headless',
        r.fired_at,
        sStatus === 'alive' ? null : (r.ended_at || null),
        sStatus === 'alive' ? null : `migrated from flat status '${r.status}'`
      );
      linkTurn.run(Number(res.lastInsertRowid), tStatus, r.exec_id);
    }
  },
};

const LATEST = MIGRATIONS.length ? MIGRATIONS[MIGRATIONS.length - 1].version : 0;

function userVersion(db) {
  const row = db.prepare('PRAGMA user_version').get();
  return Number(row.user_version || 0);
}

function tableCount(db) {
  const row = db.prepare(
    "SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
  ).get();
  return Number(row.n || 0);
}

// Call BEFORE schema.sql runs. Afterwards every store has the tables and the answer is always
// "not fresh" — the distinction only exists in the moment before the CREATEs.
function isFreshStore(db) {
  return tableCount(db) === 0;
}

function migrate(db, opts = {}) {
  const fresh = Boolean(opts.fresh);
  // The migration LIST is injectable for the same reason the probe suite's discover/execute are:
  // the only honest way to prove this mechanism carries a schema change is to hand it a real one
  // and watch a column appear on a real store. A test-only backdoor inside migrate() would be a
  // path that never runs in production; a parameter defaulting to MIGRATIONS is the same code.
  const list = Array.isArray(opts.migrations) ? opts.migrations : MIGRATIONS;
  const latest = list.length ? list[list.length - 1].version : 0;
  const from = userVersion(db);

  // A store written by a NEWER build than this one. Running our older migrations over it would
  // corrupt it, and pretending it is current would silently mis-read its rows. Refuse, named.
  if (from > latest) {
    throw new HeartStoreError(
      E_STORE_NEWER_THAN_CODE,
      `heart store is at schema version ${from} but this build only knows up to ${latest} — `
      + `it was written by a newer ignite. Refusing to open it rather than migrate it backwards.`
    );
  }

  if (from === latest) return { from, to: from, applied: [], fresh };

  if (fresh) {
    // schema.sql already IS the latest shape; stamp it and run nothing.
    db.exec(`PRAGMA user_version = ${latest}`);
    return { from, to: latest, applied: [], fresh };
  }

  const applied = [];
  for (const m of list) {
    if (m.version <= from) continue;
    db.exec('BEGIN IMMEDIATE;');
    try {
      m.up(db);
      // Stamped INSIDE the transaction: the schema change and the claim to have made it commit
      // together or not at all. Stamping after COMMIT would leave a window where the work is done
      // and the version says otherwise — and a crash in that window re-runs the migration.
      db.exec(`PRAGMA user_version = ${m.version}`);
      db.exec('COMMIT;');
    } catch (e) {
      try { db.exec('ROLLBACK;'); } catch { /* the transaction is already gone */ }
      throw new HeartStoreError(
        E_MIGRATION_FAILED,
        `heart store migration ${m.version} (${m.name}) FAILED and was rolled back — the store is `
        + `still at version ${userVersionSafe(db, from)} and is NOT half-migrated. Cause: `
        + `${e && e.message ? e.message : String(e)}`
      );
    }
    applied.push(m.version);
  }
  return { from, to: userVersion(db), applied, fresh };
}

// Reading the version during failure handling must never mask the real error with a second one.
function userVersionSafe(db, fallback) {
  try { return userVersion(db); } catch { return fallback; }
}

module.exports = {
  MIGRATIONS,
  LATEST,
  migrate,
  isFreshStore,
  userVersion,
  // Exported but NOT in MIGRATIONS — see the comment on it. Registering it is the ratification act.
  MIGRATION_SESSION_SPLIT,
};
