# Command

A command is a cognitive unit a human invokes by typing its name. The agent reads the command's instructions after invocation.

Use a command when the human must choose when an action starts and supply its inputs with that invocation. Write the body using [Cognitive unit](cognitive-unit.md); this page adds the invocation requirements.

## File and loading

Write `commands/<name>.md` with frontmatter matching the [command schema](../templates/command.schema.json). The installer writes a copy for each harness: the source body with each link made the absolute path of its target. It does not expand argument placeholders there.

The Claude Code and OpenCode copies carry the description. The Codex copy does not, so the name must identify the action without relying on the description. Check [Harness](harness.md) for platform details.

## Write for an invocation already made

Name the action and take inputs from the text typed after the command name. Do not use `$ARGUMENTS` or another substitution placeholder in the source; the agent reads it as text. If an input is absent, stop and say what the next invocation must include. Do not ask the user to choose the action again or wait for inputs the invocation was meant to supply.

Choose a name specific to the action and distinct from built-in harness commands. A colliding name can replace or override a built-in even when the installer accepts it.

Use [Routing table](routing-table.md) for the description. PURPOSE includes every input the human must type, in the human's terms. ALWAYS LOAD WHEN identifies the action for which to invoke it; DO NOT LOAD WHEN identifies the nearest different action and its alternative. Keep tool invocations and procedure steps in the body, not in the description the human uses to choose.

When the action must also run without a human invocation, put its reusable instructions in a [Capability](capability.md). The command supplies the invocation's inputs and directs the agent there. Use [Entry point](entry-point.md) for a routing body and [Nested exposure](../nested-exposure.md) for grouping capabilities. Any input that selects a route must be part of the invocation, not a second menu after it.

## Template

```markdown
---
name: <specific-action>
description: "CONTAINS: <instructions> PURPOSE: <result and typed inputs> ALWAYS LOAD WHEN: <invocation situation> DO NOT LOAD WHEN: <nearest different action>"
---

<Perform the action. Take the named inputs from the invocation.>
<If a required input is absent, stop and name what the next invocation must include.>
<Instructions or conditional capability routes.>
```

## Edit, convert and test

Edit the source, then regenerate the installed copy, following [rbtv CLI](rbtv-cli.md). Until then an invocation reads the earlier body and description. On conversion, replace argument placeholders with instructions to read invocation text and preserve each input in the description. Classify other content using [Choosing what to build](../choosing-what-to-build.md).

Test the name and description without revealing the body. A human should select it for the intended action, avoid it for a neighboring action and supply its inputs. Then run a complete invocation and one missing an input. Check the action and missing-input result. Validate the frontmatter separately; acceptance does not establish usability or behavior.
