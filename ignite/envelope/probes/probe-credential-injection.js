'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { admitLaunch } = require('../launch');
const { parseSeatPath } = require('../../runtime/seat-identity/seat-folder');
const { buildBwrapArgv } = require('../../supervisor/spawn/bwrap');
const { composeCageFor } = require('../../supervisor/spawn/spawn');

const FIXTURE_TMP = '/var/tmp';
const outPath = path.join(__dirname, 'probe-credential-injection.out');
fs.writeFileSync(outPath, '');

function out(line) {
  fs.appendFileSync(outPath, line + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push(pass);
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

function mkdirp(p) { fs.mkdirSync(p, { recursive: true }); }
function touch(p, b) { mkdirp(path.dirname(p)); fs.writeFileSync(p, b == null ? '' : b); }

function setupFixture(prefix) {
  fs.mkdirSync(FIXTURE_TMP, { recursive: true });
  const root = fs.mkdtempSync(path.join(FIXTURE_TMP, prefix));
  const workspace = path.join(root, 'ws');
  const home = path.join(root, 'home');
  const rbtvRepo = path.join(root, 'rbtv');
  const goalId = 'test-cred-injection';
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
  touch(path.join(workspace, '.rbtv', 'config', '.env'), 'ELEVENLABS_API_KEY=fixture-not-a-real-secret\n');
  touch(path.join(seatDir, 'seat.md'), ['---', 'seat: prober', 'harness: bash', 'model: test-sleep', '---', ''].join('\n'));
  return { root, workspace, home, rbtvRepo, goalId, goalDir, seatDir };
}

function cagedPrint(composed, seatDir, py) {
  const argv = buildBwrapArgv({
    argv: ['python3', '-c', py],
    workdir: seatDir,
    harness: null,
    seatBinds: composed,
  });
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

function main() {
  out('COMMAND: node ignite/envelope/probes/probe-credential-injection.js');
  out('evidence-class: FIXTURE /var/tmp workspace; REAL admitLaunch + composeCageFor + bwrap');
  const fx = setupFixture('cred-inj-');
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
  const envPy = 'import os; print(os.environ.get("ELEVENLABS_API_KEY","ABSENT"))';
  const maskPy = `import os; p=${JSON.stringify(path.join(fx.workspace, '.rbtv', 'config', '.env'))}; print("READ" if os.path.exists(p) and open(p).read().strip() else "ABSENT-FILE")`;

  const noFill = admitLaunch({ ...base, fillIns: null });
  let composedEmpty;
  let emptyErr;
  try { composedEmpty = composeCageFor({}, seatPath, fx.seatDir, null, () => {}); }
  catch (err) { emptyErr = err; }
  const emptyPrint = Array.isArray(composedEmpty)
    ? cagedPrint(composedEmpty, fx.seatDir, envPy)
    : { exit: -1, stdout: 'COMPOSE-FAILED', stderr: String(emptyErr && emptyErr.message) };
  check(
    'L1 no envelope.json → caged print ABSENT',
    noFill.spawn === true && JSON.stringify(noFill.credentialNames) === '[]'
      && emptyPrint.exit === 0 && emptyPrint.stdout === 'ABSENT',
    `spawn=${noFill.spawn} names=${JSON.stringify(noFill.credentialNames)} print=${emptyPrint.stdout} exit=${emptyPrint.exit}`,
  );

  fs.writeFileSync(path.join(fx.goalDir, 'envelope.json'), JSON.stringify({
    credentialNames: ['NO_SUCH_FIXTURE_KEY'],
  }) + '\n');
  const missing = admitLaunch(base);
  let missingComposeErr;
  try { composeCageFor({}, seatPath, fx.seatDir, null, () => {}); }
  catch (err) { missingComposeErr = err; }
  check(
    'L2 declared absent name refuses launch',
    missing.spawn === false && missing.refuse && missing.refuse.kind === 'missing-credential'
      && Array.isArray(missing.refuse.missing) && missing.refuse.missing.includes('NO_SUCH_FIXTURE_KEY')
      && missingComposeErr && missingComposeErr.code === 'E_LAUNCH_REFUSED',
    `spawn=${missing.spawn} refuse=${JSON.stringify(missing.refuse)} composeErr=${missingComposeErr && missingComposeErr.code}`,
  );

  fs.writeFileSync(path.join(fx.goalDir, 'envelope.json'), JSON.stringify({
    credentialNames: ['ELEVENLABS_API_KEY'],
  }) + '\n');
  const filled = admitLaunch(base);
  let composed;
  let composeErr;
  try { composed = composeCageFor({}, seatPath, fx.seatDir, null, () => {}); }
  catch (err) { composeErr = err; }
  const hasSetenv = Array.isArray(composed) && composed.some((a, i) => (
    a === '--setenv' && composed[i + 1] === 'ELEVENLABS_API_KEY'
  ));
  const presentPrint = Array.isArray(composed)
    ? cagedPrint(composed, fx.seatDir, envPy)
    : { exit: -1, stdout: 'COMPOSE-FAILED', stderr: String(composeErr && composeErr.message) };
  check(
    'L3 envelope.json ELEVENLABS_API_KEY is present inside the cage',
    filled.spawn === true && hasSetenv && presentPrint.exit === 0
      && presentPrint.stdout === 'fixture-not-a-real-secret',
    `spawn=${filled.spawn} setenv=${hasSetenv} print=${presentPrint.stdout} err=${composeErr && composeErr.message}`,
  );

  const masked = Array.isArray(composed)
    ? cagedPrint(composed, fx.seatDir, maskPy)
    : { exit: -1, stdout: 'COMPOSE-FAILED', stderr: '' };
  const maskedOk = masked.stdout === 'ABSENT-FILE' || masked.exit !== 0;
  check(
    'L4 canonical .env stays masked inside the cage',
    maskedOk,
    `exit=${masked.exit} stdout=${masked.stdout} stderr=${masked.stderr}`,
  );

  try { fs.rmSync(fx.root, { recursive: true, force: true }); } catch { /* best effort */ }
  const failed = checks.filter((p) => !p).length;
  out(failed === 0 ? 'ALL LEGS PASS' : `FAILED ${failed}/${checks.length}`);
  process.exit(failed === 0 ? 0 : 1);
}

main();
