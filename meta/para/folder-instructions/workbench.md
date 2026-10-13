---
target: workbench
---

# workbench/

Independent repositories and worktrees. Each entry has its own layout, its own commit history, and hosts code or content that needs a real repository. This component does not impose vault conventions inside an entry.

Notes and tasks with no repository belong in `projects/{name}/`. When there is a repository, the repository lives here. Notes and tasks may stay in `projects/` and link the repository path.

| Item | Rule |
|---|---|
| One folder per repository | `workbench/{repo-name}/`, lowercase kebab-case |
| Internals | Governed by that repository's own instruction file |
| Instruction file of the repository | At the repository root. User-owned. This component does not generate it |
| Vault index | Optional `projects/{name}/{name}.md` that links the workbench path |

Subfolders under `workbench/` are independent git repositories. The installation's ignore rules exclude them. Commit, push, branch and review operations target the nested repository, not the workspace that contains it. Do not create a workbench entry anywhere except `workbench/`.

| Question | `projects/` | `workbench/` |
|---|---|---|
| Notes, tasks and references only | yes | |
| A repository with its own history | | yes |
| Needs releases, branches or external collaborators | | yes |

A workspace may use both: `projects/{name}/` for notes and tasks, and `workbench/{repo-name}/` for the repository. Cross-link them in the project index.

`resources/tools/` holds installed tooling that is also often a nested repository. Workbench entries are your active project repositories. Tooling that serves the workspace belongs under `resources/tools/`.
