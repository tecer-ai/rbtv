'use strict';

const { setup, teardown, capture } = require('./lib');
const { validateSpawnRequest } = require('../spawn');

capture('probe-flag-injection', async (lines) => {
  const ctx = setup();
  try {
    const cases = [
      { name: 'flag in prompt', fn: () => ctx.mgr.spawn(0, 'test-sleep', 'headless', '-h', null, 'probe') },
      { name: 'flag in workdir', fn: () => ctx.mgr.spawn(0, 'test-sleep', 'headless', null, '-/tmp', 'probe') },
      { name: 'unknown request key', fn: () => validateSpawnRequest({ profile: 'test-sleep', session_mode: 'headless', prompt: null, workdir: null, extra: 1 }) },
      { name: 'unknown profile', fn: () => ctx.mgr.spawn(0, 'not-a-profile', 'headless', null, null, 'probe') },
    ];
    for (const c of cases) {
      try {
        await c.fn();
        lines.push(`${c.name}: UNEXPECTED PASS`);
      } catch (err) {
        lines.push(`${c.name}: ${err.code}`);
      }
    }
    lines.push('result: all injection attempts refused typed');
  } finally {
    teardown(ctx);
  }
});
