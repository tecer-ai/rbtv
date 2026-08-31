'use strict';

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { openHeartStore, closeHeartStore } = require('../state-store/heart/heart-store');
const { reconcileGoal } = require('./reconcile');
const { finishEvent, FINISH_MARKER } = require('./owed-from-endings');
const { seedRecoveryConfig, loadRecoveryConfig } = require('./recovery-config');
const { requirePythonCmd } = require('../runtime/python-cmd');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'finish-no-leader-selftest-'));
const COORD_PY = path.join(__dirname, '..', 'coord', 'coord.py');
const lines = [];
function say(s) { lines.push(s); console.log(s); }

function counterFixture(name) {
  const root = fs.mkdtempSync(path.join(tmpRoot, `${name}-ws-`));
  seedRecoveryConfig(root);
  return {
    workspaceRoot: root,
    recovery: loadRecoveryConfig({ workspace: root }),
    countersFile: path.join(root, 'counters.json'),
    lanesFile: path.join(root, 'provider-lanes.json'),
  };
}

function writeSeat(goalFolder, seat) {
  const dir = path.join(goalFolder, 'seats', seat);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'seat.md'),
    `---\nseat: ${seat}\nharness: bash\nmodel: probe-reconcile\n---\n\nbody\n`);
}

function writeTaskforce(goalFolder) {
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n'
    + 'tf,leader,,bash,probe-reconcile,high,35,\n'
    + 'tf,builder,,bash,probe-reconcile,high,35,m1\n'
    + 'tf,auditor,builder,bash,probe-reconcile,high,35,m7\n');
}

function writeSessions(goalFolder) {
  const cols = ['session-id', 'seat', 'harness', 'native-session-id', 'workdir',
    'recorded', 'started', 'ended', 'pid', 'pid-starttime', 'tty', 'disposition',
    'disposition-writer', 'execution', 'checkin', 'model', 'hold-anchor'];
  const row = {
    'session-id': 'ld1', seat: 'leader', started: '2026-08-19 10:00',
    ended: '2026-08-19 10:05', disposition: 'done', checkin: '2026-08-19 10:04',
  };
  fs.writeFileSync(path.join(goalFolder, 'sessions.csv'),
    `${cols.join(',')}\n${cols.map((c) => (row[c] == null ? '' : String(row[c]))).join(',')}\n`);
}

function writeMessages(goalFolder, blocks) {
  const dir = path.join(goalFolder, 'coordination');
  fs.mkdirSync(dir, { recursive: true });
  const parts = ['# messages\n'];
  for (const b of blocks) {
    parts.push(`## ${b.num} | from: ${b.sender} | to: ${b.to} | type: ${b.type} | ${b.ts || '2026-08-28 22:17'}`);
    parts.push('');
    parts.push(b.body || 'body');
    parts.push('');
  }
  fs.writeFileSync(path.join(dir, 'messages.md'), parts.join('\n'));
}

function lastMilestoneStall() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'stall-'));
  writeSeat(goalFolder, 'leader');
  writeSeat(goalFolder, 'builder');
  writeSeat(goalFolder, 'auditor');
  writeTaskforce(goalFolder);
  writeSessions(goalFolder);
  writeMessages(goalFolder, [
    { num: 1, sender: 'auditor', to: 'leader', type: 'completion',
      body: 'M7 COMPLETE — verdict PASS. Product: evidence/m7/audit.md. Work-already-done.' },
  ]);
  return goalFolder;
}

function midPipeline() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'mid-'));
  writeSeat(goalFolder, 'leader');
  writeSeat(goalFolder, 'builder');
  writeSeat(goalFolder, 'auditor');
  writeTaskforce(goalFolder);
  writeSessions(goalFolder);
  writeMessages(goalFolder, [
    { num: 1, sender: 'builder', to: 'leader', type: 'completion',
      body: 'M1 COMPLETE — mid-pipeline; auditor has not run.' },
  ]);
  return goalFolder;
}

function openStore() {
  const dbPath = path.join(fs.mkdtempSync(path.join(tmpRoot, 'db-')), 'heart.db');
  return openHeartStore({ dbPath });
}

const readyEmpty = { ready: new Map(), granted: new Map(), rows: [], reason: null };

function run() {
  say('── HEAD red: last-milestone completion, empty leader chair, no EVENT ──');
  {
    const goalFolder = lastMilestoneStall();
    assert.strictEqual(finishEvent(goalFolder), false, 'fixture already finished');
    const env = { ...process.env };
    delete env.COORD_AGENT;
    const r = spawnSync(requirePythonCmd(), [
      COORD_PY, '--package', goalFolder, '--as', 'ignite-daemon', 'finish-on-completion',
    ], { encoding: 'utf8', timeout: 30000, env });
    assert.strictEqual(r.status, 0, `finish-on-completion failed: ${r.stdout}${r.stderr}`);
    assert.strictEqual(finishEvent(goalFolder), true, 'EVENT not written');
    const bus = fs.readFileSync(path.join(goalFolder, 'coordination', 'messages.md'), 'utf8');
    assert.ok(bus.includes('| from: ignite-daemon |'), bus);
    assert.ok(bus.includes(FINISH_MARKER), bus);
    assert.ok(bus.includes('Work-already-done'), 'last-milestone body was rewritten');
    say('ok  stall fixture: EVENT set, from: ignite-daemon, work-already-done body kept');
  }

  say('── reconcile: last-milestone stall fires finish-on-completion, does not relaunch ──');
  {
    const store = openStore();
    const fx = counterFixture('foc');
    try {
      const goalFolder = lastMilestoneStall();
      const rebuilt = [];
      const r = reconcileGoal({
        goal: 'fx-foc', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'BOOT',
        recoverFn: (a) => { rebuilt.push(a); return { ok: true }; },
        ...fx,
      });
      assert.strictEqual(r.skipped, 'finished', JSON.stringify(r));
      assert.strictEqual(rebuilt.length, 0, `room rebuilt: ${JSON.stringify(rebuilt)}`);
      const kinds = (r.actions || []).map((a) => a.kind);
      assert.deepStrictEqual(kinds, ['finish-on-completion'], JSON.stringify(r.actions));
      assert.strictEqual(finishEvent(goalFolder), true);
      say(`ok  reconcile fired finish-on-completion; actions=${JSON.stringify(kinds)}; no relaunch`);
    } finally {
      store.close();
      closeHeartStore();
    }
  }

  say('── mid-pipeline 429-shaped stall does not fire finish ──');
  {
    const store = openStore();
    const fx = counterFixture('mid');
    try {
      const goalFolder = midPipeline();
      const rebuilt = [];
      const r = reconcileGoal({
        goal: 'fx-mid', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'BOOT',
        recoverFn: (a) => { rebuilt.push(a); return { ok: true }; },
        ...fx,
      });
      assert.notStrictEqual(r.skipped, 'finished', JSON.stringify(r));
      assert.strictEqual(finishEvent(goalFolder), false);
      const kinds = (r.actions || []).map((a) => a.kind);
      assert.ok(!kinds.includes('finish-on-completion'), JSON.stringify(r.actions));
      say(`ok  mid-pipeline: skipped=${r.skipped} finishEvent=false actions=${JSON.stringify(kinds)}`);
    } finally {
      store.close();
      closeHeartStore();
    }
  }

  say('── RED: disable finish-on-completion and the stall returns ──');
  {
    const store = openStore();
    const fx = counterFixture('red');
    try {
      const goalFolder = lastMilestoneStall();
      const rebuilt = [];
      const r = reconcileGoal({
        goal: 'fx-red', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'BOOT',
        recoverFn: (a) => { rebuilt.push(a); return { ok: true }; },
        finishOnCompletionFn: () => ({ fired: false }),
        ...fx,
      });
      assert.notStrictEqual(r.skipped, 'finished', JSON.stringify(r));
      assert.strictEqual(finishEvent(goalFolder), false);
      const launched = (r.actions || []).filter((a) => a.kind === 'enqueue');
      assert.ok(rebuilt.length > 0 || launched.length > 0,
        `stall did not return: rebuilt=${JSON.stringify(rebuilt)} actions=${JSON.stringify(r.actions)}`);
      say(`ok  RED stall returns (rebuilt=${rebuilt.length} launches=${launched.length})`);
    } finally {
      store.close();
      closeHeartStore();
    }
  }

  fs.rmSync(tmpRoot, { recursive: true, force: true });
  say('finish-no-leader.selftest OK');
}

run();
if (require.main === module) process.exit(0);
