---
id: check-resources
description: "Try to fail the draft plan on the resources dimension — every task's means shopped and assigned; no seat left to improvise"
---

<task-goal>
Return a findings verdict on the seeded draft plan for the resources dimension only — every unprovided or improvised means found, or a pass forced by a criterion-by-criterion empty hunt.
</task-goal>

<scope>
- Read: the draft plan — the manifest at `planning/current/manifest.csv` and one prompt+task pair per seat under `planning/current/seats/<seat-id>/`; the capability-cards output (verifying a claimed means exists is reading the cards); the guides named in this task's Guides bullet.
- Write: this inspection's findings file at `planning/current/findings-resources.md`, relative to the goal folder — nothing else. The whole `planning/` subtree is read-write for every seat of this run; overwrite the file if it already exists (findings are per-round, never appended across rounds).
- **Guides — read whole before writing:** `references/kind-capability.md`.
</scope>

<done-contract>
Kill criteria — the dimension's whole law; any hit is a FAIL finding:
- A means named by any task that no capability card matches and no toolsmith task covers.
- A toolsmith task ordered after — or unordered relative to — a task consuming its product.
- A toolsmith task whose done contract omits scaffolding registration or exposure.
- A procedure step whose work has no means assigned — a seat left to improvise.

Done when, checkable at the edge:
- `planning/current/findings-resources.md` carries a PASS|FAIL verdict line as its first non-blank line. (The file may exist EMPTY from spawn — existence is not the artifact; the verdict line is.)
- Every finding names {plan location, violated criterion, evidence, fix-class: mechanical|judgment}.
- On PASS, the file carries the per-criterion account of what was checked and found empty.
- No finding cites any dimension other than resources.

Outcome map:
- Verdict written (PASS or FAIL) → completion; the findings seed the digesting seat.
- `planning/current/manifest.csv` missing or unreadable → FAIL-BLOCKED naming it; feedback schema {expected-path, expected-producer: plan-assembler}.
</done-contract>
