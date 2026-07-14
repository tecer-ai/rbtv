'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');

function isActive(unit) {
  try {
    return execFileSync('systemctl', ['--user', 'is-active', unit], { encoding: 'utf8' }).trim();
  } catch (e) {
    return (e.stdout || 'inactive').toString().trim() || 'inactive';
  }
}

function pidAlive(pid) {
  try { fs.accessSync(`/proc/${pid}`); return true; } catch { return false; }
}

function workerPPid(pid) {
  try {
    const stat = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
    const rparen = stat.lastIndexOf(')');
    const rest = stat.slice(rparen + 2).trim().split(/\s+/);
    return parseInt(rest[1], 10); // field 4 (ppid) = index 1 after state
  } catch { return null; }
}

// CON-1: prove the worker survives its LAUNCHER exiting — not merely infer it from ownership.
// A separate `node` child (the launching process) fires a row and spawns the worker, then EXITS.
// The parent then confirms the worker is still active AND the launcher PID is gone.
capture('probe-survive-close', async (lines) => {
  const libPath = path.join(__dirname, 'lib.js');
  const childScript = `
    const { setup, fire } = require(${JSON.stringify(libPath)});
    (async () => {
      const ctx = setup();
      const fired = fire(ctx, { profile: 'test-sleep', sessionMode: 'headless', workdir: ctx.defaultWorkdir });
      const row = await ctx.mgr.spawn(fired.exec_id, 'test-sleep', 'headless', null, null, 'probe');
      process.stdout.write(JSON.stringify({ unit: row.unit_name, pid: row.pid, tmp: ctx.tmp, launcherPid: process.pid }));
      // Deliberately DO NOT teardown: leave the worker running and exit the launcher.
      process.exit(0);
    })().catch((e) => { process.stderr.write(String((e && e.stack) || e)); process.exit(1); });
  `;

  lines.push('action: a child node LAUNCHER spawns the worker then EXITS; re-check worker survives');
  const out = execFileSync('node', ['-e', childScript], { encoding: 'utf8' });
  const info = JSON.parse(out);
  lines.push(`launcher(child node) pid=${info.launcherPid} spawned unit=${info.unit} worker-pid=${info.pid}`);

  // execFileSync has returned => the launcher process has exited.
  const launcherGone = !pidAlive(info.launcherPid);
  const active = isActive(info.unit);
  const ppid = workerPPid(info.pid);
  lines.push(`after launcher exit: launcher-pid-alive=${!launcherGone} worker is-active=${active} worker-ppid=${ppid} (launcher-pid=${info.launcherPid})`);
  lines.push('result: launcher process is gone yet the worker is still active; worker PPID is the user manager, never the (dead) launcher (CON-1)');

  try {
    // Cleanup: stop the unit and remove the launcher's temp dir.
    execFileSync('systemctl', ['--user', 'stop', info.unit], { stdio: 'ignore' });
  } catch {}
  try { fs.rmSync(info.tmp, { recursive: true, force: true }); } catch {}

  if (!launcherGone || active !== 'active' || ppid === info.launcherPid) {
    throw new Error(`survive-close not proven: launcherGone=${launcherGone} active=${active} ppid=${ppid}`);
  }
});
