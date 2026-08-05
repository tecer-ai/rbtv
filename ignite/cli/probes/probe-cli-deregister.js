'use strict';

// probe-cli-deregister — proves `ignite deregister-job` end-to-end through the REAL CLI
// binary against a REAL (throwaway) daemon (task 7.364 / F20; issue
// G-m4-demo-verdict-assembler-0804-1610).
//
// THE FAILURE THIS COVERS, and why the control matters more than the happy path: before
// this verb, a registered definition could never be stopped — `remove-job` takes a QUEUE
// id and never touches the catalogue — so a homed job outlived the goal tree it named.
// A stop path that REPORTS SUCCESS OVER NOTHING is worse than no stop path at all: a
// teardown ledger would record the job as retired while it stayed enabled and fireable.
// So check 4 (an unknown id is REFUSED, non-zero) is the discriminating one; checks 1-3
// only show the mechanism moving.
//
// What it proves:
//   1. `inspect jobs` shows the throwaway definition enabled=1/fireable BEFORE.
//   2. deregister-job exits 0 and says what it did.
//   3. `inspect jobs` shows the SAME row enabled=0 AFTER — the state actually changed,
//      read back through the tool's own read surface, never from the command's own line.
//   4. CONTROL: an UNKNOWN job id is REFUSED (exit 4, VALIDATION_FAILED / E_UNKNOWN_JOB),
//      and the catalogue is unchanged by the attempt.
//   5. A DISABLED definition is no longer enqueueable — add-job refuses it. The stop is
//      real, not a cosmetic flag.
//   6. Idempotent: a second deregister of the same id succeeds and reports that nothing
//      changed (a teardown must be re-runnable).
//   7. `ignite --help` lists the verb — read out of the TOOL's own help output.
//   8. A BRIDGE sender is refused UNAUTHORIZED_SENDER; an AGENT sender is allowed (the
//      same master-approximation policy the create arm carries).
//
// NEVER touches the live daemon or the live catalogue: throwaway workspace, throwaway
// senders file, ephemeral port; only the child this probe spawns is ever signaled.
//
// ⚑ REQUIRES A POSIX BOX (like every cli/ probe): it boots a real daemon.

const fs = require('node:fs');
const path = require('node:path');
const { freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, runCli } = require('./lib/fixtures');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-deregister.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// `launch-agent` requires `profile` in args_schema.required (the S-2(a) register-time
// gate), or the registration below is refused before this probe reaches its subject.
const SCHEMA = '{"required":{"profile":"string"}}';

// The row for a given job id out of `inspect jobs --json`, so every state assertion is a
// FIELD read rather than a substring match on rendered text.
// ⚑ The envelope key is `result.rows` (inspect.js renderRows), NOT `result.jobs`. An
// earlier cut of this probe read `.jobs`, got undefined, and reported BOTH state checks
// FAIL against a verb that was working — a reader that cannot find the row is
// indistinguishable from a row that is not there, so it must throw rather than return null.
function jobRows(stdout) {
  const rows = JSON.parse(stdout).result.rows;
  if (!Array.isArray(rows)) throw new Error(`inspect jobs --json carried no result.rows: ${stdout.slice(0, 200)}`);
  return rows;
}

function jobRow(stdout, jobId) {
  return jobRows(stdout).find((j) => j.job_id === jobId) || null;
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('p7-364-cli-deregister');
  const port = await freePort();
  const env = baseEnv(ws, port);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  try {
    const ownerEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };
    const agentEnv = ws.AGENT_TOKEN
      ? { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.AGENT_TOKEN }
      : null;
    const bridgeEnv = ws.BRIDGE_TOKEN
      ? { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.BRIDGE_TOKEN }
      : null;

    // Registered through the SHIPPED path, not seeded into the store: the subject of this
    // probe is the catalogue surface, and a fixture write would bypass the very pipeline
    // the deregister half has to work through.
    let r = await runCli(['register-job', 'throwaway-deregister', '--action-type', 'launch-agent', '--args-schema', SCHEMA], ownerEnv);
    check('a throwaway definition registers (setup)', r.code === 0, `exit=${r.code} stderr=${r.stderr.trim()}`);

    // 1. BEFORE.
    r = await runCli(['--json', 'inspect', 'jobs'], ownerEnv);
    const before = jobRow(r.stdout, 'throwaway-deregister');
    out('--- inspect jobs BEFORE ---', JSON.stringify(before));
    check('BEFORE: the definition is present and enabled=1',
      !!before && before.enabled === 1, `row=${JSON.stringify(before)}`);

    // 2. The act.
    r = await runCli(['deregister-job', 'throwaway-deregister'], ownerEnv);
    out('--- deregister-job ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim(), 'STDERR=' + r.stderr.trim());
    check('deregister-job exits 0 and reports the retirement',
      r.code === 0 && /throwaway-deregister/.test(r.stdout) && /disabled/.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 3. AFTER — the state change read back through the READ surface.
    r = await runCli(['--json', 'inspect', 'jobs'], ownerEnv);
    const after = jobRow(r.stdout, 'throwaway-deregister');
    out('--- inspect jobs AFTER ---', JSON.stringify(after));
    check('AFTER: the SAME row is still present and now enabled=0',
      !!after && after.enabled === 0, `row=${JSON.stringify(after)}`);

    // 4. ⚑ THE DISCRIMINATING CONTROL. An unknown id must REFUSE, not report success.
    //    Asserted on the EXIT CODE (captured before any pipe) AND the typed code, so a
    //    non-zero from an unrelated crash cannot pass as the refusal.
    const beforeUnknown = (await runCli(['--json', 'inspect', 'jobs'], ownerEnv)).stdout;
    r = await runCli(['deregister-job', 'no-such-job-id-ever-registered'], ownerEnv);
    out('--- CONTROL: unknown id ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim(), 'STDERR=' + r.stderr.trim());
    check('CONTROL: an UNKNOWN job id is REFUSED (exit 4, E_UNKNOWN_JOB) — never success over nothing',
      r.code === 4 && /E_UNKNOWN_JOB|unknown job/.test(r.stderr) && !/deregistered:/.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()} stderr=${r.stderr.trim()}`);
    const afterUnknown = (await runCli(['--json', 'inspect', 'jobs'], ownerEnv)).stdout;
    check('CONTROL: the refused attempt changed no catalogue row',
      JSON.stringify(jobRows(beforeUnknown)) === JSON.stringify(jobRows(afterUnknown)),
      `rows before=${jobRows(beforeUnknown).length} after=${jobRows(afterUnknown).length}`);

    // 5. The stop is REAL: a disabled definition cannot be scheduled.
    r = await runCli([
      'add-job', '--fn', 'throwaway-deregister', '--profile', 'test-sleep',
      '--trigger', 'scheduled', '--at', '2099-01-01T00:00:00Z',
    ], ownerEnv);
    out('--- add-job on a deregistered job ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('a DEREGISTERED definition can no longer be enqueued (E_JOB_DISABLED)',
      r.code !== 0 && /E_JOB_DISABLED|disabled/.test(r.stderr),
      `exit=${r.code} stderr=${r.stderr.trim()}`);

    // 6. Idempotence — a teardown gets re-run.
    r = await runCli(['deregister-job', 'throwaway-deregister'], ownerEnv);
    check('deregistering an ALREADY-disabled job succeeds and says nothing changed',
      r.code === 0 && /already disabled/.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 7. The tool's OWN help lists the verb (read from help output, not from the source).
    r = await runCli(['--help'], ownerEnv);
    check('`ignite --help` lists deregister-job',
      r.code === 0 && /ignite deregister-job <job-id>/.test(r.stdout),
      `exit=${r.code}`);

    // 8. Authorization — the create arm's policy, verbatim.
    if (bridgeEnv) {
      r = await runCli(['deregister-job', 'throwaway-deregister'], bridgeEnv);
      // EXIT 1, not 3: 3 is AUTH_REFUSED (unknown/disabled token, refused at the gateway);
      // an ENROLLED bridge passes auth and is denied by the CORE with UNAUTHORIZED_SENDER,
      // which the ratified exit table puts in the catch-all 1 (probe-cli-register's note).
      check('a BRIDGE sender is refused UNAUTHORIZED_SENDER (exit 1 catch-all)',
        r.code === 1 && /UNAUTHORIZED_SENDER/.test(r.stderr) && /deregister-job requires/.test(r.stderr),
        `exit=${r.code} stderr=${r.stderr.trim()}`);
    } else {
      out('SKIP  bridge-sender authz — the fixture workspace defines no bridge token');
    }
    if (agentEnv) {
      // ⚑ Asserts an ACCEPTED EXPOSURE, not a safety property (see authz.canRegisterJob):
      // until CMP-13 lands, ANY enrolled agent token stands in for "the master".
      await runCli(['register-job', 'agent-target', '--action-type', 'launch-agent', '--args-schema', SCHEMA], ownerEnv);
      r = await runCli(['deregister-job', 'agent-target'], agentEnv);
      check('an AGENT sender IS allowed (master approximation, same policy as register)',
        r.code === 0 && !/UNAUTHORIZED_SENDER/.test(r.stderr),
        `exit=${r.code} stderr=${r.stderr.trim()}`);
    } else {
      out('SKIP  agent-sender authz — the fixture workspace defines no agent token');
    }
  } finally {
    await stopDaemon(d);
  }

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`CLI_DEREGISTER_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
}

main().catch((err) => {
  out('ERROR:', err.message, err.stack);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
});
