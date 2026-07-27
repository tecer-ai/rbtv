'use strict';

// Task 7.11 §4a — LAUNCH-TIME GATE PROBES. Pre-registered bars P1, P2, P3 (+ the P9 launch leg).
//
// THE EVIDENCE RULE (design §6): "Wrong-folder refusals must be REAL refusals: no pane, no unit,
// no store row past `launching`, proven by absence." A typed error object is NOT the pass
// condition here — every leg re-checks the filesystem and the store AFTER the refusal and asserts
// that nothing was created. A gate that throws loudly while still having mkdir'd a session dir
// and appended a row would satisfy the error check and fail the actual bar.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');
const { capture } = require('./lib');
const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createSpawnManager } = require('../spawn');

// A goal tree with a LIVE run (run-1), a CLOSED run (run-0), a real seat, an imposter folder, and
// the flat interim `.rbtv/sessions/` dir the task retires for seat spawns.
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'g4-launch-'));
  const ws = path.join(root, 'ws');
  const goalsDir = path.join(ws, '.rbtv', 'goals');
  const goalDir = path.join(goalsDir, 'testgoal');
  const runDir = path.join(goalDir, 'runs', 'run-1');
  const closedRunDir = path.join(goalDir, 'runs', 'run-0');
  const seatDir = path.join(runDir, 'seats', 'mine');
  const imposterDir = path.join(runDir, 'seats', 'imposter');
  const closedSeatDir = path.join(closedRunDir, 'seats', 'mine');
  const interimDir = path.join(ws, '.rbtv', 'sessions', 'exec-7');
  for (const d of [seatDir, imposterDir, closedSeatDir, interimDir]) fs.mkdirSync(d, { recursive: true });

  fs.writeFileSync(path.join(goalsDir, 'goals.csv'), 'goal-id,state\ntestgoal,open\n');
  fs.writeFileSync(path.join(goalDir, 'runs.csv'), 'run-id,state\nrun-1,open\nrun-0,closed\n');
  for (const rd of [runDir, closedRunDir]) {
    fs.writeFileSync(path.join(rd, 'taskforce.csv'), 'taskforce-id,seat\ntf-1,mine\n');
    fs.writeFileSync(path.join(rd, 'sessions.csv'), 'seat,session-id,harness,workdir,pid,pid-starttime,tty,worktree-path,started,ended\n');
  }
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: mine\n---\n');
  fs.writeFileSync(path.join(closedSeatDir, 'seat.md'), '---\nseat: mine\n---\n');

  const dataRoot = path.join(root, 'data');
  fs.mkdirSync(dataRoot, { recursive: true });

  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(root, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'systemd', kill_grace_seconds: 2 },
    default_workdir_root: root,
    profiles: {
      'seat-probe': {
        exec: { argv: ['bash', '-c', 'sleep 3600'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        headed: { tui: { argv: ['bash', '-c', 'sleep 3600'] } },
        workdir_root: goalsDir,
        caps: { memory_max: '64M', runtime_max: '1h' },
        sandbox: {
          NoNewPrivileges: true,
          ReadWritePaths: ['{workdir}'],
          SeatBinds: [
            'ro-bind:{goalDir}', 'tmpfs:{goalDir}/runs', 'ro-bind:{runDir}',
            'tmpfs:{runDir}/seats', 'bind:{seatDir}', 'ro-bind:{seatDir}/seat.md',
          ],
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
  return { root, ws, goalDir, runDir, seatDir, imposterDir, closedSeatDir, interimDir, store, mgr, dataRoot };
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
      await f.mgr.spawnSeat(row.exec_id, 'seat-probe', { room: 'probe-room', seatName, seatDir });
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
      leg(`P1[${label}]`, 'refused, and NOTHING was created (absence-proven, not message-proven)',
        r.threw && r.code === 'E_WORKDIR_ESCAPE' && nothingHappened && r.status !== 'running',
        `code=${r.code} store-status=${r.status} world-unchanged=${nothingHappened} (sessions dirs ${after.sessionDirs.length}, csv rows ${after.csvRows}, logs ${after.units.length})`);
    }

    // ── P2 — a seat of a CLOSED run.
    const before2 = worldAfter(f, f.closedSeatDir);
    const r2 = await refuse(f.closedSeatDir, 'mine');
    const after2 = worldAfter(f, f.closedSeatDir);
    leg('P2', 'a seat of a CLOSED run is refused E_RUN_NOT_LIVE, nothing created',
      r2.threw && r2.code === 'E_RUN_NOT_LIVE' && JSON.stringify(before2) === JSON.stringify(after2) && r2.status !== 'running',
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
    const dry = await f.mgr.spawnSeat(row.exec_id, 'seat-probe', { room: 'probe-room', seatName: 'mine', seatDir: f.seatDir, dryRun: true });
    const argv = (dry.wrappedArgv || []).join(' ');
    const chdirOk = argv.includes(`--chdir ${f.seatDir}`);
    const cageOk = Array.isArray(dry.seatCage) && dry.seatCage.length > 0;
    const peerAbsent = argv.includes(`--tmpfs ${path.join(f.runDir, 'seats')}`);
    leg('P9-launch', 'a REAL seat composes: launch home is the seat folder, the cage is applied',
      Boolean(dry.dryRun) && chdirOk && cageOk && peerAbsent,
      `chdir->seatDir=${chdirOk} cage-entries=${cageOk ? dry.seatCage.length : 0} peer-tmpfs=${peerAbsent}`);

    // ── And a dryRun must leave NO trace — it is what makes composition checkable off a live room.
    const afterDry = worldAfter(f, f.seatDir);
    leg('P-dry', 'dryRun writes nothing — no session dir, no session row',
      afterDry.sessionDirs.length === 0 && afterDry.csvRows === 0,
      `session dirs ${afterDry.sessionDirs.length}, csv rows ${afterDry.csvRows}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`launch gate probes failed: ${fails.join(', ')}`);
  } finally {
    try { closeHeartStore(); } catch {}
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
