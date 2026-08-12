'use strict';

const { setup, teardown, capture, fire } = require('./lib');

capture('probe-killtree', async (lines) => {
  const ctx = setup();
  try {
    lines.push('action: fire row, spawn forker worker, kill it, verify whole tree gone');
    const fired = fire(ctx, { cast: 'test-forker', sessionMode: 'headless', workdir: ctx.seatDir });
    const row = await ctx.mgr.spawn(fired.exec_id, 'headless', null, ctx.seatDir, 'probe');
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
    // ASSERT, never merely record: this probe is the sole guard of whole-tree kill containment and
    // every line below used to be a `lines.push` — a surviving unit, a live process tree and a row
    // still marked `running` all read PASS.
    if (activeAfter !== 'inactive') {
      throw new Error(`is-active after kill: '${activeAfter}' != 'inactive' — the unit survived the kill`);
    }
    lines.push(`is-active after kill: ${activeAfter}`);

    // Check no survivor PIDs by re-scanning the cgroup path. A read failure is LOUD: the old
    // `catch { survivors = 0 }` reported perfect containment for a cgroup it could not read, which
    // is the same PASS a real zero gives. ENOENT is the ONE honest zero — systemd removes the
    // cgroup with the unit, so a missing path IS the tree being gone.
    // The PREMISE of that scan, asserted first: an empty/garbage ControlGroup would leave cgPath ''
    // and point the read at the ROOT cgroup — readable, and near-certainly empty, so the survivor
    // assertion below would pass while scanning nothing to do with this unit.
    const cgPath = cgroupBefore.replace(/^ControlGroup=/, '');
    if (!cgPath.startsWith('/') || !cgPath.includes(row.unit_name)) {
      throw new Error(`cgroup before kill '${cgroupBefore}' names no cgroup for ${row.unit_name} — the survivor scan below would be vacuous`);
    }
    let survivors;
    try {
      const procs = require('node:fs').readFileSync(`/sys/fs/cgroup${cgPath}/cgroup.procs`, 'utf8').trim();
      survivors = procs.length > 0 ? procs.split('\n').length : 0;
    } catch (err) {
      if (err.code !== 'ENOENT') throw err;
      survivors = 0;
      lines.push(`cgroup ${cgPath} gone (ENOENT) — removed with the unit, so the tree went with it`);
    }
    if (survivors !== 0) {
      throw new Error(`survivor PIDs in cgroup: ${survivors} != 0 — the kill left part of the tree alive`);
    }
    lines.push(`survivor PIDs in cgroup: ${survivors}`);

    const statusAfter = ctx.store.getExecution(row.exec_id).status;
    if (statusAfter !== 'killed') {
      throw new Error(`row status after kill: '${statusAfter}' != 'killed'`);
    }
    lines.push(`row status after kill: ${statusAfter}`);
  } finally {
    teardown(ctx);
  }
});
