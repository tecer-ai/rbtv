# document tools

This folder holds the tools of the `document` component: `converter-cli` and `posh-cli`. Each tool has its record here; its program is at the path the record's `entry` names, in `../converter/tool/` and `../posh/tool/`. No tool of this component has a page. A tool's record, tests, data, its page `<tool>/<tool>.md` and its `documentation/` folder belong here. Prose methods belong in `../methods/`; glossary entries belong in `../glossary/`.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md) | The sequence for designing, building and testing a command: job and boundary, cold observation, interface specification, build, verification | Keep a command usable by a person and an agent | adding a tool to this component, or changing a verb, an option, help text, output or an error message of one |
