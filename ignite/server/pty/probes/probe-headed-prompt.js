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
//   (d) task 7.22: a MULTI-TURN-SHAPED prompt (leading dash, embedded newline, $()) RIDES a
//       file-carriage headed profile to the pty — the prompt is 0600-file DATA, never argv, so
//       the request-level flag-injection gate must NOT refuse it (the over-refusal p7-multiturn
//       removed headless-side). Proven end-to-end: spawn succeeds, the prompt file holds the
//       EXACT bytes, and the TUI inside the sandbox reads the file and renders its properties.

const fs = require('node:fs');
const path = require('node:path');
const { setup, fire, teardown, capture, sleep } = require('./lib');
const { composeHeadedArgv, validateHeadedCarriage } = require('../carriage');

// TUI for case (d): reads the prompt file handed via the {prompt_file} argv slot and renders its
// observed properties (length, leading dash, embedded newline, $() marker) — so a post-attach
// screen capture proves the multi-turn prompt content reached the TUI through the pty sandbox.
const PF_READER_SRC =
  "const fs=require('node:fs');const w=s=>process.stdout.write(s);" +
  "let frame;try{const c=fs.readFileSync(process.argv[1],'utf8');" +
  "frame='PF:'+c.length+':'+(c.startsWith('-')?'DASH':'nodash')+':'+(c.includes('\\n')?'NL':'nonl')+':'+(c.includes('$(')?'SUBST':'nosubst');}" +
  "catch(e){frame='PFERR:'+e.message;}" +
  "const paint=()=>w('\\x1b[2J\\x1b[H'+frame+'\\r\\n');paint();process.on('SIGWINCH',paint);" +
  "setTimeout(()=>process.exit(0),60000);";

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

    // (d) task 7.22: multi-turn-shaped prompt rides a FILE-carriage headed profile to the pty.
    const MULTI = '-continue the composed plan\nsecond turn: verify $(echo unexpanded) stays literal\n-third turn; done';
    ctx.mgr.config.profiles['test-headed-file'] = {
      exec: { argv: ['sleep', '3600'], prompt: 'stdin' },
      session_ref: { source: 'cwd-implicit' },
      headed: { tui: { argv: ['node', '-e', PF_READER_SRC, '{prompt_file}'], prompt: 'file' } },
      workdir_root: ctx.workRoot,
      caps: { memory_max: '256M', runtime_max: '1h' },
      sandbox: { ReadWritePaths: ['{workdir}'], NoNewPrivileges: true },
    };
    const firedM = fire(ctx, { profile: 'test-headed-file', sessionMode: 'headed', workdir: ctx.defaultWorkdir });
    let rM;
    try {
      rM = await ctx.routed.spawn(firedM.exec_id, 'test-headed-file', 'headed', MULTI, null, 'probe');
    } catch (e) {
      throw new Error(`(d) a multi-turn-shaped prompt on a file-carriage headed profile was REFUSED (${e.code}: ${e.message}) — the 7.22 over-refusal is back`);
    }
    if (rM && rM.unit_name) ctx.units.push(rM.unit_name);
    lines.push(`(d) spawn accepted the multi-turn-shaped prompt on file carriage (unit ${rM.unit_name})`);

    // Byte-exact: the 0600 prompt file holds EXACTLY the multi-turn bytes.
    const promptDir = path.join(ctx.dataRoot, 'prompts');
    const promptFiles = fs.readdirSync(promptDir).filter((f) => f.endsWith('.txt'));
    if (promptFiles.length !== 1) throw new Error(`(d) expected exactly 1 prompt file, found ${promptFiles.length}`);
    const pfPath = path.join(promptDir, promptFiles[0]);
    const pfContent = fs.readFileSync(pfPath, 'utf8');
    if (pfContent !== MULTI) throw new Error(`(d) prompt file bytes differ from the supplied prompt (got ${JSON.stringify(pfContent)})`);
    const pfMode = fs.statSync(pfPath).mode & 0o777;
    lines.push(`(d) prompt file ${pfPath} byte-exact (${pfContent.length} chars), mode ${pfMode.toString(8)}`);

    // To-the-pty: the TUI inside the sandbox read the file and rendered its properties.
    const expectFrame = `PF:${MULTI.length}:DASH:NL:SUBST`;
    let screen = '';
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline) {
      try { screen = ctx.ptyHost.captureScreen(firedM.exec_id).screen; } catch { screen = ''; }
      if (screen.includes(expectFrame) || screen.includes('PFERR')) break;
      await sleep(300);
    }
    if (!screen.includes(expectFrame)) throw new Error(`(d) rendered screen never showed ${expectFrame} — prompt did not demonstrably reach the pty TUI (screen: ${JSON.stringify(screen.slice(0, 200))})`);
    lines.push(`(d) TUI rendered ${expectFrame} — the multi-turn prompt rode file carriage to the pty`);

    lines.push('RESULT: prompt carriage is reject-by-default for no-carriage profiles; the retired argv carriage is TYPED-REJECTED at the spawn gate and the unit level; stdin is structurally absent; a multi-turn-shaped prompt RIDES file carriage to the pty (7.22).');
  } finally {
    teardown(ctx);
  }
});
