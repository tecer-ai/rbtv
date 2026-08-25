'use strict';

// probe-goal-teardown — `rbtv-goal teardown` end to end (IPH-27), driven as a real child
// process against a REAL throwaway daemon.
//
// ⚑ THE ONLY JS PROBE IN THIS FOLDER, and the reason is the subject. Its three siblings here
// are pure-python because the verbs they cover are pure file operations; `teardown` is the ONE
// `rbtv-goal` verb that needs the daemon up, because what it reclaims — the job CATALOGUE —
// lives in heart.db and is served only by the gateway. So the probe has to BOOT a daemon, and
// `../../..​/cli/probes/lib/fixtures.js` is the one thing in this repo that does (a throwaway
// workspace, an ephemeral port, its own senders file). Reusing it is the whole point: nothing
// here ever touches the live `rbtv-ignite` daemon or the live catalogue.
//
// THE FAILURE THIS COVERS. Scaffolding a goal WRITES catalogue rows and deleting the goal folder
// removed none of them; registration is create-only, so the goal's NAME was burnt — 18 stranded
// rows for one goal on the live box, and a same-name re-scaffold refused E_JOB_EXISTS.
//
// What it proves:
//   1. EXACT PATH — with `taskforce.csv` present, teardown composes ids from the goal's OWN seat
//      registry: `--dry-run` names exactly the workflow-start row plus one per seat, and changes
//      nothing (the catalogue is byte-identical after).
//   2. THE ACT — the rows are gone from `inspect jobs`, and the GOAL FOLDER IS STILL THERE
//      (owner-ruled: teardown cleans the daemon's side only).
//   3. ⚑ THE PAYOFF — the id REGISTERS AGAIN. This is the discriminating check; everything above
//      it only shows the mechanism moving.
//   4. CONTROL — a pending QUEUE ROW does not defeat it: teardown removes the row first, in the
//      one order the purge guards admit. (Run the steps out of order by hand and the purge
//      refuses `pending-queue-rows`.)
//   5. CONTROL — the ORPHAN path (folder already gone, ids matched by NAME) REFUSES without
//      `--yes` and deletes nothing; with `--yes` it purges.
//   6. ⚑ CONTROL — THE PREFIX COLLISION. A goal name can be a prefix of another goal's name
//      (the live box carries `throwaway-0811-settle` / `throwaway-0811-settle-kill` today), so
//      the orphan path's name match sweeps the OTHER goal's seat rows. Teardown must NAME the
//      shadowing goal and refuse rather than delete on trust.
//   7. A goal with NO catalogue rows at all is a clean no-op, never an error.
//
// ⚑ REQUIRES A POSIX BOX (like every probe that boots a daemon).

const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, runCli } = require('../../../ignite-cli/probes/lib/fixtures');
const { requirePythonCmd } = require('../../../runtime/python-cmd');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-goal-teardown.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const GOAL_CLI = path.join(__dirname, '..', 'tool', 'goal_cli.py');
const CLI_ENTRY = path.join(__dirname, '..', '..', '..', 'ignite-cli', 'ignite.js');
// 7.787: `launch-agent` requires NOTHING (`#d-abolish-profile-names` emptied its REQUIRED_ARGS),
// so the S-2(a) register-time gate admits an empty `required`. This probe's subject is teardown's
// SEQUENCING, not the args schema — the row only has to be enqueueable.
const SCHEMA = '{"required":{},"optional":{"workdir":"string"}}';

// The verb under test, run as a REAL child process — never imported, never emulated. It is handed
// the throwaway daemon's address and token exactly as an operator's shell would be.
// ⚑ `pythonCmd` IS A STRING (`'python3'`), not an argv array — `requirePythonCmd` returns the
// command name. Spreading it as if it were an array turns it into single CHARACTERS and spawns
// `p` with args `y,t,h,o,n,3`, whose ENOENT arrives as an 'error' event: with no listener the
// process dies where it stands, writing no verdict and no EXIT line. That is what the `error`
// handler below exists for — a probe that cannot run its subject must FAIL, never vanish.
function runTeardown(pythonCmd, goalsRoot, argv, env) {
  return new Promise((resolve) => {
    const proc = spawn(pythonCmd, [GOAL_CLI, 'teardown', ...argv,
      '--root', goalsRoot, '--ignite-bin', CLI_ENTRY], { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = ''; let stderr = '';
    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });
    proc.on('error', (err) => resolve({ code: -1, stdout, stderr: `spawn failed: ${err.message}` }));
    proc.on('exit', (code) => resolve({ code, stdout, stderr }));
  });
}

// A goal folder is only ever as much as teardown reads: the seat registry. Written with the same
// header the real writer uses so the reader under test is exercised, not a shape invented here.
function makeGoal(goalsRoot, name, seats) {
  const dir = path.join(goalsRoot, name);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'taskforce.csv'),
    'taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n'
    + seats.map((s, i) => `tf-1,${s},${i ? seats[i - 1] : ''},claude,claude-fable-5,high,35,`).join('\n')
    + '\n');
  return dir;
}

async function jobIds(env) {
  const r = await runCli(['--json', 'inspect', 'jobs'], env);
  const rows = JSON.parse(r.stdout).result.rows;
  if (!Array.isArray(rows)) throw new Error(`inspect jobs carried no result.rows: ${r.stdout.slice(0, 200)}`);
  return rows.map((j) => j.job_id).sort();
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const pythonCmd = requirePythonCmd();
  const ws = makeWorkspace('iph27-goal-teardown');
  const port = await freePort();
  const env = baseEnv(ws, port);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); process.exitCode = 1; return; }

  try {
    const ownerEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };
    // ⚑ The goals root is a THROWAWAY DIRECTORY, deliberately not the daemon's own workspace
    // `.rbtv/goals`: a folder appearing under a live goals root is something the daemon's lane
    // watch reads, and a probe must not hand a daemon a goal to think about.
    const goalsRoot = path.join(ws.workRoot, 'goals');
    fs.mkdirSync(goalsRoot, { recursive: true });

    const SEATS = ['alpha', 'beta', 'gamma'];
    const goalDir = makeGoal(goalsRoot, 'tdgoal', SEATS);
    const ids = ['tdgoal-workflow-start', ...SEATS.map((s) => `seat-tdgoal-${s}`)];
    // ⚑ EVERY SETUP CALL IS CHECKED, and the timeout is raised past `runCli`'s 15 s default.
    // Under `--only` this probe is alone on the box; in a directory sweep it shares the machine,
    // and on the first sweep run ONE register-job was SIGKILLed at 15 s. The missing row then
    // surfaced two checks later as "the catalogue does not have what I registered" — a setup
    // failure wearing a subject failure's clothes. A setup step that fails must say so where it
    // happens, or the probe reports on a subject it never assembled.
    const setupFailures = [];
    for (const id of ids) {
      const rr = await runCli(['register-job', id, '--action-type', 'launch-agent',
        '--args-schema', SCHEMA], ownerEnv, { timeoutMs: 60000 });
      if (rr.code !== 0) setupFailures.push(`${id}: exit ${rr.code} ${rr.stderr.trim().slice(0, 120)}`);
    }
    const seeded = await jobIds(ownerEnv);
    check('setup: the goal\'s 4 catalogue rows are registered',
      setupFailures.length === 0 && ids.every((i) => seeded.includes(i)),
      setupFailures.length ? `register failed — ${setupFailures.join(' | ')}`
        : `catalogue=${JSON.stringify(seeded)}`);

    // --- 1. EXACT PATH, dry run: ids come from taskforce.csv, and nothing changes. -----------
    const beforeDry = await jobIds(ownerEnv);
    let r = await runTeardown(pythonCmd, goalsRoot, ['tdgoal', '--dry-run'], ownerEnv);
    out('--- teardown --dry-run ---', 'EXIT=' + r.code, r.stdout.trim(), r.stderr.trim());
    check('EXACT: --dry-run names every id from the goal\'s own taskforce.csv',
      r.code === 0 && /ids from: taskforce/.test(r.stdout) && ids.every((i) => r.stdout.includes(i)),
      `exit=${r.code}`);
    check('EXACT: --dry-run changed no catalogue row',
      JSON.stringify(await jobIds(ownerEnv)) === JSON.stringify(beforeDry),
      `before=${beforeDry.length} after=${(await jobIds(ownerEnv)).length}`);

    // --- 4. CONTROL: a pending queue row is removed first, in the order the guards admit. ----
    // Seeded BEFORE the act on purpose: run the steps by hand in the wrong order and the purge
    // refuses `pending-queue-rows`, so this is what proves teardown sequences them itself.
    // 7.787: no `--profile` — the flag is gone and `launch-agent` requires no argument, so the
    // row is enqueued with none. What it runs is the seat's own cast, resolved at spawn.
    const added = await runCli(['add-job', '--fn', 'seat-tdgoal-beta',
      '--trigger', 'scheduled', '--at', '2099-01-01T00:00:00Z'], ownerEnv, { timeoutMs: 60000 });
    const queuedBefore = JSON.parse((await runCli(['--json', 'inspect', 'queue'], ownerEnv)).stdout).result.rows;
    check('setup: a pending queue row exists against one of the goal\'s seats',
      added.code === 0 && queuedBefore.some((q) => q.job_id === 'seat-tdgoal-beta'),
      `add-job exit=${added.code} ${added.stderr.trim().slice(0, 120)} queue=${JSON.stringify(queuedBefore.map((q) => q.job_id))}`);

    // --- 2. THE ACT. -----------------------------------------------------------------------
    r = await runTeardown(pythonCmd, goalsRoot, ['tdgoal'], ownerEnv);
    out('--- teardown ---', 'EXIT=' + r.code, r.stdout.trim(), r.stderr.trim());
    const afterAct = await jobIds(ownerEnv);
    check('the act exits 0 and reports the name is free',
      r.code === 0 && /is now free/.test(r.stdout), `exit=${r.code} stdout=${r.stdout.trim()}`);
    check('every one of the goal\'s rows is GONE from the catalogue',
      ids.every((i) => !afterAct.includes(i)), `catalogue=${JSON.stringify(afterAct)}`);
    check('CONTROL: the pending queue row was removed as part of it',
      !JSON.parse((await runCli(['--json', 'inspect', 'queue'], ownerEnv)).stdout)
        .result.rows.some((q) => q.job_id === 'seat-tdgoal-beta'));
    // ⚑ The owner ruling, asserted rather than trusted to the help text.
    check('THE GOAL FOLDER IS UNTOUCHED (teardown cleans the daemon\'s side only)',
      fs.existsSync(path.join(goalDir, 'taskforce.csv')), `goalDir=${goalDir}`);

    // --- 3. ⚑ THE PAYOFF. ------------------------------------------------------------------
    r = await runCli(['register-job', 'seat-tdgoal-alpha', '--action-type', 'launch-agent', '--args-schema', SCHEMA], ownerEnv);
    check('PAYOFF: a torn-down id REGISTERS AGAIN (the name is genuinely free)',
      r.code === 0 && !/E_JOB_EXISTS/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);
    await runCli(['deregister-job', 'seat-tdgoal-alpha'], ownerEnv);
    await runCli(['deregister-job', 'seat-tdgoal-alpha', '--purge'], ownerEnv);

    // --- 5. CONTROL: the ORPHAN path refuses without --yes. --------------------------------
    const orphanIds = ['orphan-workflow-start', 'seat-orphan-a', 'seat-orphan-b'];
    for (const id of orphanIds) {
      await runCli(['register-job', id, '--action-type', 'launch-agent', '--args-schema', SCHEMA], ownerEnv);
    }
    // No folder is created at all — this IS the state a deleted goal leaves behind.
    r = await runTeardown(pythonCmd, goalsRoot, ['orphan'], ownerEnv);
    out('--- ORPHAN without --yes ---', 'EXIT=' + r.code, r.stdout.trim(), r.stderr.trim());
    check('CONTROL: the ORPHAN path REFUSES without --yes and names what it matched',
      r.code === 1 && /confirm-required/.test(r.stderr) && orphanIds.every((i) => r.stderr.includes(i)),
      `exit=${r.code} stderr=${r.stderr.trim().slice(0, 300)}`);
    const afterRefusal = await jobIds(ownerEnv);
    check('CONTROL: the refused orphan run deleted nothing',
      orphanIds.every((i) => afterRefusal.includes(i)), `catalogue=${JSON.stringify(afterRefusal)}`);

    // --- 6. ⚑ CONTROL: THE PREFIX COLLISION, which is why check 5's gate exists. -------------
    // `orphan-kill` extends `orphan`, so `seat-orphan-` matches ITS seat too. Registered BEFORE
    // the --yes run so the sweep would take it if the shadow gate were not there — the check is
    // that teardown NAMES the shadowing goal and refuses, not that it quietly does the right thing.
    // ⚑ RUN WITH `--yes`, WHICH IS THE POINT. The first cut of this guard was a REFUSAL gated on
    // `not args.yes`, so the flag that confirms the orphan LIST also switched off the shadow
    // protection and this exact command purged `seat-orphan-kill-z`. This probe caught that on
    // its first run; the fix excludes the other goal's rows instead of refusing, so the assertion
    // is now the CORRECT OUTCOME (their row survives, mine are purged) rather than a refusal.
    fs.mkdirSync(path.join(goalsRoot, 'orphan-kill'), { recursive: true });
    await runCli(['register-job', 'seat-orphan-kill-z', '--action-type', 'launch-agent', '--args-schema', SCHEMA], ownerEnv);
    r = await runTeardown(pythonCmd, goalsRoot, ['orphan', '--yes'], ownerEnv);
    out('--- ORPHAN --yes with a PREFIX-SHADOWING goal present ---', 'EXIT=' + r.code, r.stdout.trim(), r.stderr.trim());
    const afterShadow = await jobIds(ownerEnv);
    check('CONTROL: a prefix-SHADOWING goal\'s row SURVIVES the sweep, even under --yes',
      afterShadow.includes('seat-orphan-kill-z'), `catalogue=${JSON.stringify(afterShadow)}`);
    check('the goal\'s OWN rows are still purged in the same run',
      r.code === 0 && orphanIds.every((i) => !afterShadow.includes(i)),
      `exit=${r.code} catalogue=${JSON.stringify(afterShadow)}`);

    // --- 7. A goal with no rows at all is a clean no-op. ------------------------------------
    makeGoal(goalsRoot, 'tdempty', ['solo']);
    r = await runTeardown(pythonCmd, goalsRoot, ['tdempty'], ownerEnv);
    out('--- teardown of a goal with NO catalogue rows ---', 'EXIT=' + r.code, r.stdout.trim());
    check('a goal with NO registered rows is a clean no-op, never an error',
      r.code === 0 && /never registered/.test(r.stdout), `exit=${r.code} stdout=${r.stdout.trim()}`);
  } finally {
    await stopDaemon(d);
  }

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`GOAL_TEARDOWN_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
}

main().catch((err) => {
  out('ERROR:', err.message, err.stack);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
});
