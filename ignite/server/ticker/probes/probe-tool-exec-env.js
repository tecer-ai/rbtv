'use strict';

// ── F1 · the environment a DAEMON-FIRED TOOL actually runs in ────────────────────────────────
//
// THE DEFECT THIS EXISTS FOR (C5E review, finding F1, 2026-08-08). `runToolLikeExec` handed the
// carrier `envFile: null` and `buildSystemdRunArgs` emitted no env of any kind, so a fired tool ran
// with the systemd `--user` MANAGER's environment — whose PATH does NOT carry `~/.local/bin`. Every
// ruled bare tool name therefore resolved for every interactive caller and for NOBODY under the
// daemon: `scaffold-seats` exited 127, `create()` refused, and the goal it had already scaffolded
// was left orphaned with no run package. Owner ruling `d-owner-f1-carrier-env-0808` fixed it at the
// CARRIER rather than at the call site, so that every future fire-tool entry is fixed at once.
//
// WHY A PROBE HERE AND NOT ONLY AT THE CALL SITE. The reviewer's own diagnosis was that
// `probe-planning-entry.py` could not see F1 BY CONSTRUCTION: its drain runs `subprocess.run`, which
// inherits the PROBE's environment, and the probe and the daemon differ on exactly the one variable
// that decides the outcome. So the guard has to live where the environment is composed and be
// driven by a REAL fired unit — which is what this file does. Nothing here is hand-typed: the unit
// that runs is composed by the real ticker through the real carrier.
//
// THE FOUR ARMS, and the control is the point rather than the success:
//
//   R1  a real fire-tool exec's PATH carries `~/.local/bin`, FIRST         (the fix works)
//   R2  the same exec's env introduces NO variable name the pre-fix        (the fix leaks nothing)
//       composition did not already have, and PATH is exactly the
//       one value `toolExecEnv()` composes
//   R3  a tool exec's unit carries NO `EnvironmentFile=` and exactly       (the credential channel
//       ONE `--setenv`, named PATH                                          is not co-opted)
//   R4  R1's check, run against the PRE-FIX composition, goes RED          (the check discriminates)
//
// R2's baseline is not a guess at what systemd sets: it is the SAME unit composed with `setenv: {}`
// — the pre-fix shape — and actually run. One variable changed, both arms measured.
//
// Exit 0 PASS · 1 FAIL (lib/capture owns the exit).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { setup, teardown, capture, sleep } = require('./lib');
const carrier = require('../../spawn/carrier');

const LOCAL_BIN = path.join(os.homedir(), '.local', 'bin');

// Read an `/usr/bin/env` dump back as a NAME->VALUE map. Values may contain `=`; names may not.
function parseEnvDump(text) {
  const map = {};
  for (const line of text.split('\n')) {
    const i = line.indexOf('=');
    if (i > 0) map[line.slice(0, i)] = line.slice(i + 1);
  }
  return map;
}

// Wait for a detached unit's append-log to stop being empty. The carriers resolve when the child is
// LAUNCHED, not when it finishes (carrier.js), so there is no handle to await for a tool exec.
async function waitForLog(logPath, budgetMs = 15000) {
  const deadline = Date.now() + budgetMs;
  while (Date.now() < deadline) {
    try {
      const t = fs.readFileSync(logPath, 'utf8');
      if (t.includes('PATH=')) return t;
    } catch {}
    await sleep(200);
  }
  return null;
}

capture('probe-tool-exec-env', async (lines) => {
  if (!carrier.systemdAvailable(true)) {
    throw new Error('INOPERATIVE: no systemd --user manager — the carrier this probe measures is unreachable');
  }
  lines.push(`local-bin (derived from HOME, never typed): ${LOCAL_BIN}`);
  lines.push(`manager PATH: ${execFileSync('systemctl', ['--user', 'show-environment'], { encoding: 'utf8' })
    .split('\n').find((l) => l.startsWith('PATH=')) || '(none)'}`);

  const ctx = setup();
  try {
    // A REAL fire-tool row through the REAL ticker. `/usr/bin/env` is the tool, so the unit's own
    // environment lands in the exec's log — the daemon's answer, not the probe's.
    ctx.store.config.tools = { 'env-dump-probe': { argv: ['/usr/bin/env'] } };
    ctx.store.registerJob({
      jobId: 'env-dump-job',
      actionType: 'fire-tool',
      function: 'fire-tool',
      argsSchema: JSON.stringify({ required: { tool: 'string' }, optional: { workdir: 'string' } }),
    });
    ctx.store.enqueue({
      jobId: 'env-dump-job',
      args: JSON.stringify({ tool: 'env-dump-probe', workdir: ctx.defaultWorkdir }),
      sessionMode: 'headless',
      triggerKind: 'scheduled',
      runAt: new Date(Date.now() - 1000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
      enqueuedBy: 'probe',
    });

    const r = await ctx.ticker.tick(new Date());
    const fired = r.actions.find((a) => a.action === 'fire-tool');
    if (!fired) throw new Error(`no fire-tool action in tick: ${JSON.stringify(r.actions)}`);

    const row = ctx.store.dump().jobs_log.find((j) => j.exec_id === fired.execId);
    if (!row || !row.log_path) throw new Error('fired exec recorded no log_path');
    const dump = await waitForLog(row.log_path);
    if (!dump) throw new Error(`the fired tool wrote no env dump to ${row.log_path} within budget`);
    const firedEnv = parseEnvDump(dump);
    lines.push(`fired exec ${fired.execId} · carrier=${row.carrier} · PATH=${firedEnv.PATH}`);

    // ── R1 · the fix: the fired tool can NAME what lives in ~/.local/bin ──────────────────────
    const firstEntry = (firedEnv.PATH || '').split(':')[0];
    if (firstEntry !== LOCAL_BIN) {
      throw new Error(`R1 RED: a daemon-fired tool's PATH does not begin with ${LOCAL_BIN} — `
        + `first entry is ${JSON.stringify(firstEntry)}. Every ruled bare tool name is exit 127 here.`);
    }
    lines.push(`R1 PASS: the fired tool's PATH begins with ${LOCAL_BIN}`);

    // ── R2 · the control: the SAME unit composed the PRE-FIX way, actually run ────────────────
    // The baseline is not an assumption about what systemd sets — it is this exact unit with the
    // one added variable removed. Anything present in the fired env and absent here is a leak we
    // introduced.
    const baseLog = path.join(ctx.dataRoot, 'logs', 'prefix-baseline.log');
    fs.mkdirSync(path.dirname(baseLog), { recursive: true });
    fs.writeFileSync(baseLog, '');
    const { args: baseArgs } = carrier.buildSystemdRunArgs({
      sessionId: 'prefix-baseline',
      argv: ['/usr/bin/env'],
      workdir: ctx.defaultWorkdir,
      logPath: baseLog,
      caps: {},
      sandbox: {},
      envFile: null,
      setenv: {},          // ← the pre-fix composition, explicitly
      userManager: true,
    });
    execFileSync('systemd-run', ['--wait', ...baseArgs.filter((a) => a !== '--collect')],
      { stdio: 'ignore', timeout: 20000 });
    const baseEnv = parseEnvDump(fs.readFileSync(baseLog, 'utf8'));
    lines.push(`pre-fix baseline PATH: ${baseEnv.PATH}`);

    const introduced = Object.keys(firedEnv).filter((k) => !Object.hasOwn(baseEnv, k));
    if (introduced.length > 0) {
      throw new Error(`R2 RED (leak): the fix introduced env variable(s) the pre-fix unit did not `
        + `carry: ${JSON.stringify(introduced)}. PATH-scope only is the design constraint.`);
    }
    const expected = carrier.toolExecEnv ? carrier.toolExecEnv().PATH : null;
    if (!expected) throw new Error('R2 RED: carrier exports no toolExecEnv() — nothing composes the tool-exec environment');
    if (firedEnv.PATH !== expected) {
      throw new Error(`R2 RED: the fired PATH is not the composed value.\n  fired:    ${firedEnv.PATH}\n  composed: ${expected}`);
    }
    lines.push(`R2 PASS: no variable introduced beyond PATH (${Object.keys(firedEnv).length} names, `
      + `identical name-set to the pre-fix unit); PATH is exactly toolExecEnv()'s value`);

    // ── R3 · the credential channel is not co-opted ───────────────────────────────────────────
    const { args: fixArgs } = carrier.buildSystemdRunArgs({
      sessionId: 'compose-probe',
      argv: ['/usr/bin/env'],
      workdir: ctx.defaultWorkdir,
      logPath: baseLog,
      caps: {},
      sandbox: {},
      envFile: null,
      setenv: carrier.toolExecEnv(),
      userManager: true,
    });
    const envFileProps = fixArgs.filter((a) => typeof a === 'string' && a.startsWith('EnvironmentFile='));
    const setenvNames = fixArgs.filter((a, i) => fixArgs[i - 1] === '--setenv').map((a) => a.split('=')[0]);
    if (envFileProps.length !== 0) throw new Error(`R3 RED: a tool exec's unit carries ${JSON.stringify(envFileProps)}`);
    if (setenvNames.length !== 1 || setenvNames[0] !== 'PATH') {
      throw new Error(`R3 RED: expected exactly one --setenv named PATH, got ${JSON.stringify(setenvNames)}`);
    }
    lines.push('R3 PASS: no EnvironmentFile= on a tool exec; exactly one --setenv, named PATH');

    // ── R4 · discrimination: R1's check MUST reject the pre-fix composition ───────────────────
    const baseFirst = (baseEnv.PATH || '').split(':')[0];
    if (baseFirst === LOCAL_BIN) {
      throw new Error('R4 INOPERATIVE: the pre-fix composition ALREADY begins with local-bin, so R1 '
        + 'cannot discriminate on this box — the manager PATH must be carrying it from elsewhere');
    }
    lines.push(`R4 PASS: the pre-fix composition's PATH begins with ${JSON.stringify(baseFirst)}, not `
      + `${LOCAL_BIN} — R1 goes RED on it, so R1 is measuring the fix and not the box`);
  } finally {
    teardown(ctx);
  }
});
