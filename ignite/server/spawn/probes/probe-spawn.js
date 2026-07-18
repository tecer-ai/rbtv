'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, capture, fire } = require('./lib');
const { buildBwrapArgv } = require('../bwrap');

// Replica of bwrap.js resolveBinary/scanPath (the resolver is not exported): the absolute path
// execvp would use for a bare PATH name. Lets the assertion state the EXPECTED head independently.
function expectResolved(name) {
  if (path.isAbsolute(name)) return name;
  for (const dir of (process.env.PATH || '').split(':')) {
    if (!dir) continue;
    const cand = path.join(dir, name);
    try { fs.accessSync(cand, fs.constants.X_OK); return cand; } catch {}
  }
  return null;
}

// D109 — the token immediately after `--` MUST be the RESOLVED absolute binary path, not the bare
// argv[0]: inside the bwrap namespace execvp searches the sandbox PATH (which need not contain
// argv[0]'s dir), so a bare head dies `execvp: No such file or directory`. Trailing args verbatim.
function assertExecHead(label, composed, argv, expectedHead) {
  const i = composed.indexOf('--');
  if (i === -1) throw new Error(`${label}: no '--' separator in composed bwrap argv`);
  const head = composed[i + 1];
  if (head !== expectedHead) {
    throw new Error(`${label}: exec head '${head}' != resolved absolute path '${expectedHead}'`);
  }
  const tail = composed.slice(i + 2);
  const want = argv.slice(1);
  if (tail.length !== want.length || tail.some((t, k) => t !== want[k])) {
    throw new Error(`${label}: trailing args ${JSON.stringify(tail)} != ${JSON.stringify(want)}`);
  }
}

capture('probe-spawn', async (lines) => {
  const ctx = setup();
  try {
    // --- D109 unit assertion: buildBwrapArgv execs the RESOLVED binary path as argv[0] ---
    const probeArgv = ['sleep', '3600'];
    const expectedHead = expectResolved('sleep');
    lines.push(`D109 assert: argv[0]='${probeArgv[0]}' resolves to '${expectedHead}'`);
    if (!expectedHead || expectedHead === probeArgv[0]) {
      throw new Error(`D109: 'sleep' did not resolve to an absolute PATH entry (got ${expectedHead})`);
    }
    const composed = buildBwrapArgv({ argv: probeArgv, workdir: ctx.defaultWorkdir, harness: null });
    assertExecHead('live buildBwrapArgv', composed, probeArgv, expectedHead);
    lines.push("D109 assert PASS: post-'--' head is the resolved absolute path; tail preserved in order");

    // --- D109 mutation self-check leg: the assertion MUST reject the pre-fix (bare argv[0]) head ---
    const dashIdx = composed.indexOf('--');
    const mutant = [...composed.slice(0, dashIdx + 1), ...probeArgv]; // simulate buggy out.push(...argv)
    let caught = false;
    try {
      assertExecHead('mutant (bare argv[0])', mutant, probeArgv, expectedHead);
    } catch {
      caught = true;
    }
    if (!caught) throw new Error('D109 mutation self-check FAILED: assertion did not reject the bare-argv[0] head');
    lines.push('D109 mutation self-check PASS: assertion rejects the pre-fix bare-argv[0] head');

    lines.push('action: fire row then spawn trivial worker via test-sleep profile');
    const fired = fire(ctx, { profile: 'test-sleep', sessionMode: 'headless', workdir: ctx.defaultWorkdir });
    lines.push(`exec_id before spawn: ${fired.exec_id}, status: ${fired.status}`);

    const row = await ctx.mgr.spawn(fired.exec_id, 'test-sleep', 'headless', null, null, 'probe');
    lines.push(`exec_id after spawn: ${row.exec_id}`);
    lines.push(`session_id: ${row.session_id}`);
    lines.push(`pid: ${row.pid}`);
    lines.push(`carrier: ${row.carrier}`);
    lines.push(`unit_name: ${row.unit_name}`);
    lines.push(`status: ${row.status}`);
    lines.push(`log_path: ${row.log_path}`);
    lines.push(`workdir: ${row.workdir}`);

    // Prove the unit exists and carries the profile's caps.
    const { execFileSync } = require('node:child_process');
    const show = execFileSync('systemctl', ['--user', 'show', '--property=MemoryMax,MemoryMaxUSec,CPUQuota,RuntimeMaxSec,RuntimeMaxUSec,TasksMax', row.unit_name], { encoding: 'utf8' });
    lines.push('systemctl --user show caps:');
    for (const line of show.split('\n')) {
      if (line.trim()) lines.push('  ' + line.trim());
    }

    // Prove the worker is actually running.
    const active = execFileSync('systemctl', ['--user', 'is-active', row.unit_name], { encoding: 'utf8' }).trim();
    lines.push(`systemctl --user is-active: ${active}`);

    // Prove the log file exists.
    lines.push(`log file exists: ${require('node:fs').existsSync(row.log_path)}`);

    // Clean up.
    await ctx.mgr.kill(row.exec_id);
  } finally {
    teardown(ctx);
  }
});
