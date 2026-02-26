---
task_id: p4-refs
status: completed
phase: understand
complexity_score: 6
human_review: none
---

# Task p4-refs: Verify all internal markdown links

## Goal

Verify all internal markdown links in files modified by this plan resolve correctly.

---

## Context Files

**MUST read every file in the table below before any execution phase.** Do not proceed to Phase: Understand until all are loaded and read.

| File | Purpose |
|------|---------|
| `.cursor/plans/rbtv-tools-manifest/shape.md` | Execution log — list of all modified files |

---

## Execution Flow

### Phase: Understand

1. **MUST** read every file in the Context Files table above. Do not continue until all are read.
2. In the plan file (the `.plan.md` in this plan's directory), set this task's todo to `status: in_progress`.
3. Review shape.md execution log to compile the complete list of files modified by this plan.

### Phase: Execute

1. For each modified file, search for markdown links (patterns: `[text](path)`, backtick file references).
2. For each link target, verify the referenced file exists at the specified path.
3. Compile a list of broken links (if any).

**Discovery Handling:**
- If broken links found and fix is simple (<5 min): Fix immediately, document in shape.md.
- If broken links require complex changes: Add new task to plan.

### Phase: Validate

1. Verify deliverable meets goal statement.
2. Confirm zero broken internal links across all modified files.

### Phase: Close

1. Append execution entry to shape.md (never modify existing entries).
2. **MUST** present a brief summary to the user (max 2000 characters) of what was done. Do not mark complete until the user approves.
3. After user approval, set this task's todo to `status: completed` in the plan file.
4. Notify user of completion and any plan changes.

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Link verification report | Reported to user | Summary with any broken links identified |

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
