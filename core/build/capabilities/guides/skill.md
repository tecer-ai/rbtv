# Building a skill

A [skill](../glossary/skill.md) is a [cognitive unit](../glossary/cognitive-unit.md) an agent reads only after its description shows it is relevant.

## Purpose

It holds instructions an agent should load only when it judges them relevant. Without that choice, the instructions are missing on the tasks that need them, or they crowd every task. Follow the [entry point and capabilities shape](capability.md) and the choice in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- Description alone: the first sentence accepts one task that should open it. The rest, not the body, names one similar task that must not. The first sentence does not carry the refusal ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Walk one representative task through the body using only its stated inputs and references: every step is executable and produces the stated result, steps that change the same file are ordered, and a missing input has an explicit next action ([Micro agency](../principles/micro-agency.md)).
- One purpose. No unrelated "and also". A split fails when a piece is not independent, with no judgeable result of its own ([Micro agency](../principles/micro-agency.md)).
- A judgment step states the criterion and the reason.
- A check every run of this skill must pass is a step in the body, not a [done contract](../glossary/done-contract.md).
- No sentence repeats instructions that already have a home. Each shared instruction is a pointer that names the moment; a one-line warning for a mistake made before opening the file a pointer names may stay ([Single source of truth](../principles/single-source-of-truth.md)).
- Every exact-answer step names a [tool](tool.md). No exact answer is left to the agent ([Deterministic first](../principles/deterministic-first.md)).
- Removing any sentence loses a requirement or a decision ([Keep it simple](../principles/kiss.md)).

## Making it good

Write the description before the body. Name the situations that should open it, including one that does not use the skill's name. Put every "when" in the description, and do not use first or second person.

Name the inputs the body requires, the result it produces, and what the agent does when an input is missing. Write the body as imperative steps for that one purpose.

## Traps

- The description is a slogan, or the situations are only in the body, so the agent never opens it.
- No similar task it must refuse, or a pile of synonyms, so it opens on adjacent work or on a word.
