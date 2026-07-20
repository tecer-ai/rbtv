'use strict';

// `ignite kill <session-id>` — wraps the `kill-session` intent (cli-expansion
// ruling D2): TERM → grace → KILL of the whole process tree; the session's
// status becomes `killed` (D23 closed enum).

const { CliUsageError } = require('../lib/errors');
const { requirePositional } = require('../lib/args');
const { finish } = require('../lib/output');

const HELP = `ignite kill <session-id>

  Kills a session: TERM, a grace period, then KILL of the whole process
  tree; the session's status becomes "killed". Works on any session mode
  (headless or headed). Typed not-found for an unknown id; a session
  already terminal (done/failed/killed) is refused typed.`;

function build(argv) {
  const raw = requirePositional(argv, 'session-id');
  if (argv.length > 0) throw new CliUsageError(`kill: unrecognized argument(s): ${argv.join(' ')}`);

  // No local integer check — deliberately UNLIKE remove-job. The gateway's
  // shape-check (parse.js parseSessionScopedId) owns the integer refusal, so a
  // non-integer id is a typed SHAPE_INVALID (exit 4), keeping the refusal
  // vocabulary in the ONE place raw sender input is interpreted. A numeric
  // string off argv is coerced there, exactly as send/screen's ids are.
  return { intent: 'kill-session', payload: { id: raw } };
}

function renderKilled(result) {
  console.log(`killed: session ${result.execId} (signal ${result.signal ?? 'none'})`);
}

async function run(argv, ctx) {
  const { intent, payload } = build(argv);
  const { envelope } = await ctx.call(intent, payload);
  return finish(envelope, { json: ctx.json, renderSuccess: renderKilled });
}

module.exports = { HELP, build, run };
