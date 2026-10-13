---
target: projects
---

# projects/

Bounded work with a beginning and an end. An area is a continuing responsibility. A project retires when its outcome is reached or the work stops. Move that folder to `archives/`.

A due date is optional. The defining trait is a bounded lifespan, not a deadline. Dated tasks live in the project's task file. Do not treat a dated task as a project.

## Folder convention

| Item | Rule |
|---|---|
| One folder per project | `projects/{name}/`, lowercase kebab-case. Do not prefix the name with `project-` |
| Index | `{name}.md` — purpose, scope, current state. It holds the folder's only routing table |
| Index frontmatter | `type: index`. `tags` starts with the folder name. `area:` names the parent area. `status` records the current state. `due` is optional |
| Task file | `{name}-tasks.md`, created when the first task lands. Same `tags` and `area` as the index |
| Instruction file | Mandatory. It says to read `{name}.md` first and holds the folder-wide rules. It holds no routing table and no generated section |
| Other subfolders | Free-form reference. Follow the project's instruction file |

Work not started, active work and completed work follow `rbtv structure project`. Completed work is not an archive. A decision stays authoritative until superseded. Do not keep a second status narrative in the index when a workflow or status file owns execution state: link that file.

## Routing

| Situation | Action |
|---|---|
| New bounded work with a defined end | Create `projects/{name}/` with the index and the instruction file. Add the task file when the first task lands |
| Project complete or abandoned | Move the folder to `archives/` |
| Work has no defined end | It belongs in `areas/` |
| A single dated to-do | Add it to the relevant task file. Do not create a project folder for it |
| Reference that may seed a later project | It belongs in `resources/` |

Loose markdown files at the `projects/` root, siblings of project folders, are user-owned.

## Cross-references

Areas are continuing responsibilities. A project names its parent with `area:`. Archives are the destination when a project completes or stalls. A repository that backs the project lives in `workbench/{repo-name}/`. The project folder holds the notes and tasks.
