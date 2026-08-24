---
description: Use when asked to use sub-agents, or when a task you are to perform requires sub-agents.
tags: [sub-agents]
---

# Sub-agents

- Your role is that of a MANAGER, never an executor. You coordinate others' work and verify it, or have some other agent verify it. Your work is to get the right models, to the right agents, to do the right job. You must enforce and ensure it.

- You MUST delegate because it:
  - **Saves your context** — every file a sub-agent reads is a file you did not. A small context is what keeps your judgment sharp.
  - **Better results** — each question gets a fresh, focused context that carries nothing but that question; and a judgment call gets several independent views instead of one.
  - **Saves money** — cheap models do the wide base, strong models are spent only where judgment is needed. `cast route` per question is what makes that split; one big agent pays SOTA prices for mechanical reads.

- Spend your reasoning on **high-leverage work** only:
  - designs — seats, agents, the shape of the work
  - delegates — every task that another agent can do
  - decides — the calls only the manager can make
  - criticizes and pushes — reviews what comes back and demands better

  Everything else is executed by sub-agents.

- Launching:
  - ALWAYS check `cast route` to define the best agent/model for the desired task before launching. The verdict's top-level worker is THE choice — launch it; the `alternates` list is backup only, for when the first cannot be launched (unavailable harness, no native tool for it). Never pick an alternate because you prefer it.
  - Use the `cast` CLI to launch sub-agents (directly or from seats), decide best models, see models available, etc.
  - If your harness natively allows launching sub-agents, you can use it for such — but only if you first checked `cast route` and you can launch the recommended model through your native sub-agent tool.

- Compose freely: swarm, panel, synthesis seats are BUILDING BLOCKS, not a menu to pick one item from. Waves of panels, panels over swarm outputs, a synthesis seat between any two stages: combine whatever fits the job. Worked chain example (real case):
  1. Several problems → one investigate swarm PER problem, run in parallel; within each swarm, one lane per facet of that problem.
  2. One synthesis seat per swarm → one page per problem.
  3. One cross-cutting panel over those pages — 4 lenses, different models.
  4. One synthesis seat over the panel.
  5. The manager reads that one page, and decides.

- Staffing:
  - Treat each sub-agent as a seat, and create its files as such. How to create a seat: `component.md` § "seat.md descriptor behavior" (this component's root).
  - Give each agent a bounded and small scope: keeps its context optimized (low context usage, better answers).
    - More critical on L2-level models and below; mandatory on L3 and L4 (model levels per `cast -h`: SOTA > L1 > L2 > L3 > L4).
    - The small-scope test — a scope is one agent's ONLY when ALL three hold; fail one and it is NOT one agent's scope:
      1. ONE question (or one artifact). The scope asks a single question whose answer does not wait on another question's answer. Two independently-answerable questions are two agents. A PROBLEM (an issue entry, a bug, a feature, "why does X happen") is never one agent's scope — it decomposes into questions, and that decomposition is a wave (`swarm.md`). Example: "why does the leader respawn forever" is a problem; its questions are (a) where the cursor value is written, (b) what the writer stores there, (c) how the reader parses it — three agents, not one.
      2. A NAMED read-set. The prompt can list the files to read or the commands to run. "Find where X happens, then check it" is two scopes: locating is one agent's; checking is the next wave's, pointed at what the first found.
      3. ONE-PAGE output. The answer fits the output schema in one section. A report that needs a section per sub-finding was several scopes.
    - Too small is also wrong: a question one file read or one command answers is ONE agent — never a wave. Do not build a run folder and a synthesis pass to report one word.
    - Decompose BEFORE routing. Splitting a problem into questions is manager work (design); `cast route` is asked per question, not per problem.
  - Output schema — optional (quick, ~140 chars with the basics of what you want); NOT optional, required, when piping a sub-agent's output as input to other sub-agents, processes, workflows, etc.
  - Always when possible, if launching waves of similar sub-agents, structure their seats to optimize KV cache.
  - Output location:
    - Working on a specific project → create a folder for your investigation in the most suited location and place all files there (seats of sub-agents, their outputs, etc.) so the result can be tracked.
    - Not clear → ask the user whether to save this history anywhere, or leave it in your scratchpad.
