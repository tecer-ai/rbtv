---
description: "Use on ANY code write, edit, fix, or refactor — in a repo, a vault script, or a mirror CLI — BEFORE the first edit. Carries the four code-hygiene disciplines the code must meet when you leave it: no dead code, no duplicate source, no monolith file, no patch in place of a root-cause fix. A violation your own change creates is fixed in the same change; a pre-existing one is surfaced, never fixed unasked."
tags: [coding]
---

# coding — how code is left after any change

You are about to write, edit, fix, or refactor code. Read the four references below NOW — all four, every time (most edits touch all four) — and hold them for the whole change:

| Reference | Governs |
|---|---|
| `3-resources/tools/rbtv/core/coding/references/no-dead-code.md` | nothing your change made unused is left behind |
| `3-resources/tools/rbtv/core/coding/references/no-duplicate.md` | one authored source per fact and per behaviour |
| `3-resources/tools/rbtv/core/coding/references/no-monolith.md` | one responsibility per file |
| `3-resources/tools/rbtv/core/coding/references/no-patches.md` | a fix lands at the cause, never at the symptom |

## Rules that hold across all four

| # | Rule |
|---|------|
| 1 | **Own change: fix. Pre-existing: surface.** A violation your change CREATES — code your edit made unused, a second source you introduced, a file you pushed into a second job, a symptom-level fix — MUST be fixed in the same change. A violation that was ALREADY there MUST be named to the owner in your closing message (file, symbol or line) and NEVER fixed unasked: widening the diff is not yours to decide. |
| 2 | **Scope: any code, anywhere.** NEVER assume a test suite, a CI, or a commit step exists; the four disciplines hold without them. |
| 3 | **Boundaries.** Whether to build at all, and how simply, was decided BEFORE this skill loaded — that is the `kiss` rule. How a request is framed is the `problem-framing` rule; why a fix is made at the cause, the sibling sweep, and the root-cause statement written BEFORE the edit are the `root-cause` rule. This skill governs ONLY the code you leave. |
