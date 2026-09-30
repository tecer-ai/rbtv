---
description: "Read at the moment a change creates a file or grows one — to rule the one-responsibility-per-file shape, what a size signal means, and when splitting is the wrong move."
tags: [coding]
---

# no-monolith

ONE responsibility per file, named by its filename. Size is a smell, never a cap.

## Rules

| # | Rule |
|---|------|
| 1 | A new file holds ONE responsibility, and its filename says which. A file whose name needs "and" to describe it holds two — split before writing. |
| 2 | When your change grows an existing file, you MUST answer: does this file now do more than one thing? Yes → the new thing goes in its own file, reached by import. The existing file is NEVER split unasked — that is pre-existing; surface it. |
| 3 | Judgment call: around 300 lines, stop and answer rule 2's question. A 400-line file with one responsibility stays; a 120-line file with three is split. |
| 4 | NEVER split a cohesive file into fragments to hit a size. A set of thin files an agent must bounce between to follow one concept is the opposite failure — a shallow module (the `improve-codebase-architecture` skill's subject). Splitting is right only when each part can be verified on its own. |

## Tripwire

Before closing: for every file you grew, name its one responsibility in one line. Two lines → the new responsibility goes in its own file (rule 2). Size is not the trigger; the second responsibility is.
