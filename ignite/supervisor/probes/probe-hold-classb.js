#!/usr/bin/env node
'use strict';

// probe-hold-classb — A LIVE SEAT HOLD SUPPRESSES CLASS B (UNREAD-MAIL) TOO
//
// WHAT THIS PROBE IS FOR. `owed-from-endings.js#classifyOwed` computes ONE `holdMap` and the
// class-A loop already consulted it. The class-B loop (unread-mail relaunch) did not — its own
// header comment even said so ("Class B is untouched"), which was the defect's own documentation,
// not a ruling. LIVE, 2026-08-30: a hold placed on `meet-transcript-summarizer-planning/leader` at
// 18:04:23Z suppressed class A (`heldExcluded` named it) but not class B — the SAME
// `reconcile: pass` line logged `heldExcluded:["leader:until release",...]` AND
// `classB:["leader"]`, and launched two paid sittings (`ed9ffb12`, `e60bb439`). Task 140
// (`redesign-continue-1`), fixed in commit `bb1e6350` (`if (holdMap.has(chair)) continue;` added
// to the class-B loop).
//
// WHY A DEDICATED PROBE AND NOT ONLY `reconcile.selftest.js`. That shared suite currently aborts
// before reaching its own hold arms (an unrelated, pre-existing D35 assertion failure, not this
// fix's surface — filed separately, owned elsewhere). This probe is self-contained, discovered and
// counted by `ignite/deploy/probe-suite.js` (any `probes/probe-*.js`), and proves the class-B hold
// behaviour on its own so its evidence does not depend on that suite's health.
//
// THREE ARMS, mirroring the CLASS-A hold arms already in `reconcile.selftest.js`:
//   1. CONTROL — an UNHELD chair with pending staff mail IS relaunched via class B. Without this,
//      arm 2 (suppression) would prove nothing: it could pass on a fixture that never fired.
//   2. HELD — the SAME chair, SAME mail, now under a live hold: class B excludes it, no launch, no
//      further attempt counted, and the pass still NAMES the hold (`heldExcluded`).
//   3. RED — with this fix's `holdMap.has(chair)` line removed from a COPY of the live source, the
//      held chair is launched again: the exact live bypass, reproduced.
//
// evidence-class: FIXTURE. A throwaway workspace under the OS temp dir, its own heart.db, its own
// recovery config and counter ledger. Drives the REAL `reconcileGoal`/`classifyOwed`. No daemon, no
// live goals tree, no Slack, no tmux.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HERE = __dirname;
const SUP = path.join(HERE, '..');
const OUT_PATH = path.join(HERE, 'probe-hold-classb.out');

const { reconcileGoal } = require(path.join(SUP, 'reconcile'));
const counters = require(path.join(SUP, 'attempt-counters'));
const { seedRecoveryConfig, loadRecoveryConfig } = require(path.join(SUP, 'recovery-config'));
const { openHeartStore, closeHeartStore } = require(path.join(SUP, '..', 'state-store', 'heart', 'heart-store'));
const { bind } = require(path.join(SUP, '..', 'state-store'));

const lines = [];
const checks = [];
function out(...rows) { for (const r of rows) { lines.push(r); process.stderr.write(`${r}\n`); } }
function check(label, ok, detail) {
  checks.push({ label, ok });
  out(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? `  — ${detail}` : ''}`);
}

const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-hold-classb-'));

function workspace(name) {
  const ws = path.join(ROOT, name);
  fs.mkdirSync(path.join(ws, 'goals'), { recursive: true });
  seedRecoveryConfig(ws);
  return {
    workspaceRoot: ws,
    recovery: loadRecoveryConfig({ workspace: ws }),
    countersFile: path.join(ws, 'counters.json'),
    lanesFile: path.join(ws, 'provider-lanes.json'),
  };
}

const SESSION_COLS = ['session-id', 'seat', 'harness', 'native-session-id', 'workdir',
  'recorded', 'started', 'ended', 'pid', 'pid-starttime', 'tty', 'disposition',
  'disposition-writer', 'execution', 'checkin', 'model', 'hold-anchor'];

function writeSessions(goalFolder, rows) {
  const body = [SESSION_COLS.join(',')];
  for (const r of rows) {
    body.push(SESSION_COLS.map((c) => (r[c] == null ? '' : String(r[c]).replace(/,/g, ' '))).join(','));
  }
  fs.writeFileSync(path.join(goalFolder, 'sessions.csv'), `${body.join('\n')}\n`);
}

function writeMessages(goalFolder, blocks) {
  const dir = path.join(goalFolder, 'coordination');
  fs.mkdirSync(dir, { recursive: true });
  const parts = ['# messages\n'];
  for (const b of blocks) {
    parts.push(`## ${b.num} | from: ${b.sender} | to: ${b.to} | type: note | ${b.ts}`);
    parts.push('', 'body', '');
  }
  fs.writeFileSync(path.join(dir, 'messages.md'), parts.join('\n'));
}

function makeGoal(fx, goal, seats) {
  const goalFolder = path.join(fx.workspaceRoot, 'goals', goal);
  for (const s of seats) {
    const dir = path.join(goalFolder, 'seats', s);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, 'seat.md'), `---\nseat: ${s}\nharness: bash\nmodel: probe-hold\n---\n\nbody\n`);
  }
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n${
      seats.map((s) => `tf,${s},,bash,probe-hold,high,35,`).join('\n')}\n`);
  return goalFolder;
}

// One chair (`leader`, a STAFF_CHAIR), one message addressed to it, no `ended` on its session so
// class A has nothing to classify — only the unread mail can wake this chair. No `workers.md` at
// all, so `readCursor` answers `null` (owed ALL its mail), the same default a chair with no roster
// row gets.
function holdFixture(fx, goal, name) {
  const goalFolder = makeGoal(fx, goal, ['leader']);
  writeSessions(goalFolder, [
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-30 18:00', checkin: '2026-08-30 18:00' },
  ]);
  writeMessages(goalFolder, [
    { num: 1, sender: 'boundary-auditor', to: 'leader', ts: '2026-08-30 18:03' },
  ]);
  return goalFolder;
}

function classBPass(reconcile, store, goal, goalFolder, fx) {
  const out2 = reconcile.reconcileGoal({
    goal, goalFolder, engine: { heartStore: store },
    say: () => {}, force: true,
    readyAnswer: { ready: new Map(), granted: new Map(), rows: [], reason: null },
    live: new Set(), promptFn: () => 'BOOT', recoverFn: () => ({ ok: true }),
    ...fx,
  });
  const counted = counters.peekCounter({
    driver: counters.DRIVERS.RECONCILE_RESPAWN, goal, seat: 'leader', reasonClass: 'unread',
  }, { countersFile: fx.countersFile });
  return {
    launches: out2.actions.filter((a) => a.kind === 'enqueue' && a.reason === 'unread').length,
    classB: out2.derived.classB.map((x) => x.seat),
    held: (out2.derived.heldSeats || []).map((h) => `${h.seat}:${h.until}`),
    attempts: counted ? Number(counted.attempts) : 0,
  };
}

// ── ARM 1 · CONTROL — an unheld chair with pending mail IS relaunched via class B ─────────────
out('', '── ARM 1 · CONTROL — unheld chair with pending mail wakes via class B ──');
let control = null;
{
  const fx = workspace('arm1-control');
  const goal = 'fx-hold-b';
  const goalFolder = holdFixture(fx, goal, 'control');
  const dbPath = path.join(fs.mkdtempSync(path.join(ROOT, 'db1-')), 'heart.db');
  const store = openHeartStore({ dbPath });
  try {
    control = classBPass({ reconcileGoal }, store, goal, goalFolder, fx);
  } finally {
    store.close();
    closeHeartStore();
  }
  out(`  control: ${JSON.stringify(control)}`);
  check('A1.1 the unheld fixture classifies leader as class B', JSON.stringify(control.classB) === JSON.stringify(['leader']), JSON.stringify(control));
  check('A1.2 the unheld fixture wakes the leader over unread mail', control.launches === 1, JSON.stringify(control));
  check('A1.3 the wake counted exactly one attempt', control.attempts === 1, JSON.stringify(control));
}

// ── ARM 2 · HELD — the same chair, same mail, under a live hold: class B excludes it ──────────
out('', '── ARM 2 · HELD — the same chair under a live hold is excluded from class B ──');
{
  const fx = workspace('arm2-held');
  const goal = 'fx-hold-b';
  const goalFolder = holdFixture(fx, goal, 'held');
  const dbPath = path.join(fs.mkdtempSync(path.join(ROOT, 'db2-')), 'heart.db');
  const store = openHeartStore({ dbPath });
  try {
    // The control shape, replayed on THIS store, so the hold arm proves suppression against a
    // fixture already shown (arm 1) to fire without it.
    const before = classBPass({ reconcileGoal }, store, goal, goalFolder, fx);
    check('A2.1 (replay) the unheld pass still wakes the leader on this store', before.launches === 1, JSON.stringify(before));

    bind(store.db).holdSeat({
      goal, seat: 'leader', until: 'release',
      anchor: 'probe: task 140 class-B hold suppression', held_by: 'orchestrator',
    });

    const passes = [];
    for (let i = 0; i < 2; i += 1) passes.push(classBPass({ reconcileGoal }, store, goal, goalFolder, fx));
    out(`  held passes: ${JSON.stringify(passes)}`);
    check('A2.2 every held pass excludes the chair from class B', passes.every((p) => p.classB.length === 0), JSON.stringify(passes));
    check('A2.3 every held pass launches nothing for it', passes.every((p) => p.launches === 0), JSON.stringify(passes));
    // The attempt counter is NOT reset by a hold — it stops advancing past what the control/replay
    // pass already counted (1); the same shape the class-A hold arm in reconcile.selftest.js uses.
    check('A2.4 the counter does not advance past the pre-hold count on any held pass', passes.every((p) => p.attempts === 1), JSON.stringify(passes));
    check('A2.5 every held pass still NAMES the hold on heldExcluded', passes.every((p) => JSON.stringify(p.held) === JSON.stringify(['leader:release'])), JSON.stringify(passes));
  } finally {
    store.close();
    closeHeartStore();
  }
}

// ── ARM 3 · RED — with the exclusion removed, the held chair is launched again ────────────────
out('', '── ARM 3 · RED — remove `holdMap.has(chair)` from class B: the bypass reproduces ──');
{
  const owedFile = path.join(SUP, 'owed-from-endings.js');
  const src = fs.readFileSync(owedFile, 'utf8');
  const ANCHOR = '    if (holdMap.has(chair)) continue;\n    if (abandonedMap.has(chair)) continue;\n    if (liveSet.has(chair) || queuedSet.has(chair)) continue;';
  const anchored = src.includes(ANCHOR);
  let mutantLaunches = null;
  if (anchored) {
    const mutated = src.replace(ANCHOR, '    if (abandonedMap.has(chair)) continue;\n    if (liveSet.has(chair) || queuedSet.has(chair)) continue;');
    const Module = require('node:module');
    const owedMut = new Module(owedFile, null);
    owedMut.filename = owedFile;
    owedMut.paths = Module._nodeModulePaths(SUP);
    owedMut._compile(mutated, owedFile);

    // `reconcile.js` requires `./owed-from-endings` through `./owed` — inject the mutant into the
    // require cache and force both to re-resolve through it, exactly as `reconcile.selftest.js`'s
    // own RED arms already do for the class-A exclusion.
    const owedSaved = require.cache[owedFile];
    const chainSaved = ['./owed', './reconcile'].map((m) => {
      const resolved = require.resolve(m, { paths: [SUP] });
      return [resolved, require.cache[resolved]];
    });
    try {
      require.cache[owedFile] = owedMut;
      for (const [file] of chainSaved) delete require.cache[file];
      const reconcileResolved = require.resolve('./reconcile', { paths: [SUP] });
      const mutReconcile = require(reconcileResolved);

      const fx = workspace('arm3-red');
      const goal = 'fx-hold-b';
      const goalFolder = holdFixture(fx, goal, 'red');
      const dbPath = path.join(fs.mkdtempSync(path.join(ROOT, 'db3-')), 'heart.db');
      const store = openHeartStore({ dbPath });
      try {
        bind(store.db).holdSeat({
          goal, seat: 'leader', until: 'release',
          anchor: 'probe red: task 140 class-B bypass reproduction', held_by: 'orchestrator',
        });
        const red = classBPass(mutReconcile, store, goal, goalFolder, fx);
        mutantLaunches = red.launches;
        out(`  red (exclusion removed): ${JSON.stringify(red)}`);
      } finally {
        store.close();
        closeHeartStore();
      }
    } finally {
      require.cache[owedFile] = owedSaved;
      for (const [file, mod] of chainSaved) {
        if (mod) require.cache[file] = mod; else delete require.cache[file];
      }
    }
  }
  check('A3.1 the class-B hold-exclusion anchor is present in the live source', anchored, ANCHOR);
  check('A3.2 with the exclusion removed, a held chair with unread mail is launched again — the arms above discriminate',
    mutantLaunches === 1, `mutant launches=${mutantLaunches}`);
}

const failed = checks.filter((c) => !c.ok);
out('', `checks: ${checks.length - failed.length}/${checks.length} PASS`);
const body = ['probe-hold-classb — a live seat hold suppresses class B (unread-mail) relaunch, not only class A',
  `fixture root: ${ROOT}`, ...lines, failed.length ? 'RESULT: FAIL' : 'RESULT: PASS'].join('\n');
fs.writeFileSync(OUT_PATH, `${body}\n`);
console.log(body);
process.exit(failed.length ? 1 : 0);
