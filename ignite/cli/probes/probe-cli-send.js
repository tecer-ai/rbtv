'use strict';

// probe-cli-send — proves `ignite send <session-id> --data <string>` end-to-end
// through the REAL CLI binary against a REAL (throwaway) daemon: local usage
// errors (exit 2); gateway shape refusals (exit 4) on a non-integer id and on
// empty data; typed NOT_FOUND for a session that does not exist (exit 1); and
// the deepest path this daemon can honestly serve WITHOUT a live headed
// session (run decisions D4) — a REAL seeded execution row whose
// session_mode:headless draws the server's headed-only re-validation refusal
// (exit 4), proving the full gateway->server->store->authz->mode chain. The
// `--json` envelope shape is asserted on every path.
//
// NEVER touches the live daemon: throwaway workspace, throwaway senders file,
// ephemeral port; only the child this probe spawns is ever signaled.

const fs = require('node:fs');
const path = require('node:path');
const {
  freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, seedCatalogue, runCli,
} = require('./lib/fixtures');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-send.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

function parseEnvelope(r) {
  try { return JSON.parse(r.stdout.trim()); } catch { return null; }
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('ce-2-cli-send');
  const port = await freePort();
  const env = baseEnv(ws, port);
  // A REAL execution row (session_mode defaults to headless) — the honest
  // server-side target for the headed-only refusal below.
  const { execId } = seedCatalogue(ws, { withExecution: true });
  out(`seeded headless execution exec_id=${execId}`);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  const cliEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };

  try {
    // 1. Local usage errors, exit 2: missing id, missing --data, extra args.
    let r = await runCli(['send'], cliEnv);
    out('--- send (no args) ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('send with no arguments is a LOCAL usage error, exit 2',
      r.code === 2 && /USAGE ERROR/.test(r.stderr) && /session-id/.test(r.stderr), `exit=${r.code}`);

    r = await runCli(['send', String(execId)], cliEnv);
    out('--- send (missing --data) ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('send with no --data is a LOCAL usage error, exit 2',
      r.code === 2 && /USAGE ERROR/.test(r.stderr) && /--data/.test(r.stderr), `exit=${r.code}`);

    r = await runCli(['--json', 'send', String(execId)], cliEnv);
    let envl = parseEnvelope(r);
    out('--- send (missing --data, --json) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('--json on a local usage error keeps the envelope shape with code CLI_USAGE_ERROR, exit 2',
      r.code === 2 && envl !== null && envl.ok === false && envl.error.code === 'CLI_USAGE_ERROR',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    r = await runCli(['send', String(execId), '--data', 'x', 'stray-extra'], cliEnv);
    out('--- send (extra arg) ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('send with an unrecognized extra argument is a LOCAL usage error, exit 2',
      r.code === 2 && /USAGE ERROR/.test(r.stderr) && /unrecognized/.test(r.stderr), `exit=${r.code}`);

    // 2. Gateway shape refusal, exit 4: a NON-INTEGER id crosses as argv gave
    //    it (the CLI never pre-validates it) and the gateway refuses it typed.
    r = await runCli(['send', 'not-a-number', '--data', 'hi'], cliEnv);
    out('--- send non-integer id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('send with a non-integer id is the GATEWAY\'s typed shape refusal, exit 4',
      r.code === 4 && /SHAPE_INVALID/.test(r.stderr) && /integer session id/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);

    r = await runCli(['--json', 'send', 'not-a-number', '--data', 'hi'], cliEnv);
    envl = parseEnvelope(r);
    out('--- send non-integer id (--json) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('--json on the non-integer-id refusal is the gateway envelope verbatim: ok:false, code SHAPE_INVALID, exit 4',
      r.code === 4 && envl !== null && envl.ok === false && envl.error.code === 'SHAPE_INVALID',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 3. Gateway shape refusal, exit 4: EMPTY data. `--data ''` is PRESENT
    //    (so no local usage error) but empty — the gateway owns the non-empty
    //    check (parse.js parseSendToSession), the CLI never duplicates it.
    r = await runCli(['send', String(execId), '--data', ''], cliEnv);
    out('--- send empty data ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('send with empty --data is the GATEWAY\'s typed shape refusal, exit 4',
      r.code === 4 && /SHAPE_INVALID/.test(r.stderr) && /non-empty data/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);

    r = await runCli(['--json', 'send', String(execId), '--data', ''], cliEnv);
    envl = parseEnvelope(r);
    out('--- send empty data (--json) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('--json on the empty-data refusal is the gateway envelope verbatim: ok:false, code SHAPE_INVALID, exit 4',
      r.code === 4 && envl !== null && envl.ok === false && envl.error.code === 'SHAPE_INVALID' && envl.error.details && envl.error.details.field === 'data',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 4. A session that does not exist: typed NOT_FOUND from the server's own
    //    re-validation (exit 1, the catch-all row of the exit-code table).
    r = await runCli(['send', '999999', '--data', 'hi'], cliEnv);
    out('--- send unknown id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('send to an execution id that does not exist is a typed NOT_FOUND, exit 1',
      r.code === 1 && /NOT_FOUND/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);

    r = await runCli(['--json', 'send', '999999', '--data', 'hi'], cliEnv);
    envl = parseEnvelope(r);
    out('--- send unknown id (--json) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('--json on the unknown-id refusal is the gateway envelope verbatim: ok:false, code NOT_FOUND, exit 1',
      r.code === 1 && envl !== null && envl.ok === false && envl.error.code === 'NOT_FOUND',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 5. The deepest HONEST path without a live headed session (D4): the
    //    seeded row EXISTS and the owner IS authorized, so the request runs
    //    the full gateway->server->store->authz chain and is refused at the
    //    headed-only mode check — proving id coercion, auth, and the server's
    //    complete re-validation, not just gateway parsing.
    r = await runCli(['send', String(execId), '--data', 'hi'], cliEnv);
    out('--- send to headless session ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('send to a REAL headless execution is the server\'s headed-only re-validation refusal (VALIDATION_FAILED), exit 4',
      r.code === 4 && /VALIDATION_FAILED/.test(r.stderr) && /headed-only/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);

    r = await runCli(['--json', 'send', String(execId), '--data', 'hi'], cliEnv);
    envl = parseEnvelope(r);
    out('--- send to headless session (--json) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('--json on the headed-only refusal carries the server\'s typed details (check:session-mode, the session\'s own mode), exit 4',
      r.code === 4 && envl !== null && envl.ok === false && envl.error.code === 'VALIDATION_FAILED'
        && envl.error.details && envl.error.details.check === 'session-mode' && envl.error.details.session_mode === 'headless',
      `exit=${r.code} stdout=${r.stdout.trim()}`);
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
