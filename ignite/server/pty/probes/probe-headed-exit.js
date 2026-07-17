'use strict';

// Behavior #8 + Amendment #5 (exit-code sourcing): a headed session's exit_code is NEVER the
// unit's ExecMainStatus (M3 masks it) — it is sourced from the in-unit no-shell status shim
// (Design 2 caveat 1, option i). Proven by driving the TUI to exit 42, then showing the shim's
// status file holds the TRUE code 42 while the unit's ExecMainStatus is a masked 0.

const { setup, fire, teardown, capture, unitState, sleep } = require('./lib');

capture('probe-headed-exit', async (lines) => {
  const ctx = setup();
  try {
    const fired = fire(ctx, { profile: 'test-headed-exit', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    const row = await ctx.routed.spawn(fired.exec_id, 'test-headed-exit', 'headed', null, null, 'probe');
    ctx.units.push(row.unit_name);
    lines.push(`spawned headed session exec_id=${row.exec_id} unit=${row.unit_name}`);

    await sleep(700);
    lines.push('action: sendKeys("bye\\n") — the TUI exits with code 42');
    ctx.ptyHost.sendKeys(row.exec_id, 'bye\n');
    await sleep(1200); // let the TUI exit + the shim write the status file + dtach tear down

    lines.push(`unit state after TUI exit: ${unitState(row.unit_name)}`);
    const sourced = ctx.ptyHost.sourceExitCode(row.exec_id);
    lines.push(`ptyHost.sourceExitCode -> ${JSON.stringify(sourced)}`);

    // Read the raw shim status file for the record.
    const fs = require('node:fs'); const path = require('node:path');
    const sf = path.join(row.workdir, '.ignite-headed-exit.json');
    lines.push(`shim status file (${sf}) = ${fs.existsSync(sf) ? fs.readFileSync(sf, 'utf8') : '(absent)'}`);

    if (sourced.exit_code !== 42) throw new Error(`exit_code sourced as ${JSON.stringify(sourced.exit_code)}, expected the TRUE 42 (a masked 0 is the forbidden outcome)`);
    if (sourced.source !== 'status-shim') throw new Error(`exit_code source is ${sourced.source}, expected status-shim`);
    lines.push('RESULT: the headed exit_code is the TRUE child status (42) from the in-unit shim, NOT the masked ExecMainStatus=0.');
  } finally {
    teardown(ctx);
  }
});
