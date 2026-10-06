# Cognitive unit

A cognitive unit is a set of instructions an agent follows. In rbtv, skills, rules, commands and prompts are cognitive units. There is no separate cognitive-unit file.

Use this page for their shared authoring method. Use the entry of the particular kind for how it reaches the agent and what that kind requires. [Choosing what to build](../choosing-what-to-build.md) settles the kind before this method is applied.

## Write the instructions

1. **Establish the result.** Identify what goes wrong without the instructions and the missing fact, action, limit or fallback that explains it. Consider the current task and another task the instructions must support. Keep this reasoning in the authoring record; open the finished instructions with their purpose.
2. **Write the body before its description.** Describe the work the agent must do, not the steps you took to design the instructions. The description is written from that finished work.
3. **Specify inputs and missing-input behavior.** Obtain installation-specific paths, accounts and settings from the task or configuration. For each required input, name a supplied source or a documented substitute. If neither is available, stop and identify the missing input; do not have the agent invent it.
4. **Make the decisions usable.** Follow the framework's simplicity principle: settle task-independent choices, give a default for task-dependent choices, and state the conditions and evidence that change it. Name an exact detail when a wrong value fails the task. Do not present several equivalent methods and make each reader choose again.
5. **Name tools for exact answers.** Apply [Deterministic first](../principles/deterministic-first.md). Give the tool and invocation needed for the step. Avoid relying exclusively on a tool available in only one harness when the instructions must run elsewhere.
6. **Keep shared work in one place.** Reuse an existing capability rather than copying its instructions. When several cognitive units need the same new instructions, put them in a capability and name when each caller reads it. Keep one purpose; a separate independently useful result needs its own instructions.
7. **Make findings actionable.** When the work produces a review or diagnosis, require the relevant passage or location, its consequence and the proposed correction. “This section is unclear” is not a finding a reader can act on.

Apply [Scaffolding language](scaffolding-language.md) for wording and examples. Do not reteach a familiar domain merely to fill a section. Include facts needed to perform this particular work. State current instructions rather than date-triggered changes that a later reader must interpret.

## Edit, convert and review

An edit must retain the purpose and required behavior unless the user changes them. During conversion, record where each operational requirement went. Preserve its actions, conditions, scope, limits, inputs and outputs; source headings, repeated reasons and illustrative stories are not themselves obligations. Use the language page’s conditions for retaining explanations and examples. Route content of another kind through Choosing what to build.

Review the instructions together with the other cognitive units the same agent receives. Resolve conflicting answers for the same behavior in the same authorized change. A supporting report does not replace reading the main documents being judged.

Use the concrete kind’s verification tasks as one test plan. In those runs, check the required result, missing-input behavior and use of tools for exact answers. Include any applicable description and route checks from Routing table and Entry point in the same plan; a case that covers several checks runs once. If a required test agent cannot be launched, report those checks as not run and give the reason. A reading check does not establish tested behavior.
