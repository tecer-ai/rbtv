'use strict';

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const yaml = require('js-yaml');
const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createSpawnManager } = require('../../spawn/spawn');
const { createTicker } = require('../ticker');
// 7.544 — ONE reaper implementation, owned by the spawn probe fixture (PRIN-11). Both fixtures
// spawn through the same carrier and leak the same `rbtv-worker-*` units; a second copy here is
// the same drift as a second rule.
const { reapWorkerUnit } = require('../../spawn/probes/lib');

function setup(configOverrides = {}, extraProfiles = {}, extraHarnesses = null) {
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
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: probe-seat\nharness: bash\nmodel: test-sleep\n---\n');
  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,session-id,harness,workdir,pid,pid-starttime,tty,worktree-path,started,ended\n');

  const cfg = {
    bind: { host: '127.0.0.1', port: 7432 },
    auth: { senders_file: path.join(tmp, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'auto', kill_grace_seconds: 2 },
    default_workdir_root: defaultWorkdir,
    // ── THE FIXTURE'S LAUNCH SPECS, KEYED BY (harness, model) — 7.787 ────────────────────────
    //
    // `profiles: { 'test-sleep': … }` is gone with the name layer (`#d-abolish-profile-names`).
    // These three are keyed by a pair like every real spec, and a SEAT'S CAST is what selects one
    // — `nextSeatHome(ctx, cast)` writes `harness:`/`model:` into the seat descriptor, which is the
    // only address a launch has now.
    //
    // ⚠ WHY `bash -c … --model <name>` RATHER THAN A BARE `sleep`. `profiles.js#validateSpecKey`
    // refuses at config LOAD when a spec's argv disagrees with the key it is filed under — that
    // guard is what makes the key trustworthy as an authority. A fixture must therefore satisfy it
    // honestly: `bash -c 'exec sleep 3600' --model test-sleep` REALLY runs `sleep 3600` (the two
    // trailing words land in `$0`/`$1`, which the script never reads) while genuinely pinning a
    // model the key can be checked against. Faking the guard off for fixtures would leave the one
    // check that makes the whole re-keying safe untested against the config shape probes use.
    'launch-specs': {
      bash: {
        'test-sleep': {
          exec: { argv: ['bash', '-c', 'exec sleep 3600', '--model', 'test-sleep'], prompt: 'stdin' },
          session_ref: { source: 'cwd-implicit' },
          workdir_root: workRoot,
          caps: { memory_max: '64M', runtime_max: '1h' },
        },
        'test-silent': {
          exec: { argv: ['bash', '-c', 'exec sleep 3600', '--model', 'test-silent'], prompt: 'stdin' },
          session_ref: { source: 'cwd-implicit' },
          workdir_root: workRoot,
          caps: { memory_max: '64M', runtime_max: '1h' },
        },
        'test-writer': {
          exec: { argv: ['bash', '-c', 'while true; do sleep 1; echo ping >> "$RANDOM"; done', '--model', 'test-writer'], prompt: 'stdin' },
          session_ref: { source: 'cwd-implicit' },
          workdir_root: workRoot,
          caps: { memory_max: '64M', runtime_max: '1h' },
        },
        ...(typeof extraProfiles === 'function' ? extraProfiles({ workRoot, dataRoot, defaultWorkdir }) : extraProfiles),
      },
      // A probe whose fixture must be classified as a DIFFERENT harness files its extras here
      // instead — `harnessOf` reads `basename(exec.argv[0])`, so the key and the argv have to
      // agree (`profiles.js#validateSpecKey` enforces exactly that at LOAD).
      ...(typeof extraHarnesses === 'function' ? extraHarnesses({ workRoot, dataRoot, defaultWorkdir }) : (extraHarnesses || {})),
    },
  };
  const cfgPath = path.join(tmp, 'ignite.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const dbPath = path.join(tmp, 'heart.db');
  const feedPath = path.join(tmp, 'feed.jsonl');
  const logPath = path.join(tmp, 'ticker.log');
  const store = openHeartStore({ dbPath, tools: {}, workflows: {} });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });
  // The composition root's own assignment (engine/index.js): seeding and any per-seat cage read
  // reach the launch specs through the store.
  store.config.launchSpecs = mgr.config.launchSpecs;
  const ticker = createTicker({
    heartStore: store,
    spawnManager: mgr,
    config: { tick_interval_ms: 10000, max_live_agent_sessions: 2, slot_max_repeats: 10, ...configOverrides },
    feedPath,
    logPath,
  });

  return { tmp, dataRoot, workRoot, defaultWorkdir, seatDir, runDir, cfgPath, store, mgr, ticker, dbPath, feedPath, logPath };
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
    // 7.787 — `required` is EMPTY: `launch-agent` carries nothing profile-shaped, and the daemon
    // derives the cast from the seat's own descriptor at spawn.
    argsSchema: JSON.stringify({
      required: {},
      optional: { prompt: 'string', workdir: 'string' },
    }),
  });
}

// The next never-yet-used seat home under the fixture's run, materialized to the minimal valid
// shape (folder + seat.md) the launch door demands. Counter lives on ctx, so seats stay distinct
// across every enqueue of one scenario and reset with the fixture.
// ⚠ THE DESCRIPTOR CARRIES THE CAST (7.787). A seat with no `harness:`/`model:` is UNCAST and
// every launch door refuses it (`E_UNCAST_SEAT`) — there is no caller-named profile left to fall
// back to — so the fixture's seats declare one, exactly as a materialized seat does.
const DEFAULT_CAST = { harness: 'bash', model: 'test-sleep' };

function nextSeatHome(ctx, cast = DEFAULT_CAST) {
  ctx._seatSeq = (ctx._seatSeq || 0) + 1;
  const seat = `probe-seat-${ctx._seatSeq}`;
  const dir = path.join(ctx.runDir, 'seats', seat);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'seat.md'),
    `---\nseat: ${seat}\nharness: ${cast.harness}\nmodel: ${cast.model}\n---\n`);
  return dir;
}

// `cast` selects WHICH of the fixture's launch specs the seat this call homes at is cast to. It
// replaces the old `profile` NAME argument (7.787): the queue row carries no such value any more,
// so what a launch runs is decided where it is now decided everywhere — in the seat's descriptor.
function enqueueLaunchAgent(ctx, { jobId = 'launch-agent', cast = DEFAULT_CAST, prompt = null, workdir = null, runAt, triggerKind = 'scheduled', intervalSeconds = null, maxFires = null, enqueuedBy = 'probe' }) {
  const args = {};
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
  else if (ctx.seatDir) args.workdir = nextSeatHome(ctx, cast);
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

module.exports = { setup, teardown, now, registerLaunchAgentJob, enqueueLaunchAgent, nextSeatHome, DEFAULT_CAST, sleep, writeOut, capture };
