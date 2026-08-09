'use strict';

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
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

function teardown(ctx) {
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

module.exports = { setup, teardown, now, writeOut, capture, fire };
