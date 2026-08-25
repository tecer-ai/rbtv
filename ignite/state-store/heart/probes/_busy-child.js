'use strict';

const { DatabaseSync } = require('node:sqlite');
const dbPath = process.argv[2];

const db = new DatabaseSync(dbPath);
db.exec('PRAGMA busy_timeout = 0;');
try {
  db.prepare('INSERT INTO probe_w (payload) VALUES (?)').run('child');
  console.log('OK');
} catch (err) {
  console.log(`BUSY:${err.code}:${err.message}`);
}
db.close();
