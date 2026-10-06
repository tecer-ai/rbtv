# `runtime/`

`.rbtv/runtime/` holds operational data that components create while running. An agent’s live data stays in its own [agent folder](agent.md) instead, so the agent remains self-contained.

Write component runtime data to its documented location here, not to component source or [mirror/](mirror.md). User-selected settings belong in [config/](config.md). For records that software reads, use fixed fields defined by the consumer rather than prose that another agent must interpret.

Exercise the operation that writes the data and the operation that reads it. Check that both use the same location and that running the component does not create a second copy in source or the mirror.
