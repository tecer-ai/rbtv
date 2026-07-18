'use strict';

const { setup, teardown, capture, fire } = require('./lib');
const { validateSpawnRequest } = require('../spawn');

capture('probe-flag-injection', async (lines) => {
  const ctx = setup();
  try {
    // The prompt guard is CARRIAGE-CONDITIONAL (p7-multiturn): argv-last is the
    // one carriage whose prompt rides argv, so ONLY it refuses flag-shaped /
    // metacharacter prompts. File/stdin prompts are data in a 0600 file.
    const cases = [
      { name: 'flag in prompt (argv-last carriage)', fn: () => ctx.mgr.spawn(0, 'test-argvlast', 'headless', '-h', null, 'probe') },
      { name: 'metacharacters in prompt (argv-last carriage)', fn: () => ctx.mgr.spawn(0, 'test-argvlast', 'headless', 'x; rm -rf $(HOME)', null, 'probe') },
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
