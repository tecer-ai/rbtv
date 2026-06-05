---
name: 'step-01-init'
description: 'Load context, verify prerequisites, explain Brand Archetypes framework'
nextStepFile: './step-02-exploration.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/brand-archetypes.md'
---

# Step 1: Initialize Brand Archetypes

**Progress: Step 1 of 5** — Next: Archetype Exploration

---

## STEP GOAL

Verify M1/M2 prerequisites, load context from project-memo and prior frameworks, explain Brand Archetypes methodology.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Challenge aspirational thinking, demand evidence-based choices. Brand archetypes must be grounded in customer reality, not founder preference.

### Step-Specific Rules
- M1 AND M2 must be complete before starting Brand Archetypes
- If prerequisites are missing, HALT and explain what's needed
- If brand-archetypes.md exists with stepsCompleted, offer to continue
- Do NOT evaluate archetypes in this step — that's Step 2

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and stepsCompleted
2. Read `./data/brand-archetypes-framework.md` for framework knowledge
3. Check M1/M2 prerequisites by verifying these exist in stepsCompleted:
   - `bi-m1-working-backwards`
   - `bi-m1-jobs-to-be-done`
   - `bi-m1-lean-canvas`
   - At least 3 M2 frameworks
4. Check if `{outputFolder}/brand-archetypes.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Verification

Check project-memo stepsCompleted for:

**Required M1 Frameworks:**
- Working Backwards (customer definition, emotional language)
- Jobs-to-be-Done (emotional jobs, social jobs)
- Lean Canvas (UVP, Customer Segments, Unfair Advantage)

**Required M2 Frameworks:**
- At least 3 M2 validation frameworks completed

If missing:
> "⛔ **Prerequisites Incomplete**
>
> Brand Archetypes requires:
> - [Missing framework list]
>
> Complete these before starting M3 Brand work. Brand choices without customer evidence are just guessing.
>
> Return to: [M1/M2 milestone]"

HALT — do not proceed.

### 2. Context Detection

If prerequisites met:
- Check for existing `brand-archetypes.md` with `stepsCompleted`
- If exists:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Brand Archetypes briefly:

> "Carl Jung identified 12 universal archetypes that recur across cultures because they map to fundamental human motivations. We'll select an archetype for your brand grounded in:
>
> 1. **Emotional Fit** — Does it match how customers want to feel?
> 2. **Purpose Fit** — Does it naturally deliver your UVP?
> 3. **Differentiation** — Does it distinguish you from competitors?
>
> The output is not just a label — it's concrete guidance for voice, visuals, relationships, and content themes."

### 4. Project Context Summary

From project-memo and M1 frameworks, summarize:
- Project name
- Primary customer (from Working Backwards)
- Key emotional jobs (from JTBD)
- Key social jobs (from JTBD)
- UVP and Unfair Advantage (from Lean Canvas)

Present: "Here's the customer evidence that will ground your archetype selection..."

### 5. Create Output Document

If not continuing, create brand-archetypes.md:

```yaml
---
name: brand-archetypes
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Brand Archetypes: {Project Name}

## Emotional Territory Brief

*(To be completed in Step 2)*

## Archetype Evaluation Matrix

*(To be completed in Step 2)*

## Primary Archetype Selection

*(To be completed in Step 3)*

## Secondary Archetype (Optional)

*(To be completed in Step 3)*

## Archetype Expression Guide

*(To be completed in Step 4)*

## Synthesis

*(To be completed in Step 5)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Archetype Exploration

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure brand-archetypes.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-exploration.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Prerequisites verified, customer evidence summarized, output document created

❌ **FAILURE:** Proceeding without M1/M2 prerequisites, evaluating archetypes in this step, skipping evidence summary
