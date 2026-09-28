'use strict';

// ── OPENING THE ENDING STORE **AT ITS OWN HOME**, WITHOUT THE HEART STORE'S WRITER SLOT ────────
//
// WHY THIS EXISTS. Spec-state-store §1.1 puts the ONE ending store at
// `<workspace>/.rbtv/runtime/ignite/heart.db` — workspace-scoped, and explicitly NOT per-goal
// `heart.db` ("that would recreate dual writers") and NOT `{state_root}/heart.db` after cutover.
// A reader therefore has to reach a file that is NOT the lane store it already holds: the attached
// lane opens `<goal>/heart.db` and the daemon opens `{data_root}/heart.db`, and if endings were
// read out of those, the two lanes would answer differently about one seat — which is the whole
// fact `probe-cross-lane-resume` measures.
//
// AND IT CANNOT BE A SECOND `HeartStore`. That class holds a PROCESS-WIDE writer slot
// (`E_SECOND_WRITER`, one handle per process), so a lane that already opened its own store cannot
// open the ending home through it at all. This module opens the home directly instead: the same
// `node:sqlite` handle, the same pragma order heart-store uses (busy_timeout FIRST, then WAL), and
// `tables.sql` — which is `CREATE TABLE IF NOT EXISTS` throughout, so it creates the tables on a
// fresh home, ADDS a newly-declared one to a home that predates it, and is a no-op on the shared
// host. That is the whole migration path a new table gets here: declare it in `tables.sql`.
//
// ⚠ IT OPENS NO `jobs_log` AND OWNS NO HISTORY. This handle is for `seat_endings`, `goal_states`,
// `open_asks` and the leader's `seat_holds` only. History stays where §5 leaves it: the lane's own
// store.

const fs = require('node:fs');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');
const { endingStorePath } = require('./paths');

const TABLES_SQL = fs.readFileSync(path.join(__dirname, 'tables.sql'), 'utf8');

// ── THE SQLITE-CHECK-WIDENING TRAP (d-goal-closed-word, 2026-09-01) ────────────────────────────
//
// `TABLES_SQL` above is `CREATE TABLE IF NOT EXISTS` throughout — a no-op on a table that already
// exists. Widening `goal_states.stored`'s CHECK in `tables.sql` (to admit `closed`) therefore
// changes NOTHING on a live workspace's `heart.db`: its CHECK constraint stays exactly what it was
// created with, and `writeGoalWord({stored:'closed', ...})` would raise `SQLITE_CONSTRAINT`
// against it — measured directly against this vault's own live db before this landed. Unlike
// `seat_endings` gaining `abandoned` (`seat_abandonments`, a genuinely SECOND fact type, correctly
// a sibling table), `closed` is the FOURTH value of the SAME column `GOAL_WORDS` already names —
// a sibling table would leave `stored` capped at three words and split one fact across two places
// (`no-duplicate`). SQLite cannot `ALTER` a CHECK, so the one non-destructive fix is the standard
// rebuild: rename the old table out of the way, create the new shape fresh (byte-identical to
// `tables.sql`'s own block, so a migrated store's schema matches a freshly-created one), copy every
// row across, drop the renamed-out original. Detection is the CHECK clause itself, never a bare
// `'closed'` substring — this table's own comment above the CHECK now quotes the word too.
function migrateGoalStatesClosed(db) {
  const row = db.prepare(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='goal_states'",
  ).get();
  if (!row || /CHECK\s*\(\s*stored\s+IN\s*\(\s*'running'\s*,\s*'paused'\s*,\s*'finished'\s*,\s*'closed'\s*\)\s*\)/.test(String(row.sql))) {
    return;
  }
  db.exec('ALTER TABLE goal_states RENAME TO goal_states_pre_closed;');
  db.exec(
    "CREATE TABLE goal_states (\n"
    + "  goal TEXT PRIMARY KEY,\n"
    + "  stored TEXT NOT NULL CHECK (stored IN ('running','paused','finished','closed')),\n"
    + "  who_stamped TEXT NOT NULL CHECK (who_stamped IN ('owner','system')),\n"
    + "  evidence_pointer TEXT NOT NULL CHECK (evidence_pointer != ''),\n"
    + "  stamped_at TEXT NOT NULL,\n"
    + "  CHECK (stored != 'paused' OR who_stamped = 'owner'),\n"
    + "  CHECK (stored != 'finished' OR who_stamped = 'system'),\n"
    + "  CHECK (stored != 'closed' OR who_stamped = 'owner')\n"
    + ');',
  );
  db.exec(
    'INSERT INTO goal_states (goal, stored, who_stamped, evidence_pointer, stamped_at)\n'
    + 'SELECT goal, stored, who_stamped, evidence_pointer, stamped_at FROM goal_states_pre_closed;',
  );
  db.exec('DROP TABLE goal_states_pre_closed;');
}

// ── `open_asks` GAINS `kind`/`subject`/`options_json` (`d-owner-ask-shape`, 2026-09-01) ──────────
//
// Same trap `migrateGoalStatesClosed` documents, different shape of fix: `TABLES_SQL`'s widened
// `open_asks` above is `CREATE TABLE IF NOT EXISTS` — a no-op on a table that already exists, so an
// existing `heart.db` needs an explicit patch or the three columns simply never appear on it. Unlike
// `goal_states.stored` (a CHECK widened, forcing the rename-rebuild dance because SQLite cannot
// `ALTER` a CHECK), none of these three columns carry a CHECK — a plain `ALTER TABLE … ADD COLUMN`
// is the whole fix, detected via `PRAGMA table_info` rather than parsing `CREATE TABLE` SQL text
// (there is no CHECK clause here to pattern-match against).
function migrateOpenAsksShape(db) {
  const cols = db.prepare('PRAGMA table_info(open_asks)').all().map((c) => c.name);
  if (!cols.includes('kind')) db.exec("ALTER TABLE open_asks ADD COLUMN kind TEXT NOT NULL DEFAULT '';");
  if (!cols.includes('subject')) db.exec("ALTER TABLE open_asks ADD COLUMN subject TEXT NOT NULL DEFAULT '';");
  if (!cols.includes('options_json')) db.exec("ALTER TABLE open_asks ADD COLUMN options_json TEXT NOT NULL DEFAULT '';");
}

// One handle per FILE per process. Two goals in one workspace are one store, and re-deriving a
// handle per read would pay a file open on every seat of every pass.
const handles = new Map();

function openEndingStore(dbPath) {
  const resolved = path.resolve(dbPath);
  const cached = handles.get(resolved);
  if (cached) return cached;
  fs.mkdirSync(path.dirname(resolved), { recursive: true });
  const db = new DatabaseSync(resolved);
  try {
    db.exec('PRAGMA busy_timeout = 5000;');
    db.exec('PRAGMA journal_mode = WAL;');
    db.exec(TABLES_SQL);
    db.exec('BEGIN IMMEDIATE;');
    try {
      migrateGoalStatesClosed(db);
      migrateOpenAsksShape(db);
      db.exec('COMMIT;');
    } catch (migErr) {
      try { db.exec('ROLLBACK;'); } catch { /* the throw above is what matters */ }
      throw migErr;
    }
  } catch (err) {
    try { db.close(); } catch { /* the throw above is what matters */ }
    throw err;
  }
  handles.set(resolved, db);
  return db;
}

function closeEndingStores() {
  for (const [, db] of handles) {
    try { db.close(); } catch { /* closing a closed handle is not a failure */ }
  }
  handles.clear();
}

function openEndingStoreFor(workspaceRoot) {
  return openEndingStore(endingStorePath(workspaceRoot));
}

module.exports = {
  openEndingStore, openEndingStoreFor, closeEndingStores, migrateGoalStatesClosed, migrateOpenAsksShape,
};
