---
description: "Use to discover available agent cards, cognitive units, seats, tasks, or workflows before staffing a plan; search the catalog by meaning."
exposes-cli:
  - rbtv-teambuild
---

# teambuild

Run `rbtv-teambuild <database>` to browse the component catalog. The equivalent
dispatcher is `rbtv teambuild`. Use `agents`, `units`, `seats`, `tasks`, or
`workflows` for a known database, or `search "<need>"` to rank all of them by
meaning. Run `rbtv-teambuild --help` for flags and read `ignite/teambuild/component.md` when
the search index or provider behavior matters. This command discovers choices;
it does not bind an executor.
