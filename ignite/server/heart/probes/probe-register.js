'use strict';

// Task 7.12 — catalogue registration through the store (owner ruling 2026-07-25).
//
// Isolation: a THROWAWAY db under os.tmpdir(), per the convention every heart probe
// follows (probe-enqueue / probe-queue-remove / probe-jobslog). This probe WRITES
// catalogue rows — it must NEVER be pointed at the live store, which a live daemon
// is ticking against.
//
// The capture is truncated at module load, BEFORE any work — a probe that dies at
// start (module-resolution/syntax error) then leaves an EMPTY capture rather than
// the previous run's stale `EXIT: 0` (the D51 evidence-husk hazard). The exit code
// of the process remains the truth; this footer is a hint.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-register.out');
fs.writeFileSync(outPath, '');

const { openHeartStore, closeHeartStore, E_JOB_EXISTS, E_BAD_ARGS } = require('../heart-store');

const tmpDb = path.join(os.tmpdir(), `heart-probe-register-${Date.now()}-${process.pid}.db`);

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// Read back from DISK on a fresh raw node:sqlite connection — never the store's own
// in-memory view. Read-only: a reader can never be a second writer.
function readBackJobs() {
  const raw = new DatabaseSync(tmpDb, { readOnly: true });
  try {
    return raw.prepare('SELECT job_id, action_type, function, args_schema, description, enabled FROM jobs ORDER BY job_id').all();
  } finally {
    raw.close();
  }
}

function refusal(fn) {
  try {
    fn();
    return null;
  } catch (err) {
    return err;
  }
}

try {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  const store = openHeartStore({
    dbPath: tmpDb,
    profiles: { default: { headed: false } },
  });

  // --- 1. A valid registration persists, on disk, with its fields intact.
  const created = store.registerJob({
    jobId: 'launch-worker',
    actionType: 'launch-agent',
    function: 'spawnLaunchAgent',
    argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { prompt: 'string' } }),
    description: 'the probe job',
  });
  const afterFirst = readBackJobs();
  check('a valid registration lands on disk',
    afterFirst.length === 1 && afterFirst[0].job_id === 'launch-worker'
      && afterFirst[0].action_type === 'launch-agent' && afterFirst[0].enabled === 1,
    `rows=${afterFirst.length} row=${JSON.stringify(afterFirst[0])}`);
  check('the registration returns the created row',
    created && created.job_id === 'launch-worker' && created.function === 'spawnLaunchAgent',
    `returned=${JSON.stringify(created)}`);

  // --- 2. CREATE-ONLY: a duplicate id is refused typed, and NOTHING is overwritten.
  //        (Under the retired upsert this call silently replaced every field.)
  const dup = refusal(() => store.registerJob({
    jobId: 'launch-worker',
    actionType: 'send-message',
    function: 'OVERWRITTEN',
    argsSchema: '{}',
  }));
  check('a duplicate job_id is refused with E_JOB_EXISTS',
    dup !== null && dup.code === E_JOB_EXISTS,
    `code=${dup && dup.code}`);
  const afterDup = readBackJobs();
  check('the refused duplicate overwrote nothing',
    afterDup.length === 1 && afterDup[0].function === 'spawnLaunchAgent' && afterDup[0].action_type === 'launch-agent',
    `row=${JSON.stringify(afterDup[0])}`);

  // --- 3. Field-level refusals, each naming the offending field.
  const badAction = refusal(() => store.registerJob({
    jobId: 'x1', actionType: 'not-a-type', function: 'f',
  }));
  check('an unknown action_type is refused with E_BAD_ARGS',
    badAction !== null && badAction.code === E_BAD_ARGS,
    `code=${badAction && badAction.code}`);

  const badFn = refusal(() => store.registerJob({
    jobId: 'x2', actionType: 'launch-agent', function: '',
  }));
  check('an empty function is refused with E_BAD_ARGS',
    badFn !== null && badFn.code === E_BAD_ARGS && badFn.details.field === 'function',
    `code=${badFn && badFn.code} field=${badFn && badFn.details.field}`);

  const badId = refusal(() => store.registerJob({
    jobId: '', actionType: 'launch-agent', function: 'f',
  }));
  check('an empty job_id is refused with E_BAD_ARGS',
    badId !== null && badId.code === E_BAD_ARGS && badId.details.field === 'jobId',
    `code=${badId && badId.code}`);

  const badJson = refusal(() => store.registerJob({
    jobId: 'x3', actionType: 'launch-agent', function: 'f', argsSchema: '{not json',
  }));
  check('a non-JSON args_schema is refused with E_BAD_ARGS',
    badJson !== null && badJson.code === E_BAD_ARGS && badJson.details.field === 'args_schema',
    `code=${badJson && badJson.code}`);

  // The registration-only strictness: every DECLARED type must be a valid primitive.
  // This is the check that stops a bad schema poisoning every future enqueue.
  const badType = refusal(() => store.registerJob({
    jobId: 'x4',
    actionType: 'launch-agent',
    function: 'f',
    argsSchema: JSON.stringify({ required: { profile: 'strnig' } }),
  }));
  check('a schema declaring an unknown type is refused, naming the field',
    badType !== null && badType.code === E_BAD_ARGS && badType.details.field === 'args_schema.required.profile',
    `code=${badType && badType.code} field=${badType && badType.details.field}`);

  // --- 4. Every refusal above wrote NOTHING.
  const afterRefusals = readBackJobs();
  check('no refused registration created a row',
    afterRefusals.length === 1,
    `disk catalogue rows=${afterRefusals.length}`);

  // --- 5. Validate-only mode: full validation, no write.
  const verdict = store.registerJob({
    jobId: 'dry-one', actionType: 'fire-tool', function: 'fire-tool', dryRun: true,
  });
  check('dry-run returns a verdict',
    verdict && verdict.dryRun === true && verdict.valid === true,
    `verdict=${JSON.stringify(verdict)}`);
  check('dry-run wrote nothing',
    readBackJobs().length === 1,
    `disk catalogue rows=${readBackJobs().length}`);

  // The duplicate check runs INSIDE the dry-run — the whole point of validating first.
  const dryDup = refusal(() => store.registerJob({
    jobId: 'launch-worker', actionType: 'launch-agent', function: 'f', dryRun: true,
  }));
  check('dry-run reports a duplicate as E_JOB_EXISTS',
    dryDup !== null && dryDup.code === E_JOB_EXISTS,
    `code=${dryDup && dryDup.code}`);

  // --- 6. A registered job is immediately enqueueable (registration is what the
  //        queue's foreign key demands: no catalogue row, no queue row).
  const row = store.enqueue({
    jobId: 'launch-worker',
    args: JSON.stringify({ profile: 'default' }),
    triggerKind: 'scheduled',
    runAt: new Date(Date.now() + 60000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
    enqueuedBy: 'probe-register',
  });
  check('a freshly registered job is enqueueable',
    row && row.job_id === 'launch-worker',
    `queue row=${row && row.queue_id}`);

  // --- 7. REGRESSION GUARD for the shared-schema extraction: enqueue must keep its
  //        LAZY declared-type behaviour. A bogus type declared for an arg the caller
  //        does not supply has always passed enqueue; the strict check belongs to
  //        registration only. If this flips, certified enqueue behaviour moved.
  const raw = new DatabaseSync(tmpDb);
  raw.prepare(`INSERT INTO jobs (job_id, action_type, function, args_schema, description, enabled, created_at, updated_at)
               VALUES ('legacy-lazy', 'launch-agent', 'f', ?, NULL, 1, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')`)
    .run(JSON.stringify({ required: { profile: 'string' }, optional: { extra: 'strnig' } }));
  raw.close();
  const lazy = refusal(() => store.enqueue({
    jobId: 'legacy-lazy',
    args: JSON.stringify({ profile: 'default' }),
    triggerKind: 'scheduled',
    runAt: new Date(Date.now() + 60000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
    enqueuedBy: 'probe-register',
  }));
  check('enqueue keeps its lazy declared-type check (extraction changed no behaviour)',
    lazy === null,
    lazy ? `unexpected refusal ${lazy.code}` : 'accepted, as before');

  closeHeartStore();

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`REGISTER_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
} catch (err) {
  out('ERROR:', err.message, err.stack);
  out(`EXIT: 1`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
} finally {
  try { closeHeartStore(); } catch {}
  try { fs.unlinkSync(tmpDb); } catch {}
  try { fs.unlinkSync(tmpDb + '-wal'); } catch {}
  try { fs.unlinkSync(tmpDb + '-shm'); } catch {}
}
