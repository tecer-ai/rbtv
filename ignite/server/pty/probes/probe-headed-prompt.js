'use strict';

// Criterion 8 (Test Plan): headed prompt carriage is DEFINED or TYPED-REJECTED for every profile
// shape (session-surface-spec.md Design 3, OQ-F RULED D83; vocabulary NARROWED to file|keystroke
// by the batch-08 item 4 half A owner ruling, 2026-07-20 — `argv` REMOVED so caller free text
// NEVER becomes argv).
//   (a) prompt + headed on a NO-carriage profile   -> typed rejection (E_HEADED_PROMPT_REJECTED).
//   (b) prompt + headed on the RETIRED argv-carriage profile -> typed rejection
//       (E_HEADED_PROMPT_CARRIAGE — the spawn gate refuses the retired carriage; nothing spawns).
//   (c) stdin carriage -> structurally absent (a config-load failure), proven at the unit level.
//   (c2) composeHeadedArgv refuses the retired argv carriage at the unit level too — the
//        {prompt}-slot substitution path no longer exists.

const { setup, fire, teardown, capture } = require('./lib');
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

    // (b) the RETIRED argv carriage: a prompt against test-headed-argv (injected post-config;
    // config.js refuses this profile at LOAD — probe-carriage-vocab.js proves that) must be
    // refused TYPED at the spawn gate, and nothing may spawn.
    const firedD = fire(ctx, { profile: 'test-headed-argv', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    let argvRejected = false;
    try {
      const r = await ctx.routed.spawn(firedD.exec_id, 'test-headed-argv', 'headed', 'PROMPTPAYLOAD', null, 'probe');
      if (r && r.unit_name) ctx.units.push(r.unit_name);
    } catch (e) {
      argvRejected = true;
      if (e.code !== 'E_HEADED_PROMPT_CARRIAGE') throw new Error(`(b) retired argv carriage refused with WRONG code ${e.code} (expected E_HEADED_PROMPT_CARRIAGE)`);
      lines.push(`(b) prompt + headed on the RETIRED argv-carriage profile -> TYPED REJECTION ${e.code}: ${e.message}`);
    }
    if (!argvRejected) throw new Error('(b) the retired argv carriage was NOT rejected — a {prompt}-substitution path survives');

    // (c) unit-level: composeHeadedArgv rejects stdin carriage and an unknown carriage.
    let stdinRejected = false;
    try { validateHeadedCarriage({ tui: { argv: ['x'], prompt: 'stdin' } }, 'probe'); }
    catch (e) { stdinRejected = true; lines.push(`(c) stdin carriage -> ${e.code}: structurally absent`); }
    if (!stdinRejected) throw new Error('(c) stdin carriage was not rejected as structurally absent');

    // (c2) unit-level: the retired argv carriage is refused by composeHeadedArgv directly.
    let unitArgvRejected = false;
    try { composeHeadedArgv({ tui: { argv: ['tui', '--prompt', '{prompt}'], prompt: 'argv' } }, 'a b c', 'probe', {}); }
    catch (e) {
      unitArgvRejected = true;
      if (e.code !== 'E_HEADED_PROMPT_CARRIAGE') throw new Error(`(c2) retired argv carriage refused with WRONG code ${e.code}`);
      lines.push(`(c2) composeHeadedArgv argv carriage -> TYPED REJECTION ${e.code} (retired, batch-08 item 4)`);
    }
    if (!unitArgvRejected) throw new Error('(c2) composeHeadedArgv accepted the retired argv carriage');

    lines.push('RESULT: prompt carriage is reject-by-default for no-carriage profiles; the retired argv carriage is TYPED-REJECTED at the spawn gate and the unit level; stdin is structurally absent.');
  } finally {
    teardown(ctx);
  }
});
