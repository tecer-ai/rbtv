# Rule

A rule is a cognitive unit supplied on every task where it is installed. In Claude Code and OpenCode the agent does not choose whether to load its body. Codex has no such channel: there the rule is a listed skill whose description tells the model to open it when a session starts. In every harness the agent acts on the body only when its condition applies.

Use a rule for behavior that must be available across tasks and folders, without relying on the agent to select a skill. If the requirement belongs only to one folder, revisit [Choosing what to build](../choosing-what-to-build.md).

## Source and delivery

Write `rules/<name>.md` using the [rule schema](../templates/rule.schema.json). Claude Code receives a copy and strips its frontmatter. OpenCode loads the same copy, which rbtv lists in `opencode.json`. Codex receives the body as a skill under a description rbtv generates from the rule's name, so the name must differ from every skill installed beside it. The acting agent cannot rely on the rule's own description for conditions or inputs. [Harness](harness.md) states what each harness loads.

The description selects which agents should have the rule installed. It does not select individual tasks. A Codex permission-rule file is a different mechanism, and rbtv does not carry Claude Code path-list frontmatter as the rule's acting condition.

## Write the body

Follow [Cognitive unit](cognitive-unit.md) for shared instructions. At the start, state the observable condition, the action when it applies and what to do otherwise. “Always active” does not establish when a conditional behavior is required.

For example: “When replying to the user in chat, lead with the decision. Do not apply this chat format to files you write.” Both cases are explicit without a ritual on every task.

Put all required inputs and exact checks in the body. Keep only the guidance needed before a conditional method starts; place that method in a [Capability](capability.md) and route to it at the condition. Use [Entry point](entry-point.md) for the split and [Routing table](routing-table.md) for rows. Capability paths start at the repository root or `.rbtv/`, not beside the source rule, so the installer can resolve them after placement.

The body is present on every task in Claude Code and OpenCode, and in Codex once the model opens it. Do not repeat a task-specific method there. See [Harness](harness.md) and [rbtv CLI](rbtv-cli.md) for delivery limits.

Read the other rules and prompt the same agent receives. Give a behavior one owner and resolve in-scope contradictions together. Do not add a second independent purpose to the rule.

## Describe the installation choice

Use the four description fields from Routing table. CONTAINS distinguishes its guidance; PURPOSE identifies the standing behavior; ALWAYS LOAD WHEN identifies the kind of agent work that needs it installed; DO NOT LOAD WHEN identifies a neighboring installation choice. Do not substitute a single task trigger for the installation condition. Keep the first two fields distinguishable even in a shortened listing.

```markdown
---
name: <behavior>
description: "CONTAINS: <guidance> PURPOSE: <standing behavior> ALWAYS LOAD WHEN: <agent work needing this rule> DO NOT LOAD WHEN: <neighboring installation case>"
---

<Observable condition, action when true, and action otherwise.>
<Shared instructions or conditional routes, without duplicating their methods.>
```

## Edit, convert and test

Edit the source and regenerate the installed copy before treating the behavior as changed. Keep the description consistent with the body. On conversion, move acting conditions out of frontmatter into the body; classify non-rule content through Choosing what to build.

Test the body without its description on a task where the condition occurs and another-folder task where it does not. Inspect the behavior and any capability path followed. Test the description separately for installation selection. Validate the frontmatter, but do not treat that as evidence that the agent follows the rule.
