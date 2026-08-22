---
id: plan-milestone
description: "Plan one collapsed-mode milestone end to end alone — tasks, resources, assembly, checks, binding — with no contract weakened"
---

<task-goal>
Plan the seeded collapsed-stamped milestone end to end alone — tasks defined, resources assigned, plan assembled, every check dimension the pass runs inspected, taskforce bound and verified — meeting every contract the full team's pipeline meets.
</task-goal>

<scope>
- Read: the seeded milestone row (stamped `planning-mode=collapsed`) and its done contract; the run's goal artifacts (`goal.md`, `milestones.csv`); the capability-cards output; the planning component's `component.md`, seat catalog, and judge/eval pool — `seats.csv` plus the definitions `prompts/dod-judge.md` + `tasks/judge-milestone.md` and `prompts/unblock-checker.md` + `tasks/check-unblocked.md`, the pool being its own state source; the staffing hints; the run's `taskforce.csv`; the materialized seat folders; the guides named in this task's Guides bullet.
- Write: the goal's planning workspace under `planning/current/` — the task DAG at `planning/current/task-dag.md`, the resourced plan at `planning/current/resourced-plan.md`, the manifest at `planning/current/manifest.csv` with each seat's pair under `seats/<seat-id>/`, the per-dimension check record at `planning/current/findings-<dimension>.md` with its dispositions at `planning/current/dispositions.md`, and the verification report at `planning/current/verification.md`; the run's `taskforce.csv` (append only); the produced seats' `seat.md` inscriptions.
- **Guides — read whole before writing:** `references/file-prompt.md`; `references/file-task.md`; `references/kind-role.md`; `references/kind-procedure.md`; `references/kind-io-spec.md`; `references/kind-permissions.md`; `references/kind-restrictions.md`; `references/kind-constraints.md`; `references/kind-task-goal.md`; `references/kind-scope.md`; `references/kind-done-contract.md`; `references/kind-capability.md`; `references/component-anatomy.md`; `references/exposure.md`; `references/workflow-anatomy.md`; `references/authoring-style.md`; `ws:1-projects/build-ignite/system-definition/primer.md`.
</scope>

<done-contract>
Done when, checkable at the edge — the union of the phase's contracts, none weakened:
- Task DAG: acyclic; every task one simple job (no description needing "and" twice); every milestone-DoD clause traced to a task and every task to a clause; per-task done contracts with observable criteria, outcome maps, and feedback schemas.
- Resources: every means matched to a capability card or covered by a toolsmith task ordered before its consumers, toolsmith done contracts including scaffolding registration and exposure; every grant traceable to a step, write scope no wider than read.
- Assembly: a manifest (Seat/workflow · after · i/o · Modality, no order column) plus one seat definition per row, every demanded section present with nested kinds nested; the two closing seats from the judge/eval pool as the final rows, the unblock-checker flagged interim while bound as an agent seat.
- Checks: a check record covering the six standing dimensions — per dimension, findings with dispositions or the per-criterion checked-and-empty account — plus, when and only when `goal.md`'s `use-case:` reads optimize, port, or scaffold, a seventh mechanization record: one cheap per-seat probe per seat of the draft, and every mechanization opportunity found (agentic work code could fully do · a judgment fingerprint repeated across two or more seats with no shared tool · content whose restructuring would turn a step or check deterministic · an agent step an existing third-party CLI covers) recorded with its tool shape and payoff, the declined ones included.
- Binding: rows appended to the run's single `taskforce.csv` with pre-existing rows byte-identical and `after` sets frozen-copied; full `seat.md` inscriptions for an ephemeral product; goal lint exit 0; a read-back verification report listing each materialized artifact.

Outcome map:
- All of the above verified → completion: the pass's terminal act.
- The seeded row's stamp is not `collapsed` → FAIL immediately; feedback schema {row, observed-stamp}. This task never plans a full-team milestone.
- Milestone done contract ambiguous, a means unresolvable, the judge/eval pool absent, or materialization incomplete → FAIL back or FAIL-BLOCKED with the same feedback schemas the full-team tasks declare for those scenarios: {clause, why-untestable, question} · {task, means, why-unresolvable, options} · {missing-definition, pool-state-source} · {row, expected-artifact, observed}.
</done-contract>
