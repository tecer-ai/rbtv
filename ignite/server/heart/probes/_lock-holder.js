'use strict';

// Holds a write lock on <dbPath> for <holdMs>, announcing it by creating <markerPath>. Used by
// probe-single-writer arm (d) to prove the heart store's `busy_timeout` is set BEFORE the
// WAL/schema/migrate sequence: with it, the parent's open WAITS here; without it, it throws
// `database is locked` at once.

const fs = require('node:fs');
const { DatabaseSync } = require('node:sqlite');
const [dbPath, holdMs, markerPath] = process.argv.slice(2);

const db = new DatabaseSync(dbPath);
db.exec('PRAGMA journal_mode = WAL;');
db.exec('CREATE TABLE IF NOT EXISTS lock_probe (id INTEGER PRIMARY KEY)');
db.exec('BEGIN IMMEDIATE;');
db.prepare('INSERT INTO lock_probe DEFAULT VALUES').run();
fs.writeFileSync(markerPath, 'locked');
Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, Number(holdMs));
db.exec('ROLLBACK;');
db.close();
