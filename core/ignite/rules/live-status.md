---
name: live-status
description: "CONTAINS: how an Ignite agent declares the kind of work it is doing and how its result sets the task state the owner sees in Slack PURPOSE: keep a non-interactive agent's work visible to the owner while it runs ALWAYS LOAD WHEN: the agent runs Ignite turns DO NOT LOAD WHEN: the agent is only opened by a person in a terminal"
---

# Live status

The owner cannot see your terminal. On the latest message of your conversation's thread, your replies included, Ignite shows the owner a [live status](core/ignite/capabilities/glossary/live-status.md): the system's state, then yours while you work, or the task's once your replies are delivered. Every turn starts as `working`.

When you move to a different kind of work, declare it before you start that work, with a foreground command:

| Command | When |
|---|---|
| `ignite status gathering` | Reading, searching, collecting what the work needs |
| `ignite status thinking` | Analysing, comparing, deciding, planning |
| `ignite status making` | Writing, building, editing files |
| `ignite status orchestrating` | Launching and coordinating workers |

Declare a change of kind, not every step. A declaration is not a reply: the owner still gets your answer only through `replies`.

The task state comes from RESULT_FILE, not from this command: `completed` shows done, `waiting_owner` a question, `stopped` stopped. When the work is done with problems worth a follow-up, add `"caveats": true` to a `completed` result. `"caveats": true` on any other disposition fails the turn; `false`, `null` or no `caveats` means none. A `waiting_workers` result shows you waiting until the next turn of this conversation starts.

When an earlier owner message of this conversation has changed state since its turn finished (its question answered, its follow-up done), set its task state with `ignite status --task done|caveats|question|stopped --message <its Slack timestamp>`. The history gives each owner message's Slack timestamp; Ignite puts the task on the message that shows it. `ignite status -h` gives the rest.
