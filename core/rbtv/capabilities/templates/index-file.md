<!--
Shape of a folder content index, _artifacts/index.md. Copy the skeleton into the instance. Do not copy this comment.
Does not list _artifacts items; folder instructions list those. A wiki keeps its own index names.
A generated index uses the same table, carries no frontmatter, and lists every file of its folder.
-->

## Skeleton

```markdown
---
type: index
tags:
  - <folder-name>
area: <parent area>        # projects only
status: <active | paused | done>   # projects only
---

# <folder-name>

<One sentence: what this folder is for.>

| Open | When |
|---|---|
| [../<subfolder>/](../<subfolder>/) | <BEFORE / WHEN / ALWAYS / ONLY — the moment to go in.> ⚠ <hazard, if any.> |
| [../<file>.md](../<file>.md) | <the moment to open it.> |
```

<!-- ===================== FILLED EXAMPLE (fictional project) — example, never copy ===================== -->

```markdown
---
type: index
tags:
  - website-relaunch
area: marketing
status: active
---

# website-relaunch

Relaunch of the company website on a new theme, ending when the new site is live and the old host is cancelled.

| Open | When |
|---|---|
| [../build/](../build/) | ONLY when the board, a task or a decision points at a run folder; never browsed cold. |
| [../theme/](../theme/) | BEFORE editing the site's look. ⚠ Never edit the generated `theme/dist/` — edit `theme/src/` and rebuild. |
```
