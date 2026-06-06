---
task_id: pN-checkpoint
status: pending
phase: close
complexity_score: 7
human_review: required
---

# Checkpoint pN-checkpoint: Final Review

## Goal

Evaluate plan completion against final review criteria and obtain user approval to complete the plan.

---

## Context Files

| File | Purpose |
|------|---------|
| ../shape.md | Full decision/discovery history. |
| ../learnings.md | Compound output from T21 (pN-compound). |
| README.md | Run/usage doc (T19) to verify. |
| ../../../spec/04-implementation-plan.md | All task STATUS values (must be DONE). |
| docs/verification-results.md | Final verification evidence. |

---

## Work to Evaluate

Final phase produced: README (T19); reference review (pN-refs/T20); compound learnings (pN-compound/T21).

## Review Criteria

1. All tasks T1–T18 + checkpoints are DONE in `../../../spec/04-implementation-plan.md` and the plan task list.
2. README lets a fresh reader start the server and open/edit/save a fixture (T19).
3. All internal plan links resolve and comply with the Plan Linking Standard (T20/pN-refs): internal = file-relative, external = root-relative.
4. learnings.md entries are triaged; compound entries written or "none" (T21/pN-compound).
5. The Save-As validity gate is green on both fixtures (carried from CP3).

## Execution Flow

### Phase: Evaluate
1. Read all Context Files.
2. Verify each criterion PASS/FAIL with evidence.
3. Prepare a completion summary.

### Phase: Gate
1. Present the completion summary with clear PASS/FAIL per criterion.
2. MUST append the Human Review Presentation block (format + flag criteria per `3-resources/tools/rbtv/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation and `.../data/plan-creation-rules.md` § Human Review Flag Criteria); if all green, write "None identified" + one-line rationale.
3. HALT for human approval.
4. If rejected: document feedback in shape.md, address, do not complete.
5. If approved: mark the plan complete.
