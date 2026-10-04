# Tool

An executable program supplied by a component. Each tool is a [capability](capability.md) with its own folder, `capabilities/tools/<tool>/`, described by its [`<tool>.json`](tool-json.md); rbtv makes it runnable through `PATH`. The tool is not a [cognitive unit](cognitive-unit.md): it does exact, repeatable work outside the [context window](context-window.md), so only its result enters it, which lowers context load and cognitive load. A skill, rule, or command tells an agent when and how to use it.
