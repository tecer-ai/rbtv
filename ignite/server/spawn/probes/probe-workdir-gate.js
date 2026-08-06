'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, capture, fire } = require('./lib');

capture('probe-workdir-gate', async (lines) => {
  const ctx = setup();
  try {
    // A REAL symlink-escape: a link INSIDE workdir_root that resolves OUTSIDE it.
    // canonicalizeWorkdir uses realpathSync, so the escape must be caught post-resolution.
    const escapeLink = path.join(ctx.workRoot, 'escape-link');
    fs.symlinkSync(ctx.escapedir, escapeLink);
    lines.push(`symlink ${escapeLink} -> ${fs.realpathSync(escapeLink)} (outside workdir_root ${ctx.workRoot})`);

    const cases = [
      { name: 'workdir outside workdir_root', fn: () => ctx.mgr.spawn(0, 'test-sleep', 'headless', null, ctx.escapedir, 'probe') },
      { name: 'symlink escape (link inside root resolves outside)', fn: () => ctx.mgr.spawn(0, 'test-sleep', 'headless', null, escapeLink, 'probe') },
      { name: 'absolute path outside root', fn: () => ctx.mgr.spawn(0, 'test-sleep', 'headless', null, '/tmp', 'probe') },
    ];
    for (const c of cases) {
      try {
        await c.fn();
        lines.push(`${c.name}: UNEXPECTED PASS`);
      } catch (err) {
        lines.push(`${c.name}: ${err.code}`);
      }
    }

    // Omitted workdir: REFUSED (r-seats-only-architecture (3)). The default branch used to
    // fall back to default_workdir_root / materialize the flat .rbtv/sessions/ dir; a dispatch
    // with no home is now a refusal, not a flat dir.
    const fired = fire(ctx, { profile: 'test-sleep', sessionMode: 'headless', workdir: null });
    try {
      await ctx.mgr.spawn(fired.exec_id, 'test-sleep', 'headless', null, null, 'probe');
      throw new Error('workdir omitted: UNEXPECTED PASS — the retired flat/default branch admitted a homeless dispatch');
    } catch (err) {
      if (err.code !== 'E_SEATLESS_GOAL_DISPATCH' || !/REFUSING SEATLESS DISPATCH/.test(err.message)) throw err;
      lines.push(`workdir omitted: ${err.code} (REFUSING SEATLESS DISPATCH)`);
    }
    // A flat non-seat workdir inside the root: refused by the same door.
    try {
      await ctx.mgr.spawn(0, 'test-sleep', 'headless', null, ctx.workRoot, 'probe');
      throw new Error('flat workdir: UNEXPECTED PASS — a non-seat workdir was admitted');
    } catch (err) {
      if (err.code !== 'E_SEATLESS_GOAL_DISPATCH') throw err;
      lines.push(`flat non-seat workdir inside root: ${err.code}`);
    }
    lines.push('result: escapes rejected; omitted and non-seat workdirs are REFUSED (no flat fallback remains)');
  } finally {
    teardown(ctx);
  }
});
