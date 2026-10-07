# Prompt

A prompt is the standing text an agent follows across launches. In rbtv it is the body of `prompt.md`; the frontmatter is not part of the prompt. Each launch supplies a separate task.

Use the prompt for the agent's standing function, method and limits. Put one task's files, goal, scope and completion criteria in [Task](task.md). Follow [Cognitive unit](cognitive-unit.md) for shared instruction-writing requirements and [Agent](agent.md) for placement.

## Establish the launch conditions

Identify who launches the agent and two different tasks it must handle. Do not assume it receives the caller's prompt or memory. Require injected memory only when every supported launch supplies it, such as a specifically identified Ignite wake.

An interactive user can answer questions. A noninteractive launch must return a missing-input result instead of waiting for a later answer. When any supported launch is noninteractive, state what the next launch must supply. Checks needed for the conclusion must complete within that turn.

Keep instructions out of frontmatter: rbtv and Ignite launches strip it. Harness sub-agent placement instead directs the model to read the source file.

## Sections

Use these headings in order. Omit optional sections when their stated condition is absent; do not leave empty headings.

### Role

State the standing function and purpose, using the user's terms. Keep task-specific goals, procedure steps, tools and completion checks elsewhere.

Add a persona only when it determines a choice the task and procedure leave open, such as a risk preference or tie-breaker. Put that standpoint in one or two sentences inside Role. A decorative voice is not a decision rule. Do not add a persona heading or repeat the task's completion criteria.

### Navigation

Include this section when work extends beyond the agent's own folder. State that these workspace paths start at the installation root, then list the stable paths. Do not use the current working folder as an implicit base: an rbtv launch works in the agent folder, while a harness sub-agent may start elsewhere.

Do not put one task's filenames or one machine's absolute paths here. This section is author-written guidance, not a record parsed by the installer.

### Procedure

Write the standing method in execution order. State branch conditions, actions and missing-input behavior. Order steps that change the same file or record. Put exact checks and their tools here, not in Constraints. When another task consumes a result, name the file or record it can read without retaining this agent.

Read a capability at the step that needs it instead of copying its method. Capability paths start at the repository root or `.rbtv/`, so rbtv can derive a path for both copied and source-read prompts. Workspace navigation and capability source paths have different bases; label them accordingly.

A prompt is not an entry point and has no routing table. Its procedure directly names each conditional reading. Do not paste the caller's prompt or memory. A dependency listed in `agent.json` may be absent in harness-sub-agent placement; state the next action instead of assuming that placement installed it.

### Constraints

Include only standing limits that require judgment and are not already procedure steps. State the prohibited behavior and the alternative action. Include its reason when the authoring standard requires one, rather than adding a reason by format.

Keep one-task limits in the task. Put tool-enforced checks in Procedure. Combine limits on the same behavior instead of restating them in several sections.

## Template

```markdown
---
name: <same name as folder and agent record>
---

## Role
<Standing function and purpose; decision-shaping standpoint only if needed.>

## Navigation
<Paths from the installation root; omit when work stays in the agent folder.>

## Procedure
<Standing method, branches, inputs, checks and conditional capability readings.>

## Constraints
<Standing limits and alternative actions; omit when none remain.>
```

The [prompt-frontmatter schema](../templates/prompt.schema.json) owns the permitted fields. Do not add model settings, tool permissions or a description to this frontmatter.

## Review and test

Read all sections together and remove conflicting or repeated orders. Verify that Role applies to an unfamiliar task, paths resolve under each supported placement, and no section assumes one task's inputs.

Launch with a task not used while writing and with one required input absent. Check the function followed, paths opened, dependency handling and whether a noninteractive agent returns instead of waiting. Review the body without the caller's prompt or frontmatter. Installer acceptance does not test any of these behaviors.

Edit the source and update copied placements as Agent specifies. For an outside prompt, separate the standing body, launch task and record fields; preserve requirements while removing duplicated headings and unsupported assumptions.
