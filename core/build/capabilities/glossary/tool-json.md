# `<tool>.json`

The [folder artifact](folder-artifact.md) holding each [tool](tool.md)'s record, named after the tool: `capabilities/tools/<tool>/<tool>.json`. The installer reads it for:

- The tool's name.
- A one-line description, which the installer uses to tell agents the tool exists.
- Its entry: the program file the installer places on `PATH` under the tool's name.
