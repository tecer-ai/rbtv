---
description: Meta module — tools that maintain and expose the rbtv system
---

# meta

The `meta/` module holds tooling whose subject is rbtv itself. Current components:

| Component | Entry point |
|---|---|
| `planning/` | `build` routes scaffolding work; `plan` defines console seat plans. |
| `installer/` | `rbtv install` lists and searches modules, components, and items; configures, installs, removes, updates, and checks a workspace; `manage-components` guides agents through it. |
| `rbtv-cli/` | `rbtv` lists components and routes commands. |
| `control-panel/` | `rbtv control-panel` shows the shipped and installed seat and workflow catalog. |
| `embed-search/` | `voyage-embed` (a standalone command, not an `rbtv` verb) indexes and searches folders; the `embed-search` skill exposes it. |

The direct-message primary agent is named `master`; its home and runtime are owned by
`ignite/agents/`.
