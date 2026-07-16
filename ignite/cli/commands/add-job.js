'use strict';

// `ignite add-job` — wraps the `enqueue-job` intent (gateway-cli-spec.md § CLI
// Surface). Thin wrapper only: this file builds a payload and hands it to the
// gateway client; it never touches the store, the spawn machinery, or the
// job/profile catalogue directly.

const { CliUsageError } = require('../lib/errors');
const { takeValue, takeFlag, takeRepeated } = require('../lib/args');
const { finish } = require('../lib/output');

const HELP = `ignite add-job --fn <function> [--arg k=v ...] [--args-json '<json>']
                --trigger scheduled|periodic
                scheduled: --at <ISO-8601 UTC datetime> [--repeat <5-field cron>]
                periodic:  --every <seconds>  (first fire defaults to now)
                [--profile <name>] [--session-mode headless|headed] [--dry-run]

  Enqueues a job (the server core dry-run-validates before writing). Prints
  the new queue id on success. --dry-run: validate-only, nothing enqueued.`;

function buildArgsObject(argv) {
  const argPairs = takeRepeated(argv, '--arg');
  const argsJson = takeValue(argv, '--args-json');
  if (argPairs.length > 0 && argsJson !== undefined) {
    throw new CliUsageError('add-job takes --arg OR --args-json, never both');
  }

  if (argsJson !== undefined) {
    let parsed;
    try {
      parsed = JSON.parse(argsJson);
    } catch (err) {
      throw new CliUsageError(`--args-json is not valid JSON: ${err.message}`);
    }
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new CliUsageError('--args-json must decode to a JSON object');
    }
    return parsed;
  }

  const args = {};
  for (const pair of argPairs) {
    const eq = pair.indexOf('=');
    if (eq <= 0) throw new CliUsageError(`--arg must be k=v, got "${pair}"`);
    args[pair.slice(0, eq)] = pair.slice(eq + 1);
  }
  return args;
}

function build(argv) {
  const fn = takeValue(argv, '--fn');
  if (!fn) throw new CliUsageError('add-job requires --fn <function>');

  const args = buildArgsObject(argv);

  // Sugar: --profile is CLI-level convenience for args.profile — the wire
  // envelope has no top-level "profile" field (gateway/parse.js's ENQUEUE_KEYS);
  // a launch-agent job reads its named profile OFF the args object
  // (server/heart/heart-store.js `parsedArgs.profile`). DEC-1 R3: still a
  // NAME only, never raw flags.
  const profile = takeValue(argv, '--profile');
  if (profile !== undefined) {
    if ('profile' in args) throw new CliUsageError('--profile conflicts with an explicit profile= in --arg/--args-json — set it once');
    args.profile = profile;
  }

  const trigger = takeValue(argv, '--trigger');
  if (trigger !== 'scheduled' && trigger !== 'periodic') {
    throw new CliUsageError('add-job requires --trigger scheduled|periodic');
  }

  const at = takeValue(argv, '--at');
  const repeat = takeValue(argv, '--repeat');
  const every = takeValue(argv, '--every');
  const sessionMode = takeValue(argv, '--session-mode');
  const dryRun = takeFlag(argv, '--dry-run');

  if (argv.length > 0) {
    throw new CliUsageError(`add-job: unrecognized argument(s): ${argv.join(' ')}`);
  }

  if (trigger === 'scheduled') {
    if (every !== undefined) throw new CliUsageError('--every applies only to --trigger periodic');
    if (!at) throw new CliUsageError('add-job --trigger scheduled requires --at <ISO-8601 UTC datetime>');
  } else {
    if (at !== undefined) throw new CliUsageError('--at applies only to --trigger scheduled (periodic uses --every)');
    if (repeat !== undefined) throw new CliUsageError('--repeat applies only to --trigger scheduled');
    if (!every) throw new CliUsageError('add-job --trigger periodic requires --every <seconds>');
  }

  const payload = { job_id: fn, args, trigger_kind: trigger };
  if (dryRun) payload.dry_run = true;
  if (trigger === 'scheduled') {
    payload.run_at = at;
    if (repeat !== undefined) payload.repeat_rule = repeat;
  } else {
    const intervalSeconds = Number(every);
    if (!Number.isInteger(intervalSeconds) || intervalSeconds <= 0) {
      throw new CliUsageError('--every must be a positive integer number of seconds');
    }
    payload.interval_seconds = intervalSeconds;
    // ⚑ gateway/parse.js requires `run_at` on EVERY enqueue-job call regardless
    // of trigger_kind (it is the row's first-due time; the recurrence fields
    // govern subsequent fires) — gateway-cli-spec.md's CLI Surface table gives
    // periodic no `--at` flag at all, so "start now" is the only sensible
    // default with no invented flag: fixed-width ISO-8601 UTC "now", same
    // formatting server/index.js's own isoNow() uses.
    payload.run_at = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  }
  if (sessionMode !== undefined) payload.session_mode = sessionMode;

  return { intent: 'enqueue-job', payload };
}

async function run(argv, ctx) {
  const { intent, payload } = build(argv);
  const { envelope } = await ctx.call(intent, payload);
  return finish(envelope, {
    json: ctx.json,
    renderSuccess: (result) => {
      if (result.dry_run) console.log('dry-run: VALID — validated, nothing enqueued');
      else console.log(`queued: queue id ${result.jobId}`);
    },
  });
}

module.exports = { HELP, build, run };
