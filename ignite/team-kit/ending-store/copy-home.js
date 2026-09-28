'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');
const { openHeartStore, closeHeartStore } = require('./heart/heart-store');

const OPERATIONAL_TABLES = Object.freeze([
  'jobs', 'queue', 'messages', 'sessions', 'jobs_log', 'enqueue_log', 'ticks', 'warnings', 'reconcile_attempts', 'reconcile_pass',
]);

function tableExists(db, name) {
  const row = db.prepare(
    "SELECT 1 AS hit FROM sqlite_master WHERE type='table' AND name = ?",
  ).get(name);
  return Boolean(row);
}

function columnsOf(db, table) {
  return db.prepare(`PRAGMA table_info(${table})`).all().map((r) => r.name);
}

function copyFromAttached(dest, alias, table) {
  const srcHas = dest.prepare(
    `SELECT 1 AS hit FROM ${alias}.sqlite_master WHERE type='table' AND name = ?`,
  ).get(table);
  if (!srcHas) return 0;
  if (!tableExists(dest, table)) return 0;
  const destCols = columnsOf(dest, table);
  const srcCols = dest.prepare(`PRAGMA ${alias}.table_info(${table})`).all().map((r) => r.name);
  const cols = destCols.filter((c) => srcCols.includes(c));
  if (!cols.length) return 0;
  const list = cols.join(', ');
  dest.exec(`INSERT OR IGNORE INTO ${table} (${list}) SELECT ${list} FROM ${alias}.${table}`);
  return dest.prepare('SELECT changes() AS n').get().n;
}

function copyHeartHome({ daemonDb, workspaceDb, destDb }) {
  if (!destDb) throw new Error('copyHeartHome requires destDb');
  if (fs.existsSync(destDb)) {
    throw new Error(`refusing to overwrite existing dest ${destDb}`);
  }
  fs.mkdirSync(path.dirname(destDb), { recursive: true });
  const store = openHeartStore({ dbPath: destDb });
  const copied = {};
  try {
    const sources = [
      daemonDb && { alias: 'daemon_src', file: daemonDb },
      workspaceDb && { alias: 'workspace_src', file: workspaceDb },
    ].filter((s) => s && s.file && fs.existsSync(s.file));
    for (const src of sources) {
      const srcPath = path.resolve(src.file).replace(/'/g, "''");
      store.db.exec(`ATTACH DATABASE '${srcPath}' AS ${src.alias}`);
      copied[src.alias] = {};
      try {
        for (const table of OPERATIONAL_TABLES) {
          copied[src.alias][table] = copyFromAttached(store.db, src.alias, table);
        }
      } finally {
        store.db.exec(`DETACH DATABASE ${src.alias}`);
      }
    }
  } finally {
    store.close();
    closeHeartStore();
  }
  return { destDb, copied };
}

function parseArgs(argv) {
  const out = { daemonDb: null, workspaceDb: null, destDb: null };
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    const val = argv[i + 1];
    if (key === '--daemon-db') { out.daemonDb = val; i += 1; }
    else if (key === '--workspace-db') { out.workspaceDb = val; i += 1; }
    else if (key === '--dest') { out.destDb = val; i += 1; }
  }
  return out;
}

if (require.main === module) {
  const result = copyHeartHome(parseArgs(process.argv.slice(2)));
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

module.exports = { copyHeartHome, OPERATIONAL_TABLES };
