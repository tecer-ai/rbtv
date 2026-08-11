'use strict';

// MC7 / store row 7.449 — THE TRACE PRECONDITION AT BOTH DAEMON DOORS.
//
// The clause under test is a PRECONDITION, not a writer. The daemon already reaches a
// trace-creating act twice (`spawn`'s at-dispatch door and `spawnSeat`'s seat door, both through
// `seat-identity/csv.js appendRow`) — and `appendRow` opens with
//
//     if (!exists || header.length === 0) return { appended: false, reason: 'no header …' }
//
// inside a `try` whose only failure arm is a warn line. So on a package the kit never launched
// into, the daemon's row silently does not land, the run's `sessions.csv` never comes into
// existence, and the edge-runner's gate 3 refuses the whole package.
//
// WHAT THE FIX IS, AND WHAT IT DELIBERATELY IS NOT. It is NOT a second writer: adding
// `coord.py session-open` on top of a door that already appends yields TWO rows per launch. It is
// a guarantee that the file exists WITH THE OWNER'S HEADER, after which the door's own existing
// append lands — so the row keeps the daemon's own `session-id` (task 7.73's join key) and the
// real `pid`/`pid-starttime` pair the seat-identity gate decides on. T1/T5 assert exactly those
// two cells, not a row count, because a row count cannot tell the daemon's row from a foreign one.
//
// Every leg is written to DISCRIMINATE: T3 is the same door on a package whose trace ALREADY has a
// header, and it must come out unchanged — a fix that rewrote a live header would move the column
// positions of every live reader. T4 is the failure arm: a spawn that cannot come up must leave NO
// row and NO file, which is the false-completion the ordering exists to prevent.

require('../../../deploy/probe-self-isolate').selfIsolateTmux(); // solo-run tmux isolation (task 7.630) — no-op under the runner
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');
const { capture, reapWorkerUnit } = require('./lib');
const { requirePythonCmd } = require('../../../lib/python-cmd');
const { listSystemdUnits } = require('../carrier');
const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createSpawnManager } = require('../spawn');

// The trace schema is OWNED BY coord.py. This probe asks that owner for it, independently of the
// code under test, rather than spelling it a second time here — a probe carrying its own copy of
// the header would stay green against a fix that hardcoded a STALE header, which is precisely the
// failure this leg exists to catch.
const KIT = path.resolve(__dirname, '../../../team-kit');
function ownerHeader() {
  return execFileSync(requirePythonCmd(), ['-c',
    'import sys; sys.path.insert(0, sys.argv[1]); import coord; print(",".join(coord.SESSIONS_COLS))',
    KIT], { encoding: 'utf8', timeout: 60000 }).trim();
}

// A canonical goal tree with a LIVE run and one rostered seat. `sessions.csv` is NOT written here:
// each leg decides its own precondition, which is the whole variable under test.
function fixture(over) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'mc7-trace-'));
  const ws = path.join(root, 'ws');
  const goalsDir = path.join(ws, '.rbtv', 'goals');
  const goalDir = path.join(goalsDir, 'tracegoal');
  const runDir = goalDir;   // 7.607 E2a — goal-direct: the goal folder IS the package
  const seatDir = path.join(runDir, 'seats', 'tracer');
  fs.mkdirSync(seatDir, { recursive: true });
  fs.writeFileSync(path.join(goalsDir, 'goals.csv'), 'name,created,due,type,status\ntracegoal,2026-08-06,,one-shot,active\n');
  fs.writeFileSync(path.join(runDir, 'taskforce.csv'), 'taskforce-id,seat\ntf-1,tracer\n');
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: tracer\n---\n');

  const dataRoot = path.join(root, 'data');
  fs.mkdirSync(dataRoot, { recursive: true });
  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(root, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'auto', kill_grace_seconds: 2 },
    default_workdir_root: ws,
    profiles: {
      'trace-probe': {
        exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: ws,
        caps: { memory_max: '64M', runtime_max: '1h' },
        ...(over || {}),
      },
    },
  };
  const cfgPath = path.join(root, 'spawn.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));
  const dbPath = path.join(root, '.rbtv', 'heart', 'heart.db');
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const store = openHeartStore({ dbPath });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });
  return { root, ws, goalDir, runDir, seatDir, sessionsCsv: path.join(runDir, 'sessions.csv'), store, mgr, dataRoot };
}

function rows(csvPath) {
  if (!fs.existsSync(csvPath)) return null;
  const raw = fs.readFileSync(csvPath, 'utf8').trim();
  if (!raw) return { header: [], data: [] };
  const lines = raw.split('\n');
  const header = lines[0].split(',');
  return {
    header,
    data: lines.slice(1).filter(Boolean).map((l) => {
      const cells = l.split(',');
      return Object.fromEntries(header.map((h, i) => [h, cells[i] === undefined ? '' : cells[i]]));
    }),
  };
}

const inode = (p) => { try { return fs.statSync(p).ino; } catch { return null; } };

// ── 7.607 E2a — THE ROOM IS THE GOAL'S NAME, AND IT LIVES ON AN ISOLATED SOCKET ────────────────
//
// Two changes, and both are forced by the lease. (1) `spawnSeat`'s L2 now asks whether the GOAL is
// executing, and the evidence is a room named for it (design-lock item 2) — so a room called
// `mc7-trace-<pid>` would leave every seat leg refused before it reached the door under test.
// (2) The socket is a scratch `TMUX_TMPDIR` rather than the box's default server: the default
// server carries the owner's attached session, and a probe may neither add a session to it nor
// read it as evidence. `process.pid` still keeps two concurrent suite runs apart — now in the
// SOCKET PATH rather than the session name, which is what lets the name be the goal's.
const ROOM = 'tracegoal';
const ROOM_TMPDIR = path.join(os.tmpdir(), `e2a-trace-${process.pid}`);
const tmuxFixture = (args) => execFileSync('tmux', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });

capture('probe-trace-header', async (lines) => {
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  const HEADER = ownerHeader();
  lines.push(`owner header (coord.py SESSIONS_COLS, asked at run time): ${HEADER}`);

  // The isolated fixture server, up for the whole probe: T5 launches INTO it and T6 needs the
  // goal's lease live so its refusal comes from the missing WINDOW rather than from L2.
  const savedTmpdir = process.env.TMUX_TMPDIR;
  const savedTmux = process.env.TMUX;
  const savedTmuxPane = process.env.TMUX_PANE;
  fs.mkdirSync(ROOM_TMPDIR, { recursive: true, mode: 0o700 });
  process.env.TMUX_TMPDIR = ROOM_TMPDIR;
  // $TMUX overrides TMUX_TMPDIR: run from inside a pane, every tmux call here — including the
  // finally's kill-server — would hit the DEFAULT server. Cleared so the redirect actually binds.
  delete process.env.TMUX;
  delete process.env.TMUX_PANE;

  // ── 7.544 — THIS PROBE'S OWN UNIT TEARDOWN, AND THE COUNT THAT PROVES IT ────────────────────
  //
  // Its legs fire the at-dispatch door on a `sleep 3600` profile, and `--collect` reaps a
  // transient unit only when it EXITS — so before this, each full run of the suite left THREE
  // live `rbtv-worker-*` units behind for an hour (T1/T2/T3; T4's spawn is refused by systemd-run
  // and creates none, and T5/T6 go through the SEAT door, whose scope is `rbtv-seat-*`).
  //
  // This fixture is hand-built rather than lib's `setup()`, so lib's `teardown()` — which reaps —
  // never ran for it. The ids are collected as they are minted and reaped in the outer `finally`,
  // which covers the normal, assertion-failure and crash paths alike. The before/after census is
  // the p3-6 instrument (`deploy/p3-6-bwrap-write.js`), scoped to the units THIS run created so a
  // concurrent probe's units can never make it read clean.
  const spawnedIds = [];
  const unitCensus = () => listSystemdUnits('rbtv-worker-').map((u) => u.unitName.replace(/\.service$/, ''));
  const unitsBefore = unitCensus();
  lines.push(`rbtv-worker-* units before: ${unitsBefore.length} (systemctl --user list-units --type=service 'rbtv-worker-*')`);

  const fixtures = [];
  // The heart store is a per-process singleton (`E_SECOND_WRITER`), so each leg's fixture closes
  // the previous one's store rather than the legs sharing a package — a shared package could not
  // vary the precondition, which is the only variable these legs exist to change.
  const make = (over) => {
    try { closeHeartStore(); } catch { /* first leg has none */ }
    const f = fixture(over); fixtures.push(f); return f;
  };
  const dispatch = async (f, profile) => {
    const row = f.store.recordExecutionStart({
      jobId: 'launch-agent', actionType: 'launch-agent', args: JSON.stringify({ profile, workdir: f.seatDir }),
      enqueuedBy: 'probe', sessionMode: 'headless', firedTick: 1, firedAt: new Date(),
      profile, workdir: f.seatDir,
    });
    try {
      await f.mgr.spawn(row.exec_id, profile, 'headless', null, f.seatDir, 'probe');
      return { threw: false, execId: row.exec_id };
    } catch (err) {
      return { threw: true, execId: row.exec_id, code: err.code, message: err.message };
    } finally {
      // 7.544 — record the session id whether the spawn returned or THREW: the throwing path is
      // the one that can still have left a unit behind (systemd-run may accept the unit and fail
      // afterwards), so reading the id from the store rather than from spawn's return value is
      // what makes the abnormal path reapable too.
      try { spawnedIds.push(f.store.getExecution(row.exec_id).session_id); } catch { /* no row */ }
    }
  };
  // Every leg asserts the SAME three properties of the landed row, so a leg cannot pass by a
  // different mechanism than its sibling: the header is the owner's, there is exactly ONE row, and
  // that row is THE DAEMON'S OWN — its `session-id` equal to this dispatch's jobs_log key and its
  // `pid` non-empty. H4 of the C-4 map (one row, but written by a foreign act) is separated here
  // and nowhere else.
  const assertOneDaemonRow = (f, r) => {
    const t = rows(f.sessionsCsv);
    if (!t) return { ok: false, why: 'no sessions.csv at all', t };
    const exec = f.store.getExecution(r.execId);
    const one = t.data.length === 1 ? t.data[0] : null;
    return {
      ok: t.header.join(',') === HEADER && !!one && one.seat === 'tracer'
        && one['session-id'] === exec.session_id && one['session-id'] !== ''
        && one.pid !== '' && one.started !== '' && !one.ended,
      why: `header-is-owners=${t.header.join(',') === HEADER} rows=${t.data.length} `
        + `seat=${one && one.seat} row.session-id=${one && one['session-id']} `
        + `jobs_log.session_id=${exec.session_id} identical=${!!one && one['session-id'] === exec.session_id} `
        + `pid=${one && one.pid}`,
      t,
    };
  };

  try {
    // ── T1 — TRACE ABSENT (the measured defect): the at-dispatch door on a package the kit never
    // launched into. This is the state that makes gate 3 refuse the whole package.
    {
      const f = make();
      const pre = fs.existsSync(f.sessionsCsv);
      const r = await dispatch(f, 'trace-probe');
      const v = assertOneDaemonRow(f, r);
      leg('T1', 'AT-DISPATCH DOOR, trace file ABSENT: the launch creates it with the OWNER\'S header and exactly ONE row — the daemon\'s own',
        !r.threw && !pre && v.ok, `pre-existing=${pre} refused=${r.threw} ${v.why}`);
    }

    // ── T2 — TRACE EMPTY AND HEADERLESS: `composeCageFor`'s service-seat pre-create (MC6 F-6a-2).
    // This file passes gate 3's `exists()` and can never hold a row. The INODE assertion is the
    // whole reason this leg is separate from T1: that file is RO-BOUND into the seat's cage, so a
    // header written by replacing the inode would be invisible from inside the cage — correct
    // outside, useless inside, and no row-level instrument can see the difference.
    {
      const f = make();
      fs.writeFileSync(f.sessionsCsv, '');
      const ino0 = inode(f.sessionsCsv);
      const r = await dispatch(f, 'trace-probe');
      const v = assertOneDaemonRow(f, r);
      const ino1 = inode(f.sessionsCsv);
      leg('T2', 'AT-DISPATCH DOOR, trace file EMPTY AND HEADERLESS (the poisoned trace): one daemon row, and THE INODE IS PRESERVED so a cage ro-bind of it still sees the row',
        !r.threw && v.ok && ino0 !== null && ino0 === ino1,
        `inode before=${ino0} after=${ino1} preserved=${ino0 === ino1} ${v.why}`);
    }

    // ── T3 — CONTROL: a trace that ALREADY carries a header, in a DIFFERENT spelling from the
    // owner's. The door must append into it and leave the header byte-identical. Without this leg
    // a fix that unconditionally rewrote the header would read green above and would silently move
    // every live reader's column positions.
    {
      const f = make();
      const LIVE = 'seat,session-id,harness,workdir,pid,pid-starttime,tty,worktree-path,started,ended';
      fs.writeFileSync(f.sessionsCsv, LIVE + '\n');
      const r = await dispatch(f, 'trace-probe');
      const t = rows(f.sessionsCsv);
      const exec = f.store.getExecution(r.execId);
      leg('T3', 'CONTROL — a trace that already has a (different) header is APPENDED to and its header is left byte-identical',
        !r.threw && t.header.join(',') === LIVE && t.data.length === 1
        && t.data[0]['session-id'] === exec.session_id && t.data[0].pid !== '',
        `header-unchanged=${t.header.join(',') === LIVE} rows=${t.data.length} identical-session-id=${t.data[0] && t.data[0]['session-id'] === exec.session_id}`);
    }

    // ── T4 — THE FAILURE ARM: a spawn that does not come up leaves NO row and NO trace file. This
    // is the false completion the ordering exists to prevent (a seat that never booted must not
    // look traced).
    //
    // ⚠ THE PROVOCATION IS THE CARRIER, NOT THE BINARY, and that was measured rather than assumed:
    // a profile naming a NONEXISTENT BINARY does NOT throw here — `systemd-run` accepts the unit
    // and the failure surfaces asynchronously, so `spawn` returns normally and the row is written.
    // That first attempt read PASS-shaped for the wrong reason. An unparseable cap makes
    // `systemd-run` itself refuse, synchronously, which is the "never came up" this leg means.
    {
      const f = make({ caps: { memory_max: 'not-a-size' } });
      const r = await dispatch(f, 'trace-probe');
      const t = rows(f.sessionsCsv);
      leg('T4', 'FAILURE ARM — a spawn that does not come up leaves NO row and NO trace file',
        r.threw && t === null,
        `refused=${r.threw} code=${r.code} sessions.csv exists=${fs.existsSync(f.sessionsCsv)} rows=${t ? t.data.length : 'n/a'}`);
    }
    // ── T5 — THE SEAT DOOR, trace file ABSENT. The other member of MC5's census, and the one that
    // matters most: this row is what the seat-identity gate matches live /proc against, so its
    // `pid`/`pid-starttime` pair must be REAL. It is driven through the daemon's own `spawnSeat`
    // into a THROWAWAY tmux room — never this run's — because a hand-composed argv would not be
    // the door under test.
    {
      const f = make({ headed: { tui: { argv: ['sleep', '90'] } } });
      let roomUp = false;
      try {
        tmuxFixture(['new-session', '-d', '-s', ROOM, '-n', 'idle', 'sleep', '120']);
        roomUp = true;
        const row = f.store.recordExecutionStart({
          jobId: 'launch-agent', actionType: 'launch-agent', args: JSON.stringify({ profile: 'trace-probe' }),
          enqueuedBy: 'probe', sessionMode: 'headed', firedTick: 1, firedAt: new Date(),
          profile: 'trace-probe', workdir: f.seatDir,
        });
        const pre = fs.existsSync(f.sessionsCsv);
        let threw = null;
        try {
          await f.mgr.spawnSeat(row.exec_id, 'trace-probe', { room: ROOM, seatName: 'tracer', seatDir: f.seatDir, enqueuedBy: 'probe' });
        } catch (err) { threw = err.code || err.message; }
        const v = assertOneDaemonRow(f, { execId: row.exec_id });
        const one = v.t && v.t.data[0];
        leg('T5', 'SEAT DOOR (live tmux), trace file ABSENT: the launch creates it with the OWNER\'S header and ONE daemon row carrying a REAL identity pair',
          !threw && !pre && v.ok && one && one['pid-starttime'] !== '',
          `pre-existing=${pre} threw=${threw} pid-starttime=${one && one['pid-starttime']} ${v.why}`);
      } finally {
        // The SESSION stays up for T6 (which needs this goal's lease live so its refusal comes from
        // the missing window, not from L2); the whole fixture SERVER is reaped in the outer finally.
        void roomUp;
      }
    }
    // ── T6 — THE FAILURE ARM AT THE SEAT DOOR. T4 proves it at the at-dispatch door only, and the
    // two doors fail at different calls (the carrier vs `runTmux`), so one does not stand in for the
    // other. Here the room does not exist, so `tmux new-window` fails and `spawnSeat` throws BEFORE
    // its append is reached: no row, and no trace file brought into existence by the attempt.
    {
      const f = make({ headed: { tui: { argv: ['sleep', '90'] } } });
      const row = f.store.recordExecutionStart({
        jobId: 'launch-agent', actionType: 'launch-agent', args: JSON.stringify({ profile: 'trace-probe' }),
        enqueuedBy: 'probe', sessionMode: 'headed', firedTick: 1, firedAt: new Date(),
        profile: 'trace-probe', workdir: f.seatDir,
      });
      let threw = null;
      try {
        await f.mgr.spawnSeat(row.exec_id, 'trace-probe', { room: `${ROOM}-absent`, seatName: 'tracer', seatDir: f.seatDir, enqueuedBy: 'probe' });
      } catch (err) { threw = err.code || err.message; }
      const t = rows(f.sessionsCsv);
      leg('T6', 'FAILURE ARM AT THE SEAT DOOR — a seat spawn into a room that does not exist leaves NO row and NO trace file',
        !!threw && t === null,
        `threw=${threw} sessions.csv exists=${fs.existsSync(f.sessionsCsv)} rows=${t ? t.data.length : 'n/a'}`);
    }
  } finally {
    for (const sid of spawnedIds) reapWorkerUnit(sid);
    try { tmuxFixture(['kill-server']); } catch { /* already gone */ }
    if (savedTmpdir === undefined) delete process.env.TMUX_TMPDIR; else process.env.TMUX_TMPDIR = savedTmpdir;
    if (savedTmux === undefined) delete process.env.TMUX; else process.env.TMUX = savedTmux;
    if (savedTmuxPane === undefined) delete process.env.TMUX_PANE; else process.env.TMUX_PANE = savedTmuxPane;
    try { fs.rmSync(ROOM_TMPDIR, { recursive: true, force: true }); } catch { /* teardown */ }
    try { closeHeartStore(); } catch { /* teardown */ }
    for (const f of fixtures) { try { fs.rmSync(f.root, { recursive: true, force: true }); } catch { /* teardown */ } }
  }

  // ── T7 (7.544) — NO LEAKED UNIT. Measured against the units this run itself created, not the
  // raw total, so a unit spawned by a concurrent probe neither fails this leg nor hides a leak.
  // Read IMMEDIATELY after teardown: waiting out the `sleep 3600` would make the check vacuous.
  const unitsAfter = unitCensus();
  const leaked = unitsAfter.filter((u) => !unitsBefore.includes(u));
  leg('T7', 'TEARDOWN — every rbtv-worker-* unit this run created is gone the moment the run ends (no unit outlives its fixture)',
    leaked.length === 0,
    `before=${unitsBefore.length} after=${unitsAfter.length} spawned=${spawnedIds.length} leaked=${JSON.stringify(leaked)}`);

  if (fails.length) throw new Error(`legs failed: ${fails.join(', ')}`);
  lines.push('legs: ALL PASS');
});
