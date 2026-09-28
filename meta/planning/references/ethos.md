---
description: Design principles for component scaffolding and console seat plans
tags: [planning]
---

# Design ethos

- Start with the result and the reader who must verify it.
- Reuse an existing component or tool when it already serves the job. During seat planning,
  inspect exposed resources with `capability-cards` before inventing a tool.
- Use a deterministic command for deterministic work; reserve an agent seat for judgment.
- Give each seat one bounded job, a self-contained body, a named output, and a falsifiable
  done contract. Add a dependency only when an artifact crosses it.
- Keep one authored home for each fact. A second file points to that home instead of copying it.
- Make every instruction usable by a reader who has never seen this planning session.
