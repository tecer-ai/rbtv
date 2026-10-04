# `<tool>.json`

The [folder artifact](<../_under-evaluation/guides/folder artifacts/glossary/folder-artifact.md>) holding each [tool](tool.md)'s record, named after the tool: `capabilities/tools/<tool>/<tool>.json`. The `rbtv` command reads it for:

- The tool's name.
- A one-line description, which rbtv uses to tell agents the tool exists.
- Its entry: the program file rbtv places on `PATH` under the tool's name.
