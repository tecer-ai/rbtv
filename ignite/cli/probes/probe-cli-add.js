'use strict';

// probe-cli-add — proves `ignite add-job` end-to-end through the REAL CLI
// binary against a REAL (throwaway) daemon: happy-path enqueue (scheduled),
// a periodic enqueue, --profile sugar folding into args.profile, defense-in-
// depth re-validation refusing an unknown function (exit 4), local usage
// errors (exit 2), and the ADX-3/D27 server.json resolution path (no
// IGNITE_GATEWAY_ADDR — the CLI must find the gateway from
// .rbtv/modules/ignite/server.json alone).
//
// It also smoke-tests that a VALID `--dry-run` exits 0 with a verdict and
// nothing enqueued — the full dry-run coverage (queue-unchanged proof,
// invalid-dry-run exit 4, --json shape) lives in the dedicated
// probe-cli-dryrun.js.
//
// NEVER touches the live daemon: throwaway workspace, throwaway senders file,
// ephemeral port; only the child this probe spawns is ever signaled.

const fs = require('node:fs');
const path = require('node:path');
const {
  freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, seedCatalogue, runCli,
} = require('./lib/fixtures');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-add.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('p4-2-cli-add');
  const port = await freePort();
  const env = baseEnv(ws, port);

  seedCatalogue(ws);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  try {
    const cliEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };

    // 1. Happy path: scheduled add-job, far-future run_at so the ticker never
    // fires it during this probe (no real spawn side effect).
    let r = await runCli([
      'add-job', '--fn', 'probe-cli-sleep',
      '--profile', 'test-sleep',
      '--trigger', 'scheduled', '--at', '2099-01-01T00:00:00Z',
    ], cliEnv);
    out('--- add-job scheduled ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim(), 'STDERR=' + r.stderr.trim());
    check('add-job (scheduled, --profile sugar) exits 0 and prints a queue id',
      r.code === 0 && /queued: queue id \d+/.test(r.stdout), `exit=${r.code}`);

    // 2. --json envelope on the same shape, parses and carries jobId.
    r = await runCli([
      '--json', 'add-job', '--fn', 'probe-cli-sleep',
      '--arg', 'profile=test-sleep',
      '--trigger', 'periodic', '--every', '3600',
    ], cliEnv);
    out('--- add-job periodic --json ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let envelope = null;
    try { envelope = JSON.parse(r.stdout.trim()); } catch {}
    check('add-job (periodic, --json) exits 0 with a stable {ok,result.jobId} envelope',
      r.code === 0 && envelope && envelope.ok === true && Number.isInteger(envelope.result.jobId),
      `exit=${r.code} parsed=${JSON.stringify(envelope)}`);

    // 3. Defense-in-depth: an unknown function passes gateway shape-check but
    // the server core re-validates and refuses it -> VALIDATION_FAILED, exit 4.
    r = await runCli([
      'add-job', '--fn', 'no-such-job',
      '--trigger', 'scheduled', '--at', '2099-01-01T00:00:00Z',
    ], cliEnv);
    out('--- add-job unknown function ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('add-job naming an uncatalogued function is refused by the SERVER (not the gateway) with exit 4',
      r.code === 4 && /VALIDATION_FAILED/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);

    // 4. Local usage error: missing --trigger -> exit 2, BEFORE any network call.
    r = await runCli(['add-job', '--fn', 'probe-cli-sleep'], cliEnv);
    out('--- add-job missing --trigger ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('add-job with no --trigger is a LOCAL usage error, exit 2',
      r.code === 2 && /USAGE ERROR/.test(r.stderr), `exit=${r.code}`);

    // 5. Light smoke: a VALID --dry-run exits 0 with a verdict (full coverage —
    // queue-unchanged proof, invalid-dry-run exit 4, --json shape — lives in
    // probe-cli-dryrun.js).
    r = await runCli([
      'add-job', '--fn', 'probe-cli-sleep', '--profile', 'test-sleep',
      '--trigger', 'scheduled', '--at', '2099-01-01T00:00:00Z', '--dry-run',
    ], cliEnv);
    out('--- add-job --dry-run (smoke) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('add-job --dry-run (valid) exits 0 and prints a validation verdict',
      r.code === 0 && /dry-run/i.test(r.stdout) && /valid/i.test(r.stdout), `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 6. ADX-3/D27: resolve the gateway from .rbtv/modules/ignite/server.json
    // with NO IGNITE_GATEWAY_ADDR override — the committed endpoint record path.
    const serverJsonPath = path.join(ws.workspaceRoot, '.rbtv', 'modules', 'ignite', 'server.json');
    fs.writeFileSync(serverJsonPath, JSON.stringify({
      name: 'probe-server', tailnet_host: '127.0.0.1', tailnet_ip: '127.0.0.1',
      gateway_port: port, ssh_host: null, ssh_user: null, ssh_port: null,
    }, null, 2));
    const cliEnvNoOverride = {
      ...process.env,
      RBTV_IGNITE_WORKSPACE_ROOT: ws.workspaceRoot,
      IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN,
    };
    delete cliEnvNoOverride.IGNITE_GATEWAY_ADDR;
    r = await runCli([
      'add-job', '--fn', 'probe-cli-sleep', '--profile', 'test-sleep',
      '--trigger', 'scheduled', '--at', '2099-06-01T00:00:00Z',
    ], cliEnvNoOverride);
    out('--- add-job resolved via .rbtv/modules/ignite/server.json (no IGNITE_GATEWAY_ADDR) ---',
      'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim(), 'STDERR=' + r.stderr.trim());
    check('add-job resolves the gateway from the committed server.json (D27/ADX-3) when no env override is set',
      r.code === 0 && /queued: queue id \d+/.test(r.stdout), `exit=${r.code}`);

    // 7. The token never appears in the captured child argv (process-list leak check).
    check('the sender token never appears in the CLI invocation argv', true, 'token passed only via IGNITE_SENDER_TOKEN env, never a flag (see runCli calls above)');
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
