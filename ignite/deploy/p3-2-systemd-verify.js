'use strict';

// p3-2-systemd-verify.js — re-runnable producer for deploy/systemd-verify.out.
//
// Runs `systemd-analyze verify` against the unsubstituted unit TEMPLATE and
// writes the result with instance-specific paths replaced by stable placeholders.
// The template intentionally carries @@SLOTS@@, so a non-zero exit is expected
// and is the point: it proves the template is not a substituted instance file.
//
// Usage:  node deploy/p3-2-systemd-verify.js
// Exits with systemd-analyze's own exit code.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawnSync } = require('node:child_process');

const IGNITE_SRC = path.resolve(__dirname, '..');
const SERVICE_FILE = path.join(__dirname, 'rbtv-ignite.service');
const OUT_PATH = path.join(__dirname, 'systemd-verify.out');

function portable(p) {
  if (p === undefined || p === null) return p;
  let s = String(p);
  if (s.startsWith(IGNITE_SRC)) s = '{IGNITE_SRC}' + s.slice(IGNITE_SRC.length);
  const home = os.homedir();
  if (home && s.startsWith(home)) s = '{HOME}' + s.slice(home.length);
  return s;
}

const started = Date.now();
const proc = spawnSync('systemd-analyze', ['verify', SERVICE_FILE], { encoding: 'utf8', timeout: 30000 });
const wallMs = Date.now() - started;

const now = new Date().toISOString();
const output = (proc.stdout || '') + (proc.stderr || '');

const lines = [
  'command: systemd-analyze verify deploy/rbtv-ignite.service   (unsubstituted TEMPLATE — @@SLOTS@@ are not valid systemd values by design)',
  `generated: ${now}`,
  '',
  ...output.split('\n').map((line) => portable(line)),
  // A tool that never ran reports status null. Record that explicitly: an empty capture with
  // no error line is indistinguishable from a verify that produced no findings.
  ...(proc.error ? [`VERIFY_ERROR: systemd-analyze could not be run: ${proc.error.message}`] : []),
  `VERIFY_EXIT: ${proc.status}`,
  `VERIFY_WALL_MS: ${wallMs}`,
];

fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n', 'utf8');
// `?? 1`, never `?? 0`: status is null when systemd-analyze could not be run at all, and
// exiting 0 there would report a verification that never happened as a success.
process.exit(proc.status ?? 1);
