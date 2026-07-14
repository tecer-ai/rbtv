'use strict';

const { setup, teardown, capture } = require('./lib');

capture('probe-orphan-rescan', async (lines) => {
  const ctx = setup();
  try {
    lines.push('action: run orphan rescan on empty store');
    const results = await ctx.mgr.orphanRescan();
    lines.push(`reattached: ${results.reattached.length}`);
    lines.push(`marked_failed: ${results.markedFailed.length}`);
    lines.push(`row_less_units: ${results.rowLessUnits.length}`);
    lines.push('note: full test needs pre-existing rows (blocked by row seam)');
  } finally {
    teardown(ctx);
  }
});
