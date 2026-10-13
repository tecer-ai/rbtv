---
target: areas
---

# areas/

Continuing responsibilities with no finish line. An area has no defined end, no deadline, and a standard you uphold continuously.

Work with a deadline and a defined outcome belongs in `projects/`. Reference with no active stewardship belongs in `resources/`.

## Folder convention

| Item | Rule |
|---|---|
| One folder per area | `areas/{name}/`, lowercase kebab-case |
| Index | `{name}.md` — scope, current state and standing notes. It holds the folder's only routing table |
| Index frontmatter | `type: index`. `tags` starts with the folder name |
| Task file | `{name}-tasks.md`, created when the first task lands. The same first tag as the index |
| Instruction file | Mandatory. It says to read `{name}.md` first and holds the folder-wide rules. It holds no routing table and no generated section |
| Subfolders | One per ongoing topic, each with its own `{topic}.md` index |

Current reference stays at the area root. Bounded work follows `rbtv structure area`. Completed work is not an archive. A decision stays authoritative until superseded.

When work inside an area has a bounded outcome, name what you found, recommend extracting it to `projects/{name}/` with `area:` pointing back here, and offer to keep it as an area topic. Proceed on the owner's decision. An ongoing practice that spawns bounded efforts stays in the area. Only the bounded efforts move.

## Tags

Every file inside `areas/{name}/` gets `{name}` as a tag. The index and the task file carry it as the first tag. A cross-cutting tag combines with it and does not replace it.

## Routing

| Situation | Action |
|---|---|
| New ongoing responsibility | Create `areas/{name}/` with the index and the instruction file. Add the task file when the first task lands |
| The area gains a deadline and a defined outcome | Create `projects/{name}/` for that work. The area folder remains |
| The area is no longer maintained | Move the folder to `archives/` |
| Reference with no active stewardship | It belongs in `resources/` |

Loose markdown files at the `areas/` root are user-owned.
