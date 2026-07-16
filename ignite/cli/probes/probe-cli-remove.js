'use strict';

// probe-cli-remove — proves `ignite remove-job <queue-id>` end-to-end through
// the REAL CLI binary against a REAL (throwaway) daemon: add then remove then
// confirm gone (test plan #5); removing a PERIODIC row cancels the whole
// recurring schedule and the CLI says so loudly (D68); an unknown id is a
// typed NOT_FOUND; local usage errors.
//
// NEVER touches the live daemon: throwaway workspace, throwaway senders file,
// ephemeral port; only the child this probe spawns is ever signaled.

const fs = require('node:fs');
const path = require('node:path');
const {
  freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, seedCatalogue, runCli,
} = require('./lib/fixtures');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-remove.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('p4-2-cli-remove');
  const port = await freePort();
  const env = baseEnv(ws, port);
  seedCatalogue(ws);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  const cliEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };

  try {
    // 1. add -> remove -> inspect queue confirms it is gone (test plan #5).
    let r = await runCli([
      'add-job', '--fn', 'probe-cli-sleep', '--profile', 'test-sleep',
      '--trigger', 'scheduled', '--at', '2099-01-01T00:00:00Z',
    ], cliEnv);
    check('setup: add-job succeeds', r.code === 0, `exit=${r.code} ${r.stderr}`);
    const queueId = (r.stdout.match(/queue id (\d+)/) || [])[1];
    out(`queued queue_id=${queueId}`);

    r = await runCli(['remove-job', queueId], cliEnv);
    out('--- remove-job (scheduled) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('remove-job on a scheduled (non-repeating) row exits 0 and does NOT claim the whole schedule was cancelled',
      r.code === 0 && /^removed: trigger=scheduled/.test(r.stdout) && !/WHOLE recurring schedule/.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    r = await runCli(['--json', 'inspect', 'queue'], cliEnv);
    let envelope = null;
    try { envelope = JSON.parse(r.stdout.trim()); } catch {}
    const stillThere = envelope && envelope.ok && envelope.result.rows.some((row) => String(row.queue_id) === queueId);
    check('the removed row is actually gone from inspect queue', r.code === 0 && stillThere === false,
      `rows=${JSON.stringify(envelope && envelope.result && envelope.result.rows)}`);

    // 2. Removing a PERIODIC row: the CLI must say the WHOLE schedule was
    // cancelled (D68 widened result fields), not just "removed".
    r = await runCli([
      'add-job', '--fn', 'probe-cli-sleep', '--profile', 'test-sleep',
      '--trigger', 'periodic', '--every', '3600',
    ], cliEnv);
    check('setup: add-job (periodic) succeeds', r.code === 0, `exit=${r.code} ${r.stderr}`);
    const periodicId = (r.stdout.match(/queue id (\d+)/) || [])[1];

    r = await runCli(['remove-job', periodicId], cliEnv);
    out('--- remove-job (periodic) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('remove-job on a periodic row exits 0 and LOUDLY says the whole schedule was cancelled (D68)',
      r.code === 0 && /interval_seconds=3600/.test(r.stdout) && /WHOLE recurring schedule/.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 3. Removing an id that does not exist -> typed NOT_FOUND.
    r = await runCli(['remove-job', '999999'], cliEnv);
    out('--- remove-job unknown id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('remove-job on an unknown queue id is a typed NOT_FOUND (exit 1, catch-all per the exit-code table)',
      r.code === 1 && /NOT_FOUND/.test(r.stderr), `exit=${r.code}`);

    // 4. Local usage errors: no id, non-integer id.
    r = await runCli(['remove-job'], cliEnv);
    out('--- remove-job missing id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('remove-job with no id is a LOCAL usage error, exit 2', r.code === 2 && /USAGE ERROR/.test(r.stderr), `exit=${r.code}`);

    r = await runCli(['remove-job', 'not-a-number'], cliEnv);
    out('--- remove-job non-integer id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('remove-job with a non-integer id is a LOCAL usage error, exit 2', r.code === 2 && /USAGE ERROR/.test(r.stderr), `exit=${r.code}`);
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
