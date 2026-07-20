'use strict';

const { setup, teardown, capture, fire } = require('./lib');
const { validateSpawnRequest } = require('../spawn');

capture('probe-flag-injection', async (lines) => {
  const ctx = setup();
  try {
    // NO prompt flag-injection guard remains (batch-08 item 4 half A): with the carriage
    // vocabulary collapsed to stdin (headless) / file|keystroke (headed), no carriage puts
    // caller text on a command line, so the prompt is 0600-file DATA everywhere and the former
    // argv-last guard cases are config-load failures now (probe-carriage-vocab.js proves that).
    // The WORKDIR guard stays UNCONDITIONAL — a workdir always rides argv/unit properties.
    const cases = [
      { name: 'flag in workdir', fn: () => ctx.mgr.spawn(0, 'test-sleep', 'headless', null, '-/tmp', 'probe') },
      { name: 'unknown request key', fn: () => validateSpawnRequest({ profile: 'test-sleep', session_mode: 'headless', prompt: null, workdir: null, extra: 1 }) },
      { name: 'unknown profile', fn: () => ctx.mgr.spawn(0, 'not-a-profile', 'headless', null, null, 'probe') },
    ];
    for (const c of cases) {
      try {
        await c.fn();
        throw new Error(`${c.name}: UNEXPECTED PASS — refusal did not fire`);
      } catch (err) {
        if (!err.code) throw err; // the UNEXPECTED PASS Error has no .code — rethrow
        lines.push(`${c.name}: ${err.code}`);
      }
    }
    lines.push('result: all injection attempts refused typed');

    // POSITIVE leg — stdin carriage accepts a composed-transcript prompt (newlines,
    // parentheses, dollar signs are DATA there; the pre-p7-multiturn unconditional
    // guard refused exactly this and broke every composed multi-turn prompt).
    const fired = fire(ctx, { profile: 'test-quick', sessionMode: 'headless', workdir: ctx.defaultWorkdir });
    const transcript = '[owner] what is 17*23? (exactly)\n\n[assistant] 391\n\n[owner] now add 9 & say "$done"';
    const row = await ctx.mgr.spawn(fired.exec_id, 'test-quick', 'headless', transcript, null, 'probe');
    lines.push(`stdin-carriage transcript prompt ACCEPTED: exec ${row.exec_id} spawned (session ${row.session_id})`);
  } finally {
    teardown(ctx);
  }
});
