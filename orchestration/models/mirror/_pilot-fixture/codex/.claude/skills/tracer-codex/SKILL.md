---
name: tracer-codex
description: A2 loader-follow tracer for the codex mirror pilot. Use when asked to invoke the tracer-codex skill or run the tracer. Reads and executes the tracer workflow file, which carries a unique sentinel the pilot checks for.
---

# tracer-codex

This skill is a thin loader. To execute it you MUST do exactly this:

1. Read the workflow file at `workflows/tracer-workflow.md` (relative to this
   workspace root — the directory that contains this `AGENTS.md` / `CLAUDE.md`).
2. Follow its single instruction exactly.

Do nothing else. The workflow file contains the operative instruction; this
loader contains only the pointer to it.
