---
name: 'step-01-init'
description: 'Load context, verify prerequisites, explain Unit Economics framework'
nextStepFile: './step-02-cac-analysis.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/unit-economics.md'
---

# Step 1: Initialize Unit Economics

**Progress: Step 1 of 5** — Next: CAC Analysis

---

## STEP GOAL

Load context from project-memo and upstream frameworks, verify TAM/SAM/SOM is complete, explain the Unit Economics framework, and prepare for financial modeling.

---

## Prior Context

**Builds on:** TAM/SAM/SOM, Leap of Faith
**Inherits (do not restate):** Market sizing (SAM for revenue projections) — reference `{outputFolder}/tam-sam-som.md`; market-related assumptions — reference `{outputFolder}/leap-of-faith.md`
**This framework adds:** Unit economics (CAC, LTV, LTV:CAC ratio, payback period), break-even analysis, financial sensitivity modeling

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor demanding financial honesty. Push for ranges, not point estimates. Every number is a hypothesis. Continue this persona throughout.

### Step-Specific Rules
- If unit-economics.md exists with stepsCompleted, offer to continue from last step
- Do NOT calculate LTV or CAC in this step — that's for later steps
- MUST verify TAM/SAM/SOM is complete before proceeding

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context
2. Read `{outputFolder}/tam-sam-som.md` for market sizing
3. Read `{outputFolder}/../m1-conception/lean-canvas.md` for economic blocks
4. Read `{outputFolder}/bmad-analysis/` contents (if exists) for market pricing data and competitive benchmarks
5. Read `./data/unit-economics-framework.md` for framework knowledge
6. Check if `{outputFolder}/unit-economics.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Check

Verify TAM/SAM/SOM is complete:
- Check project-memo.md `stepsCompleted` for `bi-m2-tam-sam-som`
- Check if `tam-sam-som.md` exists with status: completed

Verify Lean Canvas exists:
- Check for M1 Lean Canvas with Revenue Streams, Cost Structure, Channels, Key Metrics

**If TAM/SAM/SOM NOT complete:**
> "⚠️ Prerequisite Missing: Unit Economics requires a completed TAM/SAM/SOM analysis.
>
> TAM/SAM/SOM provides the market size, segment count, and average deal size we need for realistic projections.
>
> **Action needed:** Return to M2 workflow and complete TAM/SAM/SOM first."

HALT and present option to return to M2 workflow.

**If Lean Canvas is sparse:**
> "⚠️ Lean Canvas blocks needed: Unit Economics requires Revenue Streams, Cost Structure, Channels, and Key Metrics.
>
> We can proceed but will need to develop these as we go. Expect more hypothesis development."

Note gaps and proceed with caution.

### 2. Context Detection

Check for existing outputs:
- If `unit-economics.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Unit Economics briefly:

> "Unit economics answers one question: **Can we make money serving one customer, and how long until we do?**
>
> We'll build a model with:
> - **CAC** — What it costs to acquire one customer
> - **LTV** — What that customer is worth over their lifetime
> - **LTV:CAC Ratio** — The viability indicator (target: 3:1 or higher)
> - **Payback Period** — When we recover acquisition cost
> - **Break-Even** — How many customers until we're self-sustaining
>
> Every number is a hypothesis. We'll use pessimistic/base/optimistic ranges, never point estimates. The pessimistic scenario is where we test viability — not the optimistic one."

### 4. Input Inventory

From upstream frameworks, extract and summarize:

**From TAM/SAM/SOM:**
- SOM size (Year 1 target customers)
- Average deal size / price point
- Segment characteristics

**From Lean Canvas:**
- Revenue Streams: pricing model, price points
- Cost Structure: fixed and variable costs
- Channels: acquisition channels planned
- Key Metrics: retention/churn assumptions

**From Working Backwards (if available):**
- Internal FAQ economics section
- Pricing constraints or willingness-to-pay assumptions

Present: "Here's what we're starting with from your upstream work..."

### 5. Create Output Document

If not continuing, create unit-economics.md:

```yaml
---
name: unit-economics
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
prerequisite: tam-sam-som
---

# Unit Economics: {Project Name}

## Unit Definition

*(To be completed in Step 2)*

## CAC Analysis

*(To be completed in Step 2)*

## LTV Calculation

*(To be completed in Step 3)*

## LTV:CAC Ratio & Payback

*(To be completed in Step 4)*

## Break-Even & Sensitivity

*(To be completed in Step 5)*

## Synthesis

*(To be completed in Step 5)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to CAC Analysis

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure unit-economics.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-cac-analysis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** TAM/SAM/SOM verified complete, inputs inventoried, output document created

❌ **FAILURE:** Proceeding without TAM/SAM/SOM, calculating numbers in this step, using point estimates
