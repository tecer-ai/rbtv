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
- No per-seat wall-clock deadline field. No durable scaffolding minted. Envelope is a section, not a compiled artifact.
- Every produced execution seat carries the six authoring declarations (one `goal-writes` or documented empty+chat schema; instruments named; interact+fallback when the role reaches a human; seat-folder names; no hardcoded owner values; a complete done-contract).
- An `input-gaps` list is present (may be empty).
- Completeness: every actor has a seat or an explicit out-of-scope; every input has a source seat or an input-gap; each seat names its failure arm; two seats with the same id is a fail; a declared output present in neither a seat `goal-writes` nor a named handoff is a fail.

Outcome map:

- **Complete** → the draft seeds review+finalize.
- **Markerless upstream** → repair forward, log the gap, complete. Never reject. Never re-enter design.
- **Owner reject-retry comments** (when this task is relaunched with comments as a closed findings list) → treat those comments as the only fix targets; do not reopen the approach.
</done-contract>
