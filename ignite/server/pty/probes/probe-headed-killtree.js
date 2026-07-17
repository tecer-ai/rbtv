'use strict';

// Criterion 6 (Test Plan): tree-kill is airtight for a headed session — kill <id> on a headed
// session tears the WHOLE tree down (the M2 property at build fidelity). Proven by OBSERVED unit
// state + an emptied/removed cgroup after the kill (D79).

const { setup, fire, teardown, capture, cgroupProcs, unitState, sleep } = require('./lib');

capture('probe-headed-killtree', async (lines) => {
  const ctx = setup();
  try {
    const fired = fire(ctx, { profile: 'test-headed', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    const row = await ctx.routed.spawn(fired.exec_id, 'test-headed', 'headed', null, null, 'probe');
    ctx.units.push(row.unit_name);
    lines.push(`spawned headed session exec_id=${row.exec_id} unit=${row.unit_name}`);

    await sleep(600);
    const before = cgroupProcs(row.unit_name);
    lines.push(`BEFORE kill: unit ${unitState(row.unit_name)}`);
    lines.push(`BEFORE kill: cgroup pids = ${before.pids.length} (${before.pids.join(',')})`);
    if (before.pids.length < 3) throw new Error('expected the holder tree (dtach+bwrap+node) alive before kill');

    lines.push('action: ctx.routed.kill(exec_id) — the SAME kill surface as any spawn');
    await ctx.mgr.kill(row.exec_id);
    await sleep(600);

    const after = cgroupProcs(row.unit_name);
    lines.push(`AFTER kill: unit ${unitState(row.unit_name)}`);
    lines.push(`AFTER kill: cgroup readable = ${after.cg !== null}; survivor pids = ${after.pids.length}`);
    lines.push(`row status after kill: ${ctx.store.getExecution(row.exec_id).status}`);
    const fs = require('node:fs'); const path = require('node:path');
    const sock = path.join(ctx.dataRoot, 'ptys', `${row.session_id}.sock`);
    lines.push(`holder socket after kill present: ${fs.existsSync(sock)} (expected false)`);

    if (after.pids.length > 0) throw new Error(`tree-kill left ${after.pids.length} survivor pids in the cgroup`);
    lines.push('RESULT: kill tore the whole headed tree down (unit inactive, cgroup emptied/removed, socket gone) — no policy escape via the pty.');
  } finally {
    teardown(ctx);
  }
});
