---
name: 'step-04-synthesis'
description: 'Integrate BMAD design output into project-memo; instruct return to M4 milestone menu'
nextStepFile: null
---

# Step 4: Synthesis

**Progress: Step 4 of 4** — Final Step

---

## STEP GOAL

Receive BMAD create-ux-design output (e.g. ux-design-specification.md, design_brief.md, design.json or equivalent), update project-memo with Design Direction synthesis, and instruct the user to return to M4 milestone menu and select [B] Back or next framework [B], [C], [H], [F].

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Referral logic is inviolable: framework/bridge last step = update project-memo + instruct return to milestone menu.

### Step-Specific Rules
- project-memo.md MUST be updated with Design Direction synthesis
- Return instruction MUST be explicit: "Return to M4 milestone menu and select [B] Back or next framework [B], [C], [H], [F]"

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for update
2. Discover BMAD output: look for ux-design-specification.md, design_brief.md, design.json, or equivalent in `{outputFolder}` or planning_artifacts paths. If user describes where BMAD wrote output, use that path.

---

## MANDATORY SEQUENCE

### 1. Confirm BMAD Output

Identify BMAD create-ux-design output:

- Common locations: `{outputFolder}/ux-design-specification.md`, `{outputFolder}/design_brief.md`, `{outputFolder}/design.json`, or paths from BMAD config (planning_artifacts).
- If output not found in standard paths, ask user: "Where did BMAD create-ux-design save its output? (e.g. path to ux-design-specification.md or design_brief.md)"
- Summarize what was produced (design specification, design brief, design tokens, etc.)

### 2. Update Project Memo

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

**Next:** Return to M4 milestone menu and select [B] Back or next framework: [B] Build Prototype, [C] Conversion Optimization, [H] Heuristic Evaluation, [F] Testing Prep
```

### 3. Present Completion Summary

> "**Design Context Bridge Complete** ✅
>
> **What was done:**
> - Design context prepared from User Flow & IA and M1/M3
> - BMAD create-ux-design run with that context
> - project-memo updated with Design Direction synthesis
>
> **Next Step:**
> **Return to M4 milestone menu** and select:
> - **[B] Back** — return to milestone selection (bi-business-innovation)
> - **Next framework:** [B] Build Prototype, [C] Conversion Optimization, [H] Heuristic Evaluation, [F] Testing Prep
>
> Do not load another step. The bridge is complete."

### 4. Present Menu Options

**Select an Option:**
- **[B] Back** — return to M4 Prototypation milestone menu (user action; no further step to load)
- **[R] Review** — review project-memo Design Direction section

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

Bridge is COMPLETE. There is no next step file. User must return to M4 milestone workflow and select [B] or next framework. Referral logic: milestone = entry points; bridge last step = update project_memo + instruct return to milestone menu.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** project-memo updated with Design Direction synthesis, explicit return instruction given, no next step loaded

❌ **FAILURE:** project-memo not updated, return instruction missing or unclear, or loading another step after synthesis
