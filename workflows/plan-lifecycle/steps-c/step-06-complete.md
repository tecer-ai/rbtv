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

### 1b. Validate Task File References (Bidirectional)

Task file paths are embedded in the `content` field using `[brackets]` suffix (e.g., `"p1-1: Description [phase-1/p1-1.task.md]"`). Parse the path from the last `[...]` in each todo's `content`.

**YAML → Disk:** For every YAML todo whose `content` contains a `[path]` suffix, verify the referenced file exists on disk at the expected path (relative to the plan folder).

**Disk → YAML:** For every `.task.md` file found on disk in phase folders, verify a matching `[path]` reference exists in a YAML todo's `content`.

| Check | Passes When | Failure Indicates |
|-------|-------------|-------------------|
| YAML → Disk | Every `[path]` value resolves to an existing file | Broken reference — file was not generated or was deleted |
| Disk → YAML | Every `.task.md` on disk has a corresponding `[path]` in a todo's content | Orphaned file — micro-step file exists but no todo references it |

**If ANY validation fails:**
```
⚠️ INCOMPLETE: task file reference validation failed

Broken references (YAML → Disk):
- {task-id}: [path] "{path}" not found on disk

Orphaned files (Disk → YAML):
- {file-path}: no matching [path] reference in any todo content

Returning to step-05 to fix missing artifacts.
```

Load `./step-05-generate-artifacts.md` and re-execute.

### 1c. Validate Plan Linking Standard

Search all files inside the plan folder for violations of the Plan Linking Standard (see `plan-creation-rules.md`).

**Check 1 — No brittle self-references:** Search all `.md` files in the plan folder for patterns that embed the plan folder's own path as a root-relative or absolute reference. Use grep pattern: the plan folder name followed by `/` in a path context (e.g., `.cursor/plans/{plan-name}/` or `{project-root}/.../{plan-name}/`).

**Check 2 — Internal links are relative:** Verify that references to sibling files (`shape.md`, `learnings.md`, task files) use `../` or `./` patterns, not root-relative paths.

| Check | Passes When | Failure Indicates |
|-------|-------------|-------------------|
| No brittle self-refs | Zero matches for plan-folder-name-based absolute paths inside plan files | Files contain move-fragile self-references |
| Internal links relative | All intra-plan references use `./` or `../` | Links will break on folder relocation |

**If ANY linking violation is found:**
```
⚠️ Plan Linking Standard violation detected

Brittle self-references found in:
- {file-path}: line {N} — {matched text}

Fix these references to use file-relative paths (e.g., ../shape.md instead of .cursor/plans/{plan-name}/shape.md).
```

Fix violations before proceeding — do NOT skip this check.

**If core artifacts are missing:**
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

1. Check the task's `content` for a `[path]` suffix (e.g., `[phase-1/p1-1.task.md]`)
2. If `[path]` is present: read that file and follow its execution phases
3. If no `[path]`: execute directly from the task's `content` description
4. Update `shape.md` with execution log entry when complete
5. Capture any meta-learnings in `learnings.md`
6. Mark task complete in plan YAML frontmatter
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

- ✅ All core artifacts validated (plan, shape, learnings, phase folders)
- ✅ Bidirectional task file reference validation passed (YAML `[path]` → Disk and Disk → YAML `[path]`)
- ✅ Plan Linking Standard validation passed (no brittle self-references, internal links relative)
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
