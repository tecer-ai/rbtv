# `<tool>.json`

The [folder artifact](folder-artifact.md) containing each [tool](tool.md)'s record, named after the tool: `capabilities/tools/<tool>/<tool>.json`. The `rbtv` CLI reads it for:

- The tool's name.
- A one-line description, which rbtv uses to tell agents the tool exists.
- Its entry: the file of the tool's CLI that rbtv places on `PATH` under the tool's name.
