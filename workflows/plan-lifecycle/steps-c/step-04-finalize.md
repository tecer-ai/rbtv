---
stepNumber: 4
stepName: 'finalize'
nextStepFile: null
outputFile: '{outputFolder}/{plan-name}/{plan-name}.plan.md'
templateFile: ../templates/plan-template.md
microstepTemplateFile: ../templates/plan-task-microstep-template.md
shapeTemplateFile: ../templates/shape-template.md
learningsTemplateFile: ../templates/learnings-template.md
---

# Step 04: Finalize and Write Plan

**Purpose:** Write the complete plan file, companion files (shape.md, learnings.md), and generate micro-step task files.

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Load Templates

- Read `{templateFile}` from frontmatter for plan structure
- Read `{microstepTemplateFile}` for task file structure
- Read `{shapeTemplateFile}` for shape.md structure
- Read `{learningsTemplateFile}` for learnings.md structure

### 2. Compile YAML Frontmatter

Generate the `todos` array from the task structure:

```yaml
---
name: {plan-name}
overview: "{One-sentence summary of what this plan accomplishes}"
todos:
  - id: p1-1
    content: "p1-1: [Task description]"
    status: pending
  # ... all tasks ...
  - id: pN-compound
    content: "pN-compound: Review learnings.md and compound into system improvements"
    status: pending
isProject: false
---
```

### 3. Write Plan Body

Compile the complete plan document:

1. **Title** — `# {Plan Name}`
2. **Architecture Overview** — Mermaid diagram from step-03
3. **Phase Sections** — For each phase:
   - Phase header with goal
   - Task list with descriptions
   - Checkpoint (where applicable)
4. **Key Files Summary** — Organized by phase with Action/File columns

### 4. Create Plan Folder Structure

Create the complete folder structure:

```
.cursor/plans/{plan-name}/
├── {plan-name}.plan.md
├── shape.md
├── learnings.md
├── phase-1/
│   ├── p1-1.task.md
│   ├── p1-2.task.md
│   └── ...
├── phase-2/
│   └── ...
└── phase-N/
    └── pN-compound.task.md
```

### 5. Write Plan File

Write the complete plan to: `.cursor/plans/{plan-name}/{plan-name}.plan.md`

### 6. Write shape.md

Create shape.md using `{shapeTemplateFile}` with content from step-02:

- **Original Shaping** section (immutable): scope, key decisions, constraints, user inputs
- **Standards Applied** section: rules governing the plan
- **Execution Log** section: empty, ready for append-only entries
- **Execution Discoveries** section: empty, ready for discovery entries

### 7. Write learnings.md

Create learnings.md using `{learningsTemplateFile}`:

- Purpose statement: System improvement queue for BMAD/RBTV meta-learnings
- Empty structure ready for learning entries during execution
- Per-learning format: source task, trigger, category, user words, recommended change

### 8. Generate Micro-Step Task Files

For each task in the plan, generate a task file using `{microstepTemplateFile}`:

**Location:** `.cursor/plans/{plan-name}/phase-{N}/{task-id}.task.md`

**Content includes:**
- YAML frontmatter: task_id, status, phase, complexity_score, human_review
- Goal section: what this task achieves
- Context Files: task-specific documents to load
- Tools: explicit declarations with mode (skill/subagent)
- Execution Flow: phased steps (understand → execute → validate → close)
- Discovery Handling: revolving plan rules
- Output Requirements: what to produce and where

### 9. Display Completion Summary

```
✅ Plan Created Successfully

**Plan:** {plan-name}
**Location:** .cursor/plans/{plan-name}/

**Structure:**
- Plan file: {plan-name}.plan.md
- Companion files: shape.md, learnings.md
- Task files: {count} micro-step files across {count} phases

**Tasks:** {count} tasks across {count} phases
**Checkpoints:** {count} checkpoints
**First task:** {first-task-id}

---

Plans are self-executing. To work on this plan:
1. Read the task's micro-step file (e.g., phase-1/p1-1.task.md)
2. Follow the execution flow in the file
3. Update shape.md with execution log entry when complete
4. Capture any meta-learnings in learnings.md
```

### 10. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[S] Start First Task` → Open and begin first task file
- `[V] View Plan` → Display the complete plan file
- `[D] Done` → Exit workflow (plan is saved)

---

## WORKFLOW COMPLETE

This completes the Create workflow. The plan and all supporting files are saved and ready for execution.

---

## SUCCESS CRITERIA

- ✅ Plan file written to correct location
- ✅ YAML frontmatter contains all tasks with correct IDs
- ✅ Architecture diagram included
- ✅ Phase sections with task descriptions
- ✅ shape.md created with original shaping content
- ✅ learnings.md created with empty structure
- ✅ Phase folders created (phase-1/, phase-2/, etc.)
- ✅ Micro-step task files generated for all tasks
- ✅ Final compound task included (pN-compound)
- ✅ Completion summary displayed
- ✅ Menu presented with explicit HALT
