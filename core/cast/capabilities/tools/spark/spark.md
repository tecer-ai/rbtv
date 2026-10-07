# spark

`spark` opens an rbtv agent in this terminal, for a person. It is a thin layer over [cast](../cast/cast.md): it finds the agent, prints what it is about to open and starts `cast --agent NAME --headed`. `spark -h` owns the grammar and options; this page states what each form returns and what a change to the program must keep.

## What each form returns

`spark AGENT` prints the agent's folder, harness, model and effort, then starts `cast --agent NAME --headed` with a one-line greeting. It passes no harness, model or effort, so cast reads them from `agent.json`. It needs `cast` on PATH and finds the agent the same way cast does: a name or a path. With `--target FOLDER`, AGENT is a name among the agents of FOLDER (the three folders `cast list --target` takes), and spark hands cast that agent's folder, since a launch takes no `--target`.

- `--dry-run` prints the cast command and launches nothing; `--dry-run --json` prints one JSON value with `agent`, `home` and `cast`. A real launch ignores `--json`.
- Refusals, exit 1: no agent by that name or path, `agent.json` unreadable or missing, `prompt.md` missing, `cast` not on PATH, or an unknown option.

`spark list [AGENT]` shows the agents spark can open by name, or one of them in full: the list of `cast list --agents`, read in the same process, so it needs no `cast` on PATH and opens nothing. Showing what is installed in an agent needs `rbtv` on PATH. The first argument that is not an option decides the form, so `list` is never taken as an agent name: an agent whose name is `list` is opened by its path. `spark list --target FOLDER` shows the agents of FOLDER.

- Refusals, exit 1: `--dry-run`, more than one agent, an agent that is not found or cannot be launched, or an unknown option. A refusal is text on standard error and leaves standard output empty, with or without `--json`.

## Layout

| File | What it owns |
|---|---|
| `capabilities/tools/spark/spark.js` | both forms: the terminal handoff and `spark list` |
| `capabilities/tools/spark/spark.json` | the tool record: the name `spark`, its listing description and the executable `spark.js` |
| `capabilities/tools/spark/test_spark.js` | the suite; it puts a recording `cast` on PATH, so no harness is launched |

spark keeps no copy of what cast knows. It loads three modules of `capabilities/tools/cast/lib/`: `agent.js` (where an agent's folder is and how `agent.json` is read), `agent-list.js` (the list) and `win-exec.js` (starting `cast` on Windows). Change those in cast, described in [cast](../cast/cast.md), Layout; a change there needs both suites run.

## Self-check

```
node capabilities/tools/spark/test_spark.js     # -> test_spark: ok
```
