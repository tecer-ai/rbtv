'use strict';

// probe-ticker-cadence-flow — task 7.66's criterion, END TO END, against a THROWAWAY DAEMON.
//
// ⚠ THE LIVE DAEMON IS NEVER TOUCHED, AND THAT IS THE POINT. This probe fabricates its own
// workspace root, data root, senders file, config (on a free port) and systemd USER UNIT under
// os.tmpdir(), starts a real `ignite/server/index.js` in it, and drives the real
// `rbtv-ignite-daemon restart` at THAT unit via `RBTV_IGNITE_UNIT` — the pattern `C1-standin`
// established for 7.67 (`daemon-operator` § v_selftest), inherited rather than re-derived.
// A daemon restart is the one act no seat on this box may perform on `rbtv-ignite.service`; this
// proves the flow without ever asking for it. The unit name is asserted to be the throwaway one
// before any lifecycle verb runs, so a mis-set env var refuses instead of reaching the live unit.
//
// WHAT IT PROVES — the criterion's exact words, "an operator changes tick_interval_ms through
// settings.json, the daemon restarts, and supervision resumes":
//
//   1. A daemon with no settings entry runs at the DEFAULT cadence, and says so at boot.
//   2. An edit WITHOUT --restart is written and NOT in effect: the running daemon keeps its old
//      cadence while settings.json holds the new one. The pending state is real, not a message.
//   3. An edit WITH --restart puts it in effect: the restarted daemon resolves the new cadence
//      FROM settings.json.
//   4. ⚠ SUPERVISION RESUMES, AND IT IS MEASURED BY BEHAVIOUR, NOT BY SELF-REPORT: ticks keep
//      firing after the restart, and the OBSERVED INTERVAL BETWEEN THEM MATCHES THE NEW CADENCE.
//      A daemon that merely printed the new number while still ticking on the old timer would
//      pass a self-report check and fail this one — that gap is where `p-green-harness` lives.
//
// Capture truncated at module load, BEFORE any work (D51). Exit code is the truth; the tally
// asserts its own completeness (`G-121`).

const fs = require('node:fs');
const os = require('node:os');
const net = require('node:net');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync, spawnSync } = require('node:child_process');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-ticker-cadence-flow.out');
fs.writeFileSync(outPath, '');

const IGNITE_ROOT = path.resolve(__dirname, '..', '..', '..');
const SERVER_ENTRY = path.join(IGNITE_ROOT, 'server', 'index.js');
const TICKER_TOOL = path.join(IGNITE_ROOT, 'capabilities', 'ticker-settings', 'tool', 'rbtv-ignite-ticker');
const DAEMON_TOOL = path.join(IGNITE_ROOT, 'capabilities', 'daemon-operator', 'tool', 'rbtv-ignite-daemon');
const UNIT = 'rbtv-ignite-tickerprobe.service';
const LIVE_UNIT = 'rbtv-ignite.service';

const EXPECTED_CHECKS = 18;

const checks = [];
let skipped = 0;
function out(...args) {
  const line = args.join(' ');
  fs.appendFileSync(outPath, line + '\n');
  console.log(line);
}
function check(name, pass, detail = '') {
  checks.push({ name, pass: !!pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? `  [${detail}]` : ''}`);
}
function sleep(ms) { execFileSync('sleep', [String(ms / 1000)]); }

// ⚠ HARD GUARD, checked before every lifecycle call rather than once at the top: this probe drives
// systemd, and the difference between its unit and the live one is a single string.
function assertThrowaway(unit) {
  if (unit !== UNIT || unit === LIVE_UNIT) {
    throw new Error(`REFUSING: lifecycle verb aimed at "${unit}", not the throwaway unit "${UNIT}"`);
  }
}

function sc(...args) {
  return spawnSync('systemctl', ['--user', ...args], { encoding: 'utf8' });
}

// A port the kernel hands out, taken SYNCHRONOUSLY in a child: `listen(0)` is asynchronous, so
// reading `address()` on the next line returns null. Asking the kernel beats guessing a range —
// this probe must not fail because something else already holds the port it picked.
function freePort() {
  const r = spawnSync(process.execPath, ['-e',
    "const s=require('node:net').createServer();s.listen(0,'127.0.0.1',()=>{console.log(s.address().port);s.close();});"],
    { encoding: 'utf8' });
  const p = Number((r.stdout || '').trim());
  if (!Number.isInteger(p) || p <= 0) throw new Error(`could not obtain a free port: ${r.stderr || r.stdout}`);
  return p;
}

// The daemon's own journal, as lines. This is what "the daemon says" means here — its real
// stdout under its real unit, never a value this probe handed it.
function journal(since) {
  const r = sc('--no-pager', '-n', '0', 'status', UNIT); // touch, keeps systemd warm
  void r;
  const j = spawnSync('journalctl', ['--user', '-u', UNIT, '--since', since, '-o', 'short-iso', '--no-pager'],
    { encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 });
  return (j.stdout || '').split('\n').filter(Boolean);
}

// The `ticker settings resolved` line the boot half emits — cadence AND its source.
function resolvedFromJournal(lines) {
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const m = /ticker settings resolved.*?"tick_interval_ms":(\d+).*?"source":"([a-z.]+)"/.exec(lines[i]);
    if (m) return { ms: Number(m[1]), source: m[2] };
    const m2 = /ticker settings resolved/.test(lines[i]) ? lines[i] : null;
    if (m2) return { raw: m2 };
  }
  return null;
}

// Timestamps of `tick N start` lines — the BEHAVIOURAL measurement.
function tickTimes(lines) {
  const ts = [];
  for (const l of lines) {
    if (!/tick \d+ start/.test(l)) continue;
    const m = /^(\S+)/.exec(l);
    if (m) { const t = Date.parse(m[1]); if (!Number.isNaN(t)) ts.push(t); }
  }
  return ts;
}

let root = null;
let unitFile = null;

function main() {
  // ── The throwaway world ─────────────────────────────────────────────────────────────────────
  root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-ticker-flow-'));
  const workspace = path.join(root, 'workspace');
  const dataRoot = path.join(root, 'state');
  const workdirRoot = path.join(root, 'work');
  for (const d of [path.join(workspace, '.rbtv', 'modules', 'ignite'), dataRoot, workdirRoot]) {
    fs.mkdirSync(d, { recursive: true });
  }

  // A throwaway sender registry: the startup gate refuses to boot without one (0600, non-empty,
  // at least one sender). The token is random, never printed, never messaged, and dies with the
  // temp dir — the owner's credential is not involved at any point.
  const sendersFile = path.join(root, 'senders.yaml');
  const hash = crypto.createHash('sha256').update(crypto.randomBytes(32).toString('hex')).digest('hex');
  fs.writeFileSync(sendersFile,
    `senders:\n  - sender-id: probe-owner\n    kind: owner\n    token-hash: ${hash}\n    enabled: true\n`);
  fs.chmodSync(sendersFile, 0o600);

  const port = freePort();
  const cfg = fs.readFileSync(path.join(IGNITE_ROOT, 'config', 'spawn-profiles.yaml'), 'utf8')
    .replace(/^(\s*)port: \d+/m, `$1port: ${port}`);
  const cfgPath = path.join(root, 'spawn-profiles.yaml');
  fs.writeFileSync(cfgPath, cfg);

  const unitDir = path.join(process.env.XDG_CONFIG_HOME || path.join(os.homedir(), '.config'), 'systemd', 'user');
  fs.mkdirSync(unitDir, { recursive: true });
  unitFile = path.join(unitDir, UNIT);
  fs.writeFileSync(unitFile,
`[Unit]
Description=THROWAWAY ignite daemon for probe-ticker-cadence-flow (task 7.66) — never the live unit
[Service]
Type=simple
ExecStart=${process.execPath} ${SERVER_ENTRY}
Environment=RBTV_IGNITE_WORKSPACE_ROOT=${workspace}
Environment=RBTV_IGNITE_DATA_ROOT=${dataRoot}
Environment=RBTV_IGNITE_WORKDIR_ROOT=${workdirRoot}
Environment=RBTV_IGNITE_CONFIG_PATH=${cfgPath}
Environment=RBTV_IGNITE_SENDERS_FILE=${sendersFile}
Environment=RBTV_IGNITE_TAILNET_ADDR=none
Environment=RBTV_IGNITE_SRC=${IGNITE_ROOT}
`);
  sc('daemon-reload');

  const env = {
    ...process.env,
    RBTV_IGNITE_WORKSPACE_ROOT: workspace,
    RBTV_IGNITE_UNIT: UNIT,
    RBTV_IGNITE_SETTLE_SECONDS: '3',
  };
  const ticker = (args) => {
    try {
      return { status: 0, stdout: execFileSync(TICKER_TOOL, args, { env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }) };
    } catch (err) { return { status: err.status ?? -1, stdout: err.stdout || '', stderr: err.stderr || '' }; }
  };
  const daemon = (verb) => {
    assertThrowaway(env.RBTV_IGNITE_UNIT);
    return spawnSync(DAEMON_TOOL, [verb], { env, encoding: 'utf8' });
  };

  // ── 1. Boot at the DEFAULT cadence ──────────────────────────────────────────────────────────
  const t0 = new Date(Date.now() - 2000).toISOString();
  const started = daemon('start');
  if (started.status !== 0) {
    out('the throwaway daemon did not start — SKIPPING the end-to-end legs rather than reporting them green');
    out((started.stdout || '') + (started.stderr || ''));
    out(journal(t0).slice(-25).join('\n'));
    skipped = EXPECTED_CHECKS;
    // A probe that cannot build its world must FAIL, never pass vacuously (`G-141` bar 2).
    check('the throwaway daemon starts (precondition for every leg below)', false,
      `exit=${started.status}`);
    return;
  }
  check('the throwaway daemon starts (precondition for every leg below)', true);
  sleep(3000);

  let lines = journal(t0);
  const r1 = resolvedFromJournal(lines);
  check('a daemon with NO settings entry resolves the DEFAULT cadence and names the source',
    r1 && r1.ms === 10000 && r1.source === 'default', JSON.stringify(r1));

  // ── 2. Edit WITHOUT --restart: written, NOT in effect ───────────────────────────────────────
  const e1 = ticker(['set-interval', '15s']);
  check('the edit is accepted and reports itself pending', e1.status === 0 && e1.stdout.includes('NOT IN EFFECT YET'),
    `exit=${e1.status}`);

  const S = require('../../../server/settings.js');
  check('settings.json now holds the new cadence',
    S.effectiveBlock(workspace, 'ticker').tick_interval_ms === 15000);

  // The running daemon is UNCHANGED — no reload happened, which is the ruled design (§ 2.3) and
  // not an omission. Measured from its own journal, which carries no second `resolved` line.
  const r2 = resolvedFromJournal(journal(t0));
  check('⚠ the RUNNING daemon still reports the OLD cadence — the edit is genuinely pending',
    r2 && r2.ms === 10000, JSON.stringify(r2));

  // ── 3. Edit WITH --restart: adopted ─────────────────────────────────────────────────────────
  // 5s is the floor — the lowest legal cadence, chosen so the behavioural measurement below
  // completes in seconds while still being a value the surface would accept from an operator.
  const tRestart = new Date(Date.now() - 1000).toISOString();
  const e2 = ticker(['set-interval', '5s', '--restart']);
  check('the --restart edit succeeds and says the cadence is in effect',
    e2.status === 0 && e2.stdout.includes('now in effect'), `exit=${e2.status}`);

  sleep(4000);
  const afterLines = journal(tRestart);
  const r3 = resolvedFromJournal(afterLines);
  check('the RESTARTED daemon resolves the new cadence FROM settings.json',
    r3 && r3.ms === 5000 && r3.source === 'settings.json', JSON.stringify(r3));

  const unitState = sc('show', UNIT, '--property=ActiveState,NRestarts');
  check('the unit is active after the restart', /ActiveState=active/.test(unitState.stdout || ''),
    (unitState.stdout || '').trim().replace(/\n/g, ' '));

  // ── 4. SUPERVISION RESUMES — measured by BEHAVIOUR ──────────────────────────────────────────
  // Observe long enough to see several ticks at 5s. The interval between them is the proof: a
  // daemon that adopted the value into its config but kept the OLD timer would pass every check
  // above and fail here, which is exactly the gap this leg exists to close.
  sleep(16000);
  const flowLines = journal(tRestart);
  const times = tickTimes(flowLines);
  check('ticks are still firing after the restart (supervision resumed)', times.length >= 3,
    `ticks observed=${times.length}`);

  const gaps = [];
  for (let i = 1; i < times.length; i += 1) gaps.push(times[i] - times[i - 1]);
  const median = gaps.length ? gaps.slice().sort((a, b) => a - b)[Math.floor(gaps.length / 2)] : null;
  check('⚠ the OBSERVED tick interval matches the NEW cadence, not the old one',
    median !== null && median >= 4000 && median <= 7000,
    `median gap=${median}ms over ${gaps.length} intervals; gaps=${gaps.join(',')}`);
  check('...and it is decisively NOT the 10s default it booted with',
    median !== null && median < 8000, `median=${median}ms`);

  // ── 4b. ⚠ THE WRONG-WORKSPACE DEFECT — regression, and it FAILS ON THE PRE-FIX RESOLVER ─────
  //
  // The first build resolved the workspace by walking up from cwd. The rbtv repo has its OWN
  // `.rbtv/`, so an operator editing the cadence from inside it wrote a settings file the live
  // daemon never reads — success reported, history appended, nothing changed. These two checks
  // exist because that shipped-and-was-caught, and both are RED on a plain walk-up resolver.
  {
    const decoy = path.join(root, 'decoy');
    fs.mkdirSync(path.join(decoy, '.rbtv'), { recursive: true });
    const noEnv = { ...process.env, RBTV_IGNITE_UNIT: UNIT };
    delete noEnv.RBTV_IGNITE_WORKSPACE_ROOT;
    const r = spawnSync(TICKER_TOOL, ['show'], { cwd: decoy, env: noEnv, encoding: 'utf8' });
    check('⚠ standing in a DIFFERENT .rbtv/ than the unit names, the surface REFUSES (exit 2)',
      r.status === 2 && /two different workspaces/.test(r.stderr || ''),
      `exit=${r.status}: ${(r.stderr || '').split('\n')[0]}`);
    check('...and the refusal NAMES both candidates, so the operator can pick',
      (r.stderr || '').includes(workspace) && (r.stderr || '').includes(decoy));
  }

  // ── 4c. ⚠ ENFORCEMENT POINT TWO, ON A REAL DAEMON START ──────────────────────────────────────
  //
  // The surface's refusal and the boot refusal are two halves, and proving each alone leaves the
  // SEAM untested — which is exactly the gap `G-124` was filed for. So this hand-edits a value
  // PAST the surface (as an operator with a text editor would) and observes the real unit refuse
  // to start, with the error naming the problem. Nothing here goes through the CLI.
  {
    const sp = S.settingsPaths(workspace).settingsPath;
    const good = fs.readFileSync(sp, 'utf8');
    const bad = JSON.parse(good);
    bad.machines[S.thisMachine()] = { ticker: { tick_interval_ms: 250 } }; // far below the 5000 floor
    fs.writeFileSync(sp, JSON.stringify(bad, null, 2));

    const tBad = new Date(Date.now() - 1000).toISOString();
    daemon('restart');
    sleep(3000);
    const st = sc('show', UNIT, '--property=ActiveState');
    check('⚠ a value hand-edited PAST the surface makes the real daemon REFUSE TO START',
      /ActiveState=(failed|activating|inactive)/.test(st.stdout || ''), (st.stdout || '').trim());
    const jb = journal(tBad).join('\n');
    check('...and the refusal NAMES the offending setting rather than dying anonymously',
      /is below the floor/.test(jb) && /REFUSES TO START/.test(jb),
      /is below the floor/.test(jb) ? 'named' : 'NOT named');

    // Put the world back so the legs below run against a healthy daemon.
    fs.writeFileSync(sp, good);
    sc('reset-failed', UNIT);
    daemon('start');
    sleep(3000);
    check('...and restoring a legal value lets it start again (the refusal is not sticky)',
      /ActiveState=active/.test((sc('show', UNIT, '--property=ActiveState').stdout || '')));
  }

  // ── 5. `inspect daemon` reports running vs configured (design § 2.1) ────────────────────────
  // Read through the module the handler uses, with the daemon's materialized value standing in
  // for `daemonConfig` — the field pair's arithmetic, exercised at both states.
  {
    const configured = S.effectiveBlock(workspace, 'ticker').tick_interval_ms;
    check('configured == running while nothing is pending', configured === 5000, `configured=${configured}`);
    S.setValue(workspace, { block: 'ticker', key: 'tick_interval_ms', value: 30000, by: 'probe' });
    const pending = S.effectiveBlock(workspace, 'ticker').tick_interval_ms;
    check('a fresh edit makes configured != running, which is what pending_restart reports',
      pending === 30000 && pending !== 5000, `configured=${pending}, running=5000`);
  }
}

try {
  main();
} catch (err) {
  out('ERROR:', err.message, err.stack);
  checks.push({ name: 'unhandled error', pass: false });
} finally {
  // Teardown is unconditional and aimed ONLY at the throwaway unit.
  try {
    if (unitFile) {
      sc('kill', '--signal=SIGKILL', UNIT);
      sc('stop', UNIT);
      sc('reset-failed', UNIT);
      fs.rmSync(unitFile, { force: true });
      sc('daemon-reload');
      out(`throwaway unit ${UNIT} removed`);
    }
  } catch (err) { out('teardown warning:', err.message); }
  try { if (root) fs.rmSync(root, { recursive: true, force: true }); } catch { /* tmp */ }
}

const failed = checks.filter((c) => !c.pass);
const complete = checks.length === EXPECTED_CHECKS;
out('');
out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
out(`SKIPPED_COUNT: ${skipped}`);
out(`COMPLETE: ${complete} (ran ${checks.length}, expected ${EXPECTED_CHECKS})`);
if (!complete) out('INCOMPLETE RUN — a short tally is a FAILURE however many checks passed (G-121)');
out(`CADENCE_FLOW_OK: ${failed.length === 0 && complete}`);
out(`EXIT: ${failed.length === 0 && complete ? 0 : 1}`);
out(`WALL_MS: ${Date.now() - start}`);
process.exitCode = (failed.length === 0 && complete) ? 0 : 1;
