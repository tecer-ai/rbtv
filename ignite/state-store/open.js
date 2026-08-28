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

module.exports = { openEndingStore, openEndingStoreFor, closeEndingStores };
