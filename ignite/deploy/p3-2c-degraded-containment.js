'use strict';

// p3-2c-degraded-containment.js — re-runnable proof that a DEGRADED user manager still
// resolves the systemd carrier and keeps worker containment intact.
//
// Why this script exists (ADX-12 defect 2): `systemdAvailable()` used to treat `degraded`
// as unavailable, which made `carrier: auto` silently fall back to setsid and drop every
// cap/sandbox. A degraded manager still carries transient units perfectly well, so the
// carrier must stay systemd and the profile caps must still be enforced.
//
// The proof forces the degraded state by leaving one failed user unit, then runs the
// daemon's own spawn path for a sandboxed profile and reads a cap value back from the
// live transient unit. Capture is written to deploy/p3-2c-degraded-containment.out.
//
// Usage:  node deploy/p3-2c-degraded-containment.js
// Exits 0 (PASS) / 1 (FAIL). Needs no privilege.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');

const IGNITE_SRC = path.resolve(__dirname, '..');
const CONFIG_PATH = process.env.RBTV_IGNITE_CONFIG_PATH || path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml');
const OUT_PATH = path.join(__dirname, 'p3-2c-degraded-containment.out');
const FAIL_UNIT = 'rbtv-p3-2c-fail.service';

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

function userManagerState() {
  try {
    return execFileSync('systemctl', ['--user', 'is-system-running'], { encoding: 'utf8' }).trim();
  } catch (err) {
    return String(err.stdout || err.stderr || '').trim() || 'unavailable';
  }
}

function resetFailed(unit) {
  try { execFileSync('systemctl', ['--user', 'reset-failed', unit], { stdio: 'ignore' }); } catch {}
}

async function main() {
  log('p3-2c degraded-manager containment proof — carrier stays systemd, containment stays on');
  log(`started: ${now()}`);
  log('command: node deploy/p3-2c-degraded-containment.js');
  log(`config: ${portable(CONFIG_PATH)}`);
  log(`initial user manager state: ${userManagerState()}`);

  // --- force degraded state ---
  log('');
  log('=== forcing user manager degraded state ===');
  resetFailed(FAIL_UNIT);
  try {
    // Run WITHOUT --collect so the unit stays in the failed state and degrades the manager.
    execFileSync('systemd-run', ['--user', '--unit', FAIL_UNIT.replace(/\.service$/, ''), '/bin/false'], { encoding: 'utf8' });
  } catch (err) {
    // The unit is expected to fail; we only need it to leave a failed state behind.
    log(`failing unit exited as expected: ${err.stderr || err.stdout || '(no output)'}`.trim());
  }

  let degraded = false;
  for (let i = 0; i < 20; i++) {
    if (userManagerState() === 'degraded') { degraded = true; break; }
    await new Promise((r) => setTimeout(r, 100));
  }
  log(`user manager state after forcing failure: ${userManagerState()}`);
  if (!degraded) {
    throw new Error('failed to force user manager into degraded state');
  }

  // --- run containment proof through the daemon's own spawn path ---
  log('');
  log('=== spawning a sandboxed worker while degraded ===');

  const realCfg = yaml.load(fs.readFileSync(CONFIG_PATH, 'utf8'));
  log(`carrier under test: ${realCfg.spawn?.carrier || 'auto'}`);
  const profileName = 'codex-git-write';
  const realProfile = realCfg.profiles[profileName];
  if (!realProfile) throw new Error(`profile not found in ${portable(CONFIG_PATH)}: ${profileName}`);

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p3-2c-degraded-'));
  const dataRoot = path.join(tmp, 'data');
  const workRoot = path.join(tmp, 'work');
  fs.mkdirSync(dataRoot, { recursive: true });
  fs.mkdirSync(workRoot, { recursive: true });

  const testProfile = {
    ...realProfile,
    exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
    session_ref: { source: 'cwd-implicit' },
    workdir_root: workRoot,
  };
  delete testProfile.headed;

  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(tmp, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: realCfg.spawn?.carrier || 'auto', kill_grace_seconds: 2 },
    default_workdir_root: workRoot,
    profiles: { [profileName]: testProfile },
  };
  const cfgPath = path.join(tmp, 'spawn-profiles.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const store = openHeartStore({ dbPath: path.join(tmp, 'heart.db') });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });

  let row;
  let containmentOk = false;
  try {
    const fired = store.recordExecutionStart({
      jobId: 'launch-agent', actionType: 'launch-agent',
      args: JSON.stringify({ profile: profileName, workdir: null }),
      enqueuedBy: 'p3-2c-degraded-containment', sessionMode: 'headless',
      firedTick: 1, firedAt: new Date(), profile: profileName, workdir: null,
    });

    row = await mgr.spawn(fired.exec_id, profileName, 'headless', null, null, 'p3-2c-degraded-containment');
    log(`spawned via createSpawnManager().spawn(): carrier=${row.carrier} unit=${row.unit_name} workdir=${portable(row.workdir)}`);

    if (row.carrier !== 'systemd') {
      throw new Error(`carrier resolved to ${row.carrier}, not systemd — containment would be lost`);
    }

    // Prove the ReadWritePaths slot was resolved (defect 1) and the cap is enforced.
    const props = execFileSync('systemctl', ['--user', 'show', row.unit_name, '-pMemoryMax', '-pReadWritePaths', '--value'], { encoding: 'utf8' });
    const [memMax, rwPaths] = props.split('\n').map((l) => l.trim());
    const expectedMem = String(4 * 1024 ** 3);
    containmentOk = memMax === expectedMem && rwPaths.includes(row.workdir) && !/\{[a-z_]+\}/.test(rwPaths);

    log(`MemoryMax readback: ${memMax} (expected ${expectedMem})`);
    log(`ReadWritePaths readback: ${rwPaths}`);
    log(`containment intact under degraded manager: ${containmentOk ? 'PASS' : 'FAIL'}`);
  } finally {
    try { if (row) await mgr.kill(row.exec_id); } catch {}
    try { closeHeartStore(); } catch {}
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}
  }

  // --- cleanup failed unit and report ---
  resetFailed(FAIL_UNIT);
  log('');
  log(`user manager state after cleanup: ${userManagerState()}`);
  log(`forced degraded state held during spawn: ${degraded}`);
  log(`carrier resolved to systemd with containment intact: ${containmentOk}`);
  log(`result: ${containmentOk ? 'PASS' : 'FAIL'}`);
  log(`ended: ${now()}`);
  fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n', 'utf8');
  return containmentOk ? 0 : 1;
}

main()
  .then((code) => { process.exit(code); })
  .catch((err) => {
    log(`error: ${err.code || err.name}: ${err.message}`);
    log('result: FAIL');
    log(`ended: ${now()}`);
    try { fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n', 'utf8'); } catch {}
    resetFailed(FAIL_UNIT);
    process.exit(1);
  });
