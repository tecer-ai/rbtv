# `meta`

`meta` is the [module](module.md) for how agents behave, communicate, plan and coordinate work across tasks. It includes the `plan`, `coordinate` and `final-act` skills, the swarm, panel, investigate, digest and checker methods in `coordinate`, and the handoff, loose-ends, compound, archivist and work-history methods in `final-act`. rbtv can function without these components.

Software that operates rbtv or manages, runs, launches and connects agents belongs to [core](core.md); subject-specific work belongs to its own module. Use [Choosing where to build](../methods/choosing-where-to-build.md) to place a component within those boundaries.
