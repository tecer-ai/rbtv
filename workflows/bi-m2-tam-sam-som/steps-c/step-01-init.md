---
name: 'step-01-init'
description: 'Load context, verify prerequisites, explain TAM/SAM/SOM framework'
nextStepFile: './step-02-boundaries.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/tam-sam-som.md'
---

# Step 1: Initialize TAM/SAM/SOM

**Progress: Step 1 of 7** — Next: Define Market Boundaries

---

## STEP GOAL

Load context from project-memo and M1 frameworks, verify prerequisites, explain the TAM/SAM/SOM framework, and prepare for market sizing.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for rigor. Reject single-source estimates. Demand ranges not point estimates. Continue this persona throughout.

### Step-Specific Rules
- If tam-sam-som.md exists with stepsCompleted, offer to continue from last step
- Do NOT calculate any market figures in this step — that's for later steps
- Verify M1 frameworks are available for inputs

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context
2. Read `{outputFolder}/lean-canvas.md` for Customer Segments, Revenue Streams, Channels (if exists)
3. Read `{outputFolder}/working-backwards.md` for customer definition (if exists)
4. Read `{outputFolder}/jobs-to-be-done.md` for segment selection (if exists)
5. Read `{outputFolder}/leap-of-faith.md` for market-related assumptions (if exists)
6. Read `{outputFolder}/bmad-analysis/` contents (if exists) for market data, competitive intelligence, and sizing inputs
7. Read `./data/tam-sam-som-framework.md` for framework knowledge
8. Check if `{outputFolder}/tam-sam-som.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Check

Check for M1 framework inputs:
- Lean Canvas (Customer Segments, Revenue Streams, Channels)
- Working Backwards (customer definition)
- JTBD (segment selection)

**If key M1 frameworks missing:**
> "⚠️ Recommended Prerequisites: For accurate market sizing, we ideally need:
> - Lean Canvas (Customer Segments, Revenue Streams, Channels)
> - Working Backwards (customer definition)
> - JTBD (segment selection)
>
> [List which are missing]
>
> We can proceed, but estimates will be less grounded. Shall we continue or complete M1 first?"

Check for Leap of Faith (M2):
- **If exists:** Note market-related assumptions to validate through sizing
- **If missing:** Note this is acceptable but Leap of Faith should follow

### 2. Context Detection

Check for existing outputs:
- If `tam-sam-som.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain TAM/SAM/SOM briefly:

> "TAM/SAM/SOM is how we size your market opportunity with discipline, not optimism.
>
> - **TAM (Total Addressable Market):** If everyone in the world who could buy your type of product did, how much revenue?
> - **SAM (Serviceable Addressable Market):** Given your geographic, segment, and channel constraints, how much can you actually serve?
> - **SOM (Serviceable Obtainable Market):** Given your go-to-market capacity and competition, how much can you realistically capture in Years 1-3?
>
> **Key rules:**
> 1. Use BOTH top-down (industry data) AND bottom-up (customer count × ARPU)
> 2. Express everything as ranges, not point estimates
> 3. SOM comes from your actual capacity, not a percentage of SAM
>
> The goal is to **know what you don't know** — the gaps between methods reveal your weakest assumptions."

### 4. M1 Framework Summary

From available M1 frameworks, summarize:

**From Lean Canvas:**
- Customer Segments definition
- Revenue model / pricing logic
- Channels

**From Working Backwards:**
- Primary customer archetype
- Problem statement

**From JTBD:**
- Primary job being done
- Target segment

Present: "Here's what we know about your market from M1 work..."

### 5. Create Output Document

If not continuing, create tam-sam-som.md:

```yaml
---
name: tam-sam-som
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
version: 'v1.0-pre-revenue'
---

# TAM/SAM/SOM Market Sizing: {Project Name}

## Market Definition Brief

*(To be completed in Step 2)*

## Total Addressable Market (TAM)

*(To be completed in Step 3)*

## Serviceable Addressable Market (SAM)

*(To be completed in Step 4)*

## Serviceable Obtainable Market (SOM)

*(To be completed in Step 5)*

## Stress Test & Reconciliation

*(To be completed in Step 6)*

## Synthesis

*(To be completed in Step 7)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Define Market Boundaries

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure tam-sam-som.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-boundaries.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** M1 inputs reviewed, framework explained, output document created

❌ **FAILURE:** Calculating market figures in this step, skipping M1 review, not creating output document
