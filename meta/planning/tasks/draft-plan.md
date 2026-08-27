---
id: draft-plan
description: "Produce the complete draft plan — seats/workflow, envelope and credential-name sections, interact flags, outputs, relaunch budget"
---

<task-goal>
Produce the complete draft plan for the seeded goal: every design milestone detailed, the execution seats or workflow, envelope and credential-name sections, interact flags, declared outputs, and relaunch budget.
</task-goal>

<scope>
- **Read:** `planning/design.md`, `planning/facts-brief.md`, and every artifact those name.
- **Write:** `planning/draft-plan.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/draft-plan.md` exists and its first line is exactly `DRAFT-PLAN`.
- Every milestone id from `planning/design.md` appears, detailed; no id added or dropped.
- The body has an execution seats/workflow, a permission-envelope *section*, a credential-name *section* (names only), per-seat interact flags, declared outputs, a relaunch budget, and named handoff contents.
- An **EXECUTION DECLARATION** section is present and complete. Approval BIRTHS the execution goal: the owner's `approve` runs a Path-B birth that scaffolds a new goal folder and MINTS its roster, so a plan with no declaration has no truthful value for the fields that birth requires, and no plan executes "in place" inside the planning goal. The section carries exactly these fields and no others — they are what the `approve-package` writer takes:
  - `execution-goal` — the bare safe name the goal will be born under. It becomes a path segment under `.rbtv/goals/`, so it must match `^[A-Za-z0-9][A-Za-z0-9._-]*$` and must not be `owner`. Not a path, not a title, not a sentence.
  - `lane` — the born goal's lane, as `scaffold --lane` takes it.
  - `roster` — the execution seat ids, comma-separated. Duplicate ids are refused at birth.
  - `workflow` and `sheet` — where the plan lands as a durable workflow, when the owner declared durable at goal creation. Omitted for a one-off taskforce, and said to be omitted.
  - `contract-file` — the goal contract the birth's scaffold receives, where the plan names one.
- The declaration says, in the plan's own words, that the daemon mints those roster seats AT BIRTH from this declaration. NO seat in this planning goal casts, materializes, or launches an execution seat, and no milestone may assign that act to one — a milestone whose mechanism names a planning-goal seat as the caster is not draftable and the mechanism must be rewritten to the birth.
- No per-seat wall-clock deadline field. No durable scaffolding minted. Envelope is a section, not a compiled artifact.
- Every produced execution seat carries the six authoring declarations (one `goal-writes` or documented empty+chat schema; instruments named; interact+fallback when the role reaches a human; seat-folder names; no hardcoded owner values; a complete done-contract).
- An `input-gaps` list is present (may be empty).
- Completeness: every actor has a seat or an explicit out-of-scope; every input has a source seat or an input-gap; each seat names its failure arm; two seats with the same id is a fail; a declared output present in neither a seat `goal-writes` nor a named handoff is a fail; a roster seat id absent from the plan's own seat list, or a plan seat absent from the roster, is a fail.

Outcome map:

- **Complete** → the draft seeds review+finalize.
- **Markerless upstream** → repair forward, log the gap, complete. Never reject. Never re-enter design.
- **Owner reject-retry comments** (when this task is relaunched with comments as a closed findings list) → treat those comments as the only fix targets; do not reopen the approach.
</done-contract>
