---
id: assemble-plan
description: "Assemble the seeded milestone's draft manifest and seat definitions, adding the standard closing seats from the judge pool"
---

<task-goal>
Assemble the seeded resourced task DAG into the milestone's execution workflow — one seat definition per task plus the manifest, closed by the two standard closing seats from the judge/eval pool.
</task-goal>

<scope>
- Read: the seeded resourced task-DAG draft; the planning component's `component.md`, seat catalog, and judge/eval pool — `seats.csv` plus the definitions `prompts/dod-judge.md` + `tasks/judge-milestone.md` and `prompts/unblock-checker.md` + `tasks/check-unblocked.md`, the pool being its own state source; the guides named in this task's Guides bullet.
- Write: the draft manifest at `planning/current/manifest.csv` and, per manifest row, `planning/current/seats/<seat-id>/prompt.md` + `planning/current/seats/<seat-id>/task.md` — nothing else. The goal's `planning/` subtree is read-write for you.
- **Guides — read whole before writing:** `references/file-prompt.md`; `references/file-task.md`; `references/kind-role.md`; `references/kind-procedure.md`; `references/kind-io-spec.md`; `references/kind-permissions.md`; `references/kind-restrictions.md`; `references/kind-constraints.md`; `references/component-anatomy.md`; `references/exposure.md`; `references/workflow-anatomy.md`; `references/authoring-style.md`; `ws:1-projects/build-ignite/system-definition/primer.md`.
</scope>

<done-contract>
Done when, checkable at the edge:
- The draft manifest exists at `planning/current/manifest.csv` — one row per seat (Seat/workflow · after · i/o · Modality), no order column, `after` sets matching the resourced DAG.
- One seat definition exists per manifest row, as the seat's PAIR: the prompt file (role with persona and agent type nested, procedure, i/o spec with input/outcome/output nested, permissions, restrictions) AND its paired task file (task-goal, scope, done contract — per `references/file-task.md`); a reused cataloged seat records its source prompt/task ids.
- Every seat whose role includes talking to the human carries `human-interactive: yes` in its prompt frontmatter, and every flagged seat's procedure states its autonomous fallback arm.
- The two standard closing seats — the DoD judge and the unblock-checker — are the milestone's final rows, sourced from the judge/eval pool; the unblock-checker row carries the interim flag whenever it is bound as an agent seat.
- On a workflow-producing run (`goal.md` `use-case:` optimize, port, or scaffold), the drafted workflow definition declares `default-execution-mode:` — `interactive` or `autonomous` — carried verbatim from `goal.md`'s field of that name, and declares nothing where `goal.md` declares nothing (owner ruling 2026-08-10; the creation path derives the same value from the Modality column, so an invented declaration would outrank an owner-confirmed derivation).
- No seat text cites a knowledge-graph record or ruling in place of a direct instruction.

Outcome map:
- Completion → the draft plan seeds the check swarm.
- The judge/eval pool or a closing-seat definition is absent → FAIL back to the workflow; feedback schema {missing-definition, pool-state-source}. Never author a substitute.
- A task unassemblable as one seat (its resourced definition is contradictory or oversized) → route back; feedback schema {task, defect}.
</done-contract>
