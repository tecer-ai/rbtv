'use strict';

// probe-gateway-live — the DAEMON-LEVEL proof, not a module-level one.
//
// Every other p4-1 probe exercises the modules in isolation. That is not the same
// claim: D56's lesson on this run is that a proof of the configuration is not a proof
// of the code path, and the entire composition (server/index.js minting the per-boot
// secret, handing it to exactly one module, starting the listener) plus the HTTP
// framing itself would otherwise ship UNEXERCISED into a daemon the owner restarts.
//
// So this probe boots the REAL daemon entry point as a REAL child process, drives a
// REAL HTTP request over the REAL loopback listener with a REAL Bearer token, and
// reads the answer off the socket.
//
// ⚑ IT NEVER TOUCHES THE LIVE DAEMON. It runs a throwaway workspace, a throwaway data
// root, a throwaway senders_file, and an EPHEMERAL PORT (never the configured 7431),
// and it starts/stops only the child it spawned. No systemctl, no signal to anything
// it did not create.
//
// It also proves the landmine in the direction that matters: with NO senders_file
// deployed, the daemon REFUSES TO START and says why.
//
// Capture truncated at module load, BEFORE any work (D51). The process exit code is
// the truth; the footer is a hint.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const net = require('node:net');
const { spawn } = require('node:child_process');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-gateway-live.out');
fs.writeFileSync(outPath, '');

const { hashToken } = require('../sender-auth');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const ENTRY = path.join(IGNITE_SRC, 'server', 'index.js');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
const skipped = 0;
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), `p4-1-live-${process.pid}-`));
const workspaceRoot = path.join(tmp, 'workspace');
const dataRoot = path.join(tmp, 'data');
const workRoot = path.join(tmp, 'work');
for (const d of [workspaceRoot, dataRoot, workRoot]) fs.mkdirSync(d, { recursive: true });

const OWNER_TOKEN = crypto.randomBytes(16).toString('hex');
const sendersFile = path.join(tmp, 'senders.yaml');
fs.writeFileSync(sendersFile, [
  'senders:',
  '  - sender-id: probe-owner',
  '    kind: owner',
  `    token-hash: ${hashToken(OWNER_TOKEN)}`,
  '    enabled: true',
  '',
].join('\n'), { mode: 0o600 });
fs.chmodSync(sendersFile, 0o600);

// An EPHEMERAL port, taken from the OS. Never the configured 7431: a probe must not
// be able to collide with — or be mistaken for — the live daemon's ingress.
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

function baseEnv(port) {
  return {
    ...process.env,
    RBTV_IGNITE_SRC: IGNITE_SRC,
    RBTV_IGNITE_WORKSPACE_ROOT: workspaceRoot,
    RBTV_IGNITE_CONFIG_PATH: path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml'),
    RBTV_IGNITE_WORKDIR_ROOT: workRoot,
    RBTV_IGNITE_DATA_ROOT: dataRoot,
    RBTV_IGNITE_USER_MANAGER: 'true',
    RBTV_IGNITE_BIND_HOST: '127.0.0.1',
    RBTV_IGNITE_BIND_PORT: String(port),
    RBTV_IGNITE_SENDERS_FILE: sendersFile,
  };
}

function request(port, { token, body }) {
  return new Promise((resolve, reject) => {
    const payload = Buffer.from(JSON.stringify(body), 'utf8');
    const headers = { 'content-type': 'application/json', 'content-length': payload.length };
    // ⚑ The token rides in a HEADER, never a URL or an argv — process lists and
    // access logs leak both.
    if (token) headers['authorization'] = `Bearer ${token}`;
    const req = http.request({ host: '127.0.0.1', port, method: 'POST', path: '/', headers }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        let parsed = null;
        try { parsed = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch {}
        resolve({ status: res.statusCode, body: parsed });
      });
    });
    req.once('error', reject);
    req.end(payload);
  });
}

// Boots the daemon and resolves once its own log says the ingress is up. Waiting on
// the daemon's OWN readiness line (never a sleep) is what keeps this deterministic.
//
// ⚑ The log is exposed as a LIVE ACCESSOR (`d.log()`), not as a string field. Strings
// are immutable: a `stdout` snapshot taken at resolve time can never contain a line
// the daemon writes afterwards — so any post-boot assertion against it (shutdown,
// secret-leak) would be reading a frozen prefix and silently passing or failing on
// evidence that could not possibly be there.
function bootDaemon(env, { expectExit = false } = {}) {
  const state = { stdout: '', stderr: '' };
  return new Promise((resolve) => {
    const proc = spawn(process.execPath, [ENTRY], { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let settled = false;
    const base = { proc, log: () => state.stdout, errLog: () => state.stderr };
    const done = (res) => { if (!settled) { settled = true; resolve({ ...base, ...res }); } };

    proc.stdout.on('data', (d) => {
      state.stdout += d.toString();
      if (!expectExit && /"message":"gateway listening"/.test(state.stdout)) done({ listening: true });
    });
    proc.stderr.on('data', (d) => { state.stderr += d.toString(); });
    proc.on('exit', (code) => done({ exitCode: code, listening: false }));
    setTimeout(() => done({ listening: false, timedOut: true }), 20000);
  });
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  // ── A. THE LANDMINE, proven: no senders_file -> the daemon REFUSES TO START. ──
  const portA = await freePort();
  const noSendersEnv = { ...baseEnv(portA), RBTV_IGNITE_SENDERS_FILE: path.join(tmp, 'absent.yaml') };
  const a = await bootDaemon(noSendersEnv, { expectExit: true });
  check('LANDMINE: with NO senders_file deployed, the daemon REFUSES TO START',
    a.exitCode === 1 && a.listening === false,
    `exit=${a.exitCode}, never reached "gateway listening"`);
  check('LANDMINE: the refusal is LOUD — it names the cause and the remedy in the daemon log',
    /REFUSING TO START/.test(a.log()) && /senders_file is missing/.test(a.log()) && /senders\.example/.test(a.log()),
    'daemon log carries the actionable refusal');
  check('LANDMINE: the daemon never opened its ingress before refusing',
    !/gateway listening/.test(a.log()),
    'no listener was ever bound');
  try { a.proc.kill('SIGKILL'); } catch {}

  // ── B. THE HAPPY PATH: a real daemon, a real socket, a real token. ──
  const port = await freePort();
  const b = await bootDaemon(baseEnv(port));
  check('the daemon BOOTS and its gateway LISTENS on loopback',
    b.listening === true, b.listening ? `bound 127.0.0.1:${port}` : `did not listen (exit=${b.exitCode}) ${b.errLog().slice(0, 200)}`);

  if (!b.listening) {
    out('ABORT: the daemon never listened; the remaining live checks cannot run.');
    try { b.proc.kill('SIGKILL'); } catch {}
    return;
  }

  check('the startup gate is reported as PASSED in the daemon log before the ingress opens',
    /sender registry startup gate passed/.test(b.log()), 'gate logged at boot');
  check('the bind is LOOPBACK, never a public interface (DEC-3 zero-ingress)',
    /"message":"gateway listening"[^}]*"host":"127\.0\.0\.1"/.test(b.log()),
    'host=127.0.0.1');

  try {
    // 1. Unauthenticated, over the real socket.
    let r = await request(port, { token: null, body: { intent: 'inspect', payload: { target: 'queue' } } });
    check('LIVE: an unauthenticated request over the real socket is refused AUTH_REFUSED (401)',
      r.status === 401 && r.body.error.code === 'AUTH_REFUSED',
      `status=${r.status} code=${r.body && r.body.error && r.body.error.code}`);

    // 2. Wrong token, over the real socket.
    r = await request(port, { token: 'not-the-token', body: { intent: 'inspect', payload: { target: 'queue' } } });
    check('LIVE: a wrong token over the real socket is refused AUTH_REFUSED (401)',
      r.status === 401 && r.body.error.code === 'AUTH_REFUSED',
      `status=${r.status} code=${r.body && r.body.error && r.body.error.code}`);

    // 3. A VALID token round-trips through gateway -> internal API -> store and back.
    // This is the whole invariant chain in one gesture: sender -> gateway -> server
    // core -> queue.
    r = await request(port, { token: OWNER_TOKEN, body: { intent: 'inspect', payload: { target: 'queue' } } });
    check('LIVE: a VALID token round-trips the full chain (sender -> gateway -> core -> store)',
      r.status === 200 && r.body.ok === true && Array.isArray(r.body.result.rows),
      `status=${r.status} ok=${r.body && r.body.ok} rows=${r.body && r.body.result && r.body.result.rows.length}`);

    // 4. The per-boot secret is REAL and never leaves the process.
    check('the per-boot internal secret never appears in the daemon log or on the wire',
      !/"auth":"[0-9a-f]{64}"/.test(b.log()) && !JSON.stringify(r.body).includes('auth'),
      'no L2 secret in the log or the response');

    // 5. The core re-validates over the real socket too (defense-in-depth, end to end).
    r = await request(port, {
      token: OWNER_TOKEN,
      body: { intent: 'enqueue-job', payload: { job_id: 'no-such-job', args: '{}', trigger_kind: 'scheduled', run_at: '2026-01-01T00:00:00Z' } },
    });
    check('LIVE: the core re-validates over the socket — an unknown job is VALIDATION_FAILED (400)',
      r.status === 400 && r.body.error.code === 'VALIDATION_FAILED',
      `status=${r.status} code=${r.body && r.body.error && r.body.error.code}`);

    // 6. A garbage body from an AUTHENTICATED sender is a shape error — the other
    // half of the auth-precedes-parse ordering, proven live.
    r = await request(port, { token: OWNER_TOKEN, body: { intent: 'not-an-intent', payload: {} } });
    check('LIVE: an AUTHENTICATED sender naming a bogus intent gets UNKNOWN_INTENT (not an auth error)',
      r.body.error && r.body.error.code === 'UNKNOWN_INTENT',
      `code=${r.body && r.body.error && r.body.error.code}`);
  } finally {
    // Stop ONLY the child this probe spawned, through the real shutdown path.
    const exited = new Promise((resolve) => b.proc.once('exit', resolve));
    b.proc.kill('SIGTERM');
    await Promise.race([exited, new Promise((r) => setTimeout(r, 5000))]);
    try { b.proc.kill('SIGKILL'); } catch {}
  }

  check('the daemon shut down cleanly through its real SIGTERM path (the ingress closes first)',
    /received SIGTERM, shutting down/.test(b.log()) && /daemon stopped/.test(b.log()),
    'clean shutdown logged');
}

main().then(() => {
  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`SKIPPED_COUNT: ${skipped}`);
  out(`GATEWAY_LIVE_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
}).catch((err) => {
  out('ERROR:', err.message, err.stack);
  out(`SKIPPED_COUNT: ${skipped}`);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
}).finally(() => {
  try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}
});
