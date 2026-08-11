'use strict';

// Resolve a python interpreter that ACTUALLY RUNS python. Extracted from the probe-suite runner
// (task 7.700) so every site that shells out to python shares ONE detection instead of hardcoding
// `python3` and hitting the same lie one level deeper (task 7.706).
//
// WHY: `python3` IS NOT AN INTERPRETER ON WINDOWS — it is usually a lie. Windows ships a
// Microsoft-Store app-execution alias at `%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe` that is
// ON PATH, IS EXECUTABLE, AND RUNS NO PYTHON: it prints "Python was not found; run without
// arguments to install from the Microsoft Store" and exits non-zero. A `where python3` LOOKUP finds
// it; only EXECUTING it and reading its exit code + output tells the alias from a real interpreter.
// Probed ONCE per process, in PATH order; first candidate that reports `Python <n>` on exit 0 wins.
// POSIX IS BYTE-UNCHANGED: `python3 --version` exits 0 saying `Python 3.x` there, so `python3` is
// still what every caller spawns; the `python` fallback is reachable only where `python3` is absent
// or the alias.

const { spawnSync } = require('node:child_process');

let cachedPython;
function pythonCmd() {
  if (cachedPython !== undefined) return cachedPython;
  cachedPython = null;
  for (const cmd of ['python3', 'python']) {
    const r = spawnSync(cmd, ['--version'], { encoding: 'utf8', timeout: 15000 });
    if (r.error || r.status !== 0) continue;
    if ([r.stdout, r.stderr].some((s) => /^Python \d/.test(String(s || '').trim()))) {
      cachedPython = cmd;
      break;
    }
  }
  return cachedPython;
}

// For a caller that CANNOT proceed without python: an honest refusal instead of spawning the alias
// and getting its cryptic "install from the Microsoft Store" failure — the exact defect 7.700 was
// born to kill. POSIX still returns `python3`, so spawns there are byte-unchanged.
function requirePythonCmd() {
  const cmd = pythonCmd();
  if (cmd === null) {
    throw new Error(
      'no working python3 interpreter found — `python3` and `python` are both absent or resolve to '
      + 'the Windows Microsoft-Store alias (which runs no python). Install Python or put a real '
      + 'interpreter on PATH.');
  }
  return cmd;
}

module.exports = { pythonCmd, requirePythonCmd };

// Self-check: the resolved command must EXECUTE python, not merely exist on PATH (the alias bug).
if (require.main === module) {
  const assert = require('node:assert');
  const cmd = pythonCmd();
  if (cmd === null) {
    assert.throws(requirePythonCmd, /no working python3 interpreter/);
    console.log('python-cmd selftest OK (no interpreter on this box; refusal is honest)');
  } else {
    const r = spawnSync(cmd, ['-c', 'print("live")'], { encoding: 'utf8', timeout: 15000 });
    assert(!r.error && r.status === 0 && /live/.test(String(r.stdout || '')),
      `resolved '${cmd}' does not run python: status=${r.status} stderr=${r.stderr}`);
    assert.strictEqual(requirePythonCmd(), cmd);
    console.log(`python-cmd selftest OK (resolved '${cmd}')`);
  }
}
