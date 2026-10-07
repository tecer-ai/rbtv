# `runtime/`

`.rbtv/runtime/` holds operational data: what a program writes while running in order to work, such as state, caches, locks and logs. Every component and every custom tool writes that data in one folder named exactly as its component, `.rbtv/runtime/<component>/`, the naming [config/](config.md) uses for settings. The tools of one component share the folder and name their files by purpose.

The program that writes creates `.rbtv/runtime/<component>/` on first use; rbtv does not prepare it. Never write operational data beside the program, in component source or in [mirror/](mirror.md).

Two kinds of data do not belong here. What the user chose or supplied belongs in config/. An agent’s live data stays in its own [agent folder](agent.md), so the agent remains self-contained.

For records that software reads, use fixed fields defined by the consumer rather than prose that another agent must interpret.

Exercise the operation that writes the data and the operation that reads it. Check that both use the same location under `.rbtv/runtime/<component>/`, that a first run in an installation without that folder creates it, and that running the component does not create a second copy in source or the mirror.
