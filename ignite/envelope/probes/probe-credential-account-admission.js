'use strict';

// DoD #1/#3 of `d-hold5-wire-the-broker`, the seat `broker-wire`: quotes today's REAL refusal
// shape for a fixture mirroring `transcript-summarizer-build`'s own manifest (three
// `gtools-account` entries named `pessoal`, `tecer`, `ignite` — the same three names
// `admitLaunch()` refuses on the live goal, per the loose end this seat closes), then proves
// admission now PASSES once the typed manifest shape's account files exist on disk. Never runs
// against the real `transcript-summarizer-build` goal or the real gtools accounts — fixture
// credential files only, under a throwaway `/var/tmp` workspace.

const fs = require('node:fs');
const path = require('node:path');
const { admitLaunch } = require('../launch');

const outPath = path.join(__dirname, 'probe-credential-account-admission.out');
fs.writeFileSync(outPath, '');
function out(line) { fs.appendFileSync(outPath, `${line}\n`); }
const checks = [];
function check(name, pass, detail) {
  checks.push(pass);
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

function mkdirp(p) { fs.mkdirSync(p, { recursive: true }); }
function touch(p, b) { mkdirp(path.dirname(p)); fs.writeFileSync(p, b == null ? '' : b); }

const ACCOUNTS = ['pessoal', 'tecer', 'ignite']; // the exact three names admitLaunch() refuses on the live goal

function setupFixture(prefix, { withAccountFiles }) {
  const root = fs.mkdtempSync(path.join('/var/tmp', prefix));
  const workspace = path.join(root, 'ws');
  const home = path.join(root, 'home');
  const goalDir = path.join(workspace, '.rbtv', 'goals', 'g');
  const seatDir = path.join(goalDir, 'seats', 's');
  mkdirp(path.join(goalDir, 'scratch'));
  mkdirp(seatDir);
  mkdirp(path.join(workspace, '.rbtv', 'mirror', 'x'));
  mkdirp(path.join(workspace, '.rbtv', 'config'));
  mkdirp(path.join(home, '.cache'));
  mkdirp(path.join(home, '.config', 'tool'));
  touch(path.join(workspace, '.rbtv', 'config', '.env'), '');
  touch(path.join(root, 'rbtv', 'ignite', 'envelope', 'spawn-profiles.yaml'), '');
  // The typed manifest shape `plan_envelope.py#_credential_names` now accepts — the exact
  // producer output for `transcript-summarizer-build`'s three accounts.
  fs.writeFileSync(path.join(goalDir, 'envelope.json'), JSON.stringify({
    credentialNames: ACCOUNTS.map((account) => ({ type: 'gtools-account', account })),
  }));
  if (withAccountFiles) {
    const gtoolsRoot = path.join(workspace, '3-resources', 'tools', 'gtools');
    for (const account of ACCOUNTS) {
      touch(path.join(gtoolsRoot, 'credentials', account, 'credentials.json'), '{"fixture":true}');
      touch(path.join(gtoolsRoot, 'credentials', account, 'token.json'), '{"fixture":true}');
    }
  }
  return { root, workspace, home, goalDir, seatDir };
}

function main() {
  out('COMMAND: node ignite/envelope/probes/probe-credential-account-admission.js');
  out('evidence-class: FIXTURE /var/tmp workspace mirroring transcript-summarizer-build\'s own three-account manifest; REAL admitLaunch');

  // ── RED — quotes today's real refusal shape for the three declared accounts, files absent ──
  const red = setupFixture('cred-admit-red-', { withAccountFiles: false });
  const refused = admitLaunch({
    workspaceRoot: red.workspace, goalId: 'g', goalDir: red.goalDir, seatDir: red.seatDir,
    home: red.home, tmpdir: require('node:os').tmpdir(), rbtvRepo: path.join(red.root, 'rbtv'),
  });
  check(
    'RED admitLaunch() refuses missing-credential for pessoal, tecer, ignite — the exact shape the live goal hits today',
    refused.spawn === false && refused.refuse && refused.refuse.kind === 'missing-credential'
      && ACCOUNTS.every((a) => refused.refuse.missing.includes(`gtools-account:${a}`)),
    JSON.stringify(refused.refuse),
  );
  try { fs.rmSync(red.root, { recursive: true, force: true }); } catch { /* best effort */ }

  // ── GREEN — the same three-account manifest, files now present, admits ────────────────────
  const green = setupFixture('cred-admit-green-', { withAccountFiles: true });
  const admitted = admitLaunch({
    workspaceRoot: green.workspace, goalId: 'g', goalDir: green.goalDir, seatDir: green.seatDir,
    home: green.home, tmpdir: require('node:os').tmpdir(), rbtvRepo: path.join(green.root, 'rbtv'),
  });
  check(
    'GREEN admitLaunch() admits once all three accounts\' login files exist — no missing-credential refusal',
    admitted.spawn === true && ACCOUNTS.every((a) => (admitted.accountCredentials || []).includes(a)),
    `spawn=${admitted.spawn} accounts=${JSON.stringify(admitted.accountCredentials)} refuse=${JSON.stringify(admitted.refuse)}`,
  );
  try { fs.rmSync(green.root, { recursive: true, force: true }); } catch { /* best effort */ }

  const failed = checks.filter((p) => !p).length;
  out(failed === 0 ? 'ALL LEGS PASS' : `FAILED ${failed}/${checks.length}`);
  process.exit(failed === 0 ? 0 : 1);
}

main();
