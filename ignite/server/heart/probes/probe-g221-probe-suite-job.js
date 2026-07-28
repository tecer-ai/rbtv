'use strict';

// probe-g221-probe-suite-job — G-221 (A): the IN-DAEMON arm of the verification trigger.
//
// ⚠⚠ A IS DOGFOODING, NOT COVERAGE (leader bound, #1400). This is the run adopting the feature it
// builds (conduct.md §1). It is NOT redundancy for B (the systemd timer), and B IS NEVER WEAKENED
// BECAUSE A EXISTS: a checker that lives inside the system it checks SHARES ITS FAILURE MODE — if
// the daemon stops, A stops, and A's silence looks exactly like health. Measured the same day:
// `selfheal-watch` and `selfheal-room` were dead 23 hours with nothing reporting it (G-254).
//
// ⚠⚠ WHAT THIS PROBE IS FOR, AND IT IS NOT "DOES THE PERIODIC MECHANISM WORK":
// `registerJob` IS CREATE-ONLY — no update, no unregister surface. So the live registration is a
// ONE-SHOT act on the certified store: whatever id, description and schema it lands with are what
// that id has forever.
//
// ⚠ AN EARLIER VERSION OF THIS HEADER OVERSTATED THE HAZARD AND IS CORRECTED HERE RATHER THAN
// QUIETLY EDITED, because the overstatement flattered this probe. It said a bad schema would BURN
// the id, citing heart-store.js's S-2 note ("registers, reports enabled=1 forever, structurally
// unable to fire"). MEASURED while writing this: registration-time strictness (task 7.12) REFUSES
// both bad shapes AT THE DOOR. My own two wrong guesses — a JSON-Schema-shaped value, and one
// omitting `tool` — were each REFUSED, not burned. The S-2 sentence is true of LEGACY ROWS already
// on the box (which is why `jobFireability` still exists to report them) and false of any
// registration attempted today.
//
// ⇒ SO THE HONEST VALUE OF THIS PROBE IS SMALLER AND STILL REAL: it establishes the exact schema
// that WORKS, and that the tool RESOLVES, before anyone runs an irreversible create-only write on
// the live store — rather than discovering it by being refused at the console during a deploy.
// It does NOT save the id from destruction, because the door already does that.
//
// ⚠ THE CLAIM AT ITS TRUE STRENGTH, and it must not be softened: A IS PROVEN IN ISOLATION ON THIS
// COMMIT AND IS NOT EXERCISED IN PRODUCTION. Registration and the first live fire wait for a human
// deploy (the daemon runs stale code; nobody restarts — G-250). Recorded exactly as G-222 and G-225
// are recorded. An unexercised path must never read as working.
//
// NOT re-proven here, deliberately, because it already has probes: that a periodic queue row fires
// and re-enqueues at all (`probe-periodic.js`), and that the ticker spawns a fire-tool argv
// (`probe-scheduled.js`). Re-asserting them would be a second copy that can drift from the first.
//
// The live store is never opened; every fixture is a throwaway file in tmpdir.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { openHeartStore, closeHeartStore, jobFireability } = require('../heart-store');

const OUT = path.join(__dirname, 'probe-g221-probe-suite-job.out');
const IGNITE_ROOT = path.resolve(__dirname, '..', '..', '..');
const PROFILES_YAML = path.join(IGNITE_ROOT, 'config', 'spawn-profiles.yaml');

const started = new Date();
const lines = [];
const checks = [];

function say(s) {
  lines.push(s);
  console.log(s);
}

function check(name, ok, detail) {
  checks.push({ name, ok: Boolean(ok) });
  say(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

// ⚠ THE SUBJECT OF THIS PROBE. Both values are what the deploy step MUST use verbatim; they are
// declared once, here, and every assertion below reads THESE rather than a retyped copy — a second
// spelling of an irreversible registration is exactly the drift that burns an id.
const JOB_ID = 'probe-suite';
const TOOL_NAME = 'probe-suite';
// ⚠⚠ THIS IS NOT JSON SCHEMA, AND MY FIRST VERSION ASSUMED IT WAS. The store's own format is
// `{required: {name: type}, optional: {name: type}}` (parseArgsSchema, heart-store.js:142) — a
// JSON-Schema-shaped value is REFUSED with "required and optional must be objects". Matched to what
// the live `selfheal-*` fire-tool jobs are actually registered with, read off the store rather than
// invented: {"required":{"tool":"string"},"optional":{"workdir":"string"}}.
//
// ⚠ I FIRST WROTE THAT THIS "PAID FOR ITSELF" BY SAVING THE ID FROM A PERMANENT BURN. THAT WAS
// FALSE and the correction is the more useful note: the guessed schema would have been REFUSED at
// the door, not burned. What the guess actually cost was a failed registration attempt — cheap
// here, and merely annoying at a deploy console. The claim is downgraded rather than deleted
// because inflating the severity of a defect I caught is the same failure as inflating a result.
const ARGS_SCHEMA = JSON.stringify({
  required: { tool: 'string' },
  optional: { workdir: 'string' },
});

function tmpStore(tag) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), `probe-g221-${tag}-`));
  return path.join(dir, 'heart.db');
}

let store = null;
try {
  // ─────────────────────────────────── the tool must EXIST in the shipped config, not in a fixture
  // Read from the real spawn-profiles.yaml. A fixture that supplies its own tools map would prove
  // this probe can build a config, not that the daemon will find the tool (bars.md 10).
  const yamlText = fs.readFileSync(PROFILES_YAML, 'utf8');
  const toolsIdx = yamlText.indexOf('\ntools:');
  const toolsSection = toolsIdx === -1 ? '' : yamlText.slice(toolsIdx);
  const declared = new RegExp(`^\\s{2}${TOOL_NAME}:\\s*$`, 'm').test(toolsSection);
  check(`the shipped config declares the \`${TOOL_NAME}\` tool`, declared, PROFILES_YAML);

  const runnerLine = /deploy\/probe-suite-scheduled\.py/.test(toolsSection);
  check('and its argv points at the SAME runner the systemd arm uses — one implementation, not two',
    runnerLine, 'deploy/probe-suite-scheduled.py');

  const runnerPath = path.join(IGNITE_ROOT, 'deploy', 'probe-suite-scheduled.py');
  check('that runner exists on disk and is executable',
    fs.existsSync(runnerPath) && Boolean(fs.statSync(runnerPath).mode & 0o111),
    runnerPath);

  // ⚠ THE POSITIVE CONTROL RUNS FIRST, and its ORDER is forced rather than chosen: the heart store
  // is a PROCESS SINGLETON ("writer already open in this process"), so the two fixtures cannot be
  // open at once. Running the control first means the real registration below is asserted while
  // nothing else holds the writer — and it means a control failure cannot be mistaken for a
  // teardown artifact of the run it is supposed to bound.
  //
  // Without this control the row below is worth nothing: `jobFireability` returning true for
  // EVERYTHING and returning true FOR THE RIGHT REASON print the same PASS.
  //
  // ⚠⚠ THIS CONTROL CORRECTED THIS PROBE'S OWN PREMISE, and the correction is kept because a
  // successor will read the same stale comment I did. `heart-store.js`'s S-2 note says a bad-schema
  // fire-tool job "registers, reports enabled=1 forever, and is structurally unable to ever fire",
  // and I wrote this control expecting exactly that. MEASURED: `registerJob` now REFUSES it AT THE
  // DOOR (task 7.12 registration-time strictness) — the unfireable job can no longer be created.
  // The S-2 sentence is true of the LEGACY ROWS already on the box, which is why `jobFireability`
  // still exists to report them, and false of any registration attempted today.
  // ⇒ The door is a STRONGER guarantee than the report, so this control asserts the door.
  {
    const trapStore = openHeartStore({ dbPath: tmpStore('trap'), tools: { [TOOL_NAME]: {} } });
    let refused = false;
    let namesThePermanence = false;
    let namesTheMissingArg = false;
    try {
      trapStore.registerJob({
        jobId: 'probe-suite-trap',
        actionType: 'fire-tool',
        function: 'fire-tool',
        argsSchema: '{}',          // the S-2 shape
        description: 'control: the unfireable shape',
      });
    } catch (err) {
      refused = true;
      namesTheMissingArg = /declares no "tool"/.test(err.message || '');
      namesThePermanence = /create-only|no way to repair/.test(err.message || '');
    }
    check('CONTROL: the empty-schema shape is REFUSED AT REGISTRATION — the id cannot be burned today',
      refused && namesTheMissingArg, `refused=${refused}`);
    check('CONTROL: and the refusal states the permanence, so an operator learns it at the door rather than afterwards',
      namesThePermanence);
    closeHeartStore();
  }

  // ───────────────────────────────────────── THE REGISTRATION THE DEPLOY STEP WILL PERFORM, PROVEN
  store = openHeartStore({
    dbPath: tmpStore('register'),
    // Mirrors what the daemon's composition root hands in: the tool must resolve through
    // `config.tools`, which is where enqueue looks (heart-store.js:622).
    tools: { [TOOL_NAME]: { argv: ['/usr/bin/python3', runnerPath] } },
  });

  const job = store.registerJob({
    jobId: JOB_ID,
    actionType: 'fire-tool',
    function: 'fire-tool',
    argsSchema: ARGS_SCHEMA,
    description: 'G-221(A): run the probe suite and refresh its liveness artifact',
  });
  const verdict = jobFireability(job);
  check('THE EXACT REGISTRATION IS FIREABLE — the deploy step will not burn the id',
    verdict.fireable === true, `fireable=${verdict.fireable} reason=${verdict.reason}`);

  // ────────────────────────────────────────────────── the periodic enqueue this job will ride on
  const runAt = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const row = store.enqueue({
    jobId: JOB_ID,
    args: JSON.stringify({ tool: TOOL_NAME }),
    triggerKind: 'periodic',
    runAt,
    intervalSeconds: 3600,
    enqueuedBy: 'probe',
  });
  check('a PERIODIC enqueue of this job is accepted at the interval the systemd arm uses (3600s)',
    Boolean(row) && row.trigger_kind === 'periodic' && row.interval_seconds === 3600,
    `trigger_kind=${row && row.trigger_kind} interval=${row && row.interval_seconds}`);

  // ⚠ CONTROL FOR THE ROW ABOVE: the enqueue path really does resolve the tool against config,
  // so "accepted" means the tool was FOUND — not that the check is absent.
  let unknownRefused = false;
  let refusalNamesTheTool = false;
  try {
    store.enqueue({
      jobId: JOB_ID,
      args: JSON.stringify({ tool: 'probe-suite-does-not-exist' }),
      triggerKind: 'periodic',
      runAt,
      intervalSeconds: 3600,
      enqueuedBy: 'probe',
    });
  } catch (err) {
    unknownRefused = true;
    refusalNamesTheTool = /unknown tool/.test(err.message || '');
  }
  check('CONTROL: an unknown tool is REFUSED — so the acceptance above means the tool RESOLVED',
    unknownRefused && refusalNamesTheTool, `refused=${unknownRefused}`);

  // ──────────────────────────────── the two arms share ONE artifact, and that is the design
  // Whichever arm fired last, a reader looks in one place. Asserted against the runner's source
  // rather than by running it: this probe must stay fast and must not fire a 150-second suite.
  const runnerSrc = fs.readFileSync(runnerPath, 'utf8');
  check('both arms write the SAME liveness artifact — one place to read, whichever fired last',
    /runtime.*probe-suite/.test(runnerSrc) && /latest\.json/.test(runnerSrc));
  check('and the runner still emits its instant and its own staleness budget on EVERY fire',
    /fired_at/.test(runnerSrc) && /stale_after_seconds/.test(runnerSrc) && /interval_seconds/.test(runnerSrc),
    'the leader-bound liveness property (#1373)');
} catch (err) {
  check(`UNCAUGHT: ${err && err.message ? err.message : String(err)}`, false);
} finally {
  try { closeHeartStore(); } catch { /* already closed */ }
  store = null;
}

const failed = checks.filter((c) => !c.ok).length;
say('');
say(`${checks.length} checks, ${failed} failure(s)`);
say(`started ${started.toISOString()} ended ${new Date().toISOString()}`);
// Completeness trailer (G-121): a truncated run reads greener than a complete one.
say('PROBE-COMPLETE');
fs.writeFileSync(OUT, `${lines.join('\n')}\n`, 'utf8');
process.exit(failed ? 1 : 0);
