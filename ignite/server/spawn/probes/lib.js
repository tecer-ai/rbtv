'use strict';

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');
const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createSpawnManager } = require('../spawn');

function setup() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p2-2-probe-'));
  const dataRoot = path.join(tmp, 'data');
  const workRoot = path.join(tmp, 'work');
  const defaultWorkdir = path.join(tmp, 'default');
  const escapedir = path.join(tmp, 'escape');
  fs.mkdirSync(dataRoot, { recursive: true });
  fs.mkdirSync(workRoot, { recursive: true });
  fs.mkdirSync(defaultWorkdir, { recursive: true });
  fs.mkdirSync(escapedir, { recursive: true });

  // r-seats-only-architecture (3): every daemon spawn resolves a canonical seat folder or is
  // refused, so the fixture provides one INSIDE workdir_root for the probes' live-spawn legs.
  // 7.607 E2a — GOAL-DIRECT: `<ws>/.rbtv/goals/<goal>/seats/<seat>/`, no run compartment. The
  // goal-level sessions.csv carries the real 7.37 header so the at-dispatch row appends cleanly
  // rather than warning. `runDir` survives here as a LOCAL VARIABLE NAME the consuming probes
  // destructure, and it IS the goal dir: the cage slot of that name is retired (7.607 E2b), so
  // this is a fixture's own spelling and no longer a template contract.
  const runDir = path.join(workRoot, '.rbtv', 'goals', 'probe-goal');
  const seatDir = path.join(runDir, 'seats', 'probe-seat');
  fs.mkdirSync(seatDir, { recursive: true });
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: probe-seat\n---\n');
  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,session-id,harness,workdir,pid,pid-starttime,tty,worktree-path,started,ended\n');

  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(tmp, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'auto', kill_grace_seconds: 2 },
    default_workdir_root: defaultWorkdir,
    profiles: {
      'test-sleep': {
        exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: workRoot,
        caps: { memory_max: '64M', runtime_max: '1h' },
      },
      'test-headed': {
        exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        headed: { tui: { argv: ['sleep', '3600'] } },
        // An effort ladder, so the SEAT door's rung composition is exercisable (probe-tmux-seat
        // leg 9b). Inert for every caller that passes no rung — resolveEffort composes nothing on
        // a null — so no existing leg's argv changes.
        effort: { dialect: 'probe', rungs: ['0.1', '0.2'], argv: ['-t', '{effort}'] },
        workdir_root: workRoot,
        caps: { memory_max: '64M', runtime_max: '1h' },
      },
      'test-forker': {
        exec: { argv: ['bash', '-c', 'sleep 3600 & sleep 3600 & wait'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: workRoot,
        caps: { memory_max: '64M', runtime_max: '1h' },
      },
      // (the former test-argvlast fixture is gone WITH its carriage: `argv-last` was removed
      // from the vocabulary — batch-08 item 4 half A — and now fails config load, proven by
      // probe-carriage-vocab.js.)
      // Exits 0 immediately: exit-marker + accepted-prompt legs need a worker
      // that finishes on its own (no kill, no lingering unit).
      'test-quick': {
        exec: { argv: ['true'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: workRoot,
        caps: { memory_max: '64M', runtime_max: '1h' },
      },
    },
  };
  const cfgPath = path.join(tmp, 'spawn.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const dbPath = path.join(tmp, 'heart.db');
  const store = openHeartStore({ dbPath });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });
  return { tmp, dataRoot, workRoot, defaultWorkdir, escapedir, seatDir, runDir, cfgPath, store, mgr, dbPath };
}

// Forcibly reap a transient user unit spawned by a probe, clearing any failed state (a SIGKILLed
// unit lingers as `failed` until reset-failed). Best-effort and idempotent: safe on an
// already-dead or never-created unit. THE ONE implementation — the ticker probe fixture
// (`server/ticker/probes/lib.js`) imports this rather than carrying a second copy.
function reapWorkerUnit(sessionId) {
  if (!sessionId) return;
  const unit = `rbtv-worker-${sessionId}.service`;
  for (const sig of ['SIGTERM', 'SIGKILL']) {
    try { execFileSync('systemctl', ['--user', 'kill', `--signal=${sig}`, unit], { stdio: 'ignore', timeout: 10000 }); } catch {}
  }
  try { execFileSync('systemctl', ['--user', 'stop', unit], { stdio: 'ignore', timeout: 10000 }); } catch {}
  try { execFileSync('systemctl', ['--user', 'reset-failed', unit], { stdio: 'ignore', timeout: 10000 }); } catch {}
}

// 7.544 — GUARANTEED UNIT TEARDOWN. `--collect` garbage-collects a transient unit only when it
// EXITS, and this fixture's `test-sleep`/`test-headed`/`test-forker` profiles run `sleep 3600`: a
// probe that spawned one and then killed it only on its happy path left a live `rbtv-worker-*`
// behind for an hour on every assertion failure or crash, and one that never killed it leaked on
// EVERY run. A leaked unit is indistinguishable from a live one, so anything counting workers to
// judge system state reads an inflated number.
//
// Every probe calls teardown() from a `finally`, so reaping here covers the normal, the
// assertion-failure, and the crash path in one place — no reaper, no sweeper, no cron: the units
// are never left behind in the first place. Runs BEFORE the store closes, because the store is
// where the session ids live. The ticker probe fixture has done exactly this since its own leak;
// this fixture was the half that never got it.
function teardown(ctx) {
  try {
    if (ctx && ctx.store && ctx.store.db) {
      for (const row of ctx.store.dump().jobs_log) {
        reapWorkerUnit(row.session_id);
        if (row.carrier === 'setsid' && row.pid) {
          try { process.kill(-row.pid, 'SIGKILL'); } catch {}
        }
      }
    }
  } catch {}
  try { closeHeartStore(); } catch {}
  try { fs.rmSync(ctx.tmp, { recursive: true, force: true }); } catch {}
}

function now() {
  return new Date().toISOString();
}

let tickCounter = 1;

function fire(ctx, { profile, sessionMode = 'headless', workdir = null, enqueuedBy = 'probe' }) {
  const args = JSON.stringify({ profile, workdir });
  const row = ctx.store.recordExecutionStart({
    jobId: 'launch-agent',
    actionType: 'launch-agent',
    args,
    enqueuedBy,
    sessionMode,
    firedTick: tickCounter++,
    firedAt: new Date(),
    profile,
    workdir,
  });
  return row;
}

function writeOut(name, lines) {
  const outPath = path.join(__dirname, `${name}.out`);
  fs.writeFileSync(outPath, lines.join('\n') + '\n', 'utf8');
  return outPath;
}

function capture(name, fn) {
  const start = Date.now();
  const outPath = path.join(__dirname, `${name}.out`);
  let status = 'UNKNOWN';
  let exit = 0;
  const lines = [`probe: ${name}`, `started: ${now()}`, `command: node probes/${name}.js`];
  // 7.50: stamp the capture at START. A probe that dies before its completion write used to
  // leave the PREVIOUS run's PASS on disk; now an aborted run leaves an explicit INCOMPLETE.
  fs.writeFileSync(outPath, lines.join('\n') + '\nstatus: INCOMPLETE\n', 'utf8');

  return fn(lines)
    .then(() => {
      status = 'PASS';
      exit = 0;
    })
    .catch((err) => {
      status = 'FAIL';
      exit = 1;
      lines.push(`error: ${err.code || err.name}: ${err.message}`);
    })
    .finally(() => {
      const wall = Date.now() - start;
      lines.push(`status: ${status}`);
      lines.push(`exit: ${exit}`);
      lines.push(`wall_ms: ${wall}`);
      lines.push(`ended: ${now()}`);
      fs.writeFileSync(outPath, lines.join('\n') + '\n', 'utf8');
      return { name, status, exit, wall_ms: wall, outPath };
    })
    .finally(() => {
      process.exit(exit);
    });
}

module.exports = { setup, teardown, now, writeOut, capture, fire, reapWorkerUnit };
