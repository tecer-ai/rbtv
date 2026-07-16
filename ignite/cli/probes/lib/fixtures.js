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
// to give a fresh daemon something in its catalogue to enqueue against (v1
// ships no CLI-reachable way to register a catalogue job at all — that
// surface does not exist yet, gateway-cli-spec.md's CLI Surface table has no
// such subcommand).

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
    '',
  ].join('\n'), { mode: 0o600 });
  fs.chmodSync(sendersFile, 0o600);

  return { tmp, workspaceRoot, dataRoot, workRoot, sendersFile, OWNER_TOKEN, AGENT_TOKEN };
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
function bootDaemon(env) {
  const state = { stdout: '', stderr: '' };
  return new Promise((resolve) => {
    const proc = spawn(process.execPath, [SERVER_ENTRY], { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let settled = false;
    const base = { proc, log: () => state.stdout, errLog: () => state.stderr };
    const done = (res) => { if (!settled) { settled = true; resolve({ ...base, ...res }); } };

    proc.stdout.on('data', (d) => {
      state.stdout += d.toString();
      if (/"message":"gateway listening"/.test(state.stdout)) done({ listening: true });
    });
    proc.stderr.on('data', (d) => { state.stderr += d.toString(); });
    proc.on('exit', (code) => done({ exitCode: code, listening: false }));
    setTimeout(() => done({ listening: false, timedOut: true }), 20000);
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
  await Promise.race([exited, new Promise((r) => setTimeout(r, 5000))]);
  try { d.proc.kill('SIGKILL'); } catch {}
}

// FIXTURE SETUP ONLY (see file header): seeds one catalogue job — a
// launch-agent job naming the shipped, side-effect-free `test-sleep` profile
// (D52) — directly into the SAME sqlite db path server/index.js's own
// openHeartStore({ runtimeStateRoot }) resolves to
// (`<workspaceRoot>/.rbtv/heart/heart.db`), so the daemon that boots
// afterwards sees it. Optionally also seeds one jobs_log execution row (for
// probes exercising `inspect status`/`inspect logs`, which are exec-scoped
// and have no other way to get an id without actually spawning a worker), and
// optionally points that row's log_path at a REAL file with real content —
// spawnManager.logs() reads log_path straight off the row (server/spawn/spawn.js),
// so this is enough to prove `inspect logs` renders REAL captured output
// without this probe having to actually launch and wait on a worker process.
function seedCatalogue(ws, { withExecution = false, withLogLines = null } = {}) {
  const store = openHeartStore({
    runtimeStateRoot: ws.workspaceRoot,
    profiles: { 'test-sleep': { headed: false } },
  });
  try {
    store.registerJob({
      jobId: 'probe-cli-sleep',
      actionType: 'launch-agent',
      function: 'spawnLaunchAgent',
      argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: {} }),
    });
    let execId = null;
    let logPath = null;
    if (withExecution) {
      const row = store.recordExecutionStart({
        jobId: 'probe-cli-sleep',
        actionType: 'launch-agent',
        args: JSON.stringify({ profile: 'test-sleep' }),
        enqueuedBy: 'probe-owner',
        firedTick: 0,
        firedAt: new Date(),
        profile: 'test-sleep',
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
  const store = openHeartStore({ runtimeStateRoot: ws.workspaceRoot });
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
