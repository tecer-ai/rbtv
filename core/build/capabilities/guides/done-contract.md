# Building a done contract

A [done contract](../glossary/done-contract.md) states the observable conditions for one [task](../glossary/task.md), and what to do when the result misses them.

## Purpose

It is the standard a second reader uses to pass or fail this task's result. Without it, the agent stops when the work looks done, and the author asserts success. The choice of unit is [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- A second reader, with only the result, reaches the same pass or fail. "Looks complete" fails. ([Micro agency](../principles/micro-agency.md))
- Each exact check names a [tool](../glossary/tool.md) and the pass or fail that tool returns. A check that needs judgment says what on the result to score. ([Deterministic first](../principles/deterministic-first.md))
- It judges one result. Independent results are a split task, not extra lines. ([Micro agency](../principles/micro-agency.md))
- No condition holds for every task of the [skill](../glossary/skill.md), [command](../glossary/command.md), or [procedure](../glossary/procedure.md) that does the work. ([Single source of truth](../principles/single-source-of-truth.md))
- A condition whose removal loses no decision about this task is absent. ([Keep it simple](../principles/kiss.md))
- A miss names the feedback and the next action. "Retry" alone fails.

## Making it good

State each condition as something a reader can observe on the result. On a miss, name the feedback to return and the next action: stop, or continue with a named change.
