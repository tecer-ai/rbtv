---
description: Check a reusable component workflow seat before registering its catalog and manifest rows
tags: [planning]
---

# Workflow-authoring checklist

Use this for a seat in a reusable component workflow. For a console seat plan, use `plan.md`:
its `seat.md` body is self-contained and its folder is launched with `cast seat`.

1. **Pairing.** The `seats.csv` row names an existing prompt and task, each with a distinct
   role. The manifest references the seat id exactly once when it is a scheduled node.
2. **Inputs and output.** Name the request or predecessor artifact the seat reads, the
   artifact or verdict it produces, and the exact path or channel its consumer reads. An
   `after` edge exists only where that artifact crosses it.
3. **Instruments.** For each tool or guide the procedure needs, resolve its real exposure
   row or executable path and describe when the seat uses it. Remove a grant with no step.
4. **Contact and failure.** If the seat reaches the owner, say when, what answer it needs,
   and what happens if the answer does not arrive. A failure route names a real next seat or
   reports the issue for a human ruling; no implicit retry loop.
5. **Portability.** No owner's channel, host, account, credential, or workspace path is baked
   into the definition. Resolve instance values from configuration at execution time.
6. **Done contract.** State falsifiable checks that cover the actual result, missing inputs,
   duplicate events, and the failure route. Run an adversarial completeness review before
   registering the rows.

A seat plan's own files are `seats.md`, `read-first.md`, and `seats/<name>/seat.md`; each seat
writes a report at `seats/<name>/report.md`. Create scratch files only when needed. The plan
orchestrator verifies reports and records state in `seats.md`.
