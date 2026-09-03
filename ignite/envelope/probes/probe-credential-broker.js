'use strict';

// Red-first proof for `d-ask17-credential-token-broker`: (1) today's admission refusal for a
// dead/absent gtools account, (2) a caged seat obtaining a working short-lived token through the
// broker socket WITHOUT any credential directory entering the cage, (3) the negative control —
// the account's real credential folder stays unreachable from inside the cage, and a directory
// BIND on it is still refused by the deny-list (`T2-R11`/`D19` regression). Fixture minter only —
// no real account, no Google, no network. Pattern: `probe-credential-injection.js`.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync, execFile } = require('node:child_process');
const { promisify } = require('node:util');

const execFileAsync = promisify(execFile);
const { admitLaunch } = require('../launch');
const { compile } = require('../compiler');
const { socketPath } = require('../credential-broker');
const { parseSeatPath } = require('../../runtime/seat-identity/seat-folder');
const { buildBwrapArgv } = require('../../supervisor/spawn/bwrap');
const {
  composeCageFor, ensureGoalBroker, stopGoalBroker,
} = require('../../supervisor/spawn/spawn');

const FIXTURE_TMP = '/var/tmp';
const outPath = path.join(__dirname, 'probe-credential-broker.out');
fs.writeFileSync(outPath, '');

function out(line) { fs.appendFileSync(outPath, `${line}\n`); }

const checks = [];
function check(name, pass, detail) {
  checks.push(pass);
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

function mkdirp(p) { fs.mkdirSync(p, { recursive: true }); }
function touch(p, b) { mkdirp(path.dirname(p)); fs.writeFileSync(p, b == null ? '' : b); }

function setupFixture(prefix) {
  fs.mkdirSync(FIXTURE_TMP, { recursive: true });
  const root = fs.mkdtempSync(path.join(FIXTURE_TMP, prefix));
  const workspace = path.join(root, 'ws');
  const home = path.join(root, 'home');
  const rbtvRepo = path.join(root, 'rbtv');
  const goalId = 'test-cred-broker';
  const goalDir = path.join(workspace, '.rbtv', 'goals', goalId);
  const seatDir = path.join(goalDir, 'seats', 'prober');
  mkdirp(path.join(goalDir, 'scratch'));
  mkdirp(path.join(goalDir, 'coordination'));
  mkdirp(seatDir);
  mkdirp(path.join(workspace, '.rbtv', 'mirror', 'x'));
  mkdirp(path.join(workspace, '.rbtv', 'config'));
  mkdirp(path.join(home, '.cache'));
  mkdirp(path.join(home, '.config', 'tool'));
  mkdirp(path.join(rbtvRepo, 'ignite', 'envelope'));
  touch(path.join(goalDir, 'sessions.csv'), '');
  touch(path.join(rbtvRepo, 'ignite', 'envelope', 'spawn-profiles.yaml'), '');
  touch(path.join(workspace, '.rbtv', 'config', '.env'), '');
  // The fixture "account" — never a real gtools account, never anything an implementer of this
  // probe should mistake for one: two placeholder files, no OAuth material.
  const gtoolsRoot = path.join(workspace, '3-resources', 'tools', 'gtools');
  touch(path.join(gtoolsRoot, 'credentials', 'fixture-acct', 'credentials.json'), '{"fixture":true}');
  touch(path.join(gtoolsRoot, 'credentials', 'fixture-acct', 'token.json'), '{"fixture":true}');
  touch(path.join(seatDir, 'seat.md'), ['---', 'seat: prober', 'harness: bash', 'model: test-sleep', '---', ''].join('\n'));
  return { root, workspace, home, rbtvRepo, goalId, goalDir, seatDir, gtoolsRoot };
}

function cagedRun(composed, seatDir, py) {
  const argv = buildBwrapArgv({ argv: ['python3', '-c', py], workdir: seatDir, harness: null, seatBinds: composed });
  try {
    return {
      exit: 0,
      stdout: execFileSync(argv[0], argv.slice(1), {
        stdio: ['ignore', 'pipe', 'pipe'], timeout: 15000, encoding: 'utf8',
      }).trim(),
      stderr: '',
    };
  } catch (err) {
    return {
      exit: err.status === undefined ? -1 : err.status,
      stdout: String(err.stdout || '').trim(),
      stderr: String(err.stderr || '').trim().slice(0, 240),
    };
  }
}

// ⚠ MUST BE ASYNC, NOT `execFileSync`. The in-process broker (`startBroker`) answers requests on
// THIS Node process's own event loop — a synchronous `execFileSync` call blocks that event loop
// for its whole duration, so the caged client's connection would sit accepted-by-the-kernel but
// never SERVICED (no 'connection' callback fires) until the child exits, which it never does
// because it is waiting on the very response the blocked loop cannot send. Measured directly:
// swapping this leg to `execFileSync` reproduces a hang that outlives any client-side socket
// timeout. `execFile` (promisified) keeps the loop free while the caged child runs.
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

// A one-shot newline-JSON client, run FROM INSIDE THE CAGE (via `python3 -c`, no node inside a
// bwrap sandbox that only ever carries `python3`/`bash` for a fixture seat) — sockets are
// language-agnostic, and this is exactly what a real caged tool would do.
function mintClientPy(sockAbsPath, account) {
  return `
import json, socket, sys
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
  out('COMMAND: node ignite/envelope/probes/probe-credential-broker.js');
  out('evidence-class: FIXTURE /var/tmp workspace + fixture minter; REAL admitLaunch + credential-broker + composeCageFor + bwrap');
  const fx = setupFixture('cred-broker-');
  const base = {
    workspaceRoot: fx.workspace,
    goalId: fx.goalId,
    goalDir: fx.goalDir,
    home: fx.home,
    tmpdir: require('node:os').tmpdir(),
    rbtvRepo: fx.rbtvRepo,
    seatDir: fx.seatDir,
  };
  const seatPath = parseSeatPath(fx.seatDir);

  // ── RED 1 — today's admission refusal for a dead/absent account ──────────────────────────
  fs.writeFileSync(path.join(fx.goalDir, 'envelope.json'), JSON.stringify({
    credentialNames: [{ type: 'gtools-account', account: 'no-such-account' }],
  }));
  const refused = admitLaunch(base);
  check(
    'RED1 admission refuses a dead/absent account, loud, before spawn',
    refused.spawn === false && refused.refuse && refused.refuse.kind === 'missing-credential'
      && Array.isArray(refused.refuse.missing) && refused.refuse.missing.includes('gtools-account:no-such-account'),
    `spawn=${refused.spawn} refuse=${JSON.stringify(refused.refuse)}`,
  );

  // ── GREEN — a real account admits, the broker starts, a caged process mints a token ──────
  fs.writeFileSync(path.join(fx.goalDir, 'envelope.json'), JSON.stringify({
    credentialNames: [{ type: 'gtools-account', account: 'fixture-acct' }],
  }));
  const admitted = admitLaunch(base);
  check(
    'ADMIT a present fixture account admits the launch',
    admitted.spawn === true && Array.isArray(admitted.accountCredentials)
      && admitted.accountCredentials.includes('fixture-acct'),
    `spawn=${admitted.spawn} accounts=${JSON.stringify(admitted.accountCredentials)} refuse=${JSON.stringify(admitted.refuse)}`,
  );

  const FIXTURE_TOKEN = 'fixture-short-lived-token-not-a-real-secret';
  // Registered through the SAME shared registry `composeCageFor` reads below (`ensureGoalBroker`,
  // `d-hold5-wire-the-broker`'s spawn.js wiring) — never a bare `startBroker` call the registry
  // cannot see: `composeCageFor`'s own launch sequence starts a broker for any admitted
  // `gtools-account` goal, and a second, uncoordinated `startBroker` for the SAME goalDir would
  // race it for the socket and lose (measured while landing that wiring). Passing a fixture
  // minter here still proves the broker's own protocol in isolation from the real minter
  // pipeline — `probe-credential-broker-lifecycle.js` covers the real pipeline end to end.
  await ensureGoalBroker(fx.goalDir, fx.workspace, admitted.accountCredentials || [], async (account) => (
    account === 'fixture-acct'
      ? { ok: true, accessToken: FIXTURE_TOKEN, expiresAt: '2099-01-01T00:00:00Z' }
      : { ok: false, reason: 'fixture minter knows only fixture-acct' }));

  let composed;
  let composeErr;
  try { composed = composeCageFor({}, seatPath, fx.seatDir, null, () => {}); } catch (err) { composeErr = err; }
  const sockAbs = socketPath(fx.goalDir);
  const mintResult = Array.isArray(composed)
    ? await cagedRunAsync(composed, fx.seatDir, mintClientPy(sockAbs, 'fixture-acct'))
    : { exit: -1, stdout: 'COMPOSE-FAILED', stderr: String(composeErr && composeErr.message) };
  let mintJson = null;
  try { mintJson = JSON.parse(mintResult.stdout); } catch { /* checked below */ }
  check(
    'GREEN caged process mints a working short-lived token via the broker socket',
    mintResult.exit === 0 && mintJson && mintJson.ok === true && mintJson.accessToken === FIXTURE_TOKEN,
    `exit=${mintResult.exit} stdout=${mintResult.stdout} stderr=${mintResult.stderr}`,
  );

  // Cross-account request refused even though the broker is live and reachable — the allow-list
  // (this goal's own declared accounts), not just "the socket exists", is what authorizes a mint.
  const crossResult = Array.isArray(composed)
    ? await cagedRunAsync(composed, fx.seatDir, mintClientPy(sockAbs, 'some-other-account'))
    : { exit: -1, stdout: 'COMPOSE-FAILED' };
  let crossJson = null;
  try { crossJson = JSON.parse(crossResult.stdout); } catch { /* checked below */ }
  check(
    'ALLOWLIST an undeclared account is refused even by a live, reachable broker',
    crossJson && crossJson.ok === false && /not declared/.test(crossJson.reason || ''),
    `stdout=${crossResult.stdout}`,
  );

  // ── NEGATIVE CONTROL — the real account folder never entered the cage ────────────────────
  const realAcctDir = path.join(fx.gtoolsRoot, 'credentials', 'fixture-acct');
  const maskPy = `import os; print("REAL-ACCOUNT-VISIBLE" if os.path.exists(${JSON.stringify(realAcctDir)}) else "ABSENT")`;
  const maskResult = Array.isArray(composed)
    ? cagedRun(composed, fx.seatDir, maskPy)
    : { exit: -1, stdout: 'COMPOSE-FAILED' };
  check(
    'NEGATIVE the real gtools/credentials/<account> folder never enters the cage',
    maskResult.stdout === 'ABSENT' || maskResult.exit !== 0,
    `exit=${maskResult.exit} stdout=${maskResult.stdout} stderr=${maskResult.stderr}`,
  );

  // ── REGRESSION — T2-R11/D19: an rw BIND on the account folder is still refused ────────────
  const compileResult = compile({
    workspaceRoot: fx.workspace,
    goalId: fx.goalId,
    rbtvRepo: fx.rbtvRepo,
    home: fx.home,
    tmpdir: require('node:os').tmpdir(),
    namedRepos: [],
    projectFolder: null,
    credentialNames: [],
    extraPaths: [{ access: 'rw', path: '3-resources/tools/gtools/credentials/fixture-acct' }],
  });
  check(
    'REGRESSION deny-list still refuses a directory bind on the account folder (kind:"conflict")',
    compileResult.ok === false && compileResult.refuse && compileResult.refuse.kind === 'conflict',
    JSON.stringify(compileResult),
  );

  await stopGoalBroker(fx.goalDir);
  try { fs.rmSync(fx.root, { recursive: true, force: true }); } catch { /* best effort */ }
  const failed = checks.filter((p) => !p).length;
  out(failed === 0 ? 'ALL LEGS PASS' : `FAILED ${failed}/${checks.length}`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((err) => {
  out(`FATAL ${err && err.stack}`);
  process.exit(1);
});
