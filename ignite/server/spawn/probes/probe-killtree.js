'use strict';

const { setup, teardown, capture, fire } = require('./lib');

capture('probe-killtree', async (lines) => {
  const ctx = setup();
  try {
    lines.push('action: fire row, spawn forker worker, kill it, verify whole tree gone');
    const fired = fire(ctx, { profile: 'test-forker', sessionMode: 'headless', workdir: ctx.defaultWorkdir });
    const row = await ctx.mgr.spawn(fired.exec_id, 'test-forker', 'headless', null, null, 'probe');
    lines.push(`spawned session_id=${row.session_id} unit=${row.unit_name} pid=${row.pid}`);

    const { execFileSync } = require('node:child_process');
    const activeBefore = execFileSync('systemctl', ['--user', 'is-active', row.unit_name], { encoding: 'utf8' }).trim();
    lines.push(`is-active before kill: ${activeBefore}`);

    // List PIDs in the cgroup before kill.
    const cgroupBefore = execFileSync('systemctl', ['--user', 'show', '--property=ControlGroup', row.unit_name], { encoding: 'utf8' }).trim();
    lines.push(`cgroup before: ${cgroupBefore}`);

    await ctx.mgr.kill(row.exec_id);

    const activeAfter = (() => {
      try { return execFileSync('systemctl', ['--user', 'is-active', row.unit_name], { encoding: 'utf8' }).trim(); }
      catch { return 'inactive'; }
    })();
    lines.push(`is-active after kill: ${activeAfter}`);

    // Check no survivor PIDs by re-scanning the cgroup path.
    let survivors = 'n/a';
    try {
      const cgPath = cgroupBefore.replace(/^ControlGroup=/, '');
      const procs = require('node:fs').readFileSync(`/sys/fs/cgroup${cgPath}/cgroup.procs`, 'utf8').trim();
      survivors = procs.length > 0 ? procs.split('\n').length : 0;
    } catch {
      survivors = 0;
    }
    lines.push(`survivor PIDs in cgroup: ${survivors}`);
    lines.push(`row status after kill: ${ctx.store.getExecution(row.exec_id).status}`);
  } finally {
    teardown(ctx);
  }
});
