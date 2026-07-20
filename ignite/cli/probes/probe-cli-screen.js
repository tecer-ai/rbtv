'use strict';

// probe-cli-screen — proves `ignite screen <session-id>` end-to-end through
// the REAL CLI binary against a REAL (throwaway) daemon, WITHOUT ever needing
// a live headed session (cli-expansion decisions D4): local usage error on a
// missing id (exit 2); gateway SHAPE_INVALID on a non-integer id (exit 4);
// typed NOT_FOUND on a nonexistent session (exit 1, catch-all); the headed-only
// refusal on a headless execution row (exit 4); the never-spawned liveness
// refusal on a headed row with no transcript log (exit 4); and the --json
// envelope shape on each path.
//
// NEVER touches the live daemon: throwaway workspace, throwaway senders file,
// ephemeral port; only the child this probe spawns is ever signaled.

const fs = require('node:fs');
const path = require('node:path');
const {
  IGNITE_SRC, freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, seedCatalogue, runCli,
} = require('./lib/fixtures');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-screen.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// LOCAL fixture helper (fixtures.js is READ-ONLY — D4: a missing helper is
// built locally inside the probe file). Seeds one HEADED execution row that
// never reached spawn (no log_path), directly into the same sqlite db the
// daemon will open — exactly the seedCatalogue(withExecution) pattern, before
// the daemon boots. This is TEST-FIXTURE SETUP in this probe's own process,
// not the CLI bypassing the gateway.
function seedHeadedNeverSpawnedRow(ws) {
  const { openHeartStore, closeHeartStore } =
    require(path.join(IGNITE_SRC, 'server', 'heart', 'heart-store'));
  const store = openHeartStore({ runtimeStateRoot: ws.workspaceRoot });
  try {
    const row = store.recordExecutionStart({
      jobId: 'probe-cli-sleep',
      actionType: 'launch-agent',
      args: JSON.stringify({ profile: 'test-sleep' }),
      enqueuedBy: 'probe-owner',
      sessionMode: 'headed',
      firedTick: 0,
      firedAt: new Date(),
      profile: 'test-sleep',
    });
    return row.exec_id;
  } finally {
    closeHeartStore();
  }
}

function parseEnvelope(r) {
  try { return JSON.parse(r.stdout.trim()); } catch { return null; }
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('ce-3-cli-screen');
  const port = await freePort();
  const env = baseEnv(ws, port);
  // Seed BEFORE boot (fixtures discipline): the catalogue job + one HEADLESS
  // execution row (headed-only refusal target) + one HEADED never-spawned row
  // (liveness-refusal target).
  const { execId: headlessExecId } = seedCatalogue(ws, { withExecution: true });
  const headedExecId = seedHeadedNeverSpawnedRow(ws);
  out(`seeded headless exec_id=${headlessExecId} headed(never-spawned) exec_id=${headedExecId}`);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  const cliEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };

  try {
    // 1. Missing id: LOCAL usage error, exit 2 — and the --json envelope keeps
    // the same {ok:false,error:{code}} shape with the CLI-local code.
    let r = await runCli(['screen'], cliEnv);
    out('--- screen missing id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('screen with no id is a LOCAL usage error, exit 2',
      r.code === 2 && /USAGE ERROR/.test(r.stderr), `exit=${r.code}`);

    r = await runCli(['--json', 'screen'], cliEnv);
    out('--- screen missing id --json ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let envl = parseEnvelope(r);
    check('missing id under --json is the standard envelope with CLI_USAGE_ERROR, exit 2',
      r.code === 2 && envl && envl.ok === false && envl.error.code === 'CLI_USAGE_ERROR',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 2. Non-integer id: the CLI forwards it and the GATEWAY shape-check
    // refuses it — SHAPE_INVALID, exit 4 (never a local exit-2).
    r = await runCli(['screen', 'not-a-number'], cliEnv);
    out('--- screen non-integer id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('screen with a non-integer id is a gateway shape refusal (SHAPE_INVALID), exit 4',
      r.code === 4 && /SHAPE_INVALID/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);

    r = await runCli(['--json', 'screen', 'not-a-number'], cliEnv);
    out('--- screen non-integer id --json ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    envl = parseEnvelope(r);
    check('non-integer id under --json is the gateway envelope with SHAPE_INVALID, exit 4',
      r.code === 4 && envl && envl.ok === false && envl.error.code === 'SHAPE_INVALID',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 3. Nonexistent session: typed NOT_FOUND from the core's re-validation —
    // exit 1 (catch-all per the exit-code table).
    r = await runCli(['screen', '999999'], cliEnv);
    out('--- screen nonexistent session ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('screen on a nonexistent session is a typed NOT_FOUND, exit 1 (catch-all)',
      r.code === 1 && /NOT_FOUND/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);

    r = await runCli(['--json', 'screen', '999999'], cliEnv);
    out('--- screen nonexistent session --json ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    envl = parseEnvelope(r);
    check('nonexistent session under --json is the gateway envelope with NOT_FOUND, exit 1',
      r.code === 1 && envl && envl.ok === false && envl.error.code === 'NOT_FOUND',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 4. Deeper path the throwaway daemon honestly serves: a HEADLESS execution
    // row — the headed-only refusal (D7/D17), VALIDATION_FAILED, exit 4.
    r = await runCli(['screen', String(headlessExecId)], cliEnv);
    out('--- screen headless session ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('screen on a HEADLESS session is the headed-only refusal (VALIDATION_FAILED), exit 4',
      r.code === 4 && /VALIDATION_FAILED/.test(r.stderr) && /headed-only/.test(r.stderr),
      `exit=${r.code} stderr=${r.stderr.trim()}`);

    r = await runCli(['--json', 'screen', String(headlessExecId)], cliEnv);
    out('--- screen headless session --json ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    envl = parseEnvelope(r);
    check('headless refusal under --json is the gateway envelope with VALIDATION_FAILED, exit 4',
      r.code === 4 && envl && envl.ok === false && envl.error.code === 'VALIDATION_FAILED',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 5. Deeper path #2: a HEADED row that never reached spawn (no transcript
    // log) — the narrow structural liveness guard (the C3(b) finding),
    // VALIDATION_FAILED / E_SESSION_NOT_LIVE, exit 4.
    r = await runCli(['screen', String(headedExecId)], cliEnv);
    out('--- screen headed never-spawned ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('screen on a headed row that never spawned is the liveness refusal (VALIDATION_FAILED), exit 4',
      r.code === 4 && /VALIDATION_FAILED/.test(r.stderr) && /never spawned/.test(r.stderr),
      `exit=${r.code} stderr=${r.stderr.trim()}`);
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
