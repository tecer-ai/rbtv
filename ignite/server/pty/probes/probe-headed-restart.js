'use strict';

// Criterion 7 (Test Plan, OQ-E RULED D83 — the HOLDER, not restart-mortality): restart SURVIVAL.
// The pty master lives in the in-unit dtach holder, so a headed session survives the daemon losing
// its bridge/pty-host; on "restart" the daemon reconnects to the holder socket and the vt model
// repaints on reattach. Proven by: session bytes established, the pty host is TORN DOWN (bridges
// detached — the daemon-restart analogue), a FRESH pty host reconnects to the SAME holder socket,
// and a capture after reconnect shows the session's live rendered content (repainted).

const fs = require('node:fs');
const path = require('node:path');
const { createPtyHost } = require('../pty-host');
const { setup, fire, teardown, capture, unitState, sleep } = require('./lib');

capture('probe-headed-restart', async (lines) => {
  const ctx = setup();
  let ptyHost2 = null;
  try {
    const fired = fire(ctx, { profile: 'test-headed', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    const row = await ctx.routed.spawn(fired.exec_id, 'test-headed', 'headed', null, null, 'probe');
    ctx.units.push(row.unit_name);
    lines.push(`spawned headed session exec_id=${row.exec_id} unit=${row.unit_name} session_id=${row.session_id}`);

    await sleep(700);
    const token = `survivor-${Math.floor(Math.random() * 1e6)}`;
    ctx.ptyHost.sendKeys(row.exec_id, `${token}\n`);
    await sleep(500);
    lines.push(`established session state; screen before restart:\n${ctx.ptyHost.captureScreen(row.exec_id).screen}`);

    const sock = path.join(ctx.dataRoot, 'ptys', `${row.session_id}.sock`);
    lines.push(`holder socket before restart: ${fs.existsSync(sock)}`);

    // ── Simulate the daemon restart: detach the pty host (bridges closed). The holder + TUI live
    //    in the transient unit, so they must SURVIVE this.
    lines.push('action: ptyHost.shutdown() — the daemon-restart analogue (bridges detached, holders left running)');
    ctx.ptyHost.shutdown();
    await sleep(600);
    lines.push(`unit still active after pty-host shutdown: ${unitState(row.unit_name)}`);
    lines.push(`holder socket survived pty-host shutdown: ${fs.existsSync(sock)} (expected true)`);
    if (!fs.existsSync(sock)) throw new Error('holder socket vanished on pty-host shutdown — session did NOT survive');

    // ── A FRESH pty host (the rebooted daemon's) reconnects to the surviving holder.
    ptyHost2 = createPtyHost({ heartStore: ctx.store, spawnManager: ctx.mgr, dataRoot: ctx.dataRoot, userManager: true, logger: null });
    lines.push('action: fresh ptyHost.reconnect(exec_id) — the rebooted daemon reattaching');
    const rec = ptyHost2.reconnect(row.exec_id);
    lines.push(`reconnect result: ${JSON.stringify(rec)}`);
    await sleep(400);
    // Nudge a repaint by driving one more render and confirm the vt model rebuilt live.
    ptyHost2.sendKeys(row.exec_id, 'afterreconnect\n');
    await sleep(700);
    const screen2 = ptyHost2.captureScreen(row.exec_id).screen;
    lines.push(`screen AFTER reconnect (repainted):\n${screen2}`);
    if (!/afterreconnect/.test(screen2)) throw new Error('reconnected session did not render new input — reattach failed');

    lines.push('RESULT: the headed session SURVIVED the pty-host restart; a fresh pty host reconnected to the in-unit holder socket and the vt model repainted (D7 property 2 holds for restarts).');
  } finally {
    try { if (ptyHost2) ptyHost2.shutdown(); } catch { /* best-effort */ }
    teardown(ctx);
  }
});
