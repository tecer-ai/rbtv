---
name: sub-agents
description: "Use before launching sub-agents for delegation, a swarm of parallel investigators, or a panel of independent perspectives. Triggers include 'sub-agent', 'sub agents', 'subagent', 'delegate this', 'launch agents', 'parallel agents', 'workers', 'spawn agents', 'swarm', 'panel', 'second opinion', 'multiple perspectives', 'have different models look at this', 'devil's advocate', and 'independent review' — even when a native sub-agent tool is available. For a task settled by one read without launching another agent, this skill is not needed."
---
# Sub-agents

Before launching agents for a broad task with parallel investigation, open the [swarm capability](../capabilities/swarm.md). Before seeking independent judgments on one subject, open the [panel capability](../capabilities/panel.md). The [capabilities index](../capabilities/capabilities.md) names when to open each page.

- Your role is that of a MANAGER, never an executor. You coordinate others' work and verify it, or have some other agent verify it. Your work is to get the right models, to the right agents, to do the right job. You must enforce and ensure it.

- You MUST delegate because it:
  - **Saves your context** — every file a sub-agent reads is a file you did not. A small context is what keeps your judgment sharp.
  - **Better results** — each question gets a fresh, focused context that carries nothing but that question; and a judgment call gets several independent views instead of one.
  - **Saves money** — cheap models do the wide base, strong models are spent only where judgment is needed. `cast route` per question is what makes that split; one big agent pays SOTA prices for mechanical reads.

- Spend your reasoning on **high-leverage work** only:
  - designs — tasks, agents, the shape of the work
  - delegates — every task that another agent can do
  - decides — the calls only the manager can make
  - criticizes and pushes — reviews what comes back and demands better

  Everything else is executed by sub-agents.

- Launching:
  - ALWAYS check `cast route` to define the best agent/model for the desired task before launching. The verdict's top-level worker is THE choice — launch it; the `alternates` list is backup only, for when the first cannot be launched (unavailable harness, no native tool for it). Never pick an alternate because you prefer it. This covers a launch that names harness, model and effort on the command line (`cast <harness> <model> <effort>` with `-p` or `-f`, or `-rogue FILE`). A `-rbtv` launch takes none of them: the verdict does not apply to it.
  - Use the `cast` CLI to launch sub-agents, passing each task with `-p` or `-f` and choosing an rbtv agent with `-rbtv` (it runs on the harness, model and effort in that agent's `agent.json`; cast takes none of them, and to change them run `rbtv agent configure AGENT`) or a rogue agent file with `-rogue` (which takes the harness, model and effort on the command line); use it to see models available, etc. An rbtv agent is a folder holding `agent.md` and `agent.json`; `-rbtv` takes its name (found under `<installation>/.rbtv/agents/`) or its folder path. To make one, follow the [agent guide](../../../core/build/capabilities/guides/agent.md).
  - **Codex agents on native Windows only:** request execution outside the Codex sandbox when launching a sub-agent with `cast`. The sandbox can deny access to user-installed harness commands and `cast`'s session files even when those commands work in another terminal. Use the harness's normal escalation mechanism and let its configured reviewer decide; if denied, report the block. Do not change the sandbox or approval policy, and do not apply this instruction to agents running in other harnesses.
  - If your harness natively allows launching sub-agents, you can use it for such — but only if you first checked `cast route` and you can launch the recommended model through your native sub-agent tool.

- Compose freely: swarm, panel, synthesis tasks are BUILDING BLOCKS, not a menu to pick one item from. Waves of panels, panels over swarm outputs, a synthesis task between any two stages: combine whatever fits the job. Worked chain example (real case):
  1. Several problems → one investigate swarm PER problem, run in parallel; within each swarm, one lane per facet of that problem.
  2. One synthesis task per swarm → one page per problem.
  3. One cross-cutting panel over those pages — 4 lenses, different models.
  4. One synthesis task over the panel.
  5. The manager reads that one page, and decides.

- Staffing:
  - Give each sub-agent a [task](../../../core/build/capabilities/glossary/task.md) with its [scope](../capabilities/scope.md) and [done contract](../capabilities/done-contract.md). For several tasks with dependencies, write a `workflow.md` file following the [workflow guide](../capabilities/workflow.md) and [workflow template](../capabilities/templates/workflow.md). If the tasks run as rbtv agents, write the workflow with the `plan` skill instead (its format carries the Install line for each agent).
  - Give each agent a bounded and small scope: keeps its context optimized (low context usage, better answers).
    - More critical on L2-level models and below; mandatory on L3 (model levels per `cast route -h`: SOTA > L1 > L2 > L3).
    - The small-scope test — a scope is one agent's ONLY when ALL three hold; fail one and it is NOT one agent's scope:
      1. ONE question (or one artifact). The scope asks a single question whose answer does not wait on another question's answer. Two independently-answerable questions are two agents. A PROBLEM (an issue entry, a bug, a feature, "why does X happen") is never one agent's scope — it decomposes into questions, and that decomposition is a wave (`../capabilities/swarm.md`). Example: "why does the session list miss a turn" is a problem; its questions are (a) where the session id is recorded, (b) what the writer stores there, (c) how the reader filters it — three agents, not one.
      2. A NAMED read-set. The task can list the files to read or the commands to run. "Find where X happens, then check it" is two scopes: locating is one agent's; checking is the next wave's, pointed at what the first found.
      3. ONE-PAGE output. The answer fits the output schema in one section. A report that needs a section per sub-finding was several scopes.
    - Too small is also wrong: a question one file read or one command answers is ONE agent — never a wave. Do not build a run folder and a synthesis pass to report one word.
    - Decompose BEFORE routing. Splitting a problem into questions is manager work (design); `cast route` is asked per question, not per problem.
  - Output schema — optional (quick, ~140 chars with the basics of what you want); NOT optional, required, when piping a sub-agent's output as input to other sub-agents, processes, workflows, etc.
  - Always when possible, if launching waves of similar sub-agents, structure their tasks to optimize KV cache.
  - Output location:
    - Working on a specific project → create a folder for your investigation in the most suited location and place all files there (task files, their outputs, etc.) so the result can be tracked.
    - Not clear → ask the user whether to save this history anywhere, or leave it in your scratchpad.
