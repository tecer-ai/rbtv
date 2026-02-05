---
stepNumber: 4
stepName: 'generate-artifacts'
nextStepFile: ./step-05-create-plan.md
outputFile: '{outputFolder}/{plan-name}/{plan-name}.plan.md'
microstepTemplateFile: ../templates/plan-task-microstep-template.md
shapeTemplateFile: ../templates/shape-template.md
learningsTemplateFile: ../templates/learnings-template.md
---

# Step 04: Generate Companion Artifacts

**Progress: Step 4 of 6** — Next: Create Plan

---

## STEP GOAL

Create all companion artifacts using Write tool operations. This step REQUIRES Agent mode.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Mode Requirement
- **AGENT MODE REQUIRED** — This step uses Write tool to create files
- If in Ask mode, STOP immediately and display: "This step requires Agent mode. Please switch modes."

### Step-Specific Rules
- Load each template before generating its corresponding file
- Create ALL artifacts before presenting menu — partial completion is not acceptable
- Use explicit Write tool calls for each file — no shortcuts

---

## MANDATORY SEQUENCE

### 1. Mode Gate Check

**FIRST ACTION:** Verify Agent mode is active.

If NOT in Agent mode:
```
🛑 STOP — Agent Mode Required

This step creates files using the Write tool:
- shape.md
- learnings.md
- Phase folders
- Micro-step task files

Please switch to Agent mode and say "Continue".
```

HALT until Agent mode is confirmed.

### 2. Load Templates

Read the following templates from frontmatter paths:
- `{shapeTemplateFile}` — for shape.md structure
- `{learningsTemplateFile}` — for learnings.md structure
- `{microstepTemplateFile}` — for task file structure

### 3. Create Plan Folder Structure

Use Shell tool to create phase folders:

```
.cursor/plans/{plan-name}/
├── phase-1/
├── phase-2/
├── ...
└── phase-N/
```

Command pattern: `mkdir -p ".cursor/plans/{plan-name}/phase-{N}"`

### 4. Write shape.md

**Location:** `.cursor/plans/{plan-name}/shape.md`

Generate shape.md using `{shapeTemplateFile}` with content from step-02:

| Section | Content Source |
|---------|----------------|
| Original Shaping | Scope, key decisions, constraints from step-02 |
| User Inputs | User requirements captured during planning |
| Collaborative Decisions | AI-user decisions made during planning |
| Standards Applied | BMAD/RBTV rules governing this plan |
| Execution Log | Empty — ready for append-only entries |
| Execution Discoveries | Empty — ready for discovery entries |

**Use Write tool** to create the file.

### 5. Write learnings.md

**Location:** `.cursor/plans/{plan-name}/learnings.md`

Generate learnings.md using `{learningsTemplateFile}`:

| Section | Content |
|---------|---------|
| Purpose | System improvement queue for BMAD/RBTV meta-learnings |
| What Belongs Here | Guidelines table (from template) |
| Learning Entries | Empty — ready for append-only entries |
| Compound Generation | Instructions (from template) |

**Use Write tool** to create the file.

### 6. Generate Micro-Step Task Files

For EACH non-checkpoint task in the plan, generate a `.task.md` file.

**Location pattern:** `.cursor/plans/{plan-name}/phase-{N}/{task-id}.task.md`

**For each task, generate using `{microstepTemplateFile}`:**

```yaml
---
task_id: {task-id}
status: pending
phase: understand
complexity_score: {from step-03 assessment}
human_review: {required | optional | none}
---
```

**Content includes:**
- Goal section — what this task achieves
- Context Files — task-specific documents to load
- Tools — explicit declarations with mode (skill/subagent)
- Execution Flow — phased steps (understand → execute → validate → close)
- Discovery Handling — revolving plan rules
- Output Requirements — what to produce and where

**Use Write tool** for EACH task file individually.

### 7. Artifact Checklist

After creating all files, verify by listing the plan folder:

```
Artifacts Created:
✅ shape.md
✅ learnings.md
✅ phase-1/ ({N} task files)
✅ phase-2/ ({N} task files)
...
✅ phase-N/ ({N} task files)

Total: {count} micro-step files created
```

If ANY artifact is missing, create it before proceeding.

### 8. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[C] Continue` → Proceed to plan file creation (step-05)
- `[L] List Files` → Show all created files with paths
- `[R] Regenerate` → Recreate a specific artifact

---

## MODE GATE FOR NEXT STEP

**CRITICAL:** Before loading step-05, the agent should be in a mode that can use CreatePlan tool.

If user selects `[C] Continue`:

1. Display:
   ```
   ✅ All companion artifacts created.
   
   Next: Create the main plan file using CreatePlan tool.
   
   If you're in Agent mode, you can proceed directly.
   If CreatePlan requires Plan mode, please switch now.
   ```
2. Load `{nextStepFile}` and follow its instructions

---

## CRITICAL STEP COMPLETION NOTE

ONLY when `[C] Continue` is selected:
1. Update frontmatter: add `step-04-generate-artifacts.md` to `stepsCompleted`
2. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS CRITERIA

- ✅ Mode gate passed (Agent mode confirmed)
- ✅ All templates loaded
- ✅ Phase folders created
- ✅ shape.md written with planning context
- ✅ learnings.md written with empty structure
- ✅ ALL micro-step task files generated (one per non-checkpoint task)
- ✅ Artifact checklist displayed and verified
- ✅ Menu presented with explicit HALT

---

## FAILURE CONDITIONS

❌ **FAILURE if any of these occur:**
- Proceeding without Agent mode
- Skipping any artifact
- Using shortcuts instead of explicit Write calls
- Presenting completion menu before all artifacts exist
- Loading next step before [C] is selected
