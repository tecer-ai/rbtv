'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const RECORD_REL = path.join('coordination', 'template-defect.json');

function posix(p) {
  return String(p || '').split(path.sep).join('/');
}

function under(root, p) {
  if (!root || !p) return false;
  const a = path.resolve(root);
  const b = path.resolve(p);
  return b === a || b.startsWith(a + path.sep);
}

function classifyFamily(wallPath, ctx = {}) {
  const home = ctx.home || os.homedir();
  const tmpdir = ctx.tmpdir || os.tmpdir();
  const p = path.resolve(wallPath);
  if (under(path.join(home, '.cache'), p) || /(^|\/)\.cache(\/|$)/.test(posix(p))) return 'cache';
  if (under(path.join(home, '.config'), p) || /(^|\/)\.config(\/|$)/.test(posix(p))) return 'config';
  if (under(tmpdir, p) || under('/tmp', p) || under('/var/tmp', p) || /(^|\/)scratch(\/|$)/.test(posix(p))) {
    return 'temp';
  }
  return 'none';
}

function writeWallReport(input) {
  const wallPath = input.path;
  const seat = input.seat;
  const goal = input.goal;
  const family = classifyFamily(wallPath, input);
  const record = {
    path: wallPath,
    'family-match': family,
    seat,
    goal,
  };
  const dest = input.recordPath || path.join(input.goalDir, RECORD_REL);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, JSON.stringify(record, null, 2) + '\n');
  return { record, recordPath: dest };
}

module.exports = {
  RECORD_REL,
  classifyFamily,
  writeWallReport,
};
