# Hook

A command a harness runs when an event happens, such as a tool use or the end of a turn. A component supplies each hook as one file in its `hooks/` folder, `<hook>.json`, in rbtv's own format; the [rbtv command](rbtv-command.md) writes it into the hook settings of Claude Code and Codex, which share Claude Code's event names. OpenCode receives no hooks. A hook is not a [cognitive unit](cognitive-unit.md): like a [tool](tool.md), it acts outside the context window. It has its own [exposure method](exposure-method.md), so it has its own folder.
