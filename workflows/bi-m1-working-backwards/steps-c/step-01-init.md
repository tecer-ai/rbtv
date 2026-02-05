---
name: 'step-01-init'
description: 'Load context, explain Working Backwards framework, detect continuation'
nextStepFile: './step-02-discover.md'
outputFile: '{outputFolder}/working-backwards.md'
---

# Step 1: Initialize Working Backwards

**Progress: Step 1 of 5** — Next: Customer & Problem Discovery

---

## STEP GOAL

Load context from project-memo, explain the Working Backwards framework, and prepare for customer/problem discovery.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Challenge assumptions, demand clarity, push for specificity. Continue this persona throughout.

### Step-Specific Rules
- If working-backwards.md exists with stepsCompleted, offer to continue from last step
- Do NOT draft any PR/FAQ content in this step — that's for later steps
- Keep framework explanation concise (under 5 minutes reading)

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context
2. Read `./data/working-backwards-framework.md` for framework knowledge
3. Check if `{outputFolder}/working-backwards.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Context Detection

Check for existing outputs:
- If `working-backwards.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 2. Framework Introduction

Explain Working Backwards briefly:

> "Working Backwards is Amazon's method for turning vague ideas into sharp product visions. We'll write a future press release and FAQs as if the product already exists. This forces clarity on:
>
> 1. Who exactly is the customer?
> 2. What specific problem do they have?
> 3. What does our solution do for them?
> 4. Why would they adopt it?
>
> The goal is to **kill or sharpen ideas** before they consume real resources."

### 3. Project Context Summary

From project-memo, summarize:
- Project name
- Current idea/problem statement (if any)
- Any existing customer hypotheses

Present: "Here's what I understand about your project so far..."

### 4. Create Output Document

If not continuing, create working-backwards.md:

```yaml
---
name: working-backwards
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Working Backwards: {Project Name}

## Customer & Problem Brief

*(To be completed in Step 2)*

## Press Release

*(To be completed in Step 3)*

## External FAQ

*(To be completed in Step 4)*

## Internal FAQ

*(To be completed in Step 4)*

## Synthesis

*(To be completed in Step 5)*
```

### 5. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Customer & Problem Discovery

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure working-backwards.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-discover.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** User understands the framework, project context is loaded, output document created

❌ **FAILURE:** Generating PR/FAQ content in this step, skipping to later steps, not creating output document
