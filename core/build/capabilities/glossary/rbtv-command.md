# `rbtv`

The command that manages what an agent is exposed to, by managing which [units](cognitive-unit.md) it has, for the installation root and for agents, and that creates agents. The root is managed with the verbs of `rbtv` itself, such as `rbtv add`, `rbtv remove`, `rbtv configure` and `rbtv update`. An agent is managed with `rbtv agent add | remove | configure | update | list`. Each agent verb takes the agent as a name, looked up in `.rbtv/agents/`, or as a folder path. Both kinds of verb run the same code, aimed at a different folder.

- `add` and `remove` choose units, one by one or through a [pack](pack.md) with `--pack NAME`.
- `update` makes the folder match its file: it generates the units the file lists and is missing, and it removes generated files that the file does not list. A hand edit to the file, or a change that arrived by `git pull`, is applied by one `update`.
- `agent configure` changes an agent's harness, model and effort, checks them against `cast list`, and regenerates the files when the harness changes.
- `agent add <name>` places an agent that a component ships in `agents/<name>/` into `.rbtv/agents/<name>/`, then generates its files.

The command reads each [`<module>.json`](module-json.md) and [`<component>.json`](component-json.md), identifies what a component offers from the folders its files sit in, checks each file's frontmatter against its [schema](schema.md), writes the files of the selected harness, and makes declared tools available on `PATH`. It also creates and maintains the installation root's `.rbtv/` structure and the user's [`~/.rbtv/`](rbtv-home-folder.md). Per-unit generated files carry `rbtv-managed`; shared files are owned through booked keys or fenced sections; guidance copies carry a generated banner; PATH shortcuts are recorded in [`~/.rbtv/path-owners.json`](path-owners-json.md). The [root's record](install-json.md) and each [agent's record](agent-json.md) track the units and the generated files.
