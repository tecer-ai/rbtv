#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const HERE = __dirname;
const SELFTEST = path.join(HERE, '..', 'last-lane-ask.selftest.js');
const OUT_PATH = path.join(HERE, 'probe-last-lane-ask.out');

const r = spawnSync(process.execPath, [SELFTEST], {
  encoding: 'utf8', timeout: 120000, cwd: path.join(HERE, '..', '..'),
});
const body = [
  'probe-last-lane-ask — last-lane-ask.selftest.js (d-recovery-last-lane-asks / d-recovery-waiting-goal-freeze)',
  `last-lane-ask.selftest exit: ${r.status}`,
  r.stdout || '',
  r.stderr ? `last-lane-ask.selftest stderr:\n${r.stderr}` : '',
].join('\n');
fs.writeFileSync(OUT_PATH, body);
if (r.status !== 0) {
  console.error(body);
  process.exit(r.status == null ? 1 : r.status);
}
console.log(body);
process.exit(0);
