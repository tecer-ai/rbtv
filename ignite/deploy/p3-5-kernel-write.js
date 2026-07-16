'use strict';

// p3-5-kernel-write.js — the DETERMINISTIC kernel-level write test (D58(3)/(5), harness-free).
// A trivial `bash` worker, launched through the daemon's OWN spawn path via the null-workdir
// (default/ticker) branch, attempts to create a file in FOUR places and reports each result to its
// unit log. The transient unit's kernel sandbox (ProtectSystem=strict + ReadWritePaths=[session
// dir, declared test folder]) must make the vault-root and .rbtv/heart writes FAIL at the kernel:
//   (a) its own session dir      -> MUST succeed
//   (b) the declared test folder -> MUST succeed
//   (c) the vault root           -> MUST fail (kernel EROFS)
//   (d) .rbtv/heart/ (the control-plane store, a sibling) -> MUST fail (kernel EROFS)
// D51: exit codes and DISK are truth; the log lines are hints. Every leg is verified against disk
// (the canary's existence/absence), never against the worker's own report alone.
//
// This is the reliable kernel-level acceptance; the live-LLM 3-way test (p3-5-three-way.js) confirms
// the same on real harnesses. No LLM, no cost, no API key — bash is the worker.
//
// Writes deploy/p3-5-kernel-write.out; exits 0 (all legs correct on disk) / 1 (any wrong).

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');

const IGNITE_SRC = path.resolve(__dirname, '..');
const VAULT_ROOT = process.env.RBTV_IGNITE_WORKSPACE_ROOT || path.resolve(IGNITE_SRC, '..', '..', '..', '..');
const TEST_FOLDER = path.join(VAULT_ROOT, '1-projects', 'rbtv-sb-merge-refactor-core-build', 'build', 'containment-test');
const REAL_HEART = path.join(VAULT_ROOT, '.rbtv', 'heart');
const OUT_PATH = path.join(__dirname, 'p3-5-kernel-write.out');

const { openHeartStore, closeHeartStore } = require(path.join(IGNITE_SRC, 'server', 'heart', 'heart-store'));
const { createSpawnManager } = require(path.join(IGNITE_SRC, 'server', 'spawn', 'spawn'));

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

const TAG = `__p35_${process.pid}`;
const CANARIES = {
  session: `${TAG}_session`,
  test: path.join(TEST_FOLDER, `${TAG}_test`),
  vault: path.join(VAULT_ROOT, `${TAG}_vault`),
  heart: path.join(REAL_HEART, `${TAG}_heart`),
};

function sleepMs(ms) { const end = Date.now() + ms; while (Date.now() < end) { try { execFileSync('true'); } catch {} } }

async function main() {
  log('p3-5 kernel-level write test — bash worker through the daemon spawn path (null-workdir branch)');
  log(`started: ${now()}`);
  log('command: node deploy/p3-5-kernel-write.js');
  log(`vault root:  ${portable(VAULT_ROOT)}`);
  log(`test folder: ${portable(TEST_FOLDER)}`);
  log(`real heart:  ${portable(REAL_HEART)}`);

  if (!fs.existsSync(TEST_FOLDER)) { log(`FAIL: declared test folder missing: ${portable(TEST_FOLDER)}`); log('result: FAIL'); fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n'); process.exit(1); }

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'p3-5-kw-'));
  const ws = path.join(tmp, 'ws');
  const dataRoot = path.join(tmp, 'data');
  fs.mkdirSync(ws, { recursive: true });
  fs.mkdirSync(dataRoot, { recursive: true });
  const sessionsRoot = path.join(ws, '.rbtv', 'sessions');

  // A benign bash worker that attempts the four writes and logs the outcome of each.
  const script = [
    'set +e',
    `touch "./${CANARIES.session}" 2>/dev/null && echo "SESSION:WROTE" || echo "SESSION:BLOCKED"`,
    `touch "${CANARIES.test}" 2>/dev/null && echo "TEST:WROTE" || echo "TEST:BLOCKED"`,
    `touch "${CANARIES.vault}" 2>/dev/null && echo "VAULT:WROTE" || echo "VAULT:BLOCKED"`,
    `touch "${CANARIES.heart}" 2>/dev/null && echo "HEART:WROTE" || echo "HEART:BLOCKED"`,
    'echo "DONE"',
    'sleep 1',
  ].join('; ');

  const profile = {
    exec: { argv: ['bash', '-c', script], prompt: 'stdin' },
    resume: { argv: ['bash', '-c', script], prompt: 'stdin' },
    session_ref: { source: 'cwd-implicit' },
    workdir_root: sessionsRoot,
    caps: { memory_max: '128M', runtime_max: '5m' },
    // The production sandbox shape, + the declared test folder (launch-time RW extension — never
    // committed to a production profile, keeping config machine-agnostic; D26(3)).
    sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}', TEST_FOLDER], PrivateTmp: true, NoNewPrivileges: true },
  };
  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(tmp, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'systemd', kill_grace_seconds: 2 },
    default_workdir_root: ws,
    profiles: { 'kernel-write': profile },
  };
  const cfgPath = path.join(tmp, 'spawn.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const store = openHeartStore({ runtimeStateRoot: ws });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });

  let row;
  try {
    const fired = store.recordExecutionStart({
      jobId: 'launch-agent', actionType: 'launch-agent', args: '{}',
      enqueuedBy: 'p3-5-kw', sessionMode: 'headless', firedTick: 1, firedAt: new Date(),
      profile: 'kernel-write', workdir: null,
    });
    row = await mgr.spawn(fired.exec_id, 'kernel-write', 'headless', null, null, 'p3-5-kw');
    log(`spawned: unit=${row.unit_name} carrier=${row.carrier} sessionDir=${portable(row.workdir)}`);
    check('worker ran under systemd (kernel sandbox in force)', row.carrier === 'systemd');

    // Wait for the worker to perform its touches and log DONE.
    let logText = '';
    for (let i = 0; i < 40; i++) {
      sleepMs(200);
      try { logText = fs.readFileSync(row.log_path, 'utf8'); } catch { logText = ''; }
      if (/DONE/.test(logText)) break;
    }
    log('worker log (hint — disk is truth):');
    for (const l of logText.split('\n').filter(Boolean)) log(`  | ${l}`);

    // ---- disk truth (D51) ----
    const sessionCanary = path.join(row.workdir, CANARIES.session);
    const sessionExists = fs.existsSync(sessionCanary);
    const testExists = fs.existsSync(CANARIES.test);
    const vaultExists = fs.existsSync(CANARIES.vault);
    const heartExists = fs.existsSync(CANARIES.heart);

    check('(a) session-dir write SUCCEEDED (canary on disk)', sessionExists, portable(sessionCanary));
    check('(b) declared-test-folder write SUCCEEDED (canary on disk)', testExists, portable(CANARIES.test));
    check('(c) vault-root write FAILED at the kernel (no canary on disk)', !vaultExists, portable(CANARIES.vault));
    check('(d) .rbtv/heart write FAILED at the kernel (no canary on disk)', !heartExists, portable(CANARIES.heart));

    // Clean up any canary that DID land (defensive — a landed vault/heart canary is a FAIL above).
    for (const p of [CANARIES.test, CANARIES.vault, CANARIES.heart]) { try { if (fs.existsSync(p)) fs.rmSync(p); } catch {} }
  } finally {
    try { if (row) await mgr.kill(row.exec_id); } catch {}
    try { closeHeartStore(); } catch {}
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}
  }

  const failed = checks.filter((c) => !c.ok);
  log('');
  log(`checks: ${checks.length} total, ${checks.length - failed.length} passed, ${failed.length} failed`);
  log(`result: ${failed.length === 0 ? 'PASS' : 'FAIL'}`);
  return failed.length === 0 ? 0 : 1;
}

main()
  .then((code) => { log(`ended: ${now()}`); fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n'); process.exit(code); })
  .catch((err) => { log(`error: ${err.code || err.name}: ${err.message}`); log('result: FAIL'); log(`ended: ${now()}`); fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n'); process.exit(1); });
