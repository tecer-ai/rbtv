#!/usr/bin/env node
'use strict';

// probe-room-selfheal-no-leader — TASK 166: a crashed daemon-lane goal's room reopens on the next
// reconcile pass EVEN WITH NO LEADER CHAIR to relaunch a seat into.
//
// THE MEASURED DEFECT this closes. `reconcile.js`'s `derived.owed && !leader` branch used to only
// log a `warn` ("this goal's room is dead or empty and there is NO LEADER CHAIR to rebuild it
// under — the room is NOT rebuilt") and leave the room dead — indefinitely, since nothing else on
// the daemon lane opens a room for a goal whose seats have already run once
// (`lane-watch.js#openGoalRoom`'s own guard 4, "NOT A FIRST SEEDING", explicitly defers that case
// to THIS file: "the owed/rebuild path's subject"). Measured 2026-08-24 on
// `goal-memory-management`: a daemon-lane goal's room died, the next seed pass refused
// `E_GOAL_NOT_LIVE`, and a human had to `tmux new-session` it back by hand
// (`.rbtv/goals/goal-memory-management/decisions.md`).
//
// WHY NOT `reconcile.selftest.js`. That file is the historical suite and it aborts, PRE-EXISTING
// and unrelated to this fix, at a stale D35 (unread-mail timestamp) assertion well before its own
// B16-adjacent task-166 blocks are ever reached (confirmed: `git show HEAD:ignite/supervisor/
// reconcile.selftest.js | node` fails at the same line with this probe's own diff completely
// removed via a scratch worktree — see this seat's report). This probe is INDEPENDENT of that
// suite, self-contained, and discoverable by `ignite/deploy/probe-suite.js` on its own.
//
// THE QUESTION, four arms:
//   1. owed + NO leader + dead room  -> the room REOPENS (one real tmux session), no seat launched
//   2. RED (the fix hunk reverted)   -> the SAME fixture reproduces the pre-fix `room-refused`,
//      room stays dead, zero tmux calls — proving arm 1 actually discriminates the fix
//   3. CONTROL: owed + leader PRESENT -> the UNCHANGED `recoverRoom` path (relaunch under the
//      named chair) still fires; `openRoomOnly` is never reached
//   4. IDEMPOTENCE: a live room (the real one arm 1 just opened) is left exactly as it is on a
//      second pass — no second tmux command, no duplicate room
//
// WHAT IS SUBSTITUTED, disclosed up front (`bars.md` 10):
//   · `reconcileGoal` is the REAL function from `ignite/supervisor/reconcile.js`. `recoverFn` (the
//     leader-present control's seat-relaunch call, `recover-room.py`) is stubbed — this probe is
//     about the ROOM, not about exercising the Python recovery script.
//   · Arms 1, 3 and 4 run against a REAL, PRIVATE tmux server (own `TMUX_TMPDIR`, `TMUX`/
//     `TMUX_PANE` cleared before anything loads) — `openRoomOnly` really shells
//     `systemd-run --user --scope --collect -- tmux new-session …`. Arm 2 (RED) uses a recorder,
//     never real tmux, since it must prove NOTHING is composed.
//   · The heart-store ending stamps are real, on a scratch SQLite file per arm — `classifyOwed`'s
//     class A (the seat's `exited` ending) is measured, not asserted.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const Module = require('node:module');

const HERE = __dirname;
const IGNITE_SRC = path.join(HERE, '..', '..');
const OUT_PATH = path.join(HERE, 'probe-room-selfheal-no-leader.out');

const start = Date.now();
const lines = [];
const failures = [];
const say = (s) => { lines.push(s); };
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}

// ── tmux isolation, BEFORE anything requires a module that may shell tmux ──────────────────────
const tmuxScratch = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-selfheal-tmux-'));
process.env.TMUX_TMPDIR = tmuxScratch;
delete process.env.TMUX;
delete process.env.TMUX_PANE;

const { reconcileGoal } = require('../reconcile');
const { openHeartStore, closeHeartStore } = require('../../state-store/heart/heart-store');
const { bind } = require('../../state-store');

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-selfheal-'));
const readyEmpty = { ready: new Map(), granted: new Map(), rows: [], reason: null };

function writeSeat(goalFolder, seat, cast) {
  const dir = path.join(goalFolder, 'seats', seat);
  fs.mkdirSync(dir, { recursive: true });
  const fm = cast
    ? `---\nseat: ${seat}\nharness: bash\nmodel: probe-reconcile\n---\n\nbody\n`
    : `---\nseat: ${seat}\n---\n\nbody\n`;
  fs.writeFileSync(path.join(dir, 'seat.md'), fm);
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
  fs.writeFileSync(path.join(dir, 'messages.md'), ['# messages', ''].concat(blocks).join('\n'));
}
function openStore() {
  const dbPath = path.join(fs.mkdtempSync(path.join(tmp, 'db-')), 'heart.db');
  return openHeartStore({ dbPath });
}
function stampExited(store, goal, seat) {
  bind(store.db).stampSystem({
    goal, seat, ending: 'failed', reason_class: 'crash',
    evidence_pointer: `probe:${seat}`, replace: true,
  });
}
function fixtureNoLeader(name) {
  const goalFolder = fs.mkdtempSync(path.join(tmp, `${name}-`));
  writeSeat(goalFolder, 'distill-ignite-memory', true);
  writeTaskforce(goalFolder, ['distill-ignite-memory']);
  writeSessions(goalFolder, [
    { 'session-id': 'd1', seat: 'distill-ignite-memory', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:07', disposition: 'exited', 'disposition-writer': 'kit',
      checkin: '2026-08-19 10:06' },
  ]);
  writeMessages(goalFolder, []);
  return goalFolder;
}
function fixtureWithLeader(name) {
  const goalFolder = fs.mkdtempSync(path.join(tmp, `${name}-`));
  writeSeat(goalFolder, 'leader', true);
  writeSeat(goalFolder, 'worker', true);
  writeTaskforce(goalFolder, ['leader', 'worker']);
  writeSessions(goalFolder, [
    { 'session-id': 'w1', seat: 'worker', started: '2026-08-19 10:00',
      ended: '2026-08-19 10:07', disposition: 'exited', 'disposition-writer': 'kit',
      checkin: '2026-08-19 10:06' },
    { 'session-id': 'l1', seat: 'leader', started: '2026-08-19 09:00',
      ended: '2026-08-19 09:30', disposition: 'done', 'disposition-writer': 'seat',
      checkin: '2026-08-19 09:30' },
  ]);
  writeMessages(goalFolder, []);
  return goalFolder;
}

function tmux(args) {
  return spawnSync('tmux', args, { encoding: 'utf8', env: process.env });
}
function sessionNames() {
  const r = tmux(['list-sessions', '-F', '#{session_name}']);
  if (r.status !== 0) return [];
  return String(r.stdout || '').split('\n').map((s) => s.trim()).filter(Boolean);
}

function main() {
  say('# fixture');
  say(`tmux server: private (TMUX_TMPDIR=${tmuxScratch})`);
  say(`sessions before: ${JSON.stringify(sessionNames())}`);
  say('');

  const before = sessionNames();
  check('the private tmux server holds NO session before the pass', before.length === 0,
    JSON.stringify(before));

  // ── ARM 1 — owed + no leader + dead room -> REAL room reopens, no seat launched ────────────────
  {
    const store = openStore();
    try {
      const goalFolder = fixtureNoLeader('arm1');
      stampExited(store, 'probe-166-arm1', 'distill-ignite-memory');
      let recoverCalls = 0;
      const r = reconcileGoal({
        goal: 'probe-166-arm1', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty, live: new Set(), promptFn: () => 'x',
        sendFn: () => ({ ok: true }),
        recoverFn: () => { recoverCalls += 1; return { ok: true }; },
      });
      check('1 · a REAL tmux room named after the goal now exists',
        sessionNames().includes('probe-166-arm1'), JSON.stringify(sessionNames()));
      check('1 · the pass reports room-reopened-no-leader',
        r.actions.some((a) => a.kind === 'room-reopened-no-leader'), JSON.stringify(r.actions));
      check('1 · no leader is named in the answer',
        r.leader === null, JSON.stringify(r.leader));
      check('1 · no seat was relaunched (recoverFn never called)', recoverCalls === 0, String(recoverCalls));
    } finally { store.close(); closeHeartStore(); }
  }

  // ── ARM 2 — RED: revert the fix hunk in-memory, same fixture -> room stays dead ─────────────────
  {
    const src = fs.readFileSync(path.join(IGNITE_SRC, 'supervisor', 'reconcile.js'), 'utf8');
    const ANCHOR = 'const opened = openRoomOnly({ goal, goalFolder, ...(runTmux ? { runTmux } : {}) });';
    if (!src.includes(ANCHOR)) {
      check('2 · RED mutation anchor present in reconcile.js', false, 'anchor text missing — probe measures nothing');
    } else {
      const p = path.join(IGNITE_SRC, 'supervisor', 'reconcile.js');
      const mut = new Module(p, null);
      mut.filename = p;
      mut.paths = Module._nodeModulePaths(path.dirname(p));
      mut._compile(src.replace(ANCHOR, "const opened = { ok: false, error: 'no-opener (pre-fix behaviour)' };"), p);
      const store = openStore();
      try {
        const goalFolder = fixtureNoLeader('arm2');
        stampExited(store, 'probe-166-arm2', 'distill-ignite-memory');
        const tmuxCalls = [];
        const rr = mut.exports.reconcileGoal({
          goal: 'probe-166-arm2', goalFolder, engine: { heartStore: store },
          say: () => {}, force: true, readyAnswer: readyEmpty, live: new Set(), promptFn: () => 'x',
          sendFn: () => ({ ok: true }), recoverFn: () => ({ ok: true }),
          runTmux: (argv) => { tmuxCalls.push(argv); return '%0 1'; },
        });
        check('2 · RED: with the opener disabled, ZERO tmux calls are composed',
          tmuxCalls.length === 0, JSON.stringify(tmuxCalls));
        check('2 · RED: the room stays refused, matching the pre-fix E_GOAL_NOT_LIVE recurrence',
          rr.actions.some((a) => a.kind === 'room-refused'), JSON.stringify(rr.actions));
        check('2 · RED: no real tmux session for this goal was ever created',
          !sessionNames().includes('probe-166-arm2'), JSON.stringify(sessionNames()));
      } finally { store.close(); closeHeartStore(); }
    }
  }

  // ── ARM 3 — CONTROL: owed + leader PRESENT -> the unchanged relaunch path, opener untouched ────
  {
    const store = openStore();
    try {
      const goalFolder = fixtureWithLeader('arm3');
      stampExited(store, 'probe-166-arm3', 'worker');
      let recoverCalls = 0;
      let recoverSeat = null;
      const r = reconcileGoal({
        goal: 'probe-166-arm3', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty, live: new Set(), promptFn: () => 'x',
        sendFn: () => ({ ok: true }),
        recoverFn: (args) => { recoverCalls += 1; recoverSeat = args.seat; return { ok: true }; },
      });
      check('3 · CONTROL: the leader-present path still relaunches under the named chair',
        recoverCalls === 1 && recoverSeat === 'leader', `calls=${recoverCalls} seat=${recoverSeat}`);
      check('3 · CONTROL: room-rebuilt is reported (the pre-existing, unchanged path)',
        r.actions.some((a) => a.kind === 'room-rebuilt'), JSON.stringify(r.actions));
      check('3 · CONTROL: room-reopened-no-leader is NOT reported here (different branch)',
        !r.actions.some((a) => a.kind === 'room-reopened-no-leader'), JSON.stringify(r.actions));
    } finally { store.close(); closeHeartStore(); }
  }

  // ── ARM 4 — IDEMPOTENCE: the REAL room arm 1 opened is left exactly as it is ────────────────────
  {
    const store = openStore();
    try {
      const goalFolder = fixtureNoLeader('arm4');
      // Re-use arm 1's goal name so its REAL room (still open on the private server) is what this
      // pass sees as already-live.
      stampExited(store, 'probe-166-arm1', 'distill-ignite-memory');
      const before4 = sessionNames();
      let recoverCalls = 0;
      const r = reconcileGoal({
        goal: 'probe-166-arm1', goalFolder, engine: { heartStore: store },
        say: () => {}, force: true, readyAnswer: readyEmpty, live: new Set(), promptFn: () => 'x',
        sendFn: () => ({ ok: true }), recoverFn: () => { recoverCalls += 1; return { ok: true }; },
      });
      check('4 · a live room is left exactly as it is — no room-related action at all',
        !r.actions.some((a) => a.kind === 'room-reopened-no-leader' || a.kind === 'room-refused' || a.kind === 'room-rebuilt'),
        JSON.stringify(r.actions));
      check('4 · exactly the same session set as before this pass (no duplicate room)',
        JSON.stringify(sessionNames().sort()) === JSON.stringify(before4.sort()),
        `before=${JSON.stringify(before4)} after=${JSON.stringify(sessionNames())}`);
      check('4 · no seat relaunch was attempted either', recoverCalls === 0, String(recoverCalls));
    } finally { store.close(); closeHeartStore(); }
  }
}

try {
  main();
} catch (err) {
  say(`FAIL  probe threw: ${err.stack || err.message}`);
  failures.push('probe threw');
} finally {
  const left = sessionNames();
  say('');
  say(`sessions on the private server at teardown: ${JSON.stringify(left)}`);
  const stray = left.filter((s) => !s.startsWith('probe-166-'));
  if (stray.length) { lines.push(`FAIL  a session this probe did not name was found: ${stray}`); failures.push('stray session'); }
  tmux(['kill-server']);
  fs.rmSync(tmuxScratch, { recursive: true, force: true });
  fs.rmSync(tmp, { recursive: true, force: true });
  const exitCode = failures.length ? 1 : 0;
  say('');
  say(exitCode
    ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
    : 'RESULT: PASS — a crashed daemon-lane room with no leader chair reopens (no seat launched), '
      + 'the RED arm reproduces the pre-fix dead-forever room, the leader-present relaunch path is '
      + 'unchanged, and a live room is never re-touched.');
  say(`WALL_MS ${Date.now() - start}`);
  say(`EXIT ${exitCode}`);
  fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n');
  console.log(lines.join('\n'));
  process.exit(exitCode);
}
