# `.rbtv/`

`.rbtv/` is an installation’s folder for local component source, configuration, agents found by name, operational data and shared memory. It is separate from the user’s [rbtv home folder](rbtv-home-folder.md), which serves several installations.

Place material through its owning entry:

- Read [Mirror](mirror.md) for local component source and self-contained skills.
- Read [Config](config.md) for installation settings and the root installation record.
- Read [Agent](agent.md) for `agents/`, which locates agents addressed by name; an explicit path can identify an agent elsewhere.
- Read [Runtime](runtime.md) for component operational data; agent live data stays in the agent’s own folder.
- Read [Memory](memory.md) for installation-wide memory.

Use the owning entry’s operations. [rbtv CLI](rbtv-cli.md) refreshes installed files from their source and selections; it does not repair arbitrary component configuration or runtime data. Edit author-maintained source or settings, not generated copies, then apply the refresh required for that change.

Check placement against the relevant entry and verify the consuming operation. Merely having a `.rbtv/` directory does not prove an installation is configured or that its generated files match its record.
