'use strict';

// probe-cli-server-json — proves the CLI resolves the daemon through the
// MACHINE-KEYED server.json map (batch-08 item 10 state-layout boundary,
// owner-ruled 2026-07-20): server.json travels via git to every machine, so
// each machine's install (endpoint + per-machine state-root path) lives under
// `machines[<hostname>]` and the CLI selects the right entry from EITHER
// machine. Covers: own-hostname selection end-to-end against a REAL throwaway
// daemon with NO IGNITE_GATEWAY_ADDR set; remote single-server selection;
// multi-server ambiguity; and the legacy flat-shape fallback.
//
// It also covers the CLI's OTHER config half — SENDER-TOKEN resolution, and
// specifically its fallback to the workspace's gitignored token file
// (owner-directed 2026-08-07). The two belong in one probe because they are
// one question — "how does this CLI find out who and where to call" — and
// because the token half's whole point is the case the address half already
// handles: a caller running deep inside a workspace with no environment.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  freePort, makeWorkspace, baseEnv, bootDaemon, waitForLog, stopDaemon, runCli,
} = require('./lib/fixtures');

const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const { selectMachineEntry, resolveGatewayAddr, resolveToken } = require(path.join(IGNITE_SRC, 'cli', 'lib', 'config'));
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

  // ── Unit checks on TOKEN resolution (owner-directed 2026-08-07) ───────────
  // The env var reaches nobody in a CAGED session — the daemon's unit ships
  // `EnvironmentFile=-/dev/null`, and bwrap passes on the environment it has —
  // so every caged seat promised the `ignite` CLI met AUTH_REFUSED. The
  // gitignored env surface was already the RULED distribution channel for this
  // token; it just had no reader. These drive the reader off a real temp tree,
  // and the WALK leg is the one the caged case depends on.
  //
  // ⚑ THE FILE IS `.rbtv/config/sender-token.env`, NOT the `.env` beside it
  // (owner ruling 2026-08-11, task 7.566). `.env` holds third-party secrets and
  // is now MASKED inside every seat cage; the token lives in its own one-key
  // file so a caged seat keeps gateway auth and loses everything else. The
  // decoy check below is what holds that split: a token sitting in `.env` must
  // NOT be found, or the mask would silently take the master's auth with it.
  const tokRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'p720-token-'));
  const tokDeep = path.join(tokRoot, '.rbtv', 'goals', '_svc');
  fs.mkdirSync(tokDeep, { recursive: true });
  fs.mkdirSync(path.join(tokRoot, '.rbtv', 'config'), { recursive: true });
  const envFile = path.join(tokRoot, '.rbtv', 'config', 'sender-token.env');
  const secretsFile = path.join(tokRoot, '.rbtv', 'config', '.env');
  const prevTok = process.env.IGNITE_SENDER_TOKEN;
  const prevTokWs = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  try {
    fs.writeFileSync(envFile, 'SLACK_BOT_TOKEN=xoxb-decoy\nIGNITE_SENDER_TOKEN=from-file\nOTHER=z\n');

    process.env.RBTV_IGNITE_WORKSPACE_ROOT = tokRoot;
    process.env.IGNITE_SENDER_TOKEN = 'from-env';
    check('the environment variable still WINS over the file', resolveToken() === 'from-env',
      `resolveToken()=${JSON.stringify(resolveToken())}`);

    delete process.env.IGNITE_SENDER_TOKEN;
    check('with no env var, the token is read from the gitignored .rbtv/config/sender-token.env',
      resolveToken() === 'from-file', `resolveToken()=${JSON.stringify(resolveToken())}`);

    // THE SPLIT (7.566). The secrets file is not a token source: masking it in the cage may
    // never cost the seat its gateway auth, and reading it there would mean the mask does.
    fs.writeFileSync(secretsFile, 'SLACK_BOT_TOKEN=xoxb-real\nIGNITE_SENDER_TOKEN=from-secrets-file\n');
    check('a token sitting in the MASKED .rbtv/config/.env is NOT read — only sender-token.env is',
      resolveToken() === 'from-file', `resolveToken()=${JSON.stringify(resolveToken())}`);
    fs.rmSync(envFile);
    check('with only .rbtv/config/.env present, the token resolves to null — no second source',
      resolveToken() === null, `resolveToken()=${JSON.stringify(resolveToken())}`);
    fs.rmSync(secretsFile);
    fs.writeFileSync(envFile, 'SLACK_BOT_TOKEN=xoxb-decoy\nIGNITE_SENDER_TOKEN=from-file\nOTHER=z\n');

    // THE CAGED LEG. A seat's cwd is its own folder, several levels below the
    // workspace root, and the root is not otherwise knowable in there.
    process.env.RBTV_IGNITE_WORKSPACE_ROOT = tokDeep;
    check('resolution WALKS UP from a seat folder to the workspace .env (the caged case)',
      resolveToken() === 'from-file', `from ${tokDeep} -> ${JSON.stringify(resolveToken())}`);

    process.env.RBTV_IGNITE_WORKSPACE_ROOT = tokRoot;
    fs.writeFileSync(envFile, '  export IGNITE_SENDER_TOKEN = "quoted-value"  \n');
    check('an `export `-prefixed, quoted, padded value parses to its bare value',
      resolveToken() === 'quoted-value', `resolveToken()=${JSON.stringify(resolveToken())}`);

    fs.writeFileSync(envFile, 'IGNITE_SENDER_TOKEN=\n');
    check('a present-but-EMPTY key resolves to null, exactly like an unset var',
      resolveToken() === null, `resolveToken()=${JSON.stringify(resolveToken())}`);

    fs.rmSync(envFile);
    let threw = null;
    let noFile;
    try { noFile = resolveToken(); } catch (err) { threw = err; }
    check('an ABSENT .env is null and never throws — the gateway\'s own AUTH_REFUSED still answers',
      threw === null && noFile === null, `threw=${threw && threw.message}; value=${JSON.stringify(noFile)}`);

    // …and the file is never a SECOND source of the address: server.json owns
    // that, and this reader must not have quietly become a general env loader.
    fs.writeFileSync(envFile, 'IGNITE_GATEWAY_ADDR=10.9.9.9:1\nIGNITE_SENDER_TOKEN=t\n');
    const prevAddrEnv = process.env.IGNITE_GATEWAY_ADDR;
    delete process.env.IGNITE_GATEWAY_ADDR;
    let addrFromFile = null;
    try { addrFromFile = resolveGatewayAddr(); } catch (err) { addrFromFile = err.constructor.name; }
    check('the .env reader takes ONLY the token — the gateway address is not loaded from it',
      addrFromFile === 'CliUsageError', `resolveGatewayAddr() -> ${JSON.stringify(addrFromFile)}`);
    if (prevAddrEnv !== undefined) process.env.IGNITE_GATEWAY_ADDR = prevAddrEnv;
  } finally {
    if (prevTok === undefined) delete process.env.IGNITE_SENDER_TOKEN; else process.env.IGNITE_SENDER_TOKEN = prevTok;
    if (prevTokWs === undefined) delete process.env.RBTV_IGNITE_WORKSPACE_ROOT; else process.env.RBTV_IGNITE_WORKSPACE_ROOT = prevTokWs;
    try { fs.rmSync(tokRoot, { recursive: true, force: true }); } catch {}
  }

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
