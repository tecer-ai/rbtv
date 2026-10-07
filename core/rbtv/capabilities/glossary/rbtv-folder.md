# `.rbtv/`

`.rbtv/` is an installation’s folder for local component source, configuration, agents found by name, operational data and shared memory. It is separate from the user’s [rbtv home folder](rbtv-home-folder.md), which serves several installations.

It has five subfolders. Place material through the entry that owns each:

- `mirror/` holds the user’s own parts that rbtv exposes to agents: components in rbtv’s layout at its root, and shareable skill folders under `_skills/`. Read [Mirror](mirror.md), and [Self-contained skill](self-contained-skill.md) for `_skills/`.
- `config/` holds what the user chose or supplied for each component (settings, choices, credentials and keys), in `config/<component>/`. Read [Config](config.md).
- `agents/` locates rbtv agents addressed by name; an explicit path can identify an agent elsewhere. Read [Agent](agent.md).
- `runtime/` is where every component and custom tool writes its operational data, in `runtime/<component>/`; an agent’s live data stays in the agent’s own folder. Read [Runtime](runtime.md).
- `memory/` holds the installation’s general memory. Ignite generates and maintains it; users and tools do not design its layout. Read [Memory folder](memory-folder.md).

Use the owning entry’s operations. [rbtv CLI](rbtv-cli.md) refreshes installed files from their source and selections; it does not repair arbitrary component configuration or runtime data. Edit author-maintained source or settings, not generated copies, then apply the refresh required for that change.

Check placement against the relevant entry and verify the consuming operation. Merely having a `.rbtv/` directory does not prove an installation is configured or that its generated files match its record.
