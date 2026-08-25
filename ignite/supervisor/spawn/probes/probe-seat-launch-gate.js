'use strict';

// Task 7.11 §4a — LAUNCH-TIME GATE PROBES. Pre-registered bars P1, P2, P3 (+ the P9 launch leg).
//
// THE EVIDENCE RULE (design §6): "Wrong-folder refusals must be REAL refusals: no pane, no unit,
// no store row past `launching`, proven by absence." A typed error object is NOT the pass
// condition here — every leg re-checks the filesystem and the store AFTER the refusal and asserts
// that nothing was created. A gate that throws loudly while still having mkdir'd a session dir
// and appended a row would satisfy the error check and fail the actual bar.

require('../../../deploy/probe-self-isolate').selfIsolateTmux(); // solo-run tmux isolation (task 7.630) — no-op under the runner
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');
const { execFileSync } = require('node:child_process');
const { capture, fixtureRoot } = require('./lib');
const { openHeartStore, closeHeartStore } = require('../../../state-store/heart/heart-store');
const { createSpawnManager } = require('../spawn');

// ── 7.607 E2a — GOAL-DIRECT, AND "NOT LIVE" IS A GOAL WITH NO ROOM ────────────────────────────
//
// The tree carried a LIVE run (run-1) and a CLOSED run (run-0) of ONE goal, and P2 launched into
// the closed one. There is no run compartment and no register left, so the two states are now two
// GOALS: `testgoal`, which has a room, and `finishedgoal`, which has an equally complete, rostered
// seat and no room at all — a historical seat folder of a finished execution, which is exactly the
// case the ruling says must grant nothing.
//
// The room is REAL, on an ISOLATED `TMUX_TMPDIR` socket, because `spawnSeat` resolves its own
// lease through the real binary. The box's default tmux server carries the owner's attached
// session and is neither read as evidence nor extended here.
function fixture() {
  const root = fixtureRoot('g4-launch-');
  const ws = path.join(root, 'ws');
  const goalsDir = path.join(ws, '.rbtv', 'goals');
  const goalDir = path.join(goalsDir, 'testgoal');
  const runDir = goalDir;                                        // the goal folder IS the package
  const closedRunDir = path.join(goalsDir, 'finishedgoal');      // …and this goal is not executing
  const seatDir = path.join(runDir, 'seats', 'mine');
  const imposterDir = path.join(runDir, 'seats', 'imposter');
  const closedSeatDir = path.join(closedRunDir, 'seats', 'mine');
  const interimDir = path.join(ws, '.rbtv', 'sessions', 'exec-7');
  for (const d of [seatDir, imposterDir, closedSeatDir, interimDir]) fs.mkdirSync(d, { recursive: true });
  fs.mkdirSync(path.join(ws, '.rbtv', 'mirror', 'x'), { recursive: true });  // envelope family 6 ro-binds {workspace}/.rbtv/mirror; a real workspace always has one

  fs.writeFileSync(path.join(goalsDir, 'goals.csv'),
    'name,created,due,type,status\ntestgoal,2026-07-27,,one-shot,active\nfinishedgoal,2026-07-27,,one-shot,active\n');
  for (const rd of [runDir, closedRunDir]) {
    // the `tmpfs:{goalDir}/runs` mountpoint the shipped template still needs (spawn.js's E2a note)
    fs.mkdirSync(path.join(rd, 'runs'), { recursive: true });
    fs.writeFileSync(path.join(rd, 'taskforce.csv'), 'taskforce-id,seat\ntf-1,mine\n');
    fs.writeFileSync(path.join(rd, 'sessions.csv'), 'seat,session-id,harness,workdir,pid,pid-starttime,tty,worktree-path,started,ended\n');
  }
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: mine\nharness: bash\nmodel: seat-probe\n---\n');
  fs.writeFileSync(path.join(closedSeatDir, 'seat.md'), '---\nseat: mine\nharness: bash\nmodel: seat-probe\n---\n');

  const dataRoot = path.join(root, 'data');
  fs.mkdirSync(dataRoot, { recursive: true });

  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(root, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'systemd', kill_grace_seconds: 2 },
    default_workdir_root: root,
    'launch-specs': {
      bash: {
      'seat-probe': {
        exec: { argv: ['bash', '-c', 'exec sleep 3600', '--model', 'seat-probe'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        headed: { tui: { argv: ['bash', '-c', 'exec sleep 3600', '--model', 'seat-probe'] } },
        workdir_root: goalsDir,
        caps: { memory_max: '64M', runtime_max: '1h' },
        sandbox: {
          NoNewPrivileges: true,
          ReadWritePaths: ['{workdir}'],
          SeatBinds: [
            // 7.607 E2b — the `{runDir}` slot and the `runs` tmpfs are RETIRED with the run
            // layer (design-lock item 8); the one `ro-bind:{goalDir}` covers what two lines did.
            'ro-bind:{goalDir}',
            'tmpfs:{goalDir}/seats', 'bind:{seatDir}', 'ro-bind:{seatDir}/seat.md',
          ],
        },
      },
      },
    },
  };
  const cfgPath = path.join(root, 'spawn.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const dbPath = path.join(root, '.rbtv', 'heart', 'heart.db');
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const store = openHeartStore({ dbPath });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });

  const roomTmpdir = path.join(os.tmpdir(), `e2a-lg-${process.pid}`);
  fs.mkdirSync(roomTmpdir, { recursive: true, mode: 0o700 });
  const savedTmpdir = process.env.TMUX_TMPDIR;
  const savedTmux = process.env.TMUX;
  const savedTmuxPane = process.env.TMUX_PANE;
  process.env.TMUX_TMPDIR = roomTmpdir;
  // $TMUX overrides TMUX_TMPDIR: run from inside a pane, every tmux call here — including the
  // reap's kill-server — would hit the DEFAULT server. Cleared so the redirect actually binds.
  delete process.env.TMUX;
  delete process.env.TMUX_PANE;
  execFileSync('tmux', ['new-session', '-d', '-s', 'testgoal', 'sleep', '600'],
    { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  const reapRoom = () => {
    try { execFileSync('tmux', ['kill-server'], { stdio: 'ignore' }); } catch { /* already gone */ }
    if (savedTmpdir === undefined) delete process.env.TMUX_TMPDIR; else process.env.TMUX_TMPDIR = savedTmpdir;
    if (savedTmux === undefined) delete process.env.TMUX; else process.env.TMUX = savedTmux;
    if (savedTmuxPane === undefined) delete process.env.TMUX_PANE; else process.env.TMUX_PANE = savedTmuxPane;
    try { fs.rmSync(roomTmpdir, { recursive: true, force: true }); } catch {}
  };
  return { root, ws, goalDir, runDir, seatDir, imposterDir, closedSeatDir, interimDir, store, mgr, dataRoot, reapRoom };
}

let tick = 1;
function fire(f) {
  return f.store.recordExecutionStart({
    jobId: 'launch-seat', actionType: 'launch-agent', args: '{}', enqueuedBy: 'probe',
    sessionMode: 'headed', firedTick: tick++, firedAt: new Date(), profile: 'seat-probe', workdir: null,
  });
}

// The absence half — re-read the world AFTER a refusal.
function worldAfter(f, seatDir) {
  const runDir = path.resolve(seatDir, '..', '..');
  const sessionsCsv = path.join(runDir, 'sessions.csv');
  return {
    sessionDirs: (() => { try { return fs.readdirSync(path.join(seatDir, 'sessions')); } catch { return []; } })(),
    csvRows: (() => { try { return fs.readFileSync(sessionsCsv, 'utf8').trim().split('\n').length - 1; } catch { return -1; } })(),
    units: (() => { try { return fs.readdirSync(path.join(f.dataRoot, 'logs')); } catch { return []; } })(),
  };
}

capture('probe-seat-launch-gate', async (lines) => {
  const f = fixture();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  const refuse = async (seatDir, seatName) => {
    const row = fire(f);
    try {
      await f.mgr.spawnSeat(row.exec_id, { room: 'probe-room', seatName, seatDir });
      return { threw: false };
    } catch (err) {
      const after = f.store.getExecution(row.exec_id);
      return { threw: true, code: err.code, message: err.message, status: after && after.status };
    }
  };

  try {
    // ── P1 — a seat dir that is not a seat folder at all: /tmp, and the flat interim path.
    for (const [label, dir] of [['/tmp', os.tmpdir()], ['.rbtv/sessions/<exec-id>', f.interimDir]]) {
      const before = worldAfter(f, f.seatDir);
      const r = await refuse(dir, 'mine');
      const after = worldAfter(f, f.seatDir);
      const nothingHappened = JSON.stringify(before) === JSON.stringify(after);
      // ⚠ THE EXPECTED CODE CHANGED AT 7.787, AND IT IS NOW THE ACCURATE ONE. These legs hand the
      // door a path that is NOT A SEAT FOLDER; they asserted `E_WORKDIR_ESCAPE` only because the
      // containment gate happened to run first, which described the fault by accident. With no
      // caller-named profile there is no spec to escape FROM until a seat declares one, so the
      // door answers what is actually wrong: no `seat.md`, therefore not a materialized seat.
      // `E_WORKDIR_ESCAPE` keeps its own coverage in `probe-workdir-gate`, whose escape legs now
      // hand it a real seat folder outside the spec's root.
      leg(`P1[${label}]`, 'refused, and NOTHING was created (absence-proven, not message-proven)',
        r.threw && r.code === 'E_NOT_A_SEAT_FOLDER' && nothingHappened && r.status !== 'running',
        `code=${r.code} store-status=${r.status} world-unchanged=${nothingHappened} (sessions dirs ${after.sessionDirs.length}, csv rows ${after.csvRows}, logs ${after.units.length})`);
    }

    // ── P2 — a complete, rostered seat of a goal that is NOT EXECUTING (no room).
    const before2 = worldAfter(f, f.closedSeatDir);
    const r2 = await refuse(f.closedSeatDir, 'mine');
    const after2 = worldAfter(f, f.closedSeatDir);
    leg('P2', 'a seat of a goal that is NOT EXECUTING is refused E_GOAL_NOT_LIVE, nothing created',
      r2.threw && r2.code === 'E_GOAL_NOT_LIVE' && JSON.stringify(before2) === JSON.stringify(after2) && r2.status !== 'running',
      `code=${r2.code} store-status=${r2.status} — ${r2.message.slice(0, 90)}`);

    // ── P3 — a hand-made seats/imposter/: right shape, no seat.md, not rostered.
    const before3 = worldAfter(f, f.imposterDir);
    const r3 = await refuse(f.imposterDir, null);
    const after3 = worldAfter(f, f.imposterDir);
    leg('P3', 'a hand-made imposter seat folder is refused E_NOT_A_SEAT_FOLDER, nothing created',
      r3.threw && r3.code === 'E_NOT_A_SEAT_FOLDER' && JSON.stringify(before3) === JSON.stringify(after3),
      `code=${r3.code} — ${r3.message.slice(0, 90)}`);

    // ── P3-ii — a supplied seat name contradicting the folder. The folder decides (G-111).
    const r3b = await refuse(f.seatDir, 'someone-else');
    leg('P3-ii', 'a seatName contradicting the folder is REFUSED, not preferred',
      r3b.threw && r3b.code === 'E_NOT_A_SEAT_FOLDER' && /never overrides/.test(r3b.message),
      `code=${r3b.code} — ${r3b.message.slice(0, 100)}`);

    // ── P9-launch — THE GATE MUST ALSO PASS THE LEGITIMATE CASE. Without this leg every bar above
    // is satisfied by a spawnSeat that refuses unconditionally.
    const row = fire(f);
    const dry = await f.mgr.spawnSeat(row.exec_id, { room: 'probe-room', seatName: 'mine', seatDir: f.seatDir, dryRun: true });
    const argv = (dry.wrappedArgv || []).join(' ');
    const chdirOk = argv.includes(`--chdir ${f.seatDir}`);
    const cageOk = Array.isArray(dry.seatCage) && dry.seatCage.length > 0;
    // ⚠ THE PEER-SEAT ARM MOVED WITH THE MODEL. The retired per-seat grant template hid sibling
    // seats behind `--tmpfs {goalDir}/seats`. The envelope has no such line: `seats/` is a
    // DAEMON-OWNED DIRECTORY (daemon-owned-records.yaml), so family 1's goal-folder RW is carved
    // by an RO bind over it — peers are readable and unwritable, which is the ruled shape.
    const peersReadOnly = argv.includes(`--ro-bind ${path.join(f.runDir, 'seats')}`);
    leg('P9-launch', 'a REAL seat composes: launch home is the seat folder, the cage is applied',
      Boolean(dry.dryRun) && chdirOk && cageOk && peersReadOnly,
      `chdir->seatDir=${chdirOk} cage-entries=${cageOk ? dry.seatCage.length : 0} peers-ro-bind=${peersReadOnly}`);

    // ── P10 — THE PRODUCTION CALL SHAPE (task 7.11, G9). `runtime/index.js` is the ONLY route to
    // spawnSeat (dispatch.js's error map says so, and a tree-wide grep confirms it), and it
    // supplies NO seatName: the folder is the identity, and the window name is DERIVED from it.
    //
    // This leg DISCRIMINATES, which is the whole reason it asserts the window name rather than
    // just "it composed": before the fix the fallback was `seatName || profileName`, so with no
    // seatName the window took the PROFILE's name ('seat-probe'). Asserting it is the seat's own
    // name ('mine') fails on pre-fix code and passes on post-fix code. A leg that only checked
    // "composed without throwing" would read green on both.
    const rowP = fire(f);
    const prod = await f.mgr.spawnSeat(rowP.exec_id, { room: 'probe-room', seatDir: f.seatDir, dryRun: true });
    const prodArgv = (prod.tmuxArgv || []).join(' ');
    const windowIsSeat = / -n mine( |$)/.test(prodArgv);
    const windowNotProfile = !/ -n seat-probe( |$)/.test(prodArgv);
    leg('P10', 'the production call shape (NO seatName) composes, and the window is named for the SEAT not the profile',
      Boolean(prod.dryRun) && prod.seat === 'mine' && windowIsSeat && windowNotProfile,
      `seat=${prod.seat} window-is-seat-name=${windowIsSeat} window-is-profile-name=${!windowNotProfile}`);

    // ── P10-ii — THE FIX MUST NOT WEAKEN THE GATE IT ROUTES AROUND. Dropping the caller's
    // seatName removes an identity ASSERTION; the refusal that fires when one IS supplied and
    // disagrees (P3-ii, the G-111 lesson) must survive untouched. A "fix" that made the gate
    // permissive would satisfy P10 and silently retire the protection.
    const r10b = await refuse(f.seatDir, `seat-${rowP.exec_id}`);
    leg('P10-ii', 'a supplied `seat-<execId>` STILL contradicts a real seat folder — the gate did not go permissive',
      r10b.threw && r10b.code === 'E_NOT_A_SEAT_FOLDER' && /never overrides/.test(r10b.message),
      `code=${r10b.code} — ${(r10b.message || '').slice(0, 90)}`);

    // ── And a dryRun must leave NO trace — it is what makes composition checkable off a live room.
    const afterDry = worldAfter(f, f.seatDir);
    leg('P-dry', 'dryRun writes nothing — no session dir, no session row',
      afterDry.sessionDirs.length === 0 && afterDry.csvRows === 0,
      `session dirs ${afterDry.sessionDirs.length}, csv rows ${afterDry.csvRows}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`launch gate probes failed: ${fails.join(', ')}`);
  } finally {
    f.reapRoom();
    try { closeHeartStore(); } catch {}
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
