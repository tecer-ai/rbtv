---
id: define-resources
description: "Shop capability cards for every task's means; assign resources, permissions, restrictions per seat; plan toolsmith tasks as early DAG nodes for missing means"
---

<task-goal>
Equip the seeded task DAG completely — every task's means shopped from the capability cards or planned as an early toolsmith task, and resources, permissions, and restrictions assigned per seat at the smallest sufficient grant.
</task-goal>

<scope>
- Read: the task-DAG draft at `planning/current/task-dag.md`; the capability-cards output; the guides named in this task's Guides bullet.
- Write: the resourced task-DAG draft at `planning/current/resourced-plan.md`, relative to the goal folder — nothing else. The goal's `planning/` subtree is read-write for you. On a relaunch driven by a route-back, additionally write `planning/current/deltas-<seat-id>-round-<n>.md` in the `delta-anchors` format — every `from` block copied verbatim **out of the target file you name**, never out of `task-dag.md`, `resourced-plan.md`, a route-back brief, or your own recollection. Run `delta-anchors check` on it before you report done; a file with findings is not a returned repair.
- **Guides — read whole before writing:** `references/kind-capability.md`; `references/kind-permissions.md`; `references/kind-restrictions.md`; `references/component-anatomy.md`; `references/exposure.md`; `references/authoring-style.md`.
</scope>

<done-contract>
Done when, checkable at the edge:
- `planning/current/resourced-plan.md` carries every task entry with its assigned resources, permissions, and restrictions. (The file may exist EMPTY from spawn — existence is not the artifact; the entries are.)
- Every means named by any task is matched to a capability card (card id recorded) or covered by a toolsmith task — zero means left unassigned.
- Every toolsmith task is ordered by `after` edges before every task consuming its product, and its done contract includes scaffolding registration and exposure.
- Every toolsmith task names the create-CLI capability (the CLI-creation skill) as its means and specifies its CLI's machine-readable output.
- Every toolsmith task's body carries the consumer-derived requirements — per consuming task, the operations, inputs, and outputs its work needs from the tool — sufficient for the toolsmith to build from the task text alone.
- Every permission row is traceable to a task step that needs it; per seat, write scope is no wider than read scope.
- On a relaunch, `delta-anchors check` on this seat's delta file exits 0.
  probe lane: `delta-anchors check planning/current/deltas-<seat-id>-round-<n>.md --goal .`

Outcome map:
- Completion → the resourced draft seeds assembly.
- A means neither shoppable nor buildable (needs an owner decision or an external system) → FAIL back to the workflow, the owner question parked durably as a message addressed to the reserved `owner` token; feedback schema {task, means, why-unresolvable, options}.
- A task whose means cannot be stated because the task itself is ambiguous → route back to task definition; feedback schema {task, ambiguity}.
</done-contract>
