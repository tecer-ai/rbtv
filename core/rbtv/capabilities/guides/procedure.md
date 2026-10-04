# Building a procedure

A [procedure](../glossary/procedure.md) is the reusable method for the agent's work.

## Purpose

It is the method that holds across this agent's tasks. Without it, each task improvises its own method, and the results differ run to run. The choice of unit is [Choosing what to build](<../_under-evaluation/guides/procedure documents/choosing-what-to-build.md>).

## What good looks like

- Each step with an exact answer names the [tool](../glossary/tool.md) that answers it ([Deterministic first](../principles/deterministic-first.md)).
- Removing any step loses a required action, result, check, or branch; otherwise remove it ([Keep it simple](../principles/kiss.md)).
- No step names one task's files, goal, or done checks ([Progressive disclosure](../principles/progressive-disclosure.md)).
- An every-task check appears once, in this procedure or in the [skill](../glossary/skill.md) or [command](../glossary/command.md) that owns it, not in both ([Single source of truth](../principles/single-source-of-truth.md)).
- One representative task and one failed prerequisite walk the complete prompt: each step has its inputs, each branch has a stated next action, the result is identifiable, and no cognitive unit of the prompt gives incompatible instructions.
- One method. An unrelated second method is a second procedure, so a second agent ([Micro agency](../principles/micro-agency.md)).
- A result another task uses is a file or record that task can read without this agent ([Micro agency](../principles/micro-agency.md)).

## Making it good

Order the steps that must happen in order. At each branch, state what changes the path.

Give each exact-answer step the tool that answers it. Leave interpretation to the agent.

When a step needs a skill or a [capability](capability.md), point to it at that step and name the moment to open it. Do not paste it.

Put a condition that must hold for every task here, or in the skill or command that does that work. Do not copy it into each [done contract](../../../../meta/sub-agents/capabilities/done-contract.md).

When another task uses a step's result, pass a file or record with fixed fields. Order steps that change the same file or record ([Micro agency](../principles/micro-agency.md)).

## Traps

- Two steps that change the same file or record are left unordered, and one overwrites the other.
