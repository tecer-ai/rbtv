'use strict';

// p3-2b-carrier-warning.js — re-runnable proof that the daemon's boot-time carrier warning
// GENUINELY FIRES when the resolved carrier is not the systemd user manager.
//
// Why this script exists (D46 / ADX-11 item 3): worker containment (`caps:`/`sandbox:`) exists
// ONLY on the systemd carrier. Under `carrier: auto` an unreachable user manager degrades to
// setsid, which accepts neither — every profile's confinement silently evaporates. A SILENT
// degradation is the defect this round exists to close, so the warning must be proven to fire
// under the real condition, not asserted by a comment.
//
// It boots the REAL entry point (server/index.js --smoke-test) as a child process under five
// carriage scenarios and asserts on the daemon's own structured log lines:
//
//   1. healthy        — user manager reachable, carrier auto   -> resolves systemd, NO warning
//   2. manager-unreachable (THE auto hazard) — XDG_RUNTIME_DIR and DBUS_SESSION_BUS_ADDRESS stripped
//                       so `systemctl --user` cannot connect, carrier auto -> degrades to setsid
//                       -> the warning MUST fire
//   3. carrier-setsid — operator pins RBTV_IGNITE_CARRIER=setsid -> the warning MUST fire
//   4. user-manager-off — RBTV_IGNITE_USER_MANAGER=false -> the warning MUST fire
//   5. pin systemd, manager unreachable (D48) — config carrier is systemd, user bus stripped
//                       -> daemon MUST fail to boot with E_SYSTEMD_NOT_AVAILABLE and MUST NOT
//                       silently produce a setsid worker.
//
// Scenarios 1-4 exercise `carrier: auto` via the RBTV_IGNITE_CARRIER env override so their
// documented behavior stays correct even though the committed config is now pinned to systemd.
// Scenario 2 is the load-bearing auto hazard: it reproduces the actual silent-degradation
// condition rather than a flag that merely announces it.
// Scenario 5 is the load-bearing D48 pin proof: a pinned carrier with no manager refuses to run.
//
// Usage:  node deploy/p3-2b-carrier-warning.js
// Writes deploy/p3-2b-carrier-warning.out and exits 0 (PASS) / 1 (FAIL). Needs no privilege.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawnSync } = require('node:child_process');

const IGNITE_SRC = path.resolve(__dirname, '..');
const ENTRY = path.join(IGNITE_SRC, 'server', 'index.js');
const CONFIG_PATH = process.env.RBTV_IGNITE_CONFIG_PATH || path.join(IGNITE_SRC, 'config', 'spawn-profiles.yaml');
const OUT_PATH = path.join(__dirname, 'p3-2b-carrier-warning.out');

const WARN_MESSAGE_MATCH = 'carrier degraded';

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

function scrub(s) {
  if (typeof s !== 'string') return s;
  let out = s;
  if (IGNITE_SRC) out = out.split(IGNITE_SRC).join('{IGNITE_SRC}');
  const home = os.homedir();
  if (home) out = out.split(home).join('{HOME}');
  return out;
}

const results = [];

function bootDaemon({ name, stripUserBus = false, extraEnv = {} }) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p3-2b-warn-'));
  const workspaceRoot = path.join(tmp, 'workspace');
  const workRoot = path.join(tmp, 'work');
  const dataRoot = path.join(tmp, 'data');
  for (const d of [workspaceRoot, workRoot, dataRoot]) fs.mkdirSync(d, { recursive: true });

  const env = {
    ...process.env,
    RBTV_IGNITE_SRC: IGNITE_SRC,
    RBTV_IGNITE_WORKSPACE_ROOT: workspaceRoot,
    RBTV_IGNITE_CONFIG_PATH: CONFIG_PATH,
    RBTV_IGNITE_WORKDIR_ROOT: workRoot,
    RBTV_IGNITE_DATA_ROOT: dataRoot,
    ...extraEnv,
  };
  // Reproduce the real hazard: with no user bus, `systemctl --user` cannot connect, so the
  // daemon's own availability probe fails exactly as it would on a box whose user manager
  // is not reachable — no simulation, no stub.
  if (stripUserBus) {
    delete env.XDG_RUNTIME_DIR;
    delete env.DBUS_SESSION_BUS_ADDRESS;
  }

  const started = Date.now();
  const proc = spawnSync(process.execPath, [ENTRY, '--smoke-test'], { env, encoding: 'utf8', timeout: 60000 });
  const wallMs = Date.now() - started;
  try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}

  const stdout = proc.stdout || '';
  const parsed = stdout.split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
  return { name, exit: proc.status, wallMs, stdout, stderr: proc.stderr || '', parsed };
}

function assertScenario({ name, stripUserBus, extraEnv, expectResolved, expectWarning }) {
  log('');
  log(`=== scenario: ${name} ===`);
  log(`  expect: resolvedCarrier=${expectResolved}, warning ${expectWarning ? 'FIRES' : 'does NOT fire'}`);

  const r = bootDaemon({ name, stripUserBus, extraEnv });
  const carriage = r.parsed.find((l) => l.message === 'spawn carriage');
  const warning = r.parsed.find((l) => l.level === 'warn' && String(l.message).includes(WARN_MESSAGE_MATCH));

  log(`  boot exit: ${r.exit} (wall_ms=${r.wallMs})`);
  if (carriage) {
    log(`  daemon reported: configuredCarrier=${carriage.configuredCarrier} resolvedCarrier=${carriage.resolvedCarrier} userManager=${carriage.userManager}`);
  } else {
    log('  daemon reported: NO "spawn carriage" line found');
  }
  log(`  warning line: ${warning ? JSON.stringify(warning, (k, v) => typeof v === 'string' ? scrub(v) : v) : '(none)'}`);

  const okBoot = r.exit === 0;
  const okResolved = carriage ? carriage.resolvedCarrier === expectResolved : false;
  const okWarning = expectWarning ? Boolean(warning) : !warning;

  for (const [label, ok] of [
    ['daemon booted and shut down cleanly (exit 0)', okBoot],
    [`resolvedCarrier is ${expectResolved}`, okResolved],
    [expectWarning ? 'degradation warning FIRED' : 'no spurious warning', okWarning],
  ]) {
    log(`  [${ok ? 'PASS' : 'FAIL'}] ${label}`);
    results.push({ scenario: name, label, ok });
  }

  if (!okBoot) log(`  stderr: ${r.stderr.split('\n').slice(0, 4).join(' | ')}`);
}

function assertPinHardFail({ name, stripUserBus, extraEnv }) {
  log('');
  log(`=== scenario: ${name} ===`);
  log('  expect: daemon fails to boot with E_SYSTEMD_NOT_AVAILABLE, no setsid worker produced');

  const r = bootDaemon({ name, stripUserBus, extraEnv });
  const carriage = r.parsed.find((l) => l.message === 'spawn carriage');
  const errorLine = r.parsed.find((l) => l.level === 'error' && l.message === 'daemon failed to start');
  const errorMessage = errorLine && errorLine.error ? String(errorLine.error) : '';
  const expectedMessage = 'systemd carrier requested but user manager is not available';
  const identityOk = errorMessage.includes(expectedMessage);
  const setsidSpawn = r.parsed.find((l) => l.message === 'setsid spawn');

  log(`  boot exit: ${r.exit} (wall_ms=${r.wallMs})`);
  log(`  error line: ${errorLine ? JSON.stringify(errorLine, (k, v) => typeof v === 'string' ? scrub(v) : v) : '(none)'}`);
  if (carriage) log(`  UNEXPECTED spawn carriage: ${JSON.stringify(carriage, (k, v) => typeof v === 'string' ? scrub(v) : v)}`);
  if (setsidSpawn) log(`  UNEXPECTED setsid spawn: ${JSON.stringify(setsidSpawn, (k, v) => typeof v === 'string' ? scrub(v) : v)}`);

  const okFail = r.exit !== 0;
  const okIdentity = identityOk;
  const okNoCarriage = !carriage;
  const okNoSetsid = !setsidSpawn;

  for (const [label, ok] of [
    ['daemon fails to boot (non-zero exit)', okFail],
    ['error identity is E_SYSTEMD_NOT_AVAILABLE (unique message)', okIdentity],
    ['no spawn carriage line produced', okNoCarriage],
    ['no setsid worker produced', okNoSetsid],
  ]) {
    log(`  [${ok ? 'PASS' : 'FAIL'}] ${label}`);
    results.push({ scenario: name, label, ok });
  }

  if (!okFail) log(`  stderr: ${r.stderr.split('\n').slice(0, 4).join(' | ')}`);
}

function main() {
  log('p3-2b carrier-degradation warning proof — does the boot-time warning actually fire?');
  log(`started: ${now()}`);
  log('command: node deploy/p3-2b-carrier-warning.js');
  log(`entry point: ${portable(ENTRY)}`);
  log(`config: ${portable(CONFIG_PATH)}`);
  log(`warning matched on: level=warn AND message contains "${WARN_MESSAGE_MATCH}"`);

  // 1. The healthy path must stay quiet — a warning that always fires teaches operators to
  //    ignore it, which is the same failure as no warning at all. Force carrier=auto so this
  //    scenario keeps testing auto's documented behavior even though the committed config is
  //    now pinned to systemd.
  assertScenario({ name: 'healthy (user manager reachable, carrier auto)', stripUserBus: false, extraEnv: { RBTV_IGNITE_CARRIER: 'auto' }, expectResolved: 'systemd', expectWarning: false });

  // 2. THE AUTO HAZARD: the real silent-degradation condition D46 exists to make visible.
  //    Force carrier=auto so auto's degrade-to-setsid behavior stays exercised and verified.
  assertScenario({ name: 'manager-unreachable (no user bus, carrier auto) — THE D46 HAZARD', stripUserBus: true, extraEnv: { RBTV_IGNITE_CARRIER: 'auto' }, expectResolved: 'setsid', expectWarning: true });

  // 3. Operator explicitly pins setsid — containment is off; say so.
  assertScenario({ name: 'carrier pinned to setsid', stripUserBus: false, extraEnv: { RBTV_IGNITE_CARRIER: 'setsid' }, expectResolved: 'setsid', expectWarning: true });

  // 4. userManager=false — carriage would target the SYSTEM manager, which an unprivileged
  //    daemon cannot drive; the warning must fire even though systemd resolves.
  assertScenario({ name: 'RBTV_IGNITE_USER_MANAGER=false', stripUserBus: false, extraEnv: { RBTV_IGNITE_USER_MANAGER: 'false' }, expectResolved: 'systemd', expectWarning: true });

  // 5. THE PIN (D48): with carrier pinned to systemd in the committed config and the user
  //    manager genuinely unreachable, the daemon must fail to boot with E_SYSTEMD_NOT_AVAILABLE
  //    and must NOT silently fall back to a setsid worker.
  assertPinHardFail({ name: 'pin systemd, manager unreachable (D48 hard-fail)', stripUserBus: true, extraEnv: {} });

  const failed = results.filter((r) => !r.ok);
  log('');
  log(`checks: ${results.length} total, ${results.length - failed.length} passed, ${failed.length} failed`);
  for (const f of failed) log(`  FAIL: [${f.scenario}] ${f.label}`);
  log(`result: ${failed.length === 0 ? 'PASS' : 'FAIL'}`);
  log(`ended: ${now()}`);
  fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n', 'utf8');
  return failed.length === 0 ? 0 : 1;
}

process.exit(main());
