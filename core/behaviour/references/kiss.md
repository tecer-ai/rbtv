---
description: "Simplicity on every turn, decided BEFORE any work starts: does this need to exist at all, and what is the simplest design that fully solves it — no speculative generality, the existing means before a new one, complexity faced only when the problem demands it."
tags: [behaviour]
---

# KISS

ALWAYS active, on EVERY piece of work — code, a plan, a document, a seat, a message — and applied BEFORE the work starts. This rule governs the DECISION of what to build and how simply. What finished code must look like (no leftovers, one source per fact, one job per file, a fix at the cause) is the `coding` skill's subject and is NOT restated here.

## Hard Rules

| # | Rule |
|---|------|
| 1 | **Does this need to exist at all?** Before building anything — a file, a step, an option, an abstraction, a seat — answer in one line what it is for. No answer → it MUST NOT be built; say so in one line and move on. |
| 2 | **The simplest solution that fully solves the problem.** Simple is reached by working the complexity OUT, never by leaving substance out. Among designs that fully solve it, the one with the fewest moving parts wins. |
| 3 | **YAGNI (you aren't gonna need it).** NEVER build for a need nobody has stated: no configurability, generality, extension point, or "while I am here" addition beyond the ask. A future need is met when it arrives. |
| 4 | **Existing means first.** Before writing anything new, find what already exists: the standard library before custom code, a native feature before a dependency, an existing tool, skill, or file before a new one, a one-line change before a new layer. |
| 5 | **Complexity is faced, never avoided.** When the problem genuinely demands a bigger structure, build it without ceremony. Rule 2 forbids needless complexity, not necessary complexity. |

## Tripwire

Before the first edit or the first new file, state the simplest solution in ONE sentence. Every part of the plan beyond that sentence MUST earn its place under rule 1, or it is dropped.

## Scope

All work, every turn. An opt-in intensity beyond this baseline is the `ponytail` skill ("be lazy", lite / full / ultra); it never replaces this rule.
