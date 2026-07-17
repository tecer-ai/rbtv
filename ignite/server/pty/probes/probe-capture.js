'use strict';

// Criterion 3 (Test Plan): screen capture returns the CURRENT rendered content from the server-side
// vt model (Amendment #4, in-house). The pty yields raw ANSI bytes; the vt model turns them into a
// cell grid; capture returns the grid. Proven by the rendered text, and by the watch-tee log
// holding the raw stream (Design 1 watch surface).

const fs = require('node:fs');
const { setup, fire, teardown, capture, sleep } = require('./lib');

capture('probe-capture', async (lines) => {
  const ctx = setup();
  try {
    const fired = fire(ctx, { profile: 'test-headed', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    const row = await ctx.routed.spawn(fired.exec_id, 'test-headed', 'headed', null, null, 'probe');
    ctx.units.push(row.unit_name);
    lines.push(`spawned headed session exec_id=${row.exec_id}`);

    await sleep(700);
    const cap1 = ctx.ptyHost.captureScreen(row.exec_id);
    lines.push(`capture #1 (${cap1.rows}x${cap1.cols}):\n${cap1.screen}`);
    if (!/READY/.test(cap1.screen)) throw new Error('initial capture did not show the renderer READY banner');

    // Drive a render and re-capture — the vt model reflects the new rendered state.
    ctx.ptyHost.sendKeys(row.exec_id, 'renderproof\n');
    await sleep(700);
    const cap2 = ctx.ptyHost.captureScreen(row.exec_id);
    lines.push(`capture #2 after a render:\n${cap2.screen}`);
    if (!/LINE1:renderproof/.test(cap2.screen)) throw new Error('capture did not reflect the newly rendered line — vt model not tracking state');

    // Watch-tee: the per-session log holds the raw pty stream (Design 1).
    const logData = fs.existsSync(row.log_path) ? fs.readFileSync(row.log_path, 'utf8') : '';
    lines.push(`watch-tee log_path=${row.log_path} bytes=${logData.length} contains 'renderproof': ${logData.includes('renderproof')}`);
    if (!logData.includes('renderproof')) throw new Error('watch-tee log did not capture the pty stream');

    // Dead-id capture → typed error.
    let typed = false;
    try { ctx.ptyHost.captureScreen(888888); } catch (e) { typed = true; lines.push(`dead-id capture -> typed ${e.code}`); }
    if (!typed) throw new Error('captureScreen on a dead id did not raise a typed error');

    lines.push('RESULT: screen capture returns live rendered content from the in-house vt model; watch-tee log holds the raw stream.');
  } finally {
    teardown(ctx);
  }
});
