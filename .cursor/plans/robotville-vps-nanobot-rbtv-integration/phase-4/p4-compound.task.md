---
task_id: p4-compound
status: pending
phase: understand
complexity_score: 8
human_review: optional
---

# Task p4-compound: Compound Plan Learnings

## Goal

Review `learnings.md` and compound qualifying entries into actionable BMAD/RBTV system improvements.

---

## Context Files

**MUST read every file in the table below before any execution phase.** Do not proceed to Phase: Understand until all are loaded and read.

| File | Purpose |
|------|---------|
| `.cursor/plans/robotville-vps-nanobot-rbtv-integration/learnings.md` | Source of meta-learnings collected during execution |
| `.cursor/plans/robotville-vps-nanobot-rbtv-integration/shape.md` | Discoveries and decision context that influence compound outputs |

---

## Execution Flow

### Phase: Understand

1. Read all context files.
2. Set `p4-compound` to `in_progress` in the plan file.
3. Identify entries marked as compound-ready.

### Phase: Execute

1. Group related learnings by target component and change type.
2. Draft compound output sections with concrete, implementable changes.
3. Record compounded references back into `learnings.md`.

### Phase: Validate

1. Verify each compounded change is self-contained and actionable.
2. Verify source learning references are complete.
3. Verify no project-specific implementation details are misclassified as system learnings.

### Phase: Close

1. Append execution entry to shape.md.
2. Present summary to user for approval.
3. After approval, set `p4-compound` to `completed`.

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Compounded improvement set | `.cursor/plans/robotville-vps-nanobot-rbtv-integration/learnings.md` | Grouped and traceable system improvement proposals |
