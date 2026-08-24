'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { classifyFamily, writeWallReport } = require('./wall-report');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'wall-report-'));
const home = path.join(root, 'home');
const goalDir = path.join(root, 'goal');
const tmpdir = path.join(root, 'tmp');

function run() {
  const cachePath = path.join(home, '.cache', 'missed-tool');
  const configPath = path.join(home, '.config', 'missed-app', 'cfg');
  const tempPath = path.join(tmpdir, 'scratch-file');
  const otherPath = '/usr/share/doc/rbtv-wall-report-none';

  assert.equal(classifyFamily(cachePath, { home, tmpdir }), 'cache');
  assert.equal(classifyFamily(configPath, { home, tmpdir }), 'config');
  assert.equal(classifyFamily(tempPath, { home, tmpdir }), 'temp');
  assert.equal(classifyFamily(otherPath, { home, tmpdir }), 'none');

  const benign = writeWallReport({
    path: cachePath,
    seat: 'worker',
    goal: 'g1',
    goalDir,
    home,
    tmpdir,
  });
  assert.equal(benign.record['family-match'], 'cache');
  assert.equal(benign.record.path, cachePath);
  assert.equal(benign.record.seat, 'worker');
  assert.equal(benign.record.goal, 'g1');
  const onDisk = JSON.parse(fs.readFileSync(benign.recordPath, 'utf8'));
  assert.deepEqual(onDisk, benign.record);

  const nonBenign = writeWallReport({
    path: otherPath,
    seat: 'worker',
    goal: 'g1',
    goalDir,
    home,
    tmpdir,
    recordPath: path.join(root, 'none.json'),
  });
  assert.equal(nonBenign.record['family-match'], 'none');
  assert.equal(nonBenign.record.path, otherPath);

  const impl = fs.readFileSync(path.join(__dirname, 'wall-report.js'), 'utf8');
  assert.ok(!/chat\.postMessage|bridges\/chat|postToSlack/i.test(impl), 'no Slack call');

  console.log('PASS wall-report');
  console.log(`benign family-match=${benign.record['family-match']} path=${benign.record.path}`);
  console.log(`non-benign family-match=${nonBenign.record['family-match']}`);
}

run();
