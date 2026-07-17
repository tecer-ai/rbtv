'use strict';

// Criterion 8 (Test Plan): headed prompt carriage is DEFINED or TYPED-REJECTED for every profile
// shape (session-surface-spec.md Design 3, OQ-F RULED D83).
//   (a) prompt + headed on a NO-carriage profile  -> typed rejection (E_HEADED_PROMPT_REJECTED).
//   (b) prompt + headed on an argv-carriage profile -> the prompt is DELIVERED into the {prompt}
//       argv slot (proven by the TUI echoing its argv, which shows the prompt landed).
//   (c) stdin carriage -> structurally absent (a config-load failure), proven at the unit level.
//
// NOTE: the argv-carriage profile (test-headed-argv) carries headed.tui.prompt, a key
// server/spawn/config.js currently REJECTS (KNOWN_TUI_KEYS={'argv'}) — its acceptance is a
// conductor-owed config.js extension OUTSIDE this task's allowlist (see the dispatch concerns).
// lib.js injects it post-config to exercise the carriage machinery the pty host already owns.

const { setup, fire, teardown, capture, sleep } = require('./lib');
const { composeHeadedArgv, validateHeadedCarriage } = require('../carriage');

capture('probe-headed-prompt', async (lines) => {
  const ctx = setup();
  try {
    // (a) reject-by-default: a prompt against test-headed (headed.tui.argv only, no carriage).
    const firedR = fire(ctx, { profile: 'test-headed', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    let rejected = false;
    try {
      const r = await ctx.routed.spawn(firedR.exec_id, 'test-headed', 'headed', 'some prompt', null, 'probe');
      if (r && r.unit_name) ctx.units.push(r.unit_name);
    } catch (e) {
      rejected = true;
      lines.push(`(a) prompt + headed on NO-carriage profile -> TYPED REJECTION ${e.code}: ${e.message}`);
    }
    if (!rejected) throw new Error('(a) a prompt against a no-carriage headed profile was NOT rejected');

    // (b) delivery: prompt into the {prompt} argv slot of test-headed-argv; the TUI echoes argv.
    const payload = `PROMPTPAYLOAD-${Math.floor(Math.random() * 1e6)}`;
    const firedD = fire(ctx, { profile: 'test-headed-argv', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    lines.push(`(b) action: spawn headed test-headed-argv with prompt='${payload}' (carriage=argv, {prompt} slot)`);
    const rowD = await ctx.routed.spawn(firedD.exec_id, 'test-headed-argv', 'headed', payload, null, 'probe');
    ctx.units.push(rowD.unit_name);
    await sleep(900);
    const screen = ctx.ptyHost.captureScreen(rowD.exec_id).screen;
    lines.push(`(b) rendered screen (TUI echoing its argv):\n${screen}`);
    if (!screen.includes(payload)) throw new Error(`(b) prompt payload '${payload}' did not reach the TUI argv — delivery failed`);
    lines.push(`(b) DELIVERED: the prompt filled the {prompt} argv slot and reached the TUI.`);

    // (c) unit-level: composeHeadedArgv rejects stdin carriage and an unknown carriage.
    let stdinRejected = false;
    try { validateHeadedCarriage({ tui: { argv: ['x'], prompt: 'stdin' } }, 'probe'); }
    catch (e) { stdinRejected = true; lines.push(`(c) stdin carriage -> ${e.code}: structurally absent`); }
    if (!stdinRejected) throw new Error('(c) stdin carriage was not rejected as structurally absent');

    // (c2) argv delivery composition is deterministic and closed-substitution (no split).
    const composed = composeHeadedArgv({ tui: { argv: ['tui', '--prompt', '{prompt}'], prompt: 'argv' } }, 'a b c', 'probe', {});
    lines.push(`(c2) composeHeadedArgv argv-slot -> ${JSON.stringify(composed.argv)}`);
    if (JSON.stringify(composed.argv) !== JSON.stringify(['tui', '--prompt', 'a b c'])) throw new Error('(c2) argv-slot substitution wrong');

    lines.push('RESULT: prompt carriage is reject-by-default for no-carriage profiles AND delivered for a declared argv carriage; stdin is structurally absent.');
  } finally {
    teardown(ctx);
  }
});
