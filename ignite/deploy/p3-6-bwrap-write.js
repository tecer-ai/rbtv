'use strict';

// p3-6-bwrap-write.js — the EXTENDED kernel-level containment probe (D59). Closes the gap the
// p3-5 probe proved open: on this box `systemd-run --user` enforces cgroup caps but its
// filesystem sandbox is a SILENT no-op, so a worker could write anywhere. The fix is bubblewrap
// (`bwrap`) nested INSIDE the transient unit — systemd keeps the cgroup caps + unit lifecycle;
// bwrap adds a mount namespace in which ONLY the session dir and the declared editable paths
// exist writable, and the vault, `.rbtv/heart/`, the rbtv source, and the user systemd bus are
// UNREACHABLE (not merely read-only — absent from the namespace).
//
// A trivial `bash` worker is launched through the daemon's OWN spawn path (the null-workdir /
// default branch), which now wraps argv in bwrap (spawn.js §4 site 1). The worker attempts
// writes/lookups in eight places; every leg is graded against REAL DISK or a typed error (D51:
// exit codes + disk are truth; worker log lines are hints only — an in-namespace write that
// "succeeds" lands on throwaway tmpfs and vanishes BY DESIGN, never chased).
//
//   (a) session dir           -> canary EXISTS on disk        (the ONE RW wall opening)
//   (b) declared test folder  -> canary EXISTS on disk        (editable path, bound back over HOME tmpfs)
//   (c) vault root            -> canary ABSENT on disk        (under HOME tmpfs, never bound)
//   (d) .rbtv/heart/ + heart.db -> canary ABSENT; heart.db ABSENT in-namespace (sibling, never bound)
//   (e) rbtv source tree      -> canary ABSENT; cat FAILS in-namespace (under /tmp tmpfs, never bound)
//   (f) user systemd bus      -> is-system-running FAILS; /run/user/<uid>/bus ABSENT (masked by /run tmpfs)
//   (g) bwrap-less box        -> spawn THROWS E_FS_SANDBOX_UNAVAILABLE; NO unit created (fail-closed)
//   (h) cgroup survival       -> unit memory.max == 134217728 (128M caps enforce THROUGH the wrap)
//
// No LLM, no cost, no API key — bash is the worker. The bwrap walls are unconditional code, not
// config, so this probe exercises the production wrap with zero profile edits.
//
// Writes deploy/p3-6-bwrap-write.out (instance paths scrubbed portable); exits 0/1.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');

const IGNITE_SRC = path.resolve(__dirname, '..');
const SOURCE_DIR = path.join(IGNITE_SRC, 'server', 'spawn');
// D26: no literal instance path/username. The vault is the workspace that roots `.rbtv/`; on the
// box it lives at $HOME/ht-wkdir/second-brain, so os.homedir() supplies the instance value. An
// explicit RBTV_IGNITE_WORKSPACE_ROOT overrides (the same knob index.js resolves the workspace by).
const VAULT_ROOT = process.env.RBTV_IGNITE_WORKSPACE_ROOT || path.join(os.homedir(), 'ht-wkdir', 'second-brain');
const TEST_FOLDER = path.join(VAULT_ROOT, '1-projects', 'rbtv-sb-merge-refactor-core-build', 'build', 'containment-test');
const REAL_HEART = path.join(VAULT_ROOT, '.rbtv', 'heart');
const OUT_PATH = path.join(__dirname, 'p3-6-bwrap-write.out');

const { openHeartStore, closeHeartStore } = require(path.join(IGNITE_SRC, 'server', 'heart', 'heart-store'));
const { createSpawnManager } = require(path.join(IGNITE_SRC, 'server', 'spawn', 'spawn'));
const { listSystemdUnits } = require(path.join(IGNITE_SRC, 'server', 'spawn', 'carrier'));
const { E_FS_SANDBOX_UNAVAILABLE } = require(path.join(IGNITE_SRC, 'server', 'spawn', 'errors'));

const lines = [];
const log = (s) => lines.push(s);
const now = () => new Date().toISOString();
function portable(p) {
  if (p == null) return p;
  const s = String(p);
  if (s.startsWith(IGNITE_SRC)) return '{IGNITE_SRC}' + s.slice(IGNITE_SRC.length);
  if (s.startsWith(VAULT_ROOT)) return '{VAULT}' + s.slice(VAULT_ROOT.length);
  const home = os.homedir();
  if (home && s.startsWith(home)) return '{HOME}' + s.slice(home.length);
  return s;
}
const checks = [];
function check(label, ok, detail) { checks.push({ label, ok }); log(`  [${ok ? 'PASS' : 'FAIL'}] ${label}${detail ? ' — ' + detail : ''}`); }

const TAG = `__p36_${process.pid}`;
const CANARIES = {
  session: `${TAG}_session`,
  test: path.join(TEST_FOLDER, `${TAG}_test`),
  vault: path.join(VAULT_ROOT, `${TAG}_vault`),
  heart: path.join(REAL_HEART, `${TAG}_heart`),
  source: path.join(SOURCE_DIR, `${TAG}_source`),
};

function sleepMs(ms) { const end = Date.now() + ms; while (Date.now() < end) { try { execFileSync('true'); } catch {} } }

// p3-2b's cgroup readback pattern: resolve the unit's cgroup, then read the kernel file. This is
// the claim that actually matters — systemd property readback reports a configured value even
// when the controller is not delegated; /sys/fs/cgroup is kernel enforcement.
function readCgroup(unit) {
  let cg;
  try {
    cg = execFileSync('systemctl', ['--user', 'show', unit, '-pControlGroup', '--value'], { encoding: 'utf8' }).trim();
  } catch { return {}; }
  if (!cg) return {};
  const base = path.join('/sys/fs/cgroup', cg);
  const read = (f) => { try { return fs.readFileSync(path.join(base, f), 'utf8').trim(); } catch { return null; } };
  return { cgroup: cg, 'memory.max': read('memory.max') };
}

async function main() {
  log('p3-6 bwrap filesystem-containment probe — bash worker through the daemon spawn path (bwrap walls in force)');
  log(`started: ${now()}`);
  log('command: node deploy/p3-6-bwrap-write.js');
  log(`bwrap:        ${execFileSync('bwrap', ['--version'], { encoding: 'utf8' }).trim()}`);
  log(`vault root:   ${portable(VAULT_ROOT)}`);
  log(`test folder:  ${portable(TEST_FOLDER)}`);
  log(`real heart:   ${portable(REAL_HEART)}`);
  log(`source dir:   ${portable(SOURCE_DIR)}`);

  if (!fs.existsSync(TEST_FOLDER)) {
    log(`FAIL: declared test folder missing: ${portable(TEST_FOLDER)}`);
    log('result: FAIL'); fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n'); process.exit(1);
  }

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p3-6-bw-'));
  const ws = path.join(tmp, 'ws');
  const dataRoot = path.join(tmp, 'data');
  fs.mkdirSync(ws, { recursive: true });
  fs.mkdirSync(dataRoot, { recursive: true });
  const sessionsRoot = path.join(ws, '.rbtv', 'sessions');

  // A benign bash worker that attempts the writes/lookups for legs (a)-(f) and reports each
  // outcome. These are HINTS; disk is truth (D51).
  const script = [
    'set +e',
    `touch "./${CANARIES.session}" 2>/dev/null && echo "A:WROTE" || echo "A:BLOCKED"`,
    `touch "${CANARIES.test}" 2>/dev/null && echo "B:WROTE" || echo "B:BLOCKED"`,
    `touch "${CANARIES.vault}" 2>/dev/null && echo "C:WROTE" || echo "C:BLOCKED"`,
    `touch "${CANARIES.heart}" 2>/dev/null && echo "D:WROTE" || echo "D:BLOCKED"`,
    `test -e "${path.join(REAL_HEART, 'heart.db')}" && echo "D:HEARTDB:PRESENT" || echo "D:HEARTDB:ABSENT"`,
    `touch "${CANARIES.source}" 2>/dev/null && echo "E:WROTE" || echo "E:BLOCKED"`,
    `cat "${path.join(SOURCE_DIR, 'spawn.js')}" 2>/dev/null >/dev/null && echo "E:CAT:OK" || echo "E:CAT:FAIL"`,
    `systemctl --user is-system-running >/dev/null 2>&1 && echo "F:SYSTEMD:REACHABLE" || echo "F:SYSTEMD:UNREACHABLE"`,
    `test -S /run/user/$(id -u)/bus && echo "F:BUS:PRESENT" || echo "F:BUS:ABSENT"`,
    'echo "DONE"',
    'sleep 3',
  ].join('; ');

  const profile = {
    exec: { argv: ['bash', '-c', script], prompt: 'stdin' },
    resume: { argv: ['bash', '-c', script], prompt: 'stdin' },
    session_ref: { source: 'cwd-implicit' },
    workdir_root: sessionsRoot,
    caps: { memory_max: '128M', runtime_max: '5m' },
    // The production sandbox shape, + the declared test folder (launch-time RW extension — never
    // committed to a production profile, keeping config machine-agnostic; D26(3)). The bwrap wrap
    // reads editablePaths from this; the systemd ReadWritePaths stays as defense in depth.
    sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}', TEST_FOLDER], PrivateTmp: true, NoNewPrivileges: true },
  };
  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(tmp, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'systemd', kill_grace_seconds: 2 },
    default_workdir_root: ws,
    profiles: { 'bwrap-write': profile },
  };
  const cfgPath = path.join(tmp, 'spawn.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const store = openHeartStore({ runtimeStateRoot: ws });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });

  let row;
  let cg = {};
  try {
    const fired = store.recordExecutionStart({
      jobId: 'launch-agent', actionType: 'launch-agent', args: '{}',
      enqueuedBy: 'p3-6-bw', sessionMode: 'headless', firedTick: 1, firedAt: new Date(),
      profile: 'bwrap-write', workdir: null,
    });
    row = await mgr.spawn(fired.exec_id, 'bwrap-write', 'headless', null, null, 'p3-6-bw');
    log(`spawned: unit=${row.unit_name} carrier=${row.carrier} sessionDir=${portable(row.workdir)}`);
    check('worker ran under systemd (cgroup caps + bwrap walls in force)', row.carrier === 'systemd');

    // Confirm the argv was wrapped (bwrap is argv[0]); a production-grade hint only.
    const wrapped = row.unit_name && execFileSync('systemctl', ['--user', 'show', row.unit_name, '-pExecStart', '--value'], { encoding: 'utf8' }).trim();
    log(`  unit ExecStart (hint): ${wrapped ? portable(wrapped).slice(0, 160) : '(unreadable)'}`);
    check('bwrap wraps the worker argv (argv[0] is bwrap)', !!wrapped && /bwrap/.test(wrapped), portable(wrapped || '').slice(0, 80));

    // Wait for the worker to perform its touches and log DONE.
    let logText = '';
    for (let i = 0; i < 40; i++) {
      sleepMs(200);
      try { logText = fs.readFileSync(row.log_path, 'utf8'); } catch { logText = ''; }
      if (/DONE/.test(logText)) break;
    }
    log('worker log (hint — disk is truth):');
    for (const l of logText.split('\n').filter(Boolean)) log(`  | ${l}`);

    // ---- leg (h): cgroup survival — read memory.max while the unit is still alive (post-DONE sleep) ----
    cg = readCgroup(row.unit_name);
    log(`cgroup readback: cgroup=${cg.cgroup || '(none)'} memory.max=${cg['memory.max']}`);

    // ---- disk truth (D51) ---- legs (a)-(e) ----
    const sessionCanary = path.join(row.workdir, CANARIES.session);
    const sessionExists = fs.existsSync(sessionCanary);
    const testExists = fs.existsSync(CANARIES.test);
    const vaultExists = fs.existsSync(CANARIES.vault);
    const heartExists = fs.existsSync(CANARIES.heart);
    const sourceExists = fs.existsSync(CANARIES.source);

    check('(a) session-dir write SUCCEEDED (canary on disk)', sessionExists, portable(sessionCanary));
    check('(b) declared-test-folder write SUCCEEDED (canary on disk)', testExists, portable(CANARIES.test));
    check('(c) vault-root write BLOCKED by bwrap (no canary on disk)', !vaultExists, portable(CANARIES.vault));
    check('(d) .rbtv/heart write BLOCKED by bwrap (no canary on disk)', !heartExists, portable(CANARIES.heart));
    const hintHeartDb = /D:HEARTDB:ABSENT/.test(logText);
    check('(d) heart.db ABSENT in-namespace (hint)', hintHeartDb, 'D:HEARTDB:ABSENT');
    check('(e) source-tree write BLOCKED by bwrap (no canary on disk)', !sourceExists, portable(CANARIES.source));
    const hintCat = /E:CAT:FAIL/.test(logText);
    check('(e) source-tree cat FAILED in-namespace (hint)', hintCat, 'E:CAT:FAIL');

    // ---- leg (f): user systemd bus masked ----
    const hintSystemdUnreachable = /F:SYSTEMD:UNREACHABLE/.test(logText);
    const hintBusAbsent = /F:BUS:ABSENT/.test(logText);
    check('(f) systemctl --user is-system-running FAILED in-namespace (hint)', hintSystemdUnreachable, 'F:SYSTEMD:UNREACHABLE');
    check('(f) /run/user/<uid>/bus ABSENT in-namespace (hint)', hintBusAbsent, 'F:BUS:ABSENT');

    // ---- leg (h): memory.max == 134217728 (128M caps enforce THROUGH the wrap) ----
    check('(h) cgroup memory.max ENFORCED through the wrap (128M == 134217728 bytes)', String(cg['memory.max']) === '134217728', `memory.max=${cg['memory.max']}`);
  } finally {
    try { if (row) await mgr.kill(row.exec_id); } catch {}
    // Clean up any canary that DID land (defensive — a landed vault/heart/source canary is a FAIL above).
    for (const p of [CANARIES.test, CANARIES.vault, CANARIES.heart, CANARIES.source]) { try { if (fs.existsSync(p)) fs.rmSync(p); } catch {} }
  }

  // ---- leg (g): bwrap-less box -> typed refusal, NO unit created ----
  let gErr = null;
  const savedPath = process.env.PATH;
  const beforeUnits = listSystemdUnits('rbtv-worker-').map((u) => u.unitName);
  try {
    const fired = store.recordExecutionStart({
      jobId: 'launch-agent', actionType: 'launch-agent', args: '{}',
      enqueuedBy: 'p3-6-bw', sessionMode: 'headless', firedTick: 2, firedAt: new Date(),
      profile: 'bwrap-write', workdir: null,
    });
    process.env.PATH = '/nonexistent';
    await mgr.spawn(fired.exec_id, 'bwrap-write', 'headless', null, null, 'p3-6-bw');
  } catch (e) {
    gErr = e;
  } finally {
    process.env.PATH = savedPath;
  }
  const afterUnits = listSystemdUnits('rbtv-worker-').map((u) => u.unitName);
  const newUnits = afterUnits.filter((u) => !beforeUnits.includes(u));
  log(`leg (g): thrown=${gErr ? `${gErr.code || gErr.name}: ${gErr.message}` : '(no throw)'}`);
  log(`leg (g): rbtv-worker units before=${beforeUnits.length} after=${afterUnits.length} new=${JSON.stringify(newUnits)}`);
  check('(g) spawn THREW SpawnError(E_FS_SANDBOX_UNAVAILABLE)', !!gErr && gErr.code === E_FS_SANDBOX_UNAVAILABLE, gErr ? String(gErr.code) : '(no throw)');
  check('(g) NO rbtv-worker unit created (fail-closed, no partial launch)', newUnits.length === 0, JSON.stringify(newUnits));

  try { closeHeartStore(); } catch {}
  try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}

  const failed = checks.filter((c) => !c.ok);
  log('');
  log(`checks: ${checks.length} total, ${checks.length - failed.length} passed, ${failed.length} failed`);
  if (failed.length) for (const c of failed) log(`  FAILED: ${c.label}`);
  log(`result: ${failed.length === 0 ? 'PASS' : 'FAIL'}`);
  return failed.length === 0 ? 0 : 1;
}

main()
  .then((code) => { log(`ended: ${now()}`); fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n'); process.exit(code); })
  .catch((err) => { log(`error: ${err.code || err.name}: ${err.message}`); log('result: FAIL'); log(`ended: ${now()}`); fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n'); process.exit(1); });
