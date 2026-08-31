'use strict';

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore } = require('../state-store/heart/heart-store');
const { owedFromLedgers, reconcileGoal } = require('./reconcile');
const counters = require('./attempt-counters');
const { FINISH_MARKER } = require('./owed-from-endings');
const { seedRecoveryConfig, loadRecoveryConfig } = require('./recovery-config');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'finish-gate-selftest-'));
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

function writeTaskforce(goalFolder, seats) {
  const rows = seats.map((s) => `tf,${s},,bash,probe-reconcile,high,35,`);
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n${rows.join('\n')}\n`);
}

function writeSessions(goalFolder, rows) {
  const cols = ['session-id', 'seat', 'harness', 'native-session-id', 'workdir',
    'recorded', 'started', 'ended', 'pid', 'pid-starttime', 'tty', 'disposition',
    'disposition-writer', 'execution', 'checkin', 'model', 'hold-anchor'];
  const linesOut = [cols.join(',')];
  for (const r of rows) {
    linesOut.push(cols.map((c) => (r[c] == null ? '' : String(r[c]).replace(/,/g, ' '))).join(','));
  }
  fs.writeFileSync(path.join(goalFolder, 'sessions.csv'), `${linesOut.join('\n')}\n`);
}

function writeMessages(goalFolder, blocks) {
  const dir = path.join(goalFolder, 'coordination');
  fs.mkdirSync(dir, { recursive: true });
  const parts = ['# messages\n'];
  for (const b of blocks) {
    parts.push(`## ${b.num} | from: ${b.sender} | to: ${b.to} | type: ${b.type} | ${b.ts || '2026-08-19 12:00'}`);
    parts.push('');
    parts.push(b.body || 'body');
    parts.push('');
  }
  fs.writeFileSync(path.join(dir, 'messages.md'), parts.join('\n'));
}

function openStore() {
  const dbPath = path.join(fs.mkdtempSync(path.join(tmpRoot, 'db-')), 'heart.db');
  return openHeartStore({ dbPath });
}

const readyEmpty = { ready: new Map(), granted: new Map(), rows: [], reason: null };

function fixtureB() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'b-'));
  writeSeat(goalFolder, 'leader');
  writeTaskforce(goalFolder, ['leader']);
  writeSessions(goalFolder, [
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'done', checkin: '2026-08-19 10:04' },
  ]);
  writeMessages(goalFolder, [
    { num: 1, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 11:00', body: 'please sit' },
  ]);
  return goalFolder;
}

function fixtureFinishedOwed() {
  const goalFolder = fs.mkdtempSync(path.join(tmpRoot, 'fin-'));
  writeSeat(goalFolder, 'leader');
  writeTaskforce(goalFolder, ['leader']);
  writeSessions(goalFolder, [
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:05', disposition: 'done', checkin: '2026-08-19 10:04' },
  ]);
  writeMessages(goalFolder, [
    { num: 1, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 11:00', body: 'please sit' },
    { num: 2, sender: 'leader', to: 'all', type: 'completion', ts: '2026-08-30 16:43',
      body: `${FINISH_MARKER}\n\nThe goal's execution is over by the deterministic finish edge.` },
  ]);
  return goalFolder;
}

function run() {
  say('── finish event PIN: JS marker is byte-identical to records.py ──');
  {
    const recordsPy = fs.readFileSync(path.join(__dirname, '..', 'coord', 'records.py'), 'utf8');
    assert.ok(recordsPy.includes(`FINISH_MARKER = "${FINISH_MARKER}"`),
      `FINISH_MARKER drifted from records.py: ${JSON.stringify(FINISH_MARKER)}`);
    say('ok  FINISH_MARKER matches coord/records.py');
  }

  say('── finish event: a finished goal with owed mail does not resurrect ──');
  {
    const store = openStore();
    const fx = counterFixture('finish-gate');
    try {
      const goalFolder = fixtureFinishedOwed();
      const d = owedFromLedgers(goalFolder, {
        readyAnswer: readyEmpty, live: new Set(), queued: new Set(),
      });
      assert.strictEqual(d.owed, false, `finished goal still owed: ${JSON.stringify(d)}`);
      assert.strictEqual(d.classA.length, 0, JSON.stringify(d.classA));
      assert.strictEqual(d.classB.length, 0, JSON.stringify(d.classB));

      const rebuilt = [];
      const r = reconcileGoal({
        goal: 'fx-finished', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'BOOT',
        recoverFn: (a) => { rebuilt.push(a); return { ok: true }; },
        ...fx,
      });
      assert.strictEqual(r.skipped, 'finished', JSON.stringify(r));
      assert.strictEqual(rebuilt.length, 0, `room rebuilt: ${JSON.stringify(rebuilt)}`);
      const launched = (r.actions || []).filter((a) => a.kind === 'enqueue');
      assert.strictEqual(launched.length, 0, JSON.stringify(r.actions));
      say('ok  finished + staff unread: skipped finished, no room-rebuilt, no launch, owed false');
    } finally {
      store.close();
      closeHeartStore();
    }
  }

  say('── finish event CONTROL: a running goal with owed mail still recovers ──');
  {
    const store = openStore();
    const fx = counterFixture('finish-ctrl');
    try {
      const goalFolder = fixtureB();
      const d = owedFromLedgers(goalFolder, {
        readyAnswer: readyEmpty, live: new Set(), queued: new Set(),
      });
      assert.strictEqual(d.owed, true, JSON.stringify(d));
      const rebuilt = [];
      const r = reconcileGoal({
        goal: 'fx-running', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'BOOT',
        recoverFn: (a) => { rebuilt.push(a); return { ok: true }; },
        ...fx,
      });
      assert.notStrictEqual(r.skipped, 'finished', JSON.stringify(r));
      const launched = (r.actions || []).filter((a) => a.kind === 'enqueue');
      assert.ok(rebuilt.length > 0 || launched.length > 0,
        `running owed goal neither rebuilt nor launched: rebuilt=${JSON.stringify(rebuilt)} actions=${JSON.stringify(r.actions)}`);
      say(`ok  running control: rebuilt=${rebuilt.length} launches=${launched.length}`);
    } finally {
      store.close();
      closeHeartStore();
    }
  }

  say('── finish event: re-arm does not restart n empty sittings ──');
  {
    const store = openStore();
    const fx = counterFixture('finish-rearm');
    try {
      const goalFolder = fixtureFinishedOwed();
      counters.rearm({ event: counters.RE_ARM.CODE_DEPLOY }, { countersFile: fx.countersFile });
      counters.rearm({
        event: counters.RE_ARM.RESUME, goal: 'fx-finished-rearm',
      }, { countersFile: fx.countersFile });
      const rebuilt = [];
      const r = reconcileGoal({
        goal: 'fx-finished-rearm', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'BOOT',
        recoverFn: (a) => { rebuilt.push(a); return { ok: true }; },
        ...fx,
      });
      assert.strictEqual(r.skipped, 'finished', JSON.stringify(r));
      assert.strictEqual(rebuilt.length, 0, JSON.stringify(rebuilt));
      const launched = (r.actions || []).filter((a) => a.kind === 'enqueue');
      assert.strictEqual(launched.length, 0, JSON.stringify(r.actions));
      say('ok  CODE_DEPLOY/RESUME re-arm on a finished goal still skips');
    } finally {
      store.close();
      closeHeartStore();
    }
  }

  say('── RED: deleting the finish gate resurrects the finished goal ──');
  {
    const Module = require('node:module');
    const owedFile = require.resolve('./owed-from-endings');
    const src = fs.readFileSync(owedFile, 'utf8');
    const ANCHOR = 'function finishEvent(goalFolder) {\n  if (!goalFolder) return false;';
    assert.ok(src.includes(ANCHOR), 'finishEvent anchor missing');
    const mutated = src.replace(ANCHOR, 'function finishEvent(goalFolder) {\n  return false;\n  if (!goalFolder) return false;');
    assert.notStrictEqual(mutated, src);

    const owedSaved = require.cache[owedFile];
    const chainSaved = ['./owed', './reconcile'].map((m) => [require.resolve(m), require.cache[require.resolve(m)]]);
    let rebuilt = [];
    let r;
    const store = openStore();
    const fx = counterFixture('red-finish');
    try {
      const mut = new Module(owedFile, null);
      mut.filename = owedFile;
      mut.paths = Module._nodeModulePaths(__dirname);
      mut._compile(mutated, owedFile);
      require.cache[owedFile] = mut;
      for (const [file] of chainSaved) delete require.cache[file];
      const mutReconcile = require('./reconcile');

      const goalFolder = fixtureFinishedOwed();
      r = mutReconcile.reconcileGoal({
        goal: 'fx-finished-red', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty,
        live: new Set(), promptFn: () => 'BOOT',
        recoverFn: (a) => { rebuilt.push(a); return { ok: true }; },
        ...fx,
      });
    } finally {
      require.cache[owedFile] = owedSaved;
      for (const [file, mod] of chainSaved) {
        if (mod) require.cache[file] = mod; else delete require.cache[file];
      }
      store.close();
      closeHeartStore();
    }
    assert.notStrictEqual(r.skipped, 'finished', JSON.stringify(r));
    const launched = (r.actions || []).filter((a) => a.kind === 'enqueue');
    assert.ok(rebuilt.length > 0 || launched.length > 0,
      `mutant did not resurrect: rebuilt=${JSON.stringify(rebuilt)} actions=${JSON.stringify(r.actions)}`);
    say(`ok  RED: without the finish gate the fixture resurrects (rebuilt=${rebuilt.length} launches=${launched.length})`);
  }

  fs.rmSync(tmpRoot, { recursive: true, force: true });
  say('finish-gate.selftest OK');
}

run();
if (require.main === module) process.exit(0);
