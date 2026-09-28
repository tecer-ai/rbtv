---
description: Choose the files a reusable rbtv component actually needs
tags: [planning]
---

# Component anatomy

A component is a direct child of a module folder. Its `component.md` explains what it is and
which entry point to use. Add other files only when the component performs that job. The
`build` skill routes authoring work; `plan.md` defines console seat plans separately.

| Artifact | Add when |
|---|---|
| `component.md` | Always: orientation and entry points. |
| `exposure.csv` | A part is exposed to an agent or a first-party CLI needs inventory. |
| `package.json` or equivalent | The runtime needs declared dependencies. |
| `prompts/<id>.md` and `tasks/<id>.md` | A reusable component seat pairs a prompt with a task. |
| `seats.csv` | The component catalogs those prompt/task pairs. |
| `workflows/<name>/` | A reusable workflow has a manifest and its own entry prose; use `workflow-anatomy.md`. |
| `capabilities/<name>/` | A capability needs instructions beyond its tool's own `-h`. |
| `references/` | A standalone subject needs a guide reached at the moment of use. |

## Existence test

1. Check whether an existing component or sibling part serves the need. Extend or reference it
   rather than duplicating its fact or behavior.
2. If a tool's `-h` explains the entire operation, add a routing line instead of another guide.
3. Keep runtime observations out of component source files. Probe the install that owns them.
4. Write a part where its owning component lives: a repo component in the repo, a mirror
   component in the mirror. An installed harness loader is generated and is never authored.

`component.md` is orientation, not a tool manual. Prompt and task formats live in `file-prompt.md`
and `file-task.md`; exposure decisions live in `exposure.md`. A new artifact with no clear
component owner is a scope question to settle before writing it.
