---
id: structure-milestone-dag
description: "Author milestones.csv — a DAG of contained, verifiable milestones with after sets, done contracts, and a planning-mode stamp per row"
---

<task-goal>
Structure the pieces into `milestones.csv` — an acyclic DAG of contained, verifiable milestones whose done contracts jointly entail the goal's definition of done.
</task-goal>

<scope>
- **Read:** the pieces draft at `planning/current/pieces-draft.md`; `goal.md` in the goal folder; the two standing context reads (the builder primer and the workflow-anatomy guide).
- **Write:** `milestones.csv` in the goal folder.
- **Guides — read whole before writing:** `ws:1-projects/build-ignite/system-definition/primer.md`; `references/workflow-anatomy.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- `milestones.csv` exists in the goal folder and parses as CSV; every row carries: milestone id, description, `after` set, done contract, `planning-mode`.
- The graph is acyclic, and every `after` entry names the datum that crosses the edge.
- Every milestone's done contract is machine-checkable — an observable, a probe, a threshold.
- `planning-mode` is `full` or `collapsed` on every row.
- Every definition-of-done clause of `goal.md` is carried by at least one milestone's contract.

Outcome map:

- **Complete** → per-milestone planning passes open per the `planning-mode` stamps (openers only read them).
- **The pieces draft has a gap or contradiction** → route back to the split task. Feedback schema: the gap, named piece by piece.
- **A cycle cannot be worked out of the graph** → FAIL back with the question parked durably for the owner — a message addressed to the reserved `owner` token on the coordination bus; the pass blocks-and-queues, disclosed, until answered (this seat opens no owner thread itself). Feedback schema: the cycle's members and the datum each of its edges carries.
</done-contract>
