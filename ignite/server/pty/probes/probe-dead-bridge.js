'use strict';

// Task 7.17 criterion 2: a probe proves a dead-bridge-over-live-unit now re-attaches and serves
// keys/capture rather than throwing E_SESSION_NOT_LIVE (the defect: ensureAttached/its callers
// handed back a mapped-but-dead bridge entry with no health check, so a session genuinely ALIVE
// in its unit was reported "dead" and the map never self-emptied to trigger the self-healing
// re-attach path — the ONLY headed-recovery failure that did not self-heal without a daemon
// restart or manual intervention).
//
// Simulates the dead-bridge-over-live-unit state by killing ONLY the daemon-side bridge process
// (the python pty-bridge.py client attaching to the in-unit dtach holder) while leaving the
// transient systemd unit (and the holder/pty inside it) running — proving the failure is about a
// STALE MAP ENTRY, not a dead unit. Also proves the two paths that must stay UNCHANGED: map-absent
// (no session row at all) and genuinely-dead-unit (unit no longer active) both still raise the
// typed E_SESSION_NOT_LIVE, never a hang (Behavior #11).

const fs = require('node:fs');
const path = require('node:path');
const { setup, fire, teardown, capture, unitState, sleep } = require('./lib');

// Scan /proc for the PID of the python pty-bridge.py client attached to `sock` (mirrors lib.js's
// cmdlineOf/proc-based observation style — never trusts a Node child_process handle we do not
// have from outside pty-host.js).
function findBridgePid(sock) {
  for (const pid of fs.readdirSync('/proc')) {
    if (!/^\d+$/.test(pid)) continue;
    let cmdline = '';
    try { cmdline = fs.readFileSync(`/proc/${pid}/cmdline`).toString().replace(/\0/g, ' '); } catch { continue; }
    if (cmdline.includes('pty-bridge.py') && cmdline.includes(sock)) return Number(pid);
  }
  return null;
}

capture('probe-dead-bridge', async (lines) => {
  const ctx = setup();
  try {
    // ── Case A: dead bridge, LIVE unit — the defect under fix. ──────────────────────────────
    const fired = fire(ctx, { profile: 'test-headed', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    const row = await ctx.routed.spawn(fired.exec_id, 'test-headed', 'headed', null, null, 'probe');
    ctx.units.push(row.unit_name);
    lines.push(`spawned headed session exec_id=${row.exec_id} unit=${row.unit_name} session_id=${row.session_id}`);

    await sleep(700);
    const token1 = `alive-${Math.floor(Math.random() * 1e6)}`;
    ctx.ptyHost.sendKeys(row.exec_id, `${token1}\n`);
    await sleep(500);
    const before = ctx.ptyHost.captureScreen(row.exec_id).screen;
    lines.push(`screen BEFORE killing the bridge:\n${before}`);
    if (!before.includes(token1)) throw new Error('session did not establish live state before the dead-bridge simulation');

    const sock = path.join(ctx.dataRoot, 'ptys', `${row.session_id}.sock`);
    const bridgePid = findBridgePid(sock);
    lines.push(`bridge pid for sock=${sock}: ${bridgePid}`);
    if (!bridgePid) throw new Error('could not locate the daemon-side pty-bridge.py process to kill — cannot simulate a dead bridge');

    lines.push(`action: kill -9 ${bridgePid} — kills ONLY the daemon-side bridge client, never the transient unit/holder`);
    process.kill(bridgePid, 'SIGKILL');

    // Wait for the pty host's own bookkeeping to observe the exit (async 'exit' event).
    let bridgeAlive = true;
    for (let i = 0; i < 20 && bridgeAlive; i++) {
      await sleep(150);
      const info = ctx.ptyHost.listHeaded().find((s) => s.execId === row.exec_id);
      bridgeAlive = info ? info.bridgeAlive : false;
    }
    lines.push(`pty host bridgeAlive after kill: ${bridgeAlive} (expected false)`);
    if (bridgeAlive) throw new Error('pty host still reports the killed bridge as alive — simulation did not take effect');

    const unitStateAfterBridgeKill = unitState(row.unit_name);
    lines.push(`unit state AFTER bridge kill (must still be active — the unit/holder must survive): ${unitStateAfterBridgeKill}`);
    if (!/ActiveState=active/.test(unitStateAfterBridgeKill)) {
      throw new Error(`unit went inactive when only the bridge was killed — simulation killed the wrong process: ${unitStateAfterBridgeKill}`);
    }

    lines.push('state reached: mapped entry present + bridge DEAD + unit LIVE (the exact dead-bridge-over-live-unit defect condition).');

    // ── The fix under test: sendKeys/captureScreen must now re-attach and serve, not throw. ──
    const token2 = `healed-${Math.floor(Math.random() * 1e6)}`;
    lines.push(`action: sendKeys("${token2}\\n") against the dead-bridge-over-live-unit entry`);
    ctx.ptyHost.sendKeys(row.exec_id, `${token2}\n`);
    await sleep(700);
    const after = ctx.ptyHost.captureScreen(row.exec_id).screen;
    lines.push(`screen AFTER the dead-bridge sendKeys (post-heal):\n${after}`);
    if (!after.includes(token2)) throw new Error(`dead-bridge-over-live-unit did not self-heal: '${token2}' never reached the TUI`);
    lines.push('RESULT A: a dead-bridge-over-live-unit re-attached and served keys/capture rather than throwing E_SESSION_NOT_LIVE.');

    // ── Case B: map-absent path stays UNCHANGED — typed E_SESSION_NOT_LIVE, never a hang. ────
    let typedAbsent = null;
    try { ctx.ptyHost.sendKeys(777777, 'x'); } catch (e) { typedAbsent = e.code; }
    lines.push(`map-absent sendKeys(777777) -> typed ${typedAbsent} (expected E_SESSION_NOT_LIVE)`);
    if (typedAbsent !== 'E_SESSION_NOT_LIVE') throw new Error(`map-absent path changed: expected E_SESSION_NOT_LIVE, got ${typedAbsent}`);

    // ── Case C: genuinely-dead-unit path stays UNCHANGED — typed E_SESSION_NOT_LIVE. ─────────
    const fired2 = fire(ctx, { profile: 'test-headed', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    const row2 = await ctx.routed.spawn(fired2.exec_id, 'test-headed', 'headed', null, null, 'probe');
    ctx.units.push(row2.unit_name);
    await sleep(700);
    ctx.ptyHost.sendKeys(row2.exec_id, 'x\n');
    await sleep(300);
    lines.push(`action: systemctl --user kill ${row2.unit_name} — kill the WHOLE unit (genuinely dead)`);
    const { execFileSync } = require('node:child_process');
    try { execFileSync('systemctl', ['--user', 'kill', row2.unit_name], { stdio: 'ignore', timeout: 8000 }); } catch { /* best-effort */ }
    await sleep(800);
    const unitStateAfterUnitKill = unitState(row2.unit_name);
    lines.push(`unit state after killing the whole unit: ${unitStateAfterUnitKill}`);

    let typedDeadUnit = null;
    try { ctx.ptyHost.sendKeys(row2.exec_id, 'y\n'); } catch (e) { typedDeadUnit = e.code; }
    lines.push(`genuinely-dead-unit sendKeys -> typed ${typedDeadUnit} (expected E_SESSION_NOT_LIVE, never a hang)`);
    if (typedDeadUnit !== 'E_SESSION_NOT_LIVE') throw new Error(`genuinely-dead-unit path changed: expected E_SESSION_NOT_LIVE, got ${typedDeadUnit}`);

    lines.push('RESULT B+C: map-absent and genuinely-dead-unit paths are UNCHANGED — still typed E_SESSION_NOT_LIVE, never a hang.');
  } finally {
    teardown(ctx);
  }
});
