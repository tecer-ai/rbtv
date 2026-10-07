# ignite

`ignite` runs and administers Ignite agents. Its waking service keeps one process per installation that receives each agent's Slack messages, schedules and queued work, and runs one turn at a time for each through `ignite turn`, with the agent's own harness, model and effort. The same program gives a person or an agent the verbs that connect an agent, inspect its turns and change its schedules, work queue, board and remembered facts. `ignite -h` and each verb's `-h` own the grammar and options. The program is `cli.js` in this folder; the waking service runs on Linux only.

## Read for this work

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [Ignite architecture](documentation/architecture.md) | What each file of this folder does, the commands and units Ignite exposes, the configuration and turn contracts | Find the file that owns a behavior and the contract it must keep | changing or reviewing Ignite's code, its configuration fields or the turn request and result |
| [Operator runbook](documentation/runbook.md) | Deploy, status, the Dreamer, inspection, posting, board writes, turn-memory recovery, repairing a hold, known behaviour | Operate a running service and repair its state | deploying, checking or repairing a running Ignite service, or acting on one agent's stored state by hand |

The terms these pages use (memory, board, Dreamer, Ignite configuration and the memory records) have their entries in `core/ignite/capabilities/glossary/`.

## After a change

After any change to a file under `core/ignite/`, or to the cast code Ignite imports, follow [Testing Ignite after a change](../../methods/testing-ignite.md) with the list of changed files before calling the change done. It names the suites the change obliges, the proof required on Linux and on Windows, and the deploy and live checks.
