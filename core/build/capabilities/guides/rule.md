# Building a rule

A [rule](../glossary/rule.md) is a [cognitive unit](../glossary/cognitive-unit.md) whose full text reaches every agent that receives it, on every task, with no choice to load it.

## Purpose

It holds an instruction that applies on every task of every agent that receives it. Without it, that instruction is missed, or it is loaded only sometimes and the tasks that needed it go wrong. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- The description's first sentence states what every receiving agent does on every task. A sentence that names a case to skip fails.
- For every sentence, you cannot name a task of a receiving agent where it does not apply. Any such task means that sentence is not a rule. The sentence is not true only inside one folder ([Progressive disclosure](../principles/progressive-disclosure.md)).
- For each line, a reviewer can name evidence of following it and evidence of violating it on a task record. A line with neither is rewritten.
- Two rules the same agent receives do not give different answers for the same behavior.
- One purpose. An unrelated "and also" is a second rule ([Micro agency](../principles/micro-agency.md)).
- An exact-answer step names the [tool](tool.md) and when to call it. The sentence is not the check ([Deterministic first](../principles/deterministic-first.md)).
- No fact is copied from a home it already has. A command the agent will not find without searching may be named ([Single source of truth](../principles/single-source-of-truth.md)).
- At most one line is emphasized.
- Removing any sentence would make the agent do the wrong thing on a task the rule covers ([Keep it simple](../principles/kiss.md)).

## Making it good

Write the description for the person choosing which rules an agent receives.

The agent receives the full instruction, and there is no second load. Keep standing behavior only, with all its content in its body. A rule may route to capabilities only when an agent's whole work is that domain; the agent's own prompt may route instead.

## Traps

- A procedure, a folder convention, or a copied document sits in the rule and crowds every task.
