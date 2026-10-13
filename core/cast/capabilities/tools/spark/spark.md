# spark

`spark` opens an rbtv agent in this terminal, for a person. It is a thin layer over [cast](../cast/cast.md): it finds the agent, prints what it is about to open and starts `cast --agent NAME --headed`; it also shows the sessions opened that way and opens one again. `spark -h` owns the grammar and options; this page states what each form returns and what a change to the program must keep.

## What each form returns

`spark AGENT` prints the agent's folder, harness, model and effort, then starts `cast --agent NAME --headed`. It passes no task, harness, model or effort: cast reads the launch values from `agent.json` and opens the session with that record's `opening` message when it has one, and with no first message otherwise. [Agent record](../../../../rbtv/capabilities/glossary/agent-json.md) defines the field; the record of an Ignite agent carries the message that has it read its board before it greets the owner. It needs `cast` on PATH and finds the agent the same way cast does: a name or a path. With `--target FOLDER`, AGENT is a name among the agents of FOLDER (the three folders `cast list --target` takes), and spark hands cast that agent's folder, since a launch takes no `--target`.

- `--dry-run` prints the cast command and launches nothing; `--dry-run --json` prints one JSON value with `agent`, `home` and `cast`. A real launch ignores `--json`.
- Refusals, exit 1: no agent by that name or path, `agent.json` unreadable or missing, `prompt.md` missing, `cast` not on PATH, or an unknown option.

`spark list [AGENT]` shows the agents spark can open by name, or one of them in full: the list of `cast list --agents`, read in the same process, so it needs no `cast` on PATH and opens nothing. Showing what is installed in an agent needs `rbtv` on PATH. The first argument that is not an option decides the form, so `list` is never taken as an agent name: an agent whose name is `list` is opened by its path. `spark list --target FOLDER` shows the agents of FOLDER.

- Refusals, exit 1: `--dry-run`, more than one agent, an agent that is not found or cannot be launched, or an unknown option. A refusal is text on standard error and leaves standard output empty, with or without `--json`.

`spark resume` shows the sessions a person opened on this machine, newest first: the ones `spark AGENT` and `cast --headed` started, which are the rows of cast's handle registry that carry a code. [cast](../cast/cast.md#the-sessions-a-person-opened) says what a row holds and how long it is kept. Each session is shown with its code, the folder name of its agent (`-` when the launch named none), harness, model, when it was opened and its launch folder; the columns are a table, or one labeled block per session on a terminal too narrow for it. It shows 5 sessions, or the `-n N` newest up to 50, and says how many are on record. `--json` prints `{on_record, sessions: [{code, agent, harness, model, opened, folder}]}`, with `agent` null where the table shows `-` and `opened` as an ISO time. No session on record is success. It needs no `cast` on PATH and opens nothing.

`spark resume CODE` prints the session's code, agent, folder, harness and model, then starts `cast resume HARNESS SESSION FOLDER --headed`, which opens the session with its history. The harness and the folder are the row's; the model and effort are those of the agent's record today, as `cast resume` reads them. Claude Code was started on an id cast chose, so the row names the session exactly. Codex and OpenCode name their session themselves: spark takes the first session they recorded for the folder from the moment of the launch, so two sessions of one of them opened in one folder in the same moment are not told apart.

- Refusals, exit 1: a code no session on record holds, more than one code, `-n` outside 1 to 50 or given with a code, an unknown option, a Codex or OpenCode session the harness recorded nothing for, or `cast` not on PATH.

## Layout

| File | What it owns |
|---|---|
| `capabilities/tools/spark/spark.js` | the three forms: the terminal handoff, `spark list` and `spark resume` |
| `capabilities/tools/spark/spark.json` | the tool record: the name `spark`, its listing description and the executable `spark.js` |
| `capabilities/tools/spark/test_spark.js` | the suite; it puts a recording `cast` on PATH, so no harness is launched |

spark keeps no copy of what cast knows. It loads five modules of `capabilities/tools/cast/lib/`: `agent.js` (where an agent's folder is and how `agent.json` is read), `agent-list.js` (the list of agents), `headed.js` (the sessions a person opened, their codes and the session each one names), `handles.js` (how long a session stays on record) and `win-exec.js` (starting `cast` on Windows). Change those in cast, described in [cast](../cast/cast.md), Layout; a change there needs both suites run.

## Self-check

```
node capabilities/tools/spark/test_spark.js     # -> test_spark: ok
```
