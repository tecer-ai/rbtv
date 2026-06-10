---
task_id: p6-compound
status: pending
phase: close
complexity_score: 6
human_review: required
executor: { model: claude, variant: opus }
reviewer: { model: claude, variant: opus }
allowlist:
  modify:
    - ../learnings.md   # plan folder (file-relative)
  create:
    - .user/compounds/orchestration/**   # compound PRDs, if any learning is compound-ready
orchestrator_executed: false
---

# Task p6-compound: Compound learnings into system improvements

## Goal

Process `learnings.md` — promote each compound-ready learning into an actionable system change (a compound PRD under `.user/compounds/{component}/`), or confirm none qualify. Decide the two candidate seeds (Agent-tool-carrier-must-be-manifested; variant field-count discipline).

## Context Files

| File | Purpose |
|------|---------|
| `../learnings.md` | The queue + the two candidate seeds |
| `../decisions.md` | Context for each learning |
| `.user/compounds/CLAUDE.md` | The compound-PRD placement convention (nested per component) |

## Allowlist

- ✎ modify: `../learnings.md` (mark processed)
- ✚ create: `.user/compounds/orchestration/cp-orchestration-{description}.md` (per compound-ready learning)

## Execution Flow

### Phase: Understand
1. Read every Context File. Mark in-progress in the three locations.

### Phase: Execute
1. Review all learnings marked compound-ready; group by target component.
2. For each group, author a compound PRD under `.user/compounds/{component}/`; mark the source learnings "Compounded: {date}".
3. Resolve the two candidate seeds: confirm or discard each as a learning.

### Phase: Validate
1. Every compound-ready learning is either compounded (PRD exists) or explicitly deferred with a reason.

### Phase: Close
Follow the microstep template Phase: Close (orchestration mode). `human_review: required` → emit the Human Review Presentation block.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Compound PRDs (if any) | `.user/compounds/orchestration/` | Markdown |
| Updated learnings | `../learnings.md` | Markdown (append "Compounded:" lines) |

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Amendments

### ADX-4 (2026-06-09, conductor ruling at the p6-compound DOUBT_ESCALATED halt) — compound-PRD destination, deferral-note scope, tracking-task grant

1. **Destination + naming CORRECTED:** the Allowlist line `create: .user/compounds/orchestration/**` and every `orchestration/` destination reference in this task are corrected to **`.user/compounds/rbtv-orchestrating/`** with filenames **`cp-rbtv-orchestrating-{description}.md`**. Rationale: the component improved is the `rbtv-orchestrating` module; the placement convention (`.user/compounds/CLAUDE.md` — one component one folder, `cp-{component}-{description}.md`), THREE existing precedent PRDs (`cp-rbtv-orchestrating-*.md`, frontmatter `component: 'rbtv-orchestrating'`, `outputPath: '.user/compounds/rbtv-orchestrating/'`), and the live tracking task in `2-areas/compounds/compounds-tasks.md` are unambiguous — disk precedent wins over this task's stray allowlist line. (Worker correctly halted on the contradiction.)
2. **Deferral-note append is IN SCOPE:** recording a learning's DEFERRED disposition in `../learnings.md` (append-only, with the reason) is within this task's learnings-update duty — the Validate phase requires every compound-ready learning either compounded OR explicitly deferred with a reason. Append-only discipline unchanged.
3. **Tracking subtasks (single-resume allowlist grant, logged in run-log):** append one subtask per new PRD under the existing rbtv-orchestrating task in `2-areas/compounds/compounds-tasks.md`, per the convention's one-subtask-per-compound rule. This grant is scoped to THIS resume only.
4. When flipping this task's `../deliverables.md` row, also correct the row's Path cell to the rbtv-orchestrating destination.
