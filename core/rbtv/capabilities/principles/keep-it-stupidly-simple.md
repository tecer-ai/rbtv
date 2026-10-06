# Keep it stupidly simple

Build the simplest design that meets the stated need. Keep every required part and add nothing for a need nobody has stated.

Apply this before adding or keeping a file, folder, field, option, step, task, agent, module or component. A need is stated by the user or the task; a possible future need is not a requirement.

## Choose the design

1. Name the required result. Use existing files, tools and components whose purpose already covers it.
2. Keep a part when removing it would lose a requirement or a necessary decision. Remove parts that serve neither. Fewer files or words is not sufficient evidence of a simpler design.
3. Do not add options for a value with one required use. Use that value directly. Add a second supported case when it is needed.
4. Give each task, cognitive unit, agent and component one purpose. Split work when its results can be judged independently; do not split to meet a file or step count. Related limits serving one purpose stay together.
5. Run independent tasks in parallel only when they do not change the same file or record. Order tasks that share writes or consume one another's results. Pass reusable results as files or records rather than keeping the producing agent involved.

A different file type or exposure method does not justify a new component. Use [Choosing where to build](../choosing-where-to-build.md) for placement. Use [Nested exposure](../nested-exposure.md) when capabilities share a purpose or the same documents. Do not combine unrelated purposes merely to reduce the number of entry points.

## Reduce unnecessary decisions

[Cognitive load](../glossary/context-window.md) includes the effort required to interpret instructions and decide how to follow them. Short instructions can impose unnecessary work when they leave the agent to invent a criterion.

Settle choices that do not depend on the task while writing the instructions. Name the method to use instead of presenting several equivalent methods. Do not ask the reader to reconsider a choice the user or preceding page already settled.

When the choice depends on the task, state:

- the default action;
- the observable condition that changes it, and the action for that condition;
- the source of any evidence the decision requires;
- what to do when that evidence is missing or conflicting.

Keep only the conditions that produce different actions. Do not turn these authoring checks into a checklist the reader must complete on every task. When no fixed condition can settle a decision, name the tradeoff and the result it must preserve; do not claim that the judgment is deterministic.

For example, replace “choose the best report format” with “use the project template; if none exists, write the result followed by evidence and remaining questions.” The author settles the general choice; the reader checks whether a template exists.

Use [Deterministic first](deterministic-first.md) for exact computations and checks. Use [Progressive disclosure](progressive-disclosure.md) to decide when guidance reaches the agent. Use [Scaffolding language](../glossary/scaffolding-language.md) for sentence wording, reasons and examples. Do not repeat those methods here or in each kind's entry.

## Review the whole use case

Read the pages an agent will receive together. Check that they do not ask it to choose twice, reconstruct an omitted requirement, or reconcile contradictory instructions. When two principles apply, choose the design with the fewest parts and decisions that satisfies both and retains every stated requirement.

Existing parts receive the same review as new parts. An outside document's structure is not itself a requirement. Do not keep an obsolete file or name beside its replacement to defer updating callers.

When changing this principle, test a design containing a missing requirement, an unused option and two unrelated purposes. The revision must restore the requirement, remove the option and separate the purposes. Also check a shared-purpose set of capabilities against Nested exposure. Installer acceptance does not establish any of these results.
