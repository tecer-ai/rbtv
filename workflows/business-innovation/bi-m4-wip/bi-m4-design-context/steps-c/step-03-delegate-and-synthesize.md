---
name: 'step-03-delegate-and-synthesize'
description: 'Invoke bmad-method-lifecycle:bmad-create-ux-design plugin skill, instruct user, wait for completion, verify file placement, synthesis'
nextStepFile: null
---

# Step 3: Delegate to Plugin & Synthesize

**Progress: Step 3 of 3** — Final Step

---

## STEP GOAL

Invoke `bmad-method-lifecycle:bmad-create-ux-design`, instruct user to run the plugin workflow with the prepared design-context, wait for completion, verify file placement, integrate output into project-memo, and instruct return to M4 menu.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Clear delegation instructions prevent wasted tokens and re-discovery.

### Step-Specific Rules
- Do NOT run the plugin workflow in place of the user — instruct the user to invoke and run it
- project-memo.md MUST be updated with Design Direction synthesis
- Return instruction MUST be explicit

---

## MANDATORY SEQUENCE

### 1. Instruct User to Invoke the Plugin

> "**Invoke `bmad-method-lifecycle:bmad-create-ux-design`**
>
> Open a NEW conversation (or agent session) and invoke the `bmad-method-lifecycle:bmad-create-ux-design` skill.
>
> **Input context:** The design-context document at `{outputFolder}/design-context.md`. Provide this document as the primary context (design brief) when prompted.
>
> **What the plugin will do:**
> Create UX design specifications: design brief, visual foundation, design directions, user journeys, component strategy, UX patterns, responsive and accessibility specs. Discovery uses visual-design-extraction, playwright-browser-automation; optionally design-validation.
>
> **After the plugin completes:**
> Return to THIS conversation and select **[C] Continue**."

### 2. Wait for Completion

> "[C] Continue — plugin workflow complete"

HALT — wait for user confirmation.

### 3. Mentor-Assisted File Placement

When user returns:
- Ask what files the plugin produced and where they are
- Verify expected output files are at `{outputFolder}/` (e.g., ux-design-specification.md, design_brief.md, design.json)
- If files are not in `{outputFolder}/`, help user move/copy them there
- Confirm all expected files are in place

### 4. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{rbtv_path}/workflows/business-innovation/data/founder-process.md` for M4.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 5. Synthesis — Update Project Memo

Read plugin output from `{outputFolder}/`.

Update `{outputFolder}/project-memo.md`:

**Add to stepsCompleted array:**
```yaml
stepsCompleted:
  - ... (existing)
  - bi-m4-design-context
```

**Add to Progress > Prototypation section:**

```markdown
### Design Direction (`bmad-method-lifecycle:bmad-create-ux-design`)
**Status:** Complete
**Bridge:** bi-m4-design-context
**Plugin output:** [path to ux-design-specification.md or design_brief.md / design.json]

**Summary:**
- Design specification / design brief created via `bmad-method-lifecycle:bmad-create-ux-design`
- Context was prepared by bi-m4-design-context bridge (user-flow-ia + M1/M3)
- [Brief summary of design direction: visual foundation, design system, UX patterns, etc.]

**Key Artifacts:**
- [List key files: ux-design-specification.md, design_brief.md, design.json if applicable]
```

### 6. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 7. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M4.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M4 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 8. Present Completion Summary

> "**Design Context Bridge Complete** ✅
>
> **What was done:**
> - Design context prepared from User Flow & IA and M1/M3
> - `bmad-method-lifecycle:bmad-create-ux-design` run with that context
> - project-memo updated with Design Direction synthesis
>
> **Next Step:**
> **Return to M4 milestone menu** and select:
> - **[B] Back** — return to M4 Prototypation milestone menu
> - **Next framework:** [B] Build Prototype, [C] Conversion Optimization, [H] Heuristic Evaluation, [F] Testing Prep
>
> Do not load another step. The bridge is complete."

### 9. Present Menu Options

**Select an Option:**
- **[B] Back** — return to M4 Prototypation milestone menu (user action; no further step to load)
- **[R] Review** — review project-memo Design Direction section

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

Bridge is COMPLETE. There is no next step file. User must return to M4 milestone workflow and select [B] or next framework. Referral logic: milestone = entry points; bridge last step = update project_memo + instruct return to milestone menu.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Plugin invoked with design-context, files verified after plugin run, project-memo updated with Design Direction synthesis, explicit return instruction given

❌ **FAILURE:** Plugin not invoked, files not verified, project-memo not updated, return instruction missing
