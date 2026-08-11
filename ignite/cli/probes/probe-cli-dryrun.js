'use strict';

// probe-cli-dryrun — proves `ignite add-job --dry-run` end-to-end through the
// REAL CLI binary against a REAL (throwaway) daemon: a valid dry-run exits 0
// with a verdict and enqueues NOTHING (proven directly against `inspect
// queue`, not by inference); an invalid dry-run (unknown function) still
// runs full gateway+server re-validation and is refused with exit 4, also
// enqueuing nothing; and the --json envelope carries the stable
// `{ ok: true, result: { dry_run: true, valid: true } }` shape.
//
// See gateway-cli-spec.md § CLI Surface (--dry-run), behavior row 2, and
// Test Plan row 6 ("Dry-run enqueues nothing").
//
// NEVER touches the live daemon: throwaway workspace, throwaway senders file,
// ephemeral port; only the child this probe spawns is ever signaled.

const fs = require('node:fs');
const path = require('node:path');
const {
  freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, seedCatalogue, runCli,
} = require('./lib/fixtures');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-dryrun.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('p4-2-cli-dryrun');
  const port = await freePort();
  const env = baseEnv(ws, port);

  seedCatalogue(ws);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  try {
    const cliEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };

    async function queueRows() {
      const r = await runCli(['--json', 'inspect', 'queue'], cliEnv);
      let envelope = null;
      try { envelope = JSON.parse(r.stdout.trim()); } catch {}
      return (envelope && envelope.ok && envelope.result && envelope.result.rows) || null;
    }

    // 0. Baseline: queue starts empty.
    let rows = await queueRows();
    check('setup: queue starts empty', Array.isArray(rows) && rows.length === 0, `rows=${JSON.stringify(rows)}`);

    // 1. Valid dry-run exits 0 and prints a verdict.
    let r = await runCli([
      'add-job', '--fn', 'probe-cli-sleep', '--profile', 'test-sleep',
      '--trigger', 'scheduled', '--at', '2099-01-01T00:00:00Z', '--dry-run',
    ], cliEnv);
    out('--- add-job --dry-run (valid) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim(), 'STDERR=' + r.stderr.trim());
    check('valid dry-run exits 0 with a verdict', r.code === 0 && /dry-run/i.test(r.stdout) && /valid/i.test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 2. Dry-run enqueues NOTHING — proven directly against `inspect queue`.
    rows = await queueRows();
    out('--- inspect queue after valid dry-run ---', `rows=${JSON.stringify(rows)}`);
    check('a valid dry-run enqueues nothing (queue still empty)', Array.isArray(rows) && rows.length === 0,
      `rows=${JSON.stringify(rows)}`);

    // 2b. TASK 7.736 DOOR 1's RENDERING. The launch-agent dry-run above carries NO `edge_fastpath`
    // field (the server core answers arming for `start-workflow` rows and nothing else), so the CLI
    // must print NOTHING about arming here — a renderer that fired on an absent field would stamp a
    // verdict on every dry-run in the system, which is worse than the silence 7.736 removes.
    check('7.736: a launch-agent dry-run prints NO arming line (the field is absent, and absent '
      + 'prints nothing)', !/EDGE-FASTPATH|edge fast path/i.test(r.stdout),
      `stdout=${r.stdout.trim()}`);

    // The three branches of the printer itself, driven directly. `armed` is a TRISTATE and the
    // third value is the one that matters: `null` means "could not look", and it must render as
    // UNKNOWN — never as either verdict. A booted daemon proves nothing extra about three ifs.
    const { renderEdgeFastpath } = require('../commands/add-job.js');
    const printed = [];
    const realLog = console.log;
    console.log = (...a) => printed.push(a.join(' '));
    try {
      renderEdgeFastpath(undefined);
      const absent = printed.length;
      renderEdgeFastpath({ armed: true, scope: 'ARMED by /g/coordination/edge-fastpath.json' });
      renderEdgeFastpath({ armed: false, scope: 'NOT ARMED: no /g/coordination/edge-fastpath.json' });
      renderEdgeFastpath({ armed: null, scope: 'arm state UNREADABLE: python3 not found' });
      console.log = realLog;
      const text = printed.join('\n');
      check('7.736: renderEdgeFastpath prints nothing for an ABSENT field, ARMED for true, '
        + 'EDGE-FASTPATH-NOT-ARMED (with its consequence) for false, and EDGE-FASTPATH-UNKNOWN for '
        + 'null — the tristate never collapses',
        absent === 0
        && /edge fast path: ARMED/.test(text)
        && (text.match(/EDGE-FASTPATH-NOT-ARMED/g) || []).length === 2
        && /CONSEQUENCE/.test(text)
        && /EDGE-FASTPATH-UNKNOWN/.test(text)
        && !/EDGE-FASTPATH-NOT-ARMED[^\n]*UNREADABLE/.test(text),
        `absent-lines=${absent} printed=${JSON.stringify(printed)}`);
    } finally {
      console.log = realLog;
    }

    // 3. Invalid dry-run (unknown function): gateway shape-check passes, server
    // re-validation refuses -> exit 4, VALIDATION_FAILED, still nothing enqueued.
    r = await runCli([
      'add-job', '--fn', 'no-such-job',
      '--trigger', 'scheduled', '--at', '2099-01-01T00:00:00Z', '--dry-run',
    ], cliEnv);
    out('--- add-job --dry-run (invalid: unknown function) ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('invalid dry-run (unknown function) is refused with exit 4 and VALIDATION_FAILED',
      r.code === 4 && /VALIDATION_FAILED/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);

    rows = await queueRows();
    out('--- inspect queue after invalid dry-run ---', `rows=${JSON.stringify(rows)}`);
    check('an invalid dry-run also enqueues nothing (queue still empty)', Array.isArray(rows) && rows.length === 0,
      `rows=${JSON.stringify(rows)}`);

    // 4. --json dry-run: stable { ok: true, result: { dry_run: true, valid: true } } envelope.
    r = await runCli([
      '--json', 'add-job', '--fn', 'probe-cli-sleep', '--profile', 'test-sleep',
      '--trigger', 'scheduled', '--at', '2099-01-01T00:00:00Z', '--dry-run',
    ], cliEnv);
    out('--- add-job --json --dry-run ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    let envelope = null;
    try { envelope = JSON.parse(r.stdout.trim()); } catch {}
    check('add-job --json --dry-run exits 0 with a stable {ok,result:{dry_run,valid}} envelope',
      r.code === 0 && envelope && envelope.ok === true && envelope.result &&
      envelope.result.dry_run === true && envelope.result.valid === true,
      `exit=${r.code} parsed=${JSON.stringify(envelope)}`);

    rows = await queueRows();
    out('--- inspect queue after --json valid dry-run ---', `rows=${JSON.stringify(rows)}`);
    check('a --json valid dry-run also enqueues nothing (queue still empty)', Array.isArray(rows) && rows.length === 0,
      `rows=${JSON.stringify(rows)}`);
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
