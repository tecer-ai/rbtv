'use strict';

// p3-2-smoke.js — re-runnable smoke-test producer for deploy/smoke.out.
//
// Boots the daemon entry point in smoke mode, captures its structured log, and
// writes it back with instance-specific paths rendered as stable placeholders
// so the committed capture is machine-portable.
//
// Usage:  node deploy/p3-2-smoke.js
// Writes deploy/smoke.out and exits with the daemon's own exit code.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const IGNITE_SRC = path.resolve(__dirname, '..');
const ENTRY = path.join(IGNITE_SRC, 'server', 'index.js');
const OUT_PATH = path.join(__dirname, 'smoke.out');

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p3-2-smoke-'));
const workspaceRoot = path.join(tmp, 'workspace');
const dataRoot = path.join(tmp, 'data');
const workRoot = path.join(tmp, 'work');
for (const d of [workspaceRoot, dataRoot, workRoot]) fs.mkdirSync(d, { recursive: true });

// The round-2 sender-registry startup gate (gateway/sender-auth.js loadSendersFile)
// makes the daemon REFUSE TO START without a valid senders_file. This smoke test boots
// the real entry point, so it must supply one — a throwaway 0600 file with one valid
// owner row, mirroring gateway/probes/probe-gateway-live.js. The token-hash is a real-
// shaped random 64-hex: this producer only boots the daemon, it never authenticates a
// sender, so the file only has to pass the boot-time gate.
const sendersFile = path.join(tmp, 'senders.yaml');
fs.writeFileSync(sendersFile, [
  'senders:',
  '  - sender-id: smoke-owner',
  '    kind: owner',
  `    token-hash: ${crypto.randomBytes(32).toString('hex')}`,
  '    enabled: true',
  '',
].join('\n'), { mode: 0o600 });
fs.chmodSync(sendersFile, 0o600);

const env = {
  ...process.env,
  RBTV_IGNITE_SRC: IGNITE_SRC,
  RBTV_IGNITE_WORKSPACE_ROOT: workspaceRoot,
  RBTV_IGNITE_CONFIG_PATH: path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml'),
  RBTV_IGNITE_WORKDIR_ROOT: workRoot,
  RBTV_IGNITE_DATA_ROOT: dataRoot,
  RBTV_IGNITE_USER_MANAGER: 'true',
  RBTV_IGNITE_SENDERS_FILE: sendersFile,
};

const started = Date.now();
const proc = spawnSync(process.execPath, [ENTRY, '--smoke-test'], { env, encoding: 'utf8', timeout: 60000 });
const wallMs = Date.now() - started;

let stdout = proc.stdout || '';

// Render instance-specific paths as stable placeholders so the committed capture
// carries no machine home directory or ignite-source absolute path.
function portable(p) {
  if (p === undefined || p === null) return p;
  let s = String(p);
  if (s.startsWith(IGNITE_SRC)) s = '{IGNITE_SRC}' + s.slice(IGNITE_SRC.length);
  if (s.startsWith(workspaceRoot)) s = '{WORKSPACE_ROOT}' + s.slice(workspaceRoot.length);
  if (s.startsWith(dataRoot)) s = '{DATA_ROOT}' + s.slice(dataRoot.length);
  if (s.startsWith(workRoot)) s = '{WORKDIR_ROOT}' + s.slice(workRoot.length);
  const home = os.homedir();
  if (home && s.startsWith(home)) s = '{HOME}' + s.slice(home.length);
  return s;
}

// Substitute placeholders inside every JSON log line without altering structure.
stdout = stdout.split('\n').map((line) => {
  if (!line.trim()) return line;
  let parsed;
  try { parsed = JSON.parse(line); } catch { return portable(line); }
  const replacer = (key, value) => {
    if (typeof value === 'string') return portable(value);
    return value;
  };
  return JSON.stringify(parsed, replacer);
}).join('\n');

// The daemon logs structured JSON to stdout; stderr should stay empty. Capture it anyway —
// a crash stack or a warning printed to stderr is exactly the evidence a scrubbing wrapper
// must not swallow, and an exit code alone would not reveal a stderr warning on a clean exit.
const stderrText = (proc.stderr || '').trim();

const out = stdout + '\n'
  + (stderrText ? `SMOKE_STDERR:\n${stderrText.split('\n').map((l) => portable(l)).join('\n')}\n` : '')
  + (proc.error ? `SMOKE_ERROR: the daemon could not be run: ${proc.error.message}\n` : '')
  + `SMOKE_EXIT: ${proc.status}\nSMOKE_WALL_MS: ${wallMs}\n`;
fs.writeFileSync(OUT_PATH, out, 'utf8');

try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}

process.exit(proc.status ?? 1);
