'use strict';

// probe-cli-server-json — proves the CLI resolves the daemon through the
// MACHINE-KEYED server.json map (batch-08 item 10 state-layout boundary,
// owner-ruled 2026-07-20): server.json travels via git to every machine, so
// each machine's install (endpoint + per-machine state-root path) lives under
// `machines[<hostname>]` and the CLI selects the right entry from EITHER
// machine. Covers: own-hostname selection end-to-end against a REAL throwaway
// daemon with NO IGNITE_GATEWAY_ADDR set; remote single-server selection;
// multi-server ambiguity; and the legacy flat-shape fallback.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  freePort, makeWorkspace, baseEnv, bootDaemon, waitForLog, stopDaemon, runCli,
} = require('./lib/fixtures');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const { selectMachineEntry, resolveGatewayAddr } = require(path.join(IGNITE_SRC, 'cli', 'lib', 'config'));
const { CliUsageError } = require(path.join(IGNITE_SRC, 'cli', 'lib', 'errors'));

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-server-json.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

function writeServerJson(ws, record) {
  const dir = path.join(ws.workspaceRoot, '.rbtv', 'modules', 'ignite');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'server.json'), JSON.stringify(record, null, 2));
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  // ── Unit checks on the selection rule (in-process, no daemon) ─────────────
  const here = os.hostname();
  const ownEntry = { tailnet_host: 'own.example.ts.net', gateway_port: 1111, state_root: '/tmp/own-state' };
  const remoteEntry = { tailnet_host: 'remote.example.ts.net', gateway_port: 2222, state_root: '/vps/state' };

  let sel = selectMachineEntry({ name: null, machines: { [here]: ownEntry, 'other-box': remoteEntry } }, 'x');
  check('own-hostname entry wins when this machine records a server',
    sel === ownEntry, `selected=${sel && sel.tailnet_host}`);

  sel = selectMachineEntry({ name: null, machines: { 'other-box': remoteEntry, [here]: { state_root: '/tmp/own-state' } } }, 'x');
  check('with no server on this machine, the one machine recording a server is selected',
    sel === remoteEntry, `selected=${sel && sel.tailnet_host}`);

  let ambiguous = null;
  try {
    selectMachineEntry({ machines: { a: remoteEntry, b: { ...ownEntry } } }, 'x');
  } catch (err) { ambiguous = err; }
  check('two remote server entries are ambiguous — loud CliUsageError, never a silent pick',
    ambiguous instanceof CliUsageError, `err=${ambiguous && ambiguous.message.slice(0, 80)}`);

  const flat = { name: null, tailnet_host: 'flat.example.ts.net', gateway_port: 3333 };
  sel = selectMachineEntry(flat, 'x');
  check('legacy flat shape (no machines map) passes through unchanged',
    sel === flat, `selected=${sel && sel.tailnet_host}`);

  // ── End-to-end: real CLI resolves a REAL daemon through the map ──────────
  const ws = makeWorkspace('p720-cli-serverjson');
  const port = await freePort();
  const d = await bootDaemon(baseEnv(ws, port));
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  try {
    // The daemon writes its OWN machine entry into server.json at boot (the D27
    // endpoint-record upsert fires between "gateway listening" and "daemon
    // composed" when a tailnet bind succeeds — this box has one). Wait for
    // "daemon composed" so that one-shot write has already landed, THEN
    // overwrite with the fixture map; otherwise the two writes race.
    await waitForLog(d, /"message":"daemon composed"/, { timeoutMs: 10000 });
    writeServerJson(ws, {
      name: 'probe',
      machines: {
        [here]: { tailnet_host: '127.0.0.1', tailnet_ip: '127.0.0.1', gateway_port: port, ssh_host: null, ssh_user: null, ssh_port: null, state_root: ws.dataRoot },
        'owner-pc': { state_root: '/tmp/owner-pc-state' },
      },
    });

    // NO IGNITE_GATEWAY_ADDR: the CLI must resolve through the machine map.
    const cliEnv = { ...process.env, RBTV_IGNITE_WORKSPACE_ROOT: ws.workspaceRoot, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };
    delete cliEnv.IGNITE_GATEWAY_ADDR;

    const r = await runCli(['--json', 'status'], cliEnv);
    out('--- ignite status --json (resolved via machines map, no IGNITE_GATEWAY_ADDR) ---',
      'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let envelope = null;
    try { envelope = JSON.parse(r.stdout.trim()); } catch {}
    check('real CLI reaches the daemon through machines[<hostname>] — ok envelope, exit 0',
      r.code === 0 && envelope && envelope.ok === true && envelope.result && envelope.result.target === 'daemon',
      `exit=${r.code} ok=${envelope && envelope.ok}`);

    // Same workspace, in-process: the resolved address is this machine's entry.
    const prevWs = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
    const prevAddr = process.env.IGNITE_GATEWAY_ADDR;
    process.env.RBTV_IGNITE_WORKSPACE_ROOT = ws.workspaceRoot;
    delete process.env.IGNITE_GATEWAY_ADDR;
    try {
      const addr = resolveGatewayAddr();
      check('resolveGatewayAddr() yields the own-machine entry host:port',
        addr.host === '127.0.0.1' && addr.port === port, `addr=${addr.host}:${addr.port}`);
    } finally {
      if (prevWs === undefined) delete process.env.RBTV_IGNITE_WORKSPACE_ROOT; else process.env.RBTV_IGNITE_WORKSPACE_ROOT = prevWs;
      if (prevAddr !== undefined) process.env.IGNITE_GATEWAY_ADDR = prevAddr;
    }
  } finally {
    await stopDaemon(d);
    try { fs.rmSync(ws.tmp, { recursive: true, force: true }); } catch {}
  }
}

main().then(() => {
  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
}).catch((err) => {
  out('ERROR:', err.message, err.stack);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
});
