#!/usr/bin/env node
'use strict';

// probe-sub-agent-dispatch — task 7.43's criteria, exercised against the REAL tree.
//
// ⚠ WHAT THIS PROBE IS AND IS NOT (`bars.md` 10). It runs against the committed
// `ignite/config/spawn-profiles.yaml`, the committed `ignite/exposure.csv`, the real
// `injection-ladder`, the real `launch-profiles`, the real workspace `.rbtv/sessions/` and — for
// the two positive checks — a REAL claude harness process. It supplies NO paths of its own to the
// dispatch path. The one thing it CANNOT claim independence from is the exposure manifest: task
// 7.43's seat authored that file, so a green on the POSITIVE half is a green against a catalog its
// own author wrote. Stated here rather than left for a reader to notice.
//
// ⚠ EVERY CHECK IS PAIRED WHERE PAIRING IS POSSIBLE (`bars.md` 11 — can this check fail?). A
// refusal check is worthless unless the same call succeeds when the bound is not violated, and a
// wall check is worthless unless the same instrument finds the thing on the unwalled side. Each
// CONTROL below is the second half of that pair and is marked `control:`.
//
// ⚠⚠ THE PAID HALF IS OPT-IN — `--real` (or `SUBAGENT_PROBE_REAL_RUN=1`). LEADER-RULED, G-213.
// Two REAL claude invocations (~60-90s, real money) and a SIGKILLed process tree do not belong in
// every `deploy/probe-suite.js` run: measured next door, the engineer's grader fix took a selftest
// from 60.26s to 4.96s and that alone made a 543-site sweep affordable. AN AVOIDED SUITE PROTECTS
// NOTHING — the same failure mode as a permanently-red probe (G-194). 7.43's criterion "after a
// real run rather than by a claim" is an ACCEPTANCE artifact, satisfied ONCE by the run recorded on
// its row; it is not a standing requirement to re-purchase the proof hourly.
//
// ⚠ THE RISK THE LEADER NAMED AND ACCEPTED: an opt-in check tends never to run again. The
// mitigation is a TRIGGER, not a mechanism, and it is not dressed up as one — RUN `--real` BEFORE
// ACCEPTING ANY CHANGE TO THIS CAPABILITY'S OWN FILES.
//
// ⚠ CHECK NUMBERS ARE STABLE ACROSS THE SPLIT, deliberately: the free half runs 1-11 then 21-23,
// the paid half 12-20 and 24-27. Output order is therefore not numeric, so that every citation in
// `report-743.md` still resolves to the check it named.
//
// ⚠ HERMETIC (`G-182`): every child this probe spawns has TMUX / TMUX_PANE / COORD_AGENT stripped
// from its environment, asserted by check 0 before anything else runs. This probe kills processes;
// it kills only pids it started, named explicitly, never a pane and never a pattern match.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync, execFileSync } = require('node:child_process');

const HERE = path.resolve(__dirname, '..');
const TOOL = path.join(HERE, 'tool', 'rbtv-subagent');
const lane = require(HERE);
const dispatchMod = require(path.join(HERE, 'dispatch.js'));
const fanout = require(path.join(HERE, 'fanout.js'));
const envMod = require(path.join(HERE, 'env.js'));

const SENTINEL = 'RBTV_PROBE_SENTINEL_LEAK_CANARY';
const SENTINEL_VALUE = 'not-a-secret-just-a-canary';

// The opt-in gate. Default OFF: the free half proves every REFUSAL and every wall that can be
// proved without buying a harness turn.
const REAL = process.argv.includes('--real') || process.env.SUBAGENT_PROBE_REAL_RUN === '1';
const FREE_CHECKS = 16;   // 0a, 0b, 1-11, 21, 22, 23 — hand-counted, asserted at the end
const REAL_CHECKS = 29;   // the above plus 12-20 and 24-27

let pass = 0;
let fail = 0;
const results = [];
function check(name, ok, detail) {
  results.push({ name, ok: Boolean(ok), detail: detail === undefined ? '' : String(detail) });
  if (ok) pass += 1; else fail += 1;
  process.stdout.write(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}\n`);
}

// The child environment every helper spawn uses: the caller's, minus the live-environment handles.
function hermeticEnv(extra = {}) {
  const e = { ...process.env, ...extra };
  delete e.TMUX;
  delete e.TMUX_PANE;
  delete e.COORD_AGENT;
  return e;
}

function runTool(args, { env = {}, timeoutMs = 60000 } = {}) {
  const r = spawnSync(process.execPath, [TOOL, ...args], {
    encoding: 'utf8', timeout: timeoutMs, env: hermeticEnv(env), cwd: os.homedir(),
  });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { /* non-json output */ }
  return { status: r.status, stdout: r.stdout, stderr: r.stderr, json };
}

function sessionsRoot() {
  const ws = dispatchMod.resolveWorkspaceRoot(os.homedir());
  return path.join(ws, '.rbtv', 'sessions');
}
function countSubagentDirs() {
  try { return fs.readdirSync(sessionsRoot()).filter((n) => n.startsWith('subagent-')).length; }
  catch { return 0; }
}
function pgidMembers(pgid) {
  try {
    return execFileSync('ps', ['-eo', 'pid=,pgid='], { encoding: 'utf8' })
      .split('\n').map((l) => l.trim().split(/\s+/))
      .filter((p) => p.length === 2 && Number(p[1]) === pgid)
      .map((p) => Number(p[0]));
  } catch { return []; }
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  // ── 0 · hermeticity, asserted before anything spawns ───────────────────────────────────────
  {
    const r = spawnSync(process.execPath, ['-e', 'process.stdout.write(JSON.stringify({t:process.env.TMUX||null,p:process.env.TMUX_PANE||null,c:process.env.COORD_AGENT||null}))'], { encoding: 'utf8', env: hermeticEnv() });
    const seen = JSON.parse(r.stdout);
    check('0a  helper children inherit no TMUX / TMUX_PANE / COORD_AGENT',
      seen.t === null && seen.p === null && seen.c === null, JSON.stringify(seen));
    // control: the SAME assertion against an un-stripped environment must find whatever this box
    // actually sets, so a green above means "stripped", not "the box has none anyway".
    const r2 = spawnSync(process.execPath, ['-e', 'process.stdout.write(String(Object.keys(process.env).filter(k=>/^(TMUX|COORD_AGENT)/.test(k)).length))'], { encoding: 'utf8' });
    check('0b  control: the un-stripped environment DOES carry live-environment handles here',
      Number(r2.stdout) > 0, `${r2.stdout} such names in the probe's own env`);
  }

  // ═══ NEGATIVE HALF — provable with no successful dispatch at all ════════════════════════════
  const before = countSubagentDirs();

  {
    const r = runTool(['dispatch', '--target', 'not-a-real-target', '--profile', 'claude-sonnet-tools', '--task', 'x', '--json']);
    check('1  non-cataloged target fails closed (boundary 1)',
      r.status === 3 && r.json && r.json.code === 'E_TARGET_NOT_CATALOGED', `exit ${r.status} ${r.json && r.json.code}`);
  }
  {
    const r = runTool(['dispatch', '--target', 'ticker-settings', '--profile', 'no-such-profile', '--task', 'x', '--json']);
    check('2  non-existent profile fails closed (boundary 2)',
      r.status === 3 && r.json && r.json.code === 'E_UNKNOWN_PROFILE', `exit ${r.status} ${r.json && r.json.code}`);
  }
  {
    const r = runTool(['dispatch', '--target', 'ticker-settings', '--profile', 'test-sleep', '--task', 'x', '--json']);
    check('3  a profile with no harness is not a sub-agent target',
      r.status === 3 && r.json && r.json.code === 'E_NO_HARNESS', `exit ${r.status} ${r.json && r.json.code}`);
  }
  {
    const r = runTool(['dispatch', '--target', 'ticker-settings', '--profile', 'claude-sonnet-tools', '--task', 'x', '--json'],
      { env: { [envMod.DEPTH_VAR]: '1' } });
    check('4  a sub-agent may not dispatch a sub-agent (boundary 9)',
      r.status === 3 && r.json && r.json.code === 'E_NESTING_REFUSED', `exit ${r.status} ${r.json && r.json.code}`);
  }
  check('5  NOTHING was spawned by any of the four refusals above',
    countSubagentDirs() === before, `session dirs ${before} -> ${countSubagentDirs()}`);

  // ── the WALK, both directions, same situation parameter ────────────────────────────────────
  // This is the one place where the rung is not written anywhere in this capability: the SAME
  // `--resumable` situation resolves to no rung at all on opencode (its headless rung is one-shot,
  // G-13) and to `headless` on claude. If the dispatch path ever handed the ladder a rung, both
  // sides of this pair would give the same answer.
  {
    const r = runTool(['dispatch', '--target', 'ticker-settings', '--profile', 'opencode-sakana', '--task', 'x', '--resumable', '--json']);
    const skipped = r.json && r.json.details && r.json.details.skipped;
    check('6  the ladder WALKS: opencode + needResumable resolves to NO rung (boundary refuses)',
      r.status === 3 && r.json && r.json.code === 'E_NO_RUNG_AVAILABLE'
      && Array.isArray(skipped) && skipped.length === 3,
      r.json && r.json.code);
  }

  // ── boundary 10, both directions ───────────────────────────────────────────────────────────
  {
    const ws = dispatchMod.resolveWorkspaceRoot(os.homedir());
    const runtimeRoot = path.join(ws, '.rbtv', 'runtime');
    const dir = fanout.registryDir(runtimeRoot, fanout.dispatcherId());
    fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
    // Occupy the cap with REAL live processes, so liveness is a fact rather than a fixture field.
    const holders = [];
    for (let i = 0; i < lane.FANOUT_MAX; i++) {
      const h = spawn('sleep', ['30'], { detached: true, stdio: 'ignore', env: hermeticEnv() });
      h.unref();
      holders.push(h.pid);
      fs.writeFileSync(path.join(dir, `${h.pid}.json`), JSON.stringify({ supervisorPid: h.pid, probe: true }), { mode: 0o600 });
    }
    const atCap = runTool(['dispatch', '--target', 'ticker-settings', '--profile', 'claude-sonnet-tools', '--task', 'x', '--json']);
    check(`7  at the cap (${lane.FANOUT_MAX} live) a further dispatch fails closed (boundary 10)`,
      atCap.status === 3 && atCap.json && atCap.json.code === 'E_FANOUT_EXCEEDED', atCap.json && atCap.json.code);

    // control: free ONE slot and the very same reservation succeeds. Without this the check above
    // would also pass if reserve() simply always threw.
    fs.rmSync(path.join(dir, `${holders[0]}.json`), { force: true });
    try { process.kill(holders[0], 'SIGKILL'); } catch { /* already gone */ }
    let reserved = null;
    try {
      reserved = fanout.reserve({ runtimeRoot, meta: { probe: true } });
      check('8  control: with one slot free the same reservation SUCCEEDS', true, `${lane.FANOUT_MAX - 1} live`);
      reserved.release();
    } catch (err) {
      check('8  control: with one slot free the same reservation SUCCEEDS', false, err.code || err.message);
    }
    for (const pid of holders.slice(1)) {
      try { process.kill(pid, 'SIGKILL'); } catch { /* already gone */ }
      fs.rmSync(path.join(dir, `${pid}.json`), { force: true });
    }
  }

  // ── boundary 6, on a path the resolver would produce ───────────────────────────────────────
  {
    let threw = null;
    try { dispatchMod.assertNotSeatIdentity('/x/.rbtv/goals/g/runs/run-2/seats/S14-743-subagent/work', 'workdir'); }
    catch (err) { threw = err.code; }
    check('9  a seat-identity workdir is refused (boundary 6)', threw === 'E_SEAT_IMPERSONATION', threw);
    let ok = true;
    try { dispatchMod.assertNotSeatIdentity('/x/.rbtv/sessions/subagent-1', 'workdir'); } catch { ok = false; }
    check('10 control: a sessions-root workdir is NOT refused', ok);
  }

  // ── the workspace-ambiguity refusal (the defect this build hit and fixed) ───────────────────
  {
    const fake = fs.mkdtempSync(path.join(os.tmpdir(), 'subagent-probe-ws-'));
    fs.mkdirSync(path.join(fake, '.rbtv'));
    let code = null;
    try { dispatchMod.resolveWorkspaceRoot(fake); } catch (err) { code = err.code; }
    check('11 two disagreeing workspaces REFUSE rather than one being picked',
      code === 'E_WORKSPACE_AMBIGUOUS', code || 'resolved without refusing');
    fs.rmSync(fake, { recursive: true, force: true });
  }

    // control: THE PRE-FIX CODE, BY CONSTRUCTION. The same supervisor, the same spec, spawned the
  // way a build that had not written env.js would spawn it — with no `env` option, so the child
  // inherits the dispatcher's environment. If the canary is absent HERE, checks 18-20 (paid half) prove
  // nothing, because they would be green with or without the wall.
  {
    const ctlDir = fs.mkdtempSync(path.join(os.tmpdir(), 'subagent-probe-envctl-'));
    const spec = { argv: ['/bin/true'], workdir: ctlDir, promptFile: null, sessionDir: ctlDir };
    const specFile = path.join(ctlDir, 'spec.json');
    fs.writeFileSync(specFile, JSON.stringify(spec));
    const ctl = spawn(process.execPath, [dispatchMod.SUPERVISOR, specFile], {
      detached: true, stdio: ['ignore', 'ignore', 'ignore', 'pipe'],
      env: hermeticEnv({ [SENTINEL]: SENTINEL_VALUE }),   // <- the pre-fix spawn: inherited env
    });
    await sleep(1500);
    let ctlNames = [];
    try { ctlNames = JSON.parse(fs.readFileSync(path.join(ctlDir, 'env-names.json'), 'utf8')).names; } catch { /* recorded below as empty */ }
    check('21 control: the SAME supervisor spawned WITHOUT the built environment DOES carry the canary',
      ctlNames.includes(SENTINEL),
      `${ctlNames.length} names; canary ${ctlNames.includes(SENTINEL) ? 'present' : 'ABSENT — checks 18-20 (paid half) prove nothing'}`);
    try { process.kill(-ctl.pid, 'SIGKILL'); } catch { /* already gone */ }
    fs.rmSync(ctlDir, { recursive: true, force: true });
  }

    // ── boundary 3 — the bus is not reachable BY NAME on the child's PATH ────────────────────
  const busCli = ['coordinate', 'sd-graph', 'sb-task', 'ignite', 'rbtv'];
  const onPath = (pathValue) => busCli.filter((b) => pathValue.split(':').some((d) => {
    try { fs.accessSync(path.join(d, b), fs.constants.X_OK); return true; } catch { return false; }
  }));
  check('22 no coordination CLI is on the sub-agent\'s PATH (boundary 3)',
    onPath(envMod.MINIMAL_PATH).length === 0, onPath(envMod.MINIMAL_PATH).join(' '));
  check('23 control: the same scan DOES find them on the dispatcher\'s own PATH',
    onPath(process.env.PATH).length > 0, onPath(process.env.PATH).join(' '));

  // ═══ POSITIVE HALF — a REAL run of a REAL harness. OPT-IN (--real), G-213. ══════════════════
  if (!REAL) {
    process.stdout.write(
      `\nSKIPPED: the paid half (checks 12-20, 24-27) — ${REAL_CHECKS - FREE_CHECKS} checks needing ` +
      `two REAL claude invocations and a SIGKILLed process tree. Re-run with --real to buy them.\n` +
      `They are NOT unproven: they were run and recorded as 7.43's acceptance evidence (G-213 ruling,\n` +
      `seats/leader/ruling-g213-and-743-deferred.md). RUN --real BEFORE ACCEPTING ANY CHANGE TO THIS\n` +
      `CAPABILITY'S OWN FILES — that trigger is the whole mitigation, and nothing enforces it.\n`);
  }

  let real = null;
  if (REAL) {
    const r = runTool([
      'dispatch', '--target', 'ticker-settings', '--profile', 'claude-sonnet-tools',
      '--effort', 'low', '--resumable', '--json',
      '--task', 'Write a file named summary.md in your working directory with three bullet lines summarising the entry point you read. Then stop.',
    ], { env: { [SENTINEL]: SENTINEL_VALUE }, timeoutMs: 300000 });
    real = r.json;
    check('12 a real sub-agent ran to completion under the claude harness',
      r.status === 0 && real && real.exitCode === 0, `exit ${r.status}, sub-agent exit ${real && real.exitCode}`);
    check('13 the ladder WALKED to headless for claude under the SAME needResumable situation',
      real && real.rung === 'headless' && real.harness === 'claude', real && `${real.harness}/${real.rung}`);
    check('14 the argv came from the shared profile resolver, not from a local table',
      real && real.argv && real.argv.length === 11 && real.argv[0].endsWith('/claude') && real.argv.includes('--effort'),
      real && real.argv && real.argv.join(' '));
  }

  if (REAL && real && real.workdir) {
    const files = fs.readdirSync(real.workdir);
    // ── boundary 6, ON DISK, after a real run ────────────────────────────────────────────────
    check('15 the sub-agent produced its artifact', files.includes('summary.md'), files.join(' '));
    const stray = [real.workdir, ...files.map((f) => path.join(real.workdir, f))]
      .filter((p) => dispatchMod.SEAT_IDENTITY_RE.test(p));
    check('16 workdir and EVERY artifact land outside any seat folder (boundary 6, path inspection)',
      stray.length === 0, stray.join(' '));
    const tfHits = spawnSync('bash', ['-lc',
      `grep -rl '${real.execId}\\|subagent-dispatch' ${dispatchMod.resolveWorkspaceRoot(os.homedir())}/.rbtv/goals/*/runs/*/taskforce.csv 2>/dev/null | head`],
    { encoding: 'utf8' }).stdout.trim();
    check('17 the sub-agent appears in no taskforce.csv', tfHits === '', tfHits);

    // ── boundary 11, from the environment the sub-agent ACTUALLY ran with ────────────────────
    const envNames = JSON.parse(fs.readFileSync(path.join(real.workdir, 'env-names.json'), 'utf8')).names;
    const expected = new Set(['PATH', ...envMod.BASE_PASSTHROUGH.filter((n) => process.env[n] !== undefined), envMod.DEPTH_VAR]);
    check('18 the sub-agent ran with EXACTLY the allowlisted variable names (boundary 11)',
      envNames.length === expected.size && envNames.every((n) => expected.has(n)), envNames.join(','));
    check('19 the dispatcher-side leak canary did NOT reach the sub-agent',
      !envNames.includes(SENTINEL), `canary ${SENTINEL} ${envNames.includes(SENTINEL) ? 'PRESENT' : 'absent'}`);
    check('20 no coordination/credential-shaped variable survived the scrub (boundary 3)',
      !envNames.some((n) => envMod.FORBIDDEN_NAME_RE.test(n) && n !== envMod.DEPTH_VAR), envNames.join(','));

  } else if (REAL) {
    check('15-20 post-run disk checks', false, 'no real run to inspect');
  }

  // ═══ boundary 8 + 4 — KILL THE DISPATCHER MID-RUN, WATCH THE TREE DIE (paid) ═══════════════
  if (REAL) {
    const cli = spawn(process.execPath, [
      TOOL, 'dispatch', '--target', 'ticker-settings', '--profile', 'claude-sonnet-tools',
      '--effort', 'low', '--json',
      '--task', 'Read the entry point and write a long, careful ten-section review of it to review.md. Take your time.',
    ], { stdio: ['ignore', 'ignore', 'ignore'], env: hermeticEnv() });

    // Find the supervisor through the fan-out registry — the dispatcher's own record of what it
    // spawned. Never a pattern match over the process table.
    const ws = dispatchMod.resolveWorkspaceRoot(os.homedir());
    const dir = fanout.registryDir(path.join(ws, '.rbtv', 'runtime'), fanout.dispatcherId());
    let supervisorPid = null;
    for (let i = 0; i < 60 && supervisorPid === null; i++) {
      await sleep(500);
      for (const c of fanout.liveClaims(dir)) {
        if (c.dispatcherPid === cli.pid) supervisorPid = c.supervisorPid;
      }
    }
    check('24 the dispatch registered a supervisor', supervisorPid !== null, `supervisor pid ${supervisorPid}`);

    if (supervisorPid) {
      const membersBefore = pgidMembers(supervisorPid);
      check('25 the sub-agent runs in its OWN process group, with the harness in it (boundary 8)',
        membersBefore.includes(supervisorPid) && membersBefore.length >= 2, `pgid ${supervisorPid}: pids ${membersBefore.join(',')}`);

      // MID-RUN, and SIGKILL specifically: an exit handler would satisfy the sentence "dies with
      // the dispatching step" and fail this test, which is why the mechanism is a death pipe.
      process.kill(cli.pid, 'SIGKILL');
      let membersAfter = membersBefore;
      for (let i = 0; i < 30; i++) {
        await sleep(500);
        membersAfter = pgidMembers(supervisorPid);
        if (membersAfter.length === 0) break;
      }
      check('26 SIGKILLing the dispatcher mid-run kills the WHOLE tree (boundaries 4 + 8)',
        membersAfter.length === 0, `survivors in pgid ${supervisorPid}: ${membersAfter.join(',') || 'none'}`);
      for (const pid of membersAfter) { try { process.kill(pid, 'SIGKILL'); } catch { /* gone */ } }
    }

    // control: THE OS DOES NOT DO THIS FOR US. A child spawned detached by a parent that is then
    // SIGKILLed SURVIVES. Without this, check 26 would be green on a box where everything happened
    // to die anyway, and the death pipe would be proving nothing.
    {
      const orphanParent = spawn(process.execPath, ['-e',
        "const{spawn}=require('node:child_process');const c=spawn('sleep',['60'],{detached:true,stdio:'ignore'});c.unref();process.stdout.write(String(c.pid));setInterval(()=>{},1000);"],
      { stdio: ['ignore', 'pipe', 'ignore'], env: hermeticEnv() });
      let orphanPid = '';
      orphanParent.stdout.on('data', (b) => { orphanPid += b; });
      await sleep(1500);
      process.kill(orphanParent.pid, 'SIGKILL');
      await sleep(1500);
      const alive = fanout.pidAlive(Number(orphanPid));
      check('27 control: a detached child WITHOUT the death pipe SURVIVES its parent\'s SIGKILL',
        alive, `orphan pid ${orphanPid} ${alive ? 'alive — the death pipe is what kills the tree' : 'died on its own — check 26 proves nothing'}`);
      try { process.kill(Number(orphanPid), 'SIGKILL'); } catch { /* gone */ }
    }
  }

  // ── completeness (G-121): a short tally is a FAILURE however many checks passed ─────────────
  // Hand-counted per MODE, and the literal EARNED its keep on the probe's first run: it said 27,
  // the run reported 29/27, and an all-green run was correctly graded a FAILURE until the count was
  // reconciled. A skipped paid half must never make the tally read complete by shrinking silently —
  // which is why there are two literals and not one derived count.
  const EXPECTED_CHECKS = REAL ? REAL_CHECKS : FREE_CHECKS;
  const complete = results.length === EXPECTED_CHECKS;
  process.stdout.write(`\n${complete ? '' : '⚠ INCOMPLETE RUN — '}${pass} passed, ${fail} failed, ${results.length}/${EXPECTED_CHECKS} checks run  [${REAL ? 'REAL — paid half bought' : 'free half only; --real buys the paid half'}]\n`);
  if (!complete) process.stdout.write('A truncated run reads greener than a complete one (G-121). Treating it as a failure.\n');
  process.exit(fail === 0 && complete ? 0 : 1);
}

main().catch((err) => { process.stdout.write(`PROBE CRASHED: ${err.stack}\n`); process.exit(1); });
