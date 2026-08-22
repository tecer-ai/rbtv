---
id: check-consistency
description: "Try to fail the draft plan on the consistency dimension — the plan traces to the milestone's done contract, nothing missing, nothing extra"
---

<task-goal>
Return a findings verdict on the seeded draft plan for the consistency-with-milestone-DoD dimension only — every gap between the plan and the milestone's done contract found, or a pass forced by a criterion-by-criterion empty hunt.
</task-goal>

<scope>
- Read: the draft plan — the manifest at `planning/current/manifest.csv` and one prompt+task pair per seat under `planning/current/seats/<seat-id>/` — and the seeded milestone's done contract.
- Write: this inspection's findings file at `planning/current/findings-consistency.md`, relative to the goal folder — nothing else. The whole `planning/` subtree is read-write for every seat of this run; overwrite the file if it already exists (findings are per-round, never appended across rounds).
- **Guides — read whole before writing:** `references/kind-done-contract.md`.
</scope>

<done-contract>
Kill criteria — the dimension's whole law; any hit is a FAIL finding:
- A clause of the milestone's done contract that no task provably serves.
- A task whose output serves no milestone clause and no other task's input — work the done contract never asked for.
- A task done contract that could pass in full while the milestone clause it serves fails — the entailment does not hold.
- An `interactive`-modality manifest row whose seat lacks `human-interactive: yes` in its prompt frontmatter, or whose done contract names no autonomous fallback arm (park durably / stated default with disclosure / block-and-queue) — and the converse: a flagged seat whose procedure states no fallback.

Done when, checkable at the edge:
- `planning/current/findings-consistency.md` carries a PASS|FAIL verdict line as its first non-blank line. (The file may exist EMPTY from spawn — existence is not the artifact; the verdict line is.)
- Every finding names {plan location, violated criterion, evidence, fix-class: mechanical|judgment}.
- On PASS, the file carries the per-criterion account of what was checked and found empty.
- No finding cites any dimension other than consistency-with-milestone-DoD.

Outcome map:
- Verdict written (PASS or FAIL) → completion; the findings seed the digesting seat.
- `planning/current/manifest.csv` or the milestone's done contract missing or unreadable → FAIL-BLOCKED naming it; feedback schema {expected-path, expected-producer: plan-assembler}.
</done-contract>
