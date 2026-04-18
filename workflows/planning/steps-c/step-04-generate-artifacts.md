---
stepNumber: 4
stepName: 'generate-artifacts'
nextStepFile: null
microstepTemplateFile: ../templates/plan-task-microstep-template.md
shapeTemplateFile: '{rbtv_path}/workflows/_shared/templates/shape-template.md'
learningsTemplateFile: ../templates/learnings-template.md
templateFile: ../templates/plan-template.md
---

# Step 04: Generate All Artifacts

**Progress: Step 4 of 4** — Final Step

---

## STEP GOAL

Create all plan artifacts: companion files (shape.md, learnings.md), micro-step task files, and the main plan file. Validate and present summary.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Step-Specific Rules
- Load each template before generating its corresponding file
- Create ALL artifacts before presenting menu — partial completion is not acceptable
- Use explicit Write tool calls for each file

---

## MANDATORY SEQUENCE

### 1. Load Templates

Read the following templates from frontmatter paths:
- `{shapeTemplateFile}` — for shape.md structure
- `{learningsTemplateFile}` — for learnings.md structure
- `{microstepTemplateFile}` — for task file structure
- `{templateFile}` — for plan file structure

### 2. Create Phase Folders

Create phase folders inside the plan folder:

```
{output-path}/{plan-name}/
├── phase-1/
├── phase-2/
├── ...
└── phase-N/
```

### 3. Write shape.md

**Location:** `{output-path}/{plan-name}/shape.md`

**Check for existing shape.md first.** The context preservation rule may have already created a shape.md during planning conversations.

**If shape.md already exists:**

1. Read the existing shape.md
2. Merge planning context into it — preserve all existing content (Decisions and Discoveries entries written by the context preservation rule)
3. Fill or update these sections from step-02 context:

| Section | Action |
|---------|--------|
| Original Shaping | Fill if empty; if already populated, preserve existing and append any missing scope/decisions/constraints from step-02 |
| User Inputs | Fill if empty; append any missing entries |
| Collaborative Decisions | Fill if empty; append any missing entries |
| Standards Applied | Fill (plan-specific section) |

4. Use Edit tool to update existing sections — never overwrite the file

**If shape.md does NOT exist:**

Generate shape.md using `{shapeTemplateFile}` with content from step-02:

| Section | Content Source |
|---------|----------------|
| Original Shaping | Scope, key decisions, constraints from step-02 |
| User Inputs | User requirements captured during planning |
| Collaborative Decisions | AI-user decisions made during planning |
| Standards Applied | BMAD/RBTV rules governing this plan |
| Decisions and Discoveries | Empty — ready for append-only entries |

Use Write tool to create the file.

### 4. Write learnings.md

**Location:** `{output-path}/{plan-name}/learnings.md`

Generate learnings.md using `{learningsTemplateFile}`:

| Section | Content |
|---------|---------|
| Purpose | System improvement queue for BMAD/RBTV meta-learnings |
| What Belongs Here | Guidelines table (from template) |
| Learning Entries | Empty — ready for append-only entries |
| Compound Generation | Instructions (from template) |

Use Write tool to create the file.

### 5. Generate Micro-Step Task Files

For each task, decide whether it needs a micro-step file:

**Generate a `.task.md` file when ANY of these apply:**
- Task requires loading 2+ context files
- Task uses specialized RBTV tools (skills, sub-agents)
- Task has 3+ distinct substeps
- Task requires phased execution (understand → execute → validate)
- Task is a checkpoint

**Skip micro-step file when ALL of these apply:**
- Task is self-explanatory from its description
- Single action, completable in one step
- No special context files or tools needed

**For tasks that need a micro-step file:**

**Location pattern:** `{output-path}/{plan-name}/phase-{N}/{task-id}.task.md`

Generate using `{microstepTemplateFile}` with:

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
- Context Files — task-specific documents to load. **Path format:** files outside the plan folder use project-root-relative paths; files inside the plan folder use file-relative paths (e.g., `../shape.md`). See Plan Linking Standard in `plan-creation-rules.md`.
- Tools section — ONLY if task requires specialized RBTV skills/sub-agents (omit for basic Read/Write/Bash tasks)
- Execution Flow — phased steps (understand → execute → validate → close)
- Discovery Handling — revolving plan rules
- Output Requirements — what to produce and where

**For checkpoint task files:**

Generate a task file that contains:
- **Goal** — evaluate phase deliverables against review criteria
- **Work to Evaluate** — summary of what the phase produced (files, artifacts, with paths)
- **Review Criteria** — 3-7 specific criteria from the phase's tasks, architectural constraints, and acceptance criteria
- **Execution Flow** — evaluate each criterion, present findings summary, HALT for human approval, do not advance if rejected

**Use Write tool for EACH task file individually.**

### 6. Write Plan File

**Location:** `{output-path}/{plan-name}/{plan-name}-plan.md`

Generate the plan document per `{templateFile}`:

1. **YAML Frontmatter** — `name` and `overview` only
2. **Title** — `# {Plan Name}`
3. **Reference directive** — shape.md and task file pointers
4. **Architectural Constraints** — plan-specific patterns and execution rules
5. **Revolving Plan Rules** — discovery handling (keep brief)
6. **Execution Workflow** — Mermaid diagram from step-03, ONLY if plan is non-linear
7. **Tasks** — Markdown checkbox list grouped by phase with `→ path` suffix for tasks with micro-step files

Use Write tool to create the file.

### 7. Validate Artifacts

**7a. Core artifacts exist:**

| Artifact | Path | Required |
|----------|------|----------|
| Plan file | `{output-path}/{plan-name}/{plan-name}-plan.md` | ✅ |
| Shape file | `{output-path}/{plan-name}/shape.md` | ✅ |
| Learnings file | `{output-path}/{plan-name}/learnings.md` | ✅ |
| Phase folders | `{output-path}/{plan-name}/phase-{N}/` | ✅ (one per phase) |

**7b. Task file references resolve:**

For every task in the plan's task list that has a `→ path` suffix, verify the referenced file exists on disk.

For every `.task.md` file on disk in phase folders, verify a matching `→ path` reference exists in the plan's task list.

**7c. Plan Linking Standard:**

Search all files inside the plan folder for path violations:
- No file contains an absolute or root-relative path referencing the plan folder itself
- All intra-plan references use `./` or `../` relative paths

**If ANY validation fails**, fix the issue before proceeding.

### 8. Present Completion Summary

```
✅ Plan Created Successfully

**Plan:** {plan-name}
**Location:** {output-path}/{plan-name}/

**Summary:**
- {N} phases
- {N} tasks
- {N} checkpoints
- {N} micro-step files

**First task:** {first-task-id} — {first-task-description}

**How to Execute:**
1. Check if the task has a file reference (`→ path`)
2. If yes: read that file and follow its execution phases
3. If no: execute directly from the task description
4. Append to shape.md after each task
5. Mark task complete in plan task list (`[x]`)
```

### 9. Present Final Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[S] Start First Task` → Open first task's micro-step file and begin execution
- `[V] View Plan` → Display the plan file
- `[D] Done` → Exit workflow (plan is saved and ready)

---

## WORKFLOW COMPLETE

This completes the Create workflow. The plan and all supporting files are saved and ready for execution.

---

## SUCCESS CRITERIA

- ✅ All templates loaded
- ✅ Phase folders created
- ✅ shape.md written with planning context (merged if pre-existing, created if not)
- ✅ learnings.md written with empty structure
- ✅ Micro-step task files generated for complex tasks and checkpoints
- ✅ Plan file written with Markdown task list
- ✅ Task file references link correctly (`→ path` ↔ file on disk)
- ✅ Plan Linking Standard validated (no brittle self-references)
- ✅ Completion summary displayed
- ✅ Menu presented with explicit HALT
