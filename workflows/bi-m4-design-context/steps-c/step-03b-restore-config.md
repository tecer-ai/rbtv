---
name: 'step-03b-restore-config'
description: 'Restore BMAD config to defaults after BMAD workflow completion'
nextStepFile: './step-04-synthesis.md'
---

# Step 3b: Restore BMAD Config

**Progress: Step 3b of 5** — Next: Synthesis

---

## STEP GOAL

Restore BMAD module config to default values after BMAD create-ux-design completion. This ensures subsequent BMAD usage (outside RBTV context) uses standard output folders.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Config restoration maintains system hygiene — handle it systematically.

### Step-Specific Rules
- ALWAYS run restore-bmad-config task after BMAD completes
- NEVER skip this step — other BMAD usage will be affected
- Verify task completion before moving to Step 4

---

## MANDATORY SEQUENCE

### 1. Confirm BMAD Completion

Verify with user:

> "Have you completed the BMAD create-ux-design workflow and received the design outputs?
>
> If yes, we'll now restore BMAD config to defaults so other BMAD workflows use standard paths.
>
> **[C] Continue** — BMAD complete; restore config and proceed to Synthesis"

HALT — wait for user confirmation.

### 2. Explain Config Restore

Present clear explanation:

> "**BMAD Config Restore**
>
> Restoring BMAD config to default values:
> - `output_folder`: `{project-root}/_bmad-output`
> - `planning_artifacts`: `{project-root}/_bmad-output/{project-name}/planning-artifacts`
> - `implementation_artifacts`: `{project-root}/_bmad-output/{project-name}/implementation-artifacts`
>
> This ensures future BMAD usage (outside this RBTV project) works correctly.
>
> Running config restore now..."

### 3. Run Restore Config Task

Execute the restore-bmad-config task:

**Task Path:** `{project-root}/_bmad/rbtv/tasks/restore-bmad-config.xml`

**Inputs:**
- `target_module`: "bmm"

**Expected Output:**
```
✅ BMAD bmm config restored to defaults
   Output folder: {project-root}/_bmad-output
   Planning artifacts: {project-root}/_bmad-output/{project-name}/planning-artifacts
   Implementation artifacts: {project-root}/_bmad-output/{project-name}/implementation-artifacts
   BMAD workflows will now use standard root output folder.
```

### 4. Confirm Success

After task completes successfully:

> "✅ **BMAD config restored to defaults**
>
> Your BMAD design outputs are saved in:
> `{outputFolder}`
>
> Ready to integrate BMAD outputs into project-memo."

### 5. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis (Step 4)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify restore-bmad-config task completed successfully
2. Load `./step-04-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Config restored; BMAD bmm module back to standard defaults

❌ **FAILURE:** Task failed or skipped; other BMAD usage may be affected
