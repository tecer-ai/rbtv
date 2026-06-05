---
name: 'step-01-init'
description: 'Load context, verify prerequisites, explain Brand Positioning framework'
nextStepFile: './step-02-inputs.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/brand-positioning.md'
---

# Step 1: Initialize Brand Positioning

**Progress: Step 1 of 6** — Next: Consolidate Positioning Inputs

---

## STEP GOAL

Verify Golden Circle and prior M3 framework prerequisites, load context from project-memo and prior frameworks, explain Brand Positioning methodology.

---

## Prior Context

**Builds on:** Brand Archetypes, Brand Prism, Golden Circle
**Inherits (do not restate):** Emotional territory — reference `{outputFolder}/brand-archetypes.md`; brand identity facets — reference `{outputFolder}/brand-prism.md`; purpose (Why) — reference `{outputFolder}/golden-circle.md`
**This framework adds:** Positioning statement, perceptual map, competitive brand differentiation

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Demand precision in positioning. Reject vague claims. Every element must be traceable to upstream strategy work.

### Step-Specific Rules
- Golden Circle MUST be complete before starting Brand Positioning
- If prerequisites are missing, HALT and explain what's needed
- If brand-positioning.md exists with stepsCompleted, offer to continue
- Do NOT draft positioning in this step — that's Step 3

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and stepsCompleted
2. Read `./data/brand-positioning-framework.md` for framework knowledge
3. Check prerequisites by verifying these exist in stepsCompleted:
   - `bi-m1-working-backwards`
   - `bi-m1-lean-canvas`
   - `bi-m2-tam-sam-som` (for competitive landscape)
   - `bi-m3-golden-circle` (REQUIRED — provides Why/How/What)
4. Preferred but not required:
   - `bi-m3-brand-prism` (personality and relationship)
   - `bi-m3-brand-archetypes` (character)
5. Check if `{outputFolder}/brand-positioning.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Verification

Check project-memo stepsCompleted for:

**Required Frameworks:**
- Golden Circle (Why, How, What — core positioning inputs)
- Working Backwards (customer definition, differentiation claims)
- Lean Canvas (UVP, Segments, Unfair Advantage)
- TAM/SAM/SOM (competitive landscape)

If missing Golden Circle:
> "⛔ **Prerequisites Incomplete**
>
> Brand Positioning requires Golden Circle to be complete — the Why becomes your benefit, the How becomes your differentiation, the What frames your category.
>
> Missing: [List missing frameworks]
>
> Return to: Golden Circle framework or missing M1/M2 work"

HALT — do not proceed.

### 2. Context Detection

If prerequisites met:
- Check for existing `brand-positioning.md` with `stepsCompleted`
- If exists:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Brand Positioning briefly:

> "Brand positioning defines the specific place you occupy in the customer's mind relative to alternatives. We'll build:
>
> 1. **Positioning Statement** — Single sentence following a precise template where every word is a strategic choice
> 2. **Perceptual Map** — Visual proof that your position is distinct and desirable
> 3. **Validation Tests** — 4 tests (Uniqueness, Credibility, Relevance, Consistency)
>
> The output is NOT a tagline — it's an internal strategic document that guides all messaging, pricing, and feature decisions."

### 4. Project Context Summary

From project-memo and upstream frameworks, summarize:
- Project name
- Golden Circle (Why, How, What)
- Target customer segments
- Key competitors identified
- UVP and Unfair Advantage

Present: "Here's your strategic foundation for positioning..."

### 5. Create Output Document

If not continuing, create brand-positioning.md:

```yaml
---
name: brand-positioning
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Brand Positioning: {Project Name}

## Positioning Inputs Brief

*(To be completed in Step 2)*

## Draft Positioning Statements

*(To be completed in Step 3)*

## Perceptual Map

*(To be completed in Step 4)*

## Validation Tests

*(To be completed in Step 5)*

## Final Positioning Statement

*(To be completed in Step 6)*

## Integration Notes

*(To be completed in Step 6)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Consolidate Positioning Inputs

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure brand-positioning.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-inputs.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Prerequisites verified, strategic foundation summarized, output document created

❌ **FAILURE:** Proceeding without Golden Circle, drafting positioning in this step, skipping prerequisite check
