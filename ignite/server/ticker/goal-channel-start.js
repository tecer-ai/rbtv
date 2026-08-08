'use strict';

// ── C3 — THE GOAL'S SLACK CHANNEL, CAUSED TO EXIST AT ITS WORKFLOW START ────────────────────────
//
// `ensureChannel`/`registerGoal` have been callable since task 7.58 and had ZERO production
// callers: `goal-channel-cli.js` says so in its own header ("this CLI is the caller … invoked by
// hand instead of by an event"), and r04 confirmed it by grep across the whole module. This file
// is the event. It decides, at the daemon's run-start dispatch, whether THIS goal gets a channel
// and what the invocation is; `ticker.js` performs it.
//
// WHAT COUNTS AS "WORKFLOW START" IS NOT DECIDED HERE. It is `one-live-run.js`'s `isRunStart()` —
// catalogue `action_type === 'start-workflow'` AND homed at a goal — which is already the daemon's
// one definition of a run start (task 7.79: "the scheduled job IS a workflow job"). Importing it
// is the point: a second predicate here would be free to disagree with the gate that decides
// whether the same row may start at all, and then a goal could start a run with no channel or get
// a channel with no run. `r04` read `launchStartWorkflow` in isolation and ruled it a false lead
// because the FUNCTION is a generic job-type executor; the discriminator that makes one of its
// rows a goal's run start lives in `one-live-run.js`, and it is the pair that is the hook.
//
// WHICH KIND GETS ONE — `interactive`, RESOLVED, NOT DECLARED (owner ruling `d-owner-batch1` (2),
// run ruling D9). The kind is read by `seat-folder.js#goalKind()`, the ONE site that turns an
// absent `goal-kind:` into the ruled default. A goal that declares `interactive` and a goal that
// declares nothing are the SAME goal to this file, deliberately: the owner ruled the default
// knowing what it means, and a caller that treated "defaulted" as a weaker `interactive` would be
// re-deciding the ruling one branch down. Non-interactive resolves to NO call — a batch goal has
// no human to address, so a channel for it is an empty room the owner has to archive later.
//
// SKIP IS THE FAIL-SAFE DIRECTION HERE, and it is the OPPOSITE of R9's. R9 queues on ignorance
// because starting a second live run is the damaging act. Here the damaging act is CREATING a
// channel, so an unresolvable workspace root (⇒ no goal folder ⇒ no readable kind) skips rather
// than guesses. Every skip carries a reason and is recorded in the tick log, so "no channel" is
// never inferred from an absence of lines.
//
// RE-ENTRY IS FREE, TWICE OVER. This module holds no state — the same job decides the same way
// every time — and `ensureChannel` itself is idempotent by construction (cached ⇒ `created:false`;
// `name_taken` ⇒ ADOPT the existing channel; `goal-channel-map.js:126-153`). A re-started workflow
// therefore re-ensures and gets the SAME channel back. Nothing here needs a fired-once register,
// and adding one would be a second answer to a question the bridge already answers correctly.
//
// ⚑ THE DAEMON STILL HOLDS NO CHAT CREDENTIAL, and this is the reason the act is an INVOCATION
// rather than a function call. `goal-channel-design.md:25-31` is explicit: the bridge is the ONE
// process that speaks to the chat transport, and "the daemon holds no chat credential and must not
// grow one". The bridge is also a separate OS process that opens no inbound listener, so the
// daemon cannot call into it. What crosses the boundary is a PROCESS: the argv below runs the
// bridge's own operator CLI, and its `SLACK_BOT_TOKEN` arrives from the carrier's EnvironmentFile
// (`ticker.js`, `RBTV_IGNITE_CHAT_ENV_FILE`) — read by systemd, never by this daemon.

const path = require('node:path');
const { isRunStart } = require('./one-live-run');
const { goalKind, goalDirOf } = require('../seat-identity/seat-folder');

// The one kind that gets a channel. Spelled once, and it is a VALUE of `seat-folder.js`'s
// `GOAL_KINDS` enum — not a second enum.
const CHANNEL_KIND = 'interactive';

const ENSURE = 'ensure';
const SKIP = 'skip';

const REASONS = {
  NOT_A_RUN_START: 'not-a-run-start',                     // the ordinary case: most rows are not
  NON_INTERACTIVE: 'non-interactive',                     // the ruled negative arm
  WORKSPACE_UNRESOLVABLE: 'workspace-root-unresolvable',  // no goal folder locatable ⇒ no kind
  DECISION_ERROR: 'decision-error',                       // the rule itself threw — contained
};

// The module root, derived from this file's own location rather than configured: `ignite/` is a
// relocatable subtree (root CLAUDE.md § ignite/), so a path computed from `__dirname` moves with
// it and an env knob would be a second answer that does not.
const IGNITE_SRC = path.resolve(__dirname, '..', '..');
const ENSURE_CLI = path.join('bridges', 'chat', 'goal-channel-cli.js');

// THE INVOCATION. `ensure <goal-id>` is `goal-channel-cli.js`'s own verb and its own idempotence;
// this composes it and adds nothing. `--prefix` is deliberately NOT passed: the prefix is the
// bridge deployment's bound (`config.js`, `channel_prefix`) and a caller that supplied one could
// create a channel outside the namespace the deployment was scoped to.
function composeEnsureArgv({ goal, igniteSrc = IGNITE_SRC, nodeBin = process.execPath }) {
  return [nodeBin, path.join(igniteSrc, ENSURE_CLI), 'ensure', String(goal)];
}

function skip(reason, extra = {}) {
  return { action: SKIP, reason, goal: null, goalDir: null, kind: null, argv: null, ...extra };
}

function decide({ job, resolveRoot, readKind = goalKind, igniteSrc = IGNITE_SRC, nodeBin = process.execPath }) {
  if (!isRunStart(job)) return skip(REASONS.NOT_A_RUN_START);

  const goal = job.goal_name;
  const workspaceRoot = typeof resolveRoot === 'function' ? resolveRoot() : resolveRoot;
  if (!workspaceRoot) return skip(REASONS.WORKSPACE_UNRESOLVABLE, { goal });

  const goalDir = goalDirOf({ workspaceRoot, goal });
  const kind = readKind(goalDir);
  if (kind !== CHANNEL_KIND) return skip(REASONS.NON_INTERACTIVE, { goal, goalDir, kind });

  return {
    action: ENSURE,
    reason: null,
    goal,
    goalDir,
    kind,
    argv: composeEnsureArgv({ goal, igniteSrc, nodeBin }),
  };
}

// ⚠ CONTAINMENT, for the same measured reason `one-live-run.js` carries it: `dispatch()` runs this
// per due row with no try around it, so a throw here would abandon the WHOLE tick — every later
// due row unserved. An internal error therefore SKIPS (never creating a channel on a rule that
// just crashed) and never propagates, and the error message rides the reason so the tick log
// carries it rather than swallowing it.
function channelEnsureDecision(input) {
  try {
    return decide(input || {});
  } catch (err) {
    const goal = (input && input.job && input.job.goal_name) || null;
    return skip(`${REASONS.DECISION_ERROR}: ${err && err.message}`, { goal });
  }
}

module.exports = {
  channelEnsureDecision,
  composeEnsureArgv,
  CHANNEL_KIND,
  ENSURE,
  SKIP,
  REASONS,
  IGNITE_SRC,
  ENSURE_CLI,
};
