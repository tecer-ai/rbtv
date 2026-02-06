---
task_id: p4-open-migration-plan
status: pending
phase: execute
complexity_score: 10
human_review: optional
---

# Task p4-open-migration-plan: Open M4, M5, M6 in Founder-Migration Plan (Like M1–M3)

## Goal

UPDATE `.cursor/plans/founder-migration/business-innovation-migration_v3.plan.md` (and create/update phase-6 task files) so that M4, M5, and M6 are "open" in the same way as M1–M3: **each framework or sub-workflow creation is its own task**, not one bundled task per milestone. This reduces token load when executing the founder-migration plan. When executing this fix, the agent must be aware that **p6-1 and p6-2 have been executed**, and **p6-3 is WIP** — **read p6-3.task.md** to understand the current state (what is done, what is remaining, what deliverables are in scope) **before** opening M4 into the standard of up to M3.

---

## Context Files

| File | Purpose |
|------|---------|
| .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-3.task.md | **MUST read first** — current state of M4 work (Work Completed, Next Steps); p6-3 is WIP |
| .cursor/plans/founder-migration/business-innovation-migration_v3.plan.md | Plan to update: Phase 6 todos and body |
| .cursor/plans/founder-migration/business-innovation-migration_v3/shape.md | p6-2 "Components to Create in p6-3" — list of M4 components; p6-1 M4 routing structure |
| .cursor/plans/founder-migration/business-innovation-migration_v3/phase-3/p3-1.task.md | Reference: M1 milestone task (single task for milestone workflow) |
| .cursor/plans/founder-migration/business-innovation-migration_v3/phase-3/p3-2.task.md | Reference: M1 framework task (one task per framework) |
| .cursor/plans/founder-migration/business-innovation-migration_v3/phase-4/p4-1.task.md | Reference: M2 milestone task pattern |
| .cursor/plans/founder-migration/business-innovation-migration_v3/phase-4/p4-2.task.md | Reference: M2 framework task pattern |

---

## Execution Flow

### Phase: Understand

1. **Read p6-3.task.md in full.** Note: Work Completed (e.g. bi-m4-user-flow-ia done), Next Steps / Remaining M4 Workflows to Create (bi-m4/workflow.md, bi-m4-design-context, bi-m4-conversion-centered-design, bi-m4-heuristic-evaluation, bi-m4-build-prototype?, bi-m4-testing-prep?, update mentor). This is the current state; p6-3 is WIP.
2. Confirm p6-1 and p6-2 are completed (evaluate M4, decide M4 scope). Do not change their status.
3. Read business-innovation-migration_v3.plan.md Phase 6 section: current tasks are p6-1, p6-2, p6-3 (single "CREATE M4 components"), p6-4 through p6-9 (evaluate/decide/create M5, evaluate/decide/create M6), p6-10 (milestone steps-c), p6-checkpoint.
4. Read M1 pattern: p3-1 (CREATE M1 milestone workflow), p3-2 to p3-7 (one task per framework). Same for M2 (p4-1 + p4-2 to p4-7), M3 (p5-1 + p5-2 to p5-7).

### Phase: Execute

1. **Open M4:** Replace the single task p6-3 ("CREATE M4 components with BMAD integration") with multiple tasks following the M1–M3 standard:
   - One task for M4 milestone workflow (bi-m4/workflow.md) if not already a separate deliverable.
   - One task per M4 component from shape p6-2 and p6-3.task.md: e.g. bi-m4-user-flow-ia (already done — may remain as completed or split out), bi-m4-design-context, bi-m4-build-prototype, bi-m4-conversion-centered-design, bi-m4-heuristic-evaluation, bi-m4-testing-prep, update mentor. Use the current state from p6-3.task.md to set which tasks are completed vs pending (e.g. bi-m4-user-flow-ia completed; bi-m4/workflow.md may exist; rest pending). Preserve p6-3 as WIP or split into p6-3a, p6-3b, ... and mark completed/pending per current state.
2. **Renumber Phase 6** so that after the new M4 tasks, p6-evaluate-M5, p6-decide-M5, and **open M5** (one task per M5 component) follow; then p6-evaluate-M6, p6-decide-M6, and **open M6** (one task per M6 component); then p6-10 (milestone steps-c), p6-checkpoint. Use consistent ID format (e.g. p6-3, p6-4, p6-5, ... for M4 frameworks; then p6-N evaluate M5, p6-N+1 decide M5, p6-N+2 ... for M5 frameworks; same for M6). If the plan already has p6-4 through p6-9 reserved for evaluate/decide/create M5 and M6, insert new M4 framework tasks between p6-3 and current p6-4 (e.g. p6-3a, p6-3b, ... or renumber to p6-3, p6-4, p6-5, ... and shift later IDs).
3. **UPDATE business-innovation-migration_v3.plan.md:** Replace Phase 6 todos with the new task list. Update any Phase 6 body section (task descriptions, phase goal) to match. Keep p6-1 and p6-2 completed; set p6-3 (or the first M4 subtask that is WIP) to in_progress; set new framework tasks to pending or completed per p6-3.task.md current state.
4. **CREATE or UPDATE phase-6 task files** for each new task: e.g. p6-3a.task.md, p6-3b.task.md, ... or p6-4.task.md, p6-5.task.md, ... (depending on renumbering). Each task file must have Goal, Context Files, Execution Flow, Output Requirements, and reference shape.md / p6-2 decision. For tasks that are "already done" (e.g. bi-m4-user-flow-ia), the task file can state "Completed in prior p6-3 execution" and output: verify artifact exists.
5. **Preserve p6-10 and p6-checkpoint** (milestone steps-c, checkpoint). Renumber if necessary so they follow the last M6 framework task.

### Phase: Validate

1. Phase 6 structure mirrors Phase 3/4/5: evaluate/decide (or just milestone workflow) then one task per framework/component.
2. p6-1 and p6-2 remain completed; p6-3 (or equivalent WIP task) remains in_progress; new tasks have correct status (completed vs pending) per p6-3.task.md.
3. All new task IDs have corresponding phase-6 task files. No broken references in plan body.

### Phase: Close

1. Append execution entry to shape.md (bi-m4-follow-up) Execution Log.
2. Mark this task (p4-open-migration-plan) completed in bi-m4-follow-up plan YAML.

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Updated plan | .cursor/plans/founder-migration/business-innovation-migration_v3.plan.md | YAML todos + Phase 6 body |
| New/updated task files | .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/*.task.md | One file per new task; follow p3-2 / p4-2 style |

---

## Revolving Plan Rules

- **MANDATORY:** Before opening M4, read p6-3.task.md to understand current state. Do not assume all M4 components are pending — bi-m4-user-flow-ia is done; bi-m4/workflow.md may exist; bridge and others may be pending or done in bi-m4-follow-up.
- If M5 or M6 scope (evaluate/decide) is not yet executed, opening M5/M6 means creating task placeholders (one task per component from shape or future p6-4/p6-5, p6-7/p6-8 decisions) so the structure is open; task content can reference "per p6-4/p6-5 decision" or "per p6-7/p6-8 decision" when those exist.
- **MANDATORY:** In output message, state any tasks added or removed in founder-migration plan.
