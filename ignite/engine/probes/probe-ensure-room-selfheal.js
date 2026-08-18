#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { openHeartStore, closeHeartStore } = require('../../server/heart/heart-store');
const { ensureRoomSelfheal, jobIdFor, GENERIC_TOOL } = require('../ensure-room-selfheal');

const outPath = path.join(__dirname, 'probe-ensure-room-selfheal.out');
fs.writeFileSync(outPath, '');
const lines = [];
const failures = [];
const say = (s) => { lines.push(s); };
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-ensure-room-selfheal-'));
const dbPath = path.join(tmp, 'heart.db');
const goal = 'scratch-selfheal-arm';
const goalFolder = path.join(tmp, 'goals', goal);
fs.mkdirSync(goalFolder, { recursive: true });

let store;
try {
  store = openHeartStore({
    dbPath,
    tools: { [GENERIC_TOOL]: { argv: ['/usr/bin/true'] } },
  });

  const first = ensureRoomSelfheal({ heartStore: store, goal, goalFolder });
  const jobs1 = store.listJobs().filter((j) => j.job_id === jobIdFor(goal));
  const queue1 = store.listQueue().filter((q) => q.job_id === jobIdFor(goal));
  check('first run registers the job', first.registered === true && jobs1.length === 1,
    JSON.stringify({ registered: first.registered, jobs: jobs1.length }));
  check('first run schedules one periodic row', first.scheduled === true && queue1.length === 1,
    JSON.stringify({ scheduled: first.scheduled, queue: queue1.length, interval: queue1[0] && queue1[0].interval_seconds }));
  check('first run uses the generic tool', first.tool === GENERIC_TOOL, first.tool);

  const snap = {
    jobs: JSON.stringify(store.listJobs()),
    queue: JSON.stringify(store.listQueue()),
  };
  const second = ensureRoomSelfheal({ heartStore: store, goal, goalFolder });
  check('second run registers nothing', second.registered === false, JSON.stringify(second));
  check('second run schedules nothing', second.scheduled === false && second.skipped === 'queue-row-exists',
    JSON.stringify(second));
  check('second run changes no job rows', JSON.stringify(store.listJobs()) === snap.jobs);
  check('second run changes no queue rows', JSON.stringify(store.listQueue()) === snap.queue);
} finally {
  try { closeHeartStore(); } catch { /* already closed */ }
}

const emptyDb = path.join(tmp, 'empty.db');
const empty = openHeartStore({ dbPath: emptyDb, tools: {} });
try {
  const skipped = ensureRoomSelfheal({
    heartStore: empty,
    goal: 'other-goal',
    goalFolder: path.join(tmp, 'goals', 'other-goal'),
  });
  check('absent tool entry is a no-op (probe fixtures stay clean)',
    skipped.skipped === 'no-tool-entry'
      && empty.listJobs().length === 0
      && empty.listQueue().length === 0,
    JSON.stringify(skipped));
} finally {
  closeHeartStore();
}

const status = failures.length ? 'FAIL' : 'PASS';
say(`${status} probe-ensure-room-selfheal — ${failures.length} failure(s)`);
fs.writeFileSync(outPath, lines.join('\n') + '\n');
process.stdout.write(lines.join('\n') + '\n');
process.exit(failures.length ? 1 : 0);
