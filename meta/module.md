---
description: Meta module — tools that maintain and expose the rbtv system
---

# meta

The `meta/` module holds tooling whose subject is rbtv itself. Current components:

| Component | Entry point |
|---|---|
| `planning/` | `build` routes scaffolding work; `plan` defines console seat plans. |
| `installer/` | `rbtv install` installs and removes component exposures. |
| `rbtv-cli/` | `rbtv` lists components and routes commands. |
| `control-panel/` | `rbtv control-panel` shows the shipped and installed seat and workflow catalog. |
| `embed-search/` | `rbtv embed-search` indexes and searches folders. |

The direct-message primary agent is named `master`; its home and runtime are owned by
`ignite/agents/`. Staffing discovery lives in `ignite/teambuild/` and remains available through
`rbtv teambuild`.
