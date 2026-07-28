'use strict';

// ═════════════════════════════════════════════════════════════════════════════════════════════
// THE SUPERVISOR — boundary 8 (own process group) and boundary 4 (dies with the dispatching step).
//
// Run as: node supervisor.js <spec.json>
// Spawned DETACHED by dispatch.js, so setsid(2) gives it a new session and a new process group
// whose leader it is: `kill(-supervisorPid)` therefore reaches the harness and every descendant
// the harness starts. That is CMP-10 boundary 8's "one kill cleans the tree", and it is why the
// harness is NOT spawned detached in turn — a second setsid would put the harness in a group the
// supervisor's kill could not reach, which is the same defect wearing the fix's clothes.
//
// ⚠ WHY A SUPERVISOR EXISTS AT ALL, rather than the dispatcher spawning the harness directly.
// Boundary 4 says the sub-agent dies with the dispatching step. A dispatcher can honour that on
// its own EXIT — but not on its own SIGKILL, because SIGKILL runs no handler. Task 7.43's criterion
// is precisely "killing the dispatcher MID-RUN and observing the whole tree die", so an exit
// handler would satisfy the sentence and fail the test.
//
// THE DEATH PIPE is the mechanism that survives SIGKILL: the dispatcher holds the WRITE end of a
// pipe whose READ end is this process's fd 3. Nothing is ever sent through it. When the dispatcher
// dies — by any means, including SIGKILL, including the terminal going away — the kernel closes
// the write end and this process reads EOF. That EOF is the death signal, it is delivered by the
// kernel rather than by anyone's cooperation, and it cannot be forgotten.
//
// It records the VARIABLE NAMES of its own environment to `env-names.json` and never a value
// (`bars.md` 8: capture the call and its result, never the credential). Because this process is
// itself launched with the scrubbed environment and hands its own `process.env` to the harness,
// that file is a true readout of what boundary 11 actually let through — not a claim about it.
// ═════════════════════════════════════════════════════════════════════════════════════════════

const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const { spawn } = require('node:child_process');

const DEATH_PIPE_FD = 3;
const TERM_GRACE_MS = 3000;

function main() {
  const specPath = process.argv[2];
  if (!specPath) {
    process.stderr.write('supervisor: no spec file\n');
    process.exit(64);
  }
  const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
  const { argv, workdir, promptFile, sessionDir } = spec;

  // Variable NAMES only — never values.
  fs.writeFileSync(
    path.join(sessionDir, 'env-names.json'),
    JSON.stringify({ pid: process.pid, pgid: process.pid, names: Object.keys(process.env).sort() }, null, 2),
    { mode: 0o600 },
  );

  const stdoutFile = fs.createWriteStream(path.join(sessionDir, 'stdout.log'), { mode: 0o600 });
  const stderrFile = fs.createWriteStream(path.join(sessionDir, 'stderr.log'), { mode: 0o600 });

  const child = spawn(argv[0], argv.slice(1), {
    cwd: workdir,
    env: process.env,
    stdio: ['pipe', 'pipe', 'pipe'],
    // NOT detached — see the header. It must stay in THIS process group.
  });

  // Results return to the dispatcher through this process's own stdout/stderr (pipes the
  // dispatcher holds) AND to files in the session dir. There is no third destination: boundary 3
  // (no coordination access) is carried by the environment and PATH the dispatcher composed, and
  // reinforced here by there being nowhere else for output to go.
  child.stdout.on('data', (b) => { process.stdout.write(b); stdoutFile.write(b); });
  child.stderr.on('data', (b) => { process.stderr.write(b); stderrFile.write(b); });

  // The headless carriage is stdin, and the profile declares it (`exec.prompt: stdin`). Written
  // then CLOSED: codex hangs without an EOF from a non-TTY, and claude waits for one too.
  if (promptFile) child.stdin.write(fs.readFileSync(promptFile));
  child.stdin.end();

  let killing = false;
  const killTree = (why) => {
    if (killing) return;
    killing = true;
    try { fs.writeFileSync(path.join(sessionDir, 'killed.json'), JSON.stringify({ why, at: new Date().toISOString() }), { mode: 0o600 }); } catch { /* the tree is going down; a missing note must not stop it */ }
    // Negative pid = the whole process group, of which this process is the leader.
    try { process.kill(-process.pid, 'SIGTERM'); } catch { /* already gone */ }
    setTimeout(() => {
      try { process.kill(-process.pid, 'SIGKILL'); } catch { /* already gone */ }
    }, TERM_GRACE_MS).unref();
  };

  // ── the death pipe ─────────────────────────────────────────────────────────────────────────
  let deathPipe = null;
  try {
    deathPipe = new net.Socket({ fd: DEATH_PIPE_FD, readable: true, writable: false });
  } catch (err) {
    // No death pipe means no boundary-4 guarantee. FAIL CLOSED: refuse to run rather than run a
    // sub-agent nothing can be sure of killing.
    process.stderr.write(`supervisor: no death pipe on fd ${DEATH_PIPE_FD} (${err.message}) — refusing\n`);
    try { child.kill('SIGKILL'); } catch { /* not started */ }
    process.exit(70);
  }
  deathPipe.resume();
  deathPipe.on('end', () => killTree('dispatcher-gone'));
  deathPipe.on('close', () => killTree('dispatcher-gone'));
  deathPipe.on('error', () => killTree('dispatcher-gone'));

  child.on('exit', (code, signal) => {
    try {
      fs.writeFileSync(
        path.join(sessionDir, 'result.json'),
        JSON.stringify({ exitCode: code, signal, supervisorPid: process.pid, pgid: process.pid }, null, 2),
        { mode: 0o600 },
      );
    } catch { /* best effort; the exit code below is the authority */ }
    stdoutFile.end();
    stderrFile.end();
    // Leave the group cleanly: nothing else should be running in it, but a harness that forked and
    // detached its own children would leave strays, and this is the one moment we can still see it.
    setTimeout(() => process.exit(signal ? 128 : (code === null ? 1 : code)), 50).unref();
  });

  child.on('error', (err) => {
    process.stderr.write(`supervisor: cannot exec ${argv[0]}: ${err.message}\n`);
    process.exit(71);
  });
}

main();
