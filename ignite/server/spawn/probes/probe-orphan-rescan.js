'use strict';

const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const { setup, teardown, capture, fire } = require('./lib');

function isActive(unit) {
  try {
    return execFileSync('systemctl', ['--user', 'is-active', unit], { encoding: 'utf8' }).trim();
  } catch (e) {
    return (e.stdout || 'inactive').toString().trim() || 'inactive';
  }
}

async function waitInactive(unit, timeoutMs = 4000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (isActive(unit) !== 'active') return true;
    await new Promise((r) => setTimeout(r, 100));
  }
  return false;
}

// D34 unblocked the real 3-case boot reconciliation: rows are created at fire by
// recordExecutionStart, so we can seed launching/running rows and prove each direction
// against ACTUAL user-manager unit state.
capture('probe-orphan-rescan', async (lines) => {
  const ctx = setup();
  const cleanup = [];
  try {
    // --- Case (a): a live worker whose row is 'running' -> REATTACHED (status intact) ---
    const firedA = fire(ctx, { profile: 'test-sleep', sessionMode: 'headless', workdir: ctx.defaultWorkdir });
    const rowA = await ctx.mgr.spawn(firedA.exec_id, 'test-sleep', 'headless', null, null, 'probe');
    cleanup.push(() => ctx.mgr.kill(rowA.exec_id).catch(() => {}));
    lines.push(`case-a live: exec_id=${rowA.exec_id} unit=${rowA.unit_name} status=${rowA.status} is-active=${isActive(rowA.unit_name)}`);

    // --- Case (b): a 'running' row whose unit is dead -> marked FAILED, surfaced as data ---
    const firedB = fire(ctx, { profile: 'test-sleep', sessionMode: 'headless', workdir: ctx.defaultWorkdir });
    const rowB = await ctx.mgr.spawn(firedB.exec_id, 'test-sleep', 'headless', null, null, 'probe');
    // Kill the unit OUT OF BAND (not via mgr.kill) so the row stays 'running' — a true orphan.
    try { execFileSync('systemctl', ['--user', 'kill', '--signal=SIGKILL', rowB.unit_name], { stdio: 'ignore' }); } catch {}
    const bDead = await waitInactive(rowB.unit_name);
    const rowBpre = ctx.store.getExecution(rowB.exec_id);
    lines.push(`case-b orphan: exec_id=${rowB.exec_id} unit=${rowB.unit_name} row-status-before-rescan=${rowBpre.status} unit-inactive=${bDead} is-active=${isActive(rowB.unit_name)}`);

    // --- Case (c): a live rbtv-worker-* unit with NO matching row -> flagged LOUD, never killed ---
    const rowlessId = crypto.randomUUID();
    const rowlessUnit = `rbtv-worker-${rowlessId}`;
    execFileSync('systemd-run', ['--user', '--unit', rowlessUnit, '--collect', 'sleep', '3600'], { stdio: 'ignore' });
    cleanup.push(() => { try { execFileSync('systemctl', ['--user', 'stop', rowlessUnit], { stdio: 'ignore' }); } catch {} });
    lines.push(`case-c row-less unit: ${rowlessUnit} is-active=${isActive(rowlessUnit)}`);

    // --- Boot orphan rescan (both directions) ---
    lines.push('action: run orphan rescan (both directions) against real user-manager units');
    const results = await ctx.mgr.orphanRescan();

    const reattachedIds = results.reattached.map((r) => r.execId);
    const failedIds = results.markedFailed.map((r) => r.execId);
    // list-units reports names WITH `.service`; normalize for comparison against bare names.
    const rowLessNames = results.rowLessUnits.map((u) => u.unitName.replace(/\.service$/, ''));

    // Case (a) proof: reattached, status STILL running, unit STILL active, NOT falsely row-less/failed.
    const rowAafter = ctx.store.getExecution(rowA.exec_id);
    lines.push(`RESULT case-a: reattached=${reattachedIds.includes(rowA.exec_id)} status-after=${rowAafter.status} is-active-after=${isActive(rowA.unit_name)} falsely-rowless=${rowLessNames.some((n) => n.includes(rowA.session_id))} falsely-failed=${failedIds.includes(rowA.exec_id)}`);

    // Case (b) proof: marked failed, row status now 'failed'.
    const rowBafter = ctx.store.getExecution(rowB.exec_id);
    const bDetail = results.markedFailed.find((r) => r.execId === rowB.exec_id);
    lines.push(`RESULT case-b: marked_failed=${failedIds.includes(rowB.exec_id)} status-after=${rowBafter.status} reason="${bDetail ? bDetail.reason : 'n/a'}"`);

    // Case (c) proof: flagged row-less, unit STILL active (never auto-killed).
    lines.push(`RESULT case-c: flagged-rowless=${rowLessNames.includes(rowlessUnit)} unit-still-active=${isActive(rowlessUnit)} (never auto-killed)`);

    lines.push(`counts: reattached=${results.reattached.length} marked_failed=${results.markedFailed.length} row_less_units=${results.rowLessUnits.length} errors=${results.errors.length}`);

    // Hard assertions — fail loud if any observable is wrong.
    const ok =
      reattachedIds.includes(rowA.exec_id) &&
      rowAafter.status === 'running' &&
      isActive(rowA.unit_name) === 'active' &&
      !failedIds.includes(rowA.exec_id) &&
      !rowLessNames.some((n) => n.includes(rowA.session_id)) &&
      failedIds.includes(rowB.exec_id) &&
      rowBafter.status === 'failed' &&
      rowLessNames.includes(rowlessUnit) &&
      isActive(rowlessUnit) === 'active';
    if (!ok) throw new Error('orphan-rescan 3-case reconciliation did not hold — see RESULT lines');
    lines.push('result: 3-case boot reconciliation proven (live reattach / dead->failed / row-less flagged, never killed)');
  } finally {
    for (const c of cleanup) { try { await c(); } catch {} }
    teardown(ctx);
  }
});
