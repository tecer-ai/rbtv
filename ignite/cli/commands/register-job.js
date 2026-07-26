'use strict';

// `ignite register-job` — wraps the `register-job` intent (task 7.12; owner ruling
// 2026-07-25). Thin wrapper only: this file builds a payload and hands it to the
// gateway client; it never touches the store or the catalogue directly.
//
// ⚑ REGISTER vs ADD. `register-job` puts a job DEFINITION in the catalogue — what the
// daemon is ABLE to run. `add-job` schedules a run of something already registered.
// The queue's own foreign key enforces the order (queue.job_id REFERENCES jobs.job_id):
// a job must be registered before it can be queued.

const { CliUsageError } = require('../lib/errors');
const { takeValue, takeFlag } = require('../lib/args');
const { finish } = require('../lib/output');

const ACTION_TYPES = ['launch-agent', 'fire-tool', 'start-workflow', 'send-message'];

const HELP = `ignite register-job <job-id> --action-type <${ACTION_TYPES.join('|')}>
                     [--function <name>]        # defaults to the action type
                     [--args-schema '<json>']   # defaults to {}
                     [--description '<text>']
                     [--disabled] [--dry-run]

  Registers a job DEFINITION in the catalogue (what the daemon is able to run);
  use add-job to schedule a run of it. Create-only: an id already registered is
  refused — nothing is ever overwritten. --dry-run: validate-only, nothing written.`;

function build(argv) {
  const jobId = argv.shift();
  if (!jobId || jobId.startsWith('--')) {
    throw new CliUsageError('register-job requires a job id as its first argument');
  }

  const actionType = takeValue(argv, '--action-type');
  if (!ACTION_TYPES.includes(actionType)) {
    throw new CliUsageError(`register-job requires --action-type ${ACTION_TYPES.join('|')}`);
  }

  // v1 convention: `function` mirrors `action_type` unless the caller says otherwise.
  // The column is the binding seam for future per-function handlers — no runtime code
  // selects on it today (the ticker's dispatch keys on action_type + args) — but it is
  // NOT NULL in the schema, so the wire always carries it explicitly.
  const fn = takeValue(argv, '--function') ?? actionType;

  const schemaJson = takeValue(argv, '--args-schema');
  let argsSchema = {};
  if (schemaJson !== undefined) {
    try {
      argsSchema = JSON.parse(schemaJson);
    } catch (err) {
      throw new CliUsageError(`--args-schema is not valid JSON: ${err.message}`);
    }
    if (argsSchema === null || typeof argsSchema !== 'object' || Array.isArray(argsSchema)) {
      throw new CliUsageError('--args-schema must decode to a JSON object');
    }
  }

  const description = takeValue(argv, '--description');
  const disabled = takeFlag(argv, '--disabled');
  const dryRun = takeFlag(argv, '--dry-run');

  if (argv.length > 0) {
    throw new CliUsageError(`register-job: unrecognized argument(s): ${argv.join(' ')}`);
  }

  const payload = {
    job_id: jobId,
    action_type: actionType,
    function: fn,
    args_schema: argsSchema,
  };
  if (description !== undefined) payload.description = description;
  if (disabled) payload.enabled = false;
  if (dryRun) payload.dry_run = true;

  return { intent: 'register-job', payload };
}

async function run(argv, ctx) {
  const { intent, payload } = build(argv);
  const { envelope } = await ctx.call(intent, payload);
  return finish(envelope, {
    json: ctx.json,
    renderSuccess: (result) => {
      if (result.dry_run) console.log('dry-run: VALID — validated, nothing registered');
      else console.log(`registered: job "${result.job_id}" (${result.action_type}, ${result.enabled ? 'enabled' : 'disabled'})`);
    },
  });
}

module.exports = { HELP, build, run };
