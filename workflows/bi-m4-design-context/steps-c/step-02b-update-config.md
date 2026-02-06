---
name: 'step-02b-update-config'
description: 'Update BMAD config to use RBTV project folder before invoking BMAD'
nextStepFile: './step-03-invoke-bmad.md'
---

# Step 2b: Update BMAD Config

**Progress: Step 2b of 5** — Next: Invoke BMAD

---

## STEP GOAL

Update BMAD module config to redirect outputs to RBTV project folder before invoking BMAD create-ux-design. This ensures BMAD outputs land in the correct project-specific location.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Config management is critical infrastructure — handle it systematically.

### Step-Specific Rules
- ALWAYS run update-bmad-config task before proceeding
- NEVER skip this step — BMAD will write to wrong location without config update
- Verify task completion before moving to Step 3

---

## MANDATORY SEQUENCE

### 1. Explain Config Update

Present clear explanation:

> "**BMAD Config Update Required**
>
> Before invoking BMAD create-ux-design, we need to update BMAD's config to use this project's output folder.
>
> **Why:** BMAD workflows read output_folder from their config file. By default, BMAD uses `_bmad-output/` (root). We need BMAD to write to `_bmad-output/{project-name}/founder/m4-prototypation/` so outputs stay organized with your project.
>
> **What happens:** The update-bmad-config task will:
> 1. Back up current BMAD config values
> 2. Update BMAD config to point to your project folder
> 3. Confirm the update
>
> After BMAD completes, we'll restore the config to defaults (Step 3b).
>
> Running config update now..."

### 2. Run Update Config Task

Execute the update-bmad-config task:

**Task Path:** `{project-root}/_bmad/rbtv/tasks/update-bmad-config.xml`

**Inputs:**
- `target_module`: "bmm"
- `project_name`: `{project-name}`
- `rbtv_output_folder`: `{outputFolder}` (should be `{project-root}/_bmad-output/{project-name}/founder/m4-prototypation`)

**Expected Output:**
```
✅ BMAD bmm config updated for RBTV project '{project-name}'
   Output folder: {outputFolder}
   BMAD workflows will now write to this RBTV project folder.
   (Original values backed up for restore)
```

### 3. Confirm Success

After task completes successfully:

> "✅ **BMAD config updated successfully**
>
> BMAD create-ux-design will now write outputs to:
> `{outputFolder}`
>
> Ready to proceed to BMAD invocation."

### 4. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Invoke BMAD (Step 3)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify update-bmad-config task completed successfully
2. Load `./step-03-invoke-bmad.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Config updated; BMAD bmm module now points to RBTV project folder

❌ **FAILURE:** Task failed or skipped; BMAD will write to wrong location
