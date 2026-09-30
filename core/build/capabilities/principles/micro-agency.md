# Micro agency

**Statement.** Give each task and each cognitive unit one purpose whose result can be judged on its own, even over the convenience of bundling related work.

**Rationale.** One purpose keeps attention on that purpose, and a result with one purpose can be checked. A unit that bundles an unrelated purpose cannot be selected or checked for one of them without dragging the other. Several purposes in one unit or task are cognitive load: the model splits its attention between them and drifts from the one the task needs ([context window](../glossary/context-window.md)).

**Implications**

- Give each [task](../glossary/task.md) one purpose, with a [done contract](../glossary/done-contract.md) that can be judged from its result alone. If the done contract lists independent results, split the task.
- Give each [cognitive unit](../glossary/cognitive-unit.md) one purpose. A unit that needs "and also" for an unrelated purpose is two units.
- Split only when the pieces are independent and each has its own judgeable result. Never split to reach a number of files or steps. A question that one file read or one tool run answers stays one task. A set of limits that serve one purpose stays one [constraints](../glossary/constraints.md) unit.
- When another task uses a result, pass it as a file or record that task can read without the agent that produced it.
- Run independent tasks in parallel only when no two of them change the same file or record. Order tasks when one uses another's result, or when they would change the same file or record.
