---
task_id: p4-fix-m5m6-structure
status: pending
phase: understand
complexity_score: 8
human_review: none
---

# Task p4-fix-m5m6-structure: Fix M5 and M6 Task Structure

## Goal

FIX M5 and M6 task structure in business-innovation-migration_v3.plan.md by removing unnecessary evaluate/decide phases and opening them directly like M1-M3, per the existing integration strategy already defined in the plan.

---

## Context Files

| File | Purpose |
|------|---------|
| .cursor/plans/founder-migration/business-innovation-migration_v3.plan.md | Plan to fix |
| .cursor/plans/founder-migration/business-innovation-migration_v3/shape.md | Reference for integration strategy |
| .cursor/plans/founder-migration/business-innovation-migration_v3/phase-3/p3-2.task.md | Reference: M1 framework task pattern |

---

## Problem

The integration strategy for M5 and M6 is **already defined** in the plan:
- **M5 Market Validation**: RBTV-native — customer validation is founder-specific, minimal BMAD overlap
- **M6 MVP**: Full BMAD integration — all software development routes to BMAD workflows

However, p4-open-migration-plan incorrectly structured M5 and M6 with evaluate/decide phases (p6-9/p6-10 for M5, p6-12/p6-13 for M6), which adds unnecessary overhead. These evaluate/decide phases were appropriate for M4 (which needed evaluation), but M5 and M6 should be opened directly like M1-M3 since their integration approach is already determined.

---

## Execution Flow

### Phase: Understand

1. Read business-innovation-migration_v3.plan.md Phase 6 Integration Strategy section
2. Confirm M5 strategy: RBTV-native (like M1-M3, just different frameworks)
3. Confirm M6 strategy: Full BMAD routing (minimal RBTV wrapper)
4. Review M1-M3 task structure (Phase 3, 4, 5) for pattern

### Phase: Execute

**M5 Market Validation — Open Like M1-M3:**

1. Remove tasks p6-9 (Evaluate M5) and p6-10 (Decide M5)
2. Replace p6-11 (bundled placeholder) with specific M5 framework tasks:
   - p6-9: CREATE bi-m5 milestone workflow
   - p6-10: CREATE bi-m5-customer-interviews (or first M5 framework per source)
   - p6-11: CREATE bi-m5-problem-validation (or second M5 framework)
   - p6-12: CREATE bi-m5-solution-validation (or third M5 framework)
   - ... (continue for all M5 frameworks per refs/founder/m5_market_validation/)
   - p6-X: UPDATE mentor agent for M5 routing

3. Renumber subsequent tasks accordingly

**M6 MVP — Open Like M1-M3 (Minimal):**

Since M6 routes entirely to BMAD, create minimal tasks:
   - p6-Y: CREATE bi-m6 milestone workflow (minimal, routes to BMAD)
   - p6-Y+1: UPDATE mentor agent for M6 routing to BMAD workflows

4. UPDATE business-innovation-migration_v3.plan.md:
   - YAML todos: Replace M5/M6 evaluate/decide/bundled with specific framework tasks
   - Phase 6 body: Update M5 and M6 task lists

5. CREATE/UPDATE phase-6 task files:
   - Delete p6-9.task.md, p6-10.task.md (M5 evaluate/decide - no longer needed)
   - Delete p6-12.task.md, p6-13.task.md (M6 evaluate/decide - no longer needed)
   - Update p6-11.task.md → p6-9.task.md (M5 milestone)
   - Create p6-10, p6-11, ... (M5 framework tasks)
   - Update p6-14.task.md → p6-X.task.md (M6 minimal tasks)
   - Renumber p6-15.task.md (steps-c) to new position

### Phase: Validate

1. Verify M5 follows M1-M3 pattern (one task per framework)
2. Verify M6 is minimal (milestone workflow + mentor update, routes to BMAD)
3. Verify no evaluate/decide phases remain for M5 or M6
4. Verify all task IDs are sequential
5. Verify integration strategy matches plan's original intent

### Phase: Close

1. Append execution entry to shape.md (bi-m4-follow-up)
2. Append execution entry to shape.md (founder-migration)
3. Mark task status as completed in bi-m4-follow-up plan YAML

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Updated plan | .cursor/plans/founder-migration/business-innovation-migration_v3.plan.md | YAML todos + Phase 6 body |
| M5 task files | .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-9.task.md, p6-10.task.md, ... | Task files following p3-2 pattern |
| M6 task files | .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-X.task.md, ... | Minimal task files |
| Deleted files | phase-6/p6-9.task.md (old evaluate M5), p6-10.task.md (old decide M5), p6-12.task.md (old evaluate M6), p6-13.task.md (old decide M6) | Removed |

---

## Revolving Plan Rules

**MANDATORY:** Before executing, read refs/founder/m5_market_validation/ to identify all M5 frameworks. The plan should specify exactly which M5 frameworks exist (don't assume).

**MANDATORY:** In output message, state the exact number of tasks in Phase 6 before and after this fix.
