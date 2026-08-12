'use strict';

// Shared fixture helpers for the p4-2 CLI probes. Every probe boots its OWN
// throwaway daemon in a throwaway workspace on an EPHEMERAL port — mirroring
// gateway/probes/probe-gateway-live.js's own pattern — and drives the REAL
// `ignite` CLI as a REAL child process against it. NONE of this ever touches
// the live `rbtv-ignite` daemon: no systemctl, no signal to anything a probe
// did not spawn itself.
//
// ⚑ Seeding the jobs catalogue (and, for status/logs, one jobs_log execution
// row) here via `server/heart/heart-store` is TEST-FIXTURE SETUP, not the
// CLI bypassing the gateway: it runs in THIS probe's own process, before the
// daemon child boots, exactly like probe-gateway-live.js writes a throwaway
// senders.yaml directly to disk before booting. The `ignite` CLI under test
// never imports server/heart itself — only this fixture file does, and only
// to give a fresh daemon something in its catalogue to enqueue against.
//
// ⚑ Since task 7.12 there IS a CLI-reachable way to register a catalogue job
// (`ignite register-job`), so this direct seeding is no longer the only route —
// it stays because it is SETUP: a probe that tests enqueue should not depend on
// registration passing first. probe-cli-register.js drives the real subcommand.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');

const IGNITE_SRC = path.resolve(__dirname, '..', '..', '..');
const SERVER_ENTRY = path.join(IGNITE_SRC, 'server', 'index.js');
const CLI_ENTRY = path.join(IGNITE_SRC, 'cli', 'ignite.js');

const { hashToken } = require(path.join(IGNITE_SRC, 'gateway', 'sender-auth'));
const { openHeartStore, closeHeartStore } = require(path.join(IGNITE_SRC, 'server', 'heart', 'heart-store'));

function freePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.once('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const p = srv.address().port;
      srv.close(() => resolve(p));
    });
  });
}

// Builds a throwaway workspace + senders registry with an OWNER sender (and,
// optionally, a disabled/other-kind row for authz probes). Returns everything
// a probe needs to boot the daemon and drive the CLI against it.
function makeWorkspace(prefix) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-${process.pid}-`));
  const workspaceRoot = path.join(tmp, 'workspace');
  const dataRoot = path.join(tmp, 'data');
  const workRoot = path.join(tmp, 'work');
  for (const d of [workspaceRoot, dataRoot, workRoot]) fs.mkdirSync(d, { recursive: true });

  const OWNER_TOKEN = crypto.randomBytes(16).toString('hex');
  const AGENT_TOKEN = crypto.randomBytes(16).toString('hex');
  // A BRIDGE sender (task 7.12): the third ratified sender kind, and the only
  // principal `register-job` refuses — a probe needs it to prove the denial half of
  // that policy. Purely additive: a row in the throwaway senders file that no existing
  // probe reads, and an unused enrolled sender changes no behaviour.
  const BRIDGE_TOKEN = crypto.randomBytes(16).toString('hex');
  const sendersFile = path.join(tmp, 'senders.yaml');
  fs.writeFileSync(sendersFile, [
    'senders:',
    '  - sender-id: probe-owner',
    '    kind: owner',
    `    token-hash: ${hashToken(OWNER_TOKEN)}`,
    '    enabled: true',
    '  - sender-id: probe-agent',
    '    kind: agent',
    `    token-hash: ${hashToken(AGENT_TOKEN)}`,
    '    enabled: true',
    '  - sender-id: probe-bridge',
    '    kind: bridge',
    `    token-hash: ${hashToken(BRIDGE_TOKEN)}`,
    '    enabled: true',
    '',
  ].join('\n'), { mode: 0o600 });
  fs.chmodSync(sendersFile, 0o600);

  return { tmp, workspaceRoot, dataRoot, workRoot, sendersFile, OWNER_TOKEN, AGENT_TOKEN, BRIDGE_TOKEN };
}

function baseEnv(ws, port) {
  return {
    ...process.env,
    RBTV_IGNITE_SRC: IGNITE_SRC,
    RBTV_IGNITE_WORKSPACE_ROOT: ws.workspaceRoot,
    RBTV_IGNITE_CONFIG_PATH: path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml'),
    RBTV_IGNITE_WORKDIR_ROOT: ws.workRoot,
    RBTV_IGNITE_DATA_ROOT: ws.dataRoot,
    RBTV_IGNITE_USER_MANAGER: 'true',
    RBTV_IGNITE_BIND_HOST: '127.0.0.1',
    RBTV_IGNITE_BIND_PORT: String(port),
    RBTV_IGNITE_SENDERS_FILE: ws.sendersFile,
  };
}

// Boots the real daemon entry point as a real child process, resolving once
// its own log says the gateway is listening (never a sleep).
//
// ⚑ Task 7.702 — PLATFORM GATE for all twelve cli probes, in the ONE place they
// share. On win32 this boot cannot succeed, for two POSIX-rooted reasons that
// are the daemon being a Linux/systemd daemon and nothing any probe asserts:
//   1. gateway/sender-auth.js loadSendersFile REFUSES TO START unless the
//      senders file's mode is 0600. NTFS has no POSIX mode: node's fs.chmodSync
//      only moves the read-only bit and stat reports 0666, so a fixture's
//      chmod 0600 can never satisfy the gate.
//   2. Past that gate, server/spawn/carrier.js selectCarrier throws
//      E_SYSTEMD_NOT_AVAILABLE — the shipped profile asks for the systemd
//      carrier and there is no systemctl.
// So the honest verdict is INOPERATIVE (exit 2, the suite's idiom — probe-suite.js
// keeps exit 2 OUT of `failed`), never a red (nothing the probe measures broke)
// and never a green (nothing ran). It lives HERE rather than in each probe
// because all twelve reach the daemon through this one function and no other
// route — one guard, one wording, one place to change. Owner ruling 2026-08-11,
// decisions.md#d-7702-win32-guard-in-bootdaemon; that ruling also read D4's
// actual words (fixtures.js takes no NEW HELPERS) and found they do not reach an
// edit inside an existing function.
// ⚠ This ends the process rather than returning — a probe whose world cannot be
// built has nothing left to do. A future cli probe that must run WITHOUT a daemon
// therefore cannot reach that work through bootDaemon.
// Linux is byte-unchanged: the branch is false there.
function bootDaemon(env) {
  if (process.platform === 'win32') {
    console.log('VERDICT: INOPERATIVE — win32: the throwaway daemon cannot boot here — the '
      + 'senders_file 0600 startup gate is unsatisfiable on NTFS, and the spawn carrier '
      + 'requires a systemd user manager');
    console.log('EXIT: 2');
    process.exit(2);
  }
  const state = { stdout: '', stderr: '' };
  return new Promise((resolve) => {
    const proc = spawn(process.execPath, [SERVER_ENTRY], { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let settled = false;
    const base = { proc, log: () => state.stdout, errLog: () => state.stderr };
    // G-157: this boot timeout is a SAFETY NET, and an uncleared one held the whole probe process
    // open for its full 20s after the work was done — a probe finishing its checks in 1.3s took
    // 20.1s to exit, measured identically to a tty, through a pipe, and to a file. Twelve cli
    // probes paid ~3.8 minutes of pure dead time, which is a large part of why this suite was
    // never run twice. Clear it the moment the boot settles.
    const done = (res) => {
      if (settled) return;
      settled = true;
      clearTimeout(bootTimeout);
      resolve({ ...base, ...res });
    };

    proc.stdout.on('data', (d) => {
      state.stdout += d.toString();
      if (/"message":"gateway listening"/.test(state.stdout)) done({ listening: true });
    });
    proc.stderr.on('data', (d) => { state.stderr += d.toString(); });
    proc.on('exit', (code) => done({ exitCode: code, listening: false }));
    const bootTimeout = setTimeout(() => done({ listening: false, timedOut: true }), 20000);
  });
}

// Polls a booted daemon's own log accessor (`d.log()`) for a pattern, rather
// than sleeping a guessed duration — mirrors bootDaemon()'s own "wait on the
// daemon's OWN readiness line, never a sleep" discipline. Used by probes that
// must land STATE BETWEEN two of the daemon's ticks (server/index.js runs one
// tick synchronously right after "gateway listening", before the next
// scheduled one 10s later — see probe-cli-snooze.js for why this matters).
function waitForLog(d, pattern, { timeoutMs = 5000, pollMs = 20 } = {}) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    const check = () => {
      if (pattern.test(d.log())) return resolve(true);
      if (Date.now() >= deadline) return reject(new Error(`timed out waiting for daemon log to match ${pattern}`));
      setTimeout(check, pollMs);
    };
    check();
  });
}

async function stopDaemon(d) {
  if (!d || !d.proc) return;
  const exited = new Promise((resolve) => d.proc.once('exit', resolve));
  try { d.proc.kill('SIGTERM'); } catch {}
  // Same G-157 shape, smaller: the grace timer must not outlive the race it was losing.
  let grace;
  await Promise.race([exited, new Promise((r) => { grace = setTimeout(r, 5000); })]);
  clearTimeout(grace);
  try { d.proc.kill('SIGKILL'); } catch {}
}

// FIXTURE SETUP ONLY (see file header): seeds one catalogue job — a
// launch-agent job naming the shipped, side-effect-free `test-sleep` profile
// (D52) — directly into the SAME sqlite db path server/index.js's own
// openHeartStore({ dbPath }) resolves to (`<dataRoot>/heart.db` — the heart
// store is per-machine state, batch-08 item 10 state-layout boundary), so the
// daemon that boots afterwards sees it. Optionally also seeds one jobs_log execution row (for
// probes exercising `inspect status`/`inspect logs`, which are exec-scoped
// and have no other way to get an id without actually spawning a worker), and
// optionally points that row's log_path at a REAL file with real content —
// spawnManager.logs() reads log_path straight off the row (server/spawn/spawn.js),
// so this is enough to prove `inspect logs` renders REAL captured output
// without this probe having to actually launch and wait on a worker process.
function seedCatalogue(ws, { withExecution = false, withLogLines = null } = {}) {
  const store = openHeartStore({
    dbPath: path.join(ws.dataRoot, 'heart.db'),
  });
  try {
    // ⚑ Registration became CREATE-ONLY at task 7.12 (`acc661d`): re-registering an id now
    // throws E_JOB_EXISTS. A probe may legitimately call seedCatalogue MORE THAN ONCE on the
    // SAME workspace to obtain several execution rows — probe-cli-inspect does, and did so
    // before 7.12 too. For those calls the catalogue row already exists and is IDENTICAL, so
    // re-registering is a no-op by intent. Swallow exactly that one code and nothing else: a
    // bare catch here would also hide E_BAD_ARGS, which is precisely how a fixture stops
    // discriminating. Because nothing runs cli/probes/, this rotted unnoticed from 2026-07-25
    // until 7.52 ran the suite, turning probe-cli-inspect into a 13ms crash before its daemon
    // ever booted — and truncating its committed .out from 78 lines to a 9-line stack trace.
    try {
      store.registerJob({
        jobId: 'probe-cli-sleep',
        actionType: 'launch-agent',
        function: 'spawnLaunchAgent',
        argsSchema: JSON.stringify({ required: {}, optional: {} }),
      });
    } catch (err) {
      if (!err || err.code !== 'E_JOB_EXISTS') throw err;
      // Already seeded by an earlier call on this same workspace — intended; carry on.
    }
    let execId = null;
    let logPath = null;
    if (withExecution) {
      const row = store.recordExecutionStart({
        jobId: 'probe-cli-sleep',
        actionType: 'launch-agent',
        args: JSON.stringify({}),
        enqueuedBy: 'probe-owner',
        firedTick: 0,
        firedAt: new Date(),
        });
      execId = row.exec_id;

      if (Array.isArray(withLogLines)) {
        logPath = path.join(ws.dataRoot, `probe-exec-${execId}.log`);
        fs.writeFileSync(logPath, withLogLines.map((l) => l + '\n').join(''));
        store.updateExecutionStatus(execId, { status: 'running', logPath });
      }
    }
    return { execId, logPath };
  } finally {
    closeHeartStore();
  }
}

// Drives the REAL CLI as a REAL child process — proof of argv parsing, env
// resolution, and the HTTP round trip together, not a call into its internals.
function runCli(args, env, { timeoutMs = 15000 } = {}) {
  return new Promise((resolve) => {
    const proc = spawn(process.execPath, [CLI_ENTRY, ...args], { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => { try { proc.kill('SIGKILL'); } catch {} }, timeoutMs);
    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });
    proc.on('exit', (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr });
    });
  });
}

// FIXTURE SETUP ONLY (see file header): raises one standing warning directly
// via heart-store.raiseWarning (p3-3's store API) so a probe can exercise
// `ignite snooze` against a REAL standing warning without needing the ticker
// to organically raise one.
function seedWarning(ws, { kind, subject }) {
  const store = openHeartStore({ dbPath: path.join(ws.dataRoot, 'heart.db') });
  try {
    return store.raiseWarning({ kind, subject, raisedAtTick: 0 });
  } finally {
    closeHeartStore();
  }
}

module.exports = {
  IGNITE_SRC,
  CLI_ENTRY,
  freePort,
  makeWorkspace,
  baseEnv,
  bootDaemon,
  waitForLog,
  stopDaemon,
  seedCatalogue,
  seedWarning,
  runCli,
};
