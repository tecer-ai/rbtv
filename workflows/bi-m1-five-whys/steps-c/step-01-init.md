---
name: 'step-01-init'
description: 'Load context, explain Five Whys framework, detect continuation'
nextStepFile: './step-02-problem-framing.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/five-whys.md'
---

# Step 1: Initialize Five Whys

**Progress: Step 1 of 5** — Next: Problem Framing

---

## STEP GOAL

Load context from project-memo and prior M1 artefacts, explain the Five Whys framework, and prepare for root cause analysis.

---

## Prior Context

**Builds on:** Working Backwards, Jobs-to-be-Done, Problem-Solution Fit, Lean Canvas
**Inherits (do not restate):** Customer definition, problem statement — reference `{outputFolder}/working-backwards.md`; solution description — reference `{outputFolder}/problem-solution-fit.md`; business model structure — reference `{outputFolder}/lean-canvas.md`
**This framework adds:** Root cause structure, causal chains, structural problem analysis

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for structural causes, not surface symptoms. Reject individual blame. This is the final M1 framework — be thorough.

### Step-Specific Rules
- If five-whys.md exists with stepsCompleted, offer to continue from last step
- Do NOT run any 5 Whys chains in this step — that's for later steps
- Verify prerequisite frameworks completed before proceeding

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context
2. Read `./data/five-whys-framework.md` for framework knowledge
3. Check if `{outputFolder}/five-whys.md` exists (continuation mode)
4. Load prior M1 artefacts for problem framing:
   - `{outputFolder}/working-backwards.md` (required)
   - `{outputFolder}/jobs-to-be-done.md` (recommended)
   - `{outputFolder}/problem-solution-fit.md` (recommended)
   - `{outputFolder}/lean-canvas.md` (recommended)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Check

Verify Working Backwards is completed:
- If working-backwards.md has `status: completed`: proceed
- If not completed: HALT and inform founder that Working Backwards is a prerequisite

### 2. Context Detection

Check for existing outputs:
- If `five-whys.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Five Whys briefly:

> "Five Whys is a root cause analysis technique that traces visible problems to their structural causes. We'll:
>
> 1. Select one specific problem scenario from your prior M1 work
> 2. Ask 'Why?' iteratively until we reach a structural cause
> 3. Separate facts from hypotheses along the way
> 4. Identify which root causes your solution will deliberately target
>
> The goal is to **understand why the problem exists structurally** so you build a solution that addresses causes, not just symptoms."

### 4. Available Context Summary

From loaded M1 artefacts, summarize what's available:

| Artefact | Status | Key Inputs for 5 Whys |
|----------|--------|----------------------|
| Working Backwards | ✅/❌ | Customer & Problem Brief, key assumptions |
| JTBD | ✅/❌ | Struggling moments, current alternatives |
| Problem-Solution Fit | ✅/❌ | Behaviours, constraints, critical assumptions |
| Lean Canvas | ✅/❌ | Problem block, Customer Segments, Key Metrics |

Present: "Here's the M1 context available for root cause analysis..."

### 5. Create Output Document

If not continuing, create five-whys.md:

```yaml
---
name: five-whys
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Five Whys: {Project Name}

## Anchor Problem Statement

*(To be completed in Step 2)*

## Scenario Brief

*(To be completed in Step 2)*

## 5 Whys Chains

*(To be completed in Step 3)*

## Root Cause Map

*(To be completed in Step 4)*

## Targeted Root Cause Hypotheses

*(To be completed in Step 4)*

## Synthesis

*(To be completed in Step 5)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Problem Framing

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure five-whys.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-problem-framing.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** User understands the framework, M1 context is loaded, output document created, prerequisites verified

❌ **FAILURE:** Running 5 Whys chains in this step, skipping to later steps, proceeding without Working Backwards completed
