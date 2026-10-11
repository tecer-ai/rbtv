# cast decisions

Standing decisions about cast. Each states the decision and its reason; the pages of `capabilities/` describe the resulting design.

## A launch falls back only on a failure to start

A launch runs a fallback when the harness cannot be started or exits with a failure in its first 15 seconds, and in no other case. Reason: a later failure can follow work the agent already did, and running the task again on another model would repeat or collide with that work. The 15 seconds are a bound on "no work yet", taken from measured start failures of 2.4 to 4 seconds; a harness that retries a provider limit for longer than that ends as an ordinary failure.

## A stalled job is never relaunched

`cast monitor` reports a job that is alive without progress, and nothing kills or relaunches a job on that report. Reason: the monitor's stall verdict has been wrong on a healthy job, and a fallback on a stall would need to kill the first run.

## A job's first verdict never reports a freeze

The first time `cast monitor` judges a job, it has watched the job's processes for 1.2 seconds only, and a job that shows no life in that time reads `SUSPECT`, never `STALLED` or `NO-SIGNAL`. A one-shot roster therefore never shows those two states, and `cast monitor --watch` reports a frozen job on its second poll of that job at the earliest. Reason: a read of one instant or of 1.2 seconds has been wrong on healthy jobs, which stay quiet for longer while they wait on a reply or a sleeping child, and a wrong "frozen" has cost a killed job. `provider-limit` and `DEADLINE` are reported on the first verdict, because neither rests on that read.

## The fallback is chosen from the model catalog, not named per model or per agent

A launch finds its fallback by ranking the other models of the failed model's level, the way `cast route` ranks. Reason: a column or an agent field that names one stand-in per model is a second table to fill and to keep valid each time a model is replaced, and the model catalog already holds what the choice needs.

## A fallback stays inside its level, and may try the same provider

A launch tries every candidate of the level in ranking order, including models of the provider that just failed, and stops when the level is used up; it names the best model of the next level down and does not launch it. Reason: a model of a lower level is a silent drop in quality, which the owner decides, and trying a model whose provider is down costs a few seconds while a rule that skips providers would also skip a model that works.

## Fallback is off until an installation turns it on

`fallback` in the installation's defaults is `off` unless set. Reason: a fallback launches models on other providers' plans, and an installation that never asked for that must not start spending them.

## A fallback ranks quality on both scores added

Reason: a launch does not say whether its task is code or text, so the stand-in has to be good at both.

## An installation decides the two overrides and which models are selected; rbtv proposes the rest

`cast models update` copies level, scores, cost, effort count and image flag from the shipped model catalog and never changes an override or which models are selected. The shipped model catalog leaves both override cells blank for every model. Reason: the first group describes the model and changes when the model does; an override is one installation's favorite, and a favorite shipped by rbtv would win a level in every installation that never chose it.

## A selected model is eligible; no column takes it out of routing

Every row of the model catalog in force competes for `cast route` verdicts, fallbacks and panel seats, subject to its login, its level and what it can do. The model catalog has no `use` column, and a file that still names one is refused as a file with an unknown column. Reason: selection already says which models an installation wants, and a second switch on each row gave two places to look for why a model was never named. A model that must not be routed is unselected.

## An image model has no level and no score

An image-generation model's row carries `image=Y` and blank `level`, `reasoning` and `coding`; `cast route --caps image` selects it, and no class, fallback or panel does, whatever its other cells hold. Reason: the levels and scores rank text and code work, and a level or a zero written for an image model put a number into rankings it has no place in.

## The shipped model catalog lists pinned versions and list prices

One row per model line names a pinned version, never a moving alias such as a `-latest` name. `cost` is the provider's standard API list price for output tokens at its base rate; a cost that is not known is blank, never a placeholder number. Reason: an alias changes what a row launches with no change to the row, and a placeholder cost ranks as a real price.

## An agent launch loads only the agent folder

A launch of an rbtv agent passes its harness the arguments and environment variables that stop it loading anything from a folder above the agent folder, and turn its native memory off. A launch that names no agent passes none. Reason: an agent's behaviour must come from its own folder, wherever that folder sits, while a worker launched into a folder is meant to receive that folder's surroundings. The launcher holds the agent folder and passes it; it is never read from `RBTV_AGENT_HOME`, and a launch never reads it from the working folder, because a worker launched into an agent folder is not that agent. `cast resume` has no agent to be told about, so it alone reads its launch folder and isolates when that folder is an agent folder: a session that ran there was the agent's. For the same reason it passes the model and effort of that folder's agent record when the record names the resumed harness: an agent's model is what its record says, never the harness's default or the account folder's.

## An agent receives nothing from the harness's account folder except the login

The launch passes each harness what stops the content of its account folder: on Claude Code `--setting-sources project,local`, the account folder's instruction file and rules in the exclusion list, and `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1`; on Codex `--disable plugins`, `-c skills.bundled.enabled=false` and `--ignore-user-config`; on OpenCode `OPENCODE_DISABLE_CLAUDE_CODE=1`, and nothing of the user's home is handed back. Reason: owner decision, 2026-10-11. The owner defines what an agent has by what rbtv ships to its folder, and the harness adds nothing by itself. Not covered, because no argument or variable does it without moving the account folder: an account `AGENTS.md`, account skills and account hooks on Codex, `config.toml` on a headed Codex launch, whose interactive form refuses `--ignore-user-config`, and the content of `~/.config/opencode/` on OpenCode. [Agent isolation](capabilities/tools/cast/documentation/agent-isolation.md) lists them.

## One function holds every harness's isolation values

`lib/isolation.js` is the only place that knows them, and cast's launch, `cast resume` and Ignite's turn call it. Reason: Ignite composes its own command line, so values kept in cast's launch alone would leave every Ignite turn unisolated, and two copies would drift.

## A Claude Code agent has only the MCP servers of its own folder

The launch passes `--strict-mcp-config`, and `--mcp-config` with the agent folder's `.mcp.json` only when that file exists. Reason: owner decision, 2026-10-11. What an agent has is what rbtv installed in its folder, so no MCP server reaches it from a parent folder, from the user's home-level configuration or from the account. The file is named only when it exists because Claude Code refuses to start on a missing one.

## Claude Code's memory is turned off by a setting, not by a variable

Reason: an environment variable is inherited by every program the agent runs, and a setting passed as an argument is not. The skills bundled in Claude Code are turned off by a variable because nothing else turns them off together.

## Every launch removes the isolation variables it inherited

Reason: OpenCode is isolated by environment variables only, and Claude Code's bundled skills by one, so a launch made by an isolated agent would otherwise configure its own harness with that agent's folder and values. The removal applies to an agent launch too, before its own values are set, so one rule covers every launch.
