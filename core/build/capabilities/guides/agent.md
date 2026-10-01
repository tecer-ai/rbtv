# Building an agent

An [agent](../glossary/agent.md) is a [prompt](../glossary/prompt.md) given to a model through a [harness](../glossary/harness.md).

## Purpose

It gives one standing prompt, and the cognitive units it selects, a different [task](../glossary/task.md) each time, when no existing agent's purpose covers that prompt. Without it, that work has no prompt that stays the same while the task changes. Where the work belongs instead is in [Choosing what to build](choosing-what-to-build.md); if nothing fails without a new agent, do not build one ([Keep it simple](../principles/kiss.md)).

## What good looks like

- On one matching task, the description's first sentence decides to invoke. The rest names one similar case that must not. The description holds no steps ([Progressive disclosure](../principles/progressive-disclosure.md)).
- One standing purpose. An unrelated second duty is a second agent ([Micro agency](../principles/micro-agency.md)).
- Skills, rules, and commands are named, not pasted. No selected unit's body appears in the prompt ([Single source of truth](../principles/single-source-of-truth.md)).
- Every selected unit already existed or was built because nothing existing covered it. A new unit that duplicates one the installer lists fails ([Keep it simple](../principles/kiss.md)).
- A skill named here is one this agent chooses on some tasks only. Text every task of this agent needs is in the prompt, or is a [rule](../glossary/rule.md) this agent names ([Progressive disclosure](../principles/progressive-disclosure.md)).
- The prompt names no file, goal, or done check that belongs to one task ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Its key folders are the folders its tasks actually work in, so it starts where its work is ([Progressive disclosure](../principles/progressive-disclosure.md)).
- An agent whose [role](role.md), [persona](persona.md), [procedure](procedure.md), and [constraints](constraints.md) match an existing agent is not created ([Keep it simple](../principles/kiss.md)).
- No channel id, absolute path, account, host, or credential is typed into it: these belong to one installation and are read at run time from its configuration, settings, or task ([Single source of truth](../principles/single-source-of-truth.md)).
- Where the agent runs without a person present (through Slack, a timer, or `cast`), the prompt never has it wait after its turn ends: each run is one turn, nothing wakes it with a result, and any check its conclusion depends on runs to completion inside the turn.
- The prompt does not paste memory. Every turn, including a scheduled wake, receives the always-loaded memory from the runtime: the profile, this agent's learned rules, this agent's board, the general-memory index, and the inbox. Workspace memory arrives only when the working directory matches its paths ([Progressive disclosure](../principles/progressive-disclosure.md)).
- The agent keeps the board current. It does not write learned rules or other long-term memory. The dreamer does ([Single source of truth](../principles/single-source-of-truth.md)).
- A scheduled wake starts with no thread. The board holds the check's details. Continuing a subject uses `ignite-agent post --thread`.

## Making it good

Start from the job: name a few concrete tasks the agent will receive and what it must do for each.

Find the cognitive units it needs with the installer's non-interactive discovery commands, `rbtv install list`, `search`, and `show`, and select the ones that fit. Build a new unit only for what nothing listed covers; which kind to build is in [Choosing what to build](choosing-what-to-build.md).

Write the description next, naming the triggers and the near-miss.

Write the prompt only as [role](role.md), with its [persona](persona.md) when needed, [procedure](procedure.md), and [constraints](constraints.md). The agent file holds no capabilities: it reaches knowledge through selected skills and commands, or, when its whole work is one domain, routes to that domain's capabilities. Leave this task's goal, [scope](../../../../meta/sub-agents/capabilities/scope.md), and [done contract](../../../../meta/sub-agents/capabilities/done-contract.md) out; they arrive with each task.

Teach the memory split in the prompt only as a standing limit: maintain the board through the board command, append a fact about the owner with `ignite-agent remember`, and never write learned rules. Do not paste the injected files into the prompt.

## Traps

- The description is missing, too long, or overlaps another agent's, so the wrong agent runs or none does.
- The prompt assumes instructions that arrive only with the caller. A called agent does not receive the caller's standing prompt.
- [Role](role.md), [procedure](procedure.md), and [constraints](constraints.md) give opposite orders, and the agent spends the task reconciling them.
