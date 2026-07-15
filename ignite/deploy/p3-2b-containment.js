'use strict';

// p3-2b-containment.js — re-runnable proof that a worker spawned through the daemon's OWN
// spawn path lands in a `systemd-run --user` transient unit CARRYING ITS PROFILE'S CAPS.
//
// Why this script exists (D46 / ADX-11 item 4): worker containment is non-negotiable, and it
// exists ONLY on the systemd carrier — `setsid` accepts neither `caps:` nor `sandbox:`. An
// exit code or a spawn count proves nothing about containment; the cap VALUES must be read
// back off the live unit. This script does that, and is committed so the claim is
// independently re-runnable rather than a one-shot capture whose producer was deleted.
//
// It proves containment at TWO levels:
//   1. systemd property readback  — `systemctl --user show` : systemd ACCEPTED and RECORDED the cap.
//   2. kernel cgroup readback     — /sys/fs/cgroup/<unit>/{memory,cpu,pids}.max : the kernel ENFORCES it.
// Level 1 alone is weaker than it looks: systemd reports a configured property even when the
// controller is not delegated to the user manager. Level 2 is the claim that actually matters.
//
// The caps and sandbox under test are read VERBATIM from the committed production profile in
// config/spawn-profiles.yaml — never restated here, so the proof tracks the real profile and
// cannot drift from it. Only the profile's `exec.argv` is substituted (for a benign `sleep`)
// and its `workdir_root` redirected to a temp dir: the executor binary is irrelevant to cgroup
// containment, and invoking a real model in a proof script would be both slow and unsafe.
// That substitution is DISCLOSED in the capture rather than hidden.
//
// Usage:  node deploy/p3-2b-containment.js [profile-name]        (default: opencode-sakana)
//         node deploy/p3-2b-containment.js --all                 (every production profile)
// Writes deploy/p3-2b-containment.out and exits 0 (PASS) / 1 (FAIL).
// Needs no privilege: `systemd-run --user` is the whole point of D46.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');

const IGNITE_SRC = path.resolve(__dirname, '..');
const CONFIG_PATH = process.env.RBTV_IGNITE_CONFIG_PATH || path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml');
const OUT_PATH = path.join(__dirname, 'p3-2b-containment.out');

const { openHeartStore, closeHeartStore } = require(path.join(IGNITE_SRC, 'server', 'heart', 'heart-store'));
const { createSpawnManager } = require(path.join(IGNITE_SRC, 'server', 'spawn', 'spawn'));

const lines = [];
const log = (s) => { lines.push(s); };
const now = () => new Date().toISOString();

function portable(p) {
  if (p === undefined || p === null) return p;
  const s = String(p);
  if (s.startsWith(IGNITE_SRC)) return '{IGNITE_SRC}' + s.slice(IGNITE_SRC.length);
  const home = os.homedir();
  if (home && s.startsWith(home)) return '{HOME}' + s.slice(home.length);
  return s;
}

// ---------- expected-value derivation (from the profile's own words) ----------

function memToBytes(v) {
  const m = String(v).trim().match(/^(\d+(?:\.\d+)?)\s*([KMGT]?)i?B?$/i);
  if (!m) return null;
  const mult = { '': 1, K: 1024, M: 1024 ** 2, G: 1024 ** 3, T: 1024 ** 4 }[m[2].toUpperCase()];
  return Math.round(parseFloat(m[1]) * mult);
}

// systemd timespans: "8h", "6h", "30s", "1min 30s", "1.500000s", "infinity".
function timespanToUsec(v) {
  const s = String(v).trim();
  if (s === 'infinity') return Infinity;
  const unit = { us: 1, ms: 1e3, s: 1e6, sec: 1e6, seconds: 1e6, min: 60e6, m: 60e6, h: 3600e6, hr: 3600e6, d: 86400e6 };
  const re = /(\d+(?:\.\d+)?)\s*(us|ms|sec|seconds|min|hr|[smhd])/g;
  let total = 0; let hit = false; let m;
  while ((m = re.exec(s)) !== null) { hit = true; total += parseFloat(m[1]) * unit[m[2]]; }
  if (!hit) { const n = parseFloat(s); return Number.isNaN(n) ? null : n * 1e6; }
  return Math.round(total);
}

function cpuQuotaToUsecPerSec(v) {
  const m = String(v).trim().match(/^(\d+(?:\.\d+)?)\s*%$/);
  return m ? Math.round(parseFloat(m[1]) / 100 * 1e6) : null;
}

// ---------- readback ----------

function showProps(unit, props) {
  const out = execFileSync('systemctl', ['--user', 'show', unit, ...props.map((p) => `-p${p}`)], { encoding: 'utf8' });
  const kv = {};
  for (const l of out.split('\n')) {
    const i = l.indexOf('=');
    if (i > 0) kv[l.slice(0, i)] = l.slice(i + 1);
  }
  return kv;
}

function readCgroup(unit) {
  let cg;
  try {
    cg = execFileSync('systemctl', ['--user', 'show', unit, '-pControlGroup', '--value'], { encoding: 'utf8' }).trim();
  } catch { return {}; }
  if (!cg) return {};
  const base = path.join('/sys/fs/cgroup', cg);
  const read = (f) => { try { return fs.readFileSync(path.join(base, f), 'utf8').trim(); } catch { return null; } };
  return { cgroup: cg, 'memory.max': read('memory.max'), 'cpu.max': read('cpu.max'), 'pids.max': read('pids.max') };
}

// ---------- the proof ----------

const checks = [];
function check(label, actual, expected, ok) {
  checks.push({ label, actual, expected, ok });
  log(`  [${ok ? 'MATCH' : 'MISMATCH'}] ${label}: actual=${actual} expected=${expected}`);
  return ok;
}

async function proveProfile(profileName, realCfg) {
  const realProfile = realCfg.profiles[profileName];
  if (!realProfile) throw new Error(`profile not found in ${portable(CONFIG_PATH)}: ${profileName}`);
  if (!realProfile.caps) throw new Error(`profile ${profileName} declares no caps: — nothing to contain`);

  log('');
  log(`=== profile under test: ${profileName} (read from ${portable(CONFIG_PATH)}) ===`);
  log(`committed caps:    ${JSON.stringify(realProfile.caps)}`);
  log(`committed sandbox: ${JSON.stringify(realProfile.sandbox || null)}`);
  log(`committed argv:    ${JSON.stringify(realProfile.exec.argv)}`);
  log('SUBSTITUTION (disclosed): exec.argv -> ["sleep","3600"], workdir_root -> temp dir.');
  log('  caps: and sandbox: are used VERBATIM as committed — they are what is under test.');

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p3-2b-containment-'));
  const dataRoot = path.join(tmp, 'data');
  const workRoot = path.join(tmp, 'work');
  fs.mkdirSync(dataRoot, { recursive: true });
  fs.mkdirSync(workRoot, { recursive: true });

  const testProfile = {
    ...realProfile,
    exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
    resume: { argv: ['sleep', '3600'], prompt: 'stdin' },
    session_ref: { source: 'cwd-implicit' },
    workdir_root: workRoot,
  };
  delete testProfile.headed;

  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(tmp, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'auto', kill_grace_seconds: 2 },
    default_workdir_root: workRoot,
    profiles: { [profileName]: testProfile },
  };
  const cfgPath = path.join(tmp, 'spawn-profiles.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const store = openHeartStore({ dbPath: path.join(tmp, 'heart.db') });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });

  let row;
  try {
    const fired = store.recordExecutionStart({
      jobId: 'launch-agent', actionType: 'launch-agent',
      args: JSON.stringify({ profile: profileName, workdir: null }),
      enqueuedBy: 'p3-2b-containment', sessionMode: 'headless',
      firedTick: 1, firedAt: new Date(), profile: profileName, workdir: null,
    });

    // The daemon's OWN spawn path — not a hand-rolled systemd-run.
    row = await mgr.spawn(fired.exec_id, profileName, 'headless', null, null, 'p3-2b-containment');
    log(`spawned via createSpawnManager().spawn(): carrier=${row.carrier} unit=${row.unit_name} pid=${row.pid} status=${row.status}`);

    if (row.carrier !== 'systemd') throw new Error(`carrier resolved to ${row.carrier}, not systemd — containment absent`);
    check('carrier is systemd', row.carrier, 'systemd', true);

    const active = execFileSync('systemctl', ['--user', 'is-active', row.unit_name], { encoding: 'utf8' }).trim();
    check('unit is-active', active, 'active', active === 'active');

    // ---- level 1: systemd property readback ----
    const props = showProps(row.unit_name, [
      'MemoryMax', 'CPUQuotaPerSecUSec', 'RuntimeMaxUSec', 'TasksMax',
      'ProtectSystem', 'PrivateTmp', 'NoNewPrivileges', 'ReadWritePaths',
    ]);
    log('systemd property readback (systemctl --user show):');
    for (const [k, v] of Object.entries(props)) log(`  ${k}=${v}`);

    const caps = realProfile.caps;
    if (caps.memory_max !== undefined) {
      const exp = memToBytes(caps.memory_max);
      check(`MemoryMax (profile memory_max=${caps.memory_max})`, props.MemoryMax, exp, String(props.MemoryMax) === String(exp));
    }
    if (caps.cpu_quota !== undefined) {
      const exp = cpuQuotaToUsecPerSec(caps.cpu_quota);
      const act = timespanToUsec(props.CPUQuotaPerSecUSec);
      check(`CPUQuotaPerSecUSec (profile cpu_quota=${caps.cpu_quota})`, `${props.CPUQuotaPerSecUSec} (${act}us)`, `${exp}us`, act === exp);
    }
    if (caps.runtime_max !== undefined) {
      const exp = timespanToUsec(caps.runtime_max);
      const act = timespanToUsec(props.RuntimeMaxUSec);
      check(`RuntimeMaxUSec (profile runtime_max=${caps.runtime_max})`, `${props.RuntimeMaxUSec} (${act}us)`, `${exp}us`, act === exp);
    }
    if (caps.tasks_max !== undefined) {
      check(`TasksMax (profile tasks_max=${caps.tasks_max})`, props.TasksMax, String(caps.tasks_max), String(props.TasksMax) === String(caps.tasks_max));
    }

    // ---- level 2: kernel cgroup readback — the claim that actually matters ----
    const cg = readCgroup(row.unit_name);
    log('kernel cgroup readback (/sys/fs/cgroup):');
    for (const [k, v] of Object.entries(cg)) log(`  ${k}=${v}`);

    if (caps.memory_max !== undefined) {
      const exp = memToBytes(caps.memory_max);
      check(`cgroup memory.max ENFORCED`, cg['memory.max'], exp, String(cg['memory.max']) === String(exp));
    }
    if (caps.cpu_quota !== undefined) {
      const pct = parseFloat(String(caps.cpu_quota));
      const parts = (cg['cpu.max'] || '').split(/\s+/);
      const actPct = parts.length === 2 && parts[0] !== 'max' ? (Number(parts[0]) / Number(parts[1])) * 100 : null;
      check(`cgroup cpu.max ENFORCED`, `${cg['cpu.max']} (${actPct}%)`, `${pct}%`, actPct === pct);
    }
    if (caps.tasks_max !== undefined) {
      check(`cgroup pids.max ENFORCED`, cg['pids.max'], String(caps.tasks_max), String(cg['pids.max']) === String(caps.tasks_max));
    }

    // ---- sandbox: reported, and slot-resolution audited ----
    if (realProfile.sandbox) {
      log('sandbox block audit:');
      const rwp = realProfile.sandbox.ReadWritePaths;
      if (rwp) {
        const declared = Array.isArray(rwp) ? rwp : [rwp];
        const declaredSlots = declared.filter((p) => /\{[a-z_]+\}/.test(p));
        const live = props.ReadWritePaths || '';
        log(`  profile declares ReadWritePaths=${JSON.stringify(declared)}`);
        log(`  live unit reports  ReadWritePaths=${live}`);
        // Report whether the profile actually declares a slot: if it declares none, the
        // resolution check below is vacuous and must not be read as proof of resolution.
        log(`  slots declared in profile: ${declaredSlots.length ? JSON.stringify(declaredSlots) : '(NONE — slot resolution is not exercised by this profile)'}`);
        // Grade BOTH halves of the label. `live.includes(workdir)` alone would pass a value
        // that still carried a literal `{slot}` next to the resolved path.
        const liveHasSlot = /\{[a-z_]+\}/.test(live);
        check(
          'ReadWritePaths template slots resolved to the real workdir',
          live, `must contain ${row.workdir} and no {slot}`,
          live.includes(row.workdir) && !liveHasSlot,
        );
      }
    }
  } finally {
    try { if (row) await mgr.kill(row.exec_id); } catch {}
    try { closeHeartStore(); } catch {}
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}
  }
}

async function main() {
  log('p3-2b containment proof — worker containment through the daemon\'s own spawn path');
  log(`started: ${now()}`);
  log(`command: node deploy/p3-2b-containment.js ${process.argv.slice(2).join(' ')}`.trim());
  log(`config:  ${portable(CONFIG_PATH)}`);
  log(`host systemd: ${execFileSync('systemctl', ['--version'], { encoding: 'utf8' }).split('\n')[0]}`);
  log(`user manager delegated controllers: ${(() => {
    try { return execFileSync('systemctl', ['show', `user@${process.getuid()}.service`, '-pDelegateControllers', '--value'], { encoding: 'utf8' }).trim() || '(none reported)'; } catch { return '(unreadable)'; }
  })()}`);

  const realCfg = yaml.load(fs.readFileSync(CONFIG_PATH, 'utf8'));
  const arg = process.argv[2];
  const targets = arg === '--all'
    ? Object.keys(realCfg.profiles).filter((p) => realCfg.profiles[p].caps)
    : [arg || 'opencode-sakana'];

  // A profile that cannot even spawn is a containment FAILURE, not a reason to abort the
  // suite: the remaining profiles still have to be reported.
  for (const p of targets) {
    try {
      await proveProfile(p, realCfg);
    } catch (err) {
      log(`  [FAILED] ${p}: ${err.code || err.name}: ${err.message}`);
      checks.push({ label: `${p}: spawns and carries its caps`, actual: `${err.code || err.name}: ${err.message}`, expected: 'spawn succeeds, caps readback matches', ok: false });
    }
  }

  const failed = checks.filter((c) => !c.ok);
  log('');
  log(`checks: ${checks.length} total, ${checks.length - failed.length} matched, ${failed.length} mismatched`);
  if (failed.length) for (const f of failed) log(`  MISMATCH: ${f.label} (actual=${f.actual} expected=${f.expected})`);
  log(`result: ${failed.length === 0 ? 'PASS' : 'FAIL'}`);
  return failed.length === 0 ? 0 : 1;
}

main()
  .then((code) => { log(`ended: ${now()}`); fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n', 'utf8'); process.exit(code); })
  .catch((err) => {
    log(`error: ${err.code || err.name}: ${err.message}`);
    log('result: FAIL');
    log(`ended: ${now()}`);
    fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n', 'utf8');
    process.exit(1);
  });
