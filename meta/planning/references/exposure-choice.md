---
description: Choose how an rbtv component part reaches an agent
tags: [planning]
---

# Exposure choice

Start with the reader and trigger. A component entry point links to a part when the reader
needs it only while doing that component's work. Give the part its own `exposure.csv` row when
an agent should find it independently. Keep one method per row; the manifest format and method
canon are in `exposure.md`.

For CLI discovery through a child or parent skill, use `exposure.md` § Skills are the discovery route.

| Reader's need | Method |
|---|---|
| A guide loaded at a recognizable task moment | `skill` |
| An explicit command in a harness | `command` |
| Standing behavior applied by the harness | `rule` or `hook` |
| An independently dispatched agent definition | `sub-agent` |
| A runnable first-party CLI | `path` |
| A reusable catalog definition with no independent loader | `pool` |

For a console seat plan, name an available instrument and its invocation in the seat body.
That plan has no generated exposure grant. Check every selected entry point exists, then use
`rbtv install` to regenerate workspace loaders for changed rows.
