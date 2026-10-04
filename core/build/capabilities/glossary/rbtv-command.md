# `rbtv`

The command that manages what an agent is exposed to, by managing which [units](unit.md) it has, for the installation root and for agents, and that creates agents. The root is managed with the verbs of `rbtv` itself, such as `rbtv add`, `rbtv remove`, `rbtv configure` and `rbtv update`. An agent is managed with `rbtv agent add | remove | configure | update | list`. Each agent verb takes the agent as a name, looked up in `.rbtv/agents/`, or as a folder path. Both kinds of verb run the same code, aimed at a different folder.

- `add` and `remove` choose [units](unit.md), one by one or through a [pack](pack.md) with `--pack NAME`.
- `update SCOPE` makes the folder match its file: it generates the units the file lists and is missing, and it removes generated files that the file does not list. The scope is required: `all` or `scaffolding` do this, and `guidance` only copies the instruction file. A hand edit to an agent's `agent.json`, or a change that arrived by `git pull`, is applied by one `update`. The root's `install.json` is changed by `rbtv configure`, `rbtv add`, `rbtv remove`, and `rbtv update`, which records the files it generated.
- `agent configure` changes an agent's harness, model, effort or voice, checks harness, model and effort against `cast list`, and regenerates the files when the harness changes.
- `agent add <name>` places an agent that a component ships in `agents/<name>/` into `.rbtv/agents/<name>/`, then generates its files.
