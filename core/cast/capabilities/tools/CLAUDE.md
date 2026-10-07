# cast tools

This folder holds the tools of the `cast` component: `cast` (launches one agent turn on any harness and model, routes a task to a model and selects the models an installation launches) and `spark` (opens an agent in a terminal for a person, through cast). The program behind `cast api` is in `cast/api/` and is documented in the cast page. A tool's program, record, tests, data, its page `<tool>/<tool>.md` and its `documentation/` folder belong here. Prose methods belong in `../methods/`; glossary entries belong in `../glossary/`.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [cast](cast/cast.md) | Launch, resume and session forms, effort mapping, agent launches, the fallback of a launch, `cast route`, `cast api`, exit codes, the layout of `cast/` and its self-check | Change or review cast without breaking what a caller receives | changing, reviewing or debugging a file under `cast/`, or reading what a cast command returned |
| [Personalizing the model catalog](cast/documentation/personalizing-the-model-catalog.md) | Selecting models for an installation, editing routing columns, supporting a new model, the order on a live installation and a second machine | Change an installation's models or the models cast supports | adding, removing or replacing a model, or editing a `models.csv` |
| [spark](spark/spark.md) | What each `spark` form returns, its refusals, the layout of `spark/` and its self-check | Change or review spark without breaking what a person sees | changing, reviewing or debugging a file under `spark/` |
| [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md) | The sequence for designing, building and testing a command: job and boundary, cold observation, interface specification, build, verification | Keep a command usable by a person and an agent | adding or changing a verb, an option, help text, output or an error message of `cast` or `spark` |
