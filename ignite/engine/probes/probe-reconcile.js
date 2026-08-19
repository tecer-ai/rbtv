#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const HERE = __dirname;
const SELFTEST = path.join(HERE, '..', 'reconcile.selftest.js');
const OUT_PATH = path.join(HERE, 'probe-reconcile.out');

const r = spawnSync(process.execPath, [SELFTEST], {
  encoding: 'utf8', timeout: 120000, cwd: path.join(HERE, '..', '..'),
});
const body = [
  'probe-reconcile — runs engine/reconcile.selftest.js (derivation, enqueue, 3-strikes, durability, red arm)',
  `exit: ${r.status}`,
  r.stdout || '',
  r.stderr ? `stderr:\n${r.stderr}` : '',
].join('\n');
fs.writeFileSync(OUT_PATH, body);
if (r.status !== 0) {
  console.error(body);
  process.exit(r.status == null ? 1 : r.status);
}
console.log(body);
process.exit(0);
