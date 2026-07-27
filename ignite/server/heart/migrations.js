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

module.exports = { MIGRATIONS, LATEST, migrate, isFreshStore, userVersion };
