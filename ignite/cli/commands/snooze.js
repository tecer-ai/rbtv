'use strict';

// `ignite snooze <kind> <subject> --minutes <N>` — wraps the `snooze` intent
// (ADX-14, owner ruling D71/D45; internal-api-contract-spec.md §1 `snooze`).
// OWNER-ONLY: authz is enforced server-side (UNAUTHORIZED_SENDER for a
// non-owner sender) — this CLI never gates on kind locally, it just forwards
// and lets the typed refusal come back loud.

const { CliUsageError } = require('../lib/errors');
const { takeValue, requirePositional } = require('../lib/args');
const { finish } = require('../lib/output');

const HELP = `ignite snooze <kind> <subject> --minutes <N>

  OWNER-ONLY. Snoozes the standing warning (kind, subject) for N minutes;
  never clears it. No standing warning for (kind, subject) is a clean
  success (nothing changed) — never an error. There is no dismiss/clear
  subcommand: snooze never clears a warning (D45).`;

function build(argv) {
  const kind = requirePositional(argv, 'kind');
  const subject = requirePositional(argv, 'subject');
  const rawMinutes = takeValue(argv, '--minutes');
  if (rawMinutes === undefined) throw new CliUsageError('snooze requires --minutes <N>');
  if (!/^\d+$/.test(rawMinutes) || Number(rawMinutes) <= 0) {
    throw new CliUsageError('--minutes must be a positive integer');
  }
  if (argv.length > 0) throw new CliUsageError(`snooze: unrecognized argument(s): ${argv.join(' ')}`);

  // The CLI passes minutes straight through — the minutes-to-ticks conversion
  // is the store's business (D44/p3-3), never re-implemented here.
  return { intent: 'snooze', payload: { kind, subject, minutes: rawMinutes } };
}

function renderSnoozed(result) {
  if (result.snoozed) {
    console.log(`snoozed: ${result.kind}/${result.subject} until tick ${result.snoozed_until_tick}`);
  } else {
    console.log(`nothing to snooze: no standing warning for ${result.kind}/${result.subject}`);
  }
}

async function run(argv, ctx) {
  const { intent, payload } = build(argv);
  const { envelope } = await ctx.call(intent, payload);
  return finish(envelope, { json: ctx.json, renderSuccess: renderSnoozed });
}

module.exports = { HELP, build, run };
