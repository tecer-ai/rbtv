# Scaffolding

Scaffolding is everything an [agent](agent.md) is exposed to, including its prompt, other instructions, reference material and available tools. The model and the [harness](harness.md) that runs it are separate parts of the agent.

[Cognitive units](cognitive-unit.md) are part of scaffolding, not another name for all of it. Folder instructions, hooks and tool connections also shape what the agent receives or can do.

Authored or generated describes where a file comes from, not whether its content is scaffolding. A generated pointer or copied instruction can deliver scaffolding; a file merely stored on disk has not necessarily reached the agent. Use [Harness](harness.md) when the distinction depends on what a running session loads, and [rbtv CLI](rbtv-cli.md) for installation and refresh operations.
