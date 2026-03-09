---
name: 'step-01-init'
description: 'Load context, explain Lean Canvas 9 blocks, check prerequisites'
nextStepFile: './step-02-customer-problem.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/lean-canvas.md'
---

# Step 1: Initialize Lean Canvas

**Progress: Step 1 of 6** — Next: Customer & Problem Blocks

---

## STEP GOAL

Load context from prior frameworks, explain the 9-block Lean Canvas methodology, and verify prerequisites are met.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Challenge assumptions. Push for testable hypotheses. Every block is a hypothesis to validate, not a fact to assert.

### Step-Specific Rules
- If lean-canvas.md exists with stepsCompleted, offer to continue from last step
- MUST check prerequisites before proceeding
- Do NOT populate any blocks in this step — that's for later steps
- Keep framework explanation concise (under 5 minutes reading)

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context
2. Read `./data/lean-canvas-framework.md` for framework knowledge
3. Check if `{outputFolder}/lean-canvas.md` exists (continuation mode)
4. Check prerequisites:
   - `{outputFolder}/working-backwards.md` — MUST exist
   - `{outputFolder}/jobs-to-be-done.md` — MUST exist
   - `{outputFolder}/problem-solution-fit.md` — MUST exist

---

## MANDATORY SEQUENCE

### 1. Prerequisite Check

**CRITICAL: Do NOT proceed if prerequisites are missing.**

Check for required outputs:
- If `working-backwards.md` missing: HALT, recommend completing Working Backwards first
- If `jobs-to-be-done.md` missing: HALT, recommend completing JTBD first
- If `problem-solution-fit.md` missing: HALT, recommend completing PSF first

If all present: "Prerequisites verified. Ready to build Lean Canvas."

### 2. Context Detection

Check for existing outputs:
- If `lean-canvas.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Lean Canvas briefly:

> "Lean Canvas encodes your business model as **9 testable hypotheses**:
>
> | Block | Question |
> |-------|----------|
> | Problem | What are the top 3 problems? |
> | Customer Segments | Who experiences these problems? |
> | Unique Value Proposition | Why are you different? |
> | Solution | What are the top 3 features? |
> | Channels | How will you reach customers? |
> | Revenue Streams | How will you make money? |
> | Cost Structure | What are main costs? |
> | Key Metrics | How will you measure success? |
> | Unfair Advantage | What can't be easily copied? |
>
> We'll populate each block using your Working Backwards, JTBD, and Problem-Solution Fit work. Every statement is a hypothesis to validate in M2."

### 4. Prior Framework Summary

Extract and summarize from completed frameworks:

**From Working Backwards:**
- Customer & Problem Brief summary
- PR headline/subheading

**From JTBD:**
- Primary job statement
- Top forces (push, pull, anxieties)

**From Problem-Solution Fit:**
- Problem brief
- Solution elements

Present: "Here's what we'll draw from..."

### 5. Create Output Document

If not continuing, create lean-canvas.md:

```yaml
---
name: lean-canvas
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
prerequisites:
  workingBackwards: completed
  jtbd: completed
  psf: completed
---

# Lean Canvas: {Project Name}

## Canvas Brief

*(To be completed in Step 2)*

## 1. Problem

*(To be completed in Step 2)*

## 2. Customer Segments

*(To be completed in Step 2)*

## 3. Unique Value Proposition

*(To be completed in Step 3)*

## 4. Solution

*(To be completed in Step 3)*

## 5. Channels

*(To be completed in Step 4)*

## 6. Revenue Streams

*(To be completed in Step 4)*

## 7. Cost Structure

*(To be completed in Step 4)*

## 8. Key Metrics

*(To be completed in Step 5)*

## 9. Unfair Advantage

*(To be completed in Step 5)*

## Assumptions List

*(To be populated throughout)*

## Synthesis

*(To be completed in Step 6)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Customer & Problem blocks

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure lean-canvas.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-customer-problem.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Prerequisites verified, user understands the framework, project context loaded, output document created

❌ **FAILURE:** Proceeding without prerequisites, populating blocks in this step, not creating output document
