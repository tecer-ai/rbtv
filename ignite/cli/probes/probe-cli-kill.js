'use strict';

// probe-cli-kill — proves `ignite kill <session-id>` end-to-end through the
// REAL CLI binary against a REAL (throwaway) daemon: local usage errors; a
// non-integer id refused at the gateway shape-check (exit 4 — the CLI carries
// no local integer check, deliberately unlike remove-job); an unknown id is a
// typed NOT_FOUND; a non-owner, non-creator sender is a typed
// UNAUTHORIZED_SENDER (D65(B) applied to kill); a session already terminal is
// a typed refusal; and a REAL kill of a live process — a `running` setsid row
// seeded to point at a sleep child THIS PROBE spawned and owns (D4 forbids
// requiring a real WORKER spawn through the daemon; a probe-owned child is the
// probe's own business, and the boot orphan rescan reattaches it as live).
// The --json envelope is asserted on each refusal class. The real kill also
// asserts the KILL AUDIT record (cli-expansion owner ruling, 2026-07-20)
// landed beside the session's output log: file exists, non-empty, and carries
// the exec id + the attested sender.
//
// NEVER touches the live daemon: throwaway workspace, throwaway senders file,
// ephemeral port; only children this probe spawns are ever signaled.

const fs = require('node:fs');
const path = require('node:path');
const { spawn: childSpawn } = require('node:child_process');
const {
  IGNITE_SRC, freePort, makeWorkspace, baseEnv, bootDaemon, stopDaemon, seedCatalogue, runCli,
} = require('./lib/fixtures');

// Local fixture helpers (D4: a missing helper is built locally inside the
// probe file, never added to fixtures). Both run in THIS probe's own process,
// before the daemon child boots, against the same db it then opens — the same
// setup discipline seedCatalogue itself follows.
const { openHeartStore, closeHeartStore } = require(path.join(IGNITE_SRC, 'server', 'heart', 'heart-store'));
const { setsidStatus } = require(path.join(IGNITE_SRC, 'server', 'spawn', 'carrier'));
const { auditPathFor } = require(path.join(IGNITE_SRC, 'server', 'internal-api', 'keys-audit'));

function seedExecution(ws, patch) {
  const store = openHeartStore({ runtimeStateRoot: ws.workspaceRoot });
  try {
    const row = store.recordExecutionStart({
      jobId: 'probe-cli-sleep',
      actionType: 'launch-agent',
      args: JSON.stringify({ profile: 'test-sleep' }),
      enqueuedBy: 'probe-owner',
      firedTick: 0,
      firedAt: new Date(),
      profile: 'test-sleep',
    });
    if (patch) store.updateExecutionStatus(row.exec_id, patch);
    return row.exec_id;
  } finally {
    closeHeartStore();
  }
}

const start = Date.now();
const outPath = path.join(__dirname, 'probe-cli-kill.out');
fs.writeFileSync(outPath, '');
function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

function parseEnvelope(r) {
  try { return JSON.parse(r.stdout.trim()); } catch { return null; }
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const ws = makeWorkspace('ce-4-cli-kill');
  const port = await freePort();
  const env = baseEnv(ws, port);
  // execId: a NEVER-SPAWNED execution row (status launching, no carrier
  // metadata), enqueued_by probe-owner — the daemon's boot orphan rescan
  // sweeps it to `failed` ("missing carrier metadata"). doneId: a terminal
  // (`done`) row. liveId: a `running` setsid row whose pid is a sleep child
  // THIS probe spawned (detached ⇒ its own process group, which is what
  // killSetsid signals); the rescan sees it live + starttime-matched and
  // REATTACHES it, so the real kill path is exercisable.
  const { execId } = seedCatalogue(ws, { withExecution: true });
  const doneId = seedExecution(ws, { status: 'done', endedAt: new Date() });
  const sleeper = childSpawn('sleep', ['300'], { detached: true, stdio: 'ignore' });
  sleeper.unref();
  const sleeperStat = setsidStatus(sleeper.pid);
  // A real spawned row ALWAYS carries a log_path (spawn writes it at `launching`, before any
  // carrier launch) — the kill audit lands beside it. Seed one so this synthetic row has the
  // same shape, and so the audit assertion below has a derivable location.
  const liveLog = path.join(ws.tmp, 'live-session.log');
  fs.writeFileSync(liveLog, '');
  const liveId = seedExecution(ws, {
    status: 'running',
    carrier: 'setsid',
    pid: sleeper.pid,
    pidStarttime: sleeperStat.pidStarttime,
    startedAt: new Date(),
    logPath: liveLog,
  });
  out(`seeded exec_id=${execId} (never spawned) done exec_id=${doneId} live exec_id=${liveId} (sleep pid ${sleeper.pid})`);

  const d = await bootDaemon(env);
  check('the throwaway daemon boots and its gateway listens', d.listening === true,
    d.listening ? `port ${port}` : `exit=${d.exitCode} ${d.errLog().slice(0, 300)}`);
  if (!d.listening) { out('ABORT: daemon never listened.'); return; }

  const ownerEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.OWNER_TOKEN };
  const agentEnv = { ...process.env, IGNITE_GATEWAY_ADDR: `127.0.0.1:${port}`, IGNITE_SENDER_TOKEN: ws.AGENT_TOKEN };

  try {
    // 1. Local usage error: no id at all → exit 2, never reaches the gateway.
    let r = await runCli(['kill'], ownerEnv);
    out('--- kill missing id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('kill with no id is a LOCAL usage error, exit 2', r.code === 2 && /USAGE ERROR/.test(r.stderr), `exit=${r.code}`);

    r = await runCli(['--json', 'kill'], ownerEnv);
    let envl = parseEnvelope(r);
    check('kill with no id under --json is the envelope shape with CLI_USAGE_ERROR, exit 2',
      r.code === 2 && envl && envl.ok === false && envl.error.code === 'CLI_USAGE_ERROR',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 2. Non-integer id: NO local integer check — the gateway's shape-check
    // refuses it typed (SHAPE_INVALID → exit 4 per the exit-code table).
    r = await runCli(['kill', 'not-a-number'], ownerEnv);
    out('--- kill non-integer id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('kill with a non-integer id is the GATEWAY shape refusal (SHAPE_INVALID, exit 4)',
      r.code === 4 && /SHAPE_INVALID/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);

    r = await runCli(['--json', 'kill', 'not-a-number'], ownerEnv);
    envl = parseEnvelope(r);
    check('non-integer id under --json is the raw envelope with SHAPE_INVALID, exit 4',
      r.code === 4 && envl && envl.ok === false && envl.error.code === 'SHAPE_INVALID',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 3. Unknown id → typed NOT_FOUND (exit 1, catch-all per the exit-code table).
    r = await runCli(['kill', '999999'], ownerEnv);
    out('--- kill unknown id ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('kill on an unknown id is a typed NOT_FOUND, exit 1', r.code === 1 && /NOT_FOUND/.test(r.stderr), `exit=${r.code}`);

    r = await runCli(['--json', 'kill', '999999'], ownerEnv);
    envl = parseEnvelope(r);
    check('unknown id under --json is the raw envelope with NOT_FOUND, exit 1',
      r.code === 1 && envl && envl.ok === false && envl.error.code === 'NOT_FOUND',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 4. Authorization (D65(B) applied to kill): the AGENT sender is neither
    // the owner nor the sender that enqueued this row (enqueued_by is
    // probe-owner) → typed UNAUTHORIZED_SENDER, exit 1. Fires BEFORE any state
    // check — the refusal must not leak the session's state.
    r = await runCli(['kill', String(execId)], agentEnv);
    out('--- kill as non-creator agent ---', 'EXIT=' + r.code, 'STDERR=' + r.stderr.trim());
    check('kill by a non-owner, non-creator sender is a typed UNAUTHORIZED_SENDER, exit 1',
      r.code === 1 && /UNAUTHORIZED_SENDER/.test(r.stderr), `exit=${r.code} stderr=${r.stderr.trim()}`);

    r = await runCli(['--json', 'kill', String(execId)], agentEnv);
    envl = parseEnvelope(r);
    check('the authz refusal under --json is the raw envelope with UNAUTHORIZED_SENDER, exit 1',
      r.code === 1 && envl && envl.ok === false && envl.error.code === 'UNAUTHORIZED_SENDER',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 5. Already-terminal session → typed refusal (VALIDATION_FAILED,
    // check session-terminal), never a re-kill that falsifies the lifecycle.
    r = await runCli(['--json', 'kill', String(doneId)], ownerEnv);
    out('--- kill terminal (done) session ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    envl = parseEnvelope(r);
    check('kill on an already-terminal (done) session is a typed VALIDATION_FAILED naming session-terminal, exit 4',
      r.code === 4 && envl && envl.ok === false && envl.error.code === 'VALIDATION_FAILED'
        && envl.error.details && envl.error.details.check === 'session-terminal',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 6. The never-spawned row: the daemon's boot orphan rescan already swept
    // it to `failed` (missing carrier metadata), so the honest wire answer is
    // the already-terminal typed refusal — proving the sweep and the terminal
    // check compose. (The E_CARRIER_FAILED wire mapping guards the in-flight
    // window where a `launching` row has no carrier YET; that window cannot be
    // held open from outside the daemon, so it is not exercisable here.)
    r = await runCli(['--json', 'kill', String(execId)], ownerEnv);
    out('--- kill never-spawned session (owner) ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    envl = parseEnvelope(r);
    check('owner kill of a never-spawned row (swept to failed at boot rescan) is the typed session-terminal refusal, exit 4',
      r.code === 4 && envl && envl.ok === false && envl.error.code === 'VALIDATION_FAILED'
        && envl.error.details && envl.error.details.check === 'session-terminal'
        && envl.error.details.status === 'failed',
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // 7. A REAL kill of a live process: the reattached `running` setsid row.
    // Human summary, exit 0; the probe's own sleep child must actually be dead
    // afterwards; the store's status must read `killed` (D23 closed enum).
    r = await runCli(['kill', String(liveId)], ownerEnv);
    out('--- kill live session ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    check('kill on a live session exits 0 and prints the human killed summary (session + signal)',
      r.code === 0 && new RegExp(`^killed: session ${liveId} \\(signal SIG(TERM|KILL)\\)`).test(r.stdout),
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // The process is REALLY gone (poll briefly — TERM is asynchronous).
    let processDead = false;
    for (let i = 0; i < 25 && !processDead; i++) {
      try { process.kill(sleeper.pid, 0); await new Promise((res) => setTimeout(res, 200)); } catch { processDead = true; }
    }
    check('the killed session\'s process is actually dead', processDead, `pid=${sleeper.pid}`);

    r = await runCli(['--json', 'inspect', 'status', String(liveId)], ownerEnv);
    envl = parseEnvelope(r);
    check('inspect status on the killed session reports status "killed" and not live',
      r.code === 0 && envl && envl.ok === true && envl.result.status === 'killed' && envl.result.live === false,
      `exit=${r.code} stdout=${r.stdout.trim()}`);

    // The KILL AUDIT record landed (cli-expansion owner ruling, 2026-07-20): the audit file
    // sits beside the session's output log (the daemon's own derivation), is non-empty, and
    // its record carries the exec id and the attested sender. No probe asserts the keystroke/
    // screen records today, so the assertion here is the dispatch-ruled baseline: exists +
    // non-empty + exec id + sender.
    const auditPath = auditPathFor(liveLog);
    const auditExists = fs.existsSync(auditPath);
    const auditRaw = auditExists ? fs.readFileSync(auditPath, 'utf8') : '';
    out('--- kill audit record ---', 'AUDIT_PATH=' + auditPath, 'AUDIT=' + auditRaw.trim());
    check('the kill audit file exists beside the session log and is non-empty',
      auditExists && auditRaw.trim().length > 0, `path=${auditPath}`);
    let auditRec = null;
    try { auditRec = JSON.parse(auditRaw.trim().split('\n')[0]); } catch {}
    check('the kill audit record is a session-killed record carrying the exec id and the attested sender',
      auditRec !== null && auditRec.event === 'session-killed' && auditRec.id === liveId
        && auditRec.sender_id === 'probe-owner',
      `record=${auditRaw.trim().split('\n')[0]}`);

    // 8. Killing it AGAIN is now the typed already-terminal refusal.
    r = await runCli(['--json', 'kill', String(liveId)], ownerEnv);
    out('--- kill already-killed session ---', 'EXIT=' + r.code, 'STDOUT=' + r.stdout.trim());
    envl = parseEnvelope(r);
    check('kill on an already-killed session is the typed session-terminal refusal (status killed), exit 4',
      r.code === 4 && envl && envl.ok === false && envl.error.code === 'VALIDATION_FAILED'
        && envl.error.details && envl.error.details.check === 'session-terminal'
        && envl.error.details.status === 'killed',
      `exit=${r.code} stdout=${r.stdout.trim()}`);
  } finally {
    await stopDaemon(d);
    try { process.kill(-sleeper.pid, 'SIGKILL'); } catch {}
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
