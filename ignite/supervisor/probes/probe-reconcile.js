#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const HERE = __dirname;
const SELFTEST = path.join(HERE, '..', 'reconcile.selftest.js');
const FINISH = path.join(HERE, '..', 'finish-gate.selftest.js');
const OUT_PATH = path.join(HERE, 'probe-reconcile.out');

const finish = spawnSync(process.execPath, [FINISH], {
  encoding: 'utf8', timeout: 120000, cwd: path.join(HERE, '..', '..'),
});
const hist = spawnSync(process.execPath, [SELFTEST], {
  encoding: 'utf8', timeout: 120000, cwd: path.join(HERE, '..', '..'),
});
const body = [
  'probe-reconcile — finish-gate.selftest.js (resurrection / control / re-arm / red mutation) then reconcile.selftest.js',
  `finish-gate exit: ${finish.status}`,
  finish.stdout || '',
  finish.stderr ? `finish-gate stderr:\n${finish.stderr}` : '',
  `reconcile.selftest exit: ${hist.status}`,
  hist.stdout || '',
  hist.stderr ? `reconcile.selftest stderr:\n${hist.stderr}` : '',
].join('\n');
fs.writeFileSync(OUT_PATH, body);
if (finish.status !== 0) {
  console.error(body);
  process.exit(finish.status == null ? 1 : finish.status);
}
console.log(body);
process.exit(0);
