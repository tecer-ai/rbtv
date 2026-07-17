'use strict';

// Criterion 1 (session-surface-spec.md Test Plan): a headed session spawns behind the server's
// policy, IN a transient unit; the child is confined in the unit cgroup (the M1 property at build
// fidelity). Proven by OBSERVED cgroup membership — never POSIX reasoning (D79).

const { setup, fire, teardown, capture, cgroupProcs, cmdlineOf, unitState, sleep } = require('./lib');

capture('probe-headed-spawn', async (lines) => {
  const ctx = setup();
  try {
    const fired = fire(ctx, { profile: 'test-headed', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    lines.push(`action: spawn session_mode=headed profile=test-headed exec_id=${fired.exec_id}`);
    const row = await ctx.routed.spawn(fired.exec_id, 'test-headed', 'headed', null, null, 'probe');
    ctx.units.push(row.unit_name);
    lines.push(`spawned: session_id=${row.session_id} unit=${row.unit_name} pid=${row.pid} status=${row.status} session_mode=${row.session_mode}`);
    lines.push(`unit state: ${unitState(row.unit_name)}`);

    await sleep(600);
    const { cg, pids } = cgroupProcs(row.unit_name);
    lines.push(`ControlGroup=${cg}`);
    lines.push(`cgroup.procs (${pids.length} pids):`);
    let sawDtach = false, sawBwrap = false, sawNode = false;
    for (const pid of pids) {
      const cl = cmdlineOf(pid);
      lines.push(`  pid ${pid} -> ${cl.slice(0, 100)}`);
      if (/\bdtach\b/.test(cl)) sawDtach = true;
      if (/\bbwrap\b/.test(cl)) sawBwrap = true;
      if (/\bnode\b/.test(cl)) sawNode = true;
    }
    lines.push(`holder(dtach) in cgroup: ${sawDtach}`);
    lines.push(`sandbox(bwrap) in cgroup: ${sawBwrap}`);
    lines.push(`TUI(node) in cgroup: ${sawNode}`);
    // sock lives at data_root/ptys/<id>.sock (the in-unit holder socket).
    const fs = require('node:fs'); const path = require('node:path');
    const sock = path.join(ctx.dataRoot, 'ptys', `${row.session_id}.sock`);
    lines.push(`holder socket present: ${fs.existsSync(sock)} (${sock})`);

    if (!(sawDtach && sawBwrap && sawNode)) throw new Error('headed child not fully confined in the unit cgroup (expected dtach+bwrap+node)');
    if (row.session_mode !== 'headed') throw new Error(`row session_mode is ${row.session_mode}, expected headed`);
    if (!fs.existsSync(sock)) throw new Error('holder socket not created');
    lines.push('RESULT: headed session runs in a transient unit; child confined in the unit cgroup; policy did not move.');
  } finally {
    teardown(ctx);
  }
});
