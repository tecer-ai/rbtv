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
  const ensureCall = tickerSrc.indexOf('await ensureGoalChannelAtStart(job, actions);');
  const launchCall = tickerSrc.indexOf('await launchStartWorkflow(queueRow, actions, tick, now);');
  check(
    'the start-workflow dispatch branch calls the ensure BEFORE launching the workflow',
    branch > 0 && ensureCall > branch && launchCall > ensureCall,
    `branch@${branch} ensure@${ensureCall} launch@${launchCall}`,
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
