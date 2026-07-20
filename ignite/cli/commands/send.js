'use strict';

// `ignite send <session-id> --data <string>` — wraps the `send-to-session`
// intent: keystroke bytes into a live HEADED session's pty (the TAKE-OVER half
// of headed mode, CMP-9's keystroke rung). Thin wrapper only: it builds the
// payload and hands it to the gateway client — the daemon stays the sole
// keystroke mediator and audit point (owner rulings D92/D93).

const { CliUsageError } = require('../lib/errors');
const { requirePositional, takeValue } = require('../lib/args');
const { finish } = require('../lib/output');

const HELP = `ignite send <session-id> --data <string>

  Sends keystroke bytes into a live HEADED session's pty. <session-id> is the
  integer execution id (the same id \`inspect status\` takes). Headed sessions
  only — a headless session's id is a typed refusal, never a hang.`;

function build(argv) {
  const raw = requirePositional(argv, 'session-id');
  const data = takeValue(argv, '--data');
  if (argv.length > 0) throw new CliUsageError(`send: unrecognized argument(s): ${argv.join(' ')}`);
  if (data === undefined) throw new CliUsageError('send requires --data <string>');

  // ⚑ Local checks END at usage (both flags present). The id crosses AS ARGV
  // GAVE IT — the gateway coerces numeric strings and refuses the rest
  // (parse.js parseSessionScopedId) — and data's non-empty check is the
  // GATEWAY's shape refusal, not a second local copy. The 4096-byte max is
  // likewise deliberately absent here: a SERVER-ENFORCED policy bound
  // (PIPE_BUF atomicity) that must not gain a second source of truth in this
  // CLI (the binding note in gateway/parse.js parseSendToSession).
  return { intent: 'send-to-session', payload: { id: raw, data } };
}

async function run(argv, ctx) {
  const { intent, payload } = build(argv);
  const { envelope } = await ctx.call(intent, payload);
  return finish(envelope, {
    json: ctx.json,
    renderSuccess: (result) => {
      console.log(`sent: ${result.wrote} bytes to session ${result.id}`);
    },
  });
}

module.exports = { HELP, build, run };
