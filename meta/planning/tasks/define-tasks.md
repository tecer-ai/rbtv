---
id: define-tasks
description: "Decompose the seeded milestone into a task DAG with after sets, i/o, guards, and per-task done contracts"
---

<task-goal>
Decompose the seeded milestone into a DAG of micro tasks — each one simple job carrying its `after` set, i/o, guards, and a machine-checkable done contract — executable by a stranger team from the task texts alone.
</task-goal>

<scope>
- Read: the seeded milestone row and its done contract; the run's goal artifacts (`goal.md`, `milestones.csv`); the guides named in this task's Guides bullet.
- Write: the task-DAG draft at `planning/current/task-dag.md`, relative to the goal folder — nothing else. The goal's `planning/` subtree is read-write for you. On a relaunch driven by a route-back, additionally write `planning/current/deltas-<seat-id>-round-<n>.md` in the `delta-anchors` format — every `from` block copied verbatim **out of the target file you name**, never out of `task-dag.md`, `resourced-plan.md`, a route-back brief, or your own recollection. Run `delta-anchors check` on it before you report done; a file with findings is not a returned repair.
- **Guides — read whole before writing:** `references/file-task.md`; `references/kind-task-goal.md`; `references/kind-scope.md`; `references/kind-done-contract.md`; `references/workflow-anatomy.md`; `references/authoring-style.md`; `ws:1-projects/build-ignite/system-definition/primer.md`.
</scope>

<done-contract>
Done when, checkable at the edge:
- `planning/current/task-dag.md` carries one entry per task with id, one-sentence description, `after` set, i/o declaration, and done contract. (The file may exist EMPTY from spawn — existence is not the artifact; the entries are.)
- No task description needs "and" twice — the split test passes on every entry.
- The DAG is acyclic, and every `after` entry names the datum that crosses it.
- Every clause of the milestone's done contract is served by at least one task and every task serves at least one clause — the trace recorded in the draft.
- Every task's done contract carries observable criteria, an outcome map covering completion and each failure scenario, and a feedback schema per failure.
- Every task row carries an execution-modality value — deterministic | agentic | interactive — and every deterministic row names its tool means — a registered CLI with at least one machine-readable output — or is preceded by a toolsmith task in the DAG.
- On a scaffolding-output run (`goal.md` `use-case:` optimize, port, or scaffold), the task authoring the produced workflow definition carries a done-contract clause requiring `workflow.md`'s frontmatter to declare `default-execution-mode:` exactly as `goal.md` carries it — and to declare none where `goal.md` carries none — with the `declared-mode-carry` check of the component-lint capability named as its edge check.
- On a relaunch, `delta-anchors check` on this seat's delta file exits 0.
  probe lane: `delta-anchors check planning/current/deltas-<seat-id>-round-<n>.md --goal .`
- Every interactive row's done contract carries its autonomous fallback arm — park durably, proceed on a stated default, or block-and-queue — named; no interactive step is load-bearing for the goal's completion in autonomous mode.

Outcome map:
- Completion → the draft seeds resource definition.
- Milestone done contract missing, or a clause two readers could score differently → FAIL back to the workflow; feedback schema {clause, why-untestable, question}. Never decompose against it.
- Milestone too entangled to cut into independently executable tasks → FAIL back; feedback schema {pieces, shared-surface, proposed-re-cut}.
</done-contract>
