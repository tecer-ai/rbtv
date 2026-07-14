'use strict';

const { setup, teardown, capture, fire } = require('./lib');

capture('probe-mode-gate', async (lines) => {
  const ctx = setup();
  try {
    const cases = [
      { name: 'headed on non-headed profile', fn: () => ctx.mgr.spawn(0, 'test-sleep', 'headed', null, null, 'probe') },
      { name: 'unknown mode', fn: () => ctx.mgr.spawn(0, 'test-sleep', 'tmux', null, null, 'probe') },
    ];
    for (const c of cases) {
      try {
        await c.fn();
        lines.push(`${c.name}: UNEXPECTED PASS`);
      } catch (err) {
        lines.push(`${c.name}: ${err.code}`);
      }
    }

    // Headed-capable profile: fire a real row and spawn.
    const fired = fire(ctx, { profile: 'test-headed', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    const row = await ctx.mgr.spawn(fired.exec_id, 'test-headed', 'headed', null, null, 'probe');
    lines.push(`headed on headed-capable profile: spawned, status=${row.status}`);
    await ctx.mgr.kill(row.exec_id);
    lines.push('result: invalid modes rejected; headed profile spawns successfully');
  } finally {
    teardown(ctx);
  }
});
