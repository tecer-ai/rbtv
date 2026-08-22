---
id: check-clarity
description: "Try to fail the draft plan on the clarity dimension — instructions a literal-minded stranger executor cannot misunderstand"
---

<task-goal>
Return a findings verdict on the seeded draft plan for the instructions-are-clear dimension only — every instruction a literal-minded stranger could misread found, or a pass forced by a criterion-by-criterion empty hunt.
</task-goal>

<scope>
- Read: the draft plan — the manifest at `planning/current/manifest.csv` and one prompt+task pair per seat under `planning/current/seats/<seat-id>/`; and `planning/current/applied-deltas-round-<n>.json` when present.
- Write: this inspection's findings file at `planning/current/findings-clarity.md`, relative to the goal folder — nothing else. The whole `planning/` subtree is read-write for every seat of this run; overwrite the file if it already exists (findings are per-round, never appended across rounds).
</scope>

<done-contract>
Kill criteria — the dimension's whole law; any hit is a FAIL finding:
- An instruction two literal-minded readers would execute differently.
- A vague noun in a task goal or done criterion — a clause two readers could score differently.
- An instruction depending on context the executor is never handed — session memory, an unstated path, an unseeded fact.
- A citation standing in for an instruction — text the executor must look up before it can act.
- **A repair that landed but does not hold** — a region named in `applied-deltas-round-<n>.json` that contradicts, duplicates, or is contradicted by another statement in its own `section` or elsewhere in the same file. Read each named region **with its whole enclosing section**, never the changed lines alone. A repair is coherent or it is a finding.

Done when, checkable at the edge:
- `planning/current/findings-clarity.md` carries a PASS|FAIL verdict line as its first non-blank line. (The file may exist EMPTY from spawn — existence is not the artifact; the verdict line is.)
- Every finding names {plan location, violated criterion, evidence, fix-class: mechanical|judgment}.
- On PASS, the file carries the per-criterion account of what was checked and found empty.
- No finding cites any dimension other than instructions-are-clear.

Outcome map:
- Verdict written (PASS or FAIL) → completion; the findings seed the digesting seat.
- `planning/current/manifest.csv` missing or unreadable → FAIL-BLOCKED naming it; feedback schema {expected-path, expected-producer: plan-assembler}.
</done-contract>
