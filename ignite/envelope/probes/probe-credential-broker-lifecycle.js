'use strict';

// Red-first proof for `d-hold5-wire-the-broker` — the SPAWN.JS WIRING specifically (the broker's
// own socket protocol is `probe-credential-broker.js`'s job, unchanged, run alongside this one).
// Drives the REAL production path: `composeCageFor` (not a hand-called `startBroker`) starts the
// goal's broker via `ensureGoalBroker`, a second seat of the SAME goal reuses it rather than
// starting a second one, a caged process mints through the REAL `gtools-token-minter.js` ->
// `gtools_mint_token.py` pipeline (never exercised end-to-end before this probe — always fixture-
// swapped out in `probe-credential-broker.js`), and `stopGoalBroker` (the goal-end integration
// point `endGoalBroker` exposes) tears it down. Fixture `scripts/auth.py` stands in for gtools'
// own OAuth module — no real account, no Google, no network, per the mission's own constraint
// that the minter has never run against a real account and this sitting does not change that.

const fs = require('node:fs');
const path = require('node:path');
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');

const execFileAsync = promisify(execFile);
const { admitLaunch } = require('../launch');
const { socketPath, logPath } = require('../credential-broker');
const { parseSeatPath } = require('../../runtime/seat-identity/seat-folder');
const { buildBwrapArgv } = require('../../supervisor/spawn/bwrap');
const {
  composeCageFor, ensureGoalBroker, brokerReadyFor, stopGoalBroker,
} = require('../../supervisor/spawn/spawn');

const FIXTURE_TMP = '/var/tmp';
const outPath = path.join(__dirname, 'probe-credential-broker-lifecycle.out');
fs.writeFileSync(outPath, '');

function out(line) { fs.appendFileSync(outPath, `${line}\n`); }

const checks = [];
function check(name, pass, detail) {
  checks.push(pass);
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

function mkdirp(p) { fs.mkdirSync(p, { recursive: true }); }
function touch(p, b) { mkdirp(path.dirname(p)); fs.writeFileSync(p, b == null ? '' : b); }

// A fixture `scripts/auth.py` standing in for gtools' OWN OAuth module — `gtools_mint_token.py`
// imports whatever module named `auth` sits first on `sys.path`, and this fixture's `gtoolsRoot`
// is a throwaway `/var/tmp` directory, so the real gtools `auth.py` is never on the search path
// and never imported. No real account, no Google, no network — a canned, valid-shaped credential
// object returned entirely locally.
const FIXTURE_AUTH_PY = `
class _Creds:
    valid = True
    token = "fixture-lifecycle-token-not-a-real-secret"
    expiry = None

def load_config():
    return {}

def get_credentials(account, config):
    if account != "fixture-acct":
        raise SystemExit("no such fixture account: " + str(account))
    return _Creds()
`;

function setupFixture(prefix) {
  fs.mkdirSync(FIXTURE_TMP, { recursive: true });
  const root = fs.mkdtempSync(path.join(FIXTURE_TMP, prefix));
  const workspace = path.join(root, 'ws');
  const home = path.join(root, 'home');
  const rbtvRepo = path.join(root, 'rbtv');
  const goalId = 'test-cbl';
  const goalDir = path.join(workspace, '.rbtv', 'goals', goalId);
  const seatDirA = path.join(goalDir, 'seats', 'a');
  const seatDirB = path.join(goalDir, 'seats', 'b');
  mkdirp(path.join(goalDir, 'scratch'));
  mkdirp(path.join(goalDir, 'coordination'));
  mkdirp(seatDirA);
  mkdirp(seatDirB);
  mkdirp(path.join(workspace, '.rbtv', 'mirror', 'x'));
  mkdirp(path.join(workspace, '.rbtv', 'config'));
  mkdirp(path.join(home, '.cache'));
  mkdirp(path.join(home, '.config', 'tool'));
  mkdirp(path.join(rbtvRepo, 'ignite', 'envelope'));
  touch(path.join(goalDir, 'sessions.csv'), '');
  touch(path.join(rbtvRepo, 'ignite', 'envelope', 'spawn-profiles.yaml'), '');
  touch(path.join(workspace, '.rbtv', 'config', '.env'), '');
  const gtoolsRoot = path.join(workspace, '3-resources', 'tools', 'gtools');
  touch(path.join(gtoolsRoot, 'credentials', 'fixture-acct', 'credentials.json'), '{"fixture":true}');
  touch(path.join(gtoolsRoot, 'credentials', 'fixture-acct', 'token.json'), '{"fixture":true}');
  touch(path.join(gtoolsRoot, 'scripts', 'auth.py'), FIXTURE_AUTH_PY);
  for (const seatDir of [seatDirA, seatDirB]) {
    touch(path.join(seatDir, 'seat.md'), ['---', `seat: ${path.basename(seatDir)}`, 'harness: bash', 'model: test-sleep', '---', ''].join('\n'));
  }
  fs.writeFileSync(path.join(goalDir, 'envelope.json'), JSON.stringify({
    credentialNames: [{ type: 'gtools-account', account: 'fixture-acct' }],
  }));
  return { root, workspace, home, rbtvRepo, goalId, goalDir, seatDirA, seatDirB, gtoolsRoot };
}

async function cagedRunAsync(composed, seatDir, py) {
  const argv = buildBwrapArgv({ argv: ['python3', '-c', py], workdir: seatDir, harness: null, seatBinds: composed });
  try {
    const { stdout } = await execFileAsync(argv[0], argv.slice(1), { timeout: 15000, encoding: 'utf8' });
    return { exit: 0, stdout: stdout.trim(), stderr: '' };
  } catch (err) {
    return {
      exit: err.code === undefined ? -1 : err.code,
      stdout: String(err.stdout || '').trim(),
      stderr: String(err.stderr || '').trim().slice(0, 240),
    };
  }
}

function mintClientPy(sockAbsPath, account) {
  return `
import json, socket
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    s.connect(${JSON.stringify(sockAbsPath)})
    s.sendall((json.dumps({"op": "mint", "account": ${JSON.stringify(account)}}) + "\\n").encode())
    buf = b""
    while b"\\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    print(buf.decode().strip())
except Exception as e:
    print(json.dumps({"ok": False, "reason": "client-error: " + str(e)}))
finally:
    s.close()
`;
}

async function main() {
  out('COMMAND: node ignite/envelope/probes/probe-credential-broker-lifecycle.js');
  out('evidence-class: FIXTURE /var/tmp workspace + fixture scripts/auth.py; REAL admitLaunch + '
    + 'composeCageFor + ensureGoalBroker/brokerReadyFor/stopGoalBroker + gtools-token-minter.js + '
    + 'gtools_mint_token.py + bwrap');
  const fx = setupFixture('cbl-');
  const base = {
    workspaceRoot: fx.workspace, goalId: fx.goalId, goalDir: fx.goalDir, home: fx.home,
    tmpdir: require('node:os').tmpdir(), rbtvRepo: fx.rbtvRepo,
  };
  const seatPathA = parseSeatPath(fx.seatDirA);
  const seatPathB = parseSeatPath(fx.seatDirB);
  const sockAbs = socketPath(fx.goalDir);

  // ── RED — before any launch, the goal has no broker socket ───────────────────────────────
  check('RED no broker socket exists before any seat of this goal launches', !fs.existsSync(sockAbs), sockAbs);

  // ── admission still passes (unchanged behaviour) ──────────────────────────────────────────
  const admitted = admitLaunch({ ...base, seatDir: fx.seatDirA });
  check(
    'ADMIT the fixture account still admits the launch (composeCageFor path unaffected by wiring)',
    admitted.spawn === true && (admitted.accountCredentials || []).includes('fixture-acct'),
    `spawn=${admitted.spawn} accounts=${JSON.stringify(admitted.accountCredentials)}`,
  );

  // ── GREEN 1 — seat A's OWN launch sequence (composeCageFor) starts the broker ────────────
  let composedA;
  let composeErrA;
  try { composedA = composeCageFor({}, seatPathA, fx.seatDirA, null, () => {}); } catch (err) { composeErrA = err; }
  check('COMPOSE seat A composes a cage without throwing', Array.isArray(composedA), String(composeErrA && composeErrA.message));
  const readyA = brokerReadyFor(fx.goalDir);
  check('KICKED-OFF composeCageFor itself registered a broker-ready promise for this goal — no manual startBroker call', Boolean(readyA));
  await readyA;
  check('GREEN broker socket exists once seat A\'s own launch sequence has run', fs.existsSync(sockAbs), sockAbs);

  // ── GREEN 2 — a caged process mints a REAL token via gtools-token-minter.js -> gtools_mint_token.py ──
  const mintResult = await cagedRunAsync(composedA, fx.seatDirA, mintClientPy(sockAbs, 'fixture-acct'));
  let mintJson = null;
  try { mintJson = JSON.parse(mintResult.stdout); } catch { /* checked below */ }
  check(
    'GREEN caged process mints a real token through the PRODUCTION minter pipeline (gtools-token-minter.js + gtools_mint_token.py), never exercised end-to-end before this probe',
    mintResult.exit === 0 && mintJson && mintJson.ok === true && mintJson.accessToken === 'fixture-lifecycle-token-not-a-real-secret',
    `exit=${mintResult.exit} stdout=${mintResult.stdout} stderr=${mintResult.stderr}`,
  );

  // ── REUSE — seat B of the SAME goal reuses the SAME broker, never starts a second one ────
  let composedB;
  try { composedB = composeCageFor({}, seatPathB, fx.seatDirB, null, () => {}); } catch { /* checked via readyB below */ }
  const readyB = brokerReadyFor(fx.goalDir);
  check(
    'REUSE seat B\'s own launch sequence reuses seat A\'s broker (same promise instance), never starts a second one',
    readyB === readyA,
  );
  const mintResultB = await cagedRunAsync(composedB, fx.seatDirB, mintClientPy(sockAbs, 'fixture-acct'));
  let mintJsonB = null;
  try { mintJsonB = JSON.parse(mintResultB.stdout); } catch { /* checked below */ }
  check(
    'REUSE seat B reaches the SAME live broker socket seat A started',
    mintResultB.exit === 0 && mintJsonB && mintJsonB.ok === true,
    `exit=${mintResultB.exit} stdout=${mintResultB.stdout}`,
  );

  // ── STOP — the goal-end integration point tears the broker down ──────────────────────────
  await stopGoalBroker(fx.goalDir);
  check('STOP the broker socket is gone once stopGoalBroker (the goal-end integration point) runs', !fs.existsSync(sockAbs), sockAbs);
  const afterStop = await cagedRunAsync(composedA, fx.seatDirA, mintClientPy(sockAbs, 'fixture-acct'));
  let afterStopJson = null;
  try { afterStopJson = JSON.parse(afterStop.stdout); } catch { /* checked below */ }
  check(
    'STOP a mint attempt after stop fails loud (connection refused), never hangs and never returns a stale token',
    afterStopJson && afterStopJson.ok === false,
    `stdout=${afterStop.stdout}`,
  );

  // ── the audit-file record is durable across the whole sequence (§10b's durable half) ─────
  const auditLines = (() => {
    try { return fs.readFileSync(logPath(fx.goalDir), 'utf8').split('\n').filter(Boolean); } catch { return []; }
  })();
  check(
    // 2, not 3: the after-stop attempt never reaches the broker at all (the socket is gone), so
    // it is never logged — that IS the proof of a clean stop, checked by the STOP leg above.
    'AUDIT the two in-flight mint attempts (seat A, seat B) each left a durable, goal-scoped log line',
    auditLines.length === 2 && auditLines.every((l) => JSON.parse(l).op === 'mint' && JSON.parse(l).ok === true),
    `lines=${auditLines.length}`,
  );

  try { fs.rmSync(fx.root, { recursive: true, force: true }); } catch { /* best effort */ }
  const failed = checks.filter((p) => !p).length;
  out(failed === 0 ? 'ALL LEGS PASS' : `FAILED ${failed}/${checks.length}`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((err) => {
  out(`FATAL ${err && err.stack}`);
  process.exit(1);
});
