---
stepNumber: 5
stepName: 'create-plan'
nextStepFile: ./step-06-complete.md
outputFile: '{outputFolder}/{plan-name}/{plan-name}.plan.md'
templateFile: ../templates/plan-template.md
---

# Step 05: Create Plan File

**Progress: Step 5 of 6** — Next: Complete

---

## STEP GOAL

Create the main plan file using the CreatePlan tool. Companion artifacts were already created in step-04.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Step-Specific Rules
- The CreatePlan tool ONLY creates the `.plan.md` file
- Companion files (shape.md, learnings.md, micro-step files) were already created in step-04
- The plan file completes the artifact set

---

## MANDATORY SEQUENCE

### 1. Load Plan Template

Read `{templateFile}` from frontmatter to understand plan file structure.

### 2. Compile YAML Frontmatter

Generate the `todos` array from the task structure created in step-03. Each todo item carries ONLY `id`, `content`, and `status`. Do NOT add custom fields — Cursor's YAML serializer strips unrecognized fields when task status updates. Task file paths are embedded in the `content` field using `[brackets]` suffix (e.g., `"p1-1: Description [phase-1/p1-1.task.md]"`).

```yaml
---
name: {plan-name}
overview: "{One-sentence summary of what this plan accomplishes}"
todos:
  - id: p1-1
    content: "p1-1: [Task description]"
    status: pending
  - id: p1-checkpoint
    content: "P1 CHECKPOINT - [Description]"
    status: pending
  # ... all tasks ...
  - id: pN-compound
    content: "pN-compound: Review learnings.md and compound into system improvements"
    status: pending
isProject: false
---
```

Checkpoint review prompts go in the plan body, not YAML. See step 3.

### 3. Compile Plan Body

Generate the slim plan document per the plan-template.md structure:

1. **Title** — `# {Plan Name}`
2. **Reference directive** — shape.md and .task.md pointers
3. **Architectural Constraints** — plan-specific patterns and inviolable rules (include quality-review checkpoint enforcement in Inviolable Rules)
4. **Checkpoint Execution Protocol** — standardized 5-step protocol for checkpoint review prompts (from template)
5. **Revolving Plan Rules** — discovery handling (keep brief)
6. **Execution Workflow** — Mermaid diagram from step-03, ONLY if plan is non-linear (omit for sequential plans)
7. **Phase Sections** — Phase name + goal + `#### P{N} Checkpoint Review Prompt` subsection with blockquoted review prompt (composed in step-03)

Do NOT include: Context section, Folder Structure, Files to Load table, Self-Execution Instructions, or Companion Files table. These live in shape.md and microstep files.

### 4. Create Plan File

Use the **CreatePlan** tool to write the plan file.

**NOTE:** The CreatePlan tool uses Cursor's default location (`~/.cursor/plans/`) and adds a hash suffix to the filename. This will be corrected in the next step.

### 5. Move Plan to Artifact Folder

**MODE CHECK:** If in Ask mode, display:

```
⚠️ MODE SWITCH REQUIRED

Plan file created at Cursor's default location with hash suffix.
To consolidate with artifacts, I need to:
1. Move the plan file to the artifact folder
2. Remove the hash suffix from the filename

Please switch to Agent mode, then say "Continue".
```

**HALT and wait for Agent mode confirmation.**

**When in Agent mode:**

1. Identify the created plan file path from CreatePlan tool output
2. Extract the hash suffix (e.g., `_84b32579` from `plan-name_84b32579.plan.md`)
3. Move plan file to: `{outputFolder}/{plan-name}/{plan-name}.plan.md`
4. Verify move succeeded

**Command pattern:**
```powershell
Move-Item -Path "{cursor-default-path}/{plan-name}_{hash}.plan.md" -Destination "{outputFolder}/{plan-name}/{plan-name}.plan.md"
```

### 6. Confirm Plan Consolidation

Display confirmation:

```
✅ Plan consolidated at: {outputFolder}/{plan-name}/

All artifacts complete:
✅ shape.md
✅ learnings.md
✅ Phase folders with micro-step task files
✅ {plan-name}.plan.md
```

### 7. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[C] Continue` → Proceed to completion summary (step-06)
- `[V] View Plan` → Display the consolidated plan file
- `[X] Exit Workflow` → Exit now (all artifacts consolidated in one location)

---

## CRITICAL STEP COMPLETION NOTE

ONLY when `[C] Continue` is selected:
1. Update frontmatter: add `step-05-create-plan.md` to `stepsCompleted`
2. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS CRITERIA

- ✅ Plan template loaded
- ✅ YAML frontmatter compiled with all tasks (only `id`, `content`, `status` per item — task file paths in `[brackets]` inside `content`)
- ✅ Plan body is slim — no duplication of shape.md, microstep, or YAML content
- ✅ CreatePlan tool used to write plan file
- ✅ Plan file moved from Cursor default location to artifact folder
- ✅ Hash suffix removed from plan filename
- ✅ All artifacts consolidated in `{outputFolder}/{plan-name}/`
- ✅ Menu presented with explicit HALT
