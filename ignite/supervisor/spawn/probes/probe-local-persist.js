'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { capture, fixtureRoot } = require('./lib');
const { parseSeatPath } = require('../../../runtime/seat-identity/seat-folder');
const { buildBwrapArgv } = require('../bwrap');
const { composeCageFor } = require('../spawn');

const PKG = 'rbtv_cage_persist';
const IMPORT = `import ${PKG}; print(${PKG}.__file__)`;

function fixture() {
  const root = fixtureRoot('local-persist-');
  const workspace = path.join(root, 'ws');
  const goalDir = path.join(workspace, '.rbtv', 'goals', 'test-local-persist');
  const seatDir = path.join(goalDir, 'seats', 'worker');
  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.mkdirSync(path.join(workspace, '.rbtv', 'mirror', 'x'), { recursive: true });
  fs.mkdirSync(seatDir, { recursive: true });
  fs.writeFileSync(path.join(goalDir, 'sessions.csv'), 'seat,session-id,pid,pid-starttime\n');
  fs.writeFileSync(path.join(seatDir, 'seat.md'), [
    '---',
    'seat: worker',
    'harness: bash',
    'model: test-sleep',
    'local-bin: true',
    '---',
    '',
  ].join('\n'));
  const pkgDir = path.join(seatDir, 'dummy-pkg');
  fs.mkdirSync(path.join(pkgDir, PKG), { recursive: true });
  fs.writeFileSync(path.join(pkgDir, PKG, '__init__.py'), 'marker = "persist"\n');
  fs.writeFileSync(path.join(pkgDir, 'setup.py'), [
    'from setuptools import setup',
    `setup(name="${PKG.replace(/_/g, '-')}", version="0.0.1", packages=["${PKG}"])`,
    '',
  ].join('\n'));
  return { root, workspace, goalDir, seatDir, pkgDir };
}

function inCage(seatDir, flags, script) {
  const argv = buildBwrapArgv({
    argv: ['bash', '-c', script],
    workdir: seatDir,
    harness: null,
    seatBinds: flags,
  });
  try {
    const stdout = execFileSync(argv[0], argv.slice(1), {
      stdio: ['ignore', 'pipe', 'pipe'], timeout: 60000, encoding: 'utf8',
    });
    return { exit: 0, stdout: String(stdout) };
  } catch (err) {
    return {
      exit: err.status === undefined ? -1 : err.status,
      stdout: String(err.stdout || ''),
      stderr: String(err.stderr || '').trim().slice(0, 400),
    };
  }
}

capture('probe-local-persist', async (lines) => {
  const f = fixture();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };
  try {
    const seatPath = parseSeatPath(f.seatDir);
    const homeLocal = path.join(os.homedir(), '.local');
    const persistSrc = path.join(f.seatDir, '.user-local');
    const hostImport = () => {
      try {
        return execFileSync('python3', ['-c', IMPORT], {
          encoding: 'utf8', timeout: 10000, stdio: ['ignore', 'pipe', 'pipe'],
        });
      } catch {
        return 'ABSENT';
      }
    };
    const hostSiteBefore = hostImport();

    const sitting1Flags = composeCageFor({}, seatPath, f.seatDir, null, () => {});
    const bindIdx = Array.isArray(sitting1Flags)
      ? sitting1Flags.findIndex((a, i) => a === '--bind' && sitting1Flags[i + 1] === persistSrc && sitting1Flags[i + 2] === homeLocal)
      : -1;
    leg('1', 'composeCageFor binds per-seat .user-local at ~/.local (not the host tree as source)',
      Array.isArray(sitting1Flags) && bindIdx >= 0,
      `bindIdx=${bindIdx} persistSrc=${persistSrc}`);

    const sitting1 = inCage(f.seatDir, sitting1Flags,
      `python3 -m pip install --user --break-system-packages --no-warn-script-location "${f.pkgDir}" && python3 -c "${IMPORT}"`);
    const sitting1Import = sitting1.exit === 0 && sitting1.stdout.includes(PKG);
    leg('2', 'sitting 1 pip --user install is importable',
      sitting1Import,
      `exit=${sitting1.exit} stdout=${sitting1.stdout.trim()} stderr=${sitting1.stderr || ''}`);

    const sitting2Flags = composeCageFor({}, seatPath, f.seatDir, null, () => {});
    const sitting2 = inCage(f.seatDir, sitting2Flags, `python3 -c "${IMPORT}"`);
    const sitting2Import = sitting2.exit === 0 && sitting2.stdout.includes(PKG);
    leg('3', 'sitting 2 of the SAME seat imports with no pip',
      sitting2Import,
      `exit=${sitting2.exit} stdout=${sitting2.stdout.trim()} stderr=${sitting2.stderr || ''}`);

    const hostAfter = hostImport();
    const hostUntouched = hostSiteBefore === 'ABSENT' && hostAfter === 'ABSENT';
    const persistHasPkg = fs.existsSync(persistSrc) && (() => {
      try {
        return fs.readdirSync(persistSrc, { recursive: true }).some((n) => String(n).includes(PKG));
      } catch {
        return false;
      }
    })();
    leg('4', 'host ~/.local is untouched; package lives in the per-seat store',
      hostUntouched && persistHasPkg,
      `hostBefore=${hostSiteBefore === 'ABSENT' ? 'ABSENT' : 'PRESENT'} hostAfter=${hostAfter === 'ABSENT' ? 'ABSENT' : 'PRESENT'} persistHasPkg=${persistHasPkg}`);
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch { /* best effort */ }
  }
  if (fails.length > 0) throw new Error(`FAILED LEGS: ${fails.join(', ')}`);
});
