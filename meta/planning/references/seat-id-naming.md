---
description: Read at the moment of naming a workflow's seat rows — the workflow-code law the seat-id prefix must satisfy, and why deploy is too late to learn it.
tags: [planning]
---

# seat-id naming — the workflow-code law

Record first: `sd-graph show "workflow code"` (`concepts/workflow-code.md`). The record IS the definition — this guide points at it and rules only the authoring moment; on any mismatch, the record wins.

## the law

- A workflow's CODE is the one prefix shared by EVERY seat-id in its manifest (`plan-interviewer`, `plan-splitter`, … → `plan`). It is DERIVED from the manifest, never typed.
- A workflow code MUST be exactly FOUR ASCII letters (owner-ruled 2026-08-10, settled by `decisions.md#d-workflow-code-mint`). Pick the four-letter prefix BEFORE writing the first seat row; every row then carries it.
- The code is load-bearing twice: it NAMES the workflow's casting sheet (`.rbtv/config/modules/<module>/<component>/bindings/<code>.json`) and it is the prefix a branch's seats carry inside a goal.

## what the prefix is independent of

The seat-id prefix owes nothing to the workflow's NAME or to its prompt file names. The precedent already in the tree: workflow `planning`, seats `plan-*`, sheet `plan.json`, prompts named bare (`interviewer.md`). A prompt id is not a seat id — the code belongs to the SEAT id and nowhere else (`file-prompt.md`, `file-task.md` § naming the id).

## why you read this NOW, not at deploy

The enforcing tool is the bindings capability's `workflow_code()`: it REFUSES a manifest whose rows share no single prefix, and any code that is not exactly four letters — and that refusal lands at casting-sheet time, AFTER the workflow is authored, committed, and pushed. The forge workflow was authored 2026-08-11 with `forge-*` seat ids — a five-letter prefix, one day after the rule was ruled — and nothing caught it during authoring, lint, or review; it was caught by `rbtv-bindings scaffold` refusing on deploy, and the fix was renaming three seat ids across four files plus an owner ruling. Satisfy the law in the seat rows and the wall is never met.
