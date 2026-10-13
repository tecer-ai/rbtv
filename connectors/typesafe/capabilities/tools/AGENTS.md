# typesafe tools

This folder holds the tool of the `typesafe` component: `typesafe` (TypeSafe typed judgments from one command: ask, yesno, choice, score, models). A tool's program, record, tests, data, its page `<tool>/<tool>.md` and its `documentation/` folder belong here. Prose methods belong in `../methods/`; glossary entries belong in `../glossary/`.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [typesafe](typesafe/typesafe.md) | What the `typesafe` CLI is: its verbs and the two service operations behind them, key resolution, retries and limits, and its self-check | Start any work on the tool from its own description | changing, reviewing or debugging a file under `typesafe/` |
| [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md) | The sequence for designing, building and testing a command: job and boundary, cold observation, interface specification, build, verification | Keep a command usable by a person and an agent | adding or changing a verb, an option, help text, output or an error message of `typesafe` |
