---
name: 'step-02-format-context'
description: 'Build design brief / context document for BMAD create-ux-design'
nextStepFile: './step-02b-update-config.md'
outputFile: '{outputFolder}/design-context.md'
---

# Step 2: Format Design Context

**Progress: Step 2 of 4** — Next: Invoke BMAD

---

## STEP GOAL

Build a design-context document (design brief) for BMAD create-ux-design from user-flow-ia.md and project-memo. Include artifact type, content hierarchy, CTA strategy, and brand references from M3.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The design-context document must give BMAD create-ux-design everything it needs to scope UX work without re-discovery.

### Step-Specific Rules
- Use content from user-flow-ia.md (artifact type, conversion goal, IA, synthesis) and project-memo (M1/M3 summary, brand)
- Write to `{outputFolder}/design-context.md`
- Do NOT invoke BMAD in this step — that is Step 3

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/user-flow-ia.md` (full document including Synthesis)
2. Read `{outputFolder}/project-memo.md` (Progress > Conception, Validation, Brand; stepsCompleted)

---

## MANDATORY SEQUENCE

### 1. Build Design Context Document

Create or overwrite `{outputFolder}/design-context.md` with the following structure. Populate from user-flow-ia and project-memo.

```markdown
# Design Context: {Project Name}

> Prepared by bi-m4-design-context bridge for BMAD create-ux-design workflow.

## Artifact Type & Conversion Goal

- **Artifact type:** [from user-flow-ia: landing page, website, infographic, one-pager]
- **Conversion goal:** [from user-flow-ia]
- **Target user:** [from project-memo / Working Backwards]

## Content Hierarchy (from User Flow & IA)

- **Sections / AIDA structure:** [Attention, Interest, Credibility, Action sections]
- **Primary content per section:** [from IA]
- **Secondary / supporting content:** [from IA]
- **Content density:** [low/medium/high] for [artifact type]

## CTA & Layout Priorities

- **CTA placement:** [from user-flow-ia synthesis]
- **Layout priorities:** [CTA visibility, breakpoints]
- **Visual hierarchy:** [what must be emphasized]

## Brand References (from M3)

- **Brand tone / voice:** [from project-memo M3 synthesis]
- **Messaging or archetype:** [if present in project-memo]
- **Design direction guidance:** [from user-flow-ia Synthesis > Design Direction Guidance]

## Prerequisites Completed

- M1: [relevant frameworks from stepsCompleted]
- M3: [relevant frameworks from stepsCompleted]
- M4 User Flow & IA: complete

## BMAD create-ux-design Input Summary

When running BMAD create-ux-design:
- Use this document as the primary context (design brief).
- Discovery: visual-design-extraction, playwright-browser-automation; optionally design-validation.
- Output: design specification and visual direction; integrate results into project-memo after workflow completion.
```

Confirm with user: "Design-context document created at `{outputFolder}/design-context.md`. Review if needed, then continue to invoke BMAD create-ux-design."

### 2. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Update BMAD Config (Step 2b)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure design-context.md exists at {outputFolder}
2. Load `./step-02b-update-config.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** design-context.md created with artifact type, content hierarchy, CTA, brand refs; user can proceed to BMAD

❌ **FAILURE:** Document missing required sections, or BMAD invoked in this step
