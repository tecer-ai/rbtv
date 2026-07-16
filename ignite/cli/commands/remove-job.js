'use strict';

// `ignite remove-job <queue-id>` — wraps the `remove-job` intent.

const { CliUsageError } = require('../lib/errors');
const { requirePositional } = require('../lib/args');
const { finish } = require('../lib/output');

const HELP = `ignite remove-job <queue-id>

  Removes a PENDING queue row (typed not-found if it does not exist).
  Removing a REPEATING row cancels the whole recurring schedule, not just
  the next fire — the CLI prints that loudly (D68).`;

function build(argv) {
  const raw = requirePositional(argv, 'queue-id');
  if (argv.length > 0) throw new CliUsageError(`remove-job: unrecognized argument(s): ${argv.join(' ')}`);
  if (!/^\d+$/.test(raw)) throw new CliUsageError('remove-job requires an integer queue id');

  // ⚑ The wire field is named `jobId` — a ratified MISNOMER (D69,
  // gateway/parse.js): it carries a QUEUE-ROW handle, not a catalogue job_id.
  // Kept verbatim on purpose; do not "fix" it here.
  return { intent: 'remove-job', payload: { jobId: raw } };
}

function renderRemoved(result) {
  const parts = [`trigger=${result.trigger_kind}`];
  if (result.repeat_rule) parts.push(`repeat_rule="${result.repeat_rule}"`);
  if (result.interval_seconds) parts.push(`interval_seconds=${result.interval_seconds}`);
  console.log(`removed: ${parts.join(' ')}`);
  if (result.trigger_kind === 'periodic' || result.repeat_rule) {
    console.log('the WHOLE recurring schedule was cancelled, not just the next fire.');
  }
}

async function run(argv, ctx) {
  const { intent, payload } = build(argv);
  const { envelope } = await ctx.call(intent, payload);
  return finish(envelope, { json: ctx.json, renderSuccess: renderRemoved });
}

module.exports = { HELP, build, run };
