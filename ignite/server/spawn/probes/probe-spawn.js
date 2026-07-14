'use strict';

const { setup, teardown, capture, fire } = require('./lib');

capture('probe-spawn', async (lines) => {
  const ctx = setup();
  try {
    lines.push('action: fire row then spawn trivial worker via test-sleep profile');
    const fired = fire(ctx, { profile: 'test-sleep', sessionMode: 'headless', workdir: ctx.defaultWorkdir });
    lines.push(`exec_id before spawn: ${fired.exec_id}, status: ${fired.status}`);

    const row = await ctx.mgr.spawn(fired.exec_id, 'test-sleep', 'headless', null, null, 'probe');
    lines.push(`exec_id after spawn: ${row.exec_id}`);
    lines.push(`session_id: ${row.session_id}`);
    lines.push(`pid: ${row.pid}`);
    lines.push(`carrier: ${row.carrier}`);
    lines.push(`unit_name: ${row.unit_name}`);
    lines.push(`status: ${row.status}`);
    lines.push(`log_path: ${row.log_path}`);
    lines.push(`workdir: ${row.workdir}`);

    // Prove the unit exists and carries the profile's caps.
    const { execFileSync } = require('node:child_process');
    const show = execFileSync('systemctl', ['--user', 'show', '--property=MemoryMax,MemoryMaxUSec,CPUQuota,RuntimeMaxSec,RuntimeMaxUSec,TasksMax', row.unit_name], { encoding: 'utf8' });
    lines.push('systemctl --user show caps:');
    for (const line of show.split('\n')) {
      if (line.trim()) lines.push('  ' + line.trim());
    }

    // Prove the worker is actually running.
    const active = execFileSync('systemctl', ['--user', 'is-active', row.unit_name], { encoding: 'utf8' }).trim();
    lines.push(`systemctl --user is-active: ${active}`);

    // Prove the log file exists.
    lines.push(`log file exists: ${require('node:fs').existsSync(row.log_path)}`);

    // Clean up.
    await ctx.mgr.kill(row.exec_id);
  } finally {
    teardown(ctx);
  }
});
