'use strict';

// probe-cli-status — proves `ignite inspect daemon` and `ignite status`
// end-to-end through the REAL CLI binary against a REAL (throwaway) daemon.

const fs = require('node:fs');
const path = require('node:path');
const {
  freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, runCli,
} = require('./lib/fixtures');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-status.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('p4-3-cli-status');
  const port = await freePort();
  const env = baseEnv(ws, port);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  const cliEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };

  try {
    // 1. inspect daemon — returns live health data.
    let r = await runCli(['--json', 'inspect', 'daemon'], cliEnv);
    out('--- inspect daemon --json ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let envelope = null;
    try { envelope = JSON.parse(r.stdout.trim()); } catch {}
    check('inspect daemon --json exits 0 and returns ok envelope with pid',
      r.code === 0 && envelope && envelope.ok === true
        && typeof envelope.result.pid === 'number' && envelope.result.pid > 0,
      `exit=${r.code} ok=${envelope && envelope.ok} pid=${envelope && envelope.result && envelope.result.pid}`);

    check('inspect daemon carries last_tick',
      envelope && envelope.ok && envelope.result.last_tick !== undefined,
      `last_tick=${envelope && envelope.result && envelope.result.last_tick}`);

    check('inspect daemon carries uptime_ms (non-negative)',
      envelope && envelope.ok && typeof envelope.result.uptime_ms === 'number' && envelope.result.uptime_ms >= 0,
      `uptime_ms=${envelope && envelope.result && envelope.result.uptime_ms}`);

    check('inspect daemon carries live_agent_sessions (non-negative integer)',
      envelope && envelope.ok && Number.isInteger(envelope.result.live_agent_sessions),
      `live_agent_sessions=${envelope && envelope.result && envelope.result.live_agent_sessions}`);

    check('inspect daemon carries config knobs',
      envelope && envelope.ok && envelope.result.config
        && typeof envelope.result.config.tick_interval_ms === 'number'
        && typeof envelope.result.config.max_live_agent_sessions === 'number',
      `config=${JSON.stringify(envelope && envelope.result && envelope.result.config)}`);

    check('inspect daemon carries queue_depth (non-negative integer)',
      envelope && envelope.ok && Number.isInteger(envelope.result.queue_depth),
      `queue_depth=${envelope && envelope.result && envelope.result.queue_depth}`);

    // 2. ignite status — same data, different entry point.
    r = await runCli(['--json', 'status'], cliEnv);
    out('--- ignite status --json ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let statusEnvelope = null;
    try { statusEnvelope = JSON.parse(r.stdout.trim()); } catch {}
    check('ignite status --json exits 0 and returns daemon health (pid present)',
      r.code === 0 && statusEnvelope && statusEnvelope.ok === true
        && typeof statusEnvelope.result.pid === 'number',
      `exit=${r.code} ok=${statusEnvelope && statusEnvelope.ok} pid=${statusEnvelope && statusEnvelope.result && statusEnvelope.result.pid}`);

    // 3. ignite status human-readable (default, no --json).
    r = await runCli(['status'], cliEnv);
    out('--- ignite status (human) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('ignite status exits 0 and renders something non-empty',
      r.code === 0 && r.stdout.trim().length > 0,
      `exit=${r.code} stdout_len=${r.stdout.trim().length}`);

    // 4. Local usage error for unknown args.
    r = await runCli(['inspect', 'daemon', 'extra'], cliEnv);
    out('--- inspect daemon with extra arg ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('inspect daemon with an extra arg is a LOCAL usage error, exit 2',
      r.code === 2 && /USAGE ERROR/.test(r.stderr), `exit=${r.code}`);
  } finally {
    await stopDaemon(d);

    // 5. ignite status against a STOPPED daemon prints "daemon: DOWN".
    let r = await runCli(['status'], cliEnv);
    out('--- ignite status (daemon stopped) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('ignite status with daemon stopped prints "daemon: DOWN" and exits 0',
      r.code === 0 && /daemon:\s*DOWN/.test(r.stdout), `exit=${r.code} stdout=${r.stdout.trim()}`);

    r = await runCli(['--json', 'status'], cliEnv);
    out('--- ignite status --json (daemon stopped) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let downEnvelope = null;
    try { downEnvelope = JSON.parse(r.stdout.trim()); } catch {}
    check('ignite status --json with daemon stopped returns DAEMON_DOWN envelope, exit 0',
      r.code === 0 && downEnvelope && downEnvelope.ok === false
        && downEnvelope.error && downEnvelope.error.code === 'DAEMON_DOWN',
      `exit=${r.code} parsed=${JSON.stringify(downEnvelope)}`);

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
