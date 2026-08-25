'use strict';

// C3 — the caller that causes an interactive goal's Slack channel to exist at its workflow start.
//
// Isolation: a throwaway workspace under os.tmpdir() holding real `.rbtv/goals/test-c3-*/goal.md`
// descriptors. Nothing here touches a real `.rbtv/`, and — by construction — nothing here can
// create a Slack channel: the decision layer under test COMPOSES an invocation and returns it. No
// process is spawned, so the CLI that holds the credential is never reached. That boundary is the
// point: everything up to the argv is proven here, and the argv itself is asserted BYTE-EXACT.
//
// ⚠ WHAT THIS PROBE IS FOR, and why half its checks are controls. Two wrong callers pass every
// naive version of this file: one that ENSURES FOR EVERYTHING (it satisfies both positive arms and
// never reads a descriptor) and one that ENSURES FOR NOTHING (it satisfies the negative arm and
// the not-a-run-start arms). So every arm here is paired with the mutant that would break it:
// `readKind` is swapped for a reader that ignores the descriptor, in BOTH directions, and each
// mutant must flip the arm it is aimed at. An arm no mutant can flip is not measuring the rule.
//
// ⚠ AND ONE CHECK READS THE LIVE `ticker.js`. A perfect decision module wired nowhere is exactly
// the state task C3 exists to end — `ensureChannel` was already correct and already callable, and
// had no caller for eleven days. So the last check asserts the branch: the daemon's start-workflow
// dispatch calls the ensure, and calls it BEFORE the workflow launches.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const outPath = path.join(__dirname, 'probe-goal-channel-start.out');
fs.writeFileSync(outPath, '');

const {
  channelEnsureDecision,
  composeEnsureArgv,
  REASONS,
  IGNITE_SRC,
  ENSURE_CLI,
} = require('../goal-channel-start');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-goal-channel-start-'));

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// A real goal folder at the real layout position, written to disk. The decision under test is
// given only the goal's NAME and the workspace root — it must find this file itself, which is what
// makes the read an integration rather than a hand-fed value.
function makeGoal(goal, frontmatter) {
  const dir = path.join(root, '.rbtv', 'goals', goal);
  fs.mkdirSync(dir, { recursive: true });
  if (frontmatter !== null) {
    fs.writeFileSync(path.join(dir, 'goal.md'), `${frontmatter}\n\nthe goal contract body\n`);
  }
  return dir;
}

// The catalogue row shape the daemon reads: `isRunStart` keys on these two columns only.
function runStartJob(goal) {
  return { job_id: `start-${goal}`, action_type: 'start-workflow', goal_name: goal };
}

const DECLARED = 'test-c3-declared-interactive';
const DEFAULTED = 'test-c3-defaulted';
const BATCH = 'test-c3-non-interactive';

try {
  const declaredDir = makeGoal(DECLARED, '---\nname: test-c3-declared-interactive\ngoal-kind: interactive\n---');
  const defaultedDir = makeGoal(DEFAULTED, '---\nname: test-c3-defaulted\n---');
  const batchDir = makeGoal(BATCH, '---\nname: test-c3-non-interactive\ngoal-kind: non-interactive\n---');

  const decide = (job, extra = {}) => channelEnsureDecision({ job, resolveRoot: root, ...extra });

  // ── the two positive arms — D9: declared and defaulted are the SAME goal to this caller ───────
  const declared = decide(runStartJob(DECLARED));
  check('a DECLARED interactive goal ensures', declared.action === 'ensure', `action=${declared.action}`);
  const defaulted = decide(runStartJob(DEFAULTED));
  check(
    'a goal declaring NO kind ensures too (D9 — the resolved kind, not the declared one)',
    defaulted.action === 'ensure' && defaulted.kind === 'interactive',
    `action=${defaulted.action} kind=${defaulted.kind}`,
  );

  // ── the negative arm ──────────────────────────────────────────────────────────────────────────
  const batch = decide(runStartJob(BATCH));
  check(
    'a non-interactive goal does NOT ensure, and composes no invocation',
    batch.action === 'skip' && batch.reason === REASONS.NON_INTERACTIVE && batch.argv === null,
    `action=${batch.action} reason=${batch.reason} argv=${JSON.stringify(batch.argv)}`,
  );

  // ── CONTROLS. Each mutant ignores the descriptor and answers one fixed kind. ──────────────────
  const alwaysInteractive = () => 'interactive';
  const alwaysBatch = () => 'non-interactive';
  const mutantOnBatch = decide(runStartJob(BATCH), { readKind: alwaysInteractive });
  check(
    'CONTROL: a readKind that ignores the descriptor FLIPS the non-interactive arm to ensure',
    mutantOnBatch.action === 'ensure',
    'so the skip above came from the descriptor, not from a caller that skips everything',
  );
  const mutantOnDeclared = decide(runStartJob(DECLARED), { readKind: alwaysBatch });
  check(
    'CONTROL: a readKind answering non-interactive FLIPS the interactive arm to skip',
    mutantOnDeclared.action === 'skip' && mutantOnDeclared.reason === REASONS.NON_INTERACTIVE,
    'so the ensure above came from the descriptor, not from a caller that ensures everything',
  );

  // ── rows that are NOT a workflow start. Each must be silent, or every goal gets a channel per
  //    watcher tick — and the discriminator is one shared with the one-live-run gate. ────────────
  const fireTool = decide({ job_id: 'watcher', action_type: 'fire-tool', goal_name: DECLARED });
  check(
    'a fire-tool row homed at the SAME interactive goal does NOT ensure',
    fireTool.action === 'skip' && fireTool.reason === REASONS.NOT_A_RUN_START,
    `reason=${fireTool.reason}`,
  );
  const homeless = decide({ job_id: 'wf', action_type: 'start-workflow', goal_name: null });
  check(
    'a start-workflow row homed at NO goal does NOT ensure',
    homeless.action === 'skip' && homeless.reason === REASONS.NOT_A_RUN_START,
    `reason=${homeless.reason}`,
  );

  // ── ignorance skips (the fail-safe direction here is NOT R9's) ────────────────────────────────
  const noRoot = channelEnsureDecision({ job: runStartJob(DECLARED), resolveRoot: () => null });
  check(
    'an unresolvable workspace root SKIPS rather than guessing a goal folder',
    noRoot.action === 'skip' && noRoot.reason === REASONS.WORKSPACE_UNRESOLVABLE && noRoot.argv === null,
    `reason=${noRoot.reason}`,
  );
  const thrower = decide(runStartJob(DECLARED), {
    readKind: () => { throw new Error('descriptor read exploded'); },
  });
  check(
    'a throw inside the rule is CONTAINED as a skip and never propagates (a throw would kill the tick)',
    thrower.action === 'skip' && String(thrower.reason).startsWith(REASONS.DECISION_ERROR),
    `reason=${thrower.reason}`,
  );

  // ── the goal folder is found at the REAL layout position ──────────────────────────────────────
  check(
    'the resolved goalDir is where the fixture was actually written',
    declared.goalDir === declaredDir && fs.existsSync(path.join(declared.goalDir, 'goal.md')),
    declared.goalDir,
  );
  check(
    'the non-interactive fixture is reported at its own folder too',
    batch.goalDir === batchDir,
    batch.goalDir,
  );
  check(
    'the defaulted fixture resolves its own folder',
    defaulted.goalDir === defaultedDir,
    defaulted.goalDir,
  );

  // ── the invocation, byte-exact, and pointing at a file that exists ────────────────────────────
  const expected = [process.execPath, path.join(IGNITE_SRC, ENSURE_CLI), 'ensure', DECLARED];
  check(
    'the composed argv is exactly `<node> <ignite>/bridges/chat/goal-channel-cli.js ensure <goal>`',
    JSON.stringify(declared.argv) === JSON.stringify(expected),
    JSON.stringify(declared.argv),
  );
  check(
    'the argv names a CLI that exists on disk (a moved/renamed CLI is caught here, not at 3am)',
    fs.existsSync(declared.argv[1]),
    declared.argv[1],
  );
  check(
    'no --prefix is passed — the channel namespace is the bridge deployment\'s bound, not the caller\'s',
    !declared.argv.includes('--prefix'),
  );
  check(
    'composeEnsureArgv agrees with the decision (one composer, not two)',
    JSON.stringify(composeEnsureArgv({ goal: DECLARED })) === JSON.stringify(declared.argv),
  );

  // ── re-entry: a re-started workflow must not double-fire destructively ────────────────────────
  const again = decide(runStartJob(DECLARED));
  check(
    're-entry returns an identical decision — the caller holds no fired-once state',
    JSON.stringify(again) === JSON.stringify(declared),
    'idempotence on the far side is ensureChannel\'s (cached / name_taken -> ADOPT)',
  );

  // ── THE WIRE. A correct decision module wired nowhere is the state C3 exists to end. ──────────
  const tickerSrc = fs.readFileSync(path.resolve(__dirname, '..', 'ticker.js'), 'utf8');
  check(
    'ticker.js requires the decision module',
    /require\('\.\/goal-channel-start'\)/.test(tickerSrc),
  );
  const branch = tickerSrc.indexOf("job.action_type === 'start-workflow'");
  const ensureCall = tickerSrc.indexOf('await ensureGoalChannel({ job }, actions);');
  const launchCall = tickerSrc.indexOf('await launchStartWorkflow(queueRow, actions, tick, now);');
  check(
    'the start-workflow dispatch branch calls the ensure BEFORE launching the workflow',
    branch > 0 && ensureCall > branch && launchCall > ensureCall,
    `branch@${branch} ensure@${ensureCall} launch@${launchCall}`,
  );

  // ── THE REAL READER ON A HOSTILE DESCRIPTOR (A3/C3 review, 2026-08-08) ───────────────────────
  //
  // The throw arm above injects a `readKind` that throws — it proves the try/catch, not the seam.
  // At TICK TIME the reader is `seat-folder.js#goalKind` and the descriptor is whatever is on
  // disk, so these arms drive the REAL reader through the shapes a broken goal.md actually takes.
  // None may throw (a throw out of `dispatch()` abandons the whole tick) and each must return a
  // decision.
  const hostileShapes = [
    ['unterminated frontmatter', '---\nname: x\ngoal-kind: non-interactive\n'],
    ['no frontmatter at all', '# just a heading'],
    ['a value outside the enum', '---\ngoal-kind: interctive\n---'],
    ['an empty goal.md', ''],
  ];
  let hostileFault = null;
  hostileShapes.forEach(([label, body], i) => {
    const g = `test-c3-hostile-${i}`;
    makeGoal(g, body);
    try {
      const d = decide(runStartJob(g));
      if (!['ensure', 'skip'].includes(d.action)) hostileFault = `${label} -> action ${d.action}`;
    } catch (err) {
      hostileFault = `${label} THREW ${err.message}`;
    }
  });
  check(
    `${hostileShapes.length} malformed descriptors each yield a decision through the REAL goalKind, none throws`,
    hostileFault === null,
    hostileFault || 'a throw here abandons every later due row in the tick',
  );
  // A goal folder that does not exist at all: the reader defaults, so this ENSURES. That is the
  // ruling working as ruled — recorded here so the behaviour is a decision on the record rather
  // than a surprise the first time a queue row outlives its goal folder.
  const orphan = decide(runStartJob('test-c3-no-such-goal'));
  check(
    'a run-start row whose goal folder is ABSENT still ensures (the ruled default, documented not accidental)',
    orphan.action === 'ensure' && orphan.kind === 'interactive',
    `action=${orphan.action} kind=${orphan.kind}`,
  );

  // ── THE CARRIER INVARIANT THE TICKER'S SKIP RESTS ON ─────────────────────────────────────────
  //
  // `ticker.js` refuses to launch the ensure on any carrier but systemd, because the chat
  // credential reaches the child ONLY as systemd's `EnvironmentFile=` property and `spawnSetsid`
  // has no such parameter — its child inherits the daemon's env, which by design holds no token,
  // so a setsid launch is a guaranteed failure recorded as a success. That refusal is only correct
  // while the invariant holds. If someone later teaches `spawnSetsid` to carry an env file, this
  // arm goes RED and points at the skip that must then be revisited (and at
  // `goal-channel-design.md`'s bound, which such a change would also have to answer).
  const carrierSrc = fs.readFileSync(path.resolve(__dirname, '..', '..', 'spawn', 'carrier.js'), 'utf8');
  const setsidSig = /function spawnSetsid\(\{([^}]*)\}/.exec(carrierSrc);
  check(
    'spawnSetsid still accepts NO envFile — the invariant the ticker\'s non-systemd skip rests on',
    !!setsidSig && !/envFile/.test(setsidSig[1]),
    setsidSig ? setsidSig[1].replace(/\s+/g, ' ').trim() : 'signature not found',
  );
  const tickerSrcCarrier = fs.readFileSync(path.resolve(__dirname, '..', 'ticker.js'), 'utf8');
  check(
    'ticker.js skips the ensure when the selected carrier is not systemd',
    /carrier !== 'systemd'/.test(tickerSrcCarrier) && /carrier-cannot-carry-credential/.test(tickerSrcCarrier),
  );

  // ── CONTAINMENT COVERS THE PREPARATION, NOT ONLY THE FORK ────────────────────────────────────
  //
  // `selectCarrier` THROWS when `spawn.carrier: systemd` is configured on a box with no user
  // manager, and `ensureLogPath`/`ensureExitFile` mkdir. `tick()` has a `finally` and no `catch`,
  // so any of those escaping abandons the rest of the tick. All three must sit INSIDE the
  // function's try.
  const fnStart = tickerSrcCarrier.indexOf('async function ensureGoalChannel(subject');
  const fnEnd = tickerSrcCarrier.indexOf('async function launchStartWorkflow', fnStart);
  const body = tickerSrcCarrier.slice(fnStart, fnEnd);
  const tryAt = body.indexOf('try {');
  check(
    'selectCarrier / ensureLogPath / ensureExitFile all sit INSIDE ensureGoalChannel\'s try',
    fnStart > 0 && fnEnd > fnStart && tryAt > 0
      && ['selectCarrier(', 'ensureLogPath(', 'ensureExitFile('].every((c) => body.indexOf(c) > tryAt),
    `try@${tryAt} selectCarrier@${body.indexOf('selectCarrier(')} ensureLogPath@${body.indexOf('ensureLogPath(')} ensureExitFile@${body.indexOf('ensureExitFile(')}`,
  );

  // ── TASK 7.789 · THE SECOND CALLER — THE DAEMON LANE ─────────────────────────────────────────
  //
  // A goal reaches its run start on two lanes. Only the QUEUED one was wired, so a daemon-lane
  // goal got no channel at all (measured: `forge-reference-seat-id-naming`, 2026-08-11, zero
  // `goal-channel-cli` lines across its whole seeding). These arms prove the second entry exists,
  // decides IDENTICALLY to the first, and is reached from `lane-watch.js` exactly once per goal.

  // 1. THE ENTRY. A goal NAME with no job is a first-class subject.
  const byName = channelEnsureDecision({ goal: DECLARED, resolveRoot: root });
  check(
    'the daemon-lane entry — a bare goal NAME, no catalogue row — decides `ensure`',
    byName.action === 'ensure' && byName.goal === DECLARED,
    `action=${byName.action} goal=${byName.goal}`,
  );

  // 2. ONE DECISION, NOT TWO. The discriminating claim: the two entries must be BYTE-IDENTICAL for
  // the same goal. A second copy of the rule is free to drift, and the drift is invisible — one
  // lane creating channels the other skips looks like nothing at all.
  check(
    'the two entries return the SAME decision for the same goal — one rule, not two copies',
    JSON.stringify(byName) === JSON.stringify(declared),
    `job-entry=${JSON.stringify(declared.argv)} goal-entry=${JSON.stringify(byName.argv)}`,
  );

  // 3. THE NEGATIVE ARM SURVIVES THE NEW ENTRY. A `goal` entry that skipped `isRunStart` AND the
  // kind read would ensure for everything — the "ensures for everything" wrong caller, arriving by
  // a new door. The kind rule must still bind on this side.
  const byNameBatch = channelEnsureDecision({ goal: BATCH, resolveRoot: root });
  check(
    'the daemon-lane entry still refuses a non-interactive goal, and composes no invocation',
    byNameBatch.action === 'skip' && byNameBatch.reason === REASONS.NON_INTERACTIVE && byNameBatch.argv === null,
    `action=${byNameBatch.action} reason=${byNameBatch.reason}`,
  );

  // 4. THE ROW GATE IS NOT WEAKENED FOR THE JOB ENTRY. Adding a second door must not open the
  // first one wider: a job that is not a run start still skips, and a call carrying NEITHER
  // subject skips rather than throwing (this module may never abandon its caller's pass).
  const notAStart = channelEnsureDecision({ job: { job_id: 'x', action_type: 'launch-agent', goal_name: DECLARED }, resolveRoot: root });
  const noSubject = channelEnsureDecision({ resolveRoot: root });
  check(
    'the job entry keeps its isRunStart gate, and a subject-less call SKIPS instead of throwing',
    notAStart.reason === REASONS.NOT_A_RUN_START && noSubject.reason === REASONS.NO_SUBJECT,
    `notAStart=${notAStart.reason} noSubject=${noSubject.reason}`,
  );

  // 5. THE WIRE, on the same terms the queued branch's wire is asserted: the performer is exposed
  // by the ticker and reached by the lane watch. A decision module with a second entry and no
  // second caller is the exact state this task exists to end.
  const laneSrc = fs.readFileSync(path.resolve(__dirname, '..', '..', '..', 'supervisor', 'lane-watch.js'), 'utf8');
  check(
    'ticker.js EXPOSES the performer so the engine lane can reach it',
    /return \{ tick, getTickNumber, nudge, stop, ensureGoalChannel \};/.test(tickerSrc),
  );
  check(
    'lane-watch.js reaches the performer through engine.ticker.ensureGoalChannel',
    /engine\.ticker\.ensureGoalChannel/.test(laneSrc) && /perform\(\{ goal \}\)/.test(laneSrc),
  );
  const adoptAt = laneSrc.indexOf('adopted.push(pickup);');
  const ensureAt = laneSrc.indexOf('ensureGoalChannelOnce({ goal, goalFolder, engine, say });');
  check(
    'the ensure fires AFTER the goal is adopted — a goal whose seeding refused gets no channel',
    adoptAt > 0 && ensureAt > adoptAt,
    `adopt@${adoptAt} ensure@${ensureAt}`,
  );

  // 6. ONCE PER GOAL, NOT ONCE PER TICK — driven, not grepped. `runLaneWatch` re-adopts an
  // assigned goal EVERY cadence; a per-tick ensure would fork ~8,600 systemd units a day per goal.
  // The real `ensureGoalChannelOnce` is called three times for one goal against a spying performer.
  const laneWatch = require('../../../supervisor/lane-watch');
  const calls = [];
  const spyEngine = { ticker: { ensureGoalChannel: (subject) => { calls.push(subject); return []; } } };
  const dedupeFolder = path.join(root, '.rbtv', 'goals', DECLARED);
  const fired = [0, 1, 2].map(() => laneWatch.ensureGoalChannelOnce({
    goal: DECLARED, goalFolder: dedupeFolder, engine: spyEngine, say: () => {},
  }));
  check(
    'three passes over one adopted goal perform the ensure exactly ONCE',
    calls.length === 1 && calls[0].goal === DECLARED && JSON.stringify(fired) === '[true,false,false]',
    `calls=${calls.length} fired=${JSON.stringify(fired)}`,
  );
  // THE CONTROL for the arm above: a memo that never fires is also `calls.length <= 1`. A SECOND
  // goal must still get its own ensure, or the check above would pass over a dead call site.
  laneWatch.ensureGoalChannelOnce({
    goal: BATCH, goalFolder: path.join(root, '.rbtv', 'goals', BATCH), engine: spyEngine, say: () => {},
  });
  check(
    'CONTROL — the memo is per GOAL, not a global fired-once: a second goal still ensures',
    calls.length === 2 && calls[1].goal === BATCH,
    `calls=${JSON.stringify(calls)}`,
  );
  // 7. THE ATTACHED LANE MUST NOT ENSURE, and that is TWO independent claims because either alone
  // would mislead. (a) CONTAINMENT BY REACHABILITY — `rbtv run` never runs this pass at all: the
  // lane watch is the DAEMON's goal pickup and `attached-execution.js` calls `seedGoal` directly.
  // That is the claim that actually holds today, and the real attached engine DOES publish a
  // `ticker`, so the guard below is not what protects it. (b) THE GUARD — an engine object with no
  // ticker surface (a probe's, a future embedder's) no-ops silently rather than throwing.
  const attachedSrc = fs.readFileSync(path.resolve(__dirname, '..', '..', '..', 'operator', 'attached-execution.js'), 'utf8');
  check(
    'the ATTACHED lane never reaches this pass — no runLaneWatch, no ensureGoalChannelOnce in it',
    !/runLaneWatch|ensureGoalChannelOnce/.test(attachedSrc),
  );
  const beforeAttached = calls.length;
  const guardFired = laneWatch.ensureGoalChannelOnce({
    goal: 'test-c3-no-ticker', goalFolder: path.join(root, '.rbtv', 'goals', 'test-c3-no-ticker'),
    engine: { seedGoal: () => {} }, say: () => { throw new Error('the guarded path said something'); },
  });
  check(
    'an engine with NO ticker surface ensures nothing, silently, and does not throw',
    guardFired === false && calls.length === beforeAttached,
  );

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`SUMMARY: ${checks.length - failed.length}/${checks.length} passed`);
  out('BOUNDARY: no process spawned, no Slack call made — the invocation is composed and asserted, never run');
  out(failed.length ? 'VERDICT: FAIL' : 'VERDICT: PASS');
  process.exitCode = failed.length ? 1 : 0;
} catch (err) {
  out(`ERROR: ${err && err.stack ? err.stack : err}`);
  out('VERDICT: FAIL');
  process.exitCode = 1;
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}
