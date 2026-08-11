'use strict';

require('../../../deploy/probe-self-isolate').selfIsolateTmux(); // solo-run tmux isolation (task 7.630) — no-op under the runner
const { setup, teardown, capture, fire } = require('./lib');

capture('probe-mode-gate', async (lines) => {
  const ctx = setup();
  try {
    const cases = [
      { name: 'headed on non-headed profile', code: 'E_HEADED_NOT_CAPABLE', fn: () => ctx.mgr.spawn(0, 'test-sleep', 'headed', null, null, 'probe') },
      { name: 'unknown mode', code: 'E_UNKNOWN_MODE', fn: () => ctx.mgr.spawn(0, 'test-sleep', 'tmux', null, null, 'probe') },
    ];
    // ASSERT the code, never merely record it: a loop that pushed `err.code` and moved on reported
    // PASS while both refusals had silently become ERR_INVALID_ARG_TYPE (the `path.basename(null)`
    // regression of 29220dc9) — a probe that cannot fail is not a probe.
    for (const c of cases) {
      try {
        await c.fn();
        throw new Error(`${c.name}: UNEXPECTED PASS — expected ${c.code}`);
      } catch (err) {
        if (err.code !== c.code) throw err;
        lines.push(`${c.name}: ${err.code}`);
      }
    }

    // Headed-capable profile: fire a real row and spawn (homed in the fixture seat folder —
    // r-seats-only-architecture refuses homeless dispatches on this door too).
    const fired = fire(ctx, { profile: 'test-headed', sessionMode: 'headed', workdir: ctx.seatDir });
    const row = await ctx.mgr.spawn(fired.exec_id, 'test-headed', 'headed', null, ctx.seatDir, 'probe');
    lines.push(`headed on headed-capable profile: spawned, status=${row.status}`);
    await ctx.mgr.kill(row.exec_id);
    lines.push('result: invalid modes rejected; headed profile spawns successfully');
  } finally {
    teardown(ctx);
  }
});
