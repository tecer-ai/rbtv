#!/usr/bin/env node
'use strict';

// probe-lane-room-open — THE DAEMON LANE OPENS A NEVER-LIVE GOAL'S FIRST ROOM
// (`lane-watch.js#openGoalRoom`, 2026-08-27).
//
// THE MEASURED DEFECT this closes. `scratch-cli-reach-report` was born through the goal-creation
// request route with a 7-row `taskforce.csv` and 7 seat folders, and was then NEVER seeded: from
// 14:55:12Z the daemon journalled, every 10 s, "goal NOT seeded this pass — the goal is not LIVE …
// has NO live room (tmux session named `scratch-cli-reach-report`) … Start the room (`rbtv run`)".
// `seeding.js` gates seeding on `deriveLease().live`, and NO daemon-side path opened a FIRST room:
// `reconcile.js` rebuilds one only when `deriveOwed` says work is owed (false by construction for a
// goal that never launched a seat), and the boot cockpit opens only `rbtv-cockpit`. 7.778 deleted
// `workflow_launcher.py` — the code that opened the room — and left "WHAT OPENS THE ENTRY SEAT NOW:
// the LANE" without giving the lane an opener.
//
// THE QUESTION. Does the daemon lane now open that first room BY ITSELF, and does it leave alone
// every goal it must not touch?
//
//   1. never-live DAEMON-lane goal with a launchable taskforce -> a REAL tmux room named after the
//      goal exists, the journal carries `room opened by the daemon lane (first seeding)` exactly
//      once, and the goal is then SEEDED (the same `deriveLease` that refused it now says live)
//   2. PAUSED                -> untouched: no tmux call, no room, not seeded
//   3. NO `taskforce.csv`    -> untouched (the loud skip stays)
//   4. CONSOLE lane          -> untouched
//  1b. a taskforce whose ONLY seat is UNCAST (no launchable row) -> untouched
//   5. IDEMPOTENCE           -> a second pass over arm 1 opens NO second room and says nothing
//   6. NOT A FIRST SEEDING   -> a goal with `sessions.csv` rows and a dead room is NOT re-opened
//      BY THIS LANE PASS. This guard cannot tell "the owner closed it" from "it crashed" — both
//      look identical from tmux's side, and by the time this pass reaches the guard the goal is
//      already confirmed daemon-assigned, not paused, and not finished, so a genuine owner-close
//      would already have routed through pause/finish upstream. The actual crashed-dead case (a
//      daemon-lane goal, still active, whose room died after seats ran) IS self-healed — task 166,
//      `reconcile.js`'s `derived.owed && !leader` branch reopens the room (never a seat) once its
//      own ledger-derived `owed` computation says work is outstanding; see
//      `reconcile.selftest.js` B16 and the task-166 arms beside it. This guard's only job is to
//      keep THIS opener from racing that one and duplicating the room.
//
// WHAT IS SUBSTITUTED, disclosed up front (`bars.md` 10):
//   · No daemon PROCESS and no ENGINE run here. `runLaneWatch` is the REAL one, driven with a stub
//     `engine` whose `seedGoal` re-asks the REAL `deriveLease` at the exact threshold
//     `seeding.js#seedGoal` reads — so "seeded" is measured at the real gate, never asserted.
//   · `openGoalRoom`, `composeDetachedSession`, `deriveLease` and tmux itself are all REAL. Arm 1
//     really creates a tmux session through the real `systemd-run --user --scope --collect`
//     wrapper.
//   · THE TMUX SERVER IS PRIVATE. `TMUX_TMPDIR` is a scratch dir and `TMUX`/`TMUX_PANE` are
//     cleared before anything, so every session this probe creates lands on a server of its own
//     and the box's real sessions are unreachable from here (verified: the wrapper inherits the
//     env). The server is killed in `finally`, and every goal — hence every room — is named
//     `probe-…`.
//
// SIX MUTATION ARMS replace one or more strings in `lane-watch.js`, compiled in memory (no file is
// written beside the source), and REQUIRE the pass to go red. Every anchor is asserted present
// first, so a mutation that matched nothing can never pass for one that was survived. Their order
// is load-bearing: the live-room arm runs while the real room is UP (that is the state its guard
// exists for), the rest after it is killed.
//
// A SEVENTH arm is DELIBERATELY NOT a red arm and says so: the taskforce-less goal is protected by
// THREE independent guards, so removing only the first changes nothing. It is measured as defence
// in depth rather than dressed up as a mutation that reddens.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const Module = require('node:module');
const { execFileSync, spawnSync } = require('node:child_process');

const HERE = __dirname;
const IGNITE_SRC = path.join(HERE, '..', '..');
const OUT_PATH = path.join(HERE, 'probe-lane-room-open.out');

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
const tmuxScratch = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-room-tmux-'));
process.env.TMUX_TMPDIR = tmuxScratch;
delete process.env.TMUX;
delete process.env.TMUX_PANE;

const laneWatch = require('../lane-watch');
const { deriveLease } = require('../../runtime/lease/lease');

const LANE_WATCH_PATH = path.join(IGNITE_SRC, 'supervisor', 'lane-watch.js');
const LANE_WATCH_SRC = fs.readFileSync(LANE_WATCH_PATH, 'utf8');

// The mutation harness: recompiled IN MEMORY under its own real filename, so its relative
// `require`s resolve exactly as the original's do. `maybeReconcile` is stubbed in mutants only —
// mutation arms prove THIS file's guards, and a reconcile pass on a room-less fixture shells
// `recover-room.py` (120 s timeout). The green pass below uses the untouched module.
function mutantWatch(edits) {
  let src = LANE_WATCH_SRC;
  for (const [from, to] of edits) {
    if (!src.includes(from)) {
      throw new Error(`mutation anchor ABSENT in lane-watch.js — the arm would measure nothing: ${from}`);
    }
    src = src.replace(from, to);
  }
  const m = new Module(LANE_WATCH_PATH, null);
  m.filename = LANE_WATCH_PATH;
  m.paths = Module._nodeModulePaths(path.dirname(LANE_WATCH_PATH));
  m._compile(
    src.replace(/\bmaybeReconcile\(/g, '(function () { return { skipped: \'probe-mutant\' }; })('),
    LANE_WATCH_PATH);
  return m.exports.runLaneWatch;
}

// ── the fixture ───────────────────────────────────────────────────────────────────────────────
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-lane-room-'));
const workspace = path.join(tmp, 'workspace');
// The parent dir is `goals`, exactly as `<workspace>/.rbtv/goals` — `openGoalRoom` derives the
// workspace root from it and the lease reads `<root>/.rbtv/goals/<goal>`.
const goalsRoot = path.join(workspace, '.rbtv', 'goals');
fs.mkdirSync(goalsRoot, { recursive: true });

const TASKFORCE = 'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n'
  + 'tf-1,alpha,,claude,claude-opus-5,high,35,\n';

function makeGoal(goal, { lane, taskforce = true, sessions = null, cast = true }) {
  const dir = path.join(goalsRoot, goal);
  fs.mkdirSync(path.join(dir, 'seats', 'alpha'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'execution-lane'), `${lane}\n`);
  if (taskforce) fs.writeFileSync(path.join(dir, 'taskforce.csv'), TASKFORCE);
  fs.writeFileSync(path.join(dir, 'seats', 'alpha', 'seat.md'),
    cast
      ? ['---', 'seat: alpha', 'harness: claude', 'model: claude-opus-5', 'effort: high', '---', '', 'probe seat.', ''].join('\n')
      : ['---', 'seat: alpha', '---', '', 'probe seat, deliberately UNCAST.', ''].join('\n'));
  if (sessions) fs.writeFileSync(path.join(dir, 'sessions.csv'), sessions);
  return dir;
}

const G_DAEMON = 'probe-room-daemon';
const G_PAUSED = 'probe-room-paused';
const G_NOTF = 'probe-room-notf';
const G_CONSOLE = 'probe-room-console';
const G_RAN = 'probe-room-ran';
const G_UNCAST = 'probe-room-uncast';

makeGoal(G_DAEMON, { lane: 'daemon' });
makeGoal(G_PAUSED, { lane: 'paused daemon' });
makeGoal(G_NOTF, { lane: 'daemon', taskforce: false });
makeGoal(G_CONSOLE, { lane: 'console' });
// A goal whose seats HAVE run: one session row, and no room. Its room was closed after the fact.
makeGoal(G_RAN, {
  lane: 'daemon',
  sessions: 'seat,session-id,started,ended,pid,pid-starttime\nalpha,s-1,2026-08-27T00:00:00Z,2026-08-27T00:10:00Z,1,1\n',
});
// A daemon-lane goal with a taskforce whose ONLY seat is uncast: every row is lane-skipped, so
// the goal has NO LAUNCHABLE ROW and a room for it would be a room nothing can ever use.
makeGoal(G_UNCAST, { lane: 'daemon', cast: false });
const PROBE_GOALS = [G_DAEMON, G_PAUSED, G_NOTF, G_CONSOLE, G_RAN, G_UNCAST];

// ── the stub engine ───────────────────────────────────────────────────────────────────────────
//
// `seedGoal` is not simulated: it re-asks the REAL `deriveLease` the REAL `seeding.js#seedGoal`
// reads, at the same threshold (`lease.live`), and reports what that gate answers. So arm 1's
// "and then it seeds" is a measurement of the production gate, not an assertion about it.
function stubEngine(seedCalls) {
  return {
    heartStore: null,
    seedGoal({ goalFolder, goal }) {
      const lease = deriveLease({ workspaceRoot: workspace, goal });
      const live = Boolean(lease.ok && lease.live);
      seedCalls.push({ goal, live });
      if (!live) {
        return {
          goalFolder, goal, seats: [], enqueued: [], seeds: {}, skippedAsFinished: [],
          heldByOtherLane: {}, blockedOnOwner: {}, heldByStore: {}, states: {},
          readinessRefused: null, goalNotLive: 'probe: no live room', skewed: [], frozen: null,
          suppressedEnqueues: {}, enqueueUnfired: [], laneSkipped: {},
        };
      }
      return {
        goalFolder, goal, seats: ['alpha'], enqueued: ['alpha'], seeds: {}, skippedAsFinished: [],
        heldByOtherLane: {}, blockedOnOwner: {}, heldByStore: {}, states: {},
        readinessRefused: null, goalNotLive: null, skewed: [], frozen: null,
        suppressedEnqueues: {}, enqueueUnfired: [], laneSkipped: {},
      };
    },
  };
}

function tmux(args) {
  return spawnSync('tmux', args, { encoding: 'utf8', env: process.env });
}
function sessionNames() {
  const r = tmux(['list-sessions', '-F', '#{session_name}']);
  if (r.status !== 0) return [];
  return String(r.stdout || '').split('\n').map((s) => s.trim()).filter(Boolean);
}

// One pass. `runTmux` is left at its default (the real executor) unless a recorder is handed in.
async function pass(runLaneWatch, { runTmux } = {}) {
  const journal = [];
  const seedCalls = [];
  const res = await runLaneWatch({
    goalsRoot,
    engine: stubEngine(seedCalls),
    logger: (m) => journal.push(m),
    ...(runTmux ? { runTmux } : {}),
  });
  return { res, journal, seedCalls };
}
const openedLines = (journal) =>
  journal.filter((m) => m.message === 'room opened by the daemon lane (first seeding)');

// ── the arms ──────────────────────────────────────────────────────────────────────────────────
async function main() {
  say('# fixture');
  say(`goals root: ${goalsRoot}`);
  say(`tmux server: private (TMUX_TMPDIR=${tmuxScratch})`);
  say(`sessions before: ${JSON.stringify(sessionNames())}`);
  say('');

  const before = sessionNames();
  check('the private tmux server holds NO session before the pass', before.length === 0,
    JSON.stringify(before));

  // ARM 1 — the never-live daemon-lane goal.
  const p1 = await pass(laneWatch.runLaneWatch);
  const rooms = sessionNames();
  check('1 · a REAL tmux room named after the daemon-lane goal now exists',
    rooms.includes(G_DAEMON), JSON.stringify(rooms));
  check('1 · the pass REPORTS the room it opened, and only that one',
    p1.res.roomsOpened.length === 1 && p1.res.roomsOpened[0].goal === G_DAEMON,
    JSON.stringify(p1.res.roomsOpened));
  const opened1 = openedLines(p1.journal);
  check('1 · the journal carries `room opened by the daemon lane (first seeding)` EXACTLY once',
    opened1.length === 1 && opened1[0].goal === G_DAEMON,
    JSON.stringify(opened1.map((m) => m.goal)));
  const seeded1 = p1.seedCalls.find((c) => c.goal === G_DAEMON);
  check('1 · and the goal is SEEDED in the SAME pass — the real `deriveLease` says live at the '
    + 'threshold seeding reads', Boolean(seeded1 && seeded1.live), JSON.stringify(seeded1));

  // ARMS 2-4 — the goals that must be untouched, in the same pass.
  check('2 · the PAUSED goal got no room', !rooms.includes(G_PAUSED));
  check('2 · the PAUSED goal was not seeded', !p1.seedCalls.some((c) => c.goal === G_PAUSED));
  check('3 · the goal with NO taskforce.csv got no room', !rooms.includes(G_NOTF));
  check('3 · and its loud skip stays', p1.res.skipped.some((s) => s.goal === G_NOTF && s.reason === 'no-taskforce-yet'),
    JSON.stringify(p1.res.skipped.filter((s) => s.goal === G_NOTF)));
  check('4 · the CONSOLE-lane goal got no room', !rooms.includes(G_CONSOLE));
  check('4 · the CONSOLE-lane goal was not seeded', !p1.seedCalls.some((c) => c.goal === G_CONSOLE));
  check('1b · a daemon-lane goal whose only seat is UNCAST (no launchable row) got no room',
    !rooms.includes(G_UNCAST));
  check('6 · a goal whose seats HAVE run (sessions.csv rows) and whose room is gone is NOT '
    + 're-opened BY THIS LANE PASS — task 166\'s crashed-dead self-heal is `reconcile.js`\'s '
    + 'owed-gated room-only reopen, a separate mechanism (reconcile.selftest.js, B16)',
    !rooms.includes(G_RAN));
  check('exactly ONE room exists after the whole pass over six goals',
    rooms.length === 1, JSON.stringify(rooms));

  // ARM 5 — idempotence. A recorder proves no tmux command is composed at all this time.
  const calls = [];
  const p2 = await pass(laneWatch.runLaneWatch, { runTmux: (argv) => { calls.push(argv); return 'recorded'; } });
  check('5 · a SECOND pass runs NO tmux command (the live room is left exactly as it is)',
    calls.length === 0, JSON.stringify(calls));
  check('5 · and says nothing a second time', openedLines(p2.journal).length === 0);
  check('5 · still exactly one room', sessionNames().length === 1);

  // The refused arms compose nothing either — proven with the recorder on a fresh, room-less tree.
  say('');
  say('# the refusals compose NO tmux argv (recorder over a room-less tree)');
  tmux(['kill-session', '-t', `=${G_DAEMON}`]);
  const calls3 = [];
  const p3 = await pass(laneWatch.runLaneWatch, { runTmux: (argv) => { calls3.push(argv); return '%0 1'; } });
  const opened3 = calls3.map((a) => a[a.indexOf('-s') + 1]);
  check('only the daemon-lane never-live goal reaches tmux at all',
    calls3.length === 1 && opened3[0] === G_DAEMON, JSON.stringify(opened3));
  check('and the composed vector is the systemd-run-wrapped detached session with NO command '
    + 'after `-c <goal folder>`',
    calls3[0][0] === 'systemd-run' && calls3[0].includes('--collect')
      && calls3[0][calls3[0].indexOf('--') + 1] === 'tmux'
      && calls3[0][calls3[0].indexOf('--') + 2] === 'new-session'
      && calls3[0].includes('-d')
      && calls3[0][calls3[0].indexOf('-c') + 1] === path.join(goalsRoot, G_DAEMON)
      && !calls3[0].includes('-n'),
    JSON.stringify(calls3[0]));
  check('the scope unit is minted per attempt under the room prefix',
    /^--unit=rbtv-tmux-room-[0-9a-f-]{36}$/.test(calls3[0][4]), calls3[0][4]);
  void p3;

  // ── mutation arms ───────────────────────────────────────────────────────────────────────────
  //
  // ORDER IS LOAD-BEARING. The live-room arm needs the real room UP (that is the state its guard
  // exists for); every other arm needs it DOWN. So it runs first, then the room is killed. All
  // mutants run with a RECORDER, so no mutant ever creates a real session.
  say('');
  say('# mutation arms — each must go RED');

  async function runMutant(edits) {
    const calls = [];
    const journal = [];
    const seedCalls = [];
    try {
      await mutantWatch(edits)({
        goalsRoot,
        engine: stubEngine(seedCalls),
        logger: (m) => journal.push(m),
        runTmux: (argv) => { calls.push(argv); return '%0 1'; },
      });
    } catch (err) {
      return { calls: [], opened: [], openedLines: 0, threw: err.message };
    }
    return {
      calls,
      opened: calls.map((a) => a[a.indexOf('-s') + 1]),
      openedLines: openedLines(journal).length,
    };
  }
  async function mutantArm(name, edits, red) {
    const outcome = await runMutant(edits);
    check(`mutant · ${name} → RED`, red(outcome),
      JSON.stringify({ opened: outcome.opened, lines: outcome.openedLines, threw: outcome.threw }));
  }

  // With the room LIVE: dropping the live-room guard composes a SECOND new-session for it.
  await mutantArm('the live-room guard is dropped (a second room for a goal that has one)',
    [["if (lease.live) return { opened: false, reason: 'room-already-live' };", '']],
    (r) => r.opened.includes(G_DAEMON));
  // The control for that arm: unmutated, the same live state composes nothing (arm 5 above).

  tmux(['kill-session', '-t', `=${G_DAEMON}`]);
  say(`room killed; sessions now ${JSON.stringify(sessionNames())}`);

  // STALE CLAIM CORRECTED (found 2026-08-31, room-selfheal seat): this arm used to assert that
  // dropping `if (lane !== DAEMON)` exposes BOTH console and paused goals. It no longer does —
  // pause moved to its OWN earlier, independent `continue` (`laneIsPaused`, reading the
  // goal-state row rather than the `execution-lane` word: "the file is no longer a pause
  // surface"), so this mutation alone can only ever expose the CONSOLE-lane goal; a paused
  // daemon-lane goal stays protected by the guard below regardless. The old combined assertion
  // was therefore UNSATISFIABLE by this mutation and had been failing on HEAD independent of any
  // change to this file (confirmed: `git diff HEAD -- ignite/supervisor/lane-watch.js` is empty
  // for this seat's whole session). Split into two honest, independently-discriminating arms.
  await mutantArm('the daemon-lane guard is dropped (console gets a room; paused stays protected '
    + 'by its OWN separate gate)',
    [['if (lane !== DAEMON) {', 'if (false) {']],
    (r) => r.opened.includes(G_CONSOLE) && !r.opened.includes(G_PAUSED));

  await mutantArm('the laneIsPaused guard is dropped (a store-paused daemon-lane goal gets a room)',
    [["if (!goal.startsWith('_') && laneIsPaused(goalFolder, engine && engine.heartStore)) {", 'if (false) {']],
    (r) => r.opened.includes(G_PAUSED));

  await mutantArm('the launchable-row guard is dropped (a room for a goal whose only seat is uncast)',
    [["if (!launchable.length) return { opened: false, reason: 'no-launchable-row' };", '']],
    (r) => r.opened.includes(G_UNCAST));

  await mutantArm('the first-seeding guard is dropped (a room the owner closed is re-opened)',
    [['if (loadSessions(goalFolder).length) {', 'if (false) {']],
    (r) => r.opened.includes(G_RAN));

  await mutantArm('the opener is never called (the state this fix closed)',
    [['const room = openGoalRoom({', 'const room = ((x) => ({ opened: false }))({']],
    (r) => r.calls.length === 0);

  await mutantArm('the journal line is silenced (an operator cannot tell who opened the room)',
    [["'room opened by the daemon lane (first seeding)'", "'quietly opened'"]],
    (r) => r.openedLines === 0 && r.opened.includes(G_DAEMON));

  // ── DEFENCE IN DEPTH, and it is NOT dressed as a red arm ─────────────────────────────────────
  //
  // The taskforce-less goal is protected by THREE independent guards that `continue` before the
  // opener is ever reached: the `taskforce.csv` existence check, `readTaskforce`'s own refusal
  // (caught as `taskforce-unreadable`), and `uncastSeats`' (caught as `cast-unreadable`). Removing
  // only the first therefore changes NOTHING — which is the honest measurement, and stating it as
  // a red arm would be a lie about what the mutation proves.
  const depth = await runMutant([['if (!fs.existsSync(path.join(goalFolder, \'taskforce.csv\'))) {', 'if (false) {']]);
  check('3b · with the taskforce EXISTENCE guard removed the goal is STILL untouched — two '
    + 'further guards refuse before the opener (defence in depth, not a red arm)',
    !depth.opened.includes(G_NOTF), JSON.stringify(depth.opened));
}

let exitCode = 0;
// `main` is async because `runLaneWatch` is (it yields the event loop between goals), so the
// teardown below has to be chained off the promise — a plain `finally` block would kill the tmux
// server while the pass was still walking the tree.
main().catch((err) => {
  say(`FAIL  probe threw: ${err.stack || err.message}`);
  failures.push('probe threw');
}).finally(() => {
  // EVERY session this probe created dies with its own server. The box's real sessions were never
  // reachable from here — a different socket entirely.
  const left = sessionNames();
  say('');
  say(`sessions on the private server at teardown: ${JSON.stringify(left)}`);
  const stray = left.filter((s) => !PROBE_GOALS.includes(s));
  if (stray.length) { lines.push(`FAIL  a session this probe did not name was found: ${stray}`); failures.push('stray session'); }
  tmux(['kill-server']);
  fs.rmSync(tmuxScratch, { recursive: true, force: true });
  fs.rmSync(tmp, { recursive: true, force: true });
  exitCode = failures.length ? 1 : 0;
  say('');
  say(exitCode
    ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
    : 'RESULT: PASS — the daemon lane opens a never-live daemon-lane goal\'s FIRST room and seeds '
      + 'it in the same pass; paused, taskforce-less, console-lane and already-run goals are never '
      + 'touched; a live room is never re-opened.');
  say(`WALL_MS ${Date.now() - start}`);
  say(`EXIT ${exitCode}`);
  fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n');
  console.log(lines.join('\n'));
  process.exit(exitCode);
});
