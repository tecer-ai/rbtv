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

For each non-checkpoint task, decide whether it needs a micro-step file or can use inline YAML content:

**Generate a `.task.md` file when ANY of these apply:**
- Task requires loading 2+ context files
- Task uses specialized RBTV tools (subagents, skills)
- Task has 3+ distinct substeps
- Task requires phased execution (understand → execute → validate)
- Task produces output that needs quality review

**Skip micro-step file when ALL of these apply:**
- Task is self-explanatory from its YAML `content` description
- Single action, completable in one step
- No special context files or tools needed

**For tasks that need a micro-step file:**

**Location pattern:** `.cursor/plans/{plan-name}/phase-{N}/{task-id}.task.md`

Generate using `{microstepTemplateFile}`:

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
- Context Files — task-specific documents to load. **Path format:** files outside the plan folder use project-root-relative paths (e.g., `workflows/plan-lifecycle/workflow.md`); files inside the plan folder use file-relative paths (e.g., `../shape.md`). See Plan Linking Standard in `plan-creation-rules.md`.
- Tools section — ONLY if task requires specialized RBTV skills/subagents (omit for basic Read/Write/Shell tasks). When including Tools: add pointer to `_bmad/rbtv/_config/tools-manifest.csv` for available tools
- Execution Flow — phased steps (understand → execute → validate → close)
- Discovery Handling — revolving plan rules
- Output Requirements — what to produce and where

**After generating each micro-step file:**
- Set `taskFile: "phase-{N}/{task-id}.task.md"` in the corresponding YAML todo entry
- The `taskFile` path is relative to the plan folder

**For simple tasks (no micro-step file):**
- Ensure the YAML `content` field contains a complete, actionable description
- Omit the `taskFile` field entirely — do NOT add an empty or null `taskFile`
- Add a comment in the plan YAML: `# inline — no micro-step file`

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
- ✅ Micro-step task files generated for complex tasks (per decision criteria)
- ✅ `taskFile` field set in YAML for every task that has a micro-step file
- ✅ `taskFile` field omitted for simple tasks (no micro-step file)
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
