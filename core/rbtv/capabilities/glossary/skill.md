# Skill

A skill is a cognitive unit an agent opens when its description matches the task. The agent reads its instructions after deciding to open it.

Use a skill when an agent needs instructions for a particular kind of task but does not need them on every task. [Choosing what to build](../methods/choosing-what-to-build.md) settles this choice before authoring.

## Source and installed file

Write `skills/<name>.md` in the owning component. The [skill schema](../templates/skill.schema.json) governs its frontmatter. The installer writes a copy for each harness: the name and description, then the source body with each link made the absolute path of its target. Supporting resources stay in the source; they are not copied beside the installed file.

This differs from an outside skill packaged as a folder. A whole-folder skill uses the separate [Self-contained skill](self-contained-skill.md) convention.

## Build the skill

Follow [Cognitive unit](cognitive-unit.md) for the body: purpose, inputs, missing-input behavior, tools and shared instructions. Add the skill-specific requirements below.

- **Make discovery work without the name.** Establish one task that needs the skill, another supported task phrased differently and a nearby task that must not select it. The description must separate those cases, and its ALWAYS LOAD WHEN quotes the phrases those tasks carry, as [Routing table](routing-table.md) states.
- **Take inputs from the task.** Do not require arguments typed after the skill's name. The agent may have selected it without a named invocation. State the action for missing inputs in the body.
- **Reach supporting pages through links.** Write a Markdown link from the source skill to the capability that contains the instructions, relative to the source file. The installed copy sits in another folder: rbtv rewrites a link for it, and leaves a path written in a code span unresolved.
- **Keep enforcement at the right place.** A body instruction runs only after the skill is opened. A requirement that must hold even when the skill is not opened cannot rely on that body alone; return to Choosing what to build for the required mechanism.
- **Cover all supported work.** If the skill routes to several capabilities, its description must cover their shared purpose and all supported cases. Use [Entry point](entry-point.md) for the body and [Nested exposure](../methods/nested-exposure.md) for grouping.

Use [Routing table](routing-table.md) for the four description fields. For a skill, CONTAINS distinguishes its instructions or the choice among its capabilities; PURPOSE names the result; ALWAYS LOAD WHEN describes a task recognizable before reading the body; DO NOT LOAD WHEN names the nearest excluded task and its alternative. The exclusion describes a task that needs a different skill or does not need this skill; it does not exclude a capability this skill supports. Do not list every supporting filename or put procedure steps in the description.

Choose a name for the work, not a common word that would match unrelated requests.

```markdown
---
name: <work-name>
description: "CONTAINS: <instructions or supported choice> PURPOSE: <result> ALWAYS LOAD WHEN: <task condition> DO NOT LOAD WHEN: <nearest excluded task>"
---

<What the skill enables the agent to do.>

<Instructions, inputs and missing-input actions.>

<Direct readings at the steps that need them; a routing table only for a choice among several targets.>
```

## Edit or convert

Change the source, then regenerate the installed copy; follow [rbtv CLI](rbtv-cli.md). Until then the agent reads the earlier body, name and description.

When converting an outside skill, retain its purpose and operational requirements. Put its instructions in this file and classify supporting content through Choosing what to build. Do not copy supporting resources beside the installed file. Remove unsupported metadata rather than pretending it controls rbtv discovery, tool access or argument passing. Record how each requirement is preserved.

## Verify

Test selection as [Running blind seats](../methods/running-blind-seats.md) states: ten headless seats of the weakest selected model on a task that should select the skill, and ten on the nearest task that should not, neither naming it, in an installation that lists the skill beside its neighbours. The description passes when every seat of the first task opens the skill before its first edit and no seat of the second opens it. One seat per task cannot show the rate: a description that selects one time in two passes or fails one seat by chance. Then test the body without arguments after the skill name and with one required input missing. Check the result and actual paths followed.

Run installer validation for the frontmatter. This verifies the checked fields, not discovery or the quality of the instructions.
