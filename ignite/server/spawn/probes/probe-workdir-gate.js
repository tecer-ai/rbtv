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

    // Omitted workdir: fire a real row and spawn.
    const fired = fire(ctx, { profile: 'test-sleep', sessionMode: 'headless', workdir: ctx.defaultWorkdir });
    const row = await ctx.mgr.spawn(fired.exec_id, 'test-sleep', 'headless', null, null, 'probe');
    lines.push(`workdir omitted: status=${row.status}, workdir=${row.workdir}`);
    lines.push(`workdir equals default_workdir_root: ${row.workdir === ctx.defaultWorkdir}`);
    await ctx.mgr.kill(row.exec_id);
    lines.push('result: escapes rejected; omitted workdir defaults to configured root');
  } finally {
    teardown(ctx);
  }
});
