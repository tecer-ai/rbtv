'use strict';

// probe-cli-inspect — proves `ignite inspect jobs|queue|status <id>|logs <id>
// [--tail n]` end-to-end through the REAL CLI binary against a REAL
// (throwaway) daemon.
//
// NEVER touches the live daemon: throwaway workspace, throwaway senders file,
// ephemeral port; only the child this probe spawns is ever signaled.

const fs = require('node:fs');
const path = require('node:path');
const {
  freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, seedCatalogue, runCli,
} = require('./lib/fixtures');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-inspect.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('p4-2-cli-inspect');
  const port = await freePort();
  const env = baseEnv(ws, port);

  const LOG_LINES = Array.from({ length: 20 }, (_, i) => `line ${i + 1}`);
  const { execId } = seedCatalogue(ws, { withExecution: true }); // never-spawned: no log_path
  const { execId: execIdWithLog } = seedCatalogue(ws, { withExecution: true, withLogLines: LOG_LINES });
  out(`seeded exec_id=${execId} (no log), exec_id=${execIdWithLog} (${LOG_LINES.length} real log lines)`);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  const cliEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };

  try {
    // 1. inspect jobs — the seeded catalogue row renders.
    let r = await runCli(['inspect', 'jobs'], cliEnv);
    out('--- inspect jobs ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('inspect jobs exits 0 and lists the seeded catalogue job',
      r.code === 0 && /probe-cli-sleep/.test(r.stdout), `exit=${r.code}`);

    // 2. Enqueue a real queue row through add-job, then inspect queue sees it.
    r = await runCli([
      'add-job', '--fn', 'probe-cli-sleep', '--profile', 'test-sleep',
      '--trigger', 'scheduled', '--at', '2099-01-01T00:00:00Z',
    ], cliEnv);
    check('setup: add-job for the inspect-queue check succeeds', r.code === 0, `exit=${r.code} ${r.stderr}`);
    const queueId = (r.stdout.match(/queue id (\d+)/) || [])[1];

    r = await runCli(['--json', 'inspect', 'queue'], cliEnv);
    out('--- inspect queue --json ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let envelope = null;
    try { envelope = JSON.parse(r.stdout.trim()); } catch {}
    const rows = envelope && envelope.ok ? envelope.result.rows : [];
    check('inspect queue --json exits 0 and shows the row just enqueued',
      r.code === 0 && Array.isArray(rows) && rows.some((row) => String(row.queue_id) === queueId),
      `exit=${r.code} queueId=${queueId} rows=${JSON.stringify(rows)}`);

    // 3. inspect status <exec-id> on the seeded execution.
    r = await runCli(['inspect', 'status', String(execId)], cliEnv);
    out('--- inspect status ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim(), 'STDERR=' + r.stderr.trim());
    check('inspect status <exec-id> exits 0 and renders the execution snapshot',
      r.code === 0 && new RegExp(`"id":${execId}`).test(r.stdout), `exit=${r.code}`);

    // 4. inspect status on an id that does not exist -> typed NOT_FOUND, exit 1
    // (NOT_FOUND has no dedicated exit code in gateway-cli-spec.md's table —
    // it falls into the documented catch-all "1 anything else").
    r = await runCli(['inspect', 'status', '999999'], cliEnv);
    out('--- inspect status unknown id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('inspect status on an unknown exec-id is a typed NOT_FOUND, exit 1',
      r.code === 1 && /NOT_FOUND/.test(r.stderr), `exit=${r.code}`);

    // 5. inspect logs <exec-id> — the seeded execution was never actually
    // spawned (this probe deliberately avoids a real spawn, see fixtures.js
    // header), so the server core correctly refuses with a typed NOT_FOUND
    // ("no log for session") rather than a fabricated empty log. This proves
    // the round trip renders the REAL typed error, exit 1 (NOT_FOUND has no
    // dedicated exit code — gateway-cli-spec.md's catch-all).
    r = await runCli(['--json', 'inspect', 'logs', String(execId)], cliEnv);
    out('--- inspect logs (never-spawned execution) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let logsEnvelope = null;
    try { logsEnvelope = JSON.parse(r.stdout.trim()); } catch {}
    check('inspect logs <exec-id> on a never-spawned execution surfaces the REAL typed NOT_FOUND, exit 1',
      r.code === 1 && logsEnvelope && logsEnvelope.ok === false && logsEnvelope.error.code === 'NOT_FOUND',
      `exit=${r.code} parsed=${JSON.stringify(logsEnvelope)}`);

    // 6. inspect logs --tail N: the client-side offset/limit walk (inspect.js)
    // must SHORT-CIRCUIT and propagate the first page's error unmasked, never
    // loop or paper over it with a fabricated success.
    r = await runCli(['--json', 'inspect', 'logs', String(execId), '--tail', '5'], cliEnv);
    out('--- inspect logs --tail 5 (never-spawned execution) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let tailEnvelope = null;
    try { tailEnvelope = JSON.parse(r.stdout.trim()); } catch {}
    check('inspect logs --tail 5 propagates the SAME typed error unmasked (no fake success from the paging loop)',
      r.code === 1 && tailEnvelope && tailEnvelope.ok === false && tailEnvelope.error.code === 'NOT_FOUND',
      `exit=${r.code} parsed=${JSON.stringify(tailEnvelope)}`);

    // 7. inspect logs <exec-id> on an execution with a REAL captured log —
    // proves the CLI renders REAL content end-to-end, not just the error path.
    r = await runCli(['--json', 'inspect', 'logs', String(execIdWithLog)], cliEnv);
    out('--- inspect logs (real content) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let realLogsEnvelope = null;
    try { realLogsEnvelope = JSON.parse(r.stdout.trim()); } catch {}
    check('inspect logs <exec-id> on a real log renders the actual captured lines',
      r.code === 0 && realLogsEnvelope && realLogsEnvelope.ok === true
        && realLogsEnvelope.result.lines[0] === 'line 1'
        && realLogsEnvelope.result.lines.length === LOG_LINES.length,
      `exit=${r.code} lineCount=${realLogsEnvelope && realLogsEnvelope.result && realLogsEnvelope.result.lines.length}`);

    // 8. inspect logs --tail 5 on that same real log — the client-side
    // offset/limit walk must return exactly the LAST 5 lines, not the first.
    r = await runCli(['--json', 'inspect', 'logs', String(execIdWithLog), '--tail', '5'], cliEnv);
    out('--- inspect logs --tail 5 (real content) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let realTailEnvelope = null;
    try { realTailEnvelope = JSON.parse(r.stdout.trim()); } catch {}
    const expectedTail = LOG_LINES.slice(-5);
    check('inspect logs --tail 5 returns exactly the LAST 5 lines (not the first 5)',
      r.code === 0 && realTailEnvelope && realTailEnvelope.ok === true
        && JSON.stringify(realTailEnvelope.result.lines) === JSON.stringify(expectedTail),
      `exit=${r.code} got=${JSON.stringify(realTailEnvelope && realTailEnvelope.result && realTailEnvelope.result.lines)} expected=${JSON.stringify(expectedTail)}`);

    // 9. Local usage errors: bad target, missing id for status.
    r = await runCli(['inspect', 'bogus'], cliEnv);
    out('--- inspect bogus target ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('inspect with an unknown target is a LOCAL usage error, exit 2',
      r.code === 2 && /USAGE ERROR/.test(r.stderr), `exit=${r.code}`);

    r = await runCli(['inspect', 'status'], cliEnv);
    out('--- inspect status missing id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('inspect status with no id is a LOCAL usage error, exit 2',
      r.code === 2 && /USAGE ERROR/.test(r.stderr), `exit=${r.code}`);
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
