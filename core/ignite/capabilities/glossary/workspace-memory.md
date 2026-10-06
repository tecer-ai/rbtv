# Workspace memory

`.rbtv/memory/workspaces/<slug>.md` holds private notes about a shared repository or workspace. Keep those notes outside the shared repository, and link its public instructions instead of copying them. Ignite supplies a note only when the turn’s working directory matches one of its declared paths; otherwise the note is read on demand.

Submit a private fact through [Inbox](inbox.md), naming the workspace. [Memory](memory.md#record-and-maintain-information) owns its writers; the conversational agent does not edit or commit the note into the shared repository.

## Record format

```markdown
---
description: when <work in this workspace needs these private notes>
type: workspace
aliases: [<workspace names>]
paths: [<installation-relative folder>]
---
# <Workspace> — private notes

- <private fact or caution>. (<YYYY-MM-DD> · <source>)
- Shared docs: [<instructions>](<relative path>)
```

The frontmatter `paths` values start at the installation root, not the agent’s current folder; absolute values and `..` are refused there. Markdown links in the body, including Shared docs, resolve from this memory file’s folder. A path matches that directory and descendants, not another directory with the same prefix. Use the particular workspace path; a broader path supplies private notes to unrelated work. Quoted inline paths or an indented string list support spaces.

Follow [Memory](memory.md#record-checks) for provenance and counting. The [memory checker](../tools/ignite/memory.js) validates the workspace type, paths, heading and dated records, with a 3,000-character limit. Description and aliases are the standing format maintained by the dreamer, not separately enforced fields at injection.

Check one working directory inside the declared workspace and a neighboring directory outside it. Confirm that only the first receives the note, links reach shared instructions, and neither the note nor copied public facts enter the shared repository.
