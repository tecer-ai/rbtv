'use strict';

// probe-cli-snooze — proves `ignite snooze <kind> <subject> --minutes <N>`
// end-to-end through the REAL CLI binary against a REAL (throwaway) daemon
// (ADX-14): a real standing warning gets snoozed and the CLI says loudly what
// was snoozed and until when; snoozing a (kind, subject) with NO standing
// warning is a clean no-op, never an error; a non-owner sender is refused
// UNAUTHORIZED_SENDER (D45/D71 owner-only authz); local usage errors.
//
// NEVER touches the live daemon: throwaway workspace, throwaway senders file,
// ephemeral port; only the child this probe spawns is ever signaled.

const fs = require('node:fs');
const path = require('node:path');
const {
  freePort, makeWorkspace, baseEnv, bootDaemon, waitForLog, stopDaemon, seedWarning, runCli,
} = require('./lib/fixtures');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-snooze.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('p4-2-cli-snooze');
  const port = await freePort();
  const env = baseEnv(ws, port);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  // ⚑ Seeded AFTER the daemon's INITIAL TICK completes, not merely after
  // "gateway listening" (that log line fires BEFORE the initial tick runs —
  // confirmed empirically: a warning seeded right after "gateway listening"
  // still got cleared, because server/index.js runs one tick synchronously
  // right after the listener comes up, and every tick's warnings-check
  // (server/ticker/warnings-check.js) CLEARS any standing
  // `seat-blocked-budget-exhausted` warning whose subject is not a REAL
  // blocked+budget-exhausted chain). Waiting for "initial tick complete"
  // lands this probe's seed in the ~10s gap before the NEXT scheduled tick
  // (server/ticker/ticker.js DEFAULT_CONFIG tick_interval_ms), ample time for
  // the handful of CLI calls this probe makes.
  await waitForLog(d, /"message":"initial tick complete"/);
  const warning = seedWarning(ws, { kind: 'seat-blocked-budget-exhausted', subject: 'probe-seat' });
  out(`seeded standing warning (after the daemon's initial tick): ${JSON.stringify(warning)}`);

  const ownerEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };
  const agentEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.AGENT_TOKEN };

  try {
    // 1. Snoozing a REAL standing warning as the owner: loud success naming
    // what was snoozed and until when.
    let r = await runCli(['snooze', 'seat-blocked-budget-exhausted', 'probe-seat', '--minutes', '30'], ownerEnv);
    out('--- snooze (hit) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('snooze on a real standing warning exits 0 and loudly names what was snoozed and until when',
      r.code === 0 && /^snoozed: seat-blocked-budget-exhausted\/probe-seat until tick \d+$/.test(r.stdout.trim()),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 2. --json shape: { ok, result: { snoozed:true, kind, subject, snoozed_until_tick } }.
    r = await runCli(['--json', 'snooze', 'seat-blocked-budget-exhausted', 'probe-seat', '--minutes', '30'], ownerEnv);
    out('--- snooze --json (hit again) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let envelope = null;
    try { envelope = JSON.parse(r.stdout.trim()); } catch {}
    check('snooze --json exits 0 with a stable {ok,result:{snoozed:true,snoozed_until_tick}} envelope',
      r.code === 0 && envelope && envelope.ok === true && envelope.result.snoozed === true && Number.isInteger(envelope.result.snoozed_until_tick),
      `exit=${r.code} parsed=${JSON.stringify(envelope)}`);

    // 3. No standing warning for (kind, subject) -> a CLEAN NO-OP, exit 0, never
    // an error (D45).
    r = await runCli(['snooze', 'seat-blocked-budget-exhausted', 'no-such-seat', '--minutes', '10'], ownerEnv);
    out('--- snooze (no-op) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('snooze with no standing warning is a CLEAN NO-OP, exit 0, never an error (D45)',
      r.code === 0 && /^nothing to snooze: no standing warning for seat-blocked-budget-exhausted\/no-such-seat$/.test(r.stdout.trim()),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 4. OWNER-ONLY authz: a non-owner (agent) sender is refused UNAUTHORIZED_SENDER.
    r = await runCli(['snooze', 'seat-blocked-budget-exhausted', 'probe-seat', '--minutes', '10'], agentEnv);
    out('--- snooze (non-owner sender) ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('snooze from a non-owner sender is refused UNAUTHORIZED_SENDER (D45/D71 owner-only, exit 1 catch-all)',
      r.code === 1 && /UNAUTHORIZED_SENDER/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);

    // 5. Local usage errors: missing --minutes, non-positive minutes, missing subject.
    r = await runCli(['snooze', 'seat-blocked-budget-exhausted', 'probe-seat'], ownerEnv);
    out('--- snooze missing --minutes ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('snooze with no --minutes is a LOCAL usage error, exit 2', r.code === 2 && /USAGE ERROR/.test(r.stderr), `exit=${r.code}`);

    r = await runCli(['snooze', 'seat-blocked-budget-exhausted', 'probe-seat', '--minutes', '0'], ownerEnv);
    out('--- snooze --minutes 0 ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('snooze --minutes 0 is a LOCAL usage error, exit 2', r.code === 2 && /USAGE ERROR/.test(r.stderr), `exit=${r.code}`);

    r = await runCli(['snooze', 'seat-blocked-budget-exhausted'], ownerEnv);
    out('--- snooze missing subject ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('snooze with no subject is a LOCAL usage error, exit 2', r.code === 2 && /USAGE ERROR/.test(r.stderr), `exit=${r.code}`);

    // 6. There is no dismiss/clear/delete subcommand (D45: snooze never clears).
    r = await runCli(['dismiss', 'seat-blocked-budget-exhausted', 'probe-seat'], ownerEnv);
    out('--- dismiss (must not exist) ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('there is no dismiss/clear/acknowledge/delete subcommand — "dismiss" is an unknown command (D45: snooze never clears)',
      r.code === 2 && /unknown command "dismiss"/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);
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
