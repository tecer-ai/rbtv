---
stepNumber: 4
stepName: 'finalize'
nextStepFile: null
outputFile: '{plans_folder}/{plan-name}/{plan-name}.plan.md'
templateFile: ../templates/plan-template.md
---

# Step 04: Finalize and Write Plan

**Purpose:** Write the complete plan file and create initial execution decisions log.

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Load Template

- Read `{templateFile}` from frontmatter
- Use template structure for output file

### 2. Compile YAML Frontmatter

Generate the `todos` array from the task structure:

```yaml
---
name: {plan-name}
overview: "{One-sentence summary of what this plan accomplishes}"
todos:
  - id: p1-1
    content: "p1-1: Create plan folder and initial execution decisions file"
    status: pending
  - id: p1-2
    content: "p1-2: [Task description]"
    status: pending
  # ... all tasks ...
isProject: false
---
```

### 3. Write Plan Body

Compile the complete plan document:

1. **Title** — `# {Plan Name}`
2. **Context Section** — From step-02 (Problem, Goals, Constraints, Decisions, Rejected)
3. **Files to Load Table** — From step-02
4. **Workflow Diagram** — Mermaid diagram from step-03
5. **Phase Sections** — For each phase:
   - Phase header with goal
   - Task list with descriptions
   - Checkpoint (where applicable)

### 4. Create Plan Folder

Create the folder structure:

```
.cursor/plans/{plan-name}/
└── {plan-name}.plan.md
```

### 5. Write Plan File

Write the complete plan to: `.cursor/plans/{plan-name}/{plan-name}.plan.md`

### 6. Create Initial Execution Decisions Log

Create an initial execution decisions file to establish the logging structure:

**Location:** `.cursor/plans/{plan-name}/p1-1_execution_decisions.md`

**Content:**

```markdown
# Task p1-1 Execution Decisions

**Task:** Create plan folder and initial execution decisions file
**Completed:** {current-date}
**Attempts:** 1
**Outcome:** Approved

---

## Outcome

Plan folder and initial structure created. Plan is ready for execution.

## Key Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Used plan workflow | Followed BMAD best practices | Ensures consistent plan structure |

## Files Modified

- `.cursor/plans/{plan-name}/{plan-name}.plan.md` — Created
- `.cursor/plans/{plan-name}/p1-1_execution_decisions.md` — Created
```

### 7. Update First Task Status

Mark `p1-1` as completed in the plan's YAML frontmatter:

```yaml
- id: p1-1
  content: "p1-1: Create plan folder and initial execution decisions file"
  status: completed
```

### 8. Display Completion Summary

```
✅ Plan Created Successfully

**Plan:** {plan-name}
**Location:** .cursor/plans/{plan-name}/{plan-name}.plan.md
**Tasks:** {count} tasks across {count} phases
**Checkpoints:** {count} checkpoints

**First task completed:** p1-1 (create log infrastructure)
**Next task:** p1-2

---

To execute this plan, work through tasks in order. For each task:
1. Read prior execution decisions
2. Execute work and invoke judge
3. Write execution decisions

Would you like to start executing the plan now?
```

### 9. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[E] Execute Plan` → Start executing tasks (route to Execute workflow)
- `[V] View Plan` → Display the complete plan file
- `[D] Done` → Exit workflow (plan is saved)

---

## WORKFLOW COMPLETE

This completes the Create workflow. The plan is saved and ready for execution.

---

## SUCCESS CRITERIA

- ✅ Plan file written to correct location
- ✅ YAML frontmatter contains all tasks with correct IDs
- ✅ Context section is complete and self-contained
- ✅ Files to Load table included
- ✅ Mermaid workflow diagram included
- ✅ Phase sections with task descriptions
- ✅ Initial execution decisions log created (p1-1)
- ✅ First task marked completed
- ✅ Completion summary displayed
- ✅ Menu presented with explicit HALT
