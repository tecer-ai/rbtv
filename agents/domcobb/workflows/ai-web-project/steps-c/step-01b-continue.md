---
stepNumber: 1
stepId: continue
---

# Step 1b: Continue Existing Project

**Goal:** Resume work on an existing AI Web Project.

---

## MANDATORY SEQUENCE

### 1. Find Existing Project

List folders inside `{output_folder}/ai-web-projects/`. Present them to the user.

- If no folders exist: "No existing projects found. Let's start fresh." → Load `./step-01-init.md` and run from step 2.
- If folders exist: Present them as a numbered list and ask which one to continue.

### 2. Load Project Brief

Read `{output_folder}/ai-web-projects/{selected-project}/project-brief.md`.

Extract from frontmatter:
- `stepsCompleted` — what has been done
- `platform` — if already selected
- `status` — current state

### 3. Determine Next Step

Find the last entry in `stepsCompleted`. Map it to its `nextStepFile`:

| Last Completed | Next Step |
|----------------|-----------|
| `step-01-init` | `./step-02-discover.md` |
| `step-02-discover` | `./step-03-generate.md` |
| `step-03-generate` | `./step-04-refine.md` |
| `step-04-refine` | Workflow complete — offer to create another or exit |

### 4. Welcome Back

> "Welcome back to **{projectName}**. You completed: {stepsCompleted}. Next up: {next step description}."

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[C] Continue** | Load the next step |
| **[R] Restart** | Start fresh — load `./step-01-init.md` from step 2 |
| **[X] Exit** | Exit workflow |
