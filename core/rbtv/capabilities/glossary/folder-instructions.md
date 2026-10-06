# Folder instructions

Folder instructions are guidance a harness supplies for work in a folder. They are an exposure method and an entry point; the agent does not choose them from a description.

Use them for the folder's own boundaries and routes. Keep instructions that apply across unrelated folders in their shared owner. Actual loading depends on the harness; the presence of a file does not guarantee every session receives it.

## One authored source

Maintain one of `CLAUDE.md` or `AGENTS.md` according to the installation's recorded choice. If no choice is recorded, ask which to author. Let rbtv generate the other name; do not maintain two independent copies.

A component can ship a source under `folder-instructions/` with frontmatter matching [folder-instructions.schema.json](../templates/folder-instructions.schema.json). Its `target` is relative to the installation root; `.` means that root. rbtv strips the frontmatter and writes the body inside a marked section of the target's instruction file. Edit that component source, not the generated section. Text outside generated markers remains locally authored.

## Body and routes

Follow [Entry point](entry-point.md) for the split between information every reading needs and conditional methods. A search must not acquire an editing procedure merely because it visits the folder.

Keep only facts specific to this folder in the body. Put subfolder-only facts in that subfolder's instructions and route there when needed. Put shared guidance in its owning page rather than copying it. Read required pages before selecting conditional routes.

Name required readings directly before the work that needs them. Use one [Routing table](routing-table.md) when the reader chooses among the folder’s case-specific files, subfolders and artifacts. Link from the instruction file to each existing target; do not add nonexistent standard files to impose a new workspace structure. Name an agent by its launch name when a row starts an agent.

Write the row's condition as recognizable work in this folder: editing, searching, reading or making a particular decision. CONTAINS distinguishes the target; PURPOSE states its use here. Do not put the target's method into the row. Add exclusions according to Routing table.

Do not use `@` imports for conditional readings. Claude Code can expand them immediately, while other harnesses do not share that behavior. Do not hide instructions in HTML comments; harness handling differs.

## Inheritance and paths

A subfolder's instructions add to their parents; they must not contradict them. Put requirements needed by all sessions in the highest relevant folder whose instructions those sessions receive. Do not rely on a child file to correct a parent for sessions that never load the child.

Claude Code can load child instructions when reading files there. Codex constructs its instruction chain from the project root to the starting working directory and applies a combined size limit. OpenCode prefers `AGENTS.md` over `CLAUDE.md` in the same folder. Follow [Harness](harness.md) for platform facts and uncertainty; test the placements actually supported.

Locally authored links resolve from the instruction file, including its same-folder generated counterpart. Component-shipped links must resolve from the target file, not the component's source folder. Shipped content cannot assume files, accounts or paths belonging to one installation. Check it against locally authored text outside the generated section. Leave the generated prompt pointer in an agent folder untouched.

## Template

```markdown
# <folder>

<Folder-specific facts required for every reading.>
<Direct required readings, if any.>

<Include the table below only when choosing among case-specific readings.>

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [<page>](<path from this file>) | <content> | <use here> | <recognizable work> |
```

A component source adds `target` frontmatter; its body follows the same layout with links based on the installed target. Use direct links for required readings; omit the table when there is no choice among case-specific readings.

## Changes and verification

Update a row when its target or condition changes and regenerate copies before treating the installed guidance as updated. On conversion, separate visit-wide facts from conditional work, replace imports with routes and retain one authored source. Use [Folder artifact](folder-artifact.md) for local supporting content.

Test a search, an edit that needs a routed file and an edit that does not. Check the actual files loaded and actions taken, plus parent/child compatibility. Installer acceptance verifies placement and frontmatter, not whether the agent follows the right route.
