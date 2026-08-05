'use strict';

// `ignite deregister-job <job-id>` — wraps the `deregister-job` intent (task 7.364 /
// F20; issue G-m4-demo-verdict-assembler-0804-1610). Thin wrapper only: it builds a
// payload and hands it to the gateway client; it never touches the store.
//
// ⚑ DEREGISTER vs REMOVE. `remove-job` takes a QUEUE id and cancels a pending schedule;
// it has never touched the catalogue. `deregister-job` takes a CATALOGUE job id and
// retires the DEFINITION. The two words are one letter apart in the help and were the
// whole confusion the filing issue records — read the argument, not the verb.

const { CliUsageError } = require('../lib/errors');
const { requirePositional } = require('../lib/args');
const { finish } = require('../lib/output');

const HELP = `ignite deregister-job <job-id>

  Retires a registered job DEFINITION by DISABLING it: the row and its id stay,
  \`enabled\` goes to 0, and the daemon stops firing it — the ticker defers every
  due queue row of a disabled job, and add-job refuses it. Typed refusal on an
  unknown id; never a success over nothing.

  Takes a CATALOGUE job id, unlike remove-job, which takes a QUEUE id.
  Idempotent: deregistering an already-disabled job succeeds and says so.
  It does NOT delete pending queue rows — they stay, deferred, and the count is
  printed; use remove-job <queue-id> to clear them.`;

function build(argv) {
  const jobId = requirePositional(argv, 'job-id');
  if (argv.length > 0) throw new CliUsageError(`deregister-job: unrecognized argument(s): ${argv.join(' ')}`);
  return { intent: 'deregister-job', payload: { job_id: jobId } };
}

function renderDeregistered(result) {
  // The no-op case is said OUT LOUD rather than rendered identically to a real change:
  // a teardown re-run that silently looks like the first run teaches nothing about which
  // one actually stopped the job.
  const what = result.was_enabled
    ? 'deregistered: job'
    : 'already disabled (nothing changed): job';
  const home = result.homed ? ` — was homed at ${result.homed.goal}/${result.homed.seat}` : '';
  console.log(`${what} "${result.job_id}" is now disabled and will not fire${home}`);
  if (result.pending_queue_rows > 0) {
    console.log(
      `${result.pending_queue_rows} pending queue row(s) still reference this job. They will NOT fire `
      + '(the ticker defers them), but they are not removed — use `ignite remove-job <queue-id>` to clear them.',
    );
  }
}

async function run(argv, ctx) {
  const { intent, payload } = build(argv);
  const { envelope } = await ctx.call(intent, payload);
  return finish(envelope, { json: ctx.json, renderSuccess: renderDeregistered });
}

module.exports = { HELP, build, run };
