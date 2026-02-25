---
name: 'step-03-invoke-bmad'
description: 'Instruct run BMAD create-ux-design with prepared context'
nextStepFile: './step-03b-restore-config.md'
---

# Step 3: Invoke BMAD create-ux-design

**Progress: Step 3 of 4** — Next: Synthesis

---

## STEP GOAL

Instruct the user to run BMAD create-ux-design with the prepared design-context document. Provide the exact workflow path and loading instructions.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Clear instructions prevent re-discovery and wasted tokens.

### Step-Specific Rules
- Do NOT run BMAD workflow in place of the user — instruct the user to load and run it
- Provide explicit path to BMAD create-ux-design workflow
- No Lavoisier reference; use current discovery mechanism wording (visual-design-extraction, playwright-browser-automation, optionally design-validation)

---

## BMAD WORKFLOW PATH

- **Path:** `{bmad_bmm}/workflows/2-plan-workflows/create-ux-design/workflow.md`
- **Context document:** `{outputFolder}/design-context.md`

---

## MANDATORY SEQUENCE

### 1. Invocation Instructions

Present clear instructions:

> "**Invoke BMAD create-ux-design**
>
> 1. **Load the BMAD workflow:**  
>    `{bmad_bmm}/workflows/2-plan-workflows/create-ux-design/workflow.md`
>
> 2. **Provide as input context:**  
>    The design-context document at `{outputFolder}/design-context.md`.  
>    BMAD create-ux-design discovers input from planning_artifacts, output_folder, and product_knowledge. Ensure the design-context document is in scope (e.g. same output folder or planning artifacts path).
>
> 3. **What BMAD will do:**  
>    Create UX design specifications: design brief, visual foundation, design directions, user journeys, component strategy, UX patterns, responsive and accessibility specs. Discovery uses visual-design-extraction, playwright-browser-automation; optionally design-validation.
>
> 4. **After BMAD completes:**  
>    Return to this bridge workflow and select **[C] Continue** to run Step 4 (Synthesis). Step 4 will integrate BMAD output (e.g. design specification, design_brief.md, design.json if produced) into project-memo and instruct return to M4 milestone menu."

### 2. Confirm Before Proceeding

> "Have you run BMAD create-ux-design and received the design output? If yes, select [C] Continue to run Synthesis (Step 4). If not, run the BMAD workflow first, then return here."

HALT — wait for user confirmation.

### 3. Present Menu Options

**Select an Option:**
- **[C] Continue** — BMAD complete; proceed to Restore Config (Step 3b)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected (user has completed BMAD create-ux-design):
1. Load `./step-03b-restore-config.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** User has clear path and instructions; user runs BMAD and returns to bridge for Step 4

❌ **FAILURE:** Vague path, or BMAD run in place of user without instruction
