# rbtv tools

This folder holds the tool of the `rbtv` component: `rbtv` (installs and manages the skills, rules, commands, tools and other files rbtv provides, an installation's agents and the provider accounts a machine uses). A tool's program, record, tests, data, its page `<tool>/<tool>.md` and its `documentation/` folder belong here. Prose methods belong in `../methods/`; glossary entries belong in `../glossary/`.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [rbtv](rbtv/rbtv.md) | What `rbtv` is, how its program is divided into files and its self-check | Start any work on the tool from its own description | changing, reviewing or debugging a file under `rbtv/` |
| [Provider accounts](rbtv/documentation/providers.md) | The `rbtv providers` verbs, where a saved login lives and the providers file | Save, switch and read provider accounts | listing or switching provider logins, reading usage limits, or adding a supported provider |
| [Installer design decisions](rbtv/documentation/design-decisions.md) | The decisions in force for the installer, each with its reason | Change the installer without undoing a settled choice | changing `install.py`, `lib/`, `discovery.py` or `selftest/` |
| [Documenting a change](../methods/documenting-a-change.md) | What to update with a source change: descriptions, records, glossary entries, schemas, routes and decisions | Keep rbtv's instructions accurate in the same change as its source | a change to `rbtv` adds, alters, renames or removes a behavior, a field or a file layout |
| [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md) | The sequence for designing, building and testing a command: job and boundary, cold observation, interface specification, build, verification | Keep a command usable by a person and an agent | adding or changing a verb, an option, help text, output or an error message of `rbtv` |
