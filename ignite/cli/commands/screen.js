'use strict';

// `ignite screen <session-id>` — wraps the `capture-session-screen` intent
// (owner ruling D90; reachable end-to-end per D91): read a live HEADED
// session's current rendered screen —
// the JOIN/view half of the session surface. A detached snapshot, never a
// stream; every read is audited server-side BEFORE the screen is served (D94).

const { CliUsageError } = require('../lib/errors');
const { requirePositional } = require('../lib/args');
const { finish } = require('../lib/output');

const HELP = `ignite screen <session-id>

  Captures a live HEADED session's current rendered screen (a detached
  snapshot with its dimensions — never a stream). Headless sessions are
  refused: the session surface is headed-only (D7/D17). "repainting" in
  the result means the pty was just re-attached and the screen has not
  painted yet — capture again.`;

function build(argv) {
  const raw = requirePositional(argv, 'session-id');
  if (argv.length > 0) throw new CliUsageError(`screen: unrecognized argument(s): ${argv.join(' ')}`);
  // ⚑ Deliberately NO local integer check (unlike remove-job): the session id's
  // shape is the GATEWAY's shape-check — parse.js parseCaptureSessionScreen →
  // parseSessionScopedId coerces a numeric string at the ONE place raw sender
  // input is interpreted and refuses anything else as SHAPE_INVALID (exit 4).
  return { intent: 'capture-session-screen', payload: { id: raw } };
}

function renderScreen(result) {
  const note = result.repainting
    ? ' (repainting: the re-attached pty has not painted yet — capture again)'
    : '';
  console.log(`session ${result.id} — ${result.rows}x${result.cols}${note}`);
  // The screen is a rendered plain string; print it as-is.
  process.stdout.write(result.screen.endsWith('\n') ? result.screen : result.screen + '\n');
}

async function run(argv, ctx) {
  const { intent, payload } = build(argv);
  const { envelope } = await ctx.call(intent, payload);
  return finish(envelope, { json: ctx.json, renderSuccess: renderScreen });
}

module.exports = { HELP, build, run };
