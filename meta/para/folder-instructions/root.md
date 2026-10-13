---
target: .
---

# Installation root

Personal workspace using PARA. The roots are `projects/`, `areas/`, `resources/`, `archives/` and `workbench/`.

## Hard rules

When you capture content, route it to the matching folder. The daily note, when this installation has one, is the fallback for genuinely ambiguous content, not the default.

| Content | Destination |
|---|---|
| Bounded work with a defined end | `projects/{name}/` |
| Ongoing responsibility | `areas/{name}/` |
| Reference material | `resources/{topic}/` |
| Completed, abandoned, or under-review content | `archives/` |
| An independent repository or worktree | `workbench/{repo-name}/` |
| A task for a project or area | `{name}-tasks.md` inside that folder |
| Genuinely ambiguous content | the daily note, when one exists |

Fits an existing file: append. An index file (`{dir-name}.md`) is never a content destination. Unclear destination: ask before writing.

When the user explicitly says to add to today or to the daily note, route there regardless of the table.

**Archives are off-limits.** Do not read, search, list or load files under `archives/` unless the user explicitly directs you to that folder or names a path inside it. It is a holding zone. Its contents must not inform answers, routing or context. An explicit instruction lifts this for that request only. When a file you are already working with carries a direct path to one file under `archives/`, you may open that one referenced file. That lift is for that path only.

A new structural convention — a new folder pattern, file-organization scheme, task format or naming standard — needs the rule written in the owning instruction file or a decisions file, and the owner's agreement, before you apply it. Creating an ordinary project or area folder that follows this routing is not a new convention.

Text outside the generated markers wins over this section when they disagree. Agents read the file top to bottom.

## Naming

The main file of a directory is `{dir-name}.md`. Do not use `README.md` as the index. Folders, files and tags use lowercase kebab-case in English. Proper nouns and acronyms are exempt.

## Tags

An index (`{dir-name}.md`) and a task file (`{name}-tasks.md`) carry their own directory name as the first tag. A project declares its parent area with `area:` frontmatter on those two files, not with an area tag. Every other file in an area gets that area's directory name as a tag. Cross-cutting tags combine with these. A resource may add topic tags.

## Roots

| Folder | Purpose |
|---|---|
| `projects/` | Bounded work with a beginning and an end |
| `areas/` | Ongoing responsibilities |
| `resources/` | Reference content |
| `archives/` | Holding zone before deletion |
| `workbench/` | The single home for independent repositories and worktrees. Do not create one anywhere else |

A vault file is a markdown file in `projects`, `areas`, `resources` or `archives`. `workbench/` holds independent repositories. It is not a vault file. Loose markdown files placed directly under a root, as siblings of subfolders, are user-owned.

## Parallel sessions

On an edit rejection because the file changed since you read it, re-read the file and re-apply only your delta. Do not restore frontmatter or body content from your earlier read.

Before committing a shared file, diff it against your own delta. Disclose foreign hunks in the commit message, or stop and re-scope. Scope the commit with `git commit -- <path>`, not a staging check followed by a bare commit. To publish off a shared branch that has diverged, cherry-pick into a temporary worktree outside the shared tree. Do not `git commit --amend` in a shared tree.

Immediately before staging, `git diff` each file and confirm your delta is still present. If it was wiped, re-read and re-apply only your delta, then commit.

On a shared working tree, do not run `git stash`, `git restore` or `git checkout` with no path, `git checkout -- .`, or `git clean`. Compare your change against clean HEAD with a scratch worktree outside the shared tree, or with `git show HEAD:<path>` for one file. Remove the scratch worktree when done.
