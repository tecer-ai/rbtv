---
id: check-permissions
description: "Try to fail the draft plan on the permissions dimension — smallest sufficient grant per seat, nothing granted to-be-safe"
---

<task-goal>
Return a findings verdict on the seeded draft plan for the permissions dimension only — every over-grant, under-grant, or misplaced bound found, or a pass forced by a criterion-by-criterion empty hunt.
</task-goal>

<scope>
- Read: the draft plan — the manifest at `planning/current/manifest.csv` and one prompt+task pair per seat under `planning/current/seats/<seat-id>/`; the grant law in the guides named in this task's Guides bullet.
- Write: this inspection's findings file at `planning/current/findings-permissions.md`, relative to the goal folder — nothing else. The whole `planning/` subtree is read-write for every seat of this run; overwrite the file if it already exists (findings are per-round, never appended across rounds).
- **Guides — read whole before writing:** `references/kind-permissions.md`; `references/kind-restrictions.md`; `references/workflow-authoring-checklist.md`.
</scope>

<done-contract>
Kill criteria — the dimension's whole law; any hit is a FAIL finding:
- A grant no procedure step needs — granted "to be safe", "for flexibility", or for a future task.
- A procedure step whose reads, writes, or commands exceed its seat's grant — an under-granted seat that cannot run.
- A write scope wider than the surfaces the seat's work actually lands on.
- A bound at the wrong enforcement locus: a prohibition sitting in permissions, a grant sitting in restrictions, or a judgment-honored bound sitting in either.
- A draft seat declaration failing the workflow-authoring checklist named in this task's Guides bullet: no `goal-writes` for a seat that produces a goal-folder artifact (or one naming ground truth, a `..`-climbing path, or a file nothing creates), an instrument the procedure uses that no `exposes:` group declares, an owner-facing seat left unmarked interactive, or an owner-specific value hardcoded instead of read from config.

Done when, checkable at the edge:
- `planning/current/findings-permissions.md` carries a PASS|FAIL verdict line as its first non-blank line. (The file may exist EMPTY from spawn — existence is not the artifact; the verdict line is.)
- Every finding names {plan location, violated criterion, evidence, fix-class: mechanical|judgment}.
- On PASS, the file carries the per-criterion account of what was checked and found empty.
- No finding cites any dimension other than permissions.

Outcome map:
- Verdict written (PASS or FAIL) → completion; the findings seed the digesting seat.
- `planning/current/manifest.csv` missing or unreadable → FAIL-BLOCKED naming it; feedback schema {expected-path, expected-producer: plan-assembler}.
</done-contract>
