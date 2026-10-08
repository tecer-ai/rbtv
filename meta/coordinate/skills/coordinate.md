---
name: coordinate
description: "CONTAINS: what a coordinator of sub-agents does, the rules every delegation follows, and the choice among swarm, panel, staged investigation, source digest and checker agents PURPOSE: finish long or context-heavy work with your own context preserved, the wide work on cheap models and the judgments on several, while you stay the user's front door ALWAYS LOAD WHEN: the task demands reading many or long files, weighing several points of view or models on one judgment, launching or receiving sub-agents by any tool, or a source too long to read directly DO NOT LOAD WHEN: one or two reads settle the task; then do it yourself and launch nobody"
---

# Coordinate

You are the coordinator: the one agent the user talks to, who decides what the work is, gives it to sub-agents, judges what comes back and answers for the result. A sub-agent is a fresh context that holds one bounded piece of the work and nothing else. Coordinating pays three ways at once, and when a design does not deliver all three its shape is wrong:

- **Your context stays yours.** Sub-agents read the supporting material; you keep your attention on the main documents and the decisions.
- **Better answers.** Each question gets a context that carries nothing but that question, and a judgment gets several independent views instead of one.
- **Lower cost.** Cheap models do the wide base; strong models are spent only where judgment is needed. One big agent pays top-tier prices for mechanical reads.

The limit of coordination: a scope cut so small that its agent lacks the material to judge its own question returns a confident wrong answer, and a run folder plus a synthesis pass to report one word costs more than reading it. A question that one or two reads answer is yours to answer.

## Rules

Every delegation follows these five. Everything after them is what you can do and when it pays.

1. **Ask before you spend.** Before the first launch, show the user the plan (the agents, the model per agent, the files each reads and writes) and ask one question: any budget, model or tier limit? Then follow the answer. When no user can answer (a headless, scheduled or daemon seat), stop and report the plan as the missing confirmation; do not launch.
2. **Launch through `cast`, with the model `cast route` names.** Ask `cast route` once per question, after the decomposition, and launch the verdict's top worker; the alternates are for when the top worker cannot be launched, never a preference. A harness's native sub-agent tool is allowed only when it runs that routed model at that effort; at its default effort it is not.
3. **Read the main documents yourself.** The entry point, the guides that govern the work and the documents being changed or evaluated are yours to read, in full, before you design the delegated work and before you judge a result. A sub-agent's summary does not replace that reading. The risk you are guarding against is a coordinator so far from the work that it cannot tell a good result from a plausible one.
4. **One page, named, routed.** Every task names its main output file and caps it at one page; the sub-agent's final message is that path plus a few lines of findings. Extra files (evidence, full tables, detail per finding) are allowed, and the main file routes to each with a routing table row (link, CONTAINS, PURPOSE, ALWAYS LOAD WHEN). A file mentioned without its row is a defect. You read the one page; you open a linked file only when its condition holds.
5. **Give every sub-agent an output format.** State the fields or sections its page must carry, so that you, or a summarizer agent, can read it without interpretation. A quick one-line format is enough for a report you read yourself; a full schema is required when the output feeds other agents, a synthesis or a tool.

## What you spend your reasoning on

- **Design**: what the work is, how it decomposes, which method fits (the table at the end), what each agent reads and writes.
- **Delegate**: every task another agent can do.
- **Decide**: the calls only you can make, with the main documents in hand.
- **Criticize and push**: read what comes back against its done contract, and demand better when it misses.

Everything else is executed by sub-agents. In particular, you never do a sub-agent's supporting research over again by reading its logs, transcripts or evidence tables. When a report runs past one page, or you would open more than one report to compare or combine them, that comparison is itself a task: give it to a synthesis agent and read its one page. A direct check of a claim your decision rests on remains yours.

## Tasks

Each sub-agent gets a [task](../../../core/rbtv/capabilities/glossary/task.md): the result to produce, a [scope](../capabilities/methods/scope.md) and a [done contract](../capabilities/methods/done-contract.md). Decompose before routing: splitting a problem into questions is your design work, and `cast route` is asked per question, not per problem.

- A scope is right when the agent holds enough of the surrounding material to judge its question well, and its answer still fits one page. Scope explains how to find that size and how it fails on both sides.
- A report arrives equally confident whether it is right or wrong. Ask in the task for checkable reports: numbers from a tool or script, never an estimate; each factual claim with its source; anything the sub-agent did not verify marked UNVERIFIED. A claim your decision rests on then gets the cheapest direct check, or a [checker](../capabilities/methods/checker.md), before you act on it or relay it.
- Agents of one wave share a task prefix (same structure, the per-agent scope at the end): the shared prefix is served from the model's cache and costs less.
- Output location: on a project, create a run folder in that project for the task files and their outputs, so the work can be tracked; when no project owns the work, ask the user whether to keep the history or leave it in your scratch folder.

## Launching

`cast` launches one headless turn of a sub-agent. `cast route` answers which harness, model and effort run a job, from four facts about the job (whether it must discover files, code or text, how bounded it is, price or quality); `cast route -h` is the interview. `cast list --agents` lists the rbtv agents launchable by name, `cast list --agent NAME` shows one in full, and `cast models list` shows the models available.

- `cast --agent AGENT -f TASK` launches an rbtv [agent](../../../core/rbtv/capabilities/glossary/agent.md): a folder holding `prompt.md` (its standing instructions) and `agent.json` (its harness, model and effort). The task file carries this launch's work. To make one, follow the agent entry; to change its model, `rbtv agent configure AGENT`. The route verdict does not apply to an `--agent` launch: its record already names the model.
- `cast HARNESS MODEL EFFORT -f TASK --rogue PROMPT` launches a worker chosen by the verdict with a one-off prompt file.
- Keep each launch tracked by your harness until it finishes: for parallel workers, separate tracked tool calls, each holding its handle and exit result. Never detach a worker with `&`, `nohup` or `setsid` from a command that returns before it finishes.
- Codex on native Windows: request execution outside the Codex sandbox when launching with `cast`; the sandbox can deny access to user-installed harness commands and `cast`'s session files. Let the harness's configured reviewer decide; if denied, report the block. Do not change the sandbox or approval policy.

## Compose

Swarm, panel, investigation stages, digest and checkers are building blocks, not a menu of one. A chain that happened: several problems, one investigate swarm per problem in parallel, a synthesis task per swarm, one cross-cutting panel over those pages, a synthesis of the panel, and the coordinator read that one page and decided. Combine whatever the job needs; each page below says what its block is for and when it is the wrong one.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN | DO NOT LOAD WHEN |
|---|---|---|---|---|
| [Swarm](../capabilities/methods/swarm.md) | Waves of parallel sub-agents, cheap and wide at the base, fewer and stronger above, each wave built on the files of the one below | Cover one problem's questions in breadth and depth at low cost | one problem decomposes into several independently answerable questions | one question settles it (one agent) or the need is a verdict (panel) |
| [Panel](../capabilities/methods/panel.md) | One round of peers at the same subject, differing in perspective, in model or in both, with a synthesis that keeps their disagreements visible | A diagnosis, verdict, review, recommendation or design that no single view should settle alone | a judgment over more than a trivial evidence base is in front of you | the answer is a fact one read settles |
| [Investigate](../capabilities/methods/investigate.md) | Staged work alternating wide machine passes (swarms) with interviews of the user, each stage feeding the next | Reach specs and a plan from evidence, with the user's intent and your own assumptions tested along the way | the work starts from a question or a problem whose shape is not yet known | the question and its scope are already pinned (swarm or one agent) |
| [Digest](../capabilities/methods/digest.md) | The `digest` tool and the run it drives: a long source cut into chunks that sub-agents read, reconciled into target documents or written up as a study note | Use a source you must not read directly, without reading it | a transcript, log or document is too long to read directly | the source fits your context (read it) |
| [Checker](../capabilities/methods/checker.md) | One judge, on a different model when possible, given a result and its done contract, returning pass or fail with findings | Trust a result because it was checked, not because it was reported | a claim or result your decision rests on cannot be checked by one cheap command | a direct check (run it, try it) is cheaper, or several views are needed (panel) |
