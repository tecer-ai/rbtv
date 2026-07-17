'use strict';

// Probe harness for the headed/pty extension (task 6.2). Mirrors server/spawn/probes/lib.js: a
// temp heart store + spawn manager + pty host + deterministic test profiles, exercised on the
// LIVE VPS with the daemon's real carrier (systemd-run --user + bwrap + dtach). Each probe proves
// its spec criterion by OBSERVED system state (D79) — cgroup membership, systemctl status, the
// captured screen bytes, the shim status file — never by POSIX/library reasoning.
//
// UNIT SAFETY: the pty host names units rbtv-worker-<uuid> (buildSystemdRunArgs, unchanged — this
// task's allowlist forbids editing carrier.js). Each session id is a fresh uuid, so probe units
// NEVER collide with the LIVE rbtv-ignite daemon's worker units, and teardown kills EXACTLY the
// unit names this harness created (tracked in ctx.units) — NEVER a blanket rbtv-worker-* kill.
//
// PROBE OUTPUT: .out captures are written to $RBTV_PTY_PROBE_OUT (this run: the dispatch
// scratchpad, per the addendum — NOT committed into the repo). The probe SCRIPTS are committed.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');
const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createSpawnManager } = require('../../spawn/spawn');
const { createPtyHost } = require('../pty-host');

// A deterministic pty "TUI": clears + prints its current frame, and on each stdin line re-renders
// "LINE<n>:<line>" at row 3. It REPAINTS on SIGWINCH exactly as a real TUI does — so dtach's
// redraw-on-attach (`-r winch`) rebuilds the vt model after an attach/reattach (Design 2 caveat 2).
// Proves keys->pty->TUI, that capture reflects rendered state, and the reattach-repaint path.
const RENDERER_SRC =
  "let n=0,frame='READY';const w=s=>process.stdout.write(s);" +
  "const paint=()=>w('\\x1b[2J\\x1b[H'+frame+'\\r\\n');paint();" +
  "process.on('SIGWINCH',paint);" +
  "process.stdin.setEncoding('utf8');let b='';" +
  "process.stdin.on('data',d=>{b+=d;let i;while((i=b.indexOf('\\n'))>=0){" +
  "const l=b.slice(0,i).replace(/\\r$/,'');b=b.slice(i+1);n++;" +
  "frame='\\x1b[3;1HLINE'+n+':'+l;paint();}});" +
  "setTimeout(()=>process.exit(0),60000);";

// Prints its own argv (minus the interpreter), repainting on SIGWINCH, so the argv prompt-carriage
// delivery is observable in a post-attach capture.
const ECHO_ARGV_SRC =
  "const w=s=>process.stdout.write(s);" +
  "const frame='ARGV:'+JSON.stringify(process.argv.slice(1));" +
  "const paint=()=>w('\\x1b[2J\\x1b[H'+frame+'\\r\\n');paint();" +
  "process.on('SIGWINCH',paint);" +
  "setTimeout(()=>process.exit(0),12000);";

// Exits with code 42 when it reads the line 'bye' (else renders) — for the exit-code shim proof.
const EXIT42_SRC =
  "const w=s=>process.stdout.write(s);w('\\x1b[2J\\x1b[HREADY\\r\\n');" +
  "process.stdin.setEncoding('utf8');let b='';" +
  "process.stdin.on('data',d=>{b+=d;let i;while((i=b.indexOf('\\n'))>=0){" +
  "const l=b.slice(0,i).replace(/\\r$/,'');b=b.slice(i+1);" +
  "if(l==='bye'){w('BYE\\r\\n');process.exit(42);}w('GOT:'+l+'\\r\\n');}});" +
  "setTimeout(()=>process.exit(0),60000);";

function setup() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p6-2-probe-'));
  const dataRoot = path.join(tmp, 'data');
  const workRoot = path.join(tmp, 'work');
  const defaultWorkdir = path.join(tmp, 'default');
  for (const d of [dataRoot, workRoot, defaultWorkdir]) fs.mkdirSync(d, { recursive: true });

  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(tmp, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'systemd', kill_grace_seconds: 3 },
    default_workdir_root: defaultWorkdir,
    profiles: {
      // Headless one-shot (the DEFAULT path — must attach NO pty).
      'test-sleep': {
        exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
        resume: { argv: ['sleep', '3600'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: workRoot,
        caps: { memory_max: '128M', runtime_max: '1h' },
        sandbox: { ReadWritePaths: ['{workdir}'], NoNewPrivileges: true },
      },
    },
  };
  const cfgPath = path.join(tmp, 'spawn.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const dbPath = path.join(tmp, 'heart.db');
  const store = openHeartStore({ dbPath });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });
  const ptyHost = createPtyHost({ heartStore: store, spawnManager: mgr, dataRoot, userManager: true, logger: null });

  // The pty-aware routing the daemon composes (index.js): headed -> pty host, else the sole path.
  // Mirrors index.js's spawnManagerWithPty EXACTLY — including the headed exit_code override
  // (Behavior #8: a dead headed session's status() must NEVER report the masked ExecMainStatus;
  // the ticker's crash sweep copies status().exitCode onto the row).
  const routed = {
    ...mgr,
    spawn: (execId, profileName, sessionMode = 'headless', prompt = null, workdir = null, enqueuedBy = 'probe') =>
      sessionMode === 'headed'
        ? ptyHost.spawnHeaded(execId, profileName, prompt, workdir, enqueuedBy)
        : mgr.spawn(execId, profileName, sessionMode, prompt, workdir, enqueuedBy),
    status: async (execId) => {
      const info = await mgr.status(execId);
      if (info.sessionMode === 'headed' && !info.live) {
        const src = ptyHost.sourceExitCode(execId);
        info.exitCode = Number.isInteger(src.exit_code) ? src.exit_code : null;
        info.exitCodeSource = src.source;
        if (info.carrierInfo) info.carrierInfo = { ...info.carrierInfo, exitCode: info.exitCode };
      }
      return info;
    },
  };

  // ★ Headed test profiles are injected DIRECTLY into the loaded config, bypassing config.js's
  // strict validation — for TWO reasons: (1) the deterministic renderer TUI is inline `node -e`
  // JS whose braces config.js's slot detector would mis-read as template slots, and (2) the
  // carriage profiles carry headed.tui.prompt, a key config.js currently REJECTS
  // (KNOWN_TUI_KEYS={'argv'}) — extending config.js is a conductor-owed change OUTSIDE this task's
  // allowlist (see the dispatch return's concerns). The pty host reads config.profiles regardless
  // of how a profile got there, so this exercises the pty host EXACTLY as it will behave once
  // config.js is extended. config.js's own (certified) headed.tui.argv validation is unchanged.
  //
  // Headed-capable, NO prompt carriage (reject-by-default). The deterministic renderer is the TUI.
  mgr.config.profiles['test-headed'] = {
    exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
    resume: { argv: ['sleep', '3600'], prompt: 'stdin' },
    session_ref: { source: 'cwd-implicit' },
    headed: { tui: { argv: ['node', '-e', RENDERER_SRC] } },
    workdir_root: workRoot,
    caps: { memory_max: '256M', runtime_max: '1h' },
    sandbox: { ReadWritePaths: ['{workdir}'], NoNewPrivileges: true },
  };
  mgr.config.profiles['test-headed-argv'] = {
    exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
    resume: { argv: ['sleep', '3600'], prompt: 'stdin' },
    session_ref: { source: 'cwd-implicit' },
    headed: { tui: { argv: ['node', '-e', ECHO_ARGV_SRC, '{prompt}'], prompt: 'argv' } },
    workdir_root: workRoot,
    caps: { memory_max: '256M', runtime_max: '1h' },
    sandbox: { ReadWritePaths: ['{workdir}'], NoNewPrivileges: true },
  };
  mgr.config.profiles['test-headed-exit'] = {
    exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
    resume: { argv: ['sleep', '3600'], prompt: 'stdin' },
    session_ref: { source: 'cwd-implicit' },
    headed: { tui: { argv: ['node', '-e', EXIT42_SRC] } },
    workdir_root: workRoot,
    caps: { memory_max: '256M', runtime_max: '1h' },
    sandbox: { ReadWritePaths: ['{workdir}'], NoNewPrivileges: true },
  };

  return { tmp, dataRoot, workRoot, defaultWorkdir, cfgPath, store, mgr, ptyHost, routed, dbPath, units: [] };
}

let tickCounter = 1;

function fire(ctx, { profile, sessionMode = 'headless', workdir = null, enqueuedBy = 'probe' }) {
  const row = ctx.store.recordExecutionStart({
    jobId: 'launch-agent', actionType: 'launch-agent',
    args: JSON.stringify({ profile, workdir }), enqueuedBy, sessionMode,
    firedTick: tickCounter++, firedAt: new Date(), profile, workdir,
  });
  return row;
}

function cgroupProcs(unitName) {
  try {
    const cg = execFileSync('systemctl', ['--user', 'show', unitName, '-p', 'ControlGroup', '--value'], { encoding: 'utf8' }).trim();
    if (!cg) return { cg: null, pids: [] };
    const raw = fs.readFileSync(`/sys/fs/cgroup${cg}/cgroup.procs`, 'utf8').trim();
    return { cg, pids: raw ? raw.split(/\s+/).filter(Boolean) : [] };
  } catch (err) {
    return { cg: null, pids: [], error: err.message };
  }
}

function cmdlineOf(pid) {
  try { return fs.readFileSync(`/proc/${pid}/cmdline`).toString().replace(/\0/g, ' ').trim(); } catch { return ''; }
}

function unitState(unitName) {
  try {
    const out = execFileSync('systemctl', ['--user', 'show', unitName, '-p', 'ActiveState', '-p', 'SubState', '-p', 'Result', '-p', 'ExecMainStatus'], { encoding: 'utf8' }).trim();
    return out.replace(/\n/g, ' ');
  } catch (err) { return `(show failed: ${err.message})`; }
}

function killUnit(unitName) {
  try { execFileSync('systemctl', ['--user', 'kill', unitName], { stdio: 'ignore', timeout: 8000 }); } catch { /* already gone */ }
  try { execFileSync('systemctl', ['--user', 'reset-failed', unitName], { stdio: 'ignore', timeout: 8000 }); } catch { /* fine */ }
}

function teardown(ctx) {
  try { ctx.ptyHost.shutdown(); } catch { /* best-effort */ }
  // Kill EXACTLY the units this harness created — never a blanket rbtv-worker-* kill (the live
  // daemon owns its own rbtv-worker units).
  for (const u of ctx.units) killUnit(u);
  try { closeHeartStore(); } catch { /* fine */ }
  try { fs.rmSync(ctx.tmp, { recursive: true, force: true }); } catch { /* fine */ }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function outDir() {
  return process.env.RBTV_PTY_PROBE_OUT || path.join(os.tmpdir(), 'p6-2-probe-out');
}

// Runs a probe fn(lines) that pushes evidence lines; writes <name>.out to the probe out dir with
// status/exit/wall_ms. Times with Date.now() (date +%s%3N is broken here, D64).
function capture(name, fn) {
  const start = Date.now();
  const dir = outDir();
  fs.mkdirSync(dir, { recursive: true });
  const outPath = path.join(dir, `${name}.out`);
  const lines = [`probe: ${name}`, `started: ${new Date().toISOString()}`, `command: node server/pty/probes/${name}.js`, `host: ${os.hostname()}`, ''];
  let status = 'UNKNOWN';
  let exit = 0;
  return Promise.resolve()
    .then(() => fn(lines))
    .then(() => { status = 'PASS'; exit = 0; })
    .catch((err) => { status = 'FAIL'; exit = 1; lines.push('', `error: ${err.code || err.name}: ${err.message}`, (err.stack || '').split('\n').slice(0, 4).join('\n')); })
    .finally(() => {
      lines.push('', `status: ${status}`, `exit: ${exit}`, `wall_ms: ${Date.now() - start}`, `ended: ${new Date().toISOString()}`);
      fs.writeFileSync(outPath, lines.join('\n') + '\n', 'utf8');
      process.stdout.write(`${name}: ${status} (exit ${exit}, ${Date.now() - start}ms) -> ${outPath}\n`);
      process.exit(exit);
    });
}

module.exports = { setup, fire, teardown, capture, cgroupProcs, cmdlineOf, unitState, killUnit, sleep, RENDERER_SRC };
