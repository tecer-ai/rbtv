---
id: check-edges
description: "Try to fail the draft plan on the edges dimension — every after edge names a datum that actually crosses and carries what its consumer needs; every task executable from its seed alone; no cycle, no ceremony edge"
---

<task-goal>
Return a findings verdict on the seeded draft plan for the edges dimension only — every `after`-edge violation found, or a pass forced by a criterion-by-criterion empty hunt.
</task-goal>

<scope>
- Read: the draft plan — the manifest at `planning/current/manifest.csv` and one prompt+task pair per seat under `planning/current/seats/<seat-id>/`; the edge law in the guides named in this task's Guides bullet.
- Write: this inspection's findings file at `planning/current/findings-edges.md`, relative to the goal folder — nothing else. The whole `planning/` subtree is read-write for every seat of this run; overwrite the file if it already exists (findings are per-round, never appended across rounds).
- **Guides — read whole before writing:** `references/workflow-anatomy.md`.
</scope>

<done-contract>
Kill criteria — the dimension's whole law; any hit is a FAIL finding:
- An `after` edge that names no datum actually crossing it — an edge born of birth order, narrative sequence, or caution.
- A datum that crosses between two seats with no `after` edge declaring it.
- An `after` edge whose producer's declared output does not carry what the consumer's declared input requires — a datum that crosses in name but not in content.
- A task whose seed does not suffice to execute it: any datum the executing seat needs that exists only in planning-time reasoning and is written nowhere the seat receives — not in its task body, its declared inputs, or its named context. (The canonical instance: a toolsmith task not carrying its consumers' derived requirements.)
- A cycle anywhere in the graph.
- A guard that cannot be evaluated deterministically against the predecessor's declared output.

Done when, checkable at the edge:
- `planning/current/findings-edges.md` carries a PASS|FAIL verdict line as its first non-blank line. (The file may exist EMPTY from spawn — existence is not the artifact; the verdict line is.)
- Every finding names {plan location, violated criterion, evidence, fix-class: mechanical|judgment}.
- On PASS, the file carries the per-criterion account of what was checked and found empty.
- No finding cites any dimension other than edges.

Outcome map:
- Verdict written (PASS or FAIL) → completion; the findings seed the digesting seat.
- `planning/current/manifest.csv` missing or unreadable → FAIL-BLOCKED naming it; feedback schema {expected-path, expected-producer: plan-assembler}.
</done-contract>
