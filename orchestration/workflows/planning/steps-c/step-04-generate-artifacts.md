---
stepNumber: 4
stepName: 'generate-artifacts'
nextStepFile: null
microstepTemplateFile: ../templates/plan-task-microstep-template.md
decisionsTemplateFile: '{rbtv_path}/orchestration/workflows/_shared/templates/decisions-template.md'
deliverablesTemplateFile: ../templates/deliverables-template.md
templateFile: ../templates/plan-template.md
---

# Step 04: Generate All Artifacts

**Progress: Step 4 of 4** — Final Step

---

## STEP GOAL

Create all plan artifacts: companion files (decisions.md, deliverables.md), spec files (code work), micro-step task files, and the main plan file. Validate and present summary.

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
- `{decisionsTemplateFile}` — for decisions.md structure
- `{deliverablesTemplateFile}` — for deliverables.md structure
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

### 3. Write decisions.md

**Location:** `{output-path}/{plan-name}/decisions.md`

**Check for existing decisions.md first.** The context preservation rule may have already created a decisions.md during planning conversations.

**If decisions.md already exists:**

1. Read the existing decisions.md
2. Merge planning context into it — preserve all existing content (Decisions and Discoveries entries written by the context preservation rule)
3. Fill or update these sections from step-02 context:

| Section | Action |
|---------|--------|
| Original Shaping | Fill if empty; if already populated, preserve existing and append any missing scope/decisions/constraints from step-02 |
| User Inputs | Fill if empty; append any missing entries |
| Collaborative Decisions | Fill if empty; append any missing entries |
| Standards Applied | Fill (plan-specific section) |

4. Use Edit tool to update existing sections — never overwrite the file

**If decisions.md does NOT exist:**

Generate decisions.md using `{decisionsTemplateFile}` with content from step-02:

| Section | Content Source |
|---------|----------------|
| Original Shaping | Scope, key decisions, constraints from step-02 (record the orchestration flag + mode, and the code-work flag, as Key Decisions when set) |
| User Inputs | User requirements captured during planning |
| Collaborative Decisions | AI-user decisions made during planning |
| Standards Applied | RBTV rules governing this plan |
| Decisions and Discoveries | Empty — ready for append-only entries |

The decisions template carries the entry-shape HARD TEXT and the Reminder Line — do NOT strip them when filling. Use Write tool to create the file.

### 4. Write Spec Files (code work)

If the plan was flagged code-bearing (step-02) and features were identified (step-03 §6b), author ONE spec per feature BEFORE generating task files — backing tasks reference the spec, so it must exist first.

**Location:** `{output-path}/{plan-name}/specs/{feature}-spec.md` (or the path the plan's own structure sets).

For each feature, read `{rbtv_path}/orchestration/workflows/_shared/authoring/spec-template.md` and fill it — the template owns the section structure; do not restate it here. The Test Plan section IS the test plan — no separate file (D2b unified). Per § Spec Authoring in `../data/plan-creation-rules.md`: reference the template, never copy a spec body into a task file.

A docs-only / vault-content / research plan authors no spec — skip this step.

Use Write tool for EACH spec file individually.

### 5. Generate Micro-Step Task Files

For each task, decide whether it needs a micro-step file by applying the Decision Criteria in `../data/plan-creation-rules.md` § Micro-step File Generation (generate when ANY generate-criterion applies; skip when ALL skip-criteria apply) — the criteria live there, do not restate them here.

**For tasks that need a micro-step file:**

**Location pattern:** `{output-path}/{plan-name}/phase-{N}/{task-id}.task.md`

Generate using `{microstepTemplateFile}` with:

```yaml
---
task_id: {task-id}
status: pending
complexity_score: {from step-03 assessment}
human_review: {required | optional | none}
---
```

**Orchestration pre-resolution frontmatter (conditional).** Orchestrated plans only: READ `../data/orchestration-planning.md` § Task-Frontmatter Pre-Resolution (step-04 body) and apply it — it states which pre-resolution fields (`executor`, `reviewer`, allowlist) land in the task frontmatter. A plain (non-orchestrated) plan omits these and binds the task to a worker at routing time.

**Worker-contract frontmatter for a pinned executor (conditional).** Orchestrated plans with a model-pinned executor only: READ `../data/orchestration-planning.md` § Worker-Contract Frontmatter for a Pinned Executor (step-04 body) and execute it — it carries the dispatch-scaffold skeleton-mode procedure, the pre-flight STOP on an uninstalled model package, and the "NEVER silently emit generic frontmatter for a worker whose contract you could not derive" rule. A plain plan, or one with no model-pinned executor, skips it.

**Setting `human_review`:** This field controls whether the executor MUST emit a Human Review Presentation block at Phase: Close (per `plan-task-microstep-template.md`). Set it deliberately — every `required` task generates a flag block the human must read.

| Value | Set when |
|-------|----------|
| `required` | Task involves any of: scope-shaping decisions, irreversible operations, new external dependencies, architectural-constraint-adjacent work, or judgment calls the user reserved. Also: every checkpoint task is implicitly `required`. |
| `optional` | Task is moderately consequential but routine — user may skim the result without per-task review |
| `none` | Mechanical task with no judgment surface — file moves following an explicit mapping, format conversions, etc. Setting `none` here means "no flag block needed" — do NOT use this to suppress flag noise on tasks that genuinely warrant review. |

The flag block is mandatory ONLY when `human_review: required`. Setting it everywhere creates noise that conditions the user to skim — set it where it earns its keep.

**Content includes:**
- Goal section — what this task achieves
- Context Files — task-specific documents to load. **Path format:** files outside the plan folder use project-root-relative paths; files inside the plan folder use file-relative paths (e.g., `../decisions.md`). See Plan Linking Standard in `plan-creation-rules.md`. For a code task, the Context Files reference its backing **spec** (`specs/{feature}-spec.md`) — the task points at the spec, never restates its behavior.
- Tools section — ONLY if task requires specialized RBTV skills/sub-agents (omit for basic Read/Write/Bash tasks)
- Execution Flow — phased steps (understand → execute → validate → close)
- Discovery Handling — revolving plan rules
- **Decisions-discipline reminder line** — every generated task file carries the Reminder Line verbatim; the microstep template already embeds it (wording: `../data/plan-creation-rules.md` § Decisions-File Discipline). Verify it survives generation.
- Output Requirements — what to produce and where

**For checkpoint task files:**

Generate a task file that contains:
- **Goal** — evaluate phase deliverables against review criteria
- **Work to Evaluate** — summary of what the phase produced (files, artifacts, with paths)
- **Review Criteria** — 3-7 specific criteria from the phase's tasks, architectural constraints, and acceptance criteria
- **Execution Flow** — evaluate each criterion, present findings summary, HALT for human approval, do not advance if rejected

**Use Write tool for EACH task file individually.**

### 6. Write deliverables.md

**Location:** `{output-path}/{plan-name}/deliverables.md`

Generate deliverables.md using `{deliverablesTemplateFile}`, pre-populated from the final task structure:

| Element | Content |
|---------|---------|
| Header block | Plan name + the mandatory read-before / update-after instruction (from template) |
| Phase tables | One section per phase; one row per task in the plan's task list — including checkpoints and final-phase tasks |
| Artifact column | What the task produces — from its Output Requirements (micro-step tasks) or task description (inline tasks) |
| Path column | Intended landing path — `./` file-relative inside the plan folder, project-root-relative outside (Plan Linking Standard) |
| Status column | `pending` on every row |
| Synthesis section | Name the plan's synthesis/integration tasks (if any) and the document-order read sequence |
| Sub-folder note | Conventional sub-folders derived from the Path column — created on demand by the first task that needs them |

Use Write tool to create the file.

### 7. Write Plan File

**Location:** `{output-path}/{plan-name}/{plan-name}-plan.md`

Generate the plan document per `{templateFile}`:

1. **YAML Frontmatter** — `name` and `overview` only
2. **Title** — `# {Plan Name}`
3. **Reference directive** — decisions.md, deliverables.md, and task file pointers
4. **Architectural Constraints** — plan-specific patterns and execution rules
5. **Revolving Plan Rules** — discovery handling (keep brief)
6. **Execution Workflow** — Mermaid diagram from step-03, ONLY if plan is non-linear
7. **Tasks** — Markdown checkbox list grouped by phase with `→ path` suffix for tasks with micro-step files

Use Write tool to create the file.

### 8. Validate Artifacts

**8a. Core artifacts exist:**

| Artifact | Path | Required |
|----------|------|----------|
| Plan file | `{output-path}/{plan-name}/{plan-name}-plan.md` | ✅ |
| Decisions file | `{output-path}/{plan-name}/decisions.md` | ✅ |
| Deliverables file | `{output-path}/{plan-name}/deliverables.md` | ✅ |
| Spec files | `{output-path}/{plan-name}/specs/{feature}-spec.md` | conditional — one per feature when the plan is code-bearing; none for docs/research plans |
| Phase folders | `{output-path}/{plan-name}/phase-{N}/` | ✅ (one per phase) |

**8b. Task file references and deliverables rows resolve:**

For every task in the plan's task list that has a `→ path` suffix, verify the referenced file exists on disk.

For every `.task.md` file on disk in phase folders, verify a matching `→ path` reference exists in the plan's task list.

For every task in the plan's task list (including checkpoints and final-phase tasks), verify a matching row exists in deliverables.md — 1:1, every row Status `pending`.

**8c. Plan Linking Standard:**

Search all files inside the plan folder for path violations:
- No file contains an absolute or root-relative path referencing the plan folder itself
- All intra-plan references use `./` or `../` relative paths

**If ANY validation fails**, fix the issue before proceeding.

### 9. Present Completion Summary

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
1. Read ./deliverables.md — it tells you where your task's output must land
2. Check if the task has a file reference (`→ path`)
3. If yes: read that file and follow its execution phases
4. If no: execute directly from the task description
5. Append to decisions.md only when a decision, finding, constraint, or unresolved question changes future execution
6. After delivering: update your task's row in ./deliverables.md (Status + Path), then mark the task complete in the plan task list (`[x]`)
```

### 10. Present Final Menu

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
- ✅ decisions.md written with planning context (merged if pre-existing, created if not), entry-shape hard text + reminder line intact
- ✅ Spec files authored for each code feature (code-work plans), from the shared spec template
- ✅ deliverables.md written — one `pending` row per task, synthesis section filled
- ✅ Micro-step task files generated for complex tasks and checkpoints, each carrying the decisions-discipline reminder line
- ✅ Plan file written with Markdown task list
- ✅ Task file references link correctly (`→ path` ↔ file on disk)
- ✅ deliverables.md rows match the task list 1:1
- ✅ Plan Linking Standard validated (no brittle self-references)
- ✅ Completion summary displayed
- ✅ Menu presented with explicit HALT
