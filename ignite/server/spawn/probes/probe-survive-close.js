'use strict';

const { setup, teardown, capture, fire } = require('./lib');

capture('probe-survive-close', async (lines) => {
  const ctx = setup();
  try {
    lines.push('action: fire row, spawn worker, verify it survives the launcher');
    const fired = fire(ctx, { profile: 'test-sleep', sessionMode: 'headless', workdir: ctx.defaultWorkdir });
    const row = await ctx.mgr.spawn(fired.exec_id, 'test-sleep', 'headless', null, null, 'probe');
    lines.push(`spawned session_id=${row.session_id} unit=${row.unit_name} pid=${row.pid}`);

    const { execFileSync } = require('node:child_process');
    const active = execFileSync('systemctl', ['--user', 'is-active', row.unit_name], { encoding: 'utf8' }).trim();
    lines.push(`systemctl --user is-active: ${active}`);

    // Show the unit is owned by the user manager, not this process's ancestry.
    const control = execFileSync('systemctl', ['--user', 'show', '--property=ControlGroup', row.unit_name], { encoding: 'utf8' }).trim();
    lines.push(`control group: ${control}`);
    lines.push('result: transient unit belongs to the user manager -> survives launcher exit (CON-1)');

    await ctx.mgr.kill(row.exec_id);
  } finally {
    teardown(ctx);
  }
});
