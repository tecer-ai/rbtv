'use strict';

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');
const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createSpawnManager } = require('../spawn');

// ⚠ A FIXTURE WORKSPACE MUST NOT LIVE UNDER `os.tmpdir()` OR `/tmp` — the envelope template bakes
// both into families 4 (`scratch-temp`) and 7 (`benign-cache-config-temp`) RW for every seat, so a
// workspace rooted there is simultaneously RW (temp family) and RO (family 5 `vault-wide-read`).
// The compiler authorizes that carve; `cage.js#lastCovering`, which `private-scope.js` asks about
// the workspace root, reads it as mixed access and refuses `E_LAUNCH_REFUSED conflict rw:/tmp …`.
// No real workspace sits inside the scratch family, so the shape is a fixture artifact, not a
// launch defect. `/var/tmp` is in no baked family — that is the whole reason it is used here.
const FIXTURE_TMP = '/var/tmp';

function fixtureRoot(prefix) {
  fs.mkdirSync(FIXTURE_TMP, { recursive: true });
  return fs.mkdtempSync(path.join(FIXTURE_TMP, prefix));
}

function setup() {
  const tmp = fixtureRoot('p2-2-probe-');
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
  fs.mkdirSync(path.join(workRoot, '.rbtv', 'mirror', 'x'), { recursive: true });  // envelope family 6 ro-binds {workspace}/.rbtv/mirror; a real workspace always has one
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: probe-seat\nharness: bash\nmodel: test-sleep\n---\n');
  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,session-id,harness,workdir,pid,pid-starttime,tty,worktree-path,started,ended\n');

  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(tmp, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'auto', kill_grace_seconds: 2 },
    default_workdir_root: defaultWorkdir,
    // ── THE FIXTURE'S LAUNCH SPECS, KEYED BY (harness, model) — 7.787 ────────────────────────
    // `profiles: { 'test-sleep': … }` went with the name layer (`#d-abolish-profile-names`); a
    // seat's CAST selects one now, so `seatWith(cast)` below writes the pair into seat.md.
    // ⚠ `bash -c … --model <name>` rather than a bare `sleep`: `profiles.js#validateSpecKey`
    // refuses at config LOAD when a spec's argv disagrees with its key, and a fixture must satisfy
    // that honestly. `bash -c 'exec sleep 3600' --model test-sleep` REALLY runs `sleep 3600` (the
    // trailing words land in `$0`/`$1`, unread) while genuinely pinning a checkable model.
    'launch-specs': {
      bash: {
        'test-sleep': {
          exec: { argv: ['bash', '-c', 'exec sleep 3600', '--model', 'test-sleep'], prompt: 'stdin' },
          session_ref: { source: 'cwd-implicit' },
          workdir_root: workRoot,
          caps: { memory_max: '64M', runtime_max: '1h' },
        },
        'test-headed': {
          exec: { argv: ['bash', '-c', 'exec sleep 3600', '--model', 'test-headed'], prompt: 'stdin' },
          session_ref: { source: 'cwd-implicit' },
          headed: { tui: { argv: ['sleep', '3600'] } },
          // An effort ladder, so the SEAT door's rung composition is exercisable (probe-tmux-seat
          // leg 9b). Inert for every caller that passes no rung — resolveEffort composes nothing
          // on a null — so no existing leg's argv changes.
          effort: { dialect: 'probe', rungs: ['0.1', '0.2'], argv: ['-t', '{effort}'], headed: true },
          workdir_root: workRoot,
          caps: { memory_max: '64M', runtime_max: '1h' },
        },
        'test-forker': {
          exec: { argv: ['bash', '-c', 'sleep 3600 & sleep 3600 & wait', '--model', 'test-forker'], prompt: 'stdin' },
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
          exec: { argv: ['bash', '-c', 'exec true', '--model', 'test-quick'], prompt: 'stdin' },
          session_ref: { source: 'cwd-implicit' },
          workdir_root: workRoot,
          caps: { memory_max: '64M', runtime_max: '1h' },
        },
      },
    },
  };
  const cfgPath = path.join(tmp, 'spawn.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const dbPath = path.join(tmp, 'heart.db');
  const store = openHeartStore({ dbPath });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });
  store.config.launchSpecs = mgr.config.launchSpecs;   // the composition root's own assignment
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
// EXITS, and this fixture's `test-sleep`/`test-headed`/`test-forker` specs run `sleep 3600`: a
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

// ⚠ NO `profile` ARGUMENT (7.787). A launch carries nothing profile-shaped; what a spawn runs is
// the CAST in the seat descriptor at `workdir`. So `cast` here is not a request that travels with
// the row — it is this fixture WRITING that descriptor, which is where a real seat's cast comes
// from too (`materialize-seats.py`). It names a MODEL of the fixture's `bash` launch specs.
function fire(ctx, { cast = 'test-sleep', sessionMode = 'headless', workdir = null, enqueuedBy = 'probe' }) {
  if (workdir === null) workdir = ctx.seatDir;
  if (workdir) castSeat(workdir, cast);
  const args = JSON.stringify({ workdir });
  const row = ctx.store.recordExecutionStart({
    jobId: 'launch-agent',
    actionType: 'launch-agent',
    args,
    enqueuedBy,
    sessionMode,
    firedTick: tickCounter++,
    firedAt: new Date(),
    workdir,
  });
  return row;
}

// CAST AN EXISTING SEAT FOLDER — rewrite its `seat.md` frontmatter to name one of the fixture's
// launch specs. This is the ONLY way a probe selects what a spawn runs since
// `#d-abolish-profile-names`, and it is the same surface production uses: a descriptor written by
// `materialize-seats.py` from the workflow's bindings sheet.
function castSeat(seatDir, model, harness = 'bash') {
  const seat = path.basename(seatDir);
  fs.mkdirSync(seatDir, { recursive: true });
  fs.writeFileSync(path.join(seatDir, 'seat.md'),
    `---\nseat: ${seat}\nharness: ${harness}\nmodel: ${model}\n---\n`);
  return seatDir;
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
      // A probe that could not RUN its legs in this process — bwrap refusing a nested namespace
      // inside a caged sitting is the measured case — throws with `code: 'E_INOPERATIVE'`. It is
      // graded INOPERATIVE with exit 2 (the suite's own code for a self-declared could-not-run),
      // never PASS, and distinct from a FAIL that measured something and found it wrong.
      const inoperative = Boolean(err) && err.code === 'E_INOPERATIVE';
      status = inoperative ? 'INOPERATIVE' : 'FAIL';
      exit = inoperative ? 2 : 1;
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

module.exports = { setup, fixtureRoot, teardown, now, writeOut, capture, fire, reapWorkerUnit, castSeat };
