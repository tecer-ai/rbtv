# Building a principle

A [principle](../glossary/principle.md) is a standing design choice that shapes an agent's [context window](../glossary/context-window.md).

## Purpose

It fixes one trade-off a builder applies to every structure, including one not yet designed. Without it, that choice is remade each time; if you cannot name what a builder does wrong without it, do not create it ([Keep it simple](../principles/kiss.md)). The choice of unit is [Choosing what to build](<../_under-evaluation/guides/procedure documents/choosing-what-to-build.md>).

## What good looks like

- The statement is "X, even over Y", and you can name a builder who would choose Y. "Even over doing it wrong" fails.
- The rationale names the context-window effects the principle reduces, hallucination or drift, and the causes it acts on: context load, context gap, cognitive load, or context poisoning ([context window](../glossary/context-window.md)). A rationale that names none fails.
- No sentence tells an agent how to behave during a task.
- Each implication is an instruction with a yes or no condition. A description of what the system does fails. A value-word such as "clean" as the test fails.
- No implication adds a section or field that every design must contain. It is a test, not a required piece of the design.
- No implication repeats another principle file. A link to that file passes ([Single source of truth](../principles/single-source-of-truth.md)).
- The file states no tie-break of its own; the tie-break lives in [Keep it simple](../principles/kiss.md) alone.

## Making it good

Write the statement first, then the rationale as why the trade-off is worth making and which context-window effects it reduces; do not repeat the implications there.

Write each implication as an instruction to the builder, naming the structure it changes and the condition a reviewer confirms or rejects. Add one only where removing it would lose a decision.
