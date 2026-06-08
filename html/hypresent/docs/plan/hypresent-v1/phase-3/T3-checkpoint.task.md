---
task_id: T3-checkpoint
status: pending
phase: close
complexity_score: 8
human_review: required
---

# Checkpoint T3-checkpoint: Product Complete & Verified (CP3)

## Goal

Evaluate the integrated product and the verification results against review criteria, and present findings for human approval.

---

## Context Files

| File | Purpose |
|------|---------|
| ../shape.md | Prior decisions and execution context. |
| docs/verification-results.md | T18 results log — the primary evidence. |
| ../../../spec/05-verification-plan.md | §4 Save-As validity gate (hard release blocker). |
| ../../decision-log.md | D1–D6 — the behaviors the product must honor. |
| app/js/shell/outline.js, app/js/shell/file-controls.js, app/js/main.js | Integration work to evaluate. |

---

## Work to Evaluate

Phase-3 produced: region/outline navigator (T16); Save-As wiring end-to-end (T17); full verification run on both fixtures (T18).

## Review Criteria

1. Outline lists regions for both fixtures; click selects in the iframe (T16 acceptance).
2. Save As writes a standalone file; dirty-state + error handling correct (V-SAVE-1/2/3).
3. Every V-case PASSED on DECK and REPORT (T18 log).
4. §3 regression checklist clean across the suite.
5. §4 Save-As validity gate GREEN on both fixtures — chrome-free, document-JS runnable, island inert/invisible, round-trip re-editable.
6. No locked-decision (D1–D6) violation anywhere in the verification evidence.

## Execution Flow

### Phase: Evaluate
1. Read all Context Files (especially the T18 results log).
2. Review shape.md Decisions/Discoveries from Phase 3.
3. Evaluate each criterion PASS/FAIL with evidence from the log.
4. Prepare a per-criterion findings summary.

### Phase: Gate
1. Present findings with clear PASS/FAIL per criterion.
2. MUST append the Human Review Presentation block (format + flag criteria per `3-resources/tools/rbtv/orchestration/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation and `3-resources/tools/rbtv/orchestration/workflows/_shared/authoring/human-review-criteria.md`), pointing at the §4 gate result and any V-case FAIL; if all green, write "None identified" + one-line rationale.
3. HALT for human approval — do not advance regardless of findings.
4. If rejected: document feedback in shape.md, do not advance.
5. If approved: mark CP3 complete in the plan task list.
