---
target: archives
---

# archives/

Holding zone before deletion. Completed projects, abandoned files and content under review live here until reviewed and either deleted or restored.

An archive has no active work, no ongoing responsibility, and is not yet ready for deletion. Active work belongs in `projects/`. A maintained responsibility belongs in `areas/`. Reference consulted on demand belongs in `resources/`.

| Stage | Meaning |
|---|---|
| In the archive | Out of active circulation, recoverable, not a source for ordinary answers |
| Deleted | Removed from the workspace; recovery only through version history |

Do not write new content directly into `archives/`. Files arrive by an archive move or an explicit user move. Do not read, search, list or load this folder unless the user explicitly directs you here or a file you are already working with names one path inside it. That lift is for that one path. Sensitive archived content is read or summarized only when the user explicitly requests it.

| Situation | Action |
|---|---|
| A project completes or stalls | Move `projects/{name}/` to `archives/{name}/` |
| An area is no longer maintained | Move `areas/{name}/` to `archives/{name}/` |
| A resource is no longer relevant | Move it to `archives/` |
| Archived content is needed again | Move it back to the matching root. Do not duplicate it |
| Archived content is reviewed and unwanted | Delete it. Deletion is a separate step from archiving |

`archives.md` may index what was archived and when. It is user-owned. This component does not enforce a retention period. Loose markdown files at the `archives/` root are user-owned.
