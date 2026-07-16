'use strict';

// p3-5-mutation.js — the MUTATION-SHAPED proof that the D56 fail-open is CLOSED, not merely
// untraveled. D58(2): the null-workdir (default/ticker) branch of resolveWorkdir() now passes the
// SAME fail-closed containment check as the caller branch — the resolved session dir must sit
// INSIDE the profile's workdir_root or the spawn REFUSES (E_WORKDIR_ESCAPE). This script drives
// TWO legs through the daemon's OWN spawn path (no hand-rolled resolver):
//   ALIGNED  — sessions root == workdir_root (production shape): a null-workdir spawn lands in
//              .rbtv/sessions/<exec-id>/ and is CONTAINED.
//   ESCAPING — workdir_root points OUTSIDE the derived sessions root (a deliberate divergence a
//              misconfiguration or a regression would cause): a null-workdir spawn must REFUSE
//              with E_WORKDIR_ESCAPE and NEVER run. This is the leg that proves the guard fires.
// The sessions root is derived from the store's own `.rbtv/` — independent of workdir_root — so
// the ESCAPING leg is a REAL divergence the check must catch, not a vacuous one it cannot.
//
// Writes deploy/p3-5-mutation.out; exits 0 (both legs as required) / 1 (any leg wrong).

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const yaml = require('js-yaml');

const IGNITE_SRC = path.resolve(__dirname, '..');
const OUT_PATH = path.join(__dirname, 'p3-5-mutation.out');
const { openHeartStore, closeHeartStore } = require(path.join(IGNITE_SRC, 'server', 'heart', 'heart-store'));
const { createSpawnManager } = require(path.join(IGNITE_SRC, 'server', 'spawn', 'spawn'));

const lines = [];
const log = (s) => lines.push(s);
const now = () => new Date().toISOString();
function portable(p) {
  if (p == null) return p;
  const s = String(p);
  const home = os.homedir();
  if (s.startsWith(IGNITE_SRC)) return '{IGNITE_SRC}' + s.slice(IGNITE_SRC.length);
  if (home && s.startsWith(home)) return '{HOME}' + s.slice(home.length);
  return s;
}
const checks = [];
function check(label, ok, detail) { checks.push({ label, ok }); log(`  [${ok ? 'PASS' : 'FAIL'}] ${label}${detail ? ' — ' + detail : ''}`); }

const PROFILE = {
  exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
  resume: { argv: ['sleep', '3600'], prompt: 'stdin' },
  session_ref: { source: 'cwd-implicit' },
  caps: { memory_max: '64M', runtime_max: '1h' },
  sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
};

function buildMgr(tmp, workdirRoot) {
  const ws = path.join(tmp, 'ws');
  const dataRoot = path.join(tmp, 'data');
  fs.mkdirSync(ws, { recursive: true });
  fs.mkdirSync(dataRoot, { recursive: true });
  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(tmp, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'systemd', kill_grace_seconds: 2 },
    default_workdir_root: ws,
    profiles: { 'test-sleep': { ...PROFILE, workdir_root: workdirRoot } },
  };
  const cfgPath = path.join(tmp, 'spawn.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));
  // Store at the workspace root → sessions root derives to <ws>/.rbtv/sessions.
  const store = openHeartStore({ runtimeStateRoot: ws });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });
  return { ws, store, mgr, sessionsRoot: path.join(ws, '.rbtv', 'sessions') };
}

async function legAligned() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p3-5-mut-aligned-'));
  log('');
  log('=== LEG 1: ALIGNED (workdir_root == derived sessions root) — must CONTAIN ===');
  let ctx, row;
  try {
    // workdir_root set to the sessions root the store will derive.
    ctx = buildMgr(tmp, path.join(tmp, 'ws', '.rbtv', 'sessions'));
    const fired = ctx.store.recordExecutionStart({
      jobId: 'launch-agent', actionType: 'launch-agent', args: '{}',
      enqueuedBy: 'p3-5-mut', sessionMode: 'headless', firedTick: 1, firedAt: new Date(),
      profile: 'test-sleep', workdir: null,
    });
    row = await ctx.mgr.spawn(fired.exec_id, 'test-sleep', 'headless', null, null, 'p3-5-mut');
    const expected = fs.realpathSync(path.join(ctx.sessionsRoot, String(fired.exec_id)));
    log(`  spawned: workdir=${portable(row.workdir)} status=${row.status}`);
    check('aligned null-workdir spawn RUNS and is contained in .rbtv/sessions/<exec-id>',
      row.status === 'running' && row.workdir === expected, portable(row.workdir));
  } finally {
    try { if (row) await ctx.mgr.kill(row.exec_id); } catch {}
    try { closeHeartStore(); } catch {}
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}
  }
}

async function legEscaping() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p3-5-mut-escape-'));
  log('');
  log('=== LEG 2: ESCAPING (workdir_root OUTSIDE the derived sessions root) — must REFUSE ===');
  let ctx, thrown = null, ranRow = null;
  try {
    const allowed = path.join(tmp, 'allowed');   // a real, existing boundary that is NOT the sessions root
    fs.mkdirSync(allowed, { recursive: true });
    ctx = buildMgr(tmp, allowed);
    log(`  workdir_root=${portable(allowed)}  derived sessions root=${portable(ctx.sessionsRoot)} (divergent)`);
    const fired = ctx.store.recordExecutionStart({
      jobId: 'launch-agent', actionType: 'launch-agent', args: '{}',
      enqueuedBy: 'p3-5-mut', sessionMode: 'headless', firedTick: 1, firedAt: new Date(),
      profile: 'test-sleep', workdir: null,
    });
    try {
      ranRow = await ctx.mgr.spawn(fired.exec_id, 'test-sleep', 'headless', null, null, 'p3-5-mut');
    } catch (err) {
      thrown = err;
    }
    log(`  spawn outcome: ${thrown ? (thrown.code || thrown.name) + ': ' + thrown.message : 'RAN (workdir=' + portable(ranRow && ranRow.workdir) + ')'}`);
    check('escaping null-workdir spawn REFUSES with E_WORKDIR_ESCAPE (fail-closed)',
      Boolean(thrown) && thrown.code === 'E_WORKDIR_ESCAPE');
    check('escaping spawn did NOT run a worker (no row went to running)', ranRow === null);
    // Disk truth (D51): the escaping session dir must not have produced a live unit; if a row
    // did run despite the mismatch, that is the fail-open still open — caught above.
  } finally {
    try { if (ranRow) await ctx.mgr.kill(ranRow.exec_id); } catch {}
    try { closeHeartStore(); } catch {}
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}
  }
}

async function main() {
  log('p3-5 mutation proof — the D56 fail-open is CLOSED by construction AND by check (D58(2))');
  log(`started: ${now()}`);
  log('command: node deploy/p3-5-mutation.js');
  await legAligned();
  await legEscaping();
  const failed = checks.filter((c) => !c.ok);
  log('');
  log(`checks: ${checks.length} total, ${checks.length - failed.length} passed, ${failed.length} failed`);
  log(`result: ${failed.length === 0 ? 'PASS' : 'FAIL'}`);
  return failed.length === 0 ? 0 : 1;
}

main()
  .then((code) => { log(`ended: ${now()}`); fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n'); process.exit(code); })
  .catch((err) => { log(`error: ${err.code || err.name}: ${err.message}`); log('result: FAIL'); log(`ended: ${now()}`); fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n'); process.exit(1); });
