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
//   R5  `toolExecEnv()` PREPENDS `~/.local/bin` to a PATH that lacks it,   (the composer is guarded,
//       and DEDUPES one that already carries it                             not just the channel)
//   R6  every variable the fired unit carries other than PATH has the      (PATH-scope means VALUES,
//       SAME VALUE as the pre-fix unit                                      not only names)
//
// R2's baseline is not a guess at what systemd sets: it is the SAME unit composed with `setenv: {}`
// — the pre-fix shape — and actually run. One variable changed, both arms measured.
//
// ⚠ R5 AND R6 EXIST BECAUSE R1–R4 WERE MEASURED GREEN ON TWO REAL MUTANTS (§2 review of 01b8960,
// each run against a scratch copy of this tree):
//   · the prepend deleted from `toolExecEnv()` (`return { PATH: base }`) — R1 still passed, because
//     EVERY process that hosts this probe (an interactive shell, the `rbtv-probe-suite` unit) already
//     carries `~/.local/bin` in its OWN PATH, so forwarding it is indistinguishable from composing
//     it. R1 measures that a `--setenv` reached the child; it cannot measure what put the entry
//     there. R4 does not help: it controls the MANAGER's PATH, which this mutant does not touch.
//   · a second variable added at the ticker's call site OVERWRITING a name the child already had
//     (`setenv: { ...toolExecEnv(), SSH_AUTH_SOCK: '/tmp/attacker.sock' }`) — R2 compares NAME SETS,
//     so an overwrite introduces no name; R3 inspects an args array IT composes from
//     `toolExecEnv()` directly, never the args the ticker actually passed. Both stayed green while
//     the hostile value rode a real fired unit.
//
// Exit 0 PASS · 1 FAIL (lib/capture owns the exit).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { setup, teardown, capture, sleep } = require('./lib');
const carrier = require('../../../supervisor/spawn/carrier');

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
    // Parameterised by tag so R6 below can run the SAME composition twice and calibrate which names
    // are per-unit by construction, rather than hand-listing them (a hand-listed exclusion set is
    // free to grow until it covers the name that mattered).
    const runPreFixUnit = (tag) => {
      const logFile = path.join(ctx.dataRoot, 'logs', `${tag}.log`);
      fs.mkdirSync(path.dirname(logFile), { recursive: true });
      fs.writeFileSync(logFile, '');
      const { args } = carrier.buildSystemdRunArgs({
        sessionId: tag,
        argv: ['/usr/bin/env'],
        workdir: ctx.defaultWorkdir,
        logPath: logFile,
        caps: {},
        sandbox: {},
        envFile: null,
        setenv: {},          // ← the pre-fix composition, explicitly
        userManager: true,
      });
      execFileSync('systemd-run', ['--wait', ...args.filter((a) => a !== '--collect')],
        { stdio: 'ignore', timeout: 20000 });
      return { env: parseEnvDump(fs.readFileSync(logFile, 'utf8')), logFile };
    };
    const { env: baseEnv, logFile: baseLog } = runPreFixUnit('prefix-baseline');
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

    // ── R5 · the COMPOSER, driven with the one input R1 can never supply ──────────────────────
    // R1 can only see that a `--setenv PATH` reached the child; it cannot see whether `toolExecEnv`
    // PUT `~/.local/bin` there, because this probe's own host process already carries it. So drive
    // the composer with a PATH that does NOT — the daemon's condition, and the whole point of the
    // derivation the ruling names. Both halves of the composition are exercised: the PREPEND, and
    // the DEDUPE that keeps a PATH already carrying the entry from growing a repeat.
    const composeWith = (p) => {
      const saved = process.env.PATH;
      process.env.PATH = p;
      try { return carrier.toolExecEnv().PATH; } finally { process.env.PATH = saved; }
    };
    const prepended = composeWith('/usr/bin:/bin');
    if (prepended !== `${LOCAL_BIN}:/usr/bin:/bin`) {
      throw new Error(`R5 RED: toolExecEnv() did not PREPEND ${LOCAL_BIN} to a PATH that lacks it.\n`
        + `  given:    "/usr/bin:/bin"\n  composed: ${JSON.stringify(prepended)}\n`
        + `A fired tool on a box whose daemon PATH omits the entry would still be exit 127.`);
    }
    const deduped = composeWith(`/usr/bin:${LOCAL_BIN}:/bin`);
    if (deduped !== `${LOCAL_BIN}:/usr/bin:/bin`) {
      throw new Error(`R5 RED: toolExecEnv() did not DEDUPE an already-present ${LOCAL_BIN}.\n`
        + `  given:    "/usr/bin:${LOCAL_BIN}:/bin"\n  composed: ${JSON.stringify(deduped)}`);
    }
    lines.push(`R5 PASS: toolExecEnv() prepends ${LOCAL_BIN} to a PATH without it and dedupes one `
      + 'with it — the composition is measured, not inferred from the host process\'s own PATH');

    // ── R6 · PATH-scope is about VALUES, not only names ───────────────────────────────────────
    // R2's name-set comparison cannot see a second variable that OVERWRITES a name the child
    // already carries, and R3 inspects an args array it composes itself rather than the ticker's.
    // This arm compares the VALUES the two real units carried. The names that legitimately differ
    // between two units are calibrated by running the pre-fix composition a SECOND time: whatever
    // differs between two identical units is per-unit by construction, and nothing else is excused.
    const { env: baseEnv2 } = runPreFixUnit('prefix-baseline-2');
    const perUnit = Object.keys(baseEnv).filter((k) => baseEnv[k] !== baseEnv2[k]);
    const compared = Object.keys(baseEnv).filter((k) => k !== 'PATH' && !perUnit.includes(k));
    if (compared.length === 0) {
      throw new Error('R6 INOPERATIVE: every non-PATH name differed between two identical pre-fix '
        + 'units, so there is nothing this arm can hold constant — it would pass on any value.');
    }
    const changed = compared.filter((k) => firedEnv[k] !== baseEnv[k]);
    if (changed.length > 0) {
      throw new Error(`R6 RED (scope): the fired unit carries a DIFFERENT VALUE than the pre-fix `
        + `unit for ${JSON.stringify(changed)}. PATH-scope only means exactly one variable changes; `
        + `an overwrite of an inherited name introduces no new NAME and so passes R2.\n`
        + changed.map((k) => `  ${k}: fired=${JSON.stringify(firedEnv[k])} pre-fix=${JSON.stringify(baseEnv[k])}`).join('\n'));
    }
    lines.push(`R6 PASS: ${compared.length} inherited variable(s) carry byte-identical values in the `
      + `fired and pre-fix units; ${perUnit.length} per-unit name(s) calibrated out `
      + `(${JSON.stringify(perUnit)}) — only PATH differs`);
  } finally {
    teardown(ctx);
  }
});
