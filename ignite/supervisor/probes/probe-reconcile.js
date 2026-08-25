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
  'probe-reconcile — runs supervisor/reconcile.selftest.js (derivation, the D33(a) word split, the D34 no-progress counter, the D44 stuck-brake, D35 mail, durability, pause gate, red arms)',
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
