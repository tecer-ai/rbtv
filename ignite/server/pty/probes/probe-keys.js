'use strict';

// Criterion 2 (Test Plan): keys reach a live session. POST /keys/:id (ptyHost.sendKeys) writes
// keystroke bytes into the pty; the TUI executes them. Proven by the CAPTURED SCREEN reflecting
// the injected input (observed bytes, not reasoning).

const { setup, fire, teardown, capture, sleep } = require('./lib');

capture('probe-keys', async (lines) => {
  const ctx = setup();
  try {
    const fired = fire(ctx, { profile: 'test-headed', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    const row = await ctx.routed.spawn(fired.exec_id, 'test-headed', 'headed', null, null, 'probe');
    ctx.units.push(row.unit_name);
    lines.push(`spawned headed session exec_id=${row.exec_id} unit=${row.unit_name}`);

    await sleep(700); // holder up, bridge attached, renderer printed READY
    const before = ctx.ptyHost.captureScreen(row.exec_id).screen;
    lines.push(`screen BEFORE keys:\n${before}`);

    const token = `keycheck-${Math.floor(Math.random() * 1e6)}`;
    lines.push(`action: sendKeys("${token}\\n")`);
    ctx.ptyHost.sendKeys(row.exec_id, `${token}\n`);
    await sleep(700);
    const after = ctx.ptyHost.captureScreen(row.exec_id).screen;
    lines.push(`screen AFTER keys:\n${after}`);

    if (!after.includes(token)) throw new Error(`injected token '${token}' did not appear on the rendered screen — keys did not reach the TUI`);
    lines.push(`RESULT: injected '${token}' reached the live TUI on the pty slave (the keystroke rung, CMP-9).`);

    // Dead-id keys → typed error, never a hang (Behavior #11).
    let typed = false;
    try { ctx.ptyHost.sendKeys(999999, 'x'); } catch (e) { typed = true; lines.push(`dead-id sendKeys -> typed ${e.code}: ${e.message}`); }
    if (!typed) throw new Error('sendKeys on a dead id did not raise a typed error');
  } finally {
    teardown(ctx);
  }
});
