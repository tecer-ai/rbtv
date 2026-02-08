---
task_id: p4-compound
status: pending
phase: understand
complexity_score: 7
human_review: none
---

# Task p4-compound: Review learnings.md and compound into system improvements

## Goal

Process all learnings captured in `learnings.md` during plan execution and generate actionable system improvement proposals for BMAD/RBTV.

---

## Context Files

**MUST read every file in the table below before any execution phase.** Do not proceed to Phase: Understand until all are loaded and read.

| File | Purpose |
|------|---------|
| `.cursor/plans/rbtv-tools-manifest/shape.md` | Full execution context |
| `.cursor/plans/rbtv-tools-manifest/learnings.md` | Learnings to process |

---

## Execution Flow

### Phase: Understand

1. **MUST** read every file in the Context Files table above. Do not continue until all are read.
2. In the plan file (the `.plan.md` in this plan's directory), set this task's todo to `status: in_progress`.
3. Review all learning entries in learnings.md.
4. Identify which learnings are compound-ready (all 4 checkboxes checked).

### Phase: Execute

1. If NO learnings exist: Report "No learnings captured during execution" and skip to Close phase.
2. If learnings exist:
   a. Group compound-ready learnings by target component.
   b. For each group, generate a compound section with specific changes and implementation notes.
   c. Append compound output to learnings.md.
   d. Mark processed learnings with "Compounded: YYYY-MM-DD" line.

**Discovery Handling:**
- If simple discovery (<5 min to resolve): Resolve immediately, document in shape.md
- If complex discovery: Add new task to plan, notify user of task addition

### Phase: Validate

1. Verify deliverable meets goal statement.
2. Confirm all compound-ready learnings were processed.
3. Confirm compound output is actionable and specific.

### Phase: Close

1. Append execution entry to shape.md (never modify existing entries).
2. **MUST** present a brief summary to the user (max 2000 characters) of what was done. Do not mark complete until the user approves.
3. After user approval, set this task's todo to `status: completed` in the plan file.
4. Notify user of completion and any plan changes.

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Compound proposals | `.cursor/plans/rbtv-tools-manifest/learnings.md` (appended) | Markdown compound sections |

---

## Revolving Plan Rules

**When discoveries occur:**
- Append discovery to shape.md Execution Discoveries section
- If work is complex (>5 min), add new task to plan with next available ID
- If work is simple, perform immediately and document
- **MANDATORY**: In output message, clearly state any tasks added or removed

**Task change notification format:**
```
PLAN MODIFIED:
- Added: {task-id} - {description}
- Removed: {task-id} - {reason}
```
