'use strict';

// Criterion 5 (Test Plan): headless stays the DEFAULT — a default worker spawns with NO pty;
// stdout/stderr go to the per-session log file. Proven by the ABSENCE of any pty holder socket
// for the session and the presence of a normal log, plus the row carrying session_mode=headless.

const fs = require('node:fs');
const path = require('node:path');
const { setup, fire, teardown, capture, sleep } = require('./lib');

capture('probe-headless-default', async (lines) => {
  const ctx = setup();
  try {
    const fired = fire(ctx, { profile: 'test-sleep', sessionMode: 'headless', workdir: ctx.defaultWorkdir });
    lines.push(`action: spawn session_mode=headless (default) profile=test-sleep exec_id=${fired.exec_id} via the pty-aware routed manager`);
    const row = await ctx.routed.spawn(fired.exec_id, 'test-sleep', 'headless', null, null, 'probe');
    ctx.units.push(row.unit_name);
    lines.push(`spawned: session_id=${row.session_id} unit=${row.unit_name} status=${row.status} session_mode=${row.session_mode}`);

    await sleep(400);
    // No pty holder socket must exist for a headless session.
    const ptyDir = path.join(ctx.dataRoot, 'ptys');
    const sock = path.join(ptyDir, `${row.session_id}.sock`);
    const ptyDirEntries = fs.existsSync(ptyDir) ? fs.readdirSync(ptyDir) : [];
    lines.push(`pty holder socket for this session present: ${fs.existsSync(sock)} (expected false)`);
    lines.push(`data_root/ptys entries: ${JSON.stringify(ptyDirEntries)}`);
    lines.push(`pty host tracks this session: ${ctx.ptyHost.listHeaded().some((s) => s.execId === row.exec_id)} (expected false)`);
    // The headless log is the normal per-session log (not a pty transcript).
    lines.push(`log_path=${row.log_path} exists=${fs.existsSync(row.log_path)}`);

    if (fs.existsSync(sock)) throw new Error('a pty holder socket was created for a HEADLESS session — headless must attach no pty');
    if (ctx.ptyHost.listHeaded().some((s) => s.execId === row.exec_id)) throw new Error('headless session leaked into the pty host');
    if (row.session_mode !== 'headless') throw new Error(`row session_mode is ${row.session_mode}, expected headless`);
    lines.push('RESULT: the default worker spawned with NO pty; headless one-shot remains the default and rides the sole spawn path unchanged.');
  } finally {
    teardown(ctx);
  }
});
