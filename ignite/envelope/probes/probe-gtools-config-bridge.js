'use strict';

// Red-first proof for `d-gtools-config-bridge` (escalation #9, remedy 2 — extends
// `d-gtools-broker-bridge`/`probe-credential-broker-lifecycle.js`'s fixture pattern). `config.yaml`
// itself is an enumerated private-scope deny entry (T2-R11/D19), so `gtools`' own `load_config()`
// hard-exited before a caged seat could even resolve an account, broker or no broker. This probe
// drives the REAL production wiring — `composeCageFor`'s `materializeGtoolsConfig` + the
// `IGNITE_GTOOLS_CONFIG` `--setenv` — against a REAL bwrap cage with a private.json deny entry
// mirroring the real one, and a FIXTURE `auth.py` standing in for gtools' own OAuth module (no
// real account, no Google, no network — same reasoning `probe-credential-broker-lifecycle.js`
// gives for its own fixture). The gtools-side change itself (`scripts/auth.py#load_config`
// preferring the env var) is proven separately against the REAL gtools code — no probe infra spans
// two repos in this tree (see the report's standalone cross-repo proof).

const fs = require('node:fs');
const path = require('node:path');
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');

const execFileAsync = promisify(execFile);
const { admitLaunch } = require('../launch');
const { socketPath } = require('../credential-broker');
const { parseSeatPath } = require('../../runtime/seat-identity/seat-folder');
const { buildBwrapArgv } = require('../../supervisor/spawn/bwrap');
const { composeCageFor } = require('../../supervisor/spawn/spawn');

const FIXTURE_TMP = '/var/tmp';
const outPath = path.join(__dirname, 'probe-gtools-config-bridge.out');
fs.writeFileSync(outPath, '');

function out(line) { fs.appendFileSync(outPath, `${line}\n`); }

const checks = [];
function check(name, pass, detail) {
  checks.push(pass);
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

function mkdirp(p) { fs.mkdirSync(p, { recursive: true }); }
function touch(p, b) { mkdirp(path.dirname(p)); fs.writeFileSync(p, b == null ? '' : b); }

// A fixture `scripts/auth.py`, same reasoning as `probe-credential-broker-lifecycle.js`'s own:
// `gtools_mint_token.py` imports whatever module named `auth` sits first on `sys.path`, and this
// fixture's `gtoolsRoot` is a throwaway `/var/tmp` directory, so the real gtools `auth.py` is
// never on the search path. It mirrors the REAL `load_config()` contract this seat just landed
// there (env-var override, loud named failure on a missing override target) so the wiring this
// probe DOES own — the rbtv side — is exercised through the same shape gtools itself now has.
const FIXTURE_AUTH_PY = `
import os, sys, yaml

CONFIG_FILE = ${JSON.stringify('__CONFIG_FILE__')}
GTOOLS_CONFIG_ENV = "IGNITE_GTOOLS_CONFIG"

class _Creds:
    valid = True
    token = "fixture-config-bridge-token-not-a-real-secret"

def load_config():
    override = os.environ.get(GTOOLS_CONFIG_ENV)
    if override:
        config_file = override
        if not os.path.exists(config_file):
            sys.exit("ERROR: " + GTOOLS_CONFIG_ENV + " is set to " + config_file + " but that file does not exist.")
    else:
        config_file = CONFIG_FILE
        if not os.path.exists(config_file):
            sys.exit("ERROR: " + config_file + " not found.")
    with open(config_file) as f:
        return yaml.safe_load(f)

def get_credentials(account, config):
    if account not in config.get("accounts", {}):
        raise SystemExit("no such fixture account: " + str(account))
    return _Creds()
`;

function setupFixture(prefix) {
  fs.mkdirSync(FIXTURE_TMP, { recursive: true });
  const root = fs.mkdtempSync(path.join(FIXTURE_TMP, prefix));
  const workspace = path.join(root, 'ws');
  const home = path.join(root, 'home');
  const rbtvRepo = path.join(root, 'rbtv');
  const goalId = 'test-gcb';
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
  const configFile = path.join(gtoolsRoot, 'config.yaml');
  touch(configFile, 'accounts:\n  fixture-acct:\n    email: fixture@example.com\n    credentials_dir: credentials/fixture-acct\nscopes: []\n');
  touch(path.join(gtoolsRoot, 'credentials', 'fixture-acct', 'credentials.json'), '{"fixture":true}');
  touch(path.join(gtoolsRoot, 'credentials', 'fixture-acct', 'token.json'), '{"fixture":true}');
  touch(path.join(gtoolsRoot, 'scripts', 'auth.py'), FIXTURE_AUTH_PY.replace('__CONFIG_FILE__', configFile));
  // Mirrors the REAL vault's `.rbtv/config/private.json`: config.yaml enumerated as `deny`, exactly
  // like escalation #9's blocker — not a hardcode, not pattern-floor-shaped by basename, so this is
  // the ONLY thing that masks it. `credentials/` masks separately via the pattern floor (`**/credentials/`),
  // regression-checked below as the T2-R11/D19 arm.
  fs.writeFileSync(path.join(workspace, '.rbtv', 'config', 'private.json'), JSON.stringify({
    deny: ['3-resources/tools/gtools/config.yaml'],
  }));
  for (const seatDir of [seatDirA, seatDirB]) {
    touch(path.join(seatDir, 'seat.md'), ['---', `seat: ${path.basename(seatDir)}`, 'harness: bash', 'model: test-sleep', '---', ''].join('\n'));
  }
  fs.writeFileSync(path.join(goalDir, 'envelope.json'), JSON.stringify({
    credentialNames: [{ type: 'gtools-account', account: 'fixture-acct' }],
  }));
  return {
    root, workspace, home, rbtvRepo, goalId, goalDir, seatDirA, seatDirB, gtoolsRoot, configFile,
  };
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

function envValue(flags, name) {
  for (let i = 0; i < flags.length - 2; i += 1) {
    if (flags[i] === '--setenv' && flags[i + 1] === name) return flags[i + 2];
  }
  return null;
}

// Reads config via the fixture auth.py's own contract (env-var preferred, loud on missing), and
// separately proves the ORIGINAL on-disk config.yaml is unreachable — the T2-R11/D19 regression
// arm, run INSIDE the cage so it reflects the real mask, not an assumption about it.
function probePy(configEnvValue, originalConfigPath) {
  return `
import json, os, sys
sys.path.insert(0, os.path.dirname(${JSON.stringify(originalConfigPath)}) + "/scripts")
import auth

result = {}
try:
    with open(${JSON.stringify(originalConfigPath)}) as f:
        f.read()
    result["original_readable"] = True
except Exception as e:
    result["original_readable"] = False
    result["original_error"] = type(e).__name__

try:
    cfg = auth.load_config()
    creds = auth.get_credentials("fixture-acct", cfg)
    result["ok"] = True
    result["accounts"] = sorted(cfg.get("accounts", {}).keys())
    result["token"] = creds.token
except SystemExit as e:
    result["ok"] = False
    result["reason"] = str(e)
print(json.dumps(result))
`;
}

async function main() {
  out('COMMAND: node ignite/envelope/probes/probe-gtools-config-bridge.js');
  out('evidence-class: FIXTURE /var/tmp workspace + fixture scripts/auth.py (mirrors the REAL '
    + 'load_config env-var contract) + a private.json deny entry mirroring the real config.yaml '
    + 'mask; REAL admitLaunch + composeCageFor + materializeGtoolsConfig + bwrap');
  const fx = setupFixture('gcb-');
  const base = {
    workspaceRoot: fx.workspace, goalId: fx.goalId, goalDir: fx.goalDir, home: fx.home,
    tmpdir: require('node:os').tmpdir(), rbtvRepo: fx.rbtvRepo,
  };
  const seatPathA = parseSeatPath(fx.seatDirA);
  const seatPathB = parseSeatPath(fx.seatDirB);
  const scratchCopy = path.join(fx.goalDir, 'scratch', 'gtools-config.yaml');

  // ── RED — before any launch, no materialized copy exists ─────────────────────────────────
  check('RED no gtools config copy exists in scratch before any seat launches', !fs.existsSync(scratchCopy), scratchCopy);

  // ── admission still passes (unchanged behaviour) ──────────────────────────────────────────
  const admitted = admitLaunch({ ...base, seatDir: fx.seatDirA });
  check(
    'ADMIT the fixture account still admits the launch',
    admitted.spawn === true && (admitted.accountCredentials || []).includes('fixture-acct'),
    `spawn=${admitted.spawn} accounts=${JSON.stringify(admitted.accountCredentials)}`,
  );

  // ── GREEN 1 — seat A's launch sequence materializes the copy and advertises its path ──────
  let composedA;
  let composeErrA;
  try { composedA = composeCageFor({}, seatPathA, fx.seatDirA, null, () => {}); } catch (err) { composeErrA = err; }
  check('COMPOSE seat A composes a cage without throwing', Array.isArray(composedA), String(composeErrA && composeErrA.message));
  check('GREEN materializeGtoolsConfig wrote the copy into the goal scratch tree', fs.existsSync(scratchCopy), scratchCopy);
  const advertised = composedA ? envValue(composedA, 'IGNITE_GTOOLS_CONFIG') : null;
  check('GREEN IGNITE_GTOOLS_CONFIG is advertised and equals the materialized copy path', advertised === scratchCopy, `advertised=${advertised}`);
  check(
    'GREEN the copy is byte-identical to the source config.yaml',
    fs.readFileSync(scratchCopy, 'utf8') === fs.readFileSync(fx.configFile, 'utf8'),
  );

  // ── GREEN 2 — a caged process, deny mask in force, authenticates via env config ───────────
  const mintResult = await cagedRunAsync(composedA, fx.seatDirA, probePy(advertised, fx.configFile));
  let mintJson = null;
  try { mintJson = JSON.parse(mintResult.stdout); } catch { /* checked below */ }
  check(
    'REGRESSION (T2-R11/D19) the ORIGINAL config.yaml is unreadable inside the cage — the mask is intact',
    mintJson && mintJson.original_readable === false,
    `exit=${mintResult.exit} stdout=${mintResult.stdout} stderr=${mintResult.stderr}`,
  );
  check(
    'GREEN the caged process authenticates a real gtools SERVICE call path through the env-config route',
    mintResult.exit === 0 && mintJson && mintJson.ok === true
      && mintJson.token === 'fixture-config-bridge-token-not-a-real-secret'
      && Array.isArray(mintJson.accounts) && mintJson.accounts.includes('fixture-acct'),
    `stdout=${mintResult.stdout}`,
  );

  // ── STALE-COPY — edit config.yaml on disk, then launch seat B of the SAME goal ────────────
  fs.writeFileSync(fx.configFile, 'accounts:\n  fixture-acct:\n    email: fixture@example.com\n    credentials_dir: credentials/fixture-acct\n  second-acct:\n    email: second@example.com\n    credentials_dir: credentials/second-acct\nscopes: []\n');
  let composedB;
  let composeErrB;
  try { composedB = composeCageFor({}, seatPathB, fx.seatDirB, null, () => {}); } catch (err) { composeErrB = err; }
  check('COMPOSE seat B composes a cage without throwing', Array.isArray(composedB), String(composeErrB && composeErrB.message));
  const scratchAfterEdit = fs.readFileSync(scratchCopy, 'utf8');
  check(
    'STALE-COPY a config.yaml edit on disk reaches the NEXT seat launch of the goal, never permanently stale',
    scratchAfterEdit.includes('second-acct'),
    `scratch content: ${scratchAfterEdit.slice(0, 120)}`,
  );

  // ── NEGATIVE — env var pointing to a missing path fails LOUD, no silent fallback ─────────
  const missingPath = path.join(fx.goalDir, 'scratch', 'does-not-exist.yaml');
  // Rebuild the flag list with IGNITE_GTOOLS_CONFIG repointed at a nonexistent file, everything
  // else (the account resolution env, the cage shape) held exactly as composeCageFor produced it.
  const repointed = [];
  for (let i = 0; i < composedB.length; i += 1) {
    if (composedB[i] === '--setenv' && composedB[i + 1] === 'IGNITE_GTOOLS_CONFIG') {
      repointed.push('--setenv', 'IGNITE_GTOOLS_CONFIG', missingPath);
      i += 2;
    } else {
      repointed.push(composedB[i]);
    }
  }
  const negResult = await cagedRunAsync(repointed, fx.seatDirB, probePy(missingPath, fx.configFile));
  let negJson = null;
  try { negJson = JSON.parse(negResult.stdout); } catch { /* checked below */ }
  check(
    'NEGATIVE a missing IGNITE_GTOOLS_CONFIG target fails LOUD with a named error, never a silent fallback to the masked original',
    negJson && negJson.ok === false && /IGNITE_GTOOLS_CONFIG/.test(negJson.reason || ''),
    `stdout=${negResult.stdout}`,
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
