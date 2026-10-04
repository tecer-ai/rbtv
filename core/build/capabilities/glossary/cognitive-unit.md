# Cognitive unit

Text an agent reads that shapes its cognition: it directs what the model attends to and how it reasons. Cognitive units are written in files — a whole file or a section of one — and organized in folders. Folders belong to them: an agent does not read a folder, but the folder decides what reaches its [context window](context-window.md), through the [folder instructions](folder-instructions.md) and [folder artifacts](folder-artifact.md) it holds and the paths the agent navigates. Together they are the toolkit an agent works with: its prompt, its skills, rules and commands, folder instructions, folder artifacts, and the folders that hold them. A file only programs read is not a cognitive unit; one that agents and programs both read, such as an agent file's frontmatter, is. A [tool](tool.md) is not a cognitive unit: it shapes the context window only indirectly, by keeping work out of it.

Cognitive units may:

- Form an agent's [prompt](prompt.md), such as a [role](role.md) or [procedure](procedure.md).
- Be exposed as a [skill](skill.md), [rule](rule.md), or [command](command.md).
- Be kept as a [capability](capability.md) that a skill or command routes to.
- Arrive with a task as its [scope](scope.md) and [done contract](done-contract.md).

An agent's cognitive units, with its hooks, MCP servers and tools, make up its [scaffolding](scaffolding.md).
