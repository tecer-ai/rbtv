---
stepNumber: 3
stepName: 'document-decisions'
nextStepFile: ./step-01-init.md
---

# Step 03: Document Execution Decisions

**Purpose:** Write execution decisions log and update plan status.

**This is Step 3 of the 3-step guardrail workflow.**

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Determine Documentation Type

Based on task type:

| Task Type | Documentation Behavior |
|-----------|------------------------|
| Regular task | Create `[task_id]_execution_decisions.md` |
| Phase condensation | Create merged phase file (no separate log) |
| Checkpoint | Append to phase file if changes needed |
| File reference review | Append to phase file if changes made |
| Final condensation | Create merged plan-level file (no separate log) |

### 2. Write Execution Decisions (Regular Tasks)

Create file: `.cursor/plans/{plan-name}/{task_id}_execution_decisions.md`

**Content:**

```markdown
# Task {task_id} Execution Decisions

**Task:** {task description}
**Completed:** {YYYY-MM-DD}
**Attempts:** {N}
**Outcome:** {Approved/Blocked/Required escalation}

---

## Outcome

{Brief summary of what was delivered or why task couldn't be completed}

## Key Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| {Choice made} | {Why} | {Effect on future tasks} |

## Issues Encountered

- {Blocker or surprise that future agents should know}

## Files Modified

- {List of files changed}
```

### 3. Handle Phase Condensation (If Applicable)

When task is phase condensation:

1. Read all `*_execution_decisions.md` files for this phase
2. Merge into single file: `{phase}_execution_decisions.md`
3. Preserve: Key decisions, issues encountered, files modified
4. Remove: Attempt details, verbose summaries
5. Delete source files after successful merge
6. Maintain chronological order by task ID

### 4. Update Plan Status

Update the plan file's YAML frontmatter:

1. Mark current task as `completed`:
   ```yaml
   - id: {task-id}
     content: "{task description}"
     status: completed
   ```

2. If next task exists, keep as `pending` (will become `in_progress` when started)

### 5. Check for Next Task

Determine what comes next:

- If more `pending` tasks exist → Loop back to step-01-init for next task
- If all tasks `completed` → Plan execution complete

### 6. Display Progress

```
## Task Completed

**Task:** {task-id} - {description}
**Status:** ✅ Completed
**Execution Log:** .cursor/plans/{plan-name}/{task_id}_execution_decisions.md

---

**Plan Progress:** {completed}/{total} tasks

**Next Task:** {next-task-id} - {description}
  OR
**Plan Complete!** All tasks finished.
```

### 7. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**If more tasks remain:**
- `[C] Continue` → Proceed to next task (loop to step-01)
- `[V] View Progress` → Show detailed plan status
- `[X] Exit` → Save state and exit

**If plan complete:**
- `[S] Summary` → Show complete execution summary
- `[D] Done` → Exit workflow

---

## NEXT STEP

On Continue selection (more tasks remain):
1. Load and execute: `./step-01-init.md` (loops back for next task)

On Done selection (plan complete):
1. Exit workflow gracefully

---

## SUCCESS CRITERIA

- ✅ Execution decisions file created with all required sections
- ✅ Key decisions documented with rationale
- ✅ Issues encountered recorded for future agents
- ✅ Files modified listed
- ✅ Plan YAML frontmatter updated (task status changed)
- ✅ Progress displayed accurately
- ✅ Menu presented with explicit HALT
