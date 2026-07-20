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

  return { tmp, dataRoot, workRoot, defaultWorkdir, cfgPath, store, mgr, ticker, dbPath, feedPath, logPath };
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

function enqueueLaunchAgent(ctx, { jobId = 'launch-agent', profile, prompt = null, workdir = null, runAt, triggerKind = 'scheduled', intervalSeconds = null, maxFires = null, enqueuedBy = 'probe' }) {
  const args = { profile };
  if (prompt !== null && prompt !== undefined) args.prompt = prompt;
  if (workdir !== null && workdir !== undefined) args.workdir = workdir;
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
