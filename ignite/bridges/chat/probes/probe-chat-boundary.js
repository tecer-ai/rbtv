'use strict';

// Test Plan #5 — Bridge holds no privileged capability (chat-bridge-spec.md
// Behavior #5). Static scan of the bridge RUNTIME source (never the probes):
// the bridge must hold NO spawn/queue handle, open NO server/listener, and reach
// into NO sibling module (relocatable subtree, ignite/CLAUDE.md rule 4). Comments
// are stripped first so a token that appears only in prose ("holds NO spawn…")
// never counts as a capability.

const path = require('node:path');
const fs = require('node:fs');
const { makeCapture, nowMs } = require('./lib');

const OUT = path.join(__dirname, 'probe-chat-boundary.out');
const SRC_DIR = path.join(__dirname, '..');

// Runtime source only — probes/ and README are excluded (probes reach siblings by design).
const RUNTIME_FILES = [
  'config.js', 'gateway-forwarder.js', 'allowlist.js', 'thread-map.js',
  'forward-path.js', 'slack-socket-mode.js', 'chat-bridge.js', 'index.js',
];

// Each pattern = a capability the bridge must NOT hold. A hit is a boundary violation.
const FORBIDDEN = [
  { name: 'store-driver (node:sqlite)', re: /node:sqlite|DatabaseSync/ },
  { name: 'store-open (heart store)', re: /openHeartStore|heart-store/ },
  { name: 'child process / spawn', re: /child_process|\bspawn\s*\(|execFile|execSync|\.exec\s*\(/ },
  { name: 'inbound listener (server)', re: /createServer|WebSocketServer|\.listen\s*\(/ },
  { name: 'sibling reach-out (server/gateway/cli)', re: /require\(['"]\.\.\/\.\.\/(server|gateway|cli)\b|require\(['"]\.\.\/(server|gateway|cli)\b/ },
  { name: 'raw queue/store write', re: /INSERT INTO|BEGIN EXCLUSIVE|\.enqueue\s*\(|removeQueueRow|fireQueueRow/ },
  // probes/lib.js legitimately reaches siblings (test harness); a RUNTIME file
  // importing it would inherit that reach transitively — forbidden.
  { name: 'probe-harness import (transitive sibling reach)', re: /require\(['"]\.\/probes|require\(['"]\.\.\/probes/ },
];

// Strip block and line comments so prose mentions do not count as code.
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1'); // keep the char before // (so 'http://' inside a string is spared the truncation-into-token risk)
}

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const hits = [];
  for (const file of RUNTIME_FILES) {
    const full = path.join(SRC_DIR, file);
    const code = stripComments(fs.readFileSync(full, 'utf8'));
    for (const pat of FORBIDDEN) {
      const lines = code.split('\n');
      lines.forEach((line, i) => {
        if (pat.re.test(line)) hits.push({ file, line: i + 1, capability: pat.name, text: line.trim().slice(0, 160) });
      });
    }
  }
  cap.log({ step: 'scanned runtime source', files: RUNTIME_FILES, forbiddenPatterns: FORBIDDEN.map((p) => p.name) });
  cap.log({ step: 'forbidden-capability hits', count: hits.length, hits });

  const pass = hits.length === 0;
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-boundary', pass, EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 });
  process.stdout.write(`PROBE probe-chat-boundary EXIT=${exit} WALL_MS=${wallMs} PASS=${pass}\n`);
  process.exit(exit);
}

main();
