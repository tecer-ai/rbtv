---
id: check-mechanization
description: "Try to fail the draft plan on the mechanization dimension — every agentic step code could do, every judgment repeated across seats, every restructuring and every existing CLI the plan left unused"
---

<task-goal>
Return a findings verdict on the seeded draft plan for the mechanization dimension only — every mechanization opportunity the plan left untaken, each with its tool shape and payoff, or a pass forced by a lens-by-lens empty hunt over every seat of the plan.
</task-goal>

<scope>
- Read: the draft plan — the manifest at `planning/current/manifest.csv` and one prompt+task pair per seat under `planning/current/seats/<seat-id>/` — each seat's task and prompt content is what the per-seat probes are handed; the capability-cards output (a means the scaffolding already carries is shopped, never proposed as a build); the tool and modality law in the guides named in this task's Guides bullet.
- Write: this inspection's findings file at `planning/current/findings-mechanization.md`, relative to the goal folder — nothing else. The whole `planning/` subtree is read-write for every seat of this run; overwrite the file if it already exists (findings are per-round, never appended across rounds).
- **Guides — read whole before writing:** `references/kind-capability.md`; `references/workflow-anatomy.md`.
</scope>

<done-contract>
Kill criteria — the dimension's whole law; any hit is a FAIL finding:
- A task stamped `agentic` whose work code could fully do — its probe returns `could-code-fully-do: yes` with a modality challenge naming the inputs, the deterministic decision, and the output, and no step of that seat survives the challenge as judgment.
- One `judgment-fingerprint` returned by two or more seats with no shared tool covering it — the same judgment paid for once per seat.
- Content a seat reads or writes as prose that, restructured into a schema, a typed field, or a marker, would turn one of its steps or checks deterministic.
- An agent step an existing third-party CLI already covers.

Done when, checkable at the edge:
- `planning/current/findings-mechanization.md` carries a PASS|FAIL verdict line as its first non-blank line. (The file may exist EMPTY from spawn — existence is not the artifact; the verdict line is.)
- Every finding names {plan location, violated criterion, evidence, fix-class: mechanical|judgment}, its evidence naming the opportunity, the shape of the tool that would take it (what it reads, what it decides, what machine-readable output it emits), and the payoff.
- The probe count equals the manifest's seat-row count, or every unprobed seat is named in the file as a coverage gap.
- Every opportunity found is in the file, the ones judged low-payoff included, each carrying its payoff statement.
- On PASS, the file carries the per-lens account of what was hunted and found empty.
- No finding re-stamps a task's modality or prescribes an edit to the plan, and no finding cites any dimension other than mechanization.

Outcome map:
- Verdict written (PASS or FAIL) → completion; the findings seed the digesting seat, and their toolsmith-worthy rows are the resource-definer's input.
- `planning/current/manifest.csv` missing or unreadable → FAIL-BLOCKED naming it; feedback schema {expected-path, expected-producer: plan-assembler}.
</done-contract>
