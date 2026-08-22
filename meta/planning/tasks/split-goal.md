---
id: split-goal
description: "Produce the pieces draft at a fixed path on the planning run surface — independent, complete pieces"
---

<task-goal>
Split the ratified goal into pieces that are independent (they parallelize) and complete (nothing lost, nothing counted twice), granular enough for milestones to be built from them.
</task-goal>

<scope>
- **Read:** `goal.md` in the goal folder.
- **Write:** the pieces draft at `planning/current/pieces-draft.md`, relative to the goal folder — nothing else.
</scope>

<done-contract>
Done criteria — all must hold:

- The pieces draft exists at `planning/current/pieces-draft.md`, one entry per piece: a name, what it delivers, the definition-of-done clauses it serves, and what crosses between it and other pieces.
- Every definition-of-done clause of `goal.md` maps to at least one piece; no deliverable is claimed by two pieces.
- Every inter-piece dependency names the datum that crosses it.

Outcome map:

- **Complete** → the draft seeds the DAG-structuring step; nothing downstream depends on it after `milestones.csv` lands.
- **`goal.md` missing or its definition of done unratified** → stop and route back to the interview task. Feedback schema: what is missing or unratified.
- **A downstream gap is routed back** (a clause no piece serves, an entangled pair) → rework the draft. Feedback schema: the gap, named clause-by-clause or pair-by-pair.
</done-contract>
