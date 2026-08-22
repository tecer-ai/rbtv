---
id: check-scope
description: "Try to fail the draft plan on the scope dimension — every seat micro, one simple job; a task description needing and twice is two tasks"
---

<task-goal>
Return a findings verdict on the seeded draft plan for the scope-is-small dimension only — every oversized seat or over-wide surface found, or a pass forced by a criterion-by-criterion empty hunt.
</task-goal>

<scope>
- Read: the draft plan — the manifest at `planning/current/manifest.csv` and one prompt+task pair per seat under `planning/current/seats/<seat-id>/`; the surface law in the guides named in this task's Guides bullet.
- Write: this inspection's findings file at `planning/current/findings-scope.md`, relative to the goal folder — nothing else. The whole `planning/` subtree is read-write for every seat of this run; overwrite the file if it already exists (findings are per-round, never appended across rounds).
- **Guides — read whole before writing:** `references/kind-scope.md`.
</scope>

<done-contract>
Kill criteria — the dimension's whole law; any hit is a FAIL finding:
- A seat holding more than one simple job — a task description that needs "and" twice is two tasks.
- A task done contract spanning deliverables no single simple job produces.
- A scope surface no done-contract clause needs — a "for context" surface is context tax.
- A seat whose honest persona converges with another seat's — two such seats are one seat.

Done when, checkable at the edge:
- `planning/current/findings-scope.md` carries a PASS|FAIL verdict line as its first non-blank line. (The file may exist EMPTY from spawn — existence is not the artifact; the verdict line is.)
- Every finding names {plan location, violated criterion, evidence, fix-class: mechanical|judgment}.
- On PASS, the file carries the per-criterion account of what was checked and found empty.
- No finding cites any dimension other than scope-is-small.

Outcome map:
- Verdict written (PASS or FAIL) → completion; the findings seed the digesting seat.
- `planning/current/manifest.csv` missing or unreadable → FAIL-BLOCKED naming it; feedback schema {expected-path, expected-producer: plan-assembler}.
</done-contract>
