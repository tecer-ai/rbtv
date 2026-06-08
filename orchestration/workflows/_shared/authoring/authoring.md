# Shared Authoring Core

Single source of artifact-authoring knowledge for the orchestration module. Two consumers read these files to author the same artifacts the same way:

| Consumer | Reads this core to |
|----------|--------------------|
| Interactive `rbtv-planning` | Author task files, spec files, and dependency-ordered plans WITH the user |
| Orchestration intake writer agents | Author the same artifacts from a goal prompt when no plan exists |

Both doors produce identical contracts because both read these files — no authoring knowledge is duplicated in either workflow.

## Files

| File | Owns |
|------|------|
| `task-file-contract.md` | What a self-contained, zero-context task file MUST contain — granularity, file-operation verbs, context budgets, checkpoint criteria, and the per-model contract plug-in seam |
| `spec-template.md` | The behavior-spec + test-plan template (NEW) — code-work plans and plan-less intakes both fill it before any executor builds. D2b's "spec template + test-plan template" are UNIFIED here: the test plan is the spec-template's Test Plan section, not a separate file. There is no standalone test-plan-template.md. |
| `complexity-rubric.md` | The widened complexity rubric — scores a body of work across weighted axes and routes it to a band (simple / moderate / complex door) |
| `dependency-ordering.md` | How to order tasks so every dependency lands before its dependents, plus the ordering-validity checks |
| `decisions-discipline.md` | The entry-shape discipline for the worker-facing `decisions.md` — the text the three D13 surfaces (template, plan reminder, reviewer audit) carry |
| `human-review-criteria.md` | Red/yellow flag criteria and no-flag affirmation rules for Human Review Presentation blocks (tasks with `human_review: required`) |

## How a consumer uses the core

1. Score the work with `complexity-rubric.md` → band selects the entry door (planning vs intake; full vs light prep).
2. Author each task file to `task-file-contract.md`. Code tasks additionally get a spec authored from `spec-template.md`. (BOTH consumers run this step: the orchestration intake writer and the interactive `rbtv-planning` workflow, whose conditional spec-authoring step authors one spec per code feature at plan creation.)
3. Order the task set with `dependency-ordering.md`; run the validity checks before finalizing.
4. Carry `decisions-discipline.md` into the run's `decisions.md` surfaces so worker-facing entries stay disciplined.

## Boundary

This core owns AUTHORING KNOWLEDGE only — what an artifact must contain and how to size, order, and discipline it. It does NOT own workflow MECHANICS: step sequencing, when to emit a micro-step file, plan-document structure, checkpoint placement, and plan-linking remain inside the consuming workflow (`rbtv-planning`). A consumer reads this core for the contract, then applies its own mechanics around it.
