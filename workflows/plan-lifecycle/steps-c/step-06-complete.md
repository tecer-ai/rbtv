---
stepNumber: 6
stepName: 'complete'
nextStepFile: null
outputFile: '{outputFolder}/{plan-name}/{plan-name}.plan.md'
---

# Step 06: Complete

**Progress: Step 6 of 6** — Final Step

---

## STEP GOAL

Validate all artifacts exist, display completion summary, and present final options.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Step-Specific Rules
- Validate ALL artifacts before declaring success
- If any artifact is missing, return to step-05 to create it
- Display clear summary with file locations

---

## MANDATORY SEQUENCE

### 1. Validate Artifact Existence

Check that ALL required artifacts exist:

| Artifact | Path | Required |
|----------|------|----------|
| Plan file | `.cursor/plans/{plan-name}/{plan-name}.plan.md` | ✅ |
| Shape file | `.cursor/plans/{plan-name}/shape.md` | ✅ |
| Learnings file | `.cursor/plans/{plan-name}/learnings.md` | ✅ |
| Phase folders | `.cursor/plans/{plan-name}/phase-{N}/` | ✅ (one per phase) |
| Task files | `.cursor/plans/{plan-name}/phase-{N}/{task-id}.task.md` | ✅ (one per non-checkpoint task) |

**If ANY artifact is missing:**
```
⚠️ INCOMPLETE: Missing artifacts detected

Missing:
- {list missing files}

Returning to step-05 to create missing artifacts.
```

Load `./step-05-generate-artifacts.md` and re-execute.

### 2. Count Artifacts

Gather counts for summary:
- Total phases
- Total tasks (excluding checkpoints)
- Total checkpoints
- Total micro-step files

### 3. Display Completion Summary

```
✅ Plan Created Successfully

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Plan:** {plan-name}
**Location:** .cursor/plans/{plan-name}/

**Structure:**
├── {plan-name}.plan.md     (main plan)
├── shape.md                 (scope & execution log)
├── learnings.md             (system improvements)
├── phase-1/                 ({N} task files)
├── phase-2/                 ({N} task files)
...
└── phase-{N}/               ({N} task files)

**Summary:**
- {N} phases
- {N} tasks
- {N} checkpoints
- {N} micro-step files

**First task:** {first-task-id} — {first-task-description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**How to Execute This Plan:**

1. Read the task's micro-step file (e.g., `phase-1/p1-1.task.md`)
2. Follow the execution flow in the file
3. Update `shape.md` with execution log entry when complete
4. Capture any meta-learnings in `learnings.md`
5. Mark task complete in plan YAML frontmatter
```

### 4. Present Final Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[S] Start First Task` → Open `phase-1/{first-task-id}.task.md` and begin execution
- `[V] View Plan` → Display the complete plan file
- `[O] Open Folder` → Show the plan folder location
- `[D] Done` → Exit workflow (plan is saved and ready)

---

## WORKFLOW COMPLETE

This completes the Create workflow. The plan and all supporting files are saved and ready for execution.

---

## SUCCESS CRITERIA

- ✅ All artifacts validated (plan, shape, learnings, phase folders, task files)
- ✅ Counts gathered accurately
- ✅ Completion summary displayed with full structure
- ✅ Execution instructions provided
- ✅ Final menu presented with explicit HALT

---

## CRITICAL STEP COMPLETION NOTE

This is the final step. When user selects:

- `[S] Start First Task` → Load and display the first task file
- `[V] View Plan` → Read and display the plan file
- `[O] Open Folder` → Show the folder path
- `[D] Done` → Exit with: "Plan creation complete. Good luck with execution!"
