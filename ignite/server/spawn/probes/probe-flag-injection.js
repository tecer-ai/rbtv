'use strict';

const fs = require('node:fs');
const path = require('node:path');
const yaml = require('js-yaml');
const { setup, teardown, capture, fire } = require('./lib');
const { validateSpawnRequest, composeArgv } = require('../spawn');
const { loadConfig } = require('../config');

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

    // Retired flat branch (r-seats-only-architecture (3)): a spawn naming NO workdir used to
    // fall through to the flat .rbtv/sessions/ branch — it is a typed refusal now.
    try {
      await ctx.mgr.spawn(0, 'test-quick', 'headless', 'x', null, 'probe');
      throw new Error('no-workdir spawn: UNEXPECTED PASS — the retired flat branch admitted it');
    } catch (err) {
      if (err.code !== 'E_SEATLESS_GOAL_DISPATCH') throw err;
      lines.push(`no-workdir spawn (retired flat branch): ${err.code}`);
    }

    // POSITIVE leg — stdin carriage accepts a composed-transcript prompt (newlines,
    // parentheses, dollar signs are DATA there; the pre-p7-multiturn unconditional
    // guard refused exactly this and broke every composed multi-turn prompt). Spawned into the
    // fixture's canonical seat folder — the only admitted home under r-seats-only-architecture.
    const fired = fire(ctx, { profile: 'test-quick', sessionMode: 'headless', workdir: ctx.seatDir });
    const transcript = '[owner] what is 17*23? (exactly)\n\n[assistant] 391\n\n[owner] now add 9 & say "$done"';
    const row = await ctx.mgr.spawn(fired.exec_id, 'test-quick', 'headless', transcript, ctx.seatDir, 'probe');
    lines.push(`stdin-carriage transcript prompt ACCEPTED: exec ${row.exec_id} spawned (session ${row.session_id})`);

    // ── THE SEAT DESCRIPTOR ON THE COMMAND LINE (owner ruling 2026-08-07) ──────────────────
    //
    // The ONE flag this path adds that the profile did not write, so it belongs in the probe
    // that owns what reaches argv. Three legs, because the interesting property is the
    // CONDITION, not the flag: `claude --append-system-prompt-file <missing>` runs NOTHING
    // (measured, 2.1.224), so a fix that appended it unconditionally would kill every spawn at
    // a seat with no descriptor — the leg below is what stands between that and the daemon.
    //
    // The profile is loaded from a real yaml through the real loader and the descriptor is read
    // off the fixture's real seat folder: nothing here is hand-fed a profile object.
    const claudeCfgPath = path.join(ctx.tmp, 'spawn-claude.yaml');
    fs.writeFileSync(claudeCfgPath, yaml.dump({
      bind: { host: '127.0.0.1', port: 7431 },
      auth: { senders_file: path.join(ctx.tmp, 'senders.yaml') },
      spawn: { data_root: ctx.dataRoot, carrier: 'auto', kill_grace_seconds: 2 },
      default_workdir_root: ctx.defaultWorkdir,
      profiles: {
        // argv[0] IS the harness classifier (`harnessOf` → `harnessFromBinary`). Never spawned.
        'test-claude': {
          exec: { argv: ['claude', '-p'], prompt: 'stdin' },
          session_ref: { source: 'cwd-implicit' },
          workdir_root: ctx.workRoot,
          caps: { memory_max: '64M', runtime_max: '1h' },
        },
      },
    }));
    const claudeCfg = loadConfig(claudeCfgPath);
    const claudeProfile = claudeCfg.profiles['test-claude'];
    const sleepProfile = loadConfig(ctx.cfgPath).profiles['test-sleep'];
    const descriptor = path.join(ctx.seatDir, 'seat.md');
    if (!fs.existsSync(descriptor)) throw new Error('fixture premise broken: the seat folder has no seat.md');

    const withSeat = composeArgv(claudeProfile, 'headless', 'sid-1', ctx.seatDir, 'p', ctx.dataRoot).argv;
    const i = withSeat.indexOf('--append-system-prompt-file');
    if (i < 0 || withSeat[i + 1] !== descriptor) {
      throw new Error(`claude + seat.md present: descriptor NOT on argv — ${JSON.stringify(withSeat)}`);
    }
    lines.push(`claude + seat.md present: --append-system-prompt-file ${path.basename(descriptor)} appended`);

    // No descriptor → the flag MUST be absent. This is the fatal case.
    const bareSeat = path.join(ctx.workRoot, '.rbtv', 'goals', 'probe-goal', 'seats', 'no-descriptor');
    fs.mkdirSync(bareSeat, { recursive: true });
    const withoutSeat = composeArgv(claudeProfile, 'headless', 'sid-2', bareSeat, 'p', ctx.dataRoot).argv;
    if (withoutSeat.includes('--append-system-prompt-file')) {
      throw new Error(`claude + NO seat.md: flag appended anyway — would refuse to run: ${JSON.stringify(withoutSeat)}`);
    }
    lines.push('claude + NO seat.md: flag correctly ABSENT (an unreadable file makes claude run nothing)');

    // A non-claude harness never receives a claude flag, even with a descriptor sitting there.
    const otherHarness = composeArgv(sleepProfile, 'headless', 'sid-3', ctx.seatDir, 'p', ctx.dataRoot).argv;
    if (otherHarness.includes('--append-system-prompt-file')) {
      throw new Error(`non-claude harness got a claude flag: ${JSON.stringify(otherHarness)}`);
    }
    lines.push('non-claude harness + seat.md present: no claude flag (harness-gated)');
  } finally {
    teardown(ctx);
  }
});
