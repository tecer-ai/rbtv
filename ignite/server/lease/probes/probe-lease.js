'use strict';

// probe-lease — 7.607 E1: the DERIVED LEASE is derived from LIVE EVIDENCE and from nothing stored.
//
// The claim under test is a negative one ("no stored status is read"), and a negative is the claim
// whose wrong answer and right answer look identical. So the probe does not look for a read that
// did not happen: it CONSTRUCTS the exact state a stored-status reader would get wrong and asserts
// the lease disagrees with it. Two of those are the run's own live defects:
//
//   L6  a `runs.csv` saying `state=open` with NO room  -> NOT live. This is 7.608's exact shape:
//       under the register that row refused every fresh start forever. If the lease could see the
//       file at all, this check goes red.
//   L7  a `runs.csv` saying `state=closed` WITH a room -> LIVE. The opposite direction, so the
//       check cannot be satisfied by a lease that simply always says "not live".
//
// ⚠ IT NEVER TOUCHES A REAL ROOM. Every tmux command runs against an ISOLATED SERVER — the probe
// points `TMUX_TMPDIR` at a scratch dir of its own and unsets `TMUX`/`TMUX_PANE`, so the socket it
// creates cannot be the box's default server and no `-t` can resolve against a live goal room (the
// owner's `d1-throwaway` acceptance run is on this box). The server is killed and the scratch dir
// removed at teardown, and the DEFAULT server's session inventory is asserted byte-identical
// before and after — "I touched nothing" is measured, not promised.
//
// ⚠ THE ANCESTRY VERIFIER IS PROVEN ABLE TO FAIL. A verifier that only ever sees good rows proves
// nothing about itself, so every green arm has its red twin built from the SAME row with ONE field
// changed: dead pid, mismatched starttime, live process outside the room. Each must be refused,
// and each is refused for a DIFFERENT reason, which is what makes the conjunction meaningful
// rather than one check wearing three hats.
//
// Capture truncated at module load, BEFORE any work (evidence-husk hazard). The process exit code
// is the truth; the footer is a hint. The check DENOMINATOR is declared before the first check
// runs and the run asserts it reached that total — a truncated run reads greener than a complete
// one (G-121).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-lease.out');
fs.writeFileSync(outPath, '');

const { deriveLease, describeLease, roomNamesForGoal, packageDirForRoom, defaultTmuxProbe } = require('../lease');

// 29 = 6 (pure predicate) + 9 (unreadable posture, incl. E3b's L3c socket-location trio + its gate
// arm) + 14 (live layer). The live layer's skip branch emits exactly 14 too, so a tmux-less box
// reaches the same denominator rather than shrinking it.
//
// ⚠ THIS NUMBER WAS WRONG ON THE FIRST RUN (declared 21, ran 23) AND THE ASSERTION IS WHAT SAID SO:
// every check passed and the probe still exited 1. Kept as the argument for the assertion existing.
const EXPECTED_CHECKS = 29;

const checks = [];
let skipped = 0;
function out(...args) {
  const line = args.join(' ');
  fs.appendFileSync(outPath, line + '\n');
  console.log(line);
}
function check(name, pass, detail = '') {
  checks.push({ name, pass: Boolean(pass) });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`);
}
function skip(name, why) {
  skipped += 1;
  checks.push({ name, pass: true });
  out(`SKIP  ${name}  — ${why}`);
}

const UNIQUE = `${process.pid}-${Date.now()}`;

// ── LAYER 1: the room predicate and the package mapping, pure ──────────────────────────────────

check('L1 the room predicate accepts the BARE GOAL NAME — design-lock item 2, one room per goal',
  roomNamesForGoal('gx', ['gx']).join() === 'gx');
check('⚠ L1 the E1 transitional `<goal>-run-N` arm is DELETED (E2b) — a legacy-named room no '
  + 'longer matches, so it can never contribute a grant or a verified seat',
  roomNamesForGoal('gx', ['gx-run-3']).length === 0);
check('⚠ L1 and NOTHING ELSE — a prefix match would hand one goal another goal\'s lease',
  roomNamesForGoal('gx', ['gx-other', 'gxy', 'gx-run-x', 'ygx', 'gx-run-']).length === 0,
  'gx-other/gxy/gx-run-x/ygx/gx-run- all refused');
check('L1 a goal name carrying regex metacharacters is matched LITERALLY, never as a pattern',
  roomNamesForGoal('g.x', ['gyx']).length === 0 && roomNamesForGoal('g.x', ['g.x']).length === 1);
check('L2 a room homes at the GOAL folder — the package IS the goal folder (item 8)',
  packageDirForRoom({ goalDir: '/w/g', goal: 'g', room: 'g' }) === '/w/g');
check('⚠ L2 and the mapping NEVER composes a runs/ segment again — the E1 legacy arm that mapped '
  + 'a room to `<goal>/runs/run-N` is deleted; that path does not exist under the new layout',
  !/runs/.test(packageDirForRoom({ goalDir: '/w/g', goal: 'g', room: 'g' })));

// ── LAYER 1b: UNREADABLE IS NOT EMPTY ─────────────────────────────────────────────────────────

const thrower = () => { throw new Error('tmux: command not found'); };
const unreadable = deriveLease({ workspaceRoot: '/w', goal: 'g', tmuxProbe: thrower });
check('⚠ L3 a tmux that THROWS yields { ok:false } — ignorance, NEVER a lease verdict. A resolver '
  + 'that returned "not live" here would let every caller start on a box whose tmux was broken',
  unreadable.ok === false && unreadable.live === undefined,
  JSON.stringify(unreadable.reason).slice(0, 90));
check('L3 the refusal NAMES the cause, so a caller\'s log says why it could not decide',
  /tmux is unreadable/.test(unreadable.reason) && /command not found/.test(unreadable.reason));
check('L3 a tmux reporting NO SESSIONS is a readable EMPTY, not an unreadable — the two are '
  + 'different answers and the module must not collapse them',
  (() => {
    const r = deriveLease({ workspaceRoot: '/w', goal: 'g', tmuxProbe: () => ({ sessions: '', panes: '' }) });
    return r.ok === true && r.live === false;
  })());

// ⚠ L3b — THE CLASSIFIER INSIDE `defaultTmuxProbe`, exercised for real. Every arm above injects a
// fake probe, so until these two rows nothing ever ran the one line that decides whether a real
// tmux failure is a legitimate EMPTY or an UNREADABLE — and a bare `error connecting` arm there
// silently reclassified EVERY connect failure as "no sessions" (§2 review, 2026-08-09). Both rows
// drive the REAL binary against an ISOLATED socket; neither hand-feeds a verdict.
//
// ⚠ `TMUX`/`TMUX_PANE` MUST BE UNSET, not just `TMUX_TMPDIR` set: inside a pane `$TMUX` names the
// socket outright and TMUX_TMPDIR is ignored, so an arm that only sets TMUX_TMPDIR silently reads
// the DEFAULT server — which is how the first draft of these two rows measured nothing at all.
function onIsolatedSocket(dir, fn) {
  const saved = { d: process.env.TMUX_TMPDIR, t: process.env.TMUX, p: process.env.TMUX_PANE };
  process.env.TMUX_TMPDIR = dir;
  delete process.env.TMUX;
  delete process.env.TMUX_PANE;
  try { return fn(); } finally {
    for (const [k, v] of [['TMUX_TMPDIR', saved.d], ['TMUX', saved.t], ['TMUX_PANE', saved.p]]) {
      if (v === undefined) delete process.env[k]; else process.env[k] = v;
    }
  }
}

check('L3b a FRESH socket dir with no server is a readable EMPTY — `error connecting … (No such '
  + 'file or directory)` carries the errno phrase and must stay an answer, not ignorance',
  (() => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lz-'));
    try {
      return onIsolatedSocket(dir, () => defaultTmuxProbe().sessions.trim() === '');
    } catch { return false; } finally {
      try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* scratch */ }
    }
  })());
check('⚠ L3b a connect failure that is NOT the no-server errno (an over-long socket path) THROWS '
  + 'rather than reporting an empty tmux — fail-OPEN on the primary evidence is the one posture '
  + 'this module may never take',
  (() => {
    const base = fs.mkdtempSync(path.join(os.tmpdir(), 'lz-'));
    // sun_path is 108 bytes; tmux appends `/tmux-<uid>/default`, so this overruns it by design.
    const dir = path.join(base, 'x'.repeat(120));
    try {
      fs.mkdirSync(dir, { recursive: true });
      onIsolatedSocket(dir, () => defaultTmuxProbe());
      return false;                       // it returned — the failure was swallowed
    } catch { return true; } finally {
      try { fs.rmSync(base, { recursive: true, force: true }); } catch { /* scratch */ }
    }
  })());

// ⚠⚠ L3c — THE MISCONFIGURED-SOCKET FAIL-OPEN, CLOSED (7.607 E3b, §2-review r17). The trio below
// is ONE layout with ONE variable — the socket LOCATION — and it is a trio on purpose: the two red
// arms alone are satisfied by a module that calls everything unreadable, and the green arm alone by
// the fail-open this closes. Measured before the fix: a live goal read `ok:true, live:false` against
// a server-less socket dir, i.e. "not executing", because tmux reports a missing socket DIRECTORY
// with the same `No such file or directory` phrase as a missing socket FILE. Every arm drives the
// REAL binary through `deriveLease`'s own default probe; none hand-feeds a verdict.
const L3C_WS = fs.mkdtempSync(path.join(os.tmpdir(), 'lz-ws-'));
fs.mkdirSync(path.join(L3C_WS, '.rbtv', 'goals', 'gsock'), { recursive: true });
fs.writeFileSync(path.join(L3C_WS, '.rbtv', 'goals', 'goals.csv'),
  'name,created,due,type,status\ngsock,2026-08-09,,one-shot,active\n');
const leaseAt = (dir) => onIsolatedSocket(dir, () => deriveLease({ workspaceRoot: L3C_WS, goal: 'gsock' }));

check('⚠⚠ L3c RED 1 — a socket dir that DOES NOT EXIST is UNREADABLE, never EMPTY. tmux silently '
  + 'falls back to the DEFAULT socket for a nonexistent TMUX_TMPDIR, so "no rooms" here would be a '
  + 'verdict read off somebody else\'s server',
  (() => {
    const r = leaseAt(path.join(os.tmpdir(), `lz-absent-${UNIQUE}`));
    return r.ok === false && r.live === undefined && /socket directory/.test(r.reason);
  })());
check('⚠⚠ L3c RED 2 — a socket dir that EXISTS but cannot be entered is UNREADABLE too. Permission '
  + 'is a second configuration fault reaching the same errno family, and the fix must not be keyed '
  + 'to absence alone',
  (() => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lz-noperm-'));
    try {
      fs.chmodSync(dir, 0o000);
      const r = leaseAt(dir);
      return r.ok === false && r.live === undefined;
    } finally {
      try { fs.chmodSync(dir, 0o700); fs.rmSync(dir, { recursive: true, force: true }); } catch { /* scratch */ }
    }
  })());
check('⚠⚠ L3c GREEN CONTROL — a REAL, readable socket dir with no server running is still a plain '
  + 'EMPTY (`ok:true, live:false`). Without this row the two above are satisfied by a module that '
  + 'refuses everything, which would take the daemon down rather than close a hole',
  (() => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lz-fresh-'));
    try {
      const r = leaseAt(dir);
      return r.ok === true && r.live === false;
    } finally { try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* scratch */ } }
  })());
check('⚠ L3c THE GATE ENGAGES: `seat-folder.checkGoalExecuting` — the command-time identity gate\'s '
  + 'and spawnSeat\'s shared L2 — REFUSES on that unreadable lease naming IGNORANCE, and admits '
  + 'nothing. A classification nothing consumes would close the hole on paper only',
  (() => {
    const { checkGoalExecuting } = require('../../seat-identity/seat-folder');
    const parsed = {
      workspaceRoot: L3C_WS,
      goal: 'gsock',
      goalsCsv: path.join(L3C_WS, '.rbtv', 'goals', 'goals.csv'),
    };
    const absent = path.join(os.tmpdir(), `lz-absent2-${UNIQUE}`);
    const v = onIsolatedSocket(absent, () => checkGoalExecuting(parsed));
    return v.ok === false && /UNREADABLE/.test(v.reason);
  })());
fs.rmSync(L3C_WS, { recursive: true, force: true });

// ── LAYER 2: live, against an ISOLATED tmux server ────────────────────────────────────────────

function tmuxAvailable() {
  try { execFileSync('tmux', ['-V'], { encoding: 'utf8', timeout: 5000 }); return true; } catch { return false; }
}

// The DEFAULT server's inventory, read BEFORE the isolation is installed and again after teardown.
function defaultServerSessions() {
  try {
    return execFileSync('tmux', ['list-sessions', '-F', '#{session_name}'],
      { encoding: 'utf8', timeout: 10000, env: { ...process.env, TMUX: '', TMUX_PANE: '' } })
      .split('\n').map((s) => s.trim()).filter(Boolean).sort().join(',');
  } catch { return ''; }
}

function starttimeOf(pid) {
  const raw = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
  return raw.slice(raw.lastIndexOf(')') + 2).trim().split(/\s+/)[22 - 3];
}

if (!tmuxAvailable()) {
  for (let i = 0; i < 14; i++) skip(`L4.${i} live lease layer`, 'tmux is not installed on this box');
} else {
  const before = defaultServerSessions();
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'rbtvlease-'));
  const isoEnv = { ...process.env, TMUX_TMPDIR: scratch };
  delete isoEnv.TMUX;
  delete isoEnv.TMUX_PANE;
  // The lease module reads process.env, so the isolation is installed on THIS process too.
  const savedEnv = { TMUX_TMPDIR: process.env.TMUX_TMPDIR, TMUX: process.env.TMUX, TMUX_PANE: process.env.TMUX_PANE };
  process.env.TMUX_TMPDIR = scratch;
  delete process.env.TMUX;
  delete process.env.TMUX_PANE;

  const itmux = (args, { allowFail = false } = {}) => {
    try { return execFileSync('tmux', args, { encoding: 'utf8', timeout: 10000, env: isoEnv }).trim(); } catch (e) {
      if (allowFail) return null;
      throw e;
    }
  };

  const wsRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'rbtvleasews-'));
  const GOAL = `zz-lease-${UNIQUE}`;
  const goalDir = path.join(wsRoot, '.rbtv', 'goals', GOAL);
  fs.mkdirSync(goalDir, { recursive: true });

  try {
    // L4 — NO ROOM. The branch that kills 7.608's gate half.
    let lease = deriveLease({ workspaceRoot: wsRoot, goal: GOAL });
    check('⚠ L4 a goal with NO ROOM is NOT LIVE — and this is the whole 7.608 fix: a fresh goal '
      + 'admits its start because nothing stored can say otherwise',
      lease.ok === true && lease.live === false && lease.rooms.length === 0);

    // L6 — the stored-status control, in the direction that deadlocked.
    fs.writeFileSync(path.join(goalDir, 'runs.csv'),
      'run-id,type,state,taskforce-ids,opened,closed\nrun-1,build,open,,2026-08-01,\n');
    lease = deriveLease({ workspaceRoot: wsRoot, goal: GOAL });
    check('⚠⚠ L6 THE NEGATIVE PROVEN POSITIVELY: a `runs.csv` row reading `state=open` with no '
      + 'room is STILL NOT LIVE. Under the register this exact row refused every start of this '
      + 'goal forever (7.608). A lease that could see the file at all fails here',
      lease.ok === true && lease.live === false);

    const room = GOAL;
    itmux(['new-session', '-d', '-s', room]);
    const panePid = Number(itmux(['list-panes', '-t', room, '-F', '#{pane_pid}']).split('\n')[0]);

    lease = deriveLease({ workspaceRoot: wsRoot, goal: GOAL });
    check('⚠ L7 THE OPPOSITE DIRECTION, so L6 cannot be satisfied by "always not live": the room '
      + 'exists, so the goal IS live — while the register still says `open` and would agree by '
      + 'accident. The next check breaks that accident',
      lease.ok === true && lease.live === true && lease.rooms[0].room === room);
    fs.writeFileSync(path.join(goalDir, 'runs.csv'),
      'run-id,type,state,taskforce-ids,opened,closed\nrun-1,build,closed,,2026-08-01,2026-08-02\n');
    lease = deriveLease({ workspaceRoot: wsRoot, goal: GOAL });
    check('⚠⚠ L7b THE ACCIDENT BROKEN: with the register now reading `state=closed` and the room '
      + 'still up, the goal is STILL LIVE. L6 and L7b disagree with the stored status in OPPOSITE '
      + 'directions, so no reading of runs.csv can produce both',
      lease.ok === true && lease.live === true);

    check('L8 the live room maps to the GOAL FOLDER as its package dir',
      lease.rooms[0].packageDir === goalDir);
    check('L8 the lease reports WHICH predicate it matched, so a reader need not find it in a comment',
      /room predicate|session name/.test(lease.evidence['room-predicate'] || ''));

    // ── the ancestry verifier, green arm then three red twins from the SAME row ────────────────
    const pkgDir = goalDir;
    const sessionsCsv = path.join(pkgDir, 'sessions.csv');
    const writeSeat = (pid, st) => fs.writeFileSync(sessionsCsv,
      `session-id,seat,harness,pid,pid-starttime,ended\ns1,builder,claude,${pid},${st},\n`);

    writeSeat(panePid, starttimeOf(panePid));
    lease = deriveLease({ workspaceRoot: wsRoot, goal: GOAL });
    check('⚠ L9 GREEN ARM: a row naming a LIVE process that IS the room\'s pane verifies',
      lease.seats.length === 1 && lease.seats[0].seat === 'builder', JSON.stringify(lease.seats));

    writeSeat(panePid, `${Number(starttimeOf(panePid)) + 1}`);
    check('⚠ L10 RED TWIN 1 — MISMATCHED STARTTIME is refused. Same live pid, one field changed: '
      + 'this is what defeats pid REUSE, so a dead seat\'s standing cannot be inherited',
      deriveLease({ workspaceRoot: wsRoot, goal: GOAL }).seats.length === 0);

    // A pid that is certainly not a live process: one past the kernel's own maximum.
    const deadPid = Number(fs.readFileSync('/proc/sys/kernel/pid_max', 'utf8').trim()) + 1;
    writeSeat(deadPid, '1');
    check('⚠ L11 RED TWIN 2 — a DEAD pid is refused. This is the ruling\'s "historical seat folders '
      + 'on disk grant nothing": the row survives the seat and must confer nothing',
      deriveLease({ workspaceRoot: wsRoot, goal: GOAL }).seats.length === 0);

    writeSeat(process.pid, starttimeOf(process.pid));
    check('⚠ L12 RED TWIN 3 — a process ALIVE but OUTSIDE the room is refused (this probe\'s own '
      + 'pid, which is genuinely running). Aliveness alone is not membership of the execution',
      deriveLease({ workspaceRoot: wsRoot, goal: GOAL }).seats.length === 0);

    writeSeat(panePid, starttimeOf(panePid));
    fs.appendFileSync(sessionsCsv, `s2,builder,claude,${panePid},${starttimeOf(panePid)},2026-08-09 10:00\n`);
    check('⚠ L13 a row carrying `ended` is a DEPARTED session and verifies nothing, even though '
      + 'its pid is alive and in the room — the record\'s own semantics, not an aliveness question',
      deriveLease({ workspaceRoot: wsRoot, goal: GOAL }).seats.length === 0);

    check('L14 describeLease() states the read-nothing-stored contract in the module\'s own words',
      /no runs\.csv|NONE/.test(describeLease()));

    itmux(['kill-session', '-t', room], { allowFail: true });
    check('⚠ L15 the room gone ⇒ the lease is gone, in the SAME process and with every file on '
      + 'disk unchanged. Nothing but the room moved, so nothing but the room decided',
      deriveLease({ workspaceRoot: wsRoot, goal: GOAL }).live === false);
  } finally {
    itmux(['kill-server'], { allowFail: true });
    for (const [k, v] of Object.entries(savedEnv)) {
      if (v === undefined) delete process.env[k]; else process.env[k] = v;
    }
    fs.rmSync(scratch, { recursive: true, force: true });
    fs.rmSync(wsRoot, { recursive: true, force: true });
  }
  check('⚠ L16 THE DEFAULT tmux SERVER IS UNTOUCHED — its session inventory is byte-identical '
    + 'before and after this probe. The owner\'s live acceptance room is on this box',
    defaultServerSessions() === before, `before=${before.slice(0, 60)}`);
}

const failed = checks.filter((c) => !c.pass);
out('');
out(`checks: ${checks.length} run (${EXPECTED_CHECKS} expected), ${failed.length} failed, ${skipped} skipped`);
if (checks.length !== EXPECTED_CHECKS) {
  out(`INCOMPLETE — ${checks.length} checks ran but ${EXPECTED_CHECKS} were declared`);
}
out(`probe-lease: ${failed.length === 0 && checks.length === EXPECTED_CHECKS ? 'PASS' : 'FAIL'} (${Date.now() - start}ms)`);
process.exit(failed.length === 0 && checks.length === EXPECTED_CHECKS ? 0 : 1);
