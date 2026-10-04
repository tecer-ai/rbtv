<!--
Shape of one workspace-memory file. Copy the skeleton into the instance. Do not copy this comment.
The dreamer writes the instance. paths are installation-relative. Cap: 3,000 characters.
-->

## Skeleton

```markdown
---
description: when working in <the repo or workspace> — <what these private notes cover>
type: workspace
aliases: [<repo name>, <team or client name>]
paths: [<vault-relative folder>, <another folder>]
---
# <Workspace name> — private notes

- <who the owner works with there / their role>. (<YYYY-MM-DD> · <agent>/<thread link>)
- <a private caution or practice that the shared repo must not carry>. (<YYYY-MM-DD> · <agent>/<thread link>)
- Shared docs: [<path of the repo's own instructions file>](<relative link>)
```

## Example (fictional — never copy)

```markdown
---
description: when working in the shared Northwind client site repo — the owner's private notes on it
type: workspace
aliases: [northwind, northwind-site, client site]
paths: [5-workbench/northwind-site]
---
# Northwind site — private notes

- Sam is the design lead on this repo. (2026-08-14 · master/[t-1720](https://example.slack.com/archives/C0000/p1720))
- [jo-tan](../entities/people/jo-tan.md) owns deploys — ask Jo before any release. (2026-08-14 · master/[t-1720](https://example.slack.com/archives/C0000/p1720))
- Never commit as Sam on this repo; it publishes to the client's public history. (2026-08-20 · master/[t-1755](https://example.slack.com/archives/C0000/p1755))
- The client contract ends 2026-12-31 — no new features after that date. (2026-09-03 · master/[t-1891](https://example.slack.com/archives/C0000/p1891))
- Shared docs: [5-workbench/northwind-site/CLAUDE.md](../../../5-workbench/northwind-site/CLAUDE.md)
```
