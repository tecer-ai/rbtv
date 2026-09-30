# Hook

A command a harness runs when an event happens, such as a tool use or the end of a turn. A component supplies each hook as one file in its `hooks/` folder, `<hook>.json`, in rbtv's own format; the [installer](rbtv-installer.md) translates it into each harness's hook settings, and a harness without hooks receives none. A hook is not a [cognitive unit](cognitive-unit.md): like a [tool](tool.md), it acts outside the context window. It has its own [exposure method](exposure-method.md), so it has its own folder.
