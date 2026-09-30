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

## Making it good

Start from the job: name a few concrete tasks the agent will receive and what it must do for each.

Find the cognitive units it needs with the installer's non-interactive discovery commands, `rbtv install list`, `search`, and `show`, and select the ones that fit. Build a new unit only for what nothing listed covers; which kind to build is in [Choosing what to build](choosing-what-to-build.md).

Write the description next, naming the triggers and the near-miss.

Write the prompt only as [role](role.md), with its [persona](persona.md) when needed, [procedure](procedure.md), and [constraints](constraints.md). Leave this task's goal, [scope](scope.md), and [done contract](done-contract.md) out; they arrive with each task.

## Traps

- The description is missing, too long, or overlaps another agent's, so the wrong agent runs or none does.
- The prompt assumes instructions that arrive only with the caller. A called agent does not receive the caller's standing prompt.
- [Role](role.md), [procedure](procedure.md), and [constraints](constraints.md) give opposite orders, and the agent spends the task reconciling them.
