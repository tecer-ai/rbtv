# PARA

Optional folder guidance for an installation that keeps work in `projects`, `areas`, `resources`, `archives` and `workbench`. rbtv works without this component. Task files, a wiki and context features are not part of it.

The roots are unnumbered. This page and the six folder-instructions sources use `projects`, `areas`, `resources`, `archives` and `workbench`. A numbered prefix is not a name this component writes.

## Two routes

Adopt this component:

```text
rbtv add meta/para
```

Adapt, and do not add this component: author your own `folder-instructions/` component under `.rbtv/mirror/` and select that component instead. A mirror component replaces a repository component of the same module and name; a different name installs beside this one only if you also add this one. Do not add `meta/para` when the mirror component is the guidance you want.

There is no install-time interview and no migration preview. The route is the command above, or the mirror component you author.

## Roots

| Folder | Purpose |
|---|---|
| `projects/` | Bounded work with a defined end |
| `areas/` | Continuing responsibilities |
| `resources/` | Reference consulted on demand |
| `archives/` | Holding zone before deletion; not a place to browse |
| `workbench/` | Independent repositories and worktrees |

The installation root receives the routing rules for those folders. Work not started, active work and completed work follow `rbtv structure project` and `rbtv structure area`. This page does not copy that tree.

## Index and instruction file

An area and a project each have one index and one instruction file.

`{name}.md` is the index. It opens with a description of purpose, scope and current state, then the folder's only routing table: `File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN`. Its frontmatter is what a task consumer already reads: `type: index`, and `tags` whose first entry is the folder name. A project index also carries `area` and `status`.

The instruction file (`CLAUDE.md` or `AGENTS.md`, the name the installation maintains) is mandatory. It says to read `{name}.md` first, then states the rules of that folder. It holds no routing table and no generated markers. A folder that has an index routes from the index.

Templates a creation step copies, then leaves as the user's files:

| Template | File |
|---|---|
| Area index | `capabilities/templates/area-index.md` |
| Project index | `capabilities/templates/project-index.md` |
| Area instruction file | `capabilities/templates/area-instructions.md` |
| Project instruction file | `capabilities/templates/project-instructions.md` |

Paths are relative to this component. Substitute `{name}` with the folder name. A project index also substitutes `{area}` with the parent area's folder name.

## What the installed sections carry

The six sources under `folder-instructions/` are the text `rbtv add meta/para` writes into the instruction file of each root. Edit those sources, not the generated section. Text outside the generated markers stays locally authored.

| Source | Target |
|---|---|
| `folder-instructions/root.md` | `.` |
| `folder-instructions/projects.md` | `projects` |
| `folder-instructions/areas.md` | `areas` |
| `folder-instructions/resources.md` | `resources` |
| `folder-instructions/archives.md` | `archives` |
| `folder-instructions/workbench.md` | `workbench` |
