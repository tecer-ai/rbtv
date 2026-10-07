# ignite tools

This folder holds the tool of the `ignite` component: `ignite` (runs and administers Ignite agents: their turns, schedules, work queue and settings). A tool's program, record, tests, data, its page `<tool>/<tool>.md` and its `documentation/` folder belong here. Prose methods belong in `../methods/`; glossary entries belong in `../glossary/`.

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [ignite](ignite/ignite.md) | What `ignite` is, what its waking service does and where its program is | Start any work on the tool from its own description | changing, reviewing or debugging a file under `ignite/` |
| [Ignite architecture](ignite/documentation/architecture.md) | What each file of `ignite/` does, the commands and units Ignite exposes, the configuration and turn contracts | Find the file that owns a behavior and the contract it must keep | changing or reviewing Ignite's code, its configuration fields or the turn request and result |
| [Operator runbook](ignite/documentation/runbook.md) | Deploy, status, the Dreamer, inspection, posting, board writes, turn-memory recovery, repairing a hold, known behaviour | Operate a running service and repair its state | deploying, checking or repairing a running Ignite service, or acting on one agent's stored state by hand |
| [Testing Ignite](../methods/testing-ignite.md) | The checks a change to Ignite must pass and how to run them | Verify a change before it is called done | a file under `ignite/` has changed and the change is about to be reported or deployed |
| [Building a command-line interface](../../../../meta/code/capabilities/methods/building-a-cli.md) | The sequence for designing, building and testing a command: job and boundary, cold observation, interface specification, build, verification | Keep a command usable by a person and an agent | adding or changing a verb, an option, help text, output or an error message of `ignite` |
