'use strict';

// migrations — bring an EXISTING heart store forward to the schema the code expects.
//
// WHY THIS EXISTS (G-135). `schema.sql` is a set of `CREATE TABLE IF NOT EXISTS` statements re-run on
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

// ⚠⚠ `r-746-schema-pregrant` — THE ARMING RIDER (owner, 2026-08-11, task 7.707;
// decisions.md#d-7707-enqueuing-seat-armed-renamed-and-the-pregrant-rider).
//
// The standing posture is that ARMING a migration is the owner's line, not the builder's (each
// migration below restates why). The rider closes the hole that posture left open:
//
//   A WRITE SITE THAT DEPENDS ON AN UNARMED MIGRATION'S SCHEMA MAY NOT LAND. The arming line and
//   EVERY site that reads or writes its columns land in ONE ratification, or none of them do.
//
// This is not a style rule. It was measured: task 7.389's write sites shipped in `3e5a945` while
// its migration sat unarmed here, and the owner's 2026-08-10 22:38 UTC restart put the LIVE VPS
// daemon into a hard crash loop (`table jobs_log has no column named enqueued_seat`, first tick,
// ~6 s cycle, 12 minutes) until an emergency DB-level repair added the columns by hand. The
// half-landed state is the ONLY reachable state that breaks — armed works, and unlanded works —
// so the rider forbids exactly that state and nothing else.
// Accepted cost, ruled knowingly: a finished schema-dependent feature waits for ratification
// before ANY of it lands. The alternative (make every write site tolerate a missing column) was
// declined — it trades a loud crash for a feature sitting silently inert on a live store.

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

// Registered 2026-07-28, owner-directed and owner-verified. It sits here because
// MIGRATION_SESSION_SPLIT is defined AFTER the array literal and so cannot be written inside it.
// (This block also said the line MUST sit above the LATEST derivation — true until task 7.683 moved
// that derivation to the foot of the file, where no registration line can outrun it.)
// Proven against a COPY of the live store before registering: 0 -> 2, session_pk created, and the
// query that crash-looped the daemon (no such column: j.session_pk) then ran clean.
MIGRATIONS.push(MIGRATION_SESSION_SPLIT);

// ── Task 7.12 · the job->seat pointer — REGISTERED 2026-08-04 under `r-migration-job-seat-home-ratified`
// (the posture below described the pre-ratification state and is kept as history).
//
// Same posture as the 7.46 split above, for the same reason and under the same ruling
// (`r-746-schema-pregrant`): LANDING A MIGRATION ARMS IT. `migrate()` runs at DAEMON START, so
// pushing this would migrate the live catalogue on the owner's next restart — a deploy nobody
// decided to make, carrying whatever else is riding that tree. The owner is AFK, and a schema
// change to the production store is not a thing an unattended build run arms on its own authority.
//
// Proven by INJECTION (`migrate(db, { migrations: [...] })` — the parameter this module exposes for
// exactly this). RATIFICATION IS THEN ONE REVIEWABLE LINE, placed immediately below, exactly where
// 7.46's went and for the reason stated above it — below the const definition:
//
//     MIGRATIONS.push(MIGRATION_JOB_SEAT_HOME);   ← SUPERSEDED DRAFT — never place the line HERE:
//     this spot precedes the const definition and throws a module-load ReferenceError (measured,
//     workflow-registration-record.md §R.10c). The LIVE arming line sits BELOW the definition.
//
// `up()` is idempotent (the column-exists guard SQLite forces, since `ALTER TABLE` has no
// `IF NOT EXISTS`), which is what makes that append a NO-OP on stores built from `schema.sql` —
// which already carries the columns — and a REAL migration on the live store, which does not.
//
// ⚠ DISCLOSED DIVERGENCE, not a silent one: SQLite's `ALTER TABLE` cannot add the both-or-neither
// CHECK that `schema.sql` puts on a fresh store, so a MIGRATED store carries the columns without
// it. The same invariant is enforced in `registerJob`, the only writer these columns have, so the
// CHECK is a second line of defence on fresh stores rather than the only one. Closing the gap
// needs SQLite's 12-step table rebuild — not worth arming against a live catalogue for a check
// already held at the writer.
const MIGRATION_JOB_SEAT_HOME = {
  version: 3,
  name: 'job-seat-home-7.12',
  up(db) {
    const cols = db.prepare('PRAGMA table_info(jobs)').all().map((r) => r.name);
    if (!cols.includes('goal_name')) {
      db.exec('ALTER TABLE jobs ADD COLUMN goal_name TEXT;');
    }
    if (!cols.includes('seat_name')) {
      db.exec('ALTER TABLE jobs ADD COLUMN seat_name TEXT;');
    }
    // NO BACKFILL, and that is a ruling rather than an omission. Every existing row is UNHOMED, and
    // `r-job-seat-home` decides where each belongs by a classification the OWNER made (goal-serving
    // vs system-serving) — where the system-serving rows belong is a `system-health` goal that does
    // not yet exist and whose birth is owner-gated ("born ONCE by owner promotion"). Writing a home
    // here would bake a pending owner decision into the store as though it had been taken.
  },
};

// ARMED per `r-migration-job-seat-home-ratified` (owner ratification, 2026-08-03) +
// `p-migration-arming-granted`; executed at the master console under the owner's GO (#3144).
// Placed HERE — after the const definition — because the comment
// block's draft spot precedes the definition and throws at module load (record §R.10c).
MIGRATIONS.push(MIGRATION_JOB_SEAT_HOME);

// ── Task 7.389 · the ENQUEUING-SEAT column (G-leader-0805-0625, G-137 precondition (b)) ──────────
//
// `queue.enqueued_by` / `jobs_log.enqueued_by` are SENDER-IDs — devices and bridges. G-137 measured
// that no column anywhere records the enqueuing SEAT, which is why `seatPrincipalResolver` could
// never grant `creator-seat` and a sender could not remove its OWN row as a seat. This is that
// column, on both tables, so the grant reads the same fact on a queue row and on the jobs_log row
// `canKillSession` is handed.
//
// NULLABLE, and no backfill — the same posture MIGRATION_JOB_SEAT_HOME took, for a stronger reason:
// the enqueuing seat of an already-written row is NOT RECOVERABLE. `enqueued_by` is a sender-id and
// the mapping sender→seat is many-to-one under a shared token (this file's own header), so any
// backfill would be a GUESS written as a fact, and the guess would then hand `creator-seat` to
// whoever the guess named. An unknown seat stays NULL and grants nothing.
//
// `up()` is idempotent via the column-exists guard SQLite's `ALTER TABLE` forces (it has no
// `IF NOT EXISTS`), so this is a NO-OP on a store built from `schema.sql` — which already carries
// both columns — and a real migration on a store that predates them.
const MIGRATION_ENQUEUING_SEAT = {
  version: 4,
  name: 'enqueuing-seat-7.389',
  up(db) {
    for (const table of ['queue', 'jobs_log']) {
      const cols = db.prepare(`PRAGMA table_info(${table})`).all().map((r) => r.name);
      if (!cols.includes('enqueuing_seat')) {
        db.exec(`ALTER TABLE ${table} ADD COLUMN enqueuing_seat TEXT;`);
      }
    }
  },
};

// ARMED per the owner's ruling on task 7.707 (2026-08-11), which renamed the column to
// `enqueuing_seat` and ratified the arming in the same change. Arming is the owner's line, not the
// builder's (`r-746-schema-pregrant`): `migrate()` runs at DAEMON START, so this push migrates the
// LIVE catalogue on the owner's next restart. Placed HERE — below the const, the spot both siblings
// use (the comment-block spot precedes the definition and throws a module-load ReferenceError,
// measured at §R.10c). It is ALSO exported BY NAME in the block at the foot of this file — never
// with a `module.exports.x =` line here, which the terminal `module.exports = { … }` assignment
// would silently clobber — because `probe-migration-enqueuing-seat` still drives it by INJECTION
// (`migrate(db, { migrations: [...] })`).
MIGRATIONS.push(MIGRATION_ENQUEUING_SEAT);

// ── W4 · the message vocabulary CLOSED AT SEVEN — `queue-request` + `escalation` ─────────────────
//
// The other four enum sites are `Set`s in JS and move with an edit. This one is a CHECK constraint,
// and SQLite CANNOT ALTER A CHECK: the only way is the documented table rebuild. So this is the
// first migration in this file that rebuilds a table rather than adding a column, and it must do it
// WITHOUT the step the documented procedure opens with — `PRAGMA foreign_keys=OFF` is a NO-OP
// inside a transaction, and `migrate()` always opens one (schema.sql's jobs_log CHECK note is where
// that trap is recorded; this is the same trap, met head on instead of avoided).
//
// ⚠ THE FOREIGN KEY IS THE HARD PART, and three plausible sequences were MEASURED to fail before
// the one below was kept. `messages` has no OUTGOING foreign key, but
// `jobs_log.completion_msg_id REFERENCES messages(msg_id)` points INTO it:
//
//   · create-new / DROP old — the DROP runs an implicit delete against a referenced table and
//     raises `FOREIGN KEY constraint failed` immediately.
//   · rename-first under `PRAGMA legacy_alter_table = ON` — measured NOT to help: the FK-clause
//     rewrite on RENAME is governed by `foreign_keys`, not by legacy_alter_table, so jobs_log's
//     clause was rewritten to name the shim table and the DROP failed anyway.
//   · `PRAGMA defer_foreign_keys = ON` (which DOES take effect inside a transaction) — the whole
//     rebuild then runs and `PRAGMA foreign_key_check` comes back CLEAN, but COMMIT still fails:
//     SQLite's deferred-violation COUNTER was incremented by the DROP and is never decremented by
//     re-inserting the same rows under a different table name.
//
// So the child column is UNHOOKED and RE-HOOKED around the rebuild. Every non-null
// `completion_msg_id` is read out, nulled, and written back after the new table is in place —
// exact, because `msg_id` values are carried through the copy. It all sits inside the one
// transaction `migrate()` opens, so a failure anywhere rolls the unhooking back with everything
// else and no row is left orphaned.
//
// IDEMPOTENT: it reads the live table's own SQL and returns immediately when the CHECK already
// carries `escalation` — so it is a NO-OP on a store built from today's `schema.sql`.
const MIGRATION_MESSAGE_TYPES_SEVEN = {
  version: 5,
  name: 'message-types-seven-w4',
  up(db) {
    const row = db.prepare(
      "SELECT sql FROM sqlite_master WHERE type='table' AND name='messages'"
    ).get();
    if (!row || String(row.sql).includes("'escalation'")) return;

    const links = db.prepare(
      'SELECT exec_id, completion_msg_id FROM jobs_log WHERE completion_msg_id IS NOT NULL'
    ).all();
    db.exec('UPDATE jobs_log SET completion_msg_id = NULL WHERE completion_msg_id IS NOT NULL;');

    db.exec(`
      CREATE TABLE messages_w4 (
        msg_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        type         TEXT NOT NULL CHECK (type IN ('completion','ask','answer','verdict','note','queue-request','escalation')),
        sender       TEXT NOT NULL,
        thread       TEXT NOT NULL,
        corpus       TEXT NOT NULL,
        status       TEXT,
        created_at   TEXT NOT NULL,
        routed_at_tick    INTEGER,
        broadcast_at_tick INTEGER,
        CHECK ((type = 'completion') = (status IS NOT NULL)),
        CHECK (status IS NULL OR status IN ('done','blocked','failed'))
      );
    `);
    // Columns named explicitly: a bare `SELECT *` would silently mis-map if the two shapes ever
    // drifted, and msg_id is carried so the re-hooked `completion_msg_id` still resolves.
    db.exec(`
      INSERT INTO messages_w4
        (msg_id, type, sender, thread, corpus, status, created_at, routed_at_tick, broadcast_at_tick)
      SELECT
         msg_id, type, sender, thread, corpus, status, created_at, routed_at_tick, broadcast_at_tick
      FROM messages;
    `);
    db.exec('DROP TABLE messages;');
    // jobs_log's clause names `messages`, NOT `messages_w4`, so this rename does not touch it — it
    // simply finds its parent again. (The reverse order is what the second failed sequence above
    // got wrong.)
    db.exec('ALTER TABLE messages_w4 RENAME TO messages;');
    // The indexes went with the dropped table and are recreated on the new one, byte-identical to
    // schema.sql's — a fresh and a migrated store must not differ in what they index either.
    db.exec('CREATE INDEX IF NOT EXISTS idx_messages_unrouted    ON messages(msg_id) WHERE routed_at_tick IS NULL;');
    db.exec('CREATE INDEX IF NOT EXISTS idx_messages_unbroadcast ON messages(msg_id) WHERE broadcast_at_tick IS NULL;');
    db.exec("CREATE INDEX IF NOT EXISTS idx_messages_unrouted_completion ON messages(msg_id) WHERE routed_at_tick IS NULL AND type = 'completion';");

    const relink = db.prepare('UPDATE jobs_log SET completion_msg_id = ? WHERE exec_id = ?');
    for (const l of links) relink.run(l.completion_msg_id, l.exec_id);
  },
};

// ARMED WITH ITS WRITE SITES, which is what `r-746-schema-pregrant`'s ARMING RIDER requires and
// not a builder overriding the owner's line: the four JS enum copies that let a `queue-request` or
// an `escalation` row reach `recordMessage` land in this same change, and the rider forbids exactly
// the half-landed state where a write site depends on an unarmed migration. W4's LANDING is the
// owner-gated ratification of the whole package (task-12, under the landing protocol) — the two
// halves ratify together or neither lands.
MIGRATIONS.push(MIGRATION_MESSAGE_TYPES_SEVEN);

// ── enqueue-record (2026-08-19) · the enqueue→launch sibling of jobs_log ──────────────────────
//
// jobs_log is fired executions only. A suppressed enqueue (the 08-19 silent vanish) wrote
// nothing anywhere. This table is purely additive — CREATE TABLE IF NOT EXISTS + index, no
// ALTER, no rebuild — so it is safe to ARM: migrate() runs at daemon start, and the durable
// record is worthless on a store that lacks the table.
//
// ponytail: the table is never pruned. Upgrade path if it ever matters: delete rows older than
// N days in the same pass. Do not build the pruner.
const MIGRATION_ENQUEUE_LOG = {
  version: 6,
  name: 'enqueue-log',
  up(db) {
    db.exec(
      'CREATE TABLE IF NOT EXISTS enqueue_log (\n'
      + '  enq_id      INTEGER PRIMARY KEY AUTOINCREMENT,\n'
      + '  job_id      TEXT NOT NULL,\n'
      + '  goal        TEXT,\n'
      + '  seat        TEXT,\n'
      + '  seat_key    TEXT,\n'
      + '  outcome     TEXT NOT NULL CHECK (outcome IN (\'enqueued\',\'suppressed\')),\n'
      + '  because     TEXT,\n'
      + '  queue_id    INTEGER,\n'
      + '  exec_id     INTEGER,\n'
      + '  held_status TEXT,\n'
      + '  at          TEXT NOT NULL\n'
      + ');'
    );
    db.exec('CREATE INDEX IF NOT EXISTS idx_enqueue_log_goal_at ON enqueue_log(goal, at);');
  },
};
MIGRATIONS.push(MIGRATION_ENQUEUE_LOG);

// ── D2 (owner ruling, 2026-08-19) · the message vocabulary widened to EIGHT — `stuck` ───────────
//
// THE SAME SHAPE AS MIGRATION 5, for the same reason: SQLite cannot ALTER a CHECK, so widening one
// is a documented table REBUILD, and `jobs_log.completion_msg_id REFERENCES messages(msg_id)`
// points INTO the table being rebuilt. Read MIGRATION_MESSAGE_TYPES_SEVEN's comment block above
// before touching this one — it records the THREE plausible sequences that were MEASURED to fail
// (`PRAGMA foreign_keys=OFF` is a no-op inside migrate()'s transaction; `legacy_alter_table` does
// not help; `defer_foreign_keys` passes `foreign_key_check` and still fails at COMMIT). The
// sequence below is the one that works, and it is deliberately a copy rather than a shared helper:
// a rebuild names its OWN column list, and a helper parameterized over two table shapes would be
// the abstraction that silently mis-maps the third.
//
// IDEMPOTENT the same way: it reads the live table's own SQL and returns immediately when the
// CHECK already carries `stuck` — so it is a NO-OP on a store built from today's `schema.sql`.
const MIGRATION_MESSAGE_TYPES_EIGHT = {
  version: 7,
  name: 'message-types-eight-stuck',
  up(db) {
    const row = db.prepare(
      "SELECT sql FROM sqlite_master WHERE type='table' AND name='messages'"
    ).get();
    if (!row || String(row.sql).includes("'stuck'")) return;

    const links = db.prepare(
      'SELECT exec_id, completion_msg_id FROM jobs_log WHERE completion_msg_id IS NOT NULL'
    ).all();
    db.exec('UPDATE jobs_log SET completion_msg_id = NULL WHERE completion_msg_id IS NOT NULL;');

    db.exec(`
      CREATE TABLE messages_d2 (
        msg_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        type         TEXT NOT NULL CHECK (type IN ('completion','ask','answer','verdict','note','queue-request','escalation','stuck')),
        sender       TEXT NOT NULL,
        thread       TEXT NOT NULL,
        corpus       TEXT NOT NULL,
        status       TEXT,
        created_at   TEXT NOT NULL,
        routed_at_tick    INTEGER,
        broadcast_at_tick INTEGER,
        CHECK ((type = 'completion') = (status IS NOT NULL)),
        CHECK (status IS NULL OR status IN ('done','blocked','failed'))
      );
    `);
    // Columns named explicitly: a bare `SELECT *` would silently mis-map if the two shapes ever
    // drifted, and msg_id is carried so the re-hooked `completion_msg_id` still resolves.
    db.exec(`
      INSERT INTO messages_d2
        (msg_id, type, sender, thread, corpus, status, created_at, routed_at_tick, broadcast_at_tick)
      SELECT
         msg_id, type, sender, thread, corpus, status, created_at, routed_at_tick, broadcast_at_tick
      FROM messages;
    `);
    // ⚠ THE `DROP` IS THE ENTIRE COST OF THIS MIGRATION, and the cause is a MISSING CHILD INDEX,
    // not the row count. With `foreign_keys` ON, dropping a referenced table runs an implicit
    // DELETE and, per deleted row, looks for children pointing at it — and `jobs_log` indexes only
    // `status`, so each of the parent's rows scanned the whole child table. MEASURED on the LIVE
    // store (2026-08-19, 32,351 messages / 29,721 jobs_log rows): `DROP TABLE messages` alone took
    // 163.3s of a 168.8s migration, every other phase under half a second. A throwaway index on
    // the child column takes it to 0.07s — whole migration 0.92s. That is the difference between a
    // daemon whose gateway is unanswerable for three minutes at boot (the watchdog alarms on it,
    // three passes running) and one that starts normally.
    //
    // Created AFTER the column is nulled and dropped IMMEDIATELY after, inside the one transaction
    // `migrate()` opens: nothing outside this migration inherits an index `schema.sql` does not
    // declare, and a failure anywhere rolls it back with everything else.
    db.exec('CREATE INDEX IF NOT EXISTS idx_tmp_d2_jobslog_completion ON jobs_log(completion_msg_id);');
    db.exec('DROP TABLE messages;');
    db.exec('DROP INDEX IF EXISTS idx_tmp_d2_jobslog_completion;');
    // jobs_log's clause names `messages`, NOT `messages_d2`, so this rename does not touch it — it
    // simply finds its parent again.
    db.exec('ALTER TABLE messages_d2 RENAME TO messages;');
    // The indexes went with the dropped table and are recreated on the new one, byte-identical to
    // schema.sql's — a fresh and a migrated store must not differ in what they index either.
    db.exec('CREATE INDEX IF NOT EXISTS idx_messages_unrouted    ON messages(msg_id) WHERE routed_at_tick IS NULL;');
    db.exec('CREATE INDEX IF NOT EXISTS idx_messages_unbroadcast ON messages(msg_id) WHERE broadcast_at_tick IS NULL;');
    db.exec("CREATE INDEX IF NOT EXISTS idx_messages_unrouted_completion ON messages(msg_id) WHERE routed_at_tick IS NULL AND type = 'completion';");

    const relink = db.prepare('UPDATE jobs_log SET completion_msg_id = ? WHERE exec_id = ?');
    for (const l of links) relink.run(l.completion_msg_id, l.exec_id);
  },
};

// ARMED WITH ITS WRITE SITES — `r-746-schema-pregrant`'s ARMING RIDER, exactly as W4 satisfied it:
// the four JS enum copies that let a `stuck` row reach `recordMessage` land in THIS same change,
// and the rider forbids the half-landed state where a write site depends on an unarmed migration.
MIGRATIONS.push(MIGRATION_MESSAGE_TYPES_EIGHT);

// ── watcher (2026-08-19) · durable 3-strike counts for the reconciliation loop ───────────────
//
// Additive CREATE TABLE IF NOT EXISTS — same shape as migration 6. Safe to ARM: migrate()
// runs at daemon start, and a count that reset on restart would never bind (D15).
const MIGRATION_RECONCILE_ATTEMPTS = {
  version: 8,
  name: 'reconcile-attempts',
  up(db) {
    db.exec(
      'CREATE TABLE IF NOT EXISTS reconcile_attempts (\n'
      + '  goal          TEXT NOT NULL,\n'
      + '  seat          TEXT NOT NULL,\n'
      + '  reason        TEXT NOT NULL,\n'
      + '  attempts      INTEGER NOT NULL DEFAULT 0,\n'
      + '  stuck_emitted INTEGER NOT NULL DEFAULT 0 CHECK (stuck_emitted IN (0,1)),\n'
      + '  signature     TEXT,\n'
      + '  updated_at    TEXT NOT NULL,\n'
      + '  PRIMARY KEY (goal, seat, reason)\n'
      + ');'
    );
    db.exec(
      'CREATE TABLE IF NOT EXISTS reconcile_pass (\n'
      + '  goal    TEXT PRIMARY KEY,\n'
      + '  last_at TEXT NOT NULL\n'
      + ');'
    );
  },
};
MIGRATIONS.push(MIGRATION_RECONCILE_ATTEMPTS);

// ── admission-brake (D52/D66, 2026-08-22) · enqueue_log gains the 'braked' outcome ─────────────
//
// SAME SHAPE AS MIGRATION 6/8 (additive) except the CHECK itself must widen, and SQLite cannot
// ALTER a CHECK — a documented rebuild, same pattern as MIGRATION_MESSAGE_TYPES_SEVEN/EIGHT, but
// simpler: nothing REFERENCES enqueue_log (no FK points in), so there is no child-index cost and
// no relink pass.
//
// ⚠ THE OLD TABLE IS RENAMED OUT OF THE WAY, NOT THE NEW ONE RENAMED IN. `ALTER TABLE … RENAME TO`
// makes SQLite re-quote the renamed table's identifier in `sqlite_master.sql`
// (`CREATE TABLE "enqueue_log" (…)`) — measured empirically while proving DoD clause 9 (create one
// fresh store and one migrated store, diff `enqueue_log`'s schema): a migration that renames its
// NEW table INTO place is never byte-identical to schema.sql's own `CREATE TABLE enqueue_log`
// (unquoted). Renaming the OLD table out of the way and creating the final `enqueue_log` fresh
// avoids the quoting divergence entirely — its stored SQL is created the same way schema.sql's is.
const MIGRATION_ENQUEUE_LOG_BRAKED = {
  version: 9,
  name: 'enqueue-log-braked',
  up(db) {
    const row = db.prepare(
      "SELECT sql FROM sqlite_master WHERE type='table' AND name='enqueue_log'"
    ).get();
    // ⚠ MATCH THE CHECK CLAUSE ITSELF, never a bare `'braked'` substring — this table's own
    // schema.sql comment (the block right above the CHECK) quotes the word 'braked' too, and a
    // loose substring test matches the COMMENT on a genuinely pre-migration store and returns
    // early without ever widening the CHECK. Measured while proving fresh-vs-migrated identity
    // for this migration (DoD clause 9): the loose guard made `up()` a permanent no-op.
    if (!row || /IN\s*\(\s*'enqueued'\s*,\s*'suppressed'\s*,\s*'braked'\s*\)/.test(String(row.sql))) return;

    db.exec('ALTER TABLE enqueue_log RENAME TO enqueue_log_pre_d52;');
    // Column body BYTE-IDENTICAL to schema.sql's own `enqueue_log` block (comment included) — that
    // identity is what DoD clause 9 checks, and `CREATE TABLE IF NOT EXISTS` / the trailing `;`
    // are both stripped from `sqlite_master.sql` on EITHER side, so neither needs to match here.
    db.exec(
      'CREATE TABLE enqueue_log (\n'
      + '  enq_id      INTEGER PRIMARY KEY AUTOINCREMENT,\n'
      + '  job_id      TEXT NOT NULL,\n'
      + '  goal        TEXT,\n'
      + '  seat        TEXT,\n'
      + '  seat_key    TEXT,\n'
      + "  -- D52/D66 (2026-08-22) — 'braked' is the admission-brake door's own refusal outcome, recorded\n"
      + '  -- for the SAME reason \'suppressed\' is: every enqueue() caller is recorded, and a refusal that\n'
      + '  -- left no trace is indistinguishable from a caller that never tried (heart-store.js § enqueue).\n'
      + "  outcome     TEXT NOT NULL CHECK (outcome IN ('enqueued','suppressed','braked')),\n"
      + '  because     TEXT,\n'
      + '  queue_id    INTEGER,\n'
      + '  exec_id     INTEGER,\n'
      + '  held_status TEXT,\n'
      + '  at          TEXT NOT NULL\n'
      + ');'
    );
    db.exec(
      'INSERT INTO enqueue_log '
      + '(enq_id, job_id, goal, seat, seat_key, outcome, because, queue_id, exec_id, held_status, at)\n'
      + 'SELECT enq_id, job_id, goal, seat, seat_key, outcome, because, queue_id, exec_id, held_status, at\n'
      + 'FROM enqueue_log_pre_d52;'
    );
    db.exec('DROP TABLE enqueue_log_pre_d52;');
    db.exec('CREATE INDEX IF NOT EXISTS idx_enqueue_log_goal_at ON enqueue_log(goal, at);');
  },
};
MIGRATIONS.push(MIGRATION_ENQUEUE_LOG_BRAKED);

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

// LATEST derives HERE, at the foot of the file — after every registration line above it — and as
// the MAX of the registered versions rather than the last element (task 7.683). It used to sit
// mid-file, which made the POSITION of every `MIGRATIONS.push(...)` load-bearing: a push below it
// left LATEST lagging the list and stores stamped a version short of the migrations that had
// actually run. Three comment blocks above had to warn about that ordering; now no push can outrun
// the derivation and the warning is unnecessary.
const LATEST = MIGRATIONS.reduce((max, m) => Math.max(max, m.version), 0);

module.exports = {
  MIGRATIONS,
  LATEST,
  migrate,
  isFreshStore,
  userVersion,
  // Exported BY NAME as well as being in MIGRATIONS: the probes inject it directly to prove it
  // WORKS, which is a separate claim from it being registered. (This line said "exported but NOT
  // in MIGRATIONS" until 2026-07-28 — true while it was parked, false from the owner's
  // ratification onward, and it sat one line above the push that falsified it.)
  MIGRATION_SESSION_SPLIT,
  // Task 7.12. Exported BY NAME as well as being in MIGRATIONS: the probes inject it directly to
  // prove it WORKS, which is a separate claim from it being registered. (This line said "exported
  // but NOT in MIGRATIONS" until ratification — true while it was parked, false from the owner's
  // ratification onward, and it sat one line above the push that falsified it, same as
  // MIGRATION_SESSION_SPLIT's history above.)
  MIGRATION_JOB_SEAT_HOME,
  // Task 7.389. Exported and NOT in MIGRATIONS — `probe-migration-enqueuing-seat` injects it to
  // prove it works, which is a separate claim from it being armed. Per the note above its
  // definition, the day the owner ratifies it the push goes below the const and THIS COMMENT
  // BECOMES FALSE: correct it in the same change, as MIGRATION_SESSION_SPLIT's had to be.
  MIGRATION_ENQUEUING_SEAT,
  // W4. Exported by name AND registered above — `probe-migration-message-types` injects it to prove
  // the REBUILD works on a store that already holds rows (the fresh-vs-migrated split schema.sql
  // documents), which is a separate claim from it being registered.
  MIGRATION_MESSAGE_TYPES_SEVEN,
  // D2 (2026-08-19). Exported BY NAME as well as being in MIGRATIONS, for the same reason
  // MIGRATION_MESSAGE_TYPES_SEVEN is: `probe-migration-message-types` injects it directly to prove
  // the widening and the re-run no-op on a store it built itself.
  MIGRATION_MESSAGE_TYPES_EIGHT,
  // enqueue-record. Exported by name AND registered above — Arm E of probe-enqueue-record drives
  // migrate() on a pre-v6 store and compares sqlite_master sql against a fresh schema.sql store.
  MIGRATION_ENQUEUE_LOG,
  MIGRATION_RECONCILE_ATTEMPTS,
  // D52/D66. Exported by name AND registered above, for the same reason MIGRATION_MESSAGE_TYPES_EIGHT
  // is: a probe injects it directly to prove the rebuild and the re-run no-op on a store it built
  // itself, and to diff a fresh-vs-migrated enqueue_log schema for byte identity.
  MIGRATION_ENQUEUE_LOG_BRAKED,
};
