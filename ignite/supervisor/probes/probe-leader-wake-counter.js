#!/usr/bin/env node
'use strict';

// probe-leader-wake-counter — A NEW STAFF MAIL IS NEW WORK, NEVER A RETRY; A DISARM IS NEVER SILENT
//
// WHAT THIS PROBE IS FOR. On 2026-08-27 the planning chain on `scratch-tool-reach-note` ran
// understander → designer → drafter → reviewer, then STOPPED. The journal's own `reconcile: pass`
// lines carry the whole story: classA was `[plan-understander]` at 16:40Z, `[plan-designer]` at
// 16:55Z, `[plan-drafter]` at 17:11Z — a STRICTLY REPLACED owed set, three FIRST attempts at three
// different pieces of work — and the leader's `(reconcile-respawn, <goal>/leader, nonterm)` counter
// read them as three retries of one failure and reached N=3. The 17:26Z pass, the one carrying the
// reviewer's ending mail, took `skip-disarmed`: no launch, no journal line, no ask, nothing.
//
// The two properties measured here are the two halves of that:
//   1. A pass whose owed items are all NEW does not advance the counter (and never resets it).
//   2. A disarm is audible ONCE — a journal `warn` carrying the counter row and the re-arm list,
//      plus an ask record on the existing owner surface.
//
// evidence-class: FIXTURE. A throwaway workspace under the OS temp dir carrying its own `goals`
// parent, its own recovery config, its own counter ledger and its own heart db. It drives the REAL
// `reconcileGoal`. No daemon, no live goals tree, no Slack, no tmux. NEVER run against the daemon.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HERE = __dirname;
const SUP = path.join(HERE, '..');
const OUT_PATH = path.join(HERE, 'probe-leader-wake-counter.out');

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

const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-leader-wake-'));

// ── THE FIXTURE ────────────────────────────────────────────────────────────────────────────────
// One workspace per arm: its own recovery config (N comes off the file, never a literal), its own
// counter ledger, its own `goals` parent. Nothing here can reach the daemon's state dir.
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
    fs.writeFileSync(path.join(dir, 'seat.md'), `---\nseat: ${s}\nharness: bash\nmodel: probe-wake\n---\n\nbody\n`);
  }
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
    `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n${
      seats.map((s) => `tf,${s},,bash,probe-wake,high,35,`).join('\n')}\n`);
  writeMessages(goalFolder, []);
  return goalFolder;
}

// Every pass gets a FRESH heart db, so a launch queued by the previous pass never masks the next
// one as `skip-live-or-queued`. The counter ledger and the workspace are the things that persist,
// and they are the things under test.
const said = [];
function stamp(store, goal, pairs) {
  const api = bind(store.db);
  for (const [seat, ending] of pairs) {
    const fields = { goal, seat, ending, evidence_pointer: `probe:${seat}`, replace: true };
    if (ending === 'done') api.stampSeatDeclare({ ...fields, declared_outputs: [] });
    else api.stampSystem({ ...fields, reason_class: 'crash' });
  }
}

function pass(fx, goal, goalFolder, { withEndingStore = false, stamps = null } = {}) {
  const dbPath = path.join(fs.mkdtempSync(path.join(ROOT, 'db-')), 'heart.db');
  const store = openHeartStore({ dbPath });
  try {
    if (stamps) stamp(store, goal, stamps);
    const engine = { heartStore: store };
    if (withEndingStore) engine.endingStore = bind(store.db);
    return reconcileGoal({
      goal,
      goalFolder,
      engine,
      say: (level, message, fields) => said.push({ level, message, fields }),
      force: true,
      readyAnswer: { ready: new Map(), granted: new Map(), rows: [], reason: null },
      live: new Set(),
      promptFn: () => 'BOOT',
      recoverFn: () => ({ ok: true }),
      ...fx,
    });
  } finally {
    store.close();
    closeHeartStore();
  }
}

function counterRow(fx, goal, seat, reasonClass) {
  return counters.peekCounter({
    driver: counters.DRIVERS.RECONCILE_RESPAWN, goal, seat, reasonClass,
  }, { countersFile: fx.countersFile });
}

// ── ARM 1 · THREE DISTINCT NEW MAILS ARE THREE FIRST ATTEMPTS ─────────────────────────────────
out('', '── ARM 1 · three distinct new staff mails → three wakes → the counter does NOT advance ──');
{
  const fx = workspace('arm1-new-mail');
  const goal = 'fx-mail';
  const goalFolder = makeGoal(fx, goal, ['leader', 'worker']);
  const seen = [];
  for (let i = 1; i <= 3; i += 1) {
    // Each hop: the chair CHECKED IN at the previous mail (so the old mail is read) and a NEW,
    // never-before-seen message arrives. This is the planning chain's per-hop shape exactly.
    writeSessions(goalFolder, [{
      'session-id': `ld${i}`, seat: 'leader', started: '2026-08-19 09:00',
      ended: `2026-08-19 1${i}:00`, disposition: 'done', 'disposition-writer': 'seat',
      checkin: `2026-08-19 1${i}:00`,
    }]);
    writeMessages(goalFolder, [{ num: i, sender: 'worker', to: 'leader', ts: `2026-08-19 1${i}:30` }]);
    const r = pass(fx, goal, goalFolder);
    const enq = r.actions.filter((a) => a.kind === 'enqueue' && a.reason === 'unread');
    seen.push({ hop: i, woken: enq.length, attempts: (counterRow(fx, goal, 'leader', 'unread') || {}).attempts });
  }
  out(`  hops: ${JSON.stringify(seen)}`);
  check('A1.1 all three new mails WOKE the leader', seen.every((s) => s.woken === 1), JSON.stringify(seen));
  check('A1.2 the unread counter stands at 1 after three distinct new mails — new work is not a retry',
    seen[seen.length - 1].attempts === 1, JSON.stringify(seen));
  const row = counterRow(fx, goal, 'leader', 'unread');
  check('A1.3 the marker rides the ROW, never the key (owed_items present, key is the class)',
    Array.isArray(row.owed_items) && row.reason_class === 'unread', JSON.stringify(row));
}

// ── ARM 2 · THE SAME PENDING MAIL RE-WOKEN IS A RETRY, AND THE DISARM IS AUDIBLE ───────────────
out('', '── ARM 2 · the SAME pending mail 3× → advances to 3 → disarmed → ONE warn + ONE ask row ──');
{
  const fx = workspace('arm2-same-mail');
  const goal = 'fx-same';
  const goalFolder = makeGoal(fx, goal, ['leader', 'worker']);
  // Nothing moves: the chair never checks in past the mail, and no new mail arrives.
  writeSessions(goalFolder, [{
    'session-id': 'ld1', seat: 'leader', started: '2026-08-19 09:00', ended: '2026-08-19 09:30',
    disposition: 'done', 'disposition-writer': 'seat', checkin: '2026-08-19 09:30',
  }]);
  writeMessages(goalFolder, [{ num: 1, sender: 'worker', to: 'leader', ts: '2026-08-19 10:00' }]);

  const attempts = [];
  said.length = 0;
  for (let i = 0; i < 3; i += 1) {
    pass(fx, goal, goalFolder, { withEndingStore: true });
    attempts.push((counterRow(fx, goal, 'leader', 'unread') || {}).attempts);
  }
  out(`  attempts after each pass: ${JSON.stringify(attempts)} (n=${fx.recovery.attempt_counter_n})`);
  check('A2.1 the same pending mail advances the counter to N',
    attempts[2] === fx.recovery.attempt_counter_n, JSON.stringify(attempts));

  // Three more passes on a disarmed lane: the brake must fire, and it must say so exactly once.
  const disarmed = [];
  for (let i = 0; i < 3; i += 1) {
    const r = pass(fx, goal, goalFolder, { withEndingStore: true });
    disarmed.push(r.actions.filter((a) => a.kind === 'skip-disarmed').length);
  }
  check('A2.2 every later pass takes the disarm brake', disarmed.every((d) => d === 1), JSON.stringify(disarmed));

  const warns = said.filter((s) => s.level === 'warn');
  const exhaustLine = warns.filter((w) => /attempt counter exhausted/.test(w.message));
  const disarmLine = warns.filter((w) => /this lane is DISARMED/.test(w.message));
  out(`  warn lines: exhausted=${exhaustLine.length} disarmed=${disarmLine.length} total=${warns.length}`);
  check('A2.3 the exhaustion is journalled exactly ONCE', exhaustLine.length === 1,
    JSON.stringify(exhaustLine.map((w) => w.message)));
  check('A2.4 the disarm announcement is journalled at most ONCE across six passes, never per cadence',
    disarmLine.length <= 1, `${disarmLine.length}`);
  const announced = exhaustLine.concat(disarmLine);
  check('A2.5 the audible line carries the counter row AND the re-arm list',
    announced.length > 0
      && announced.every((w) => Array.isArray(w.fields.re_arm_events) && w.fields.re_arm_events.length === 4)
      && announced.some((w) => Number(w.fields.attempts) >= fx.recovery.attempt_counter_n),
    JSON.stringify(announced.map((w) => w.fields)));

  // The alarm surface is `exhaustion.js`'s existing one, not a new channel.
  const asksDir = path.join(fx.workspaceRoot, '.rbtv', 'runtime', 'ignite', 'asks');
  const askFiles = fs.existsSync(asksDir) ? fs.readdirSync(asksDir).filter((f) => f.endsWith('.json')) : [];
  const record = askFiles.length === 1
    ? JSON.parse(fs.readFileSync(path.join(asksDir, askFiles[0]), 'utf8')) : null;
  check('A2.6 exactly ONE signature-grouped ask record on the existing owner surface',
    askFiles.length === 1, `${asksDir}: ${JSON.stringify(askFiles)}`);
  check('A2.7 the ask record carries ONE lane for this seat, not one per pass',
    record && record.lanes.filter((l) => l.goal === goal && l.seat === 'leader').length === 1,
    record ? JSON.stringify(record.lanes) : 'no record');

  // ── ARM 3 · A code-deploy re-arm clears it ──────────────────────────────────────────────────
  const reset = counters.rearm({ event: counters.RE_ARM.CODE_DEPLOY }, { countersFile: fx.countersFile });
  check('A3.1 a code-deploy re-arm clears the counter row', reset.reset.length >= 1 && !counterRow(fx, goal, 'leader', 'unread'),
    JSON.stringify(reset));
  const after = pass(fx, goal, goalFolder, { withEndingStore: true });
  check('A3.2 the re-armed lane wakes again on the next pass',
    after.actions.some((a) => a.kind === 'enqueue' && a.reason === 'unread'),
    JSON.stringify(after.actions.map((a) => a.kind)));
  check('A3.3 the re-armed counter starts over at 1 — and the once-marker went with the row',
    Number((counterRow(fx, goal, 'leader', 'unread') || {}).attempts) === 1
      && !(counterRow(fx, goal, 'leader', 'unread') || {}).disarm_announced_at,
    JSON.stringify(counterRow(fx, goal, 'leader', 'unread')));
}

// ── ARM 4 · THE LIVE CASE: A PER-HOP REPLACED OWED SET IS NEW WORK ────────────────────────────
out('', '── ARM 4 · the 2026-08-27 planning chain: classA replaced each hop → no advance ──');
{
  const fx = workspace('arm4-nonterm-hops');
  const goal = 'fx-hops';
  const goalFolder = makeGoal(fx, goal, ['leader', 'plan-understander', 'plan-designer', 'plan-drafter']);
  const hops = ['plan-understander', 'plan-designer', 'plan-drafter'];
  const seen = [];
  for (let i = 0; i < hops.length; i += 1) {
    // Exactly the journal's shape: the previous hop's row is RESOLVED and a different seat's
    // non-terminal ending takes its place. One owed row at a time, never accumulating.
    writeSessions(goalFolder, [
      { 'session-id': 'ld', seat: 'leader', started: '2026-08-19 09:00', ended: '2026-08-19 09:30',
        disposition: 'done', 'disposition-writer': 'seat', checkin: '2026-08-19 09:30' },
      { 'session-id': `h${i}`, seat: hops[i], started: '2026-08-19 10:00', ended: '2026-08-19 10:05',
        disposition: 'failed', 'disposition-writer': 'seat' },
    ]);
    const r = pass(fx, goal, goalFolder, { stamps: [['leader', 'done'], [hops[i], 'failed']] });
    seen.push({
      hop: hops[i],
      classA: r.derived.classA.map((x) => x.seat),
      woken: r.actions.filter((a) => a.kind === 'enqueue' && a.reason === 'nonterm').length,
      attempts: (counterRow(fx, goal, 'leader', 'nonterm') || {}).attempts,
    });
  }
  out(`  hops: ${JSON.stringify(seen)}`);
  check('A4.1 every hop woke the leader for judgment', seen.every((s) => s.woken === 1), JSON.stringify(seen));
  check('A4.2 the nonterm counter stands at 1 — three replaced owed sets are three first attempts',
    seen[seen.length - 1].attempts === 1, JSON.stringify(seen));

  // A fourth hop must still wake, which is the mail-#7 pass that took `skip-disarmed` live.
  writeSessions(goalFolder, [
    { 'session-id': 'ld', seat: 'leader', started: '2026-08-19 09:00', ended: '2026-08-19 09:30',
      disposition: 'done', 'disposition-writer': 'seat', checkin: '2026-08-19 09:30' },
    { 'session-id': 'h4', seat: 'plan-designer', started: '2026-08-19 10:00', ended: '2026-08-19 10:05',
      disposition: 'failed', 'disposition-writer': 'seat' },
  ]);
  const fourth = pass(fx, goal, goalFolder, { stamps: [['leader', 'done'], ['plan-designer', 'failed']] });
  check('A4.3 the FOURTH hop still wakes the leader — no silent skip-disarmed',
    fourth.actions.some((a) => a.kind === 'enqueue' && a.reason === 'nonterm')
      && !fourth.actions.some((a) => a.kind === 'skip-disarmed'),
    JSON.stringify(fourth.actions.map((a) => `${a.kind}:${a.reason}`)));
}

// ── ARM 5 · THE [C-4] INVERSION IS UNTOUCHED ──────────────────────────────────────────────────
out('', '── ARM 5 · an owed set that GROWS while its old rows STAND still reaches N [C-4] ──');
{
  const fx = workspace('arm5-overlap');
  const goal = 'fx-overlap';
  const goalFolder = makeGoal(fx, goal, ['leader', 'worker-a', 'worker-b']);
  const leaderRow = {
    'session-id': 'ld', seat: 'leader', started: '2026-08-19 09:00', ended: '2026-08-19 09:30',
    disposition: 'done', 'disposition-writer': 'seat', checkin: '2026-08-19 09:30',
  };
  const rowFor = (seat, id) => ({
    'session-id': id, seat, started: '2026-08-19 10:00', ended: '2026-08-19 10:05',
    disposition: 'failed', 'disposition-writer': 'seat',
  });
  const stampsA = [['leader', 'done'], ['worker-a', 'failed']];
  const stampsAB = [['leader', 'done'], ['worker-a', 'failed'], ['worker-b', 'failed']];
  writeSessions(goalFolder, [leaderRow, rowFor('worker-a', 'a')]);
  pass(fx, goal, goalFolder, { stamps: stampsA });
  pass(fx, goal, goalFolder, { stamps: stampsA });
  // worker-a's row STILL STANDS and worker-b joins it: the leader still owes judgment on work it
  // was already woken for, so this is a retry and the bound must keep closing.
  writeSessions(goalFolder, [leaderRow, rowFor('worker-a', 'a'), rowFor('worker-b', 'b')]);
  pass(fx, goal, goalFolder, { stamps: stampsAB });
  const row = counterRow(fx, goal, 'leader', 'nonterm') || {};
  check('A5.1 a GROWN owed set whose old rows stand still advances to 3 — the [C-4] inversion holds',
    Number(row.attempts) === 3, JSON.stringify(row));
}

// ── ARM 6 · THE LIVE DAEMON'S SHAPE: A COUNTER ALREADY AT N, AND NO ENDING STORE ──────────────
// This is the state the deployed daemon was actually in on 2026-08-27: five counter rows at or past
// N, `engine.endingStore` never set by anything in the tree, so the exhaustion exit was never taken
// and no row carries an announce marker. `skip-disarmed` is the ONLY branch that fires, and before
// this fix it fired in total silence.
out('', '── ARM 6 · a counter already at N with no ending store → skip-disarmed announces ONCE ──');
{
  const fx = workspace('arm6-live-shape');
  const goal = 'fx-live';
  const goalFolder = makeGoal(fx, goal, ['leader', 'worker']);
  writeSessions(goalFolder, [{
    'session-id': 'ld1', seat: 'leader', started: '2026-08-19 09:00', ended: '2026-08-19 09:30',
    disposition: 'done', 'disposition-writer': 'seat', checkin: '2026-08-19 09:30',
  }]);
  writeMessages(goalFolder, [{ num: 1, sender: 'worker', to: 'leader', ts: '2026-08-19 10:00' }]);
  // Drive the counter to N the way the live daemon did: counting only, no exit, no marker.
  for (let i = 0; i < fx.recovery.attempt_counter_n; i += 1) {
    counters.countAttempt({
      driver: counters.DRIVERS.RECONCILE_RESPAWN,
      goal,
      seat: 'leader',
      reasonClass: 'unread',
      n: fx.recovery.attempt_counter_n,
      items: ['#1'],
    }, { countersFile: fx.countersFile });
  }
  const seeded = counterRow(fx, goal, 'leader', 'unread');
  check('A6.1 the fixture reproduces the live shape: at N, never announced',
    Number(seeded.attempts) === fx.recovery.attempt_counter_n && !seeded.disarm_announced_at,
    JSON.stringify(seeded));

  said.length = 0;
  const kinds = [];
  for (let i = 0; i < 4; i += 1) {
    const r = pass(fx, goal, goalFolder);   // NO ending store, exactly like the daemon
    kinds.push(r.actions.filter((a) => a.kind === 'skip-disarmed').length);
  }
  const disarmWarns = said.filter((w) => w.level === 'warn' && /this lane is DISARMED/.test(w.message));
  out(`  skip-disarmed per pass: ${JSON.stringify(kinds)} · disarm warns: ${disarmWarns.length}`);
  check('A6.2 every pass takes the brake and the leader is never woken', kinds.every((k) => k === 1), JSON.stringify(kinds));
  check('A6.3 the disarm is journalled EXACTLY ONCE across four passes — not per cadence, not never',
    disarmWarns.length === 1, `${disarmWarns.length}`);
  check('A6.4 the one line names the counter row, the owed items and the four re-arm events',
    disarmWarns.length === 1
      && Number(disarmWarns[0].fields.attempts) === fx.recovery.attempt_counter_n
      && Array.isArray(disarmWarns[0].fields.owed_items)
      && disarmWarns[0].fields.re_arm_events.length === 4
      && disarmWarns[0].fields.stamped_disarmed === false,
    JSON.stringify(disarmWarns.map((w) => w.fields)));
  const asksDir = path.join(fx.workspaceRoot, '.rbtv', 'runtime', 'ignite', 'asks');
  const askFiles = fs.existsSync(asksDir) ? fs.readdirSync(asksDir).filter((f) => f.endsWith('.json')) : [];
  check('A6.5 the alarm row lands on the existing owner surface even with no ending store',
    askFiles.length === 1, JSON.stringify(askFiles));
}

// ── RED ARM · restore the old behaviour and ARM 1 must fail ───────────────────────────────────
out('', '── RED · strip the owed-item marker from the driver: arm 1 must stop discriminating ──');
{
  const src = fs.readFileSync(path.join(SUP, 'reconcile.js'), 'utf8');
  const ANCHOR = '        items: t.owedItems,';
  const ok = src.includes(ANCHOR);
  let mutantAttempts = null;
  if (ok) {
    const mutated = src.replace(ANCHOR, '        items: null,   // MUTANT: the pre-fix driver');
    const Module = require('node:module');
    const mut = new Module(path.join(SUP, 'reconcile.js'), null);
    mut.filename = path.join(SUP, 'reconcile.js');
    mut.paths = Module._nodeModulePaths(SUP);
    mut._compile(mutated, mut.filename);
    const fx = workspace('red-no-marker');
    const goal = 'fx-red';
    const goalFolder = makeGoal(fx, goal, ['leader', 'worker']);
    for (let i = 1; i <= 3; i += 1) {
      writeSessions(goalFolder, [{
        'session-id': `ld${i}`, seat: 'leader', started: '2026-08-19 09:00',
        ended: `2026-08-19 1${i}:00`, disposition: 'done', 'disposition-writer': 'seat',
        checkin: `2026-08-19 1${i}:00`,
      }]);
      writeMessages(goalFolder, [{ num: i, sender: 'worker', to: 'leader', ts: `2026-08-19 1${i}:30` }]);
      const dbPath = path.join(fs.mkdtempSync(path.join(ROOT, 'reddb-')), 'heart.db');
      const store = openHeartStore({ dbPath });
      try {
        mut.exports.reconcileGoal({
          goal,
          goalFolder,
          engine: { heartStore: store },
          say: () => {},
          force: true,
          readyAnswer: { ready: new Map(), granted: new Map(), rows: [], reason: null },
          live: new Set(),
          promptFn: () => 'BOOT',
          recoverFn: () => ({ ok: true }),
          ...fx,
        });
      } finally {
        store.close();
        closeHeartStore();
      }
    }
    mutantAttempts = Number((counterRow(fx, goal, 'leader', 'unread') || {}).attempts);
  }
  check('RED.1 the mutation anchor is present in the live source', ok, ANCHOR);
  check('RED.2 with the marker stripped, three distinct new mails reach 3 — arm 1 discriminates',
    mutantAttempts === 3, `mutant attempts=${mutantAttempts}`);
}

// ── RED ARM 2 · make the disarm silent again and ARM 6 must fail ──────────────────────────────
out('', '── RED · silence the disarm announcement: arm 6 must stop discriminating ──');
{
  const src = fs.readFileSync(path.join(SUP, 'reconcile.js'), 'utf8');
  const ANCHOR = '  if (!row || row.disarm_announced_at) return null;';
  const ok = src.includes(ANCHOR);
  let warns = null;
  if (ok) {
    // MUTANT: `announceDisarm` returns before it can journal or record anything — the pre-fix
    // `skip-disarmed`, which had no voice at all.
    const mutated = src.replace(ANCHOR, `${ANCHOR}\n  if (true) return null;   // MUTANT: the silent disarm`);
    const Module = require('node:module');
    const mut = new Module(path.join(SUP, 'reconcile.js'), null);
    mut.filename = path.join(SUP, 'reconcile.js');
    mut.paths = Module._nodeModulePaths(SUP);
    mut._compile(mutated, mut.filename);
    const fx = workspace('red-silent-disarm');
    const goal = 'fx-red2';
    const goalFolder = makeGoal(fx, goal, ['leader', 'worker']);
    writeSessions(goalFolder, [{
      'session-id': 'ld1', seat: 'leader', started: '2026-08-19 09:00', ended: '2026-08-19 09:30',
      disposition: 'done', 'disposition-writer': 'seat', checkin: '2026-08-19 09:30',
    }]);
    writeMessages(goalFolder, [{ num: 1, sender: 'worker', to: 'leader', ts: '2026-08-19 10:00' }]);
    for (let i = 0; i < fx.recovery.attempt_counter_n; i += 1) {
      counters.countAttempt({
        driver: counters.DRIVERS.RECONCILE_RESPAWN, goal, seat: 'leader', reasonClass: 'unread',
        n: fx.recovery.attempt_counter_n, items: ['#1'],
      }, { countersFile: fx.countersFile });
    }
    said.length = 0;
    for (let i = 0; i < 4; i += 1) {
      const dbPath = path.join(fs.mkdtempSync(path.join(ROOT, 'red2db-')), 'heart.db');
      const store = openHeartStore({ dbPath });
      try {
        mut.exports.reconcileGoal({
          goal,
          goalFolder,
          engine: { heartStore: store },
          say: (level, message, fields) => said.push({ level, message, fields }),
          force: true,
          readyAnswer: { ready: new Map(), granted: new Map(), rows: [], reason: null },
          live: new Set(),
          promptFn: () => 'BOOT',
          recoverFn: () => ({ ok: true }),
          ...fx,
        });
      } finally {
        store.close();
        closeHeartStore();
      }
    }
    warns = said.filter((w) => w.level === 'warn' && /this lane is DISARMED/.test(w.message)).length;
  }
  check('RED.3 the silence-mutation anchor is present in the live source', ok, ANCHOR);
  check('RED.4 with the announcement silenced, four disarmed passes say NOTHING — arm 6 discriminates',
    warns === 0, `mutant disarm warns=${warns}`);
}

const failed = checks.filter((c) => !c.ok);
out('', `checks: ${checks.length - failed.length}/${checks.length} PASS`);
const body = ['probe-leader-wake-counter — a NEW staff mail is new work, never a retry; a disarm is never silent',
  `fixture root: ${ROOT}`, ...lines, failed.length ? 'RESULT: FAIL' : 'RESULT: PASS'].join('\n');
fs.writeFileSync(OUT_PATH, `${body}\n`);
console.log(body);
process.exit(failed.length ? 1 : 0);
