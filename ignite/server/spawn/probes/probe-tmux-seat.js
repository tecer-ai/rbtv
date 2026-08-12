'use strict';

// probe-tmux-seat — task 7.30, the tmux SEAT spawn target (spawn/tmux.js).
//
// SCOPE, STATED SO NOBODY OVER-READS A GREEN: this probe exercises COMPOSITION ONLY. It creates no
// tmux pane, spawns no seat, touches no daemon. Run under run-1's `A3F-shadow` constraint set while
// guard B1 (the bwrap file-absence proof + its adversarial verdict) is unresolved — nothing that
// needs a live daemon-spawned seat is stubbed green here; those legs are printed by name as
// NOT-RUN at the end, and they belong to `A4-verify`.
//
// What it does check is the part that is checkable without a room, and it is the part where the
// night's bugs have actually lived: that the composed argv is a VECTOR and not a shell string,
// that the layers nest in the load-bearing order, that a bwrap-less box fails closed before any
// pane argv exists, and that an untranslatable cap refuses rather than silently under-confining.

require('../../../deploy/probe-self-isolate').selfIsolateTmux(); // solo-run tmux isolation (task 7.630) — no-op under the runner
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs');
const { capture, setup, teardown, fire } = require('./lib');
const { composeSeatSpawn, buildScopeArgv, scopeUnitName } = require('../tmux');
const { SpawnError } = require('../errors');
const { execFileSync } = require('node:child_process');

function assert(cond, msg) {
  if (!cond) throw new Error(`assertion failed: ${msg}`);
}

function expectThrow(code, fn, label) {
  try {
    fn();
  } catch (err) {
    assert(err instanceof SpawnError, `${label}: expected SpawnError, got ${err && err.name}`);
    assert(err.code === code, `${label}: expected ${code}, got ${err.code}`);
    return err;
  }
  throw new Error(`${label}: expected ${code}, nothing was thrown`);
}

capture('probe-tmux-seat', async (lines) => {
  const workdir = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-tmux-seat-'));
  const base = {
    room: 'probe-room',
    windowName: 'probe-seat',
    sessionId: '0123abcd-0000-0000-0000-000000000000',
    workdir,
    harnessArgv: ['/usr/bin/env', 'true'],
    caps: { memory_max: '512M', cpu_quota: '100%', tasks_max: 64 },
  };

  // ── leg 1: the three layers nest in the load-bearing order ────────────────────────────────
  const { tmuxArgv, scopeArgv, wrappedArgv, unitName } = composeSeatSpawn(base);
  assert(tmuxArgv[0] === 'tmux' && tmuxArgv[1] === 'new-window', 'leg1: tmux new-window is the outer call');
  const sep = tmuxArgv.indexOf('--');
  assert(sep !== -1, 'leg1: tmux argv carries a `--` separator');
  assert(tmuxArgv[sep + 1] === 'systemd-run', 'leg1: systemd-run sits immediately after tmux `--`');
  assert(scopeArgv.includes('--scope'), 'leg1: the carrier is a SCOPE, not a transient service');
  const scopeSep = scopeArgv.indexOf('--');
  assert(scopeArgv[scopeSep + 1].endsWith('/bwrap'), 'leg1: bwrap sits immediately after the scope `--`');
  assert(wrappedArgv[wrappedArgv.length - 2] === '/usr/bin/env', 'leg1: the harness argv is innermost');
  assert(unitName === scopeUnitName(base.sessionId), 'leg1: the scope unit name is derived from the session id');
  lines.push(`leg1 order: tmux -> systemd-run --scope -> bwrap -> harness  (unit ${unitName})`);

  // ── leg 2: caps reach the scope as properties ─────────────────────────────────────────────
  for (const want of ['MemoryMax=512M', 'CPUQuota=100%', 'TasksMax=64']) {
    assert(scopeArgv.includes(want), `leg2: scope carries ${want}`);
  }
  lines.push('leg2 caps: MemoryMax / CPUQuota / TasksMax emitted as scope properties');

  // ── leg 3: an untranslatable cap REFUSES (D46) ────────────────────────────────────────────
  // The containment promise is that a declared cap the carrier cannot apply fails the spawn
  // loudly. Silently dropping it would run a seat less confined than its profile promises.
  expectThrow('E_CARRIER_FAILED', () => composeSeatSpawn({ ...base, caps: { io_weight: '10' } }), 'leg3');
  lines.push('leg3 unsupported cap: refuses with E_CARRIER_FAILED rather than under-confining');

  // ── leg 4: the pane command is a VECTOR — no shell parses it ──────────────────────────────
  // This is run issue G-11's class, structurally excluded. Every metacharacter that would be
  // mangled (or executed) by a shell must survive as ONE argv element, byte-identical.
  const nasty = 'a`b`$(c) "d" \'e\' ;f | g && h\nnewline';
  const hostile = composeSeatSpawn({ ...base, harnessArgv: ['/usr/bin/env', 'printf', '%s', nasty] });
  assert(hostile.tmuxArgv.filter((a) => a === nasty).length === 1, 'leg4: the hostile argument survives as exactly one argv element');
  // "No shell" means no shell INVOCATION — an adjacent (<shell>, '-c') pair. Testing for a bare
  // '-c' token would be wrong: tmux's own `-c <workdir>` flag is a legitimate '-c' in this argv,
  // and an assertion that fires on it teaches the next reader to weaken the check instead of the
  // code. (Caught by this probe on its first run.)
  const SHELLS = new Set(['sh', 'bash', 'zsh', 'dash', '/bin/sh', '/bin/bash', '/usr/bin/bash', '/usr/bin/sh']);
  const shellInvocation = hostile.tmuxArgv.findIndex((a, i) => SHELLS.has(a) && hostile.tmuxArgv[i + 1] === '-c');
  assert(shellInvocation === -1, `leg4: no shell invocation in the composed argv (found at index ${shellInvocation})`);
  lines.push('leg4 no-shell: metacharacter-laden argument survives as one argv element; no sh -c anywhere');

  // ── leg 5: tmux target names cannot re-target another pane ────────────────────────────────
  expectThrow('E_TMUX_NAME_INVALID', () => composeSeatSpawn({ ...base, room: 'other:window' }), 'leg5 room');
  expectThrow('E_TMUX_NAME_INVALID', () => composeSeatSpawn({ ...base, windowName: 'seat.1' }), 'leg5 window');
  lines.push("leg5 targets: a room/window name carrying ':' or '.' refuses with E_TMUX_NAME_INVALID");

  // ── leg 6: FAIL CLOSED — no bwrap, no pane ────────────────────────────────────────────────
  // The order in composeSeatSpawn is the guarantee: buildBwrapArgv throws BEFORE any tmux argv
  // exists, so on a bwrap-less box the caller has nothing to execute. Simulated by emptying PATH,
  // which is how bwrap.js's own resolver decides the binary is absent.
  const savedPath = process.env.PATH;
  try {
    process.env.PATH = '/nonexistent-probe-path';
    const err = expectThrow('E_FS_SANDBOX_UNAVAILABLE', () => composeSeatSpawn(base), 'leg6');
    assert(/bwrap/.test(err.message), 'leg6: the refusal names bwrap');
  } finally {
    process.env.PATH = savedPath;
  }
  lines.push('leg6 fail-closed: bwrap absent -> E_FS_SANDBOX_UNAVAILABLE thrown before any tmux argv exists; no pane composed');

  // ── leg 7: an unresolvable harness binary also fails closed ───────────────────────────────
  expectThrow('E_FS_SANDBOX_UNAVAILABLE', () => composeSeatSpawn({ ...base, harnessArgv: ['definitely-not-a-binary-7f3a'] }), 'leg7');
  lines.push('leg7 fail-closed: unresolvable harness binary -> E_FS_SANDBOX_UNAVAILABLE, no pane composed');

  // ── leg 8: buildScopeArgv rejects an empty argv ───────────────────────────────────────────
  expectThrow('E_BAD_REQUEST', () => buildScopeArgv({ unitName: 'x', caps: {}, argv: [] }), 'leg8');
  lines.push('leg8 guard: buildScopeArgv refuses an empty argv');

  fs.rmSync(workdir, { recursive: true, force: true });

  // ── legs 9-12: the DAEMON-SIDE half, through spawnSeat({ dryRun: true }) ──────────────────
  // dryRun composes and returns without creating a pane or writing a store row, so the door's own
  // resolution logic is checkable off a live room. A pane is never created anywhere in this probe.
  const ctx = setup();
  let reapRoom = () => {};
  try {
    // TASK 7.11 UPDATE. This fixture used to be a flat `workRoot/seat-probe` directory, and the
    // §4a launch-time gate now REFUSES it — correctly: a seat spawn requires a canonical seat
    // folder that is materialized (seat.md naming it) and rostered (a taskforce row), inside the
    // goal's LIVE run. The probe's fixture is brought up to the real shape rather than the gate
    // being loosened to accept the old one; probe-seat-launch-gate.js is where the refusals of
    // every WRONG shape are proven.
    // 7.607 E2a — GOAL-DIRECT, and the goal's liveness is a REAL room on an ISOLATED socket
    // (never the box's default server, which carries the owner's attached session).
    const goalDir = path.join(ctx.workRoot, '.rbtv', 'goals', 'probegoal');
    const runDir = goalDir;
    const seatDir = path.join(runDir, 'seats', 'probe-seat');
    fs.mkdirSync(seatDir, { recursive: true });
    fs.writeFileSync(path.join(ctx.workRoot, '.rbtv', 'goals', 'goals.csv'), 'name,created,due,type,status\nprobegoal,2026-07-27,,one-shot,active\n');
    fs.writeFileSync(path.join(runDir, 'taskforce.csv'), 'taskforce-id,seat\ntf-1,probe-seat\n');
    fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,session-id,pid,pid-starttime,started,ended\n');
    fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: probe-seat\nharness: bash\nmodel: test-headed\n---\nbriefing\n');

    const roomTmpdir = path.join(os.tmpdir(), `e2a-ts-${process.pid}`);
    fs.mkdirSync(roomTmpdir, { recursive: true, mode: 0o700 });
    const savedTmpdir = process.env.TMUX_TMPDIR;
    const savedTmux = process.env.TMUX;
    const savedTmuxPane = process.env.TMUX_PANE;
    process.env.TMUX_TMPDIR = roomTmpdir;
    // $TMUX overrides TMUX_TMPDIR: run from inside a pane, every tmux call here — including the
    // reap's kill-server — would hit the DEFAULT server. Cleared so the redirect actually binds.
    delete process.env.TMUX;
    delete process.env.TMUX_PANE;
    reapRoom = () => {
      try { execFileSync('tmux', ['kill-server'], { stdio: 'ignore' }); } catch { /* already gone */ }
      if (savedTmpdir === undefined) delete process.env.TMUX_TMPDIR; else process.env.TMUX_TMPDIR = savedTmpdir;
      if (savedTmux === undefined) delete process.env.TMUX; else process.env.TMUX = savedTmux;
      if (savedTmuxPane === undefined) delete process.env.TMUX_PANE; else process.env.TMUX_PANE = savedTmuxPane;
      try { fs.rmSync(roomTmpdir, { recursive: true, force: true }); } catch {}
    };
    execFileSync('tmux', ['new-session', '-d', '-s', 'probegoal', 'sleep', '600'], { stdio: ['ignore', 'pipe', 'pipe'] });

    const row = fire(ctx, { cast: 'test-headed', sessionMode: 'headed' });
    const res = await ctx.mgr.spawnSeat(row.exec_id, {
      room: 'probegoal', seatName: 'probe-seat', seatDir, dryRun: true,
    });
    assert(res.dryRun === true, 'leg9: dryRun returns without launching');
    assert(res.workdir === fs.realpathSync(seatDir), 'leg9: the SEAT DESCRIPTOR folder is the workdir (R7 — cognitive material comes from the seat, never the profile)');
    assert(res.tmuxArgv[0] === 'tmux', 'leg9: a composed tmux argv came back');
    assert(res.scopeArgv.includes('MemoryMax=64M'), "leg9: the PROFILE's caps ride the scope (R7 — mechanism comes from the profile)");
    lines.push('leg9 R7 split: workdir from the seat descriptor, caps/argv from the profile, in one composition');

    // ── leg 9b: the EFFORT RUNG reaches the SEAT door too ─────────────────────────────────────
    // The headless door has composed the rung since `d-0811lp-effort-lane-build-now` (2026-08-11)
    // and probe-effort-lane proves it there. This door composed its own argv and never consulted
    // the ladder, so a HEADED seat ran the harness default no matter what its cast asked for —
    // silently, which is exactly what G-270 forbids. Same one interpreter (`resolveEffort`), so
    // the assertion is the profile's OWN rung literal, never a spelling this probe knows.
    const dryEffort = await ctx.mgr.spawnSeat(row.exec_id, {
      room: 'probegoal', seatName: 'probe-seat', seatDir, dryRun: true, effort: 2,
    });
    const inner = dryEffort.wrappedArgv;
    const tEffort = inner.lastIndexOf('-t');
    assert(tEffort !== -1 && inner[tEffort + 1] === '0.2',
      `leg9b: rung 2 must compose the fixture ladder's own rung-2 literal; got ${inner.join(' ')}`);
    // …and a rung outside the ladder is REFUSED here exactly as it is headless — never clamped.
    let outOfRange = null;
    try {
      await ctx.mgr.spawnSeat(row.exec_id, { room: 'probegoal', seatName: 'probe-seat', seatDir, dryRun: true, effort: 9 });
    } catch (e) { outOfRange = e; }
    assert(outOfRange && outOfRange.code === 'E_UNKNOWN_EFFORT',
      `leg9b: rung 9 on a 2-rung ladder must refuse E_UNKNOWN_EFFORT (got ${outOfRange && outOfRange.code})`);
    lines.push('leg9b effort: the seat door composes the rung through the SAME resolveEffort the headless door uses; out-of-range refuses');

    // No store row was written by a dry run.
    const after = ctx.store.getExecution(row.exec_id);
    assert(!after.session_id, 'leg10: dryRun wrote no session id to the store');
    lines.push('leg10 dry-run purity: no store row mutated, no pane created');

    // The workdir gate is REUSED, not relaxed: a seat folder outside the profile's workdir_root
    // is refused. This is the boundary `r-711-write-bounds` will redesign at task 7.11 — a need
    // to SURFACE, never one to widen here.
    // ⚠ A REAL, CAST SEAT FOLDER outside the root (7.787), not a bare directory. Containment is a
    // property of A SPEC's `workdir_root`, and since `#d-abolish-profile-names` a dispatch gets its
    // spec from the seat descriptor — so a dir with no `seat.md` is refused for not being a seat at
    // all (`E_NOT_A_SEAT_FOLDER`) before containment can speak. Handing the gate a genuine seat is
    // what actually exercises it; the other refusal keeps its own leg in probe-seat-launch-gate.
    const outsideSeat = path.join(ctx.escapedir, '.rbtv', 'goals', 'g', 'seats', 'escapee');
    fs.mkdirSync(outsideSeat, { recursive: true });
    fs.writeFileSync(path.join(outsideSeat, 'seat.md'), '---\nseat: escapee\nharness: bash\nmodel: test-headed\n---\n');
    let escaped = null;
    try {
      await ctx.mgr.spawnSeat(row.exec_id, { room: 'probe-room', seatName: 's', seatDir: outsideSeat, dryRun: true });
    } catch (e) { escaped = e; }
    assert(escaped && escaped.code === 'E_WORKDIR_ESCAPE', `leg11: seat folder outside workdir_root refuses (got ${escaped && escaped.code})`);
    lines.push('leg11 containment: a seat folder outside the profile workdir_root is refused with E_WORKDIR_ESCAPE — gate reused, not relaxed');

    let noSeat = null;
    try {
      await ctx.mgr.spawnSeat(row.exec_id, { room: 'probe-room', seatName: 's', dryRun: true });
    } catch (e) { noSeat = e; }
    assert(noSeat && noSeat.code === 'E_BAD_REQUEST', 'leg12: a seat spawn without a seat descriptor folder is refused');
    lines.push('leg12 R7 guard: no seat descriptor folder -> E_BAD_REQUEST, never a profile-supplied fallback');
  } finally {
    reapRoom();
    teardown(ctx);
  }

  // ── NOT RUN — stated, never stubbed ───────────────────────────────────────────────────────
  lines.push('');
  lines.push('NOT RUN (require a LIVE daemon-spawned seat; they belong to node A4-verify and are');
  lines.push('held while guard B1 is unresolved — r-bwrap-fail-posture. None of these is stubbed:');
  lines.push('  - kernel-cgroup memory.max readback from a live tmux-spawned seat');
  lines.push('  - the bwrap file-absence check re-run inside that live seat (this, not A1, closes 7.30\'s flag)');
  lines.push('  - a headless job spawning and completing unchanged through the untouched carrier');
  lines.push('  - pane/seat identity survival across a close/renew');
});
