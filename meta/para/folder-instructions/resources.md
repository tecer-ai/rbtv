---
target: resources
---

# resources/

Reference consulted on demand. Not an active responsibility and not a bounded goal.

A resource has no defined outcome, no standard of performance to uphold, and topical interest that may seed later work. When it needs active stewardship, move it to `areas/`. When it seeds bounded work, create a project and keep the resource as reference.

## Folder convention

| Item | Rule |
|---|---|
| Top-level folders | One per category, lowercase kebab-case |
| `tools/` | Active tooling: catalogs, reusable prompts, installed repositories. It provides function. It is not itself the reference notes |
| Index | `{category}.md` inside a leaf category that holds many similar files. A container of distinct subfolders skips the index; its instruction file does the navigation |
| Wiki | When the installation configures a wiki root, originals live under that root's raw folder and synthesis lives elsewhere under that root. This component does not define the wiki root |

Saved external content splits into raw originals and synthesis. Raw originals are immutable. Append new captures there. Write derived notes in the synthesis layer. Do not overwrite a raw file.

Subfolders under `resources/tools/` may be independent git repositories. The installation's ignore rules exclude them. Edits inside an installed repository follow that repository's rules. Re-installing or upgrading that repository is how its contents are updated.

## Routing

| Situation | Action |
|---|---|
| A new tool, prompt or installable repository | Place it under `resources/tools/` |
| Saved external content | Place the original in the configured wiki raw folder, and synthesis elsewhere under that wiki root |
| A topic with no active stewardship | Create `resources/{category}/` |
| The resource needs active stewardship | Move it to `areas/{name}/` |
| The resource seeds bounded work | Create `projects/{name}/`. The resource folder may remain |

Loose markdown files at the `resources/` root are user-owned.
