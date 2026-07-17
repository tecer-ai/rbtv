'use strict';

// ★ Amendment #5 DECISION — the no-shell status-capture shim (spec Design 2 caveat 1, option i),
// probe-verified to the M1/M2 standard this task (recon5: in-cgroup, tree-killed, TUI still
// renders + receives keys, TRUE child exit captured while the unit's ExecMainStatus stayed 0).
//
// WHY IT EXISTS: M3 measured that the unit's `ExecMainStatus` MASKS the harness exit code (child
// exited 42, unit reported 0), because the unit's main process is the dtach holder, not the TUI.
// A masked `0` copied onto the row is the ONE FORBIDDEN outcome (spec Behavior #8). This shim is
// exec'd INSIDE the same unit/cgroup, immediately around the TUI: it forks the TUI, inherits the
// pty slave stdio (so the TUI is on the pty exactly as before — the shim does NOT setsid/setpgid,
// so the TUI stays in the shim's process group = the pty's foreground group, keeping keyboard
// signals and kernel SIGWINCH transparent), waitpid()s it, and writes the EXACT status to a file
// the daemon reads. NO shell is spawned — child_process.spawn execs argv directly.
//
// Usage:  node pty-status-shim.js <status-file> <tui-argv...>
// Writes: {"code": <exit code|null>, "signal": <name|null>} (or {"error": "..."} on spawn failure)

const { spawn } = require('node:child_process');
const fs = require('node:fs');

function writeStatus(statusFile, obj) {
  try {
    fs.writeFileSync(statusFile, JSON.stringify(obj));
  } catch {
    // The daemon falls back to a typed `unknown` exit_code if the status file is unreadable;
    // never crash the exit path over the status write.
  }
}

function main() {
  const statusFile = process.argv[2];
  const argv = process.argv.slice(3);
  if (!statusFile || argv.length === 0) {
    process.stderr.write('pty-status-shim: usage: node pty-status-shim.js <status-file> <argv...>\n');
    process.exit(2);
    return;
  }

  const child = spawn(argv[0], argv.slice(1), { stdio: 'inherit' });

  child.on('error', (err) => {
    writeStatus(statusFile, { error: String(err && err.message ? err.message : err) });
    process.exit(127);
  });

  child.on('exit', (code, signal) => {
    writeStatus(statusFile, { code: code === undefined ? null : code, signal: signal || null });
    // Re-raise the child's exit shape so the holder's own exit is at least consistent (the unit
    // still masks it — the status file is the authoritative source the daemon reads).
    if (signal) {
      process.kill(process.pid, signal);
      // If the signal did not terminate us (rare), fall through to an explicit non-zero exit.
      process.exit(128);
    }
    process.exit(code === null || code === undefined ? 0 : code);
  });
}

main();
