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
const { requirePositional, takeFlag } = require('../lib/args');
const { finish } = require('../lib/output');

const HELP = `ignite deregister-job <job-id> [--purge]

  Retires a registered job DEFINITION by DISABLING it: the row and its id stay,
  \`enabled\` goes to 0, and the daemon stops firing it — the ticker defers every
  due queue row of a disabled job, and add-job refuses it. Typed refusal on an
  unknown id; never a success over nothing.

  Takes a CATALOGUE job id, unlike remove-job, which takes a QUEUE id.
  Idempotent: deregistering an already-disabled job succeeds and says so.
  It does NOT delete pending queue rows — they stay, deferred, and the count is
  printed; use remove-job <queue-id> to clear them.

  --purge  DELETE the row instead of disabling it, which FREES THE ID for
           re-registration. This is the reclaim path for machine-minted
           goal-scoped ids (<goal>-workflow-start, seat-<goal>-<seat>) left
           behind when a goal is torn down. Refused unless the job is ALREADY
           disabled, has no pending queue rows, and has no non-terminal
           execution — each refusal names the command that clears it. Run
           deregister-job first, then again with --purge.

           Past runs survive: jobs_log keeps its own copy of every execution.
           An id may name two different jobs across time; jobs_log.fired_at is
           what separates them.`;

function build(argv) {
  // Read BEFORE the positional: requirePositional takes the first non-`--` token, so an
  // un-consumed `--purge` would not be mistaken for the id — but leaving it in argv would
  // trip the unrecognized-argument guard below.
  const purge = takeFlag(argv, '--purge');
  const jobId = requirePositional(argv, 'job-id');
  if (argv.length > 0) throw new CliUsageError(`deregister-job: unrecognized argument(s): ${argv.join(' ')}`);
  return { intent: 'deregister-job', payload: { job_id: jobId, purge } };
}

function renderDeregistered(result) {
  const home = result.homed ? ` — was homed at ${result.homed.goal}/${result.homed.seat}` : '';
  // The PURGE line says "the id is free" out loud, because that is the whole reason the
  // arm exists and it is the one fact an operator came for.
  if (result.purged) {
    console.log(`purged: job "${result.job_id}" is deleted from the catalogue${home}`);
    console.log('The id is now free — `ignite register-job` can take it again. Past executions are '
      + 'untouched: jobs_log keeps its own record of every run.');
    return;
  }
  // The no-op case is said OUT LOUD rather than rendered identically to a real change:
  // a teardown re-run that silently looks like the first run teaches nothing about which
  // one actually stopped the job.
  const what = result.was_enabled
    ? 'deregistered: job'
    : 'already disabled (nothing changed): job';
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
