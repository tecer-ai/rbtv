---
description: Read at the moment of deciding whether to enter the ignite build memory — what it is and where its entry points are.
---

# work-on-ignite

The build memory for the `ignite` and `meta` trees: per-component logs of fixed issues and
landed creations, cited against the deployed tree, read before an edit and filed to after one.

## Entry points

- Skill `work-on-ignite` — `references/work-on-ignite.md` — the WHEN and the 7-step procedure.
- The memory store — `memory/<component>/` — one folder per component, read directly for its
  `_summary.md`, `_issues.md`, `_creations.md`.
- Filing command — `file-issue memory …` (team-kit's), the only writer to the memory store.
- Semantic search — `rbtv embed-search` (meta's), for symptom/feature lookups over `memory/`.
- Upkeep goal — `goal-memory-management`, which distills and rotates each component's memory.
