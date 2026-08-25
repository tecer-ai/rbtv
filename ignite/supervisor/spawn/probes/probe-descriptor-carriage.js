'use strict';

// ── UNIFORM DESCRIPTOR CARRIAGE — the stdin half (`d-uniform-descriptor-carriage`, 2026-08-12) ──
//
// `probe-flag-injection` owns the ARGV half (claude's `--append-system-prompt-file`, its
// no-descriptor fatal case, and the harness gate). THIS probe owns the MESSAGE half: a
// non-claude harness has no system-prompt flag (measured 2026-08-07), so its descriptor rides
// the FIRST stdin message — seat.md body + separator + the wake payload — composed by
// `composeArgv` at the one choke point every headless launch passes through. Four legs:
//
//   1. non-claude + seat.md, fresh   → stdin STARTS with the descriptor and ENDS with the payload
//   2. non-claude + NO seat.md       → stdin is the payload verbatim (nothing invented)
//   3. claude + seat.md, fresh       → stdin is the payload verbatim (the descriptor rides the
//                                      flag — riding both would send it twice)
//   4. non-claude + seat.md, RESUME  → stdin is the payload verbatim (the chain's first message
//                                      already carried it; a resume must never double-send)
//
// Leg 4 exercises the function-level guard directly: the spawn door refuses resumes on specs
// with no `resume:` template, but this probe's fixture declares one precisely so the
// `!resumeRef` arm is proven where it lives, not shadowed by the door.

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, capture } = require('./lib');
const { composeArgv } = require('../spawn');
const { loadConfig } = require('../config');

function stdinText(result) {
  if (!result.stdinFile) throw new Error('spec declares prompt: stdin but composeArgv returned no stdinFile');
  return fs.readFileSync(result.stdinFile, 'utf8');
}

capture('probe-descriptor-carriage', async (lines) => {
  const ctx = setup();
  try {
    const cfg = loadConfig(ctx.cfgPath);
    // The fixture's bash/test-sleep spec is the non-claude harness; give this probe's own copy a
    // resume template so leg 4 can reach composeArgv's resume arm.
    const spec = cfg.launchSpecs['bash/test-sleep'];
    const specWithResume = { ...spec, resume: { argv: ['bash', '-c', 'exec sleep 3600', '--model', 'test-sleep'], prompt: 'stdin' } };
    // harnessOf derives the harness from exec.argv[0] (D23), so a claude-like spec is made by
    // swapping the binary; composeArgv only composes, nothing here is executed.
    const claudeLike = { ...spec, exec: { ...spec.exec, argv: ['claude', ...spec.exec.argv.slice(1)] } };
    const descriptor = path.join(ctx.seatDir, 'seat.md');
    const seatBody = fs.readFileSync(descriptor, 'utf8');
    const payload = 'the wake payload: reply DONE';

    // 1. non-claude + seat.md, fresh → descriptor + separator + payload.
    const fresh = stdinText(composeArgv(spec, 'headless', 'dc-1', ctx.seatDir, payload, ctx.dataRoot));
    if (!fresh.startsWith(seatBody)) throw new Error('leg 1: stdin does not START with the seat.md body');
    if (!fresh.endsWith(payload)) throw new Error('leg 1: stdin does not END with the wake payload');
    if (fresh === payload) throw new Error('leg 1: descriptor absent from the composed first message');
    lines.push('non-claude fresh + seat.md: first message = descriptor + separator + payload');

    // 2. non-claude + NO seat.md → payload verbatim.
    const bareSeat = path.join(ctx.workRoot, '.rbtv', 'goals', 'probe-goal', 'seats', 'dc-no-descriptor');
    fs.mkdirSync(bareSeat, { recursive: true });
    const noDesc = stdinText(composeArgv(spec, 'headless', 'dc-2', bareSeat, payload, ctx.dataRoot));
    if (noDesc !== payload) throw new Error(`leg 2: expected the payload verbatim, got ${JSON.stringify(noDesc.slice(0, 120))}`);
    lines.push('non-claude fresh + NO seat.md: first message is the payload verbatim');

    // 3. claude + seat.md → payload verbatim on stdin (the flag carries the descriptor).
    const claudeStdin = stdinText(composeArgv(claudeLike, 'headless', 'dc-3', ctx.seatDir, payload, ctx.dataRoot));
    if (claudeStdin !== payload) throw new Error('leg 3: claude stdin carries the descriptor too — it would arrive twice');
    lines.push('claude fresh + seat.md: stdin is the payload verbatim (descriptor rides the flag)');

    // 4. non-claude RESUME + seat.md → payload verbatim (never double-sent).
    const resumed = stdinText(composeArgv(specWithResume, 'headless', 'dc-4', ctx.seatDir, payload, ctx.dataRoot, 'dc-1'));
    if (resumed !== payload) throw new Error('leg 4: a resume re-sent the descriptor');
    lines.push('non-claude resume + seat.md: first message is the payload verbatim (no double-send)');

    lines.push('result: descriptor rides exactly one carriage per launch, and only on fresh launches');
  } finally {
    teardown(ctx);
  }
});
