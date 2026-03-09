---
name: 'step-03-delegate-and-synthesize'
description: 'Standard lightweight BMAD delegation: update config, instruct user, wait, file placement, restore config, synthesis'
nextStepFile: null
---

# Step 3: Delegate to BMAD & Synthesize

**Progress: Step 3 of 3** — Final Step

---

## STEP GOAL

Execute the standard BMAD lightweight delegation sequence: update config, instruct user to run BMAD create-ux-design, wait for completion, verify file placement, restore config, integrate output into project-memo, and instruct return to M4 menu.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Clear delegation instructions prevent wasted tokens and re-discovery. Config management is critical infrastructure.

### Step-Specific Rules
- Do NOT run BMAD workflow in place of the user — instruct the user to load and run it
- ALWAYS update config before and restore after BMAD invocation
- project-memo.md MUST be updated with Design Direction synthesis
- Return instruction MUST be explicit

---

## MANDATORY SEQUENCE

### 1. Update BMAD Config

> "**BMAD Config Update Required**
>
> Before invoking BMAD create-ux-design, we need to update BMAD's config to use this project's output folder.
>
> BMAD workflows read output_folder from their config file. By default, BMAD uses `{bmad_output}/` (root). We need BMAD to write to `{outputFolder}/` so outputs stay organized with your project.
>
> Running config update now..."

Run task: `{project-root}/_bmad/rbtv/tasks/update-bmad-config.xml`

**Inputs:**
- `target_module`: "bmm"
- `project_name`: `{project-name}`
- `rbtv_output_folder`: `{outputFolder}`

Verify task completion before proceeding.

### 2. Instruct User to Run BMAD

> "**Invoke BMAD create-ux-design**
>
> Open a NEW conversation (or agent session) and load the following BMAD workflow:
>
> `{bmad_bmm}/workflows/2-plan-workflows/create-ux-design/workflow.md`
>
> **Input context:** The design-context document at `{outputFolder}/design-context.md`.
> BMAD create-ux-design discovers input from planning_artifacts, output_folder, and product_knowledge. The config has been updated to point to your project folder.
>
> **What BMAD will do:**
> Create UX design specifications: design brief, visual foundation, design directions, user journeys, component strategy, UX patterns, responsive and accessibility specs. Discovery uses visual-design-extraction, playwright-browser-automation; optionally design-validation.
>
> **After BMAD completes:**
> Return to THIS conversation and select **[C] Continue**."

### 3. Wait for Completion

> "[C] Continue — BMAD workflow complete"

HALT — wait for user confirmation.

### 4. Mentor-Assisted File Placement

When user returns:
- Ask what files BMAD produced and where they are
- Verify expected output files are at `{outputFolder}/` (e.g., ux-design-specification.md, design_brief.md, design.json)
- If files are not in `{outputFolder}/`, help user move/copy them there
- Confirm all expected files are in place

### 5. Restore BMAD Config

> "Restoring BMAD config to defaults so other BMAD workflows use standard paths..."

Run task: `{project-root}/_bmad/rbtv/tasks/restore-bmad-config.xml`

**Inputs:**
- `target_module`: "bmm"

Verify task completion.

### 6. Synthesis — Update Project Memo

Read BMAD output from `{outputFolder}/`.

Update `{outputFolder}/project-memo.md`:

**Add to stepsCompleted array:**
```yaml
stepsCompleted:
  - ... (existing)
  - bi-m4-design-context
```

**Add to Progress > Prototypation section:**

```markdown
### Design Direction (BMAD create-ux-design)
**Status:** Complete
**Bridge:** bi-m4-design-context
**BMAD output:** [path to ux-design-specification.md or design_brief.md / design.json]

**Summary:**
- Design specification / design brief created via BMAD create-ux-design
- Context was prepared by bi-m4-design-context bridge (user-flow-ia + M1/M3)
- [Brief summary of design direction: visual foundation, design system, UX patterns, etc.]

**Key Artifacts:**
- [List key files: ux-design-specification.md, design_brief.md, design.json if applicable]
```

### 7. Present Completion Summary

> "**Design Context Bridge Complete** ✅
>
> **What was done:**
> - Design context prepared from User Flow & IA and M1/M3
> - BMAD create-ux-design run with that context
> - project-memo updated with Design Direction synthesis
>
> **Next Step:**
> **Return to M4 milestone menu** and select:
> - **[B] Back** — return to M4 Prototypation milestone menu
> - **Next framework:** [B] Build Prototype, [C] Conversion Optimization, [H] Heuristic Evaluation, [F] Testing Prep
>
> Do not load another step. The bridge is complete."

### 8. Present Menu Options

**Select an Option:**
- **[B] Back** — return to M4 Prototypation milestone menu (user action; no further step to load)
- **[R] Review** — review project-memo Design Direction section

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

Bridge is COMPLETE. There is no next step file. User must return to M4 milestone workflow and select [B] or next framework. Referral logic: milestone = entry points; bridge last step = update project_memo + instruct return to milestone menu.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Config updated before BMAD, files verified after BMAD, config restored, project-memo updated with Design Direction synthesis, explicit return instruction given

❌ **FAILURE:** Config not updated/restored, files not verified, project-memo not updated, return instruction missing
