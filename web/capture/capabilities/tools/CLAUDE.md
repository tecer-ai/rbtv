# capture tools

This folder holds the tool of the `capture` component: `capture-cli` (fetches a URL and extracts it to clean text). The tool has its record here; its program is at the path the record's `entry` names, in `../capture/`. The tool has no page. A tool's record, tests, data, its page `<tool>/<tool>.md` and its `documentation/` folder belong here. Prose methods belong in `../methods/`; glossary entries belong in `../glossary/`.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md) | The sequence for designing, building and testing a command: job and boundary, cold observation, interface specification, build, verification | Keep a command usable by a person and an agent | adding a tool to this component, or changing a verb, an option, help text, output or an error message of `capture-cli` |
