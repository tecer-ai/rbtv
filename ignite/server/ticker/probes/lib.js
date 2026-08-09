'use strict';

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');
const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createSpawnManager } = require('../../spawn/spawn');
const { createTicker } = require('../ticker');

function setup(configOverrides = {}, extraProfiles = {}) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p3-1-probe-'));
  const dataRoot = path.join(tmp, 'data');
  const workRoot = path.join(tmp, 'work');
  const defaultWorkdir = path.join(tmp, 'default');
  fs.mkdirSync(dataRoot, { recursive: true });
  fs.mkdirSync(workRoot, { recursive: true });
  fs.mkdirSync(defaultWorkdir, { recursive: true });

  // r-seats-only-architecture (3): every daemon spawn resolves a canonical seat folder or is
  // refused, so the fixture provides one INSIDE workdir_root; enqueueLaunchAgent defaults its
  // queue args' workdir to it (the caller-named-workdir home lane the ticker admits).
  // 7.607 E2a — GOAL-DIRECT: the goal folder IS the package; `runDir` is its alias here.
  const runDir = path.join(workRoot, '.rbtv', 'goals', 'probe-goal');
  const seatDir = path.join(runDir, 'seats', 'probe-seat');
  fs.mkdirSync(seatDir, { recursive: true });
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: probe-seat\n---\n');
  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,session-id,harness,workdir,pid,pid-starttime,tty,worktree-path,started,ended\n');

  const cfg = {
    bind: { host: '127.0.0.1', port: 7432 },
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
      'test-silent': {
        exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: workRoot,
        caps: { memory_max: '64M', runtime_max: '1h' },
      },
      'test-writer': {
        exec: { argv: ['bash', '-c', 'while true; do sleep 1; echo ping >> "$RANDOM"; done'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: workRoot,
        caps: { memory_max: '64M', runtime_max: '1h' },
      },
      ...(typeof extraProfiles === 'function' ? extraProfiles({ workRoot, dataRoot, defaultWorkdir }) : extraProfiles),
    },
  };
  const cfgPath = path.join(tmp, 'ignite.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const dbPath = path.join(tmp, 'heart.db');
  const feedPath = path.join(tmp, 'feed.jsonl');
  const logPath = path.join(tmp, 'ticker.log');
  const store = openHeartStore({ dbPath, profiles: cfg.profiles, tools: {}, workflows: {} });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });
  const ticker = createTicker({
    heartStore: store,
    spawnManager: mgr,
    config: { tick_interval_ms: 10000, stall_warn_ticks: 12, stall_halt_ticks: 24, max_live_agent_sessions: 2, slot_max_repeats: 10, ...configOverrides },
    feedPath,
    logPath,
  });

  return { tmp, dataRoot, workRoot, defaultWorkdir, seatDir, runDir, cfgPath, store, mgr, ticker, dbPath, feedPath, logPath };
}

// Forcibly reap a transient user unit spawned by this probe, clearing any
// failed state (a SIGKILLed unit lingers as `failed` until reset-failed).
// Best-effort and idempotent: safe on an already-dead or never-created unit.
function reapWorkerUnit(sessionId) {
  if (!sessionId) return;
  const unit = `rbtv-worker-${sessionId}.service`;
  for (const sig of ['SIGTERM', 'SIGKILL']) {
    try { execFileSync('systemctl', ['--user', 'kill', `--signal=${sig}`, unit], { stdio: 'ignore', timeout: 10000 }); } catch {}
  }
  try { execFileSync('systemctl', ['--user', 'stop', unit], { stdio: 'ignore', timeout: 10000 }); } catch {}
  try { execFileSync('systemctl', ['--user', 'reset-failed', unit], { stdio: 'ignore', timeout: 10000 }); } catch {}
}

// Guaranteed cleanup: kill every worker unit this probe spawned, on PASS or
// FAIL. Runs in every probe's finally() before the store closes, so an
// assertion that throws mid-probe never leaks a live `rbtv-worker-*` unit.
function teardown(ctx) {
  try {
    if (ctx && ctx.store && ctx.store.db) {
      for (const row of ctx.store.dump().jobs_log) {
        // systemd carrier (the VPS default): reap the transient unit by its
        // deterministic name. setsid carrier: SIGKILL the detached pgroup.
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

function registerLaunchAgentJob(ctx, jobId = 'launch-agent') {
  // Idempotent setup: [7.12] (acc661d) made duplicate registration a typed
  // E_JOB_EXISTS refusal; multi-scenario probes register the same job once per
  // scenario on one store, so an existing row is returned, never re-registered.
  const existing = ctx.store.getJob(jobId);
  if (existing) return existing;
  return ctx.store.registerJob({
    jobId,
    actionType: 'launch-agent',
    function: 'launch-agent',
    argsSchema: JSON.stringify({
      required: { profile: 'string' },
      optional: { prompt: 'string', workdir: 'string' },
    }),
  });
}

// The next never-yet-used seat home under the fixture's run, materialized to the minimal valid
// shape (folder + seat.md) the launch door demands. Counter lives on ctx, so seats stay distinct
// across every enqueue of one scenario and reset with the fixture.
function nextSeatHome(ctx) {
  ctx._seatSeq = (ctx._seatSeq || 0) + 1;
  const seat = `probe-seat-${ctx._seatSeq}`;
  const dir = path.join(ctx.runDir, 'seats', seat);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'seat.md'), `---\nseat: ${seat}\n---\n`);
  return dir;
}

function enqueueLaunchAgent(ctx, { jobId = 'launch-agent', profile, prompt = null, workdir = null, runAt, triggerKind = 'scheduled', intervalSeconds = null, maxFires = null, enqueuedBy = 'probe' }) {
  const args = { profile };
  if (prompt !== null && prompt !== undefined) args.prompt = prompt;
  // Default the home to a canonical seat folder (r-seats-only-architecture: an unhomed launch is
  // a refusal, and these probes test ticker mechanics, not the door — the door has its own
  // probes). An explicit workdir still wins.
  //
  // ⚠ A DISTINCT SEAT PER CALL, since task Q9 (`d-q9-door`). These probes enqueue SEVERAL
  // launches to exercise ticker mechanics (the agent cap, the recycle budget), and the idempotent
  // door now collapses repeat launches of ONE (run, seat) into the first — so a shared default
  // home silently turned "3 due launches" into 1 and the cap could never be reached. One seat per
  // launch is also the shape the mechanics actually meet in a run: a cap counts live sessions
  // ACROSS seats. A probe that means to re-launch ONE seat passes `workdir` explicitly and gets
  // the door's real behaviour.
  if (workdir !== null && workdir !== undefined) args.workdir = workdir;
  else if (ctx.seatDir) args.workdir = nextSeatHome(ctx);
  return ctx.store.enqueue({
    jobId,
    args: JSON.stringify(args),
    sessionMode: 'headless',
    triggerKind,
    runAt: typeof runAt === 'string' ? runAt : runAt.toISOString().replace(/\.\d{3}Z$/, 'Z'),
    intervalSeconds,
    maxFires,
    enqueuedBy,
  });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
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
  let skipped = 0;
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
      if (err.stack) lines.push(...err.stack.split('\n').slice(1, 4));
    })
    .finally(() => {
      const wall = Date.now() - start;
      lines.push(`status: ${status}`);
      lines.push(`exit: ${exit}`);
      lines.push(`wall_ms: ${wall}`);
      lines.push(`skipped_count: ${skipped}`);
      lines.push(`ended: ${now()}`);
      fs.writeFileSync(outPath, lines.join('\n') + '\n', 'utf8');
      return { name, status, exit, wall_ms: wall, outPath };
    })
    .finally(() => {
      process.exit(exit);
    });
}

module.exports = { setup, teardown, now, registerLaunchAgentJob, enqueueLaunchAgent, sleep, writeOut, capture };
