'use strict';

// probe-cli-register — proves `ignite register-job` end-to-end through the REAL CLI
// binary against a REAL (throwaway) daemon (task 7.12; owner ruling 2026-07-25):
// happy-path registration, the CREATE-ONLY duplicate refusal (exit 4), validate-only
// --dry-run, --disabled, local usage errors (exit 2), the master-approximation authz
// (an `agent` sender may register; a `bridge` sender is refused UNAUTHORIZED_SENDER,
// which the ratified exit table puts in the catch-all exit 1 — 3 is AUTH_REFUSED,
// which an ENROLLED sender never draws), and the point
// of the whole surface: a job registered through the CLI is then visible in
// `inspect jobs` and enqueueable by `add-job`.
//
// ⚑ This probe deliberately does NOT call seedCatalogue: it registers through the
// shipped path instead. That is the proof — every other CLI probe seeds the catalogue
// by writing the store directly, which is exactly the bypass this task closes.
//
// NEVER touches the live daemon: throwaway workspace, throwaway senders file,
// ephemeral port; only the child this probe spawns is ever signaled.
//
// ⚑ REQUIRES A POSIX BOX (like every cli/ probe): it boots a real daemon, which needs
// systemd and the tree's one npm dependency (js-yaml). It is not runnable on Windows.

const fs = require('node:fs');
const path = require('node:path');
const {
  freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, runCli,
} = require('./lib/fixtures');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-register.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const SCHEMA = '{"required":{"profile":"string"},"optional":{"prompt":"string"}}';

// ⚑ The S-2(a) register-time gate (`229009b`) REFUSES a registration whose args_schema.required
// omits an argument its action type needs at enqueue — such a row would register, report
// enabled=1 forever, and be structurally unable to EVER fire, with no update or unregister
// surface to repair it. `fire-tool` requires `tool`. Every fire-tool registration below that is
// meant to SUCCEED must therefore declare it; the one that is meant to be refused is asserted
// explicitly further down, so the gate itself is covered rather than merely avoided.
const TOOL_SCHEMA = '{"required":{"tool":"string"}}';

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('p7-12-cli-register');
  const port = await freePort();
  const env = baseEnv(ws, port);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  // The summary block that sets the exit code is INSIDE main(), so this abort must carry
  // its own verdict: a bare `return` here exited 0 with the check above FAILED - a green
  // that survived a daemon that never booted, on any platform (task 7.701).
  if (!d.listening) { out('ABORT: daemon never listened.'); process.exitCode = 1; return; }

  try {
    const ownerEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };
    const agentEnv = ws.AGENT_TOKEN
      ? { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.AGENT_TOKEN }
      : null;
    const bridgeEnv = ws.BRIDGE_TOKEN
      ? { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.BRIDGE_TOKEN }
      : null;

    // 1. Happy path.
    let r = await runCli([
      'register-job', 'cli-registered', '--action-type', 'launch-agent',
      '--args-schema', SCHEMA, '--description', 'registered by probe-cli-register',
    ], ownerEnv);
    out('--- register-job ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim(), 'STDERR=' + r.stderr.trim());
    check('register-job exits 0 and reports what was registered',
      r.code === 0 && /registered: job "cli-registered"/.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 2. It is REALLY in the catalogue — read back through the read surface.
    r = await runCli(['inspect', 'jobs'], ownerEnv);
    check('the registered job appears in `inspect jobs`',
      r.code === 0 && r.stdout.includes('cli-registered'),
      `exit=${r.code} stdout=${r.stdout.trim().slice(0, 200)}`);

    // 3. CREATE-ONLY: a duplicate is a validation refusal (exit 4), not an overwrite.
    r = await runCli([
      'register-job', 'cli-registered', '--action-type', 'send-message',
    ], ownerEnv);
    out('--- duplicate ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim(), 'STDERR=' + r.stderr.trim());
    check('a duplicate id exits 4 (validation), never silently overwriting',
      r.code === 4,
      `exit=${r.code} stderr=${r.stderr.trim()}`);
    r = await runCli(['--json', 'inspect', 'jobs'], ownerEnv);
    check('the duplicate did NOT change the stored action_type',
      r.code === 0 && /"job_id":\s*"cli-registered"[^}]*"action_type":\s*"launch-agent"/.test(r.stdout.replace(/\s+/g, ' ')),
      `stdout=${r.stdout.trim().slice(0, 300)}`);

    // 4. Validate-only.
    r = await runCli(['register-job', 'dry-only', '--action-type', 'fire-tool', '--args-schema', TOOL_SCHEMA, '--dry-run'], ownerEnv);
    check('--dry-run exits 0 with a verdict',
      r.code === 0 && /dry-run: VALID/.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()}`);
    r = await runCli(['inspect', 'jobs'], ownerEnv);
    check('--dry-run registered NOTHING',
      r.code === 0 && !r.stdout.includes('dry-only'),
      `stdout=${r.stdout.trim().slice(0, 200)}`);

    // 5. --disabled registers a staged, non-runnable definition.
    r = await runCli(['register-job', 'staged', '--action-type', 'fire-tool', '--args-schema', TOOL_SCHEMA, '--disabled'], ownerEnv);
    check('--disabled registers with enabled=false',
      r.code === 0 && /disabled\)/.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 6. Local usage errors never reach the daemon (exit 2).
    r = await runCli(['register-job', 'no-type'], ownerEnv);
    check('a missing --action-type is a local usage error (exit 2)', r.code === 2, `exit=${r.code}`);
    r = await runCli(['register-job', 'bad-schema', '--action-type', 'fire-tool', '--args-schema', '{not json'], ownerEnv);
    check('a malformed --args-schema is a local usage error (exit 2)', r.code === 2, `exit=${r.code}`);

    // 6b. The S-2(a) register-time gate (`229009b`, campaign defect S-2): a registration whose
    // args_schema can NEVER satisfy its own action type is refused AT THE DOOR. This is a
    // VALIDATION refusal from the daemon (exit 4), not a local usage error — the argv is
    // well-formed; it is the combination that is unfireable. Added by task 7.52: the gate
    // shipped with no cli/ probe on it, and the three checks above were only taught to satisfy
    // it — teaching a probe to walk around a new production behaviour leaves that behaviour
    // uncovered by the suite that exists to cover it.
    r = await runCli(['register-job', 'unfireable', '--action-type', 'fire-tool'], ownerEnv);
    out('--- S-2(a) gate ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('a fire-tool job declaring no `tool` is REFUSED at registration (exit 4, E_BAD_ARGS)',
      r.code === 4 && /E_BAD_ARGS/.test(r.stderr) && /tool/.test(r.stderr),
      `exit=${r.code} stderr=${r.stderr.trim()}`);
    r = await runCli(['inspect', 'jobs'], ownerEnv);
    check('the refused unfireable job was NOT registered (the id stays free)',
      r.code === 0 && !r.stdout.includes('unfireable'),
      `stdout=${r.stdout.trim().slice(0, 200)}`);

    // 7. Authorization (owner ruling Call 1, build (ii)).
    if (bridgeEnv) {
      r = await runCli(['register-job', 'bridge-attempt', '--action-type', 'fire-tool'], bridgeEnv);
      // ⚑ EXIT 1, not 3. The ratified exit table gives 3 to AUTH_REFUSED only (an
      // unknown/disabled token, refused at the gateway). An ENROLLED bridge sender
      // passes auth and is denied by the CORE with UNAUTHORIZED_SENDER, which
      // `exitForEnvelopeCode` puts in the catch-all 1 — the same expectation
      // probe-cli-snooze asserts for its owner-only denial. Assert the code AND the
      // reason, so a 1 from an unrelated crash cannot pass as a refusal.
      check('a BRIDGE sender is refused UNAUTHORIZED_SENDER (exit 1 catch-all)',
        r.code === 1 && /UNAUTHORIZED_SENDER/.test(r.stderr),
        `exit=${r.code} stderr=${r.stderr.trim()}`);
    } else {
      out('SKIP  bridge-sender authz — the fixture workspace defines no bridge token');
    }
    if (agentEnv) {
      // ⚑ Asserts an ACCEPTED EXPOSURE, not a safety property: until CMP-13 (task 7.10)
      // lands, ANY enrolled agent token stands in for "the master".
      r = await runCli(['register-job', 'agent-registered', '--action-type', 'fire-tool', '--args-schema', TOOL_SCHEMA], agentEnv);
      // Assert the AUTHORIZATION property, not incidental success: exit 0 AND no authz refusal.
      // Before the schema above was supplied this check failed at exit 4 (VALIDATION_FAILED) —
      // i.e. the sender HAD passed authz and was stopped by an unrelated gate, so a bare
      // `code === 0` conflates "authorized" with "the whole call happened to succeed".
      check('an AGENT sender IS allowed (master approximation, owner ruling (ii))',
        r.code === 0 && !/UNAUTHORIZED_SENDER/.test(r.stderr),
        `exit=${r.code} stderr=${r.stderr.trim()}`);
    } else {
      out('SKIP  agent-sender authz — the fixture workspace defines no agent token');
    }

    // 7.605: the UNHOMED warning is SCOPED BY ACTION TYPE. Home gating is launch-agent only
    // (resolveJobHome has one call site, inside launchAgent), so a fire-tool row FIRES unhomed in
    // the default workdir and the launch wording is measured FALSE for it (w7603 evidence c05).
    // ⚠ issues.md S-11 (does a fire-tool row's goal/seat HOME its execution?) is OPEN; a ruling
    // toward homing changes the truthful wording these two arms pin.
    r = await runCli(['register-job', 'unhomed-launch-7605', '--action-type', 'launch-agent', '--args-schema', SCHEMA], ownerEnv);
    check('7.605 an unhomed LAUNCH row still warns that firing is a refusal',
      r.code === 0 && /UNHOMED — firing it is a refusal until homed/.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    r = await runCli(['register-job', 'unhomed-firetool-7605', '--action-type', 'fire-tool', '--args-schema', TOOL_SCHEMA], ownerEnv);
    check('7.605 an unhomed FIRE-TOOL row is told the truth (default workdir), not the launch refusal',
      r.code === 0 && /UNHOMED — runs in the default workdir/.test(r.stdout)
        && !/refusal until homed/.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 8. The payoff: register -> enqueue, both through the shipped CLI.
    r = await runCli([
      'add-job', '--fn', 'cli-registered', '--profile', 'test-sleep',
      '--trigger', 'scheduled', '--at', '2099-01-01T00:00:00Z',
    ], ownerEnv);
    check('a CLI-registered job is then enqueueable by add-job',
      r.code === 0 && /queued: queue id \d+/.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()} stderr=${r.stderr.trim()}`);
  } finally {
    await stopDaemon(d);
  }

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`CLI_REGISTER_OK: ${failed.length === 0}`);
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
