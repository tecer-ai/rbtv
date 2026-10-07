# `core`

`core` is the [module](module.md) for rbtv’s own operation, installation, configuration and editing, and for software that manages what agents receive, runs them, launches them or connects them to other systems. It includes the [rbtv CLI](rbtv-cli.md), Ignite, `cast` and `spark`, a tool of `cast`. A component can belong here even when rbtv does not need it to start.

Cross-task behavior, communication, planning and coordination belong to [meta](meta.md); subject-specific work belongs to its own module. Use [Choosing where to build](../methods/choosing-where-to-build.md) to place a component within those boundaries.
