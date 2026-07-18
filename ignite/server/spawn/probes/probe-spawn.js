'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, capture, fire } = require('./lib');
const { buildBwrapArgv } = require('../bwrap');
const { buildSystemdRunArgs } = require('../carrier');

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

// p7-hotfix-stdin — a `prompt: stdin` profile's unit MUST carry `StandardInput=file:<promptfile>`
// so systemd connects the prompt file as the worker's stdin (bytes, then EOF at end-of-file).
// Pre-fix, no stdin branch existed: the unit's stdin defaulted to /dev/null and a headless
// `claude -p` died with "Input must be provided either through stdin or as a prompt argument".
function assertStdinProperty(label, args, stdinFile) {
  const want = `StandardInput=file:${stdinFile}`;
  const found = args.some((a, k) => a === '--property' && args[k + 1] === want);
  if (!found) {
    throw new Error(`${label}: unit args carry no '--property ${want}'`);
  }
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

    // --- stdin-carriage unit assertion (p7-hotfix-stdin): a stdinFile handed to the carrier
    // composer MUST emit `--property StandardInput=file:<promptfile>` on the unit ---
    const stdinArgsIn = {
      sessionId: 'stdin-compose-probe',
      argv: ['sleep', '1'],
      workdir: ctx.defaultWorkdir,
      logPath: path.join(ctx.dataRoot, 'stdin-compose-probe.log'),
      stdinFile: path.join(ctx.dataRoot, 'prompts', 'stdin-compose-probe.txt'),
      caps: {}, sandbox: {}, envFile: null, userManager: true,
    };
    const { args: withStdin } = buildSystemdRunArgs(stdinArgsIn);
    assertStdinProperty('unit-compose (stdinFile set)', withStdin, stdinArgsIn.stdinFile);
    lines.push('stdin-carriage assert PASS: unit args carry StandardInput=file:<promptfile>');

    // --- stdin-carriage mutation self-check: the PRE-FIX composer shape (no stdinFile → no
    // StandardInput property, stdin defaults to /dev/null) MUST be rejected ---
    const { args: withoutStdin } = buildSystemdRunArgs({ ...stdinArgsIn, stdinFile: null });
    let stdinCaught = false;
    try {
      assertStdinProperty('mutant (no StandardInput property)', withoutStdin, stdinArgsIn.stdinFile);
    } catch {
      stdinCaught = true;
    }
    if (!stdinCaught) throw new Error('stdin-carriage mutation self-check FAILED: assertion did not reject the property-less pre-fix unit args');
    lines.push('stdin-carriage mutation self-check PASS: assertion rejects the pre-fix property-less unit args');

    lines.push('action: fire row then spawn trivial worker via test-sleep profile (prompt: stdin) with a real prompt');
    const STDIN_PROMPT = 'p7-stdin-carriage probe prompt: bytes then EOF';
    const fired = fire(ctx, { profile: 'test-sleep', sessionMode: 'headless', workdir: ctx.defaultWorkdir });
    lines.push(`exec_id before spawn: ${fired.exec_id}, status: ${fired.status}`);

    const row = await ctx.mgr.spawn(fired.exec_id, 'test-sleep', 'headless', STDIN_PROMPT, null, 'probe');
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

    // stdin-carriage LIVE: the prompt file exists with the exact prompt bytes, and the RUNNING
    // transient unit's stdin is connected to it (`systemctl cat` shows the full directive; `show`
    // reports only the mode word `file`).
    const promptPath = path.join(ctx.dataRoot, 'prompts', `${row.session_id}.txt`);
    const promptOnDisk = fs.readFileSync(promptPath, 'utf8');
    if (promptOnDisk !== STDIN_PROMPT) {
      throw new Error(`stdin live: prompt file content ${JSON.stringify(promptOnDisk)} != ${JSON.stringify(STDIN_PROMPT)}`);
    }
    lines.push(`stdin live PASS: prompt file ${promptPath} carries the prompt verbatim`);
    const unitFile = execFileSync('systemctl', ['--user', 'cat', row.unit_name], { encoding: 'utf8' });
    if (!unitFile.includes(`StandardInput=file:${promptPath}`)) {
      throw new Error(`stdin live: transient unit file carries no StandardInput=file:${promptPath}`);
    }
    const showStdin = execFileSync('systemctl', ['--user', 'show', '--property=StandardInput', row.unit_name], { encoding: 'utf8' }).trim();
    if (showStdin !== 'StandardInput=file') {
      throw new Error(`stdin live: unit StandardInput mode '${showStdin}' != 'StandardInput=file'`);
    }
    lines.push(`stdin live PASS: running unit stdin connected to the prompt file (${showStdin})`);

    // Prove the log file exists.
    lines.push(`log file exists: ${require('node:fs').existsSync(row.log_path)}`);

    // Clean up.
    await ctx.mgr.kill(row.exec_id);
  } finally {
    teardown(ctx);
  }
});
